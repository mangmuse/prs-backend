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
            raise UnauthorizedError("유효하지 않거나 만료된 토큰입니다")

        if token_data.type == "user":
            user_id = int(token_data.sub)
            user_stmt = select(User).where(col(User.id) == user_id)
            user_result = await session.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            if user:
                return user
            raise UnauthorizedError("사용자를 찾을 수 없습니다")

        raise UnauthorizedError("유효하지 않은 토큰 타입입니다")

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

    raise UnauthorizedError("인증 정보가 없습니다")


async def get_current_guest(
    identity: Guest | User = Depends(get_current_identity),
) -> Guest:
    """Guest만 허용하는 엔드포인트용 의존성."""
    if not isinstance(identity, Guest):
        raise UnauthorizedError("게스트 접근만 허용됩니다")
    return identity


async def get_current_user(
    identity: Guest | User = Depends(get_current_identity),
) -> User:
    """User만 허용하는 엔드포인트용 의존성."""
    if not isinstance(identity, User):
        raise UnauthorizedError("회원 인증이 필요합니다")
    return identity
