import pytest
from httpx import AsyncClient

from src.runs.regression import calculate_p_value


class TestCalculatePValue:
    """p-value 계산 함수 테스트 (paired t-test)"""

    def test_identical_scores_high_p_value(self):
        """동일한 점수 = 높은 p-value (유의미하지 않음)"""
        base = [0.8, 0.8, 0.8, 0.8, 0.8]
        target = [0.8, 0.8, 0.8, 0.8, 0.8]
        p_value = calculate_p_value(base, target)
        assert p_value >= 0.05

    def test_very_different_scores_low_p_value(self):
        """매우 다른 점수 = 낮은 p-value (유의미함)"""
        base = [0.9, 0.88, 0.92, 0.87, 0.91]
        target = [0.5, 0.48, 0.52, 0.47, 0.51]
        p_value = calculate_p_value(base, target)
        assert p_value < 0.05

    def test_empty_scores_returns_1(self):
        """빈 배열 = p-value 1.0"""
        assert calculate_p_value([], []) == 1.0

    def test_single_sample_returns_1(self):
        """샘플 1개 = t-test 불가, p-value 1.0"""
        assert calculate_p_value([0.8], [0.5]) == 1.0

    def test_mismatched_length_returns_1(self):
        """길이 불일치 = p-value 1.0"""
        assert calculate_p_value([0.8, 0.9], [0.5]) == 1.0


@pytest.mark.asyncio
async def test_compare_runs_not_found(
    client: AsyncClient,
    guest_cookies: dict[str, str],
) -> None:
    """존재하지 않는 Run 비교 시 404."""
    response = await client.get(
        "/runs/99999/compare/99998",
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_compare_runs_returns_row_comparisons(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    test_session_factory,
    prompt_factory,
    dataset_factory,
    profile_factory,
) -> None:
    """두 Run 비교 시 row별 데이터와 p_value 반환."""
    from unittest.mock import AsyncMock, patch

    from src.runs.models import Run, RunStatus
    from src.runs.service import execute_run

    guest_id = guest_cookies["guest_id"]
    prompt, version1 = await prompt_factory(guest_id)
    dataset = await dataset_factory(
        guest_id,
        rows=[
            {"input": {"claim": "주장1"}, "expected": "TRUE"},
            {"input": {"claim": "주장2"}, "expected": "FALSE"},
        ],
    )
    profile = await profile_factory(guest_id, semantic_threshold=0.7)

    async with test_session_factory() as session:
        run1 = Run(
            prompt_version_id=version1.id,
            dataset_id=dataset.id,
            profile_id=profile.id,
            profile_snapshot={
                "semantic_threshold": profile.semantic_threshold,
                "global_constraints": profile.global_constraints or [],
            },
            status=RunStatus.RUNNING,
        )
        session.add(run1)
        await session.commit()
        await session.refresh(run1)
        run1_id = run1.id

    mock_llm1 = AsyncMock()
    mock_llm1.generate = AsyncMock(side_effect=["TRUE", "FALSE"])

    with (
        patch("src.runs.service.async_session", test_session_factory),
        patch("src.runs.service.get_llm_client", return_value=mock_llm1),
    ):
        await execute_run(run1_id)

    version2_resp = await client.post(
        f"/prompts/{prompt.id}/versions",
        json={
            "systemInstruction": "수정된 시스템 지시문",
            "userTemplate": "{{claim}}",
        },
    )
    version2_id = version2_resp.json()["id"]

    async with test_session_factory() as session:
        run2 = Run(
            prompt_version_id=version2_id,
            dataset_id=dataset.id,
            profile_id=profile.id,
            profile_snapshot={
                "semantic_threshold": profile.semantic_threshold,
                "global_constraints": profile.global_constraints or [],
            },
            status=RunStatus.RUNNING,
        )
        session.add(run2)
        await session.commit()
        await session.refresh(run2)
        run2_id = run2.id

    mock_llm2 = AsyncMock()
    mock_llm2.generate = AsyncMock(side_effect=["FALSE", "FALSE"])

    with (
        patch("src.runs.service.async_session", test_session_factory),
        patch("src.runs.service.get_llm_client", return_value=mock_llm2),
    ):
        await execute_run(run2_id)

    response = await client.get(
        f"/runs/{run2_id}/compare/{run1_id}",
    )

    assert response.status_code == 200
    data = response.json()

    assert "pValue" in data
    assert "rowComparisons" in data
    assert len(data["rowComparisons"]) == 2

    row1 = data["rowComparisons"][0]
    assert "rowIndex" in row1
    assert "baseStatus" in row1
    assert "targetStatus" in row1
    assert "baseSemanticScore" in row1
    assert "targetSemanticScore" in row1


@pytest.mark.asyncio
async def test_compare_runs_different_datasets(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    test_session_factory,
    prompt_factory,
    dataset_factory,
    profile_factory,
) -> None:
    """서로 다른 데이터셋 비교 시 빈 공통 rows."""
    from unittest.mock import AsyncMock, patch

    from src.runs.models import Run, RunStatus
    from src.runs.service import execute_run

    guest_id = guest_cookies["guest_id"]
    _, version = await prompt_factory(guest_id)
    profile = await profile_factory(guest_id, semantic_threshold=0.7)

    dataset_a = await dataset_factory(
        guest_id,
        name="데이터셋A",
        rows=[{"input": {"claim": "주장A"}, "expected": "TRUE"}],
    )
    dataset_b = await dataset_factory(
        guest_id,
        name="데이터셋B",
        rows=[{"input": {"claim": "주장B"}, "expected": "FALSE"}],
    )

    async with test_session_factory() as session:
        run_a = Run(
            prompt_version_id=version.id,
            dataset_id=dataset_a.id,
            profile_id=profile.id,
            profile_snapshot={
                "semantic_threshold": 0.7,
                "global_constraints": [],
            },
            status=RunStatus.RUNNING,
        )
        run_b = Run(
            prompt_version_id=version.id,
            dataset_id=dataset_b.id,
            profile_id=profile.id,
            profile_snapshot={
                "semantic_threshold": 0.7,
                "global_constraints": [],
            },
            status=RunStatus.RUNNING,
        )
        session.add(run_a)
        session.add(run_b)
        await session.commit()
        await session.refresh(run_a)
        await session.refresh(run_b)
        run_a_id = run_a.id
        run_b_id = run_b.id

    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(side_effect=["TRUE", "FALSE"])

    with (
        patch("src.runs.service.async_session", test_session_factory),
        patch("src.runs.service.get_llm_client", return_value=mock_llm),
    ):
        await execute_run(run_a_id)
        await execute_run(run_b_id)

    response = await client.get(f"/runs/{run_b_id}/compare/{run_a_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["rowComparisons"] == []
    assert data["pValue"] == 1.0
