from datetime import UTC, datetime, timedelta
from uuid import UUID

from jose import JWTError, jwt

from src.auth.schemas import TokenPayload
from src.config import get_settings

settings = get_settings()


def create_access_token(
    subject: UUID,
    token_type: str,
    expires_delta: timedelta | None = None,
) -> tuple[str, datetime]:
    """JWT 토큰 생성.

    Args:
        subject: guest_id 또는 user_id
        token_type: "guest" 또는 "user"
        expires_delta: 만료 기간 (기본값: 30일)

    Returns:
        (token, expires_at) 튜플
    """
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS))

    payload = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expire


def decode_token(token: str) -> TokenPayload | None:
    """JWT 토큰 디코드.

    Args:
        token: JWT 문자열

    Returns:
        TokenPayload 또는 실패 시 None
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return TokenPayload(
            sub=payload["sub"],
            type=payload["type"],
            iat=datetime.fromtimestamp(payload["iat"], tz=UTC),
            exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
        )
    except JWTError:
        return None
