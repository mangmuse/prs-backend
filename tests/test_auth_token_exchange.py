from collections.abc import AsyncGenerator

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.redis import get_redis


@pytest.fixture(autouse=True)
async def setup_database() -> AsyncGenerator[None, None]:
    """DB 불필요."""
    yield


@pytest.fixture
async def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
async def client(fake_redis) -> AsyncGenerator[AsyncClient, None]:
    async def get_test_redis() -> AsyncGenerator[fakeredis.aioredis.FakeRedis, None]:
        yield fake_redis

    app.dependency_overrides[get_redis] = get_test_redis
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_exchange_valid_code(
    client: AsyncClient, fake_redis: fakeredis.aioredis.FakeRedis
) -> None:
    """유효한 임시코드 → 200, access_token 반환."""
    await fake_redis.set("temp_code:test-uuid-123", "jwt-access-token-here", ex=60)

    response = await client.post("/auth/token", json={"code": "test-uuid-123"})

    assert response.status_code == 200
    data = response.json()
    assert data["accessToken"] == "jwt-access-token-here"


@pytest.mark.asyncio
async def test_exchange_invalid_code(client: AsyncClient) -> None:
    """존재하지 않는 코드 → 401."""
    response = await client.post("/auth/token", json={"code": "nonexistent-code"})

    assert response.status_code == 401
    assert response.json()["detail"] == "유효하지 않은 인증 코드입니다"


@pytest.mark.asyncio
async def test_exchange_code_is_one_time(
    client: AsyncClient, fake_redis: fakeredis.aioredis.FakeRedis
) -> None:
    """임시코드는 1회용 - 두 번째 사용 시 401."""
    await fake_redis.set("temp_code:one-time-code", "jwt-token", ex=60)

    first = await client.post("/auth/token", json={"code": "one-time-code"})
    assert first.status_code == 200

    second = await client.post("/auth/token", json={"code": "one-time-code"})
    assert second.status_code == 401


@pytest.mark.asyncio
async def test_exchange_missing_code(client: AsyncClient) -> None:
    """code 필드 누락 → 422."""
    response = await client.post("/auth/token", json={})

    assert response.status_code == 422
