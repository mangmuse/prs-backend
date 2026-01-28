from datetime import UTC, datetime
from typing import ClassVar
from uuid import UUID

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from src.common.types import LogicConstraint


class EvaluatorProfile(SQLModel, table=True):
    """평가 프로필 - 채점 기준 설정."""

    __tablename__: ClassVar[str] = "evaluator_profiles"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str | None = None
    semantic_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    global_constraints: list[LogicConstraint] | None = Field(
        default=None, sa_column=Column(JSONB)
    )
    user_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    guest_id: UUID | None = Field(default=None, foreign_key="guests.id", index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
