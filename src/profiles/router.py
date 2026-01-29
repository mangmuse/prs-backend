from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from src.auth.dependencies import get_current_identity
from src.auth.models import Guest, User
from src.database import get_session
from src.profiles import schemas
from src.profiles.dependencies import get_user_profile
from src.profiles.models import EvaluatorProfile

router = APIRouter(prefix="/evaluator-profiles", tags=["profiles"])


@router.post("", response_model=schemas.ProfileResponse, status_code=201)
async def create_profile(
    data: schemas.CreateProfileRequest,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> schemas.ProfileResponse:
    """평가 프로필 생성."""
    profile = EvaluatorProfile(
        name=data.name,
        description=data.description,
        semantic_threshold=data.semantic_threshold,
        global_constraints=data.global_constraints,
        guest_id=identity.id if isinstance(identity, Guest) else None,
        user_id=identity.id if isinstance(identity, User) else None,
    )
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return schemas.ProfileResponse.model_validate(profile)


@router.get("", response_model=list[schemas.ProfileSummary])
async def list_profiles(
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.ProfileSummary]:
    """현재 사용자의 프로필 목록 조회."""
    if isinstance(identity, Guest):
        ownership_filter = col(EvaluatorProfile.guest_id) == identity.id
    else:
        ownership_filter = col(EvaluatorProfile.user_id) == identity.id

    stmt = (
        select(EvaluatorProfile)
        .where(ownership_filter)
        .order_by(col(EvaluatorProfile.created_at).desc())
    )
    result = await session.execute(stmt)
    profiles = result.scalars().all()

    summaries = []
    for p in profiles:
        assert p.id is not None
        summaries.append(
            schemas.ProfileSummary(
                id=p.id,
                name=p.name,
                description=p.description,
                semantic_threshold=p.semantic_threshold,
                constraint_count=len(p.global_constraints) if p.global_constraints else 0,
                created_at=p.created_at,
            )
        )
    return summaries


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

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)

    profile.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(profile)
    return schemas.ProfileResponse.model_validate(profile)


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(
    profile_id: int,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> None:
    """프로필 삭제."""
    profile = await get_user_profile(profile_id, identity, session)
    await session.delete(profile)
    await session.commit()
