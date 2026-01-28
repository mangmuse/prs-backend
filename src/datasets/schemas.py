from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.common.types import LogicConstraint


class CreateDatasetRequest(BaseModel):
    name: str
    description: str | None = None


class CreateRowRequest(BaseModel):
    input_data: dict
    expected_output: str
    row_constraints: list[LogicConstraint] | None = None
    tags: list[str] | None = None


class CreateDatasetResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatasetSummary(BaseModel):
    id: int
    name: str
    description: str | None
    row_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatasetRowResponse(BaseModel):
    id: int
    dataset_id: int
    input_data: dict
    expected_output: str
    row_constraints: list[LogicConstraint] | None
    tags: list[str] | None

    model_config = ConfigDict(from_attributes=True)


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total_count: int
    total_pages: int


class DatasetDetailResponse(BaseModel):
    id: int
    name: str
    description: str | None
    rows: list[DatasetRowResponse]
    pagination: PaginationMeta


class CreateRowsResponse(BaseModel):
    created_count: int
