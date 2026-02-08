from collections.abc import Callable

from src.llm.anthropic import AnthropicClient
from src.llm.base import BaseLLMClient, LLMClient
from src.llm.gemini import GeminiClient
from src.llm.openai import OpenAIClient

PROVIDER_CLIENTS: dict[str, Callable[..., BaseLLMClient]] = {
    "gemini": GeminiClient,
    "openai": OpenAIClient,
    "anthropic": AnthropicClient,
}


def get_llm_client(model: str) -> LLMClient:
    """
    모델명에서 provider를 추출하여 적절한 클라이언트 반환.

    Args:
        model: "provider/model-name" 형식 (예: "openai/gpt-4o")

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

    return PROVIDER_CLIENTS[provider](model=model_name)
