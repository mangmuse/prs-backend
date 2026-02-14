from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from src.auth.models import Guest, User

if TYPE_CHECKING:
    from src.llm.base import LLMClient
from src.common.types import JsonValue, LogicConstraint
from src.database import async_session
from src.datasets.models import DatasetRow
from src.llm.factory import get_llm_client
from src.llm.rate_limiter import extract_provider, get_semaphore
from src.llm.security import sanitize_error_message
from src.prompts.models import PromptVersion
from src.runs.evaluator.waterfall import evaluate_waterfall, re_evaluate_from_stored
from src.runs.models import ResultStatus, Run, RunResult, RunStatus
from src.runs.regression import calculate_p_value
from src.runs.repository import RunRepository
from src.runs.schemas import (
    AssembledPrompt,
    CreateRunRequest,
    ProfileInRun,
    ReEvaluatedRow,
    ReEvaluateRequest,
    ReEvaluateResponse,
    RegressionComparisonResponse,
    RelatedRunResponse,
    RelatedVersionsResponse,
    RowComparisonData,
    RunDetailResponse,
    RunMetrics,
    RunResultResponse,
    RunSummaryResponse,
    UnexecutedVersionResponse,
    UpdateProfileSnapshotRequest,
)

logger = logging.getLogger(__name__)


async def delete_run(
    run: Run,
    session: AsyncSession,
) -> None:
    """Run 삭제 (관련 RunResult cascade 삭제)."""
    assert run.id is not None
    _ = await session.execute(
        sa_delete(RunResult).where(col(RunResult.run_id) == run.id)
    )
    await session.delete(run)
    await session.commit()


async def create_run(
    data: CreateRunRequest,
    identity: Guest | User,
    session: AsyncSession,
) -> Run:
    """Run 생성 (DB 저장)."""
    repo = RunRepository(session)

    profile = await repo.get_profile_by_id(data.profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="프로필을 찾을 수 없습니다")

    profile_snapshot = {
        "semantic_threshold": profile.semantic_threshold,
        "global_constraints": [
            c.model_dump() if hasattr(c, "model_dump") else c
            for c in (profile.global_constraints or [])
        ],
    }

    run = Run(
        prompt_version_id=data.prompt_version_id,
        dataset_id=data.dataset_id,
        profile_id=data.profile_id,
        profile_snapshot=profile_snapshot,
        status=RunStatus.RUNNING,
        guest_id=identity.id if isinstance(identity, Guest) else None,
        user_id=identity.id if isinstance(identity, User) else None,
    )
    return await repo.create(run)


def assemble_prompt(
    user_template: str,
    input_data: dict[str, JsonValue],
) -> str:
    """
    user_template의 {{key}}를 input_data[key]로 치환.

    예: "검증할 문장: {{claim}}" + {"claim": "서울은 수도다"}
    → "검증할 문장: 서울은 수도다"
    """
    logger.debug(
        "프롬프트 조립 시작 | template_len=%d, input_keys=%s",
        len(user_template),
        list(input_data.keys()),
    )

    result = user_template
    for key, value in input_data.items():
        placeholder = f"{{{{{key}}}}}"
        if placeholder in result:
            result = result.replace(placeholder, str(value))
            logger.debug("치환 성공 | key=%s", key)
        else:
            logger.warning(
                "치환 실패 | key='%s'가 템플릿에 없음 (사용 가능: %s)", key, placeholder
            )

    logger.debug("프롬프트 조립 완료 | result_len=%d", len(result))
    return result


async def _process_single_row(
    row: DatasetRow,
    run_id: int,
    version: PromptVersion,
    llm: LLMClient,
    threshold: float,
    constraints: list[LogicConstraint],
) -> RunResult:
    """단일 row 처리 (LLM 호출 + 평가). 예외 발생 시 상위에서 처리."""
    assert row.id is not None
    start_time = time.perf_counter()

    user_message = assemble_prompt(version.user_template, row.input_data)

    logger.debug(
        "LLM 호출 시작 | row_id=%d, model=%s, temperature=%.1f",
        row.id,
        version.model,
        version.temperature,
    )
    llm_start = time.perf_counter()
    raw_output = await llm.generate(
        system_instruction=version.system_instruction,
        user_message=user_message,
        temperature=version.temperature,
    )
    llm_ms = int((time.perf_counter() - llm_start) * 1000)
    logger.debug(
        "LLM 응답 수신 | row_id=%d, output_len=%d, llm_ms=%d",
        row.id,
        len(raw_output),
        llm_ms,
    )

    eval_start = time.perf_counter()
    eval_result = evaluate_waterfall(
        raw_output=raw_output,
        output_schema=version.output_schema,
        expected_output=row.expected_output,
        threshold=threshold,
        constraints=constraints,
    )
    eval_ms = int((time.perf_counter() - eval_start) * 1000)

    total_ms = int((time.perf_counter() - start_time) * 1000)

    parsed = eval_result.format_result.parsed_output
    parsed_dict = parsed if isinstance(parsed, dict) else None

    return RunResult(
        run_id=run_id,
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
        constraint_results=(
            eval_result.constraint_result.model_dump()
            if eval_result.constraint_result
            else {}
        ),
        status=eval_result.status,
        trace={"llm_ms": llm_ms, "eval_ms": eval_ms, "total_ms": total_ms},
    )


async def execute_run(run_id: int, api_key: str | None = None) -> None:
    """Run 실행 로직 (LLM 호출 및 평가 수행). 모든 row를 병렬로 처리."""
    start_time = time.perf_counter()
    logger.info("Run 처리 시작 | run_id=%d", run_id)

    async with async_session() as session:
        repo = RunRepository(session)
        run = await repo.get_by_id(run_id)

        if run is None:
            logger.error("Run을 찾을 수 없음 | run_id=%d", run_id)
            return

        try:
            assert run.id is not None
            current_run_id = run.id

            version = (
                await session.execute(
                    select(PromptVersion).where(
                        PromptVersion.id == run.prompt_version_id
                    )
                )
            ).scalar_one()

            rows = (
                (
                    await session.execute(
                        select(DatasetRow)
                        .where(DatasetRow.dataset_id == run.dataset_id)
                        .order_by(col(DatasetRow.row_index))
                    )
                )
                .scalars()
                .all()
            )

            threshold = run.profile_snapshot["semantic_threshold"]
            snapshot_constraints = run.profile_snapshot["global_constraints"]

            logger.info(
                "Run 설정 로드 완료 | version_id=%d, model=%s, rows=%d, threshold=%.2f",
                version.id,
                version.model,
                len(rows),
                threshold,
            )

            llm = get_llm_client(version.model, api_key=api_key)

            provider = extract_provider(version.model)
            sem = get_semaphore(provider)

            async def _bounded_process(row: DatasetRow) -> RunResult:
                async with sem:
                    return await _process_single_row(
                        row=row,
                        run_id=current_run_id,
                        version=version,
                        llm=llm,
                        threshold=threshold,
                        constraints=snapshot_constraints,
                    )

            tasks = [_bounded_process(row) for row in rows]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            success_count = 0
            fail_count = 0
            for idx, result in enumerate(results, 1):
                if isinstance(result, BaseException):
                    logger.error(
                        "Row %d 처리 실패 | run_id=%d, error=%s",
                        idx,
                        run_id,
                        sanitize_error_message(str(result)),
                    )
                    fail_count += 1
                    continue
                _ = await repo.create_result(result)
                success_count += 1

            logger.info(
                "Row 처리 완료 | run_id=%d, 성공=%d, 실패=%d",
                run_id,
                success_count,
                fail_count,
            )

            elapsed_secs = time.perf_counter() - start_time

            if success_count == 0 and fail_count > 0:
                final_status = RunStatus.FAILED
            else:
                final_status = RunStatus.COMPLETED

            await repo.update_status(run_id, final_status)
            logger.info(
                "Run 완료 | run_id=%d, status=%s, elapsed=%.1fs (%.1fmin)",
                run_id,
                final_status.value.upper(),
                elapsed_secs,
                elapsed_secs / 60,
            )

        except Exception as e:
            logger.exception(
                "Run 처리 실패 | run_id=%d, error=%s",
                run_id,
                sanitize_error_message(str(e)),
            )
            await repo.update_status(run_id, RunStatus.FAILED)


async def get_runs_summary(
    identity: Guest | User,
    session: AsyncSession,
    grouped: bool = True,
) -> list[RunSummaryResponse]:
    """사용자의 Run 목록 조회 (집계 포함).

    Args:
        grouped: True면 같은 조합(prompt_id + dataset_id + profile_id)에서 최신 Run만 반환
    """
    repo = RunRepository(session)
    rows = await repo.get_runs_summary(identity, grouped)

    result: list[RunSummaryResponse] = []
    for row in rows:
        assert row.run.id is not None
        result.append(
            RunSummaryResponse(
                id=row.run.id,
                prompt_id=row.prompt_id,
                prompt_version_id=row.run.prompt_version_id,
                prompt_name=row.prompt_name,
                version_number=row.version_number,
                dataset_id=row.run.dataset_id,
                dataset_name=row.dataset_name,
                profile_id=row.run.profile_id,
                profile_name=row.profile_name,
                status=row.run.status.value,
                pass_rate=(
                    (row.pass_count / row.total_count) if row.total_count else None
                ),
                avg_semantic=row.avg_semantic,
                format_pass_rate=(
                    (row.format_pass_count / row.total_count)
                    if row.total_count
                    else None
                ),
                semantic_pass_rate=(
                    (row.semantic_pass_count / row.total_count)
                    if row.total_count
                    else None
                ),
                constraint_pass_rate=(
                    (row.constraint_pass_count / row.total_count)
                    if row.total_count
                    else None
                ),
                total_rows=row.total_count or 0,
                created_at=row.run.created_at,
            )
        )
    return result


async def get_run_detail(
    run_id: int,
    identity: Guest | User,
    session: AsyncSession,
) -> RunDetailResponse:
    """Run 상세 조회 (결과 및 통계 포함)."""
    repo = RunRepository(session)

    row = await repo.get_run_detail(run_id, identity)
    if not row:
        raise HTTPException(status_code=404, detail="Run을 찾을 수 없습니다")

    run = row.run
    prompt_id = row.prompt_id
    prompt_name = row.prompt_name
    version_number = row.version_number
    dataset_name = row.dataset_name

    profile = await repo.get_profile_by_id(run.profile_id)
    assert profile is not None

    results = await repo.get_results_by_run_id(run_id)

    assert run.id is not None
    assert profile.id is not None

    total = len(results)
    pass_count = sum(1 for r in results if r.status == ResultStatus.PASS)
    avg_semantic = sum(r.semantic_score for r in results) / total if total else 0.0
    format_pass_count = sum(1 for r in results if r.is_format_passed)
    semantic_pass_count = sum(
        1
        for r in results
        if r.status not in (ResultStatus.FORMAT, ResultStatus.SEMANTIC)
    )
    constraint_pass_count = pass_count

    result_responses: list[RunResultResponse] = []
    for idx, r in enumerate(results, 1):
        assert r.id is not None
        result_responses.append(
            RunResultResponse(
                id=r.id,
                row_index=idx,
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
                constraint_results=r.constraint_results,
                raw_output=r.raw_output,
                parsed_output=r.parsed_output,
            )
        )

    return RunDetailResponse(
        id=run.id,
        prompt_id=prompt_id,
        prompt_version_id=run.prompt_version_id,
        dataset_id=run.dataset_id,
        profile_id=run.profile_id,
        prompt_name=prompt_name,
        version_number=version_number,
        dataset_name=dataset_name,
        status=run.status.value,
        created_at=run.created_at,
        profile=ProfileInRun(
            id=profile.id,
            name=profile.name,
            semantic_threshold=run.profile_snapshot["semantic_threshold"],
            global_constraints=run.profile_snapshot["global_constraints"],
        ),
        metrics=RunMetrics(
            pass_rate=(pass_count / total) if total else 0.0,
            avg_semantic=avg_semantic,
            format_pass_rate=(format_pass_count / total) if total else 0.0,
            semantic_pass_rate=(semantic_pass_count / total) if total else 0.0,
            constraint_pass_rate=(constraint_pass_count / total) if total else 0.0,
        ),
        results=result_responses,
    )


async def get_related_versions(
    run_id: int,
    identity: Guest | User,
    session: AsyncSession,
) -> RelatedVersionsResponse:
    """현재 Run과 같은 조합의 다른 버전 Run들 및 미실행 버전 조회."""
    repo = RunRepository(session)

    run_row = await repo.get_run_with_prompt_id(run_id, identity)
    if not run_row:
        raise HTTPException(status_code=404, detail="Run을 찾을 수 없습니다")

    current_run = run_row.run
    prompt_id = run_row.prompt_id
    dataset_id = current_run.dataset_id
    profile_id = current_run.profile_id

    related_rows = await repo.get_related_runs(prompt_id, dataset_id, profile_id)

    executed_runs: list[RelatedRunResponse] = []
    for row in related_rows:
        assert row.run.id is not None
        executed_runs.append(
            RelatedRunResponse(
                id=row.run.id,
                version_number=row.version_number,
                status=row.run.status.value,
                pass_rate=(
                    (row.pass_count / row.total_count) if row.total_count else None
                ),
                created_at=row.run.created_at,
            )
        )

    executed_version_ids = {row.run.prompt_version_id for row in related_rows}

    all_versions = await repo.get_all_versions_by_prompt_id(prompt_id)

    unexecuted_versions = [
        UnexecutedVersionResponse(
            id=v.id,
            version_number=v.version_number,
        )
        for v in all_versions
        if v.id is not None and v.id not in executed_version_ids
    ]

    return RelatedVersionsResponse(
        executed_runs=executed_runs,
        unexecuted_versions=unexecuted_versions,
    )


async def compare_runs(
    base_run_id: int,
    target_run_id: int,
    identity: Guest | User,
    session: AsyncSession,
) -> RegressionComparisonResponse:
    """두 Run 간 회귀 분석용 raw 데이터 제공."""
    repo = RunRepository(session)

    base_results = await repo.get_run_results_for_comparison(base_run_id, identity)
    if base_results is None:
        raise HTTPException(status_code=404, detail="Run을 찾을 수 없습니다")

    target_results = await repo.get_run_results_for_comparison(target_run_id, identity)
    if target_results is None:
        raise HTTPException(status_code=404, detail="Run을 찾을 수 없습니다")

    base_by_row = {r.dataset_row_id: r for r in base_results}
    target_by_row = {r.dataset_row_id: r for r in target_results}

    common_row_ids = sorted(set(base_by_row.keys()) & set(target_by_row.keys()))

    row_comparisons: list[RowComparisonData] = []
    base_scores: list[float] = []
    target_scores: list[float] = []

    for idx, row_id in enumerate(common_row_ids, 1):
        base = base_by_row[row_id]
        target = target_by_row[row_id]

        row_comparisons.append(
            RowComparisonData(
                row_index=idx,
                dataset_row_id=row_id,
                base_status=base.status,
                target_status=target.status,
                base_semantic_score=base.semantic_score,
                target_semantic_score=target.semantic_score,
            )
        )

        base_scores.append(base.semantic_score)
        target_scores.append(target.semantic_score)

    p_value = calculate_p_value(base_scores, target_scores)

    return RegressionComparisonResponse(
        p_value=p_value,
        row_comparisons=row_comparisons,
    )


async def update_run_profile_snapshot(
    run_id: int,
    data: UpdateProfileSnapshotRequest,
    identity: Guest | User,
    session: AsyncSession,
) -> None:
    """Run의 profile_snapshot 업데이트."""
    repo = RunRepository(session)

    run = await repo.get_by_id_with_owner(run_id, identity)
    if run is None:
        raise HTTPException(status_code=404, detail="Run을 찾을 수 없습니다")

    run.profile_snapshot = {
        "semantic_threshold": data.semantic_threshold,
        "global_constraints": [c.model_dump() for c in data.global_constraints],
    }
    await session.commit()


async def re_evaluate_run(
    run_id: int,
    data: ReEvaluateRequest,
    identity: Guest | User,
    session: AsyncSession,
) -> ReEvaluateResponse:
    """저장된 결과로 재평가 (LLM 호출 없이 미리보기)."""
    repo = RunRepository(session)

    run = await repo.get_by_id_with_owner(run_id, identity)
    if run is None:
        raise HTTPException(status_code=404, detail="Run을 찾을 수 없습니다")

    results = await repo.get_results_by_run_id(run_id)

    re_evaluated: list[ReEvaluatedRow] = []
    pass_count = 0

    for r in results:
        assert r.id is not None

        new_status, constraint_result = re_evaluate_from_stored(
            is_format_passed=r.is_format_passed,
            parsed_output=r.parsed_output,
            semantic_score=r.semantic_score,
            threshold=data.semantic_threshold,
            constraints=data.global_constraints,
        )

        if new_status == ResultStatus.PASS:
            pass_count += 1

        re_evaluated.append(
            ReEvaluatedRow(
                id=r.id,
                status=new_status,
                constraint_results=constraint_result.model_dump()
                if constraint_result
                else None,
            )
        )

    total = len(results)
    pass_rate = (pass_count / total) if total else 0.0

    return ReEvaluateResponse(results=re_evaluated, pass_rate=pass_rate)
