import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_profile(
    client: AsyncClient, guest_cookies: dict[str, str]
) -> None:
    """POST /evaluator-profiles - 프로필 생성 성공."""
    response = await client.post(
        "/evaluator-profiles",
        json={
            "name": "엄격한 평가",
            "description": "높은 threshold",
            "semanticThreshold": 0.9,
        },
        cookies=guest_cookies,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "엄격한 평가"
    assert data["semanticThreshold"] == 0.9


@pytest.mark.asyncio
async def test_create_profile_with_constraints(
    client: AsyncClient, guest_cookies: dict[str, str]
) -> None:
    """POST /evaluator-profiles - 제약조건 포함 프로필 생성."""
    response = await client.post(
        "/evaluator-profiles",
        json={
            "name": "제약조건 테스트",
            "semanticThreshold": 0.8,
            "globalConstraints": [
                {"type": "contains", "value": "verdict"},
                {"type": "max_length", "value": 500},
            ],
        },
        cookies=guest_cookies,
    )

    assert response.status_code == 201
    data = response.json()
    assert len(data["globalConstraints"]) == 2


@pytest.mark.asyncio
async def test_list_profiles(
    client: AsyncClient, guest_cookies: dict[str, str]
) -> None:
    """GET /evaluator-profiles - 목록 조회 (constraintCount 포함)."""
    await client.post(
        "/evaluator-profiles",
        json={
            "name": "프로필1",
            "globalConstraints": [{"type": "contains", "value": "test"}],
        },
        cookies=guest_cookies,
    )
    await client.post(
        "/evaluator-profiles",
        json={"name": "프로필2"},
        cookies=guest_cookies,
    )

    response = await client.get("/evaluator-profiles", cookies=guest_cookies)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    profile_with_constraint = next(p for p in data if p["name"] == "프로필1")
    assert profile_with_constraint["constraintCount"] == 1

    profile_without_constraint = next(p for p in data if p["name"] == "프로필2")
    assert profile_without_constraint["constraintCount"] == 0


@pytest.mark.asyncio
async def test_get_profile_detail(
    client: AsyncClient, guest_cookies: dict[str, str]
) -> None:
    """GET /evaluator-profiles/{id} - 상세 조회."""
    create_response = await client.post(
        "/evaluator-profiles",
        json={"name": "상세조회용", "semanticThreshold": 0.75},
        cookies=guest_cookies,
    )
    profile_id = create_response.json()["id"]

    response = await client.get(f"/evaluator-profiles/{profile_id}", cookies=guest_cookies)

    assert response.status_code == 200
    assert response.json()["name"] == "상세조회용"


@pytest.mark.asyncio
async def test_update_profile(
    client: AsyncClient, guest_cookies: dict[str, str]
) -> None:
    """PATCH /evaluator-profiles/{id} - 수정."""
    create_response = await client.post(
        "/evaluator-profiles",
        json={"name": "수정전"},
        cookies=guest_cookies,
    )
    profile_id = create_response.json()["id"]

    response = await client.patch(
        f"/evaluator-profiles/{profile_id}",
        json={"name": "수정후", "semanticThreshold": 0.8},
        cookies=guest_cookies,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "수정후"
    assert response.json()["semanticThreshold"] == 0.8


@pytest.mark.asyncio
async def test_delete_profile(
    client: AsyncClient, guest_cookies: dict[str, str]
) -> None:
    """DELETE /evaluator-profiles/{id} - 삭제."""
    create_response = await client.post(
        "/evaluator-profiles",
        json={"name": "삭제용"},
        cookies=guest_cookies,
    )
    profile_id = create_response.json()["id"]

    response = await client.delete(f"/evaluator-profiles/{profile_id}", cookies=guest_cookies)
    assert response.status_code == 204

    get_response = await client.get(f"/evaluator-profiles/{profile_id}", cookies=guest_cookies)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_profile_ownership(client: AsyncClient) -> None:
    """다른 사용자의 프로필 접근 불가."""
    guest1_resp = await client.post("/auth/guest")
    cookies1 = {"guest_id": guest1_resp.json()["guestId"]}

    create_response = await client.post(
        "/evaluator-profiles",
        json={"name": "Guest1 프로필"},
        cookies=cookies1,
    )
    profile_id = create_response.json()["id"]

    client.cookies.clear()
    guest2_resp = await client.post("/auth/guest")
    cookies2 = {"guest_id": guest2_resp.json()["guestId"]}

    response = await client.get(f"/evaluator-profiles/{profile_id}", cookies=cookies2)
    assert response.status_code == 404
