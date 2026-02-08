from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_identity
from src.auth.models import Guest, User
from src.database import get_session
from src.profiles import schemas, service
from src.profiles.dependencies import get_user_profile

router = APIRouter(prefix="/evaluator-profiles", tags=["profiles"])


@router.post("", response_model=schemas.ProfileResponse, status_code=201)
async def create_profile(
    data: schemas.CreateProfileRequest,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> schemas.ProfileResponse:
    """평가 프로필 생성."""
    profile = await service.create_profile(data, identity, session)
    return schemas.ProfileResponse.model_validate(profile)


@router.get("", response_model=list[schemas.ProfileSummary])
async def list_profiles(
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.ProfileSummary]:
    """현재 사용자의 프로필 목록 조회."""
    return await service.list_profiles(identity, session)


@router.get("/{profile_id}", response_model=schemas.ProfileResponse)
async def get_profile_detail(
    profile_id: int,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> schemas.ProfileResponse:
    """프로필 상세 조회."""
    profile = await get_user_profile(profile_id, identity, session)
    return schemas.ProfileResponse.model_validate(profile)


@router.patch("/{profile_id}", response_model=schemas.ProfileResponse)
async def update_profile(
    profile_id: int,
    data: schemas.UpdateProfileRequest,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> schemas.ProfileResponse:
    """프로필 수정."""
    profile = await get_user_profile(profile_id, identity, session)
    updated = await service.update_profile(profile, data, session)
    return schemas.ProfileResponse.model_validate(updated)


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(
    profile_id: int,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> None:
    """프로필 삭제."""
    profile = await get_user_profile(profile_id, identity, session)
    await service.delete_profile(profile, session)
