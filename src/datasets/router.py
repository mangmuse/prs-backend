from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_identity
from src.auth.models import Guest, User
from src.database import get_session
from src.datasets import csv_exporter, csv_parser, schemas, service
from src.datasets.dependencies import get_user_dataset

router = APIRouter(prefix="/datasets", tags=["datasets"])

MAX_CSV_SIZE = 1_000_000


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


@router.patch("/{dataset_id}", response_model=schemas.UpdateDatasetResponse)
async def update_dataset(
    dataset_id: int,
    data: schemas.UpdateDatasetRequest,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> schemas.UpdateDatasetResponse:
    """데이터셋 메타 수정."""
    dataset = await get_user_dataset(dataset_id, identity, session)
    updated = await service.update_dataset(dataset, data, session)
    return schemas.UpdateDatasetResponse.model_validate(updated)


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(
    dataset_id: int,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> None:
    """데이터셋 삭제."""
    dataset = await get_user_dataset(dataset_id, identity, session)
    await service.delete_dataset(dataset, session)


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
    _ = await get_user_dataset(dataset_id, identity, session)
    created_count = await service.create_rows(dataset_id, rows_data, session)
    return schemas.CreateRowsResponse(created_count=created_count)


@router.put(
    "/{dataset_id}/rows/{row_id}",
    response_model=schemas.DatasetRowResponse,
)
async def update_row(
    dataset_id: int,
    row_id: int,
    data: schemas.UpdateRowRequest,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> schemas.DatasetRowResponse:
    """데이터셋 행 수정."""
    _ = await get_user_dataset(dataset_id, identity, session)
    row = await service.update_row(dataset_id, row_id, data, session)
    return schemas.DatasetRowResponse.model_validate(row)


@router.delete("/{dataset_id}/rows/{row_id}", status_code=204)
async def delete_row(
    dataset_id: int,
    row_id: int,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> None:
    """데이터셋 행 삭제."""
    _ = await get_user_dataset(dataset_id, identity, session)
    await service.delete_row(dataset_id, row_id, session)


@router.post(
    "/{dataset_id}/import-csv",
    response_model=schemas.CsvImportResponse,
    status_code=201,
)
async def import_csv(
    dataset_id: int,
    file: UploadFile,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> schemas.CsvImportResponse:
    """CSV 파일로 데이터셋 행 일괄 추가."""
    _ = await get_user_dataset(dataset_id, identity, session)

    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV 파일만 업로드 가능합니다")

    raw_bytes = await file.read()
    if len(raw_bytes) > MAX_CSV_SIZE:
        raise HTTPException(status_code=400, detail="파일 크기는 1MB 이하여야 합니다")

    try:
        parsed_rows = csv_parser.parse_csv(raw_bytes)
    except ValueError as e:
        error_data = e.args[0]
        if isinstance(error_data, list):
            raise HTTPException(
                status_code=422,
                detail={"message": "유효하지 않은 행이 있습니다", "errors": error_data},
            )
        raise HTTPException(status_code=400, detail=str(error_data))

    row_requests = [
        schemas.CreateRowRequest(
            input_data=row["input_data"],
            expected_output=row["expected_output"],
            tags=row["tags"],
        )
        for row in parsed_rows
    ]
    created_count = await service.create_rows(dataset_id, row_requests, session)

    return schemas.CsvImportResponse(created_count=created_count)


@router.get("/{dataset_id}/export-csv")
async def export_csv(
    dataset_id: int,
    identity: Guest | User = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """데이터셋 전체 행을 CSV 파일로 내보내기."""
    dataset = await get_user_dataset(dataset_id, identity, session)
    rows = await service.get_all_rows(dataset, session)

    row_dicts = [
        {
            "input_data": row.input_data,
            "expected_output": row.expected_output,
            "tags": row.tags,
        }
        for row in rows
    ]

    csv_content = csv_exporter.rows_to_csv(row_dicts)

    encoded_name = quote(f"{dataset.name}.csv")
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"},
    )
