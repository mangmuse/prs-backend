import uuid
from collections.abc import AsyncGenerator

from fastapi import Request
from redis.asyncio import Redis

TEMP_CODE_TTL_SECONDS = 60


async def get_redis(request: Request) -> AsyncGenerator[Redis, None]:
    """FastAPI Depends용 Redis 의존성. app.state.redis에서 싱글턴을 꺼내 사용."""
    yield request.app.state.redis


async def store_temp_code(redis: Redis, access_token: str) -> str:
    code = str(uuid.uuid4())
    await redis.set(f"temp_code:{code}", access_token, ex=TEMP_CODE_TTL_SECONDS)
    return code


async def retrieve_temp_code(redis: Redis, code: str) -> str | None:
    key = f"temp_code:{code}"
    value: str | None = await redis.getdel(key)
    return value
