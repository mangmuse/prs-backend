from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from src.auth import service
from src.auth.models import Guest, User
from src.common.exceptions import UnauthorizedError
from src.database import get_session

security = HTTPBearer(auto_error=False)


async def get_current_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> Guest | User:
    """현재 인증된 Guest 또는 User 반환.

    Raises:
        UnauthorizedError: 토큰 없음, 유효하지 않음, 또는 사용자 없음
    """
    if credentials is None:
        raise UnauthorizedError("Missing authentication token")

    token_data = service.decode_token(credentials.credentials)
    if token_data is None:
        raise UnauthorizedError("Invalid or expired token")

    subject_id = UUID(token_data.sub)

    identity: Guest | User | None = None
    if token_data.type == "guest":
        guest_stmt = select(Guest).where(col(Guest.id) == subject_id)
        guest_result = await session.execute(guest_stmt)
        identity = guest_result.scalar_one_or_none()
    elif token_data.type == "user":
        user_stmt = select(User).where(col(User.id) == subject_id)
        user_result = await session.execute(user_stmt)
        identity = user_result.scalar_one_or_none()
    else:
        raise UnauthorizedError("Invalid token type")

    if identity is None:
        raise UnauthorizedError("Identity not found")

    return identity


async def get_current_guest(
    identity: Guest | User = Depends(get_current_identity),
) -> Guest:
    """Guest만 허용하는 엔드포인트용 의존성."""
    if not isinstance(identity, Guest):
        raise UnauthorizedError("Guest access required")
    return identity
