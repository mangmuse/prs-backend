"""Run 결과 커서 기반 페이지네이션 테스트."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_pagination_returns_limited_results_with_cursor(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    prompt_factory,
    dataset_factory,
    profile_factory,
    run_factory,
) -> None:
    """cursor와 limit를 전달하면 해당 범위의 결과만 반환한다."""
    guest_id = guest_cookies["guest_id"]

    prompt, version = await prompt_factory(guest_id)
    dataset = await dataset_factory(
        guest_id,
        rows=[{"input": {"text": f"row_{i}"}, "expected": "ok"} for i in range(5)],
    )
    profile = await profile_factory(guest_id)

    assert version.id is not None
    assert dataset.id is not None
    assert profile.id is not None

    detail = await client.get(f"/datasets/{dataset.id}")
    row_ids = [r["id"] for r in detail.json()["rows"]]

    run = await run_factory(
        prompt_version_id=version.id,
        dataset_id=dataset.id,
        profile_id=profile.id,
        guest_id=guest_id,
        results=[
            {
                "dataset_row_id": row_id,
                "input_snapshot": {"text": f"row_{i}"},
                "expected_snapshot": "ok",
                "assembled_prompt": {"system_instruction": "s", "user_message": "u"},
                "raw_output": "ok",
                "status": "pass",
            }
            for i, row_id in enumerate(row_ids)
        ],
    )

    resp = await client.get(f"/runs/{run.id}?limit=2")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["results"]) == 2
    next_cursor = data["nextCursor"]
    assert next_cursor is not None

    resp2 = await client.get(f"/runs/{run.id}?cursor={next_cursor}&limit=2")
    assert resp2.status_code == 200
    data2 = resp2.json()

    assert len(data2["results"]) == 2

    first_ids = {r["id"] for r in data["results"]}
    second_ids = {r["id"] for r in data2["results"]}
    assert first_ids.isdisjoint(second_ids)


@pytest.mark.asyncio
async def test_no_cursor_or_limit_returns_all_results(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    prompt_factory,
    dataset_factory,
    profile_factory,
    run_factory,
) -> None:
    """cursor/limit 없이 호출하면 전체 결과를 반환한다."""
    guest_id = guest_cookies["guest_id"]

    prompt, version = await prompt_factory(guest_id)
    dataset = await dataset_factory(
        guest_id,
        rows=[{"input": {"text": f"row_{i}"}, "expected": "ok"} for i in range(5)],
    )
    profile = await profile_factory(guest_id)

    assert version.id is not None
    assert dataset.id is not None
    assert profile.id is not None

    detail = await client.get(f"/datasets/{dataset.id}")
    row_ids = [r["id"] for r in detail.json()["rows"]]

    run = await run_factory(
        prompt_version_id=version.id,
        dataset_id=dataset.id,
        profile_id=profile.id,
        guest_id=guest_id,
        results=[
            {
                "dataset_row_id": row_id,
                "input_snapshot": {"text": f"row_{i}"},
                "expected_snapshot": "ok",
                "assembled_prompt": {"system_instruction": "s", "user_message": "u"},
                "raw_output": "ok",
                "status": "pass",
            }
            for i, row_id in enumerate(row_ids)
        ],
    )

    resp = await client.get(f"/runs/{run.id}")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["results"]) == 5
    assert data["nextCursor"] is None


@pytest.mark.asyncio
async def test_response_includes_status_counts(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    prompt_factory,
    dataset_factory,
    profile_factory,
    run_factory,
) -> None:
    """응답에 statusCounts가 전체 기준으로 포함된다."""
    guest_id = guest_cookies["guest_id"]

    prompt, version = await prompt_factory(guest_id)
    dataset = await dataset_factory(
        guest_id,
        rows=[{"input": {"text": f"row_{i}"}, "expected": "ok"} for i in range(4)],
    )
    profile = await profile_factory(guest_id)

    assert version.id is not None
    assert dataset.id is not None
    assert profile.id is not None

    detail = await client.get(f"/datasets/{dataset.id}")
    row_ids = [r["id"] for r in detail.json()["rows"]]

    statuses = ["pass", "pass", "format", "semantic"]
    run = await run_factory(
        prompt_version_id=version.id,
        dataset_id=dataset.id,
        profile_id=profile.id,
        guest_id=guest_id,
        results=[
            {
                "dataset_row_id": row_ids[i],
                "input_snapshot": {"text": f"row_{i}"},
                "expected_snapshot": "ok",
                "assembled_prompt": {"system_instruction": "s", "user_message": "u"},
                "raw_output": "ok",
                "status": statuses[i],
            }
            for i in range(4)
        ],
    )

    resp = await client.get(f"/runs/{run.id}")
    assert resp.status_code == 200
    data = resp.json()

    status_counts = data["statusCounts"]
    assert status_counts["pass"] == 2
    assert status_counts["format"] == 1
    assert status_counts["semantic"] == 1
    assert status_counts["constraint"] == 0


@pytest.mark.asyncio
async def test_status_filter_returns_only_matching_results(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    prompt_factory,
    dataset_factory,
    profile_factory,
    run_factory,
) -> None:
    """status 필터를 전달하면 해당 status의 결과만 페이지네이션한다."""
    guest_id = guest_cookies["guest_id"]

    prompt, version = await prompt_factory(guest_id)
    dataset = await dataset_factory(
        guest_id,
        rows=[{"input": {"text": f"row_{i}"}, "expected": "ok"} for i in range(5)],
    )
    profile = await profile_factory(guest_id)

    assert version.id is not None
    assert dataset.id is not None
    assert profile.id is not None

    detail = await client.get(f"/datasets/{dataset.id}")
    row_ids = [r["id"] for r in detail.json()["rows"]]

    statuses = ["pass", "format", "pass", "semantic", "pass"]
    run = await run_factory(
        prompt_version_id=version.id,
        dataset_id=dataset.id,
        profile_id=profile.id,
        guest_id=guest_id,
        results=[
            {
                "dataset_row_id": row_ids[i],
                "input_snapshot": {"text": f"row_{i}"},
                "expected_snapshot": "ok",
                "assembled_prompt": {"system_instruction": "s", "user_message": "u"},
                "raw_output": "ok",
                "status": statuses[i],
            }
            for i in range(5)
        ],
    )

    resp = await client.get(f"/runs/{run.id}?status=pass")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["results"]) == 3
    assert all(r["status"] == "pass" for r in data["results"])


@pytest.mark.asyncio
async def test_status_counts_always_reflect_all_results(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    prompt_factory,
    dataset_factory,
    profile_factory,
    run_factory,
) -> None:
    """status 필터와 무관하게 statusCounts는 전체 기준이다."""
    guest_id = guest_cookies["guest_id"]

    prompt, version = await prompt_factory(guest_id)
    dataset = await dataset_factory(
        guest_id,
        rows=[{"input": {"text": f"row_{i}"}, "expected": "ok"} for i in range(4)],
    )
    profile = await profile_factory(guest_id)

    assert version.id is not None
    assert dataset.id is not None
    assert profile.id is not None

    detail = await client.get(f"/datasets/{dataset.id}")
    row_ids = [r["id"] for r in detail.json()["rows"]]

    statuses = ["pass", "pass", "format", "semantic"]
    run = await run_factory(
        prompt_version_id=version.id,
        dataset_id=dataset.id,
        profile_id=profile.id,
        guest_id=guest_id,
        results=[
            {
                "dataset_row_id": row_ids[i],
                "input_snapshot": {"text": f"row_{i}"},
                "expected_snapshot": "ok",
                "assembled_prompt": {"system_instruction": "s", "user_message": "u"},
                "raw_output": "ok",
                "status": statuses[i],
            }
            for i in range(4)
        ],
    )

    resp = await client.get(f"/runs/{run.id}?status=pass")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["results"]) == 2

    status_counts = data["statusCounts"]
    assert status_counts["pass"] == 2
    assert status_counts["format"] == 1
    assert status_counts["semantic"] == 1
    assert status_counts["constraint"] == 0


@pytest.mark.asyncio
async def test_next_cursor_is_null_on_last_page(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    prompt_factory,
    dataset_factory,
    profile_factory,
    run_factory,
) -> None:
    """nextCursor가 null이면 마지막 페이지이다."""
    guest_id = guest_cookies["guest_id"]

    prompt, version = await prompt_factory(guest_id)
    dataset = await dataset_factory(
        guest_id,
        rows=[{"input": {"text": f"row_{i}"}, "expected": "ok"} for i in range(3)],
    )
    profile = await profile_factory(guest_id)

    assert version.id is not None
    assert dataset.id is not None
    assert profile.id is not None

    detail = await client.get(f"/datasets/{dataset.id}")
    row_ids = [r["id"] for r in detail.json()["rows"]]

    run = await run_factory(
        prompt_version_id=version.id,
        dataset_id=dataset.id,
        profile_id=profile.id,
        guest_id=guest_id,
        results=[
            {
                "dataset_row_id": row_ids[i],
                "input_snapshot": {"text": f"row_{i}"},
                "expected_snapshot": "ok",
                "assembled_prompt": {"system_instruction": "s", "user_message": "u"},
                "raw_output": "ok",
                "status": "pass",
            }
            for i in range(3)
        ],
    )

    resp = await client.get(f"/runs/{run.id}?limit=2")
    data = resp.json()
    assert data["nextCursor"] is not None

    resp2 = await client.get(f"/runs/{run.id}?cursor={data['nextCursor']}&limit=2")
    data2 = resp2.json()

    assert len(data2["results"]) == 1
    assert data2["nextCursor"] is None


@pytest.mark.asyncio
async def test_total_count_always_returns_all_results_count(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    prompt_factory,
    dataset_factory,
    profile_factory,
    run_factory,
) -> None:
    """totalCount는 항상 전체 결과 수를 반환한다."""
    guest_id = guest_cookies["guest_id"]

    prompt, version = await prompt_factory(guest_id)
    dataset = await dataset_factory(
        guest_id,
        rows=[{"input": {"text": f"row_{i}"}, "expected": "ok"} for i in range(5)],
    )
    profile = await profile_factory(guest_id)

    assert version.id is not None
    assert dataset.id is not None
    assert profile.id is not None

    detail = await client.get(f"/datasets/{dataset.id}")
    row_ids = [r["id"] for r in detail.json()["rows"]]

    run = await run_factory(
        prompt_version_id=version.id,
        dataset_id=dataset.id,
        profile_id=profile.id,
        guest_id=guest_id,
        results=[
            {
                "dataset_row_id": row_ids[i],
                "input_snapshot": {"text": f"row_{i}"},
                "expected_snapshot": "ok",
                "assembled_prompt": {"system_instruction": "s", "user_message": "u"},
                "raw_output": "ok",
                "status": "pass",
            }
            for i in range(5)
        ],
    )

    resp = await client.get(f"/runs/{run.id}?limit=2")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["results"]) == 2
    assert data["totalCount"] == 5


@pytest.mark.asyncio
async def test_empty_results_returns_empty_array_and_null_cursor(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    prompt_factory,
    dataset_factory,
    profile_factory,
    run_factory,
) -> None:
    """결과가 0건이면 빈 배열과 nextCursor=null을 반환한다."""
    guest_id = guest_cookies["guest_id"]

    prompt, version = await prompt_factory(guest_id)
    dataset = await dataset_factory(
        guest_id,
        rows=[{"input": {"text": "row_0"}, "expected": "ok"}],
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

    resp = await client.get(f"/runs/{run.id}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["results"] == []
    assert data["nextCursor"] is None
    assert data["totalCount"] == 0
