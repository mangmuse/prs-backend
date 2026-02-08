from google import genai
from google.genai import types

from src.config import get_settings
from src.llm.base import BaseLLMClient
from src.llm.schemas import ModelInfo


class GeminiClient(BaseLLMClient):
    """Google Gemini LLM 클라이언트."""

    EXCLUDE_PATTERNS = [
        "gemma",
        "tts",
        "computer-use",
        "deep-research",
        "image",
        "robotics",
        "nano-banana",
    ]

    def __init__(self, model: str = "gemini-2.5-flash", api_key: str | None = None):
        settings = get_settings()
        resolved_key = api_key or settings.GOOGLE_API_KEY
        super().__init__(
            api_key=resolved_key,
            key_name="GOOGLE_API_KEY",
            model=model,
        )
        self.client: genai.Client = genai.Client(api_key=resolved_key)

    async def generate(
        self,
        system_instruction: str,
        user_message: str,
        temperature: float = 1.0,
    ) -> str:
        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
            ),
        )
        return self._ensure_response(response.text, "Gemini")

    @staticmethod
    def _is_text_model(model_id: str, supported_actions: list[str]) -> bool:
        """텍스트 생성용 모델인지 판단."""
        if "generateContent" not in supported_actions:
            return False
        model_lower = model_id.lower()
        return not any(p in model_lower for p in GeminiClient.EXCLUDE_PATTERNS)

    def list_models_sync(self) -> list[ModelInfo]:
        """모델 목록 조회 (동기)."""
        response = self.client.models.list()
        models: list[ModelInfo] = []
        for m in response:
            name = m.name or ""
            model_id = name.replace("models/", "")
            actions = getattr(m, "supported_actions", []) or []
            if not self._is_text_model(model_id, actions):
                continue
            models.append(
                ModelInfo(
                    id=f"gemini/{model_id}",
                    display_name=m.display_name or model_id,
                    provider="gemini",
                )
            )
        return models

    async def list_models(self) -> list[ModelInfo]:
        """모델 목록 조회 (async wrapper)."""
        return self.list_models_sync()
