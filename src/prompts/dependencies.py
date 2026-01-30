from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from src.auth.models import Guest, User
from src.prompts.models import Prompt, PromptVersion


async def get_user_prompt(
    prompt_id: int,
    identity: Guest | User,
    session: AsyncSession,
) -> Prompt:
    """프롬프트 조회 및 소유권 검증."""
    if isinstance(identity, Guest):
        filter_cond = col(Prompt.guest_id) == identity.id
    else:
        filter_cond = col(Prompt.user_id) == identity.id

    stmt = select(Prompt).where(
        col(Prompt.id) == prompt_id,
        filter_cond,
    )
    result = await session.execute(stmt)
    prompt = result.scalar_one_or_none()

    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


async def get_user_prompt_version(
    version_id: int,
    identity: Guest | User,
    session: AsyncSession,
) -> PromptVersion:
    """프롬프트 버전 조회 및 소유권 검증."""
    stmt = (
        select(PromptVersion)
        .join(Prompt, col(PromptVersion.prompt_id) == col(Prompt.id))
        .where(col(PromptVersion.id) == version_id)
    )

    if isinstance(identity, Guest):
        stmt = stmt.where(col(Prompt.guest_id) == identity.id)
    else:
        stmt = stmt.where(col(Prompt.user_id) == identity.id)

    result = await session.execute(stmt)
    version = result.scalar_one_or_none()

    if not version:
        raise HTTPException(status_code=404, detail="프롬프트 버전을 찾을 수 없습니다")
    return version
