"""DatasetRow CRUD 테스트."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_update_dataset_row_success(
    client: AsyncClient,
    guest_cookies: dict[str, str],
) -> None:
    """PUT /datasets/{id}/rows/{row_id} - 행 수정 성공."""
    create_ds = await client.post("/datasets", json={"name": "수정 테스트"})
    dataset_id = create_ds.json()["id"]

    await client.post(
        f"/datasets/{dataset_id}/rows",
        json=[{"inputData": {"claim": "원본"}, "expectedOutput": "TRUE"}],
    )

    detail = await client.get(f"/datasets/{dataset_id}")
    row_id = detail.json()["rows"][0]["id"]

    response = await client.put(
        f"/datasets/{dataset_id}/rows/{row_id}",
        json={
            "inputData": {"claim": "수정됨"},
            "expectedOutput": "FALSE",
            "tags": ["수정"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["inputData"] == {"claim": "수정됨"}
    assert body["expectedOutput"] == "FALSE"
    assert body["tags"] == ["수정"]


@pytest.mark.asyncio
async def test_update_dataset_row_not_found_returns_404(
    client: AsyncClient,
    guest_cookies: dict[str, str],
) -> None:
    """존재하지 않는 행 수정 시 404."""
    create_ds = await client.post("/datasets", json={"name": "404 테스트"})
    dataset_id = create_ds.json()["id"]

    response = await client.put(
        f"/datasets/{dataset_id}/rows/99999",
        json={
            "inputData": {"claim": "없는 행"},
            "expectedOutput": "TRUE",
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_dataset_row_other_owner_returns_403(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    guest_factory,
    dataset_factory,
) -> None:
    """다른 소유자의 행 수정 시 403."""
    other_guest = await guest_factory()
    dataset = await dataset_factory(
        other_guest.id,
        rows=[{"input": {"claim": "남의 것"}, "expected": "TRUE"}],
    )

    response = await client.put(
        f"/datasets/{dataset.id}/rows/1",
        json={
            "inputData": {"claim": "탈취 시도"},
            "expectedOutput": "TRUE",
        },
    )

    assert response.status_code == 403
