import uuid
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Guest(SQLModel, table=True):
    __tablename__ = "guests"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_token: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime
