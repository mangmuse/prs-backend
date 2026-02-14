from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from src.auth.dependencies import get_current_identity
from src.auth.models import Guest, User
from src.database import get_session
from src.datasets.dependencies import get_user_dataset
from src.datasets.models import DatasetRow
from src.llm.factory import resolve_api_key
from src.llm.rate_limiter import extract_provider
from src.profiles.dependencies import get_user_profile
from src.prompts.dependencies import get_user_prompt_version
from src.runs.dependencies import get_user_run
from src.runs.schemas import (
    CreateRunRequest,
    ReEvaluateRequest,
    ReEvaluateResponse,
    RegressionComparisonResponse,
    RelatedVersionsResponse,
    RunCreateResponse,
    RunDetailResponse,
    RunSummaryResponse,
    UpdateProfileSnapshotRequest,
)
from src.runs.service import (
    compare_runs,
    delete_run,
    get_related_versions,
    get_run_detail,
    get_runs_summary,
    re_evaluate_run,
    update_run_profile_snapshot,
)
from src.runs.service import (
    create_run as create_run_service,
)
from src.runs.tasks import process_run_task

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunCreateResponse, status_code=201)
async def create_run(
    data: CreateRunRequest,
    background_tasks: BackgroundTasks,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> RunCreateResponse:
    """Run 생성 및 백그라운드 실행."""
    version = await get_user_prompt_version(data.prompt_version_id, identity, session)
    _ = await get_user_dataset(data.dataset_id, identity, session)
    _ = await get_user_profile(data.profile_id, identity, session)

    provider = extract_provider(version.model)
    try:
        _ = resolve_api_key(provider, data.api_key)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"{provider} API Key가 필요합니다. Settings에서 입력해주세요.",
        )

    row_count = (
        await session.execute(
            select(func.count()).where(DatasetRow.dataset_id == data.dataset_id)
        )
    ).scalar_one()
    if row_count == 0:
        raise HTTPException(status_code=400, detail="데이터셋이 비어 있습니다")

    run = await create_run_service(data, identity, session)

    assert run.id is not None
    background_tasks.add_task(process_run_task, run.id, data.api_key)

    return RunCreateResponse(
        id=run.id,
        status=run.status.value,
        created_at=run.created_at,
    )


@router.delete("/{run_id}", status_code=204)
async def delete_run_endpoint(
    run_id: int,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Run 삭제."""
    run = await get_user_run(run_id, identity, session)
    await delete_run(run, session)


@router.get("", response_model=list[RunSummaryResponse])
async def list_runs(
    grouped: bool = True,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> list[RunSummaryResponse]:
    """Run 목록 조회."""
    return await get_runs_summary(identity, session, grouped=grouped)


@router.get("/{run_id}", response_model=RunDetailResponse)
async def get_run(
    run_id: int,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> RunDetailResponse:
    """Run 상세 조회."""
    return await get_run_detail(run_id, identity, session)


@router.get("/{run_id}/related-versions", response_model=RelatedVersionsResponse)
async def get_run_related_versions(
    run_id: int,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> RelatedVersionsResponse:
    """같은 조합의 관련 버전 조회."""
    return await get_related_versions(run_id, identity, session)


@router.get(
    "/{run_id}/compare/{base_run_id}", response_model=RegressionComparisonResponse
)
async def compare_runs_endpoint(
    run_id: int,
    base_run_id: int,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> RegressionComparisonResponse:
    """두 Run 간 회귀 분석."""
    return await compare_runs(base_run_id, run_id, identity, session)


@router.patch("/{run_id}/profile-snapshot", status_code=204)
async def update_profile_snapshot(
    run_id: int,
    data: UpdateProfileSnapshotRequest,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Run의 profile_snapshot 업데이트."""
    await update_run_profile_snapshot(run_id, data, identity, session)


@router.post("/{run_id}/re-evaluate", response_model=ReEvaluateResponse)
async def re_evaluate_run_endpoint(
    run_id: int,
    data: ReEvaluateRequest,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> ReEvaluateResponse:
    """프로필 값 변경 시 재평가 미리보기 (DB 변경 없음)."""
    return await re_evaluate_run(run_id, data, identity, session)
