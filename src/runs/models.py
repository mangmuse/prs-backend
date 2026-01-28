import uuid
from datetime import UTC, datetime
from enum import Enum

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from src.common.types import LogicCheckResult, ParsedOutput


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ResultStatus(str, Enum):
    PASS = "pass"
    FORMAT_FAIL = "format_fail"
    SEMANTIC_FAIL = "semantic_fail"
    LOGIC_FAIL = "logic_fail"


class Run(SQLModel, table=True):
    __tablename__ = "runs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    prompt_version_id: uuid.UUID = Field(foreign_key="prompt_versions.id", index=True)
    dataset_id: uuid.UUID = Field(foreign_key="datasets.id", index=True)
    profile_id: uuid.UUID = Field(foreign_key="evaluator_profiles.id", index=True)
    status: RunStatus = Field(default=RunStatus.PENDING)
    total_rows: int = Field(default=0)
    completed_rows: int = Field(default=0)
    pass_count: int = Field(default=0)
    user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id", index=True)
    guest_id: uuid.UUID | None = Field(
        default=None, foreign_key="guests.id", index=True
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class RunResult(SQLModel, table=True):
    __tablename__ = "run_results"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    run_id: uuid.UUID = Field(foreign_key="runs.id", index=True)
    dataset_row_id: uuid.UUID = Field(foreign_key="dataset_rows.id", index=True)
    status: ResultStatus = Field(default=ResultStatus.PASS)
    raw_output: str | None = None
    parsed_output: ParsedOutput | None = Field(default=None, sa_column=Column(JSONB))
    format_valid: bool = Field(default=False)
    semantic_score: float | None = None
    semantic_passed: bool = Field(default=False)
    logic_passed: bool = Field(default=False)
    logic_details: list[LogicCheckResult] | None = Field(
        default=None, sa_column=Column(JSONB)
    )
    expected_embedding: list[float] | None = Field(
        default=None, sa_column=Column(Vector(1536))
    )
    output_embedding: list[float] | None = Field(
        default=None, sa_column=Column(Vector(1536))
    )
    latency_ms: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
