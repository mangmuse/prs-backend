import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.auth import service
from src.auth.dependencies import get_current_user
from src.auth.models import Guest, User
from src.auth.oauth import oauth
from src.auth.schemas import (
    GuestSessionResponse,
    MigrateResponse,
    TokenExchangeRequest,
    TokenResponse,
    UserResponse,
)
from src.common.exceptions import BadRequestError, NotFoundError, UnauthorizedError
from src.config import get_settings
from src.database import get_session
from src.redis import get_redis, retrieve_temp_code, store_temp_code

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
logger = logging.getLogger(__name__)

COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1년
REFRESH_COOKIE_MAX_AGE = 60 * 60 * 24 * settings.REFRESH_TOKEN_EXPIRE_DAYS


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


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Access Token 재발급",
    description="Refresh Token 쿠키를 검증하고 새 Access Token을 발급합니다.",
)
async def refresh_access_token(request: Request) -> TokenResponse:
    """Refresh Token으로 새 Access Token 발급."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise UnauthorizedError("리프레시 토큰이 없습니다")

    token_data = service.decode_token(refresh_token)
    if token_data is None:
        raise UnauthorizedError("유효하지 않은 리프레시 토큰입니다")

    if not token_data.type.endswith("_refresh"):
        raise UnauthorizedError("리프레시 토큰이 아닙니다")

    original_type = token_data.type.removesuffix("_refresh")
    subject: UUID | int = (
        UUID(token_data.sub) if original_type == "guest" else int(token_data.sub)
    )
    access_token, _ = service.create_access_token(subject, original_type)

    return TokenResponse(access_token=access_token)


@router.get(
    "/google",
    summary="구글 로그인 시작",
    description="구글 OAuth 인증 페이지로 리다이렉트합니다.",
)
async def google_login(request: Request) -> RedirectResponse:
    """구글 OAuth 인증 페이지로 리다이렉트."""
    redirect_uri = str(request.url_for("google_callback"))
    response = await oauth.google.authorize_redirect(request, redirect_uri)
    if not isinstance(response, RedirectResponse):
        raise BadRequestError("구글 인증 리다이렉트에 실패했습니다")
    return response


@router.get(
    "/google/callback",
    summary="구글 OAuth 콜백",
    description="구글 인증 후 콜백을 처리하고 토큰을 발급합니다.",
)
async def google_callback(
    request: Request,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> RedirectResponse:
    """구글 OAuth 콜백 처리 후 프론트엔드로 리다이렉트."""
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        logger.exception("구글 OAuth 토큰 교환 실패")
        raise BadRequestError("구글 인증에 실패했습니다")

    userinfo = token.get("userinfo")
    if userinfo is None:
        raise BadRequestError("구글 사용자 정보를 가져올 수 없습니다")

    email: str | None = userinfo.get("email")
    email_verified: bool = userinfo.get("email_verified", False)
    sub: str | None = userinfo.get("sub")

    if not email or not sub:
        raise BadRequestError("구글 사용자 정보가 불완전합니다")

    if not email_verified:
        raise BadRequestError("인증되지 않은 이메일입니다")

    user = await service.find_or_create_user(
        session=session,
        email=email,
        provider_id=sub,
        name=userinfo.get("name"),
        picture_url=userinfo.get("picture"),
    )

    assert user.id is not None
    access_token, _ = service.create_access_token(user.id, "user")
    refresh_token, _ = service.create_refresh_token(user.id, "user")

    guest_id_cookie = request.cookies.get("guest_id")
    was_guest = guest_id_cookie is not None
    temp_code = await store_temp_code(redis, access_token, was_guest=was_guest)

    redirect_url = f"{settings.FRONTEND_URL}/auth/callback?code={temp_code}"
    response = RedirectResponse(url=redirect_url, status_code=302)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        path="/auth",
        max_age=REFRESH_COOKIE_MAX_AGE,
    )

    return response


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="임시코드로 Access Token 교환",
    description="OAuth 콜백에서 받은 임시코드를 Access Token으로 교환합니다.",
)
async def exchange_token(
    body: TokenExchangeRequest,
    redis: Redis = Depends(get_redis),
) -> TokenResponse:
    """임시코드 → Access Token 교환 (1회용)."""
    payload = await retrieve_temp_code(redis, body.code)
    if payload is None:
        raise UnauthorizedError("유효하지 않은 인증 코드입니다")

    return TokenResponse(
        access_token=str(payload["access_token"]),
        was_guest=bool(payload.get("was_guest", False)),
    )


@router.post(
    "/logout",
    status_code=204,
    summary="로그아웃",
    description="refresh_token, guest_id 쿠키를 삭제합니다.",
)
async def logout(
    response: Response,
) -> None:
    """로그아웃 - HttpOnly 쿠키 삭제."""
    response.delete_cookie(
        key="refresh_token",
        path="/auth",
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
    )
    response.delete_cookie(
        key="guest_id",
        path="/",
        httponly=True,
        samesite="lax",
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="현재 사용자 정보 조회",
    description="Bearer Token으로 인증된 사용자 정보를 반환합니다.",
)
async def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    """현재 인증된 사용자 정보 반환."""
    assert user.id is not None
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        picture_url=user.picture_url,
    )


@router.post(
    "/migrate",
    response_model=MigrateResponse,
    summary="게스트 → 회원 데이터 마이그레이션",
    description="게스트 소유 자산을 로그인한 회원으로 이전합니다.",
)
async def migrate_guest_data(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MigrateResponse:
    """게스트 데이터를 회원으로 이전."""
    guest_id_cookie = request.cookies.get("guest_id")
    if not guest_id_cookie:
        raise BadRequestError("게스트 세션 정보가 없습니다")

    try:
        guest_uuid = UUID(guest_id_cookie)
    except ValueError:
        raise BadRequestError("유효하지 않은 게스트 ID입니다")

    guest_result = await session.execute(select(Guest).where(Guest.id == guest_uuid))
    guest = guest_result.scalar_one_or_none()
    if not guest:
        raise NotFoundError("존재하지 않는 게스트입니다")

    assert user.id is not None
    counts = await service.migrate_guest_to_user(session, guest_uuid, user.id)
    await session.commit()

    response.delete_cookie("guest_id", path="/")

    return MigrateResponse(**counts)
