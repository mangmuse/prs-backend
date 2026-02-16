"""runs router 테스트 - HTTP 계층만 검증."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from src.runs.models import Run, RunStatus


@pytest.mark.asyncio
async def test_create_run_returns_201_and_running_status(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    prompt_factory,
    dataset_factory,
    profile_factory,
) -> None:
    """Run 생성 시 201과 running 상태 반환."""
    guest_id = guest_cookies["guest_id"]
    _, version = await prompt_factory(guest_id)
    dataset = await dataset_factory(guest_id, rows=[{"input": {"test": "data"}}])
    profile = await profile_factory(guest_id)

    with patch("src.runs.router.process_run_task"):
        response = await client.post(
            "/runs",
            json={
                "promptVersionId": version.id,
                "datasetId": dataset.id,
                "profileId": profile.id,
                "apiKey": "test-key",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "running"
    assert "id" in data
    assert "createdAt" in data


@pytest.mark.asyncio
async def test_create_run_with_invalid_version_returns_404(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    dataset_factory,
    profile_factory,
) -> None:
    """존재하지 않는 버전으로 Run 생성 시 404."""
    guest_id = guest_cookies["guest_id"]
    dataset = await dataset_factory(guest_id)
    profile = await profile_factory(guest_id)

    response = await client.post(
        "/runs",
        json={
            "promptVersionId": 99999,
            "datasetId": dataset.id,
            "profileId": profile.id,
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_run_with_other_user_resource_returns_404(
    client: AsyncClient,
) -> None:
    """다른 사용자의 리소스로 Run 생성 시 404."""
    guest1_resp = await client.post("/auth/guest")
    client.cookies.set("guest_id", guest1_resp.json()["guestId"])

    prompt_resp = await client.post(
        "/prompts",
        json={"name": "Guest1 프롬프트"},
    )
    prompt_id = prompt_resp.json()["id"]

    version_resp = await client.post(
        f"/prompts/{prompt_id}/versions",
        json={
            "systemInstruction": "테스트",
            "userTemplate": "{{input}}",
        },
    )
    version_id = version_resp.json()["id"]

    dataset_resp = await client.post(
        "/datasets",
        json={"name": "Guest1 데이터셋"},
    )
    dataset_id = dataset_resp.json()["id"]

    profile_resp = await client.post(
        "/evaluator-profiles",
        json={"name": "Guest1 프로필"},
    )
    profile_id = profile_resp.json()["id"]

    client.cookies.clear()
    guest2_resp = await client.post("/auth/guest")
    client.cookies.set("guest_id", guest2_resp.json()["guestId"])

    response = await client.post(
        "/runs",
        json={
            "promptVersionId": version_id,
            "datasetId": dataset_id,
            "profileId": profile_id,
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_run_with_empty_dataset_returns_400(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    prompt_factory,
    dataset_factory,
    profile_factory,
) -> None:
    """빈 데이터셋(행이 0개)으로 Run 생성 시 400."""
    guest_id = guest_cookies["guest_id"]
    _, version = await prompt_factory(guest_id)
    dataset = await dataset_factory(guest_id)
    profile = await profile_factory(guest_id)

    response = await client.post(
        "/runs",
        json={
            "promptVersionId": version.id,
            "datasetId": dataset.id,
            "profileId": profile.id,
            "apiKey": "test-key",
        },
    )

    assert response.status_code == 400
    assert "비어 있습니다" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_run_without_api_key_returns_400(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    prompt_factory,
    dataset_factory,
    profile_factory,
) -> None:
    """API Key 없이 Run 생성 시 400."""
    guest_id = guest_cookies["guest_id"]
    _, version = await prompt_factory(guest_id)
    dataset = await dataset_factory(guest_id, rows=[{"input": {"test": "data"}}])
    profile = await profile_factory(guest_id)

    response = await client.post(
        "/runs",
        json={
            "promptVersionId": version.id,
            "datasetId": dataset.id,
            "profileId": profile.id,
        },
    )

    assert response.status_code == 400
    assert "API Key" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_runs_returns_empty_initially(
    client: AsyncClient,
    guest_cookies: dict[str, str],
) -> None:
    """초기 Run 목록은 비어있음."""
    response = await client.get("/runs")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_run_not_found(
    client: AsyncClient,
    guest_cookies: dict[str, str],
) -> None:
    """존재하지 않는 Run 조회 시 404."""
    response = await client.get("/runs/99999")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_runs_includes_layer_metrics(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    test_session_factory,
    prompt_factory,
    dataset_factory,
    profile_factory,
) -> None:
    """목록 조회 시 3-layer 통과율 필드 포함."""
    from unittest.mock import AsyncMock, patch

    from src.runs.models import Run, RunStatus
    from src.runs.service import execute_run

    guest_id = guest_cookies["guest_id"]
    _, version = await prompt_factory(guest_id)
    dataset = await dataset_factory(
        guest_id,
        rows=[
            {"input": {"claim": "참인 주장"}, "expected": "TRUE"},
            {"input": {"claim": "거짓인 주장"}, "expected": "FALSE"},
        ],
    )
    profile = await profile_factory(guest_id, semantic_threshold=0.7)

    async with test_session_factory() as session:
        run = Run(
            prompt_version_id=version.id,
            dataset_id=dataset.id,
            profile_id=profile.id,
            profile_snapshot={
                "semantic_threshold": profile.semantic_threshold,
                "global_constraints": profile.global_constraints or [],
            },
            status=RunStatus.RUNNING,
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        run_id = run.id
        assert run_id is not None

    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(side_effect=["TRUE", "FALSE"])

    with (
        patch("src.runs.service.async_session", test_session_factory),
        patch("src.runs.service.get_llm_client", return_value=mock_llm),
        patch(
            "src.runs.evaluator.semantic_layer.get_embedding",
            return_value=[1.0, 0.0, 0.0],
        ),
    ):
        await execute_run(run_id)

    response = await client.get("/runs")

    assert response.status_code == 200
    runs = response.json()
    assert len(runs) == 1

    run_data = runs[0]
    assert "formatPassRate" in run_data
    assert "semanticPassRate" in run_data
    assert "constraintPassRate" in run_data
    assert run_data["formatPassRate"] == 1.0
    assert run_data["semanticPassRate"] == 1.0
    assert run_data["constraintPassRate"] == 1.0


@pytest.mark.asyncio
async def test_get_run_detail_includes_layer_metrics(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    test_session_factory,
    prompt_factory,
    dataset_factory,
    profile_factory,
) -> None:
    """상세 조회 시 metrics에 3-layer 통과율 포함."""
    from unittest.mock import AsyncMock, patch

    from src.runs.models import Run, RunStatus
    from src.runs.service import execute_run

    guest_id = guest_cookies["guest_id"]
    _, version = await prompt_factory(guest_id)
    dataset = await dataset_factory(
        guest_id,
        rows=[
            {"input": {"claim": "참인 주장"}, "expected": "TRUE"},
        ],
    )
    profile = await profile_factory(guest_id, semantic_threshold=0.7)

    async with test_session_factory() as session:
        run = Run(
            prompt_version_id=version.id,
            dataset_id=dataset.id,
            profile_id=profile.id,
            profile_snapshot={
                "semantic_threshold": profile.semantic_threshold,
                "global_constraints": profile.global_constraints or [],
            },
            status=RunStatus.RUNNING,
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        run_id = run.id
        assert run_id is not None

    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(return_value="TRUE")

    with (
        patch("src.runs.service.async_session", test_session_factory),
        patch("src.runs.service.get_llm_client", return_value=mock_llm),
        patch(
            "src.runs.evaluator.semantic_layer.get_embedding",
            return_value=[1.0, 0.0, 0.0],
        ),
    ):
        await execute_run(run_id)

    response = await client.get(f"/runs/{run_id}")

    assert response.status_code == 200
    data = response.json()
    metrics = data["metrics"]

    assert "formatPassRate" in metrics
    assert "semanticPassRate" in metrics
    assert "constraintPassRate" in metrics
    assert metrics["formatPassRate"] == 1.0
    assert metrics["semanticPassRate"] == 1.0
    assert metrics["constraintPassRate"] == 1.0


@pytest.mark.asyncio
async def test_update_profile_snapshot_returns_204(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    test_session_factory,
    prompt_factory,
    dataset_factory,
    profile_factory,
) -> None:
    """profile_snapshot 업데이트 시 204 반환."""
    guest_id = guest_cookies["guest_id"]
    _, version = await prompt_factory(guest_id)
    dataset = await dataset_factory(guest_id)
    profile = await profile_factory(guest_id, semantic_threshold=0.7)

    async with test_session_factory() as session:
        run = Run(
            prompt_version_id=version.id,
            dataset_id=dataset.id,
            profile_id=profile.id,
            profile_snapshot={
                "semantic_threshold": 0.7,
                "global_constraints": [],
            },
            status=RunStatus.COMPLETED,
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        run_id = run.id

    response = await client.patch(
        f"/runs/{run_id}/profile-snapshot",
        json={
            "semanticThreshold": 0.85,
            "globalConstraints": [
                {"type": "contains", "target": "verdict", "value": "TRUE"},
            ],
        },
    )

    assert response.status_code == 204

    detail_response = await client.get(f"/runs/{run_id}")
    detail = detail_response.json()
    assert detail["profile"]["semanticThreshold"] == 0.85
    assert len(detail["profile"]["globalConstraints"]) == 1
    assert detail["profile"]["globalConstraints"][0]["type"] == "contains"


@pytest.mark.asyncio
async def test_update_profile_snapshot_not_found(
    client: AsyncClient,
    guest_cookies: dict[str, str],
) -> None:
    """존재하지 않는 Run의 profile_snapshot 업데이트 시 404."""
    response = await client.patch(
        "/runs/99999/profile-snapshot",
        json={
            "semanticThreshold": 0.85,
            "globalConstraints": [],
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_profile_snapshot_other_user_returns_404(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    test_session_factory,
    prompt_factory,
    dataset_factory,
    profile_factory,
) -> None:
    """다른 사용자의 Run profile_snapshot 업데이트 시 404."""
    guest_id = guest_cookies["guest_id"]
    _, version = await prompt_factory(guest_id)
    dataset = await dataset_factory(guest_id)
    profile = await profile_factory(guest_id)

    async with test_session_factory() as session:
        run = Run(
            prompt_version_id=version.id,
            dataset_id=dataset.id,
            profile_id=profile.id,
            profile_snapshot={
                "semantic_threshold": 0.7,
                "global_constraints": [],
            },
            status=RunStatus.COMPLETED,
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        run_id = run.id

    client.cookies.clear()
    guest2_resp = await client.post("/auth/guest")
    client.cookies.set("guest_id", guest2_resp.json()["guestId"])

    response = await client.patch(
        f"/runs/{run_id}/profile-snapshot",
        json={
            "semanticThreshold": 0.85,
            "globalConstraints": [],
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_re_evaluate_returns_200_with_results(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    test_session_factory,
    prompt_factory,
    dataset_factory,
    profile_factory,
) -> None:
    """재평가 요청 시 200과 결과 반환."""
    from unittest.mock import AsyncMock, patch

    from src.runs.service import execute_run

    guest_id = guest_cookies["guest_id"]
    _, version = await prompt_factory(guest_id)
    dataset = await dataset_factory(
        guest_id,
        rows=[
            {"input": {"claim": "테스트"}, "expected": "TRUE"},
            {"input": {"claim": "테스트2"}, "expected": "FALSE"},
        ],
    )
    profile = await profile_factory(guest_id, semantic_threshold=0.5)

    async with test_session_factory() as session:
        run = Run(
            prompt_version_id=version.id,
            dataset_id=dataset.id,
            profile_id=profile.id,
            profile_snapshot={
                "semantic_threshold": 0.5,
                "global_constraints": [],
            },
            status=RunStatus.RUNNING,
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        run_id = run.id
        assert run_id is not None

    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(side_effect=["TRUE", "FALSE"])

    with (
        patch("src.runs.service.async_session", test_session_factory),
        patch("src.runs.service.get_llm_client", return_value=mock_llm),
    ):
        await execute_run(run_id)

    response = await client.post(
        f"/runs/{run_id}/re-evaluate",
        json={
            "semanticThreshold": 0.99,
            "globalConstraints": [],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "passRate" in data
    assert len(data["results"]) == 2
    for result in data["results"]:
        assert "id" in result
        assert "status" in result


@pytest.mark.asyncio
async def test_re_evaluate_not_found(
    client: AsyncClient,
    guest_cookies: dict[str, str],
) -> None:
    """존재하지 않는 Run 재평가 시 404."""
    response = await client.post(
        "/runs/99999/re-evaluate",
        json={
            "semanticThreshold": 0.85,
            "globalConstraints": [],
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_re_evaluate_other_user_returns_404(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    test_session_factory,
    prompt_factory,
    dataset_factory,
    profile_factory,
) -> None:
    """다른 사용자의 Run 재평가 시 404."""
    guest_id = guest_cookies["guest_id"]
    _, version = await prompt_factory(guest_id)
    dataset = await dataset_factory(guest_id)
    profile = await profile_factory(guest_id)

    async with test_session_factory() as session:
        run = Run(
            prompt_version_id=version.id,
            dataset_id=dataset.id,
            profile_id=profile.id,
            profile_snapshot={
                "semantic_threshold": 0.7,
                "global_constraints": [],
            },
            status=RunStatus.COMPLETED,
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        run_id = run.id

    client.cookies.clear()
    guest2_resp = await client.post("/auth/guest")
    client.cookies.set("guest_id", guest2_resp.json()["guestId"])

    response = await client.post(
        f"/runs/{run_id}/re-evaluate",
        json={
            "semanticThreshold": 0.85,
            "globalConstraints": [],
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_re_evaluate_run_empty_results(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    test_session_factory,
    prompt_factory,
    dataset_factory,
    profile_factory,
) -> None:
    """결과 없는 run 재평가 시 빈 결과와 passRate 0.0."""
    guest_id = guest_cookies["guest_id"]
    _, version = await prompt_factory(guest_id)
    dataset = await dataset_factory(guest_id)
    profile = await profile_factory(guest_id)

    async with test_session_factory() as session:
        run = Run(
            prompt_version_id=version.id,
            dataset_id=dataset.id,
            profile_id=profile.id,
            profile_snapshot={
                "semantic_threshold": 0.8,
                "global_constraints": [],
            },
            status=RunStatus.COMPLETED,
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        run_id = run.id

    response = await client.post(
        f"/runs/{run_id}/re-evaluate",
        json={
            "semanticThreshold": 0.85,
            "globalConstraints": [],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["results"] == []
    assert data["passRate"] == 0.0
