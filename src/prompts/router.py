from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, func, select

from src.auth.dependencies import get_current_identity
from src.auth.models import Guest, User
from src.database import get_session
from src.prompts import schemas
from src.prompts.dependencies import get_user_prompt
from src.prompts.models import Prompt, PromptVersion

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.post("", response_model=schemas.CreatePromptResponse, status_code=201)
async def create_prompt(
    data: schemas.CreatePromptRequest,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> schemas.CreatePromptResponse:
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

    return schemas.CreatePromptResponse.model_validate(prompt)


@router.get("", response_model=list[schemas.PromptSummary])
async def list_prompts(
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.PromptSummary]:
    """프롬프트 목록 조회."""
    if isinstance(identity, Guest):
        ownership_filter = col(Prompt.guest_id) == identity.id
    else:
        ownership_filter = col(Prompt.user_id) == identity.id

    version_subq = (
        select(
            PromptVersion.prompt_id,
            func.max(PromptVersion.version_number).label("latest_version"),
            func.count(PromptVersion.id).label("version_count"),
        )
        .group_by(PromptVersion.prompt_id)
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
            schemas.PromptSummary(
                id=prompt.id,
                name=prompt.name,
                description=prompt.description,
                latest_version=latest_version,
                version_count=version_count or 0,
                created_at=prompt.created_at,
            )
        )
    return summaries


@router.get("/{prompt_id}/versions", response_model=list[schemas.VersionSummary])
async def list_versions(
    prompt_id: int,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.VersionSummary]:
    """프롬프트 버전 히스토리 조회."""
    await get_user_prompt(prompt_id, identity, session)

    stmt = (
        select(PromptVersion)
        .where(col(PromptVersion.prompt_id) == prompt_id)
        .order_by(col(PromptVersion.version_number).desc())
    )
    result = await session.execute(stmt)
    versions = result.scalars().all()

    return [schemas.VersionSummary.model_validate(v) for v in versions]


@router.post(
    "/{prompt_id}/versions",
    response_model=schemas.VersionDetailResponse,
    status_code=201,
)
async def create_version(
    prompt_id: int,
    data: schemas.CreateVersionRequest,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> schemas.VersionDetailResponse:
    """새 버전 생성."""
    await get_user_prompt(prompt_id, identity, session)

    max_ver_stmt = (
        select(func.max(PromptVersion.version_number))
        .where(col(PromptVersion.prompt_id) == prompt_id)
    )
    max_ver = await session.scalar(max_ver_stmt) or 0

    version = PromptVersion(
        prompt_id=prompt_id,
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
    return schemas.VersionDetailResponse(
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


@router.get(
    "/{prompt_id}/versions/{version_id}",
    response_model=schemas.VersionDetailResponse,
)
async def get_version(
    prompt_id: int,
    version_id: int,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> schemas.VersionDetailResponse:
    """버전 상세 조회."""
    await get_user_prompt(prompt_id, identity, session)

    stmt = select(PromptVersion).where(
        col(PromptVersion.id) == version_id,
        col(PromptVersion.prompt_id) == prompt_id,
    )
    result = await session.execute(stmt)
    version = result.scalar_one_or_none()

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    assert version.id is not None
    return schemas.VersionDetailResponse(
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
