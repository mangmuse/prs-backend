from typing import Protocol


class LLMClient(Protocol):
    """LLM 클라이언트 공통 인터페이스."""

    async def generate(
        self,
        system_instruction: str,
        user_message: str,
        temperature: float = 1.0,
    ) -> str:
        """LLM 호출 후 응답 텍스트 반환."""
        ...
