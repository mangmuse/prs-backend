from datetime import UTC, datetime
from enum import Enum
from typing import ClassVar
from uuid import UUID

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class RunStatus(str, Enum):
    """실행 상태."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ResultStatus(str, Enum):
    """결과 상태 - Waterfall 평가 결과."""

    PASS = "pass"
    FORMAT = "format"
    SEMANTIC = "semantic"
    LOGIC = "logic"


class Run(SQLModel, table=True):
    """실행 마스터 - 프롬프트 버전 + 데이터셋 + 프로필 조합."""

    __tablename__: ClassVar[str] = "runs"

    id: int | None = Field(default=None, primary_key=True)
    prompt_version_id: int = Field(foreign_key="prompt_versions.id", index=True)
    dataset_id: int = Field(foreign_key="datasets.id", index=True)
    profile_id: int = Field(foreign_key="evaluator_profiles.id", index=True)
    status: RunStatus = Field(default=RunStatus.RUNNING)
    user_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    guest_id: UUID | None = Field(default=None, foreign_key="guests.id", index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )


class RunResult(SQLModel, table=True):
    """실행 결과 상세 - Live Playground의 핵심 자산."""

    __tablename__: ClassVar[str] = "run_results"

    id: int | None = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="runs.id", index=True)
    dataset_row_id: int = Field(foreign_key="dataset_rows.id", index=True)

    # 실행 당시 스냅샷 (DatasetRow 수정/삭제 시에도 과거 기록 보존)
    input_snapshot: dict = Field(sa_column=Column(JSONB))
    expected_snapshot: str
    assembled_prompt: dict = Field(sa_column=Column(JSONB))

    raw_output: str

    # Layer 1: Format Check
    is_format_passed: bool = Field(default=True)
    parsed_output: dict | None = Field(default=None, sa_column=Column(JSONB))

    # Layer 2: Semantic Score
    semantic_score: float = Field(default=0.0)

    # Layer 3: Logic Results
    logic_results: dict = Field(default={}, sa_column=Column(JSONB))

    status: ResultStatus = Field(index=True)

    trace: dict | None = Field(default=None, sa_column=Column(JSONB))
