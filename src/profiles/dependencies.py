from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from src.auth.models import Guest, User
from src.profiles.models import EvaluatorProfile


async def get_user_profile(
    profile_id: int,
    identity: Guest | User,
    session: AsyncSession,
) -> EvaluatorProfile:
    """프로필 조회 및 소유권 검증."""
    if isinstance(identity, Guest):
        filter_cond = col(EvaluatorProfile.guest_id) == identity.id
    else:
        filter_cond = col(EvaluatorProfile.user_id) == identity.id

    stmt = select(EvaluatorProfile).where(
        col(EvaluatorProfile.id) == profile_id,
        filter_cond,
    )
    result = await session.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile
