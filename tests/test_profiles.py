import pytest
from httpx import AsyncClient


async def get_guest_cookie(client: AsyncClient) -> dict[str, str]:
    """게스트 세션 생성 후 쿠키 반환."""
    response = await client.post("/auth/guest")
    return {"guest_id": response.json()["guest_id"]}


@pytest.mark.asyncio
async def test_create_profile(client: AsyncClient) -> None:
    """POST /evaluator-profiles - 프로필 생성 성공."""
    cookies = await get_guest_cookie(client)
    response = await client.post(
        "/evaluator-profiles",
        json={
            "name": "엄격한 평가",
            "description": "높은 threshold",
            "semantic_threshold": 0.9,
        },
        cookies=cookies,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "엄격한 평가"
    assert data["semantic_threshold"] == 0.9


@pytest.mark.asyncio
async def test_create_profile_with_constraints(client: AsyncClient) -> None:
    """POST /evaluator-profiles - 제약조건 포함 프로필 생성."""
    cookies = await get_guest_cookie(client)
    response = await client.post(
        "/evaluator-profiles",
        json={
            "name": "제약조건 테스트",
            "semantic_threshold": 0.8,
            "global_constraints": [
                {"type": "contains", "value": "verdict"},
                {"type": "max_length", "value": 500},
            ],
        },
        cookies=cookies,
    )

    assert response.status_code == 201
    data = response.json()
    assert len(data["global_constraints"]) == 2


@pytest.mark.asyncio
async def test_list_profiles(client: AsyncClient) -> None:
    """GET /evaluator-profiles - 목록 조회 (constraint_count 포함)."""
    cookies = await get_guest_cookie(client)
    await client.post(
        "/evaluator-profiles",
        json={
            "name": "프로필1",
            "global_constraints": [{"type": "contains", "value": "test"}],
        },
        cookies=cookies,
    )
    await client.post(
        "/evaluator-profiles",
        json={"name": "프로필2"},
        cookies=cookies,
    )

    response = await client.get("/evaluator-profiles", cookies=cookies)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    profile_with_constraint = next(p for p in data if p["name"] == "프로필1")
    assert profile_with_constraint["constraint_count"] == 1

    profile_without_constraint = next(p for p in data if p["name"] == "프로필2")
    assert profile_without_constraint["constraint_count"] == 0


@pytest.mark.asyncio
async def test_get_profile_detail(client: AsyncClient) -> None:
    """GET /evaluator-profiles/{id} - 상세 조회."""
    cookies = await get_guest_cookie(client)
    create_response = await client.post(
        "/evaluator-profiles",
        json={"name": "상세조회용", "semantic_threshold": 0.75},
        cookies=cookies,
    )
    profile_id = create_response.json()["id"]

    response = await client.get(f"/evaluator-profiles/{profile_id}", cookies=cookies)

    assert response.status_code == 200
    assert response.json()["name"] == "상세조회용"


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient) -> None:
    """PATCH /evaluator-profiles/{id} - 수정."""
    cookies = await get_guest_cookie(client)
    create_response = await client.post(
        "/evaluator-profiles",
        json={"name": "수정전"},
        cookies=cookies,
    )
    profile_id = create_response.json()["id"]

    response = await client.patch(
        f"/evaluator-profiles/{profile_id}",
        json={"name": "수정후", "semantic_threshold": 0.8},
        cookies=cookies,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "수정후"
    assert response.json()["semantic_threshold"] == 0.8


@pytest.mark.asyncio
async def test_delete_profile(client: AsyncClient) -> None:
    """DELETE /evaluator-profiles/{id} - 삭제."""
    cookies = await get_guest_cookie(client)
    create_response = await client.post(
        "/evaluator-profiles",
        json={"name": "삭제용"},
        cookies=cookies,
    )
    profile_id = create_response.json()["id"]

    response = await client.delete(f"/evaluator-profiles/{profile_id}", cookies=cookies)
    assert response.status_code == 204

    get_response = await client.get(f"/evaluator-profiles/{profile_id}", cookies=cookies)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_profile_ownership(client: AsyncClient) -> None:
    """다른 사용자의 프로필 접근 불가."""
    guest1_resp = await client.post("/auth/guest")
    cookies1 = {"guest_id": guest1_resp.json()["guest_id"]}

    create_response = await client.post(
        "/evaluator-profiles",
        json={"name": "Guest1 프로필"},
        cookies=cookies1,
    )
    profile_id = create_response.json()["id"]

    client.cookies.clear()
    guest2_resp = await client.post("/auth/guest")
    cookies2 = {"guest_id": guest2_resp.json()["guest_id"]}

    response = await client.get(f"/evaluator-profiles/{profile_id}", cookies=cookies2)
    assert response.status_code == 404
