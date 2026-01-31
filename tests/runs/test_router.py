"""runs router 테스트 - HTTP 계층만 검증."""

import pytest
from httpx import AsyncClient


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

    response = await client.post(
        "/runs",
        json={
            "promptVersionId": version.id,
            "datasetId": dataset.id,
            "profileId": profile.id,
        },
        cookies=guest_cookies,
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
        cookies=guest_cookies,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_run_with_other_user_resource_returns_404(
    client: AsyncClient,
) -> None:
    """다른 사용자의 리소스로 Run 생성 시 404."""
    guest1_resp = await client.post("/auth/guest")
    cookies1 = {"guest_id": guest1_resp.json()["guestId"]}

    prompt_resp = await client.post(
        "/prompts",
        json={"name": "Guest1 프롬프트"},
        cookies=cookies1,
    )
    prompt_id = prompt_resp.json()["id"]

    version_resp = await client.post(
        f"/prompts/{prompt_id}/versions",
        json={
            "systemInstruction": "테스트",
            "userTemplate": "{{input}}",
        },
        cookies=cookies1,
    )
    version_id = version_resp.json()["id"]

    dataset_resp = await client.post(
        "/datasets",
        json={"name": "Guest1 데이터셋"},
        cookies=cookies1,
    )
    dataset_id = dataset_resp.json()["id"]

    profile_resp = await client.post(
        "/evaluator-profiles",
        json={"name": "Guest1 프로필"},
        cookies=cookies1,
    )
    profile_id = profile_resp.json()["id"]

    client.cookies.clear()
    guest2_resp = await client.post("/auth/guest")
    cookies2 = {"guest_id": guest2_resp.json()["guestId"]}

    response = await client.post(
        "/runs",
        json={
            "promptVersionId": version_id,
            "datasetId": dataset_id,
            "profileId": profile_id,
        },
        cookies=cookies2,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_runs_returns_empty_initially(
    client: AsyncClient,
    guest_cookies: dict[str, str],
) -> None:
    """초기 Run 목록은 비어있음."""
    response = await client.get("/runs", cookies=guest_cookies)

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_run_not_found(
    client: AsyncClient,
    guest_cookies: dict[str, str],
) -> None:
    """존재하지 않는 Run 조회 시 404."""
    response = await client.get("/runs/99999", cookies=guest_cookies)

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
    from src.runs.service import process_run

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
            status=RunStatus.RUNNING,
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        run_id = run.id

    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(side_effect=["TRUE", "FALSE"])

    with (
        patch("src.runs.service.async_session", test_session_factory),
        patch("src.runs.service.get_llm_client", return_value=mock_llm),
    ):
        await process_run(run_id)

    response = await client.get("/runs", cookies=guest_cookies)

    assert response.status_code == 200
    runs = response.json()
    assert len(runs) == 1

    run_data = runs[0]
    assert "formatPassRate" in run_data
    assert "semanticPassRate" in run_data
    assert "logicPassRate" in run_data
    assert run_data["formatPassRate"] == 1.0
    assert run_data["semanticPassRate"] == 1.0
    assert run_data["logicPassRate"] == 1.0


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
    from src.runs.service import process_run

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

    response = await client.get(f"/runs/{run_id}", cookies=guest_cookies)

    assert response.status_code == 200
    data = response.json()
    metrics = data["metrics"]

    assert "formatPassRate" in metrics
    assert "semanticPassRate" in metrics
    assert "logicPassRate" in metrics
    assert metrics["formatPassRate"] == 1.0
    assert metrics["semanticPassRate"] == 1.0
    assert metrics["logicPassRate"] == 1.0
