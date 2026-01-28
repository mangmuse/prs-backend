import pytest
from httpx import AsyncClient

from src.auth import service


@pytest.mark.asyncio
async def test_create_guest_session(client: AsyncClient) -> None:
    """POST /auth/guest - 게스트 세션 생성 성공"""
    response = await client.post("/auth/guest")
    assert response.status_code == 201

    data = response.json()
    assert "guest_id" in data
    assert "token" in data
    assert "expires_at" in data

    token_data = service.decode_token(data["token"])
    assert token_data is not None
    assert token_data.type == "guest"
    assert token_data.sub == data["guest_id"]


@pytest.mark.asyncio
async def test_create_guest_session_returns_valid_jwt(client: AsyncClient) -> None:
    """POST /auth/guest - 반환된 토큰이 유효한 JWT"""
    response = await client.post("/auth/guest")
    data = response.json()

    token = data["token"]
    parts = token.split(".")
    assert len(parts) == 3


@pytest.mark.asyncio
async def test_guest_session_token_expiration(client: AsyncClient) -> None:
    """POST /auth/guest - 토큰 만료일이 30일 후"""
    from datetime import UTC, datetime, timedelta

    response = await client.post("/auth/guest")
    data = response.json()

    expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
    now = datetime.now(UTC)

    diff = expires_at - now
    assert timedelta(days=29) < diff < timedelta(days=31)
