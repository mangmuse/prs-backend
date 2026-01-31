from datetime import datetime
from typing import Any

from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from src.common.schemas import CamelCaseModel


class CreateDatasetRequest(CamelCaseModel):
    name: str
    description: str | None = None


class CreateRowRequest(CamelCaseModel):
    input_data: dict[str, Any]
    expected_output: str
    tags: list[str] | None = None


class CreateDatasetResponse(CamelCaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )


class DatasetSummary(CamelCaseModel):
    id: int
    name: str
    description: str | None
    row_count: int
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )


class DatasetRowResponse(CamelCaseModel):
    id: int
    dataset_id: int
    input_data: dict[str, Any]
    expected_output: str
    tags: list[str] | None

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )


class PaginationMeta(CamelCaseModel):
    page: int
    limit: int
    total_count: int
    total_pages: int


class DatasetDetailResponse(CamelCaseModel):
    id: int
    name: str
    description: str | None
    rows: list[DatasetRowResponse]
    pagination: PaginationMeta


class CreateRowsResponse(CamelCaseModel):
    created_count: int
