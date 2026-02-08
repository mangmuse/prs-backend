from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from src.auth.models import Guest, User
from src.common.utils import get_ownership_filter
from src.datasets.models import Dataset, DatasetRow
from src.datasets.schemas import (
    CreateDatasetRequest,
    CreateRowRequest,
    DatasetDetailResponse,
    DatasetRowResponse,
    DatasetSummary,
    PaginationMeta,
)


async def create_dataset(
    data: CreateDatasetRequest,
    identity: Guest | User,
    session: AsyncSession,
) -> Dataset:
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
    return dataset


async def list_datasets(
    identity: Guest | User,
    session: AsyncSession,
) -> list[DatasetSummary]:
    """데이터셋 목록 조회 (row count 포함)."""
    ownership_filter = get_ownership_filter(identity, Dataset)

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
        assert dataset.id is not None
        summaries.append(
            DatasetSummary(
                id=dataset.id,
                name=dataset.name,
                description=dataset.description,
                row_count=row_count,
                created_at=dataset.created_at,
            )
        )
    return summaries


async def get_dataset_detail(
    dataset: Dataset,
    session: AsyncSession,
    page: int = 1,
    limit: int = 50,
) -> DatasetDetailResponse:
    """데이터셋 상세 조회 (페이지네이션)."""
    assert dataset.id is not None

    count_stmt = (
        select(func.count())
        .select_from(DatasetRow)
        .where(col(DatasetRow.dataset_id) == dataset.id)
    )
    total_count = await session.scalar(count_stmt) or 0

    offset = (page - 1) * limit
    rows_stmt = (
        select(DatasetRow)
        .where(col(DatasetRow.dataset_id) == dataset.id)
        .order_by(col(DatasetRow.row_index))
        .offset(offset)
        .limit(limit)
    )
    rows_result = await session.execute(rows_stmt)
    rows = rows_result.scalars().all()

    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1

    return DatasetDetailResponse(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        rows=[DatasetRowResponse.model_validate(row) for row in rows],
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total_count=total_count,
            total_pages=total_pages,
        ),
    )


async def create_rows(
    dataset_id: int,
    rows_data: list[CreateRowRequest],
    session: AsyncSession,
) -> int:
    """데이터셋에 row 추가. 생성된 row 개수 반환."""
    max_index_stmt = (
        select(func.max(DatasetRow.row_index)).where(
            col(DatasetRow.dataset_id) == dataset_id
        )
    )
    max_index = await session.scalar(max_index_stmt) or 0

    new_rows = [
        DatasetRow(
            dataset_id=dataset_id,
            row_index=max_index + i + 1,
            input_data=row_data.input_data,
            expected_output=row_data.expected_output,
            tags=row_data.tags,
        )
        for i, row_data in enumerate(rows_data)
    ]

    session.add_all(new_rows)
    await session.commit()

    return len(new_rows)
