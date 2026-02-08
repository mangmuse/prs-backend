from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_identity
from src.auth.models import Guest, User
from src.database import get_session
from src.datasets import schemas, service
from src.datasets.dependencies import get_user_dataset

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("", response_model=schemas.CreateDatasetResponse, status_code=201)
async def create_dataset(
    data: schemas.CreateDatasetRequest,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> schemas.CreateDatasetResponse:
    """데이터셋 생성."""
    dataset = await service.create_dataset(data, identity, session)
    return schemas.CreateDatasetResponse.model_validate(dataset)


@router.get("", response_model=list[schemas.DatasetSummary])
async def list_datasets(
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.DatasetSummary]:
    """현재 사용자의 데이터셋 목록 조회."""
    return await service.list_datasets(identity, session)


@router.get("/{dataset_id}", response_model=schemas.DatasetDetailResponse)
async def get_dataset_detail(
    dataset_id: int,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> schemas.DatasetDetailResponse:
    """데이터셋 상세 조회 (행 페이지네이션 포함)."""
    dataset = await get_user_dataset(dataset_id, identity, session)
    return await service.get_dataset_detail(dataset, session, page, limit)


@router.post(
    "/{dataset_id}/rows",
    response_model=schemas.CreateRowsResponse,
    status_code=201,
)
async def create_rows(
    dataset_id: int,
    rows_data: list[schemas.CreateRowRequest],
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> schemas.CreateRowsResponse:
    """데이터셋 행 일괄 생성."""
    await get_user_dataset(dataset_id, identity, session)
    created_count = await service.create_rows(dataset_id, rows_data, session)
    return schemas.CreateRowsResponse(created_count=created_count)
