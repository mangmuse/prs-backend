"""Run 통합 테스트 - POST /runs 전체 플로우 검증."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from src.prompts.models import OutputSchemaType
from src.runs.models import Run, RunStatus
from src.runs.service import process_run
from tests.conftest import MockLLMClient


@pytest.mark.asyncio
async def test_run_성공_플로우_json_object(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    test_session_factory,
    prompt_factory,
    dataset_factory,
    profile_factory,
) -> None:
    """Run 생성 → 평가 → 완료 → 조회 전체 플로우 (JSON Object, Pass)."""
    guest_id = guest_cookies["guest_id"]
    _, version = await prompt_factory(
        guest_id,
        output_schema=OutputSchemaType.JSON_OBJECT,
        system_instruction="팩트체커입니다. JSON으로 응답하세요.",
        user_template="검증: {{claim}}",
    )
    dataset = await dataset_factory(
        guest_id,
        rows=[
            {
                "input": {"claim": "하늘은 파랗다"},
                "expected": '{"verdict": "TRUE"}',
            },
        ],
    )
    profile = await profile_factory(guest_id, semantic_threshold=0.7)

    async with test_session_factory() as session:
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

    mock_llm = MockLLMClient('{"verdict": "TRUE", "confidence": 0.95}')

    with (
        patch("src.runs.service.async_session", test_session_factory),
        patch("src.runs.service.get_llm_client", return_value=mock_llm),
    ):
        await process_run(run_id)

    list_response = await client.get("/runs", cookies=guest_cookies)
    assert list_response.status_code == 200
    runs = list_response.json()
    run_summary = next((r for r in runs if r["id"] == run_id), None)
    assert run_summary is not None
    assert run_summary["status"] == "completed"

    response = await client.get(f"/runs/{run_id}", cookies=guest_cookies)
    assert response.status_code == 200
    data = response.json()
    assert data["metrics"]["passRate"] == 1.0
    assert data["metrics"]["formatPassRate"] == 1.0
    assert data["metrics"]["semanticPassRate"] == 1.0

    assert len(data["results"]) == 1
    result = data["results"][0]
    assert result["status"] == "pass"
    assert result["semanticScore"] is not None
    assert result["semanticScore"] >= 0.7


@pytest.mark.asyncio
async def test_run_semantic_실패_플로우(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    test_session_factory,
    prompt_factory,
    dataset_factory,
    profile_factory,
) -> None:
    """Semantic 실패 케이스 - JSON 형식은 맞지만 내용이 다름."""
    guest_id = guest_cookies["guest_id"]
    _, version = await prompt_factory(
        guest_id,
        output_schema=OutputSchemaType.JSON_OBJECT,
        system_instruction="팩트체커입니다. JSON으로 응답하세요.",
        user_template="검증: {{claim}}",
    )
    dataset = await dataset_factory(
        guest_id,
        rows=[
            {
                "input": {"claim": "하늘은 파랗다"},
                "expected": '{"verdict": "TRUE"}',
            },
        ],
    )
    profile = await profile_factory(guest_id, semantic_threshold=0.95)

    async with test_session_factory() as session:
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

    mock_llm = MockLLMClient('{"verdict": "FALSE", "reason": "잘못된 판단"}')

    with (
        patch("src.runs.service.async_session", test_session_factory),
        patch("src.runs.service.get_llm_client", return_value=mock_llm),
    ):
        await process_run(run_id)

    list_response = await client.get("/runs", cookies=guest_cookies)
    assert list_response.status_code == 200
    runs = list_response.json()
    run_summary = next((r for r in runs if r["id"] == run_id), None)
    assert run_summary is not None
    assert run_summary["status"] == "completed"

    response = await client.get(f"/runs/{run_id}", cookies=guest_cookies)
    assert response.status_code == 200
    data = response.json()
    assert data["metrics"]["passRate"] == 0.0
    assert data["metrics"]["formatPassRate"] == 1.0
    assert data["metrics"]["semanticPassRate"] == 0.0

    assert len(data["results"]) == 1
    result = data["results"][0]
    assert result["status"] == "semantic"
    assert result["semanticScore"] is not None
    assert result["semanticScore"] < 0.95
