from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.auth.models import Guest, User
from src.common.exceptions import ForbiddenError, NotFoundError
from src.runs.models import Run


async def get_user_run(
    run_id: int,
    identity: Guest | User,
    session: AsyncSession,
) -> Run:
    """Run 조회 및 소유권 검증."""
    result = await session.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()

    if not run:
        raise NotFoundError(f"Run {run_id}를 찾을 수 없습니다")

    if isinstance(identity, Guest):
        if run.guest_id != identity.id:
            raise ForbiddenError("접근 권한이 없습니다")
    else:
        if run.user_id != identity.id:
            raise ForbiddenError("접근 권한이 없습니다")

    return run
