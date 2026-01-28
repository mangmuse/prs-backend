from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.auth.models import Guest
from src.auth.schemas import GuestSessionResponse
from src.config import get_settings
from src.database import get_session

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1년


@router.post(
    "/guest",
    response_model=GuestSessionResponse,
    summary="게스트 세션 생성",
    description="게스트 세션을 생성하거나 기존 세션을 반환합니다. HttpOnly Cookie로 인증.",
)
async def create_guest_session(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> GuestSessionResponse:
    """게스트 세션 생성 또는 기존 세션 반환."""
    existing_guest_id = request.cookies.get("guest_id")

    if existing_guest_id:
        try:
            guest_uuid = UUID(existing_guest_id)
            result = await session.execute(select(Guest).where(Guest.id == guest_uuid))
            guest = result.scalar_one_or_none()

            if guest:
                return GuestSessionResponse(
                    guest_id=guest.id,
                    created_at=guest.created_at,
                )
        except ValueError:
            pass

    guest = Guest()
    session.add(guest)
    await session.commit()
    await session.refresh(guest)

    response.set_cookie(
        key="guest_id",
        value=str(guest.id),
        httponly=True,
        samesite="lax",
        path="/",
        max_age=COOKIE_MAX_AGE,
    )

    return GuestSessionResponse(
        guest_id=guest.id,
        created_at=guest.created_at,
    )
