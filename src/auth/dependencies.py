from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from src.auth import service
from src.auth.models import Guest, User
from src.common.exceptions import UnauthorizedError
from src.database import get_session

security = HTTPBearer(auto_error=False)


async def get_current_identity(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> Guest | User:
    """현재 인증된 Guest 또는 User 반환.

    인증 우선순위:
    1. Bearer Token → User 인증
    2. Cookie (guest_id) → Guest 인증

    Raises:
        UnauthorizedError: 인증 정보 없음, 유효하지 않음, 또는 사용자 없음
    """
    if credentials:
        token_data = service.decode_token(credentials.credentials)
        if token_data is None:
            raise UnauthorizedError("Invalid or expired token")

        subject_id = UUID(token_data.sub)

        if token_data.type == "user":
            user_stmt = select(User).where(col(User.id) == subject_id)
            user_result = await session.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            if user:
                return user
            raise UnauthorizedError("User not found")

        raise UnauthorizedError("Invalid token type")

    guest_id_cookie = request.cookies.get("guest_id")
    if guest_id_cookie:
        try:
            guest_uuid = UUID(guest_id_cookie)
            guest_stmt = select(Guest).where(col(Guest.id) == guest_uuid)
            guest_result = await session.execute(guest_stmt)
            guest = guest_result.scalar_one_or_none()
            if guest:
                return guest
        except ValueError:
            pass

    raise UnauthorizedError("Missing authentication")


async def get_current_guest(
    identity: Guest | User = Depends(get_current_identity),
) -> Guest:
    """Guest만 허용하는 엔드포인트용 의존성."""
    if not isinstance(identity, Guest):
        raise UnauthorizedError("Guest access required")
    return identity
