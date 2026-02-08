"""LLM 관련 API 엔드포인트."""

from fastapi import APIRouter, Depends, HTTPException

from src.auth.dependencies import get_current_identity
from src.auth.models import Guest, User
from src.llm import service
from src.llm.schemas import ModelsResponse, VerifyKeyRequest, VerifyKeyResponse
from src.llm.security import verify_key_limiter

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/models", response_model=ModelsResponse)
async def get_models() -> ModelsResponse:
    """사용 가능한 LLM 모델 목록 조회."""
    return await service.list_models()


@router.post("/verify-key", response_model=VerifyKeyResponse)
async def verify_key(
    data: VerifyKeyRequest,
    identity: Guest | User = Depends(get_current_identity),
) -> VerifyKeyResponse:
    """API Key 유효성 검증."""
    rate_key = str(identity.id)
    if not verify_key_limiter.is_allowed(rate_key):
        raise HTTPException(
            status_code=429,
            detail="요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
        )
    return await service.verify_api_key(data.provider, data.api_key)
