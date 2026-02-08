from sqlalchemy import or_
from sqlmodel import SQLModel, col

from src.auth.models import Guest, User


def get_ownership_filter[T: SQLModel](identity: Guest | User, model: type[T]):
    """소유권 필터 조건 생성."""
    if isinstance(identity, Guest):
        return col(model.guest_id) == identity.id
    return or_(
        col(model.user_id) == identity.id,
        col(model.guest_id) == identity.id,
    )
