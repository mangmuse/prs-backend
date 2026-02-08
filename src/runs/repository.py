from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, func, select

from src.auth.models import Guest, User
from src.datasets.models import Dataset
from src.profiles.models import EvaluatorProfile
from src.prompts.models import Prompt, PromptVersion
from src.runs.models import ResultStatus, Run, RunResult, RunStatus


class RunRepository:
    """Run 도메인 데이터 접근 레이어."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, run: Run) -> Run:
        """Run 생성."""
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def get_by_id(self, run_id: int) -> Run | None:
        """Run 단건 조회."""
        return (
            await self.session.execute(select(Run).where(Run.id == run_id))
        ).scalar_one_or_none()

    async def get_by_id_with_owner(
        self,
        run_id: int,
        identity: Guest | User,
    ) -> Run | None:
        """Run 단건 조회 (소유권 검증 포함)."""
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

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(self, run_id: int, status: RunStatus) -> None:
        """Run 상태 업데이트."""
        run = await self.get_by_id(run_id)
        if run:
            run.status = status
            await self.session.commit()

    async def create_result(self, result: RunResult) -> RunResult:
        """RunResult 생성."""
        self.session.add(result)
        return result

    async def get_results_by_run_id(self, run_id: int) -> list[RunResult]:
        """Run의 모든 결과 조회."""
        return list(
            (
                await self.session.execute(
                    select(RunResult)
                    .where(RunResult.run_id == run_id)
                    .order_by(RunResult.id)
                )
            )
            .scalars()
            .all()
        )

    async def get_runs_summary(
        self,
        identity: Guest | User,
        grouped: bool = True,
    ) -> list[Any]:
        """Run 목록 조회 (집계 포함).

        Returns:
            Row 리스트. 각 Row는 다음 속성을 가짐:
            - Run, prompt_id, version_number, prompt_name, dataset_name,
              profile_name, pass_count, total_count, avg_semantic,
              format_pass_count, semantic_pass_count, constraint_pass_count
        """
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

        format_pass_subq = (
            select(func.count())
            .where(
                col(RunResult.run_id) == col(Run.id),
                col(RunResult.is_format_passed) == True,  # noqa: E712
            )
            .correlate(Run)
            .scalar_subquery()
        )

        semantic_pass_subq = (
            select(func.count())
            .where(
                col(RunResult.run_id) == col(Run.id),
                col(RunResult.status) != ResultStatus.FORMAT,
                col(RunResult.status) != ResultStatus.SEMANTIC,
            )
            .correlate(Run)
            .scalar_subquery()
        )

        constraint_pass_subq = (
            select(func.count())
            .where(
                col(RunResult.run_id) == col(Run.id),
                col(RunResult.status) == ResultStatus.PASS,
            )
            .correlate(Run)
            .scalar_subquery()
        )

        stmt = (
            select(
                Run,
                col(Prompt.id).label("prompt_id"),
                PromptVersion.version_number,
                col(Prompt.name).label("prompt_name"),
                col(Dataset.name).label("dataset_name"),
                col(EvaluatorProfile.name).label("profile_name"),
                pass_count_subq.label("pass_count"),
                total_count_subq.label("total_count"),
                avg_semantic_subq.label("avg_semantic"),
                format_pass_subq.label("format_pass_count"),
                semantic_pass_subq.label("semantic_pass_count"),
                constraint_pass_subq.label("constraint_pass_count"),
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

        if grouped:
            latest_run_ids_subq = (
                select(func.max(Run.id).label("latest_id"))
                .join(
                    PromptVersion, col(Run.prompt_version_id) == col(PromptVersion.id)
                )
                .group_by(
                    col(PromptVersion.prompt_id),
                    col(Run.dataset_id),
                    col(Run.profile_id),
                )
                .subquery()
            )
            stmt = stmt.where(col(Run.id).in_(select(latest_run_ids_subq.c.latest_id)))

        stmt = stmt.order_by(col(Run.created_at).desc())

        result = await self.session.execute(stmt)
        return list(result.all())

    async def get_run_detail(
        self,
        run_id: int,
        identity: Guest | User,
    ) -> Any | None:
        """Run 상세 조회 (소유권 검증 포함).

        Returns:
            Row 또는 None. Row는 다음 속성을 가짐:
            - Run, prompt_id, prompt_name, version_number, dataset_name
        """
        stmt = (
            select(
                Run,
                col(Prompt.id).label("prompt_id"),
                col(Prompt.name).label("prompt_name"),
                col(PromptVersion.version_number).label("version_number"),
                col(Dataset.name).label("dataset_name"),
            )
            .join(PromptVersion, col(Run.prompt_version_id) == col(PromptVersion.id))
            .join(Prompt, col(PromptVersion.prompt_id) == col(Prompt.id))
            .join(Dataset, col(Run.dataset_id) == col(Dataset.id))
            .where(col(Run.id) == run_id)
        )

        if isinstance(identity, Guest):
            stmt = stmt.where(col(Prompt.guest_id) == identity.id)
        else:
            stmt = stmt.where(col(Prompt.user_id) == identity.id)

        result = await self.session.execute(stmt)
        return result.one_or_none()

    async def get_profile_by_id(self, profile_id: int) -> EvaluatorProfile | None:
        """EvaluatorProfile 단건 조회."""
        return (
            await self.session.execute(
                select(EvaluatorProfile).where(col(EvaluatorProfile.id) == profile_id)
            )
        ).scalar_one_or_none()

    async def get_run_with_prompt_id(
        self,
        run_id: int,
        identity: Guest | User,
    ) -> Any | None:
        """Run + prompt_id 조회 (소유권 검증 포함).

        Returns:
            Row 또는 None. Row는 다음 속성을 가짐:
            - Run, prompt_id
        """
        stmt = (
            select(
                Run,
                col(PromptVersion.prompt_id).label("prompt_id"),
            )
            .join(PromptVersion, col(Run.prompt_version_id) == col(PromptVersion.id))
            .join(Prompt, col(PromptVersion.prompt_id) == col(Prompt.id))
            .where(col(Run.id) == run_id)
        )

        if isinstance(identity, Guest):
            stmt = stmt.where(col(Prompt.guest_id) == identity.id)
        else:
            stmt = stmt.where(col(Prompt.user_id) == identity.id)

        result = await self.session.execute(stmt)
        return result.one_or_none()

    async def get_related_runs(
        self,
        prompt_id: int,
        dataset_id: int,
        profile_id: int,
    ) -> list[Any]:
        """같은 조합(prompt_id + dataset_id + profile_id)의 Run 목록 조회.

        Returns:
            Row 리스트. 각 Row는 다음 속성을 가짐:
            - Run, version_number, pass_count, total_count
        """
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

        stmt = (
            select(
                Run,
                col(PromptVersion.version_number).label("version_number"),
                pass_count_subq.label("pass_count"),
                total_count_subq.label("total_count"),
            )
            .join(PromptVersion, col(Run.prompt_version_id) == col(PromptVersion.id))
            .where(
                col(PromptVersion.prompt_id) == prompt_id,
                col(Run.dataset_id) == dataset_id,
                col(Run.profile_id) == profile_id,
            )
            .order_by(col(PromptVersion.version_number).desc())
        )

        result = await self.session.execute(stmt)
        return list(result.all())

    async def get_all_versions_by_prompt_id(
        self,
        prompt_id: int,
    ) -> list[PromptVersion]:
        """프롬프트의 모든 버전 조회."""
        stmt = (
            select(PromptVersion)
            .where(col(PromptVersion.prompt_id) == prompt_id)
            .order_by(col(PromptVersion.version_number).desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_run_results_for_comparison(
        self,
        run_id: int,
        identity: Guest | User,
    ) -> list[RunResult] | None:
        """회귀 분석용 Run 결과 조회 (소유권 검증 포함).

        소유권 검증 실패 시 None 반환.
        """
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

        result = await self.session.execute(stmt)
        run = result.scalar_one_or_none()

        if not run:
            return None

        results = (
            (
                await self.session.execute(
                    select(RunResult)
                    .where(col(RunResult.run_id) == run_id)
                    .order_by(col(RunResult.dataset_row_id))
                )
            )
            .scalars()
            .all()
        )

        return list(results)
