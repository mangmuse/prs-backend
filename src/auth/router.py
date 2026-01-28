from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import service
from src.auth.models import Guest
from src.auth.schemas import GuestSessionResponse
from src.config import get_settings
from src.database import get_session

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post(
    "/guest",
    response_model=GuestSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="게스트 세션 생성",
    description="새로운 게스트 세션을 생성하고 JWT 토큰을 반환합니다. 토큰 유효기간: 30일",
)
async def create_guest_session(
    session: AsyncSession = Depends(get_session),
) -> GuestSessionResponse:
    """게스트 세션 생성 및 JWT 반환."""
    expires_delta = timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    expires_at = datetime.now(UTC) + expires_delta

    guest = Guest(session_token="temp", expires_at=expires_at)
    session.add(guest)
    await session.flush()

    token, expires_at = service.create_access_token(
        subject=guest.id,
        token_type="guest",
        expires_delta=expires_delta,
    )

    guest.session_token = token
    guest.expires_at = expires_at
    await session.commit()
    await session.refresh(guest)

    return GuestSessionResponse(
        guest_id=guest.id,
        token=token,
        expires_at=expires_at,
    )
