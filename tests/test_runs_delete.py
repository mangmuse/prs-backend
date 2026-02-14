"""Run 삭제 테스트."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_delete_run_cascades_results(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    guest_factory,
    prompt_factory,
    dataset_factory,
    profile_factory,
    run_factory,
) -> None:
    """DELETE /runs/{id} - Run 삭제 시 결과도 함께 삭제."""
    guest_id = guest_cookies["guest_id"]

    prompt, version = await prompt_factory(guest_id)
    dataset = await dataset_factory(
        guest_id, rows=[{"input": {"claim": "테스트"}, "expected": "TRUE"}]
    )
    profile = await profile_factory(guest_id)

    assert version.id is not None
    assert dataset.id is not None
    assert profile.id is not None

    detail = await client.get(f"/datasets/{dataset.id}")
    row_id = detail.json()["rows"][0]["id"]

    run = await run_factory(
        prompt_version_id=version.id,
        dataset_id=dataset.id,
        profile_id=profile.id,
        guest_id=guest_id,
        results=[
            {
                "dataset_row_id": row_id,
                "input_snapshot": {"claim": "테스트"},
                "expected_snapshot": "TRUE",
                "assembled_prompt": {"system_instruction": "s", "user_message": "u"},
                "raw_output": "TRUE",
                "status": "pass",
            }
        ],
    )

    get_before = await client.get(f"/runs/{run.id}")
    assert get_before.status_code == 200

    response = await client.delete(f"/runs/{run.id}")
    assert response.status_code == 204

    get_after = await client.get(f"/runs/{run.id}")
    assert get_after.status_code == 404


@pytest.mark.asyncio
async def test_delete_run_not_found_returns_404(
    client: AsyncClient,
    guest_cookies: dict[str, str],
) -> None:
    """존재하지 않는 Run 삭제 시 404."""
    response = await client.delete("/runs/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_run_other_owner_returns_403(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    guest_factory,
    prompt_factory,
    dataset_factory,
    profile_factory,
    run_factory,
) -> None:
    """다른 소유자의 Run 삭제 시 403."""
    other_guest = await guest_factory()

    prompt, version = await prompt_factory(other_guest.id)
    dataset = await dataset_factory(
        other_guest.id, rows=[{"input": {"claim": "남의것"}, "expected": "TRUE"}]
    )
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

    response = await client.delete(f"/runs/{run.id}")
    assert response.status_code == 403
