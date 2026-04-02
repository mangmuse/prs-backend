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
                {"type": "contains", "target": "verdict", "value": "TRUE"},
                {"type": "max_length", "target": "reasoning", "max": 500},
            ],
        },
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
            "globalConstraints": [
                {"type": "contains", "target": "verdict", "value": "test"}
            ],
        },
    )
    await client.post(
        "/evaluator-profiles",
        json={"name": "프로필2"},
    )

    response = await client.get("/evaluator-profiles")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3

    profile_with_constraint = next(p for p in data if p["name"] == "프로필1")
    assert profile_with_constraint["constraintCount"] == 1

    profile_without_constraint = next(p for p in data if p["name"] == "프로필2")
    assert profile_without_constraint["constraintCount"] == 0

    default_profile = next(p for p in data if p["name"] == "기본 평가 프로필")
    assert default_profile["constraintCount"] == 0


@pytest.mark.asyncio
async def test_get_profile_detail(
    client: AsyncClient, guest_cookies: dict[str, str]
) -> None:
    """GET /evaluator-profiles/{id} - 상세 조회."""
    create_response = await client.post(
        "/evaluator-profiles",
        json={"name": "상세조회용", "semanticThreshold": 0.75},
    )
    profile_id = create_response.json()["id"]

    response = await client.get(f"/evaluator-profiles/{profile_id}")

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
    )
    profile_id = create_response.json()["id"]

    response = await client.patch(
        f"/evaluator-profiles/{profile_id}",
        json={"name": "수정후", "semanticThreshold": 0.8},
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
    )
    profile_id = create_response.json()["id"]

    response = await client.delete(f"/evaluator-profiles/{profile_id}")
    assert response.status_code == 204

    get_response = await client.get(f"/evaluator-profiles/{profile_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_profile_ownership(client: AsyncClient) -> None:
    """다른 사용자의 프로필 접근 불가."""
    guest1_resp = await client.post("/auth/guest")
    client.cookies.set("guest_id", guest1_resp.json()["guestId"])

    create_response = await client.post(
        "/evaluator-profiles",
        json={"name": "Guest1 프로필"},
    )
    profile_id = create_response.json()["id"]

    client.cookies.clear()
    guest2_resp = await client.post("/auth/guest")
    client.cookies.set("guest_id", guest2_resp.json()["guestId"])

    response = await client.get(f"/evaluator-profiles/{profile_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_default_profile_created_on_guest_session(client: AsyncClient) -> None:
    """게스트 세션 생성 시 기본 평가 프로필이 자동 생성되어야 한다."""
    response = await client.post("/auth/guest")
    assert response.status_code == 200

    guest_id = response.json()["guestId"]
    client.cookies.set("guest_id", guest_id)

    profiles_response = await client.get("/evaluator-profiles")
    assert profiles_response.status_code == 200
    profiles = profiles_response.json()

    assert len(profiles) == 1
    assert profiles[0]["name"] == "기본 평가 프로필"
    assert profiles[0]["semanticThreshold"] == 0.75
    assert profiles[0]["constraintCount"] == 0


@pytest.mark.asyncio
async def test_existing_guest_no_duplicate_default_profile(client: AsyncClient) -> None:
    """기존 게스트가 재접속해도 기본 프로필이 중복 생성되지 않아야 한다."""
    response1 = await client.post("/auth/guest")
    guest_id = response1.json()["guestId"]
    client.cookies.set("guest_id", guest_id)

    await client.post("/auth/guest")

    profiles_response = await client.get("/evaluator-profiles")
    profiles = profiles_response.json()
    assert len(profiles) == 1
