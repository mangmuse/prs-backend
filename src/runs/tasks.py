import logging

from src.runs import service

logger = logging.getLogger(__name__)


async def process_run_task(run_id: int) -> None:
    """BackgroundTask에서 Run 처리.

    Service의 execute_run을 호출하는 얇은 래퍼.
    """
    logger.info("Run 태스크 시작 | run_id=%d", run_id)
    await service.execute_run(run_id)
    logger.info("Run 태스크 완료 | run_id=%d", run_id)
