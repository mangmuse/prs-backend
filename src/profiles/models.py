import uuid
from datetime import UTC, datetime

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from src.common.types import LogicConstraint


class EvaluatorProfile(SQLModel, table=True):
    __tablename__ = "evaluator_profiles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True)
    description: str | None = None
    semantic_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    global_constraints: list[LogicConstraint] | None = Field(
        default=None, sa_column=Column(JSONB)
    )
    user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id", index=True)
    guest_id: uuid.UUID | None = Field(
        default=None, foreign_key="guests.id", index=True
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
