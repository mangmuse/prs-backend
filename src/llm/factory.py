from src.llm.base import LLMClient
from src.llm.gemini import GeminiClient


def get_llm_client(model: str) -> LLMClient:
    """모델명에 따라 적절한 LLM 클라이언트 반환."""
    if model.startswith("gemini"):
        return GeminiClient(model=model)
    else:
        raise ValueError(f"지원하지 않는 모델: {model}")
