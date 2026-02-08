from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_identity
from src.auth.models import Guest, User
from src.database import get_session
from src.datasets.dependencies import get_user_dataset
from src.profiles.dependencies import get_user_profile
from src.prompts.dependencies import get_user_prompt_version
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
    await get_user_prompt_version(data.prompt_version_id, identity, session)
    await get_user_dataset(data.dataset_id, identity, session)
    await get_user_profile(data.profile_id, identity, session)

    run = await create_run_service(data, session)

    assert run.id is not None
    background_tasks.add_task(process_run_task, run.id, data.api_key)

    return RunCreateResponse(
        id=run.id,
        status=run.status.value,
        created_at=run.created_at,
    )


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
