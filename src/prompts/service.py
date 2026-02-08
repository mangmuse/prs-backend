from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, func, select

from src.auth.models import Guest, User
from src.common.utils import get_ownership_filter
from src.prompts.models import Prompt, PromptVersion
from src.prompts.schemas import (
    CreatePromptRequest,
    CreatePromptResponse,
    CreateVersionRequest,
    PromptSummary,
    VersionDetailResponse,
    VersionSummary,
)


async def create_prompt(
    data: CreatePromptRequest,
    identity: Guest | User,
    session: AsyncSession,
) -> CreatePromptResponse:
    """프롬프트 생성."""
    prompt = Prompt(
        name=data.name,
        description=data.description,
        guest_id=identity.id if isinstance(identity, Guest) else None,
        user_id=identity.id if isinstance(identity, User) else None,
    )
    session.add(prompt)
    await session.commit()
    await session.refresh(prompt)

    return CreatePromptResponse.model_validate(prompt)


async def list_prompts(
    identity: Guest | User,
    session: AsyncSession,
) -> list[PromptSummary]:
    """프롬프트 목록 조회 (latest_version, version_count 포함)."""
    ownership_filter = get_ownership_filter(identity, Prompt)

    version_subq = (
        select(
            PromptVersion.prompt_id,
            func.max(col(PromptVersion.version_number)).label("latest_version"),
            func.count(col(PromptVersion.id)).label("version_count"),
        )
        .group_by(col(PromptVersion.prompt_id))
        .subquery()
    )

    stmt = (
        select(
            Prompt,
            version_subq.c.latest_version,
            version_subq.c.version_count,
        )
        .outerjoin(version_subq, col(Prompt.id) == version_subq.c.prompt_id)
        .where(ownership_filter)
        .order_by(col(Prompt.created_at).desc())
    )

    result = await session.execute(stmt)
    rows = result.all()

    summaries = []
    for prompt, latest_version, version_count in rows:
        assert prompt.id is not None
        summaries.append(
            PromptSummary(
                id=prompt.id,
                name=prompt.name,
                description=prompt.description,
                latest_version=latest_version,
                version_count=version_count or 0,
                created_at=prompt.created_at,
            )
        )
    return summaries


async def list_versions(
    prompt: Prompt,
    session: AsyncSession,
) -> list[VersionSummary]:
    """프롬프트의 모든 버전 조회."""
    stmt = (
        select(PromptVersion)
        .where(col(PromptVersion.prompt_id) == prompt.id)
        .order_by(col(PromptVersion.version_number).desc())
    )
    result = await session.execute(stmt)
    versions = result.scalars().all()

    return [VersionSummary.model_validate(v) for v in versions]


async def create_version(
    prompt: Prompt,
    data: CreateVersionRequest,
    session: AsyncSession,
) -> VersionDetailResponse:
    """새 버전 생성."""
    max_ver_stmt = (
        select(func.max(PromptVersion.version_number))
        .where(col(PromptVersion.prompt_id) == prompt.id)
    )
    max_ver = await session.scalar(max_ver_stmt) or 0

    version = PromptVersion(
        prompt_id=prompt.id,
        version_number=max_ver + 1,
        system_instruction=data.system_instruction,
        user_template=data.user_template,
        model=data.model,
        temperature=data.temperature,
        output_schema=data.output_schema,
        memo=data.memo,
    )
    session.add(version)
    await session.commit()
    await session.refresh(version)

    assert version.id is not None
    return VersionDetailResponse(
        id=version.id,
        prompt_id=version.prompt_id,
        version_number=version.version_number,
        system_instruction=version.system_instruction,
        user_template=version.user_template,
        model=version.model,
        temperature=version.temperature,
        output_schema=version.output_schema,
        memo=version.memo,
        created_at=version.created_at,
    )


async def get_version(
    prompt: Prompt,
    version_id: int,
    session: AsyncSession,
) -> VersionDetailResponse:
    """버전 상세 조회."""
    stmt = select(PromptVersion).where(
        col(PromptVersion.id) == version_id,
        col(PromptVersion.prompt_id) == prompt.id,
    )
    result = await session.execute(stmt)
    version = result.scalar_one_or_none()

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    assert version.id is not None
    return VersionDetailResponse(
        id=version.id,
        prompt_id=version.prompt_id,
        version_number=version.version_number,
        system_instruction=version.system_instruction,
        user_template=version.user_template,
        model=version.model,
        temperature=version.temperature,
        output_schema=version.output_schema,
        memo=version.memo,
        created_at=version.created_at,
    )
