"""LLM 관련 API 엔드포인트."""

from fastapi import APIRouter

from src.llm import service
from src.llm.schemas import ModelsResponse

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/models", response_model=ModelsResponse)
async def get_models() -> ModelsResponse:
    """사용 가능한 LLM 모델 목록 조회."""
    return await service.list_models()
