from collections.abc import AsyncGenerator
from datetime import timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.auth.service import create_access_token, create_refresh_token


@pytest.fixture(autouse=True)
async def setup_database() -> AsyncGenerator[None, None]:
    """DB 불필요 - 상위 conftest의 autouse fixture 오버라이드"""
    yield


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """DB 의존성 없는 테스트용 HTTP 클라이언트."""
    from httpx import ASGITransport

    from src.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_refresh_with_valid_token(client: AsyncClient) -> None:
    """유효한 refresh token 쿠키 → 200, 새 access_token 반환"""
    refresh_token, _ = create_refresh_token(1, "user")
    client.cookies.set("refresh_token", refresh_token)

    response = await client.post("/auth/refresh")

    assert response.status_code == 200
    data = response.json()
    assert "accessToken" in data
    assert isinstance(data["accessToken"], str)
    assert len(data["accessToken"]) > 0


@pytest.mark.asyncio
async def test_refresh_without_cookie(client: AsyncClient) -> None:
    """쿠키 없음 → 401"""
    response = await client.post("/auth/refresh")

    assert response.status_code == 401
    assert response.json()["detail"] == "리프레시 토큰이 없습니다"


@pytest.mark.asyncio
async def test_refresh_with_invalid_token(client: AsyncClient) -> None:
    """무효한 토큰 → 401"""
    client.cookies.set("refresh_token", "invalid.token.value")

    response = await client.post("/auth/refresh")

    assert response.status_code == 401
    assert response.json()["detail"] == "유효하지 않은 리프레시 토큰입니다"


@pytest.mark.asyncio
async def test_refresh_with_access_token(client: AsyncClient) -> None:
    """access token(refresh가 아닌) → 401"""
    access_token, _ = create_access_token(1, "user")
    client.cookies.set("refresh_token", access_token)

    response = await client.post("/auth/refresh")

    assert response.status_code == 401
    assert response.json()["detail"] == "리프레시 토큰이 아닙니다"


@pytest.mark.asyncio
async def test_refresh_with_expired_token(client: AsyncClient) -> None:
    """만료된 토큰 → 401"""
    refresh_token, _ = create_refresh_token(
        1, "user", expires_delta=timedelta(seconds=-1)
    )
    client.cookies.set("refresh_token", refresh_token)

    response = await client.post("/auth/refresh")

    assert response.status_code == 401
    assert response.json()["detail"] == "유효하지 않은 리프레시 토큰입니다"


@pytest.mark.asyncio
async def test_refresh_with_guest_token(client: AsyncClient) -> None:
    """게스트 refresh token → 200, UUID sub 처리 정상"""
    guest_id = uuid4()
    refresh_token, _ = create_refresh_token(guest_id, "guest")
    client.cookies.set("refresh_token", refresh_token)

    response = await client.post("/auth/refresh")

    assert response.status_code == 200
    data = response.json()
    assert "accessToken" in data
    assert isinstance(data["accessToken"], str)
