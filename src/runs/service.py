import logging

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, func, select

from src.auth.models import Guest, User
from src.common.types import JsonValue, LogicConstraint
from src.database import async_session
from src.datasets.models import Dataset, DatasetRow
from src.llm.factory import get_llm_client
from src.profiles.models import EvaluatorProfile
from src.prompts.models import Prompt, PromptVersion
from src.runs.evaluator.waterfall import evaluate_waterfall
from src.runs.models import ResultStatus, Run, RunResult, RunStatus
from src.runs.schemas import (
    AssembledPrompt,
    ProfileInRun,
    RunDetailResponse,
    RunMetrics,
    RunResultResponse,
    RunSummaryResponse,
)

logger = logging.getLogger(__name__)


def assemble_prompt(
    user_template: str,
    input_data: dict[str, JsonValue],
) -> str:
    """
    user_template의 {{key}}를 input_data[key]로 치환.

    예: "검증할 문장: {{claim}}" + {"claim": "서울은 수도다"}
    → "검증할 문장: 서울은 수도다"
    """
    result = user_template
    for key, value in input_data.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


async def process_run(run_id: int) -> None:
    """BackgroundTask에서 Run 처리."""
    async with async_session() as session:
        run = (await session.execute(
            select(Run).where(Run.id == run_id)
        )).scalar_one_or_none()

        if run is None:
            logger.error(f"Run {run_id}를 찾을 수 없습니다")
            return

        try:
            assert run.id is not None

            version = (await session.execute(
                select(PromptVersion).where(PromptVersion.id == run.prompt_version_id)
            )).scalar_one()

            rows = (await session.execute(
                select(DatasetRow)
                .where(DatasetRow.dataset_id == run.dataset_id)
                .order_by(col(DatasetRow.row_index))
            )).scalars().all()

            profile = (await session.execute(
                select(EvaluatorProfile).where(EvaluatorProfile.id == run.profile_id)
            )).scalar_one()

            llm = get_llm_client(version.model)

            for row in rows:
                assert row.id is not None

                user_message = assemble_prompt(version.user_template, row.input_data)

                raw_output = await llm.generate(
                    system_instruction=version.system_instruction,
                    user_message=user_message,
                    temperature=version.temperature,
                )

                constraints: list[LogicConstraint] = profile.global_constraints or []

                eval_result = evaluate_waterfall(
                    raw_output=raw_output,
                    output_schema=version.output_schema,
                    expected_output=row.expected_output,
                    threshold=profile.semantic_threshold,
                    constraints=constraints,
                )

                parsed = eval_result.format_result.parsed_output
                parsed_dict = parsed if isinstance(parsed, dict) else None

                result = RunResult(
                    run_id=run.id,
                    dataset_row_id=row.id,
                    input_snapshot=row.input_data,
                    expected_snapshot=row.expected_output,
                    assembled_prompt={
                        "system_instruction": version.system_instruction,
                        "user_message": user_message,
                    },
                    raw_output=raw_output,
                    is_format_passed=eval_result.format_result.passed,
                    parsed_output=parsed_dict,
                    semantic_score=(
                        eval_result.semantic_result.semantic_score
                        if eval_result.semantic_result
                        else 0.0
                    ),
                    logic_results=(
                        eval_result.logic_result.model_dump()
                        if eval_result.logic_result
                        else {}
                    ),
                    status=eval_result.status,
                )
                session.add(result)

            run.status = RunStatus.COMPLETED
            await session.commit()

        except Exception as e:
            logger.exception(f"Run {run_id} 처리 실패: {e}")
            run.status = RunStatus.FAILED
            await session.commit()


async def get_runs_summary(
    identity: Guest | User,
    session: AsyncSession,
) -> list[RunSummaryResponse]:
    """사용자의 Run 목록 조회 (집계 포함)."""
    pass_count_subq = (
        select(func.count())
        .where(
            col(RunResult.run_id) == col(Run.id),
            col(RunResult.status) == ResultStatus.PASS,
        )
        .correlate(Run)
        .scalar_subquery()
    )

    total_count_subq = (
        select(func.count())
        .where(col(RunResult.run_id) == col(Run.id))
        .correlate(Run)
        .scalar_subquery()
    )

    avg_semantic_subq = (
        select(func.avg(RunResult.semantic_score))
        .where(col(RunResult.run_id) == col(Run.id))
        .correlate(Run)
        .scalar_subquery()
    )

    stmt = (
        select(
            Run,
            PromptVersion.version_number,
            col(Prompt.name).label("prompt_name"),
            col(Dataset.name).label("dataset_name"),
            col(EvaluatorProfile.name).label("profile_name"),
            pass_count_subq.label("pass_count"),
            total_count_subq.label("total_count"),
            avg_semantic_subq.label("avg_semantic"),
        )
        .join(PromptVersion, col(Run.prompt_version_id) == col(PromptVersion.id))
        .join(Prompt, col(PromptVersion.prompt_id) == col(Prompt.id))
        .join(Dataset, col(Run.dataset_id) == col(Dataset.id))
        .join(EvaluatorProfile, col(Run.profile_id) == col(EvaluatorProfile.id))
    )

    if isinstance(identity, Guest):
        stmt = stmt.where(col(Prompt.guest_id) == identity.id)
    else:
        stmt = stmt.where(col(Prompt.user_id) == identity.id)

    stmt = stmt.order_by(col(Run.created_at).desc())

    result = await session.execute(stmt)
    rows = result.all()

    return [
        RunSummaryResponse(
            id=row.Run.id,
            prompt_version_id=row.Run.prompt_version_id,
            prompt_name=row.prompt_name,
            version_number=row.version_number,
            dataset_id=row.Run.dataset_id,
            dataset_name=row.dataset_name,
            profile_id=row.Run.profile_id,
            profile_name=row.profile_name,
            status=row.Run.status.value,
            pass_rate=(
                (row.pass_count / row.total_count * 100) if row.total_count else None
            ),
            avg_semantic=row.avg_semantic,
            total_rows=row.total_count or 0,
            created_at=row.Run.created_at,
        )
        for row in rows
    ]


async def get_run_detail(
    run_id: int,
    identity: Guest | User,
    session: AsyncSession,
) -> RunDetailResponse:
    """Run 상세 조회 (Live Playground용)."""
    stmt = (
        select(Run)
        .join(PromptVersion, col(Run.prompt_version_id) == col(PromptVersion.id))
        .join(Prompt, col(PromptVersion.prompt_id) == col(Prompt.id))
        .where(col(Run.id) == run_id)
    )

    if isinstance(identity, Guest):
        stmt = stmt.where(col(Prompt.guest_id) == identity.id)
    else:
        stmt = stmt.where(col(Prompt.user_id) == identity.id)

    result = await session.execute(stmt)
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Run을 찾을 수 없습니다")

    profile = (
        await session.execute(
            select(EvaluatorProfile).where(col(EvaluatorProfile.id) == run.profile_id)
        )
    ).scalar_one()

    results = (
        await session.execute(
            select(RunResult)
            .where(col(RunResult.run_id) == run_id)
            .order_by(col(RunResult.id))
        )
    ).scalars().all()

    assert run.id is not None
    assert profile.id is not None

    total = len(results)
    pass_count = sum(1 for r in results if r.status == ResultStatus.PASS)
    avg_semantic = sum(r.semantic_score for r in results) / total if total else 0.0

    result_responses: list[RunResultResponse] = []
    for r in results:
        assert r.id is not None
        result_responses.append(
            RunResultResponse(
                id=r.id,
                dataset_row_id=r.dataset_row_id,
                input_snapshot=r.input_snapshot,
                expected_snapshot=r.expected_snapshot,
                assembled_prompt=AssembledPrompt(
                    system_instruction=r.assembled_prompt.get("system_instruction", ""),
                    user_message=r.assembled_prompt.get("user_message", ""),
                ),
                status=r.status,
                is_format_passed=r.is_format_passed,
                semantic_score=r.semantic_score,
                logic_results=r.logic_results,
                raw_output=r.raw_output,
                parsed_output=r.parsed_output,
            )
        )

    return RunDetailResponse(
        id=run.id,
        profile=ProfileInRun(
            id=profile.id,
            name=profile.name,
            semantic_threshold=profile.semantic_threshold,
            global_constraints=profile.global_constraints or [],
        ),
        metrics=RunMetrics(
            pass_rate=(pass_count / total * 100) if total else 0.0,
            avg_semantic=avg_semantic,
        ),
        results=result_responses,
    )
