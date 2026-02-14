from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm.base import BaseLLMClient
from src.llm.gemini import GeminiClient


def test_gemini_client_inherits_base():
    """GeminiClient는 BaseLLMClient를 상속해야 한다."""
    from src.llm.gemini import GeminiClient

    assert issubclass(GeminiClient, BaseLLMClient)


class TestGeminiClient:
    """GeminiClient 단위 테스트."""

    @pytest.mark.asyncio
    async def test_generate_returns_text(self):
        """generate()가 LLM 응답 텍스트를 반환해야 한다."""
        with patch("src.llm.gemini.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(GOOGLE_API_KEY="test-key")

            with patch("src.llm.gemini.genai.Client") as mock_genai:
                mock_client = MagicMock()
                mock_genai.return_value = mock_client

                mock_aio = MagicMock()
                mock_client.aio = mock_aio

                mock_models = MagicMock()
                mock_aio.models = mock_models

                mock_response = MagicMock(text="Test response")
                mock_models.generate_content = AsyncMock(return_value=mock_response)

                from src.llm.gemini import GeminiClient

                client = GeminiClient(model="gemini-2.5-flash")
                result = await client.generate(
                    system_instruction="You are helpful.",
                    user_message="Hello",
                    temperature=0.7,
                )

                assert result == "Test response"


class TestGeminiClientWithExternalKey:
    """외부 API Key 주입 테스트."""

    def test_external_api_key_overrides_settings(self):
        """외부 api_key가 환경 설정 키를 덮어써야 한다."""
        with patch("src.llm.gemini.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(GOOGLE_API_KEY="env-key")
            with patch("src.llm.gemini.genai.Client") as mock_genai:
                GeminiClient(model="gemini-2.5-flash", api_key="user-key")
                mock_genai.assert_called_once_with(api_key="user-key")

    def test_none_api_key_falls_back_to_settings(self):
        """api_key=None이면 환경 설정 키를 사용해야 한다."""
        with patch("src.llm.gemini.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(GOOGLE_API_KEY="env-key")
            with patch("src.llm.gemini.genai.Client") as mock_genai:
                GeminiClient(model="gemini-2.5-flash", api_key=None)
                mock_genai.assert_called_once_with(api_key="env-key")


class TestGeminiClientIsTextModel:
    """Gemini 모델 필터 테스트."""

    def test_generate_content_supported(self):
        actions = ["generateContent", "countTokens"]
        assert GeminiClient._is_text_model("gemini-2.5-flash", actions) is True

    def test_generate_content_not_supported(self):
        actions = ["embedContent", "countTokens"]
        assert GeminiClient._is_text_model("gemini-2.5-flash", actions) is False

    def test_empty_actions(self):
        assert GeminiClient._is_text_model("gemini-2.5-flash", []) is False

    def test_gemma_filtered(self):
        actions = ["generateContent", "countTokens"]
        assert GeminiClient._is_text_model("gemma-3-27b-it", actions) is False

    def test_tts_filtered(self):
        actions = ["generateContent"]
        assert (
            GeminiClient._is_text_model("gemini-2.5-flash-preview-tts", actions)
            is False
        )


class TestGeminiClientListModels:
    """Gemini list_models 테스트."""

    @pytest.mark.asyncio
    async def test_returns_filtered_models(self):
        """generateContent를 지원하는 모델만 반환해야 한다."""
        with patch("src.llm.gemini.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(GOOGLE_API_KEY="test-key")

            with patch("src.llm.gemini.genai.Client") as mock_genai:
                mock_client = MagicMock()
                mock_genai.return_value = mock_client

                mock_aio = MagicMock()
                mock_client.aio = mock_aio
                mock_models = MagicMock()
                mock_aio.models = mock_models
                mock_response = MagicMock(text="Test response")
                mock_models.generate_content = AsyncMock(return_value=mock_response)

                text_model = MagicMock()
                text_model.name = "models/gemini-2.5-flash"
                text_model.display_name = "Gemini 2.5 Flash"
                text_model.supported_actions = [
                    "generateContent",
                    "countTokens",
                ]

                embed_model = MagicMock()
                embed_model.name = "models/embedding-001"
                embed_model.display_name = "Embedding 001"
                embed_model.supported_actions = ["embedContent"]

                mock_client.models.list.return_value = [text_model, embed_model]

                client = GeminiClient(model="gemini-2.5-flash")
                models = await client.list_models()

                assert len(models) == 1
                assert models[0].id == "gemini/gemini-2.5-flash"
                assert models[0].display_name == "Gemini 2.5 Flash"
                assert models[0].provider == "gemini"
