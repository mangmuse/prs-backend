from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from joserfc import jwt as jose_jwt
from joserfc.jwk import OctKey
from joserfc.jwt import JWTClaimsRegistry
from sqlalchemy import update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from src.auth.models import Guest, User
from src.auth.schemas import TokenPayload
from src.config import get_settings
from src.datasets.models import Dataset
from src.profiles.models import EvaluatorProfile
from src.prompts.models import Prompt
from src.runs.models import Run

settings = get_settings()


def create_access_token(
    subject: UUID | int,
    token_type: str,
    expires_delta: timedelta | None = None,
) -> tuple[str, datetime]:
    """JWT 토큰 생성.

    Args:
        subject: guest_id 또는 user_id
        token_type: "guest" 또는 "user"
        expires_delta: 만료 기간 (기본값: 15분)

    Returns:
        (token, expires_at) 튜플
    """
    now = datetime.now(UTC)
    expire = now + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    key = OctKey.import_key(settings.SECRET_KEY)
    claims = {
        "sub": str(subject),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    token = jose_jwt.encode({"alg": settings.JWT_ALGORITHM}, claims, key)
    return token, expire


def create_refresh_token(
    subject: UUID | int,
    token_type: str,
    expires_delta: timedelta | None = None,
) -> tuple[str, datetime]:
    """Refresh JWT 토큰 생성.

    Args:
        subject: guest_id 또는 user_id
        token_type: "guest" 또는 "user" (자동으로 _refresh 접미사 추가)
        expires_delta: 만료 기간 (기본값: 7일)

    Returns:
        (token, expires_at) 튜플
    """
    return create_access_token(
        subject=subject,
        token_type=f"{token_type}_refresh",
        expires_delta=expires_delta
        or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> TokenPayload | None:
    """JWT 토큰 디코드.

    Args:
        token: JWT 문자열

    Returns:
        TokenPayload 또는 실패 시 None
    """
    try:
        key = OctKey.import_key(settings.SECRET_KEY)
        token_obj = jose_jwt.decode(token, key)

        claims_registry = JWTClaimsRegistry(exp={"essential": True})
        claims_registry.validate(token_obj.claims)

        claims = token_obj.claims
        return TokenPayload(
            sub=claims["sub"],
            type=claims["type"],
            iat=datetime.fromtimestamp(claims["iat"], tz=UTC),
            exp=datetime.fromtimestamp(claims["exp"], tz=UTC),
        )
    except Exception:
        return None


async def find_or_create_user(
    session: AsyncSession,
    email: str,
    provider_id: str,
    name: str | None = None,
    picture_url: str | None = None,
) -> User:
    """구글 OAuth 사용자 조회 또는 생성."""
    result = await session.execute(select(User).where(User.provider_id == provider_id))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is not None:
        user.provider_id = provider_id
        if name is not None:
            user.name = name
        if picture_url is not None:
            user.picture_url = picture_url
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    user = User(
        email=email,
        provider="google",
        provider_id=provider_id,
        name=name,
        picture_url=picture_url,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def migrate_guest_to_user(
    session: AsyncSession,
    guest_id: UUID,
    user_id: int,
) -> dict[str, int]:
    """게스트 데이터를 회원으로 이전.

    4개 테이블의 guest_id를 user_id로 전환하고 Guest 레코드를 삭제합니다.
    """
    counts: dict[str, int] = {}

    for model, key in [
        (Dataset, "datasets"),
        (Prompt, "prompts"),
        (EvaluatorProfile, "profiles"),
        (Run, "runs"),
    ]:
        result = await session.execute(
            update(model)
            .where(col(model.guest_id) == guest_id)  # type: ignore[attr-defined]
            .values(user_id=user_id, guest_id=None)
        )
        cursor_result = cast("CursorResult[Any]", result)
        counts[key] = cursor_result.rowcount

    guest_result = await session.execute(select(Guest).where(col(Guest.id) == guest_id))
    guest = guest_result.scalar_one_or_none()
    if guest:
        await session.delete(guest)

    return counts
