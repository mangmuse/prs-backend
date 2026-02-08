from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm.schemas import ModelInfo


class TestListModels:
    @pytest.mark.asyncio
    async def test_excludes_provider_without_key(self):
        """API 키가 없는 프로바이더는 제외해야 한다."""
        with patch("src.llm.service.get_settings") as mock_settings:
            settings = MagicMock()
            settings.OPENAI_API_KEY = "test-openai-key"
            settings.ANTHROPIC_API_KEY = None
            settings.GOOGLE_API_KEY = None
            mock_settings.return_value = settings

            with patch("src.llm.service.OpenAIClient") as mock_openai_cls:
                mock_client = MagicMock()
                mock_openai_cls.return_value = mock_client
                mock_client.list_models = AsyncMock(
                    return_value=[
                        ModelInfo(
                            id="openai/gpt-4o", display_name="gpt-4o", provider="openai"
                        )
                    ]
                )

                from src.llm.service import list_models

                response = await list_models()

                mock_openai_cls.assert_called_once()
                assert len(response.models) == 1
                assert response.models[0].provider == "openai"

    @pytest.mark.asyncio
    async def test_aggregates_all_providers(self):
        """모든 프로바이더의 모델을 합쳐서 반환해야 한다."""
        with patch("src.llm.service.get_settings") as mock_settings:
            settings = MagicMock()
            settings.OPENAI_API_KEY = "openai-key"
            settings.ANTHROPIC_API_KEY = "anthropic-key"
            settings.GOOGLE_API_KEY = "google-key"
            mock_settings.return_value = settings

            with (
                patch("src.llm.service.OpenAIClient") as mock_openai_cls,
                patch("src.llm.service.AnthropicClient") as mock_anthropic_cls,
                patch("src.llm.service.GeminiClient") as mock_gemini_cls,
            ):
                mock_openai = MagicMock()
                mock_openai_cls.return_value = mock_openai
                mock_openai.list_models = AsyncMock(
                    return_value=[
                        ModelInfo(
                            id="openai/gpt-4o", display_name="gpt-4o", provider="openai"
                        )
                    ]
                )

                mock_anthropic = MagicMock()
                mock_anthropic_cls.return_value = mock_anthropic
                mock_anthropic.list_models = AsyncMock(
                    return_value=[
                        ModelInfo(
                            id="anthropic/claude-sonnet-4",
                            display_name="Claude Sonnet 4",
                            provider="anthropic",
                        )
                    ]
                )

                mock_gemini = MagicMock()
                mock_gemini_cls.return_value = mock_gemini
                mock_gemini.list_models = AsyncMock(
                    return_value=[
                        ModelInfo(
                            id="gemini/gemini-2.5-flash",
                            display_name="Gemini 2.5 Flash",
                            provider="gemini",
                        )
                    ]
                )

                from src.llm.service import list_models

                response = await list_models()

                assert len(response.models) == 3

    @pytest.mark.asyncio
    async def test_continues_on_provider_failure(self):
        """한 프로바이더 실패 시 다른 프로바이더는 계속 처리해야 한다."""
        with patch("src.llm.service.get_settings") as mock_settings:
            settings = MagicMock()
            settings.OPENAI_API_KEY = "openai-key"
            settings.ANTHROPIC_API_KEY = "anthropic-key"
            settings.GOOGLE_API_KEY = None
            mock_settings.return_value = settings

            with (
                patch("src.llm.service.OpenAIClient") as mock_openai_cls,
                patch("src.llm.service.AnthropicClient") as mock_anthropic_cls,
            ):
                mock_openai = MagicMock()
                mock_openai_cls.return_value = mock_openai
                mock_openai.list_models = AsyncMock(
                    side_effect=Exception("OpenAI API Error")
                )

                mock_anthropic = MagicMock()
                mock_anthropic_cls.return_value = mock_anthropic
                mock_anthropic.list_models = AsyncMock(
                    return_value=[
                        ModelInfo(
                            id="anthropic/claude-sonnet-4",
                            display_name="Claude Sonnet 4",
                            provider="anthropic",
                        )
                    ]
                )

                from src.llm.service import list_models

                response = await list_models()

                assert len(response.models) == 1
                assert response.models[0].provider == "anthropic"
