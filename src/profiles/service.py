from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from src.auth.models import Guest, User
from src.common.utils import get_ownership_filter
from src.profiles.models import EvaluatorProfile
from src.profiles.schemas import (
    CreateProfileRequest,
    ProfileSummary,
    UpdateProfileRequest,
)


async def create_profile(
    data: CreateProfileRequest,
    identity: Guest | User,
    session: AsyncSession,
) -> EvaluatorProfile:
    """프로필 생성."""
    constraints_as_dicts = (
        [c.model_dump() for c in data.global_constraints]
        if data.global_constraints
        else None
    )
    profile = EvaluatorProfile(
        name=data.name,
        description=data.description,
        semantic_threshold=data.semantic_threshold,
        global_constraints=constraints_as_dicts,
    )
    if isinstance(identity, Guest):
        profile.guest_id = identity.id
    else:
        profile.user_id = identity.id

    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return profile


async def list_profiles(
    identity: Guest | User,
    session: AsyncSession,
) -> list[ProfileSummary]:
    """프로필 목록 조회."""
    ownership_filter = get_ownership_filter(identity, EvaluatorProfile)

    stmt = (
        select(EvaluatorProfile)
        .where(ownership_filter)
        .order_by(col(EvaluatorProfile.created_at).desc())
    )
    profiles = (await session.execute(stmt)).scalars().all()

    return [
        ProfileSummary(
            id=p.id,
            name=p.name,
            description=p.description,
            semantic_threshold=p.semantic_threshold,
            constraint_count=len(p.global_constraints) if p.global_constraints else 0,
            created_at=p.created_at,
        )
        for p in profiles
    ]


async def update_profile(
    profile: EvaluatorProfile,
    data: UpdateProfileRequest,
    session: AsyncSession,
) -> EvaluatorProfile:
    """프로필 수정."""
    update_data = data.model_dump(exclude_unset=True)

    if "global_constraints" in update_data and update_data["global_constraints"]:
        update_data["global_constraints"] = [
            c.model_dump() for c in data.global_constraints  # type: ignore[union-attr]
        ]

    for key, value in update_data.items():
        setattr(profile, key, value)

    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return profile


async def delete_profile(
    profile: EvaluatorProfile,
    session: AsyncSession,
) -> None:
    """프로필 삭제."""
    await session.delete(profile)
    await session.commit()
