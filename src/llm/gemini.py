from google import genai
from google.genai import types

from src.config import get_settings


class GeminiClient:
    """Google Gemini LLM 클라이언트."""

    def __init__(self, model: str = "gemini-2.5-flash"):
        settings = get_settings()
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다")
        self.client: genai.Client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        self.model_name: str = model

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
        if response.text is None:
            raise ValueError("Gemini 응답이 비어 있습니다")
        return response.text
