from datetime import datetime

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from src.common.schemas import CamelCaseModel
from src.common.types import LogicConstraint


class CreateProfileRequest(CamelCaseModel):
    name: str
    description: str | None = None
    semantic_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    global_constraints: list[LogicConstraint] | None = None


class UpdateProfileRequest(CamelCaseModel):
    name: str | None = None
    description: str | None = None
    semantic_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    global_constraints: list[LogicConstraint] | None = None


class ProfileResponse(CamelCaseModel):
    id: int
    name: str
    description: str | None
    semantic_threshold: float
    global_constraints: list[LogicConstraint] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )


class ProfileSummary(CamelCaseModel):
    id: int
    name: str
    description: str | None
    semantic_threshold: float
    constraint_count: int
    created_at: datetime
