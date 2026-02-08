from collections.abc import Callable

from src.config import get_settings
from src.llm.anthropic import AnthropicClient
from src.llm.base import BaseLLMClient, LLMClient
from src.llm.gemini import GeminiClient
from src.llm.openai import OpenAIClient

PROVIDER_CLIENTS: dict[str, Callable[..., BaseLLMClient]] = {
    "gemini": GeminiClient,
    "openai": OpenAIClient,
    "anthropic": AnthropicClient,
}

_PROVIDER_KEY_MAP = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GOOGLE_API_KEY",
}


def _resolve_api_key(provider: str, api_key: str | None) -> str:
    """provider별 API Key 해석: 사용자 키 > DEBUG 환경 키 > 에러."""
    if api_key:
        return api_key

    settings = get_settings()
    if settings.DEBUG:
        key_name = _PROVIDER_KEY_MAP.get(provider, "")
        env_key = getattr(settings, key_name, None) if key_name else None
        if env_key:
            return env_key

    raise ValueError(
        f"{provider} API Key가 필요합니다. Settings에서 입력해주세요."
    )


def get_llm_client(model: str, api_key: str | None = None) -> LLMClient:
    """
    모델명에서 provider를 추출하여 적절한 클라이언트 반환.

    Args:
        model: "provider/model-name" 형식 (예: "openai/gpt-4o")
        api_key: 외부에서 주입하는 API Key (None이면 환경 설정 사용)

    Raises:
        ValueError: provider가 없거나 지원하지 않는 경우
    """
    if "/" not in model:
        raise ValueError(
            f"모델명은 'provider/model-name' 형식이어야 합니다: {model}"
        )

    provider, model_name = model.split("/", 1)

    if provider not in PROVIDER_CLIENTS:
        supported = ", ".join(PROVIDER_CLIENTS.keys())
        raise ValueError(
            f"지원하지 않는 provider: {provider}. 지원 목록: {supported}"
        )

    resolved_key = _resolve_api_key(provider, api_key)
    return PROVIDER_CLIENTS[provider](model=model_name, api_key=resolved_key)
