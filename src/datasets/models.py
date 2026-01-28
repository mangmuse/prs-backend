import uuid
from datetime import UTC, datetime
from typing import ClassVar

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from src.common.types import LogicConstraint


class Dataset(SQLModel, table=True):
    __tablename__: ClassVar[str] = "datasets"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True)
    description: str | None = None
    user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id", index=True)
    guest_id: uuid.UUID | None = Field(
        default=None, foreign_key="guests.id", index=True
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DatasetRow(SQLModel, table=True):
    __tablename__: ClassVar[str] = "dataset_rows"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    dataset_id: uuid.UUID = Field(foreign_key="datasets.id", index=True)
    row_index: int = Field(default=0)
    input_text: str
    expected: str | None = None
    tags: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    logic_constraints: list[LogicConstraint] | None = Field(
        default=None, sa_column=Column(JSONB)
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
