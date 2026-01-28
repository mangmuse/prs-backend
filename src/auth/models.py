import uuid
from datetime import UTC, datetime
from typing import ClassVar

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__: ClassVar[str] = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )


class Guest(SQLModel, table=True):
    __tablename__: ClassVar[str] = "guests"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_token: str = Field(unique=True, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True)))
