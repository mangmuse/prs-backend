import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import ClassVar

from sqlmodel import Field, SQLModel


class OutputSchemaType(str, Enum):
    JSON_OBJECT = "json_object"
    JSON_ARRAY = "json_array"
    LABEL = "label"
    FREEFORM = "freeform"


class Prompt(SQLModel, table=True):
    __tablename__: ClassVar[str] = "prompts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True)
    description: str | None = None
    user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id", index=True)
    guest_id: uuid.UUID | None = Field(
        default=None, foreign_key="guests.id", index=True
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PromptVersion(SQLModel, table=True):
    __tablename__: ClassVar[str] = "prompt_versions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    prompt_id: uuid.UUID = Field(foreign_key="prompts.id", index=True)
    version: int = Field(default=1)
    system_instruction: str
    user_template: str
    model: str = Field(default="claude-3-sonnet")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    output_schema: OutputSchemaType = Field(default=OutputSchemaType.JSON_OBJECT)
    output_schema_definition: str | None = None
    semantic_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
