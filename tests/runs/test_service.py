"""runs service 테스트 - 비즈니스 로직 검증 (LLM 모킹)."""

from unittest.mock import AsyncMock, patch

import pytest

from src.prompts.models import OutputSchemaType
from src.runs.models import ResultStatus, Run, RunResult, RunStatus
from src.runs.service import assemble_prompt, process_run


class TestAssemblePrompt:
    """프롬프트 조립 함수 단위 테스트."""

    def test_single_variable_replacement(self) -> None:
        """단일 변수 치환."""
        template = "검증할 문장: {{claim}}"
        input_data = {"claim": "서울은 수도다"}

        result = assemble_prompt(template, input_data)

        assert result == "검증할 문장: 서울은 수도다"

    def test_multiple_variable_replacement(self) -> None:
        """다중 변수 치환."""
        template = "주제: {{topic}}, 질문: {{question}}"
        input_data = {"topic": "역사", "question": "언제?"}

        result = assemble_prompt(template, input_data)

        assert result == "주제: 역사, 질문: 언제?"

    def test_unused_variable_in_input(self) -> None:
        """input_data에 있지만 템플릿에 없는 변수는 무시."""
        template = "내용: {{content}}"
        input_data = {"content": "테스트", "unused": "무시됨"}

        result = assemble_prompt(template, input_data)

        assert result == "내용: 테스트"

    def test_missing_variable_keeps_placeholder(self) -> None:
        """템플릿에 있지만 input_data에 없는 변수는 그대로 유지."""
        template = "이름: {{name}}, 나이: {{age}}"
        input_data = {"name": "홍길동"}

        result = assemble_prompt(template, input_data)

        assert result == "이름: 홍길동, 나이: {{age}}"


class TestProcessRun:
    """Run 처리 통합 테스트 (LLM 모킹)."""

    @pytest.mark.asyncio
    async def test_process_run_completes_with_pass_result(
        self,
        test_session_factory,
        guest_factory,
        prompt_factory,
        dataset_factory,
        profile_factory,
    ) -> None:
        """Run 처리 성공 시 COMPLETED 상태 + RunResult 생성."""
        guest = await guest_factory()
        guest_id = guest.id

        _, version = await prompt_factory(
            guest_id,
            system_instruction="You are a fact checker.",
            user_template="Verify: {{claim}}",
            output_schema=OutputSchemaType.FREEFORM,
        )
        dataset = await dataset_factory(
            guest_id,
            rows=[
                {"input": {"claim": "서울은 한국의 수도다"}, "expected": "TRUE"},
            ],
        )
        profile = await profile_factory(guest_id, semantic_threshold=0.7)

        async with test_session_factory() as session:
            assert version.id is not None
            assert dataset.id is not None
            assert profile.id is not None

            run = Run(
                prompt_version_id=version.id,
                dataset_id=dataset.id,
                profile_id=profile.id,
                status=RunStatus.RUNNING,
            )
            session.add(run)
            await session.commit()
            await session.refresh(run)
            run_id = run.id

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value="TRUE")

        with (
            patch("src.runs.service.async_session", test_session_factory),
            patch("src.runs.service.get_llm_client", return_value=mock_llm),
        ):
            await process_run(run_id)

        async with test_session_factory() as session:
            from sqlmodel import select

            run = (await session.execute(
                select(Run).where(Run.id == run_id)
            )).scalar_one()

            assert run.status == RunStatus.COMPLETED

            results = (await session.execute(
                select(RunResult).where(RunResult.run_id == run_id)
            )).scalars().all()

            assert len(results) == 1
            assert results[0].raw_output == "TRUE"
            assert results[0].status == ResultStatus.PASS

    @pytest.mark.asyncio
    async def test_process_run_handles_semantic_fail(
        self,
        test_session_factory,
        guest_factory,
        prompt_factory,
        dataset_factory,
        profile_factory,
    ) -> None:
        """Semantic 점수가 낮으면 SEMANTIC 상태."""
        guest = await guest_factory()
        guest_id = guest.id

        _, version = await prompt_factory(
            guest_id,
            output_schema=OutputSchemaType.FREEFORM,
        )
        dataset = await dataset_factory(
            guest_id,
            rows=[
                {"input": {"input": "테스트"}, "expected": "정확한 답변"},
            ],
        )
        profile = await profile_factory(guest_id, semantic_threshold=0.99)

        async with test_session_factory() as session:
            assert version.id is not None
            assert dataset.id is not None
            assert profile.id is not None

            run = Run(
                prompt_version_id=version.id,
                dataset_id=dataset.id,
                profile_id=profile.id,
                status=RunStatus.RUNNING,
            )
            session.add(run)
            await session.commit()
            await session.refresh(run)
            run_id = run.id

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value="완전히 다른 응답")

        with (
            patch("src.runs.service.async_session", test_session_factory),
            patch("src.runs.service.get_llm_client", return_value=mock_llm),
        ):
            await process_run(run_id)

        async with test_session_factory() as session:
            from sqlmodel import select

            results = (await session.execute(
                select(RunResult).where(RunResult.run_id == run_id)
            )).scalars().all()

            assert len(results) == 1
            assert results[0].status == ResultStatus.SEMANTIC

    @pytest.mark.asyncio
    async def test_process_run_handles_format_fail(
        self,
        test_session_factory,
        guest_factory,
        prompt_factory,
        dataset_factory,
        profile_factory,
    ) -> None:
        """JSON 파싱 실패 시 FORMAT 상태."""
        guest = await guest_factory()
        guest_id = guest.id

        _, version = await prompt_factory(
            guest_id,
            output_schema=OutputSchemaType.JSON_OBJECT,
        )
        dataset = await dataset_factory(
            guest_id,
            rows=[
                {"input": {"input": "테스트"}, "expected": '{"result": "ok"}'},
            ],
        )
        profile = await profile_factory(guest_id)

        async with test_session_factory() as session:
            assert version.id is not None
            assert dataset.id is not None
            assert profile.id is not None

            run = Run(
                prompt_version_id=version.id,
                dataset_id=dataset.id,
                profile_id=profile.id,
                status=RunStatus.RUNNING,
            )
            session.add(run)
            await session.commit()
            await session.refresh(run)
            run_id = run.id

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value="이것은 JSON이 아닙니다")

        with (
            patch("src.runs.service.async_session", test_session_factory),
            patch("src.runs.service.get_llm_client", return_value=mock_llm),
        ):
            await process_run(run_id)

        async with test_session_factory() as session:
            from sqlmodel import select

            results = (await session.execute(
                select(RunResult).where(RunResult.run_id == run_id)
            )).scalars().all()

            assert len(results) == 1
            assert results[0].status == ResultStatus.FORMAT
            assert results[0].is_format_passed is False

    @pytest.mark.asyncio
    async def test_process_run_with_multiple_rows(
        self,
        test_session_factory,
        guest_factory,
        prompt_factory,
        dataset_factory,
        profile_factory,
    ) -> None:
        """여러 Row 처리 시 모두 결과 생성."""
        guest = await guest_factory()
        guest_id = guest.id

        _, version = await prompt_factory(guest_id, output_schema=OutputSchemaType.FREEFORM)
        dataset = await dataset_factory(
            guest_id,
            rows=[
                {"input": {"claim": "1"}, "expected": "A"},
                {"input": {"claim": "2"}, "expected": "B"},
                {"input": {"claim": "3"}, "expected": "C"},
            ],
        )
        profile = await profile_factory(guest_id, semantic_threshold=0.5)

        async with test_session_factory() as session:
            assert version.id is not None
            assert dataset.id is not None
            assert profile.id is not None

            run = Run(
                prompt_version_id=version.id,
                dataset_id=dataset.id,
                profile_id=profile.id,
                status=RunStatus.RUNNING,
            )
            session.add(run)
            await session.commit()
            await session.refresh(run)
            run_id = run.id

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(side_effect=["A", "B", "C"])

        with (
            patch("src.runs.service.async_session", test_session_factory),
            patch("src.runs.service.get_llm_client", return_value=mock_llm),
        ):
            await process_run(run_id)

        async with test_session_factory() as session:
            from sqlmodel import select

            run = (await session.execute(
                select(Run).where(Run.id == run_id)
            )).scalar_one()
            assert run.status == RunStatus.COMPLETED

            results = (await session.execute(
                select(RunResult).where(RunResult.run_id == run_id)
            )).scalars().all()

            assert len(results) == 3
            assert all(r.status == ResultStatus.PASS for r in results)

    @pytest.mark.asyncio
    async def test_process_run_sets_failed_on_exception(
        self,
        test_session_factory,
        guest_factory,
        prompt_factory,
        dataset_factory,
        profile_factory,
    ) -> None:
        """LLM 호출 실패 시 FAILED 상태."""
        guest = await guest_factory()
        guest_id = guest.id

        _, version = await prompt_factory(guest_id)
        dataset = await dataset_factory(
            guest_id,
            rows=[{"input": {"input": "테스트"}, "expected": "응답"}],
        )
        profile = await profile_factory(guest_id)

        async with test_session_factory() as session:
            assert version.id is not None
            assert dataset.id is not None
            assert profile.id is not None

            run = Run(
                prompt_version_id=version.id,
                dataset_id=dataset.id,
                profile_id=profile.id,
                status=RunStatus.RUNNING,
            )
            session.add(run)
            await session.commit()
            await session.refresh(run)
            run_id = run.id

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(side_effect=Exception("API Error"))

        with (
            patch("src.runs.service.async_session", test_session_factory),
            patch("src.runs.service.get_llm_client", return_value=mock_llm),
        ):
            await process_run(run_id)

        async with test_session_factory() as session:
            from sqlmodel import select

            run = (await session.execute(
                select(Run).where(Run.id == run_id)
            )).scalar_one()

            assert run.status == RunStatus.FAILED
