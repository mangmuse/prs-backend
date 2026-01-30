from datetime import UTC, datetime
from typing import Any, ClassVar
from uuid import UUID

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from src.common.types import LogicConstraint


class Dataset(SQLModel, table=True):
    """데이터셋 마스터 - 실험의 '시험 문제' 폴더."""

    __tablename__: ClassVar[str] = "datasets"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str | None = None
    user_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    guest_id: UUID | None = Field(default=None, foreign_key="guests.id", index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )


class DatasetRow(SQLModel, table=True):
    """데이터셋 행 - 개별 채점 기준을 가진 질문."""

    __tablename__: ClassVar[str] = "dataset_rows"

    id: int | None = Field(default=None, primary_key=True)
    dataset_id: int = Field(foreign_key="datasets.id", index=True)
    row_index: int = Field(default=0)
    input_data: dict[str, Any] = Field(sa_column=Column(JSONB))
    expected_output: str
    row_constraints: list[LogicConstraint] | None = Field(
        default=None, sa_column=Column(JSONB)
    )
    tags: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    updated_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
