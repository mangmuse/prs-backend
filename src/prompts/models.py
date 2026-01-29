from datetime import UTC, datetime
from enum import Enum
from typing import ClassVar
from uuid import UUID

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


class OutputSchemaType(str, Enum):
    JSON_OBJECT = "JSON Object"
    JSON_ARRAY = "JSON Array"
    LABEL = "Label"
    FREEFORM = "Freeform"


class Prompt(SQLModel, table=True):
    """프롬프트 마스터 - 폴더 역할."""

    __tablename__: ClassVar[str] = "prompts"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str | None = None
    user_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    guest_id: UUID | None = Field(default=None, foreign_key="guests.id", index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )


class PromptVersion(SQLModel, table=True):
    """프롬프트 버전 - 불변성 유지, 실제 실험체."""

    __tablename__: ClassVar[str] = "prompt_versions"

    id: int | None = Field(default=None, primary_key=True)
    prompt_id: int = Field(foreign_key="prompts.id", index=True)
    version_number: int = Field(default=1)
    system_instruction: str
    user_template: str
    model: str = Field(default="gpt-4")
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    output_schema: OutputSchemaType = Field(default=OutputSchemaType.JSON_OBJECT)
    memo: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
