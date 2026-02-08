from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.llm.schemas import ModelInfo


class LLMClient(Protocol):
    """LLM 클라이언트 공통 인터페이스 (타입 힌트용)."""

    async def generate(
        self,
        system_instruction: str,
        user_message: str,
        temperature: float = 1.0,
    ) -> str:
        """LLM 호출 후 응답 텍스트 반환."""
        ...


class BaseLLMClient(ABC):
    """LLM 클라이언트 추상 기반 클래스."""

    def __init__(self, api_key: str | None, key_name: str, model: str):
        if not api_key:
            raise ValueError(f"{key_name}가 설정되지 않았습니다")
        self.model_name = model

    @abstractmethod
    async def generate(
        self,
        system_instruction: str,
        user_message: str,
        temperature: float = 1.0,
    ) -> str:
        """LLM 호출 후 응답 텍스트 반환."""
        ...

    def _ensure_response(self, content: str | None, provider: str) -> str:
        """응답이 비어있으면 에러 발생."""
        if content is None:
            raise ValueError(f"{provider} 응답이 비어 있습니다")
        return content

    @abstractmethod
    async def list_models(self) -> list["ModelInfo"]:
        """해당 프로바이더의 텍스트 생성용 모델 목록 조회."""
        ...
