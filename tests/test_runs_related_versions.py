"""Run related-versions 엔드포인트 테스트."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_related_versions_success(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    guest_factory,
    prompt_factory,
    dataset_factory,
    profile_factory,
    run_factory,
) -> None:
    """GET /runs/{id}/related-versions — 성공 응답."""
    guest_id = guest_cookies["guest_id"]

    prompt, version = await prompt_factory(guest_id)
    dataset = await dataset_factory(
        guest_id, rows=[{"input": {"claim": "테스트"}, "expected": "TRUE"}]
    )
    profile = await profile_factory(guest_id)

    assert version.id is not None
    assert dataset.id is not None
    assert profile.id is not None

    run = await run_factory(
        prompt_version_id=version.id,
        dataset_id=dataset.id,
        profile_id=profile.id,
        guest_id=guest_id,
    )

    response = await client.get(f"/runs/{run.id}/related-versions")

    assert response.status_code == 200
    data = response.json()
    assert "executedRuns" in data
    assert "unexecutedVersions" in data


@pytest.mark.asyncio
async def test_get_related_versions_not_found(
    client: AsyncClient,
    guest_cookies: dict[str, str],
) -> None:
    """GET /runs/{id}/related-versions — 존재하지 않는 run 요청 시 404."""
    response = await client.get("/runs/99999/related-versions")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_related_versions_other_owner_returns_404(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    guest_factory,
    prompt_factory,
    dataset_factory,
    profile_factory,
    run_factory,
) -> None:
    """GET /runs/{id}/related-versions — 다른 사용자 run 요청 시 404."""
    other_guest = await guest_factory()

    prompt, version = await prompt_factory(other_guest.id)
    dataset = await dataset_factory(other_guest.id)
    profile = await profile_factory(other_guest.id)

    assert version.id is not None
    assert dataset.id is not None
    assert profile.id is not None

    run = await run_factory(
        prompt_version_id=version.id,
        dataset_id=dataset.id,
        profile_id=profile.id,
        guest_id=other_guest.id,
    )

    response = await client.get(f"/runs/{run.id}/related-versions")

    assert response.status_code == 404
