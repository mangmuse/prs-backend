from typing import override

from openai import AsyncOpenAI

from src.config import get_settings
from src.llm.base import BaseLLMClient
from src.llm.schemas import ModelInfo


class OpenAIClient(BaseLLMClient):
    """OpenAI LLM 클라이언트."""

    EXCLUDE_PATTERNS = [
        "ft:",
        "text-embedding",
        "whisper",
        "tts",
        "dall-e",
        "davinci",
        "babbage",
        "gpt-3.5-turbo-instruct",
        "realtime",
        "audio",
        "moderation",
        "image",
        "sora",
        "codex",
        "transcribe",
        "search",
    ]

    def __init__(self, model: str = "gpt-4o", api_key: str | None = None):
        settings = get_settings()
        resolved_key = api_key or settings.OPENAI_API_KEY
        super().__init__(
            api_key=resolved_key,
            key_name="OPENAI_API_KEY",
            model=model,
        )
        self.client = AsyncOpenAI(api_key=resolved_key)

    @override
    async def generate(
        self,
        system_instruction: str,
        user_message: str,
        temperature: float = 1.0,
    ) -> str:
        response = await self.client.responses.create(
            model=self.model_name,
            instructions=system_instruction,
            input=user_message,
            temperature=temperature,
        )
        content = response.output_text
        return self._ensure_response(content if content else None, "OpenAI")

    @staticmethod
    def _is_text_model(model_id: str) -> bool:
        """텍스트 생성용 모델인지 판단."""
        model_lower = model_id.lower()
        if any(p in model_lower for p in OpenAIClient.EXCLUDE_PATTERNS):
            return False
        return not (model_lower.endswith("-pro") or "-pro-" in model_lower)

    @override
    async def list_models(self) -> list[ModelInfo]:
        """텍스트 생성용 모델 목록 조회 (최신순 정렬)."""
        response = await self.client.models.list()
        filtered = [m for m in response.data if self._is_text_model(m.id)]
        sorted_models = sorted(filtered, key=lambda m: m.created, reverse=True)
        return [
            ModelInfo(id=f"openai/{m.id}", display_name=m.id, provider="openai")
            for m in sorted_models
        ]
