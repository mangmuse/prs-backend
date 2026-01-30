import google.generativeai as genai

from src.config import get_settings


class GeminiClient:
    """Google Gemini LLM 클라이언트."""

    def __init__(self, model: str = "gemini-2.5-flash"):
        settings = get_settings()
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다")
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model_name: str = model

    async def generate(
        self,
        system_instruction: str,
        user_message: str,
        temperature: float = 1.0,
    ) -> str:
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_instruction,
            generation_config={"temperature": temperature},
        )
        response = await model.generate_content_async(user_message)
        return response.text
