from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_identity
from src.auth.models import Guest, User
from src.database import get_session
from src.datasets.dependencies import get_user_dataset
from src.profiles.dependencies import get_user_profile
from src.prompts.dependencies import get_user_prompt_version
from src.runs.models import Run, RunStatus
from src.runs.schemas import (
    CreateRunRequest,
    RunCreateResponse,
    RunDetailResponse,
    RunSummaryResponse,
)
from src.runs.service import get_run_detail, get_runs_summary, process_run

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

    run = Run(
        prompt_version_id=data.prompt_version_id,
        dataset_id=data.dataset_id,
        profile_id=data.profile_id,
        status=RunStatus.RUNNING,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    assert run.id is not None
    background_tasks.add_task(process_run, run.id)

    return RunCreateResponse(
        id=run.id,
        status=run.status.value,
        created_at=run.created_at,
    )


@router.get("", response_model=list[RunSummaryResponse])
async def list_runs(
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> list[RunSummaryResponse]:
    """Run 목록 조회."""
    return await get_runs_summary(identity, session)


@router.get("/{run_id}", response_model=RunDetailResponse)
async def get_run(
    run_id: int,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> RunDetailResponse:
    """Run 상세 조회."""
    return await get_run_detail(run_id, identity, session)
