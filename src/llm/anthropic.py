from anthropic import AsyncAnthropic
from anthropic.types import TextBlock

from src.config import get_settings
from src.llm.base import BaseLLMClient
from src.llm.schemas import ModelInfo


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude LLM 클라이언트."""

    def __init__(self, model: str = "claude-sonnet-4-20250514", api_key: str | None = None):
        settings = get_settings()
        resolved_key = api_key or settings.ANTHROPIC_API_KEY
        super().__init__(
            api_key=resolved_key,
            key_name="ANTHROPIC_API_KEY",
            model=model,
        )
        self.client = AsyncAnthropic(api_key=resolved_key)

    async def generate(
        self,
        system_instruction: str,
        user_message: str,
        temperature: float = 1.0,
    ) -> str:
        response = await self.client.messages.create(
            model=self.model_name,
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": system_instruction,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
            temperature=temperature,
        )
        block = response.content[0] if response.content else None
        text = block.text if isinstance(block, TextBlock) else None
        return self._ensure_response(text, "Anthropic")

    async def list_models(self) -> list[ModelInfo]:
        """모델 목록 조회."""
        response = await self.client.models.list()
        return [
            ModelInfo(
                id=f"anthropic/{m.id}",
                display_name=m.display_name,
                provider="anthropic",
            )
            for m in response.data
        ]
