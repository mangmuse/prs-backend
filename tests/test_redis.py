import uuid
from collections.abc import AsyncGenerator

import fakeredis.aioredis
import pytest

from src.redis import retrieve_temp_code, store_temp_code


@pytest.fixture(autouse=True)
async def setup_database() -> AsyncGenerator[None, None]:
    """DB 연결 불필요 - conftest의 autouse fixture 오버라이드."""
    yield


@pytest.fixture
async def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.mark.asyncio
async def test_store_temp_code_returns_uuid(fake_redis) -> None:
    """store_temp_code는 유효한 UUID 형식의 코드를 반환한다."""
    code = await store_temp_code(fake_redis, "test-access-token")
    parsed = uuid.UUID(code)
    assert str(parsed) == code


@pytest.mark.asyncio
async def test_retrieve_temp_code_returns_value(fake_redis) -> None:
    """저장한 access_token을 코드로 조회할 수 있다."""
    token = "my-access-token-123"
    code = await store_temp_code(fake_redis, token)
    result = await retrieve_temp_code(fake_redis, code)
    assert result == token


@pytest.mark.asyncio
async def test_retrieve_temp_code_is_one_time(fake_redis) -> None:
    """임시 코드는 1회 사용 후 삭제된다."""
    code = await store_temp_code(fake_redis, "one-time-token")

    first = await retrieve_temp_code(fake_redis, code)
    assert first == "one-time-token"

    second = await retrieve_temp_code(fake_redis, code)
    assert second is None


@pytest.mark.asyncio
async def test_retrieve_nonexistent_code(fake_redis) -> None:
    """존재하지 않는 코드 조회 시 None을 반환한다."""
    result = await retrieve_temp_code(fake_redis, "nonexistent-code")
    assert result is None
