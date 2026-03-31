from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from src.auth.models import Guest, User
from src.common.exceptions import NotFoundError
from src.common.utils import get_ownership_filter
from src.datasets.models import Dataset, DatasetRow
from src.datasets.schemas import (
    CreateDatasetRequest,
    CreateRowRequest,
    DatasetDetailResponse,
    DatasetRowResponse,
    DatasetSummary,
    PaginationMeta,
    UpdateDatasetRequest,
    UpdateRowRequest,
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


async def update_dataset(
    dataset: Dataset,
    data: UpdateDatasetRequest,
    session: AsyncSession,
) -> Dataset:
    """데이터셋 메타 수정 (이름/설명)."""
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(dataset, key, value)

    session.add(dataset)
    await session.commit()
    await session.refresh(dataset)
    return dataset


async def delete_dataset(
    dataset: Dataset,
    session: AsyncSession,
) -> None:
    """데이터셋 삭제 (관련 DatasetRow cascade 삭제)."""
    assert dataset.id is not None
    _ = await session.execute(
        delete(DatasetRow).where(col(DatasetRow.dataset_id) == dataset.id)
    )
    await session.delete(dataset)
    await session.commit()


async def create_rows(
    dataset_id: int,
    rows_data: list[CreateRowRequest],
    session: AsyncSession,
) -> int:
    """데이터셋에 row 추가. 생성된 row 개수 반환."""
    max_index_stmt = select(func.max(DatasetRow.row_index)).where(
        col(DatasetRow.dataset_id) == dataset_id
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


async def update_row(
    dataset_id: int,
    row_id: int,
    data: UpdateRowRequest,
    session: AsyncSession,
) -> DatasetRow:
    """데이터셋 행 수정."""
    result = await session.execute(
        select(DatasetRow).where(
            col(DatasetRow.id) == row_id,
            col(DatasetRow.dataset_id) == dataset_id,
        )
    )
    row = result.scalar_one_or_none()

    if not row:
        raise NotFoundError(f"DatasetRow {row_id}을(를) 찾을 수 없습니다")

    row.input_data = data.input_data
    row.expected_output = data.expected_output
    row.tags = data.tags

    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def delete_row(
    dataset_id: int,
    row_id: int,
    session: AsyncSession,
) -> None:
    """데이터셋 행 삭제."""
    result = await session.execute(
        select(DatasetRow).where(
            col(DatasetRow.id) == row_id,
            col(DatasetRow.dataset_id) == dataset_id,
        )
    )
    row = result.scalar_one_or_none()

    if not row:
        raise NotFoundError(f"DatasetRow {row_id}을(를) 찾을 수 없습니다")

    await session.delete(row)
    await session.commit()


async def get_all_rows(
    dataset: Dataset,
    session: AsyncSession,
) -> list[DatasetRow]:
    """데이터셋의 전체 행을 row_index 순으로 조회."""
    assert dataset.id is not None
    stmt = (
        select(DatasetRow)
        .where(col(DatasetRow.dataset_id) == dataset.id)
        .order_by(col(DatasetRow.row_index))
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
