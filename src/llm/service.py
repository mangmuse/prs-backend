"""LLM 모델 목록 조회 및 키 검증 서비스."""

import logging

from src.config import get_settings
from src.llm.anthropic import AnthropicClient
from src.llm.factory import PROVIDER_CLIENTS
from src.llm.gemini import GeminiClient
from src.llm.openai import OpenAIClient
from src.llm.schemas import ModelInfo, ModelsResponse, VerifyKeyResponse
from src.llm.security import sanitize_error_message

logger = logging.getLogger(__name__)


async def list_models() -> ModelsResponse:
    """모든 프로바이더의 사용 가능한 모델 목록 조회."""
    settings = get_settings()
    all_models: list[ModelInfo] = []

    if settings.OPENAI_API_KEY:
        try:
            openai_client = OpenAIClient()
            models = await openai_client.list_models()
            all_models.extend(models)
        except Exception as e:
            logger.warning("OpenAI 모델 조회 실패: %s", sanitize_error_message(str(e)))

    if settings.ANTHROPIC_API_KEY:
        try:
            anthropic_client = AnthropicClient()
            models = await anthropic_client.list_models()
            all_models.extend(models)
        except Exception as e:
            logger.warning(
                "Anthropic 모델 조회 실패: %s", sanitize_error_message(str(e))
            )

    if settings.GOOGLE_API_KEY:
        try:
            gemini_client = GeminiClient()
            models = await gemini_client.list_models()
            all_models.extend(models)
        except Exception as e:
            logger.warning("Gemini 모델 조회 실패: %s", sanitize_error_message(str(e)))

    return ModelsResponse(models=all_models)


async def verify_api_key(provider: str, api_key: str) -> VerifyKeyResponse:
    """API Key 유효성 검증."""
    if provider not in PROVIDER_CLIENTS:
        return VerifyKeyResponse(
            valid=False, error=f"지원하지 않는 provider: {provider}"
        )

    try:
        client = PROVIDER_CLIENTS[provider](model="dummy", api_key=api_key)
        _ = await client.list_models()
        return VerifyKeyResponse(valid=True)
    except Exception:
        return VerifyKeyResponse(valid=False, error="API Key가 유효하지 않습니다")
