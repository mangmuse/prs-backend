from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_identity
from src.auth.models import Guest, User
from src.database import get_session
from src.prompts import schemas, service
from src.prompts.dependencies import get_user_prompt

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.post("", response_model=schemas.CreatePromptResponse, status_code=201)
async def create_prompt(
    data: schemas.CreatePromptRequest,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> schemas.CreatePromptResponse:
    """프롬프트 생성."""
    return await service.create_prompt(data, identity, session)


@router.get("", response_model=list[schemas.PromptSummary])
async def list_prompts(
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.PromptSummary]:
    """프롬프트 목록 조회."""
    return await service.list_prompts(identity, session)


@router.patch("/{prompt_id}", response_model=schemas.UpdatePromptResponse)
async def update_prompt(
    prompt_id: int,
    data: schemas.UpdatePromptRequest,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> schemas.UpdatePromptResponse:
    """프롬프트 메타 수정."""
    prompt = await get_user_prompt(prompt_id, identity, session)
    updated = await service.update_prompt(prompt, data, session)
    return schemas.UpdatePromptResponse.model_validate(updated)


@router.delete("/{prompt_id}", status_code=204)
async def delete_prompt(
    prompt_id: int,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> None:
    """프롬프트 삭제."""
    prompt = await get_user_prompt(prompt_id, identity, session)
    await service.delete_prompt(prompt, session)


@router.get("/{prompt_id}/versions", response_model=list[schemas.VersionSummary])
async def list_versions(
    prompt_id: int,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.VersionSummary]:
    """프롬프트 버전 히스토리 조회."""
    prompt = await get_user_prompt(prompt_id, identity, session)
    return await service.list_versions(prompt, session)


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
    prompt = await get_user_prompt(prompt_id, identity, session)
    return await service.create_version(prompt, data, session)


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
    prompt = await get_user_prompt(prompt_id, identity, session)
    return await service.get_version(prompt, version_id, session)
