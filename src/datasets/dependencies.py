from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.auth.models import Guest, User
from src.common.exceptions import ForbiddenError, NotFoundError
from src.datasets.models import Dataset


async def get_user_dataset(
    dataset_id: int,
    identity: Guest | User,
    session: AsyncSession,
) -> Dataset:
    """데이터셋 조회 및 소유권 검증."""
    result = await session.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()

    if not dataset:
        raise NotFoundError(f"Dataset {dataset_id} not found")

    if isinstance(identity, Guest):
        if dataset.guest_id != identity.id:
            raise ForbiddenError("Access denied")
    else:
        if dataset.user_id != identity.id:
            raise ForbiddenError("Access denied")

    return dataset
