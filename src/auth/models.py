import uuid
from datetime import UTC, datetime
from typing import ClassVar

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """회원 모델 - 구글 소셜 로그인 기반."""

    __tablename__: ClassVar[str] = "users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    provider: str = Field(default="google")
    provider_id: str = Field(unique=True, index=True)
    name: str | None = None
    picture_url: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )


class Guest(SQLModel, table=True):
    """게스트 모델 - 로그인 없이 사용."""

    __tablename__: ClassVar[str] = "guests"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
