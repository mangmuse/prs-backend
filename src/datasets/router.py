from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, func, select

from src.auth.dependencies import get_current_identity
from src.auth.models import Guest, User
from src.database import get_session
from src.datasets import schemas
from src.datasets.dependencies import get_user_dataset
from src.datasets.models import Dataset, DatasetRow

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("", response_model=schemas.CreateDatasetResponse, status_code=201)
async def create_dataset(
    data: schemas.CreateDatasetRequest,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> schemas.CreateDatasetResponse:
    """데이터셋 생성."""
    dataset = Dataset(
        name=data.name,
        description=data.description,
        guest_id=identity.id if isinstance(identity, Guest) else None,
        user_id=identity.id if isinstance(identity, User) else None,
    )
    session.add(dataset)
    await session.commit()
    await session.refresh(dataset)

    return schemas.CreateDatasetResponse.model_validate(dataset)


@router.get("", response_model=list[schemas.DatasetSummary])
async def list_datasets(
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.DatasetSummary]:
    """현재 사용자의 데이터셋 목록 조회."""
    if isinstance(identity, Guest):
        ownership_filter = col(Dataset.guest_id) == identity.id
    else:
        ownership_filter = col(Dataset.user_id) == identity.id

    stmt = (
        select(Dataset, func.count(col(DatasetRow.id)).label("row_count"))
        .outerjoin(DatasetRow, col(Dataset.id) == col(DatasetRow.dataset_id))
        .where(ownership_filter)
        .group_by(col(Dataset.id))
        .order_by(col(Dataset.created_at).desc())
    )

    result = await session.execute(stmt)
    rows = result.all()

    summaries = []
    for dataset, row_count in rows:
        assert dataset.id is not None  # DB에서 조회한 레코드는 항상 id 존재
        summaries.append(
            schemas.DatasetSummary(
                id=dataset.id,
                name=dataset.name,
                description=dataset.description,
                row_count=row_count,
                created_at=dataset.created_at,
            )
        )
    return summaries


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

    count_stmt = (
        select(func.count())
        .select_from(DatasetRow)
        .where(col(DatasetRow.dataset_id) == dataset_id)
    )
    total_count = await session.scalar(count_stmt) or 0

    offset = (page - 1) * limit
    rows_stmt = (
        select(DatasetRow)
        .where(col(DatasetRow.dataset_id) == dataset_id)
        .order_by(col(DatasetRow.row_index))
        .offset(offset)
        .limit(limit)
    )
    rows_result = await session.execute(rows_stmt)
    rows = rows_result.scalars().all()

    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1

    assert dataset.id is not None  # DB에서 조회한 레코드는 항상 id 존재
    return schemas.DatasetDetailResponse(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        rows=[schemas.DatasetRowResponse.model_validate(row) for row in rows],
        pagination=schemas.PaginationMeta(
            page=page,
            limit=limit,
            total_count=total_count,
            total_pages=total_pages,
        ),
    )


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

    max_index_stmt = (
        select(func.max(DatasetRow.row_index))
        .where(col(DatasetRow.dataset_id) == dataset_id)
    )
    max_index = await session.scalar(max_index_stmt) or 0

    new_rows = [
        DatasetRow(
            dataset_id=dataset_id,
            row_index=max_index + i + 1,
            input_data=row_data.input_data,
            expected_output=row_data.expected_output,
            row_constraints=row_data.row_constraints,
            tags=row_data.tags,
        )
        for i, row_data in enumerate(rows_data)
    ]

    session.add_all(new_rows)
    await session.commit()

    return schemas.CreateRowsResponse(created_count=len(new_rows))
