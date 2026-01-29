from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.common.types import LogicConstraint


class CreateProfileRequest(BaseModel):
    name: str
    description: str | None = None
    semantic_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    global_constraints: list[LogicConstraint] | None = None


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    semantic_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    global_constraints: list[LogicConstraint] | None = None


class ProfileResponse(BaseModel):
    id: int
    name: str
    description: str | None
    semantic_threshold: float
    global_constraints: list[LogicConstraint] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProfileSummary(BaseModel):
    id: int
    name: str
    description: str | None
    semantic_threshold: float
    constraint_count: int
    created_at: datetime
