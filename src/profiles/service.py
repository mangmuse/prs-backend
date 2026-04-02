from uuid import UUID

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

DEFAULT_PROFILE_NAME = "기본 평가 프로필"
DEFAULT_PROFILE_DESCRIPTION = (
    "예상 출력과 실제 출력의 의미적 유사도(cosine similarity)가 "
    "0.75 이상일 때 통과로 판정합니다."
)
DEFAULT_SEMANTIC_THRESHOLD = 0.75


async def create_default_profile(
    session: AsyncSession,
    *,
    guest_id: UUID | None = None,
    user_id: int | None = None,
) -> EvaluatorProfile:
    """기본 평가 프로필 생성."""
    profile = EvaluatorProfile(
        name=DEFAULT_PROFILE_NAME,
        description=DEFAULT_PROFILE_DESCRIPTION,
        semantic_threshold=DEFAULT_SEMANTIC_THRESHOLD,
        global_constraints=[],
        guest_id=guest_id,
        user_id=user_id,
    )
    session.add(profile)
    return profile


async def create_profile(
    data: CreateProfileRequest,
    identity: Guest | User,
    session: AsyncSession,
) -> EvaluatorProfile:
    """프로필 생성."""
    profile = EvaluatorProfile(
        name=data.name,
        description=data.description,
        semantic_threshold=data.semantic_threshold,
        global_constraints=[c.model_dump() for c in data.global_constraints],  # pyright: ignore[reportArgumentType]  # JSONB는 dict 필요, LogicConstraint 타입과 불가피한 불일치
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

    result: list[ProfileSummary] = []
    for p in profiles:
        assert p.id is not None
        result.append(
            ProfileSummary(
                id=p.id,
                name=p.name,
                description=p.description,
                semantic_threshold=p.semantic_threshold,
                constraint_count=len(p.global_constraints or []),
                created_at=p.created_at,
            )
        )
    return result


async def update_profile(
    profile: EvaluatorProfile,
    data: UpdateProfileRequest,
    session: AsyncSession,
) -> EvaluatorProfile:
    """프로필 수정."""
    update_data = data.model_dump(exclude_unset=True)

    if "global_constraints" in update_data and data.global_constraints is not None:
        update_data["global_constraints"] = [
            c.model_dump() for c in data.global_constraints
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
