import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.llm.base import BaseLLMClient
from src.llm.openai import OpenAIClient


def test_openai_client_inherits_base():
    """OpenAIClient는 BaseLLMClient를 상속해야 한다."""
    from src.llm.openai import OpenAIClient

    assert issubclass(OpenAIClient, BaseLLMClient)


class TestOpenAIClient:
    """OpenAIClient 단위 테스트."""

    @pytest.mark.asyncio
    async def test_generate_returns_text(self):
        """generate()가 LLM 응답 텍스트를 반환해야 한다."""
        with patch("src.llm.openai.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(OPENAI_API_KEY="test-key")

            with patch("src.llm.openai.AsyncOpenAI") as mock_openai:
                mock_client = AsyncMock()
                mock_openai.return_value = mock_client

                mock_response = MagicMock()
                mock_response.output_text = "테스트 응답"
                mock_client.responses.create.return_value = mock_response

                from src.llm.openai import OpenAIClient

                client = OpenAIClient(model="gpt-4o")
                result = await client.generate(
                    system_instruction="당신은 도움이 되는 어시스턴트입니다.",
                    user_message="안녕하세요",
                    temperature=0.7,
                )

                assert result == "테스트 응답"

    @pytest.mark.asyncio
    async def test_generate_raises_on_empty_response(self):
        """빈 응답 시 에러를 발생시켜야 한다."""
        with patch("src.llm.openai.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(OPENAI_API_KEY="test-key")

            with patch("src.llm.openai.AsyncOpenAI") as mock_openai:
                mock_client = AsyncMock()
                mock_openai.return_value = mock_client

                mock_response = MagicMock()
                mock_response.output_text = ""
                mock_client.responses.create.return_value = mock_response

                from src.llm.openai import OpenAIClient

                client = OpenAIClient(model="gpt-4o")

                with pytest.raises(ValueError, match="OpenAI 응답이 비어 있습니다"):
                    await client.generate(
                        system_instruction="당신은 도움이 되는 어시스턴트입니다.",
                        user_message="안녕하세요",
                        temperature=0.7,
                    )


class TestOpenAIClientIsTextModel:
    """OpenAI 모델 필터 테스트."""

    def test_gpt4o_is_text_model(self):
        assert OpenAIClient._is_text_model("gpt-4o") is True

    def test_gpt4o_mini_is_text_model(self):
        assert OpenAIClient._is_text_model("gpt-4o-mini") is True

    def test_o1_is_text_model(self):
        assert OpenAIClient._is_text_model("o1") is True

    def test_embedding_model_filtered(self):
        assert OpenAIClient._is_text_model("text-embedding-3-large") is False

    def test_fine_tuned_model_filtered(self):
        assert OpenAIClient._is_text_model("ft:gpt-4o:org:custom") is False

    def test_whisper_filtered(self):
        assert OpenAIClient._is_text_model("whisper-1") is False

    def test_tts_filtered(self):
        assert OpenAIClient._is_text_model("tts-1") is False

    def test_dalle_filtered(self):
        assert OpenAIClient._is_text_model("dall-e-3") is False

    def test_realtime_filtered(self):
        assert OpenAIClient._is_text_model("gpt-4o-realtime-preview") is False

    def test_audio_filtered(self):
        assert OpenAIClient._is_text_model("gpt-4o-audio-preview") is False

    def test_moderation_filtered(self):
        assert OpenAIClient._is_text_model("omni-moderation-latest") is False

    def test_pro_model_filtered(self):
        assert OpenAIClient._is_text_model("gpt-5-pro") is False

    def test_pro_model_with_date_filtered(self):
        assert OpenAIClient._is_text_model("o1-pro-2025-03-19") is False


class TestOpenAIClientWithExternalKey:
    """외부 API Key 주입 테스트."""

    def test_external_api_key_overrides_settings(self):
        """외부 api_key가 환경 설정 키를 덮어써야 한다."""
        with patch("src.llm.openai.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(OPENAI_API_KEY="env-key")
            with patch("src.llm.openai.AsyncOpenAI") as mock_openai:
                OpenAIClient(model="gpt-4o", api_key="user-key")
                mock_openai.assert_called_once_with(api_key="user-key")

    def test_none_api_key_falls_back_to_settings(self):
        """api_key=None이면 환경 설정 키를 사용해야 한다."""
        with patch("src.llm.openai.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(OPENAI_API_KEY="env-key")
            with patch("src.llm.openai.AsyncOpenAI") as mock_openai:
                OpenAIClient(model="gpt-4o", api_key=None)
                mock_openai.assert_called_once_with(api_key="env-key")


class TestOpenAIClientListModels:
    """OpenAI list_models 테스트."""

    @pytest.mark.asyncio
    async def test_returns_filtered_models(self):
        """텍스트 생성용 모델만 반환해야 한다."""
        with patch("src.llm.openai.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(OPENAI_API_KEY="test-key")

            with patch("src.llm.openai.AsyncOpenAI") as mock_openai:
                mock_client = AsyncMock()
                mock_openai.return_value = mock_client

                mock_client.models.list = AsyncMock(
                    return_value=MagicMock(
                        data=[
                            MagicMock(id="gpt-4o"),
                            MagicMock(id="text-embedding-3-large"),
                        ]
                    )
                )

                client = OpenAIClient(model="gpt-4o")
                models = await client.list_models()

                assert len(models) == 1
                assert models[0].id == "openai/gpt-4o"
                assert models[0].provider == "openai"

    @pytest.mark.asyncio
    async def test_all_filtered_returns_empty(self):
        """모든 모델이 필터링되면 빈 리스트를 반환해야 한다."""
        with patch("src.llm.openai.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(OPENAI_API_KEY="test-key")

            with patch("src.llm.openai.AsyncOpenAI") as mock_openai:
                mock_client = AsyncMock()
                mock_openai.return_value = mock_client

                mock_client.models.list = AsyncMock(
                    return_value=MagicMock(
                        data=[
                            MagicMock(id="text-embedding-3-large"),
                            MagicMock(id="whisper-1"),
                        ]
                    )
                )

                client = OpenAIClient(model="gpt-4o")
                models = await client.list_models()

                assert len(models) == 0
