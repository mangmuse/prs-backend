"""Run 상태 경량 엔드포인트 테스트."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_returns_status_for_matching_run_id(
    client: AsyncClient,
    create_run_with_results,
) -> None:
    """id와 일치하는 run의 상태를 반환해야 한다."""
    run = await create_run_with_results(["pass", "pass"])

    resp = await client.get(f"/runs/{run.id}/status")
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"] == run.id
    assert data["status"] == "completed"


@pytest.mark.asyncio
async def test_returns_404_for_nonexistent_run_id(
    client: AsyncClient,
    guest_cookies: dict[str, str],
) -> None:
    """존재하지 않는 run id의 경우 404 에러를 반환해야 한다."""
    resp = await client.get("/runs/99999/status")
    assert resp.status_code == 404
