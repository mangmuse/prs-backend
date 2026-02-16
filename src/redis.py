import json
import logging
import uuid
from collections.abc import AsyncGenerator

from fastapi import Request
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

TEMP_CODE_TTL_SECONDS = 60


async def get_redis(request: Request) -> AsyncGenerator[Redis, None]:
    """FastAPI Depends용 Redis 의존성. app.state.redis에서 싱글턴을 꺼내 사용."""
    yield request.app.state.redis


async def store_temp_code(
    redis: Redis, access_token: str, *, was_guest: bool = False
) -> str:
    code = str(uuid.uuid4())
    payload = json.dumps({"access_token": access_token, "was_guest": was_guest})
    await redis.set(f"temp_code:{code}", payload, ex=TEMP_CODE_TTL_SECONDS)
    return code


async def retrieve_temp_code(redis: Redis, code: str) -> dict[str, str | bool] | None:
    key = f"temp_code:{code}"
    value: str | None = await redis.getdel(key)
    if value is None:
        return None
    try:
        parsed: dict[str, str | bool] = json.loads(value)
        return parsed
    except json.JSONDecodeError:
        logger.warning("Redis 임시코드 JSON 파싱 실패: key=%s", key)
        return None
