import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_guest_session(client: AsyncClient) -> None:
    """POST /auth/guest - 게스트 세션 생성 성공, Cookie 설정"""
    response = await client.post("/auth/guest")
    assert response.status_code == 200

    data = response.json()
    assert "guest_id" in data
    assert "created_at" in data
    assert "token" not in data
    assert "expires_at" not in data

    assert "guest_id" in response.cookies
    assert response.cookies["guest_id"] == data["guest_id"]


@pytest.mark.asyncio
async def test_existing_cookie_returns_same_guest(client: AsyncClient) -> None:
    """POST /auth/guest - 기존 Cookie가 있으면 같은 세션 반환"""
    response1 = await client.post("/auth/guest")
    guest_id1 = response1.json()["guest_id"]

    response2 = await client.post("/auth/guest", cookies={"guest_id": guest_id1})
    guest_id2 = response2.json()["guest_id"]

    assert guest_id1 == guest_id2
    assert response2.status_code == 200


@pytest.mark.asyncio
async def test_invalid_cookie_creates_new_guest(client: AsyncClient) -> None:
    """POST /auth/guest - 유효하지 않은 Cookie는 새 세션 생성"""
    response = await client.post("/auth/guest", cookies={"guest_id": "invalid-uuid"})
    assert response.status_code == 200

    data = response.json()
    assert "guest_id" in data
    assert "guest_id" in response.cookies


@pytest.mark.asyncio
async def test_nonexistent_guest_cookie_creates_new_guest(client: AsyncClient) -> None:
    """POST /auth/guest - DB에 없는 guest_id Cookie는 새 세션 생성"""
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    response = await client.post("/auth/guest", cookies={"guest_id": fake_uuid})
    assert response.status_code == 200

    data = response.json()
    assert data["guest_id"] != fake_uuid
    assert "guest_id" in response.cookies
