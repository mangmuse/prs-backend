from typing import Any, Protocol

from sqlalchemy import ColumnElement
from sqlmodel import col

from src.auth.models import Guest, User


class OwnedModel(Protocol):
    guest_id: Any
    user_id: Any


def get_ownership_filter(
    identity: Guest | User, model: type[OwnedModel]
) -> ColumnElement[bool]:
    """소유권 필터 조건 생성."""
    if isinstance(identity, Guest):
        return col(model.guest_id) == identity.id
    return col(model.user_id) == identity.id
