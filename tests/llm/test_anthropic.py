import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from anthropic.types import TextBlock

from src.llm.base import BaseLLMClient


def test_anthropic_client_inherits_base():
    """AnthropicClient는 BaseLLMClient를 상속해야 한다."""
    from src.llm.anthropic import AnthropicClient

    assert issubclass(AnthropicClient, BaseLLMClient)


class TestAnthropicClient:
    """AnthropicClient 단위 테스트."""

    @pytest.mark.asyncio
    async def test_generate_returns_text(self):
        """generate()가 LLM 응답 텍스트를 반환해야 한다."""
        with patch("src.llm.anthropic.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(ANTHROPIC_API_KEY="test-key")

            with patch("src.llm.anthropic.AsyncAnthropic") as mock_anthropic:
                mock_client = AsyncMock()
                mock_anthropic.return_value = mock_client
                mock_client.messages.create.return_value = MagicMock(
                    content=[TextBlock(type="text", text="Test response")]
                )

                from src.llm.anthropic import AnthropicClient

                client = AnthropicClient(model="claude-sonnet-4")
                result = await client.generate(
                    system_instruction="You are helpful.",
                    user_message="Hello",
                    temperature=0.7,
                )

                assert result == "Test response"


class TestAnthropicClientListModels:
    """Anthropic list_models 테스트."""

    @pytest.mark.asyncio
    async def test_returns_all_models(self):
        """Anthropic 모델은 필터 없이 모두 반환해야 한다."""
        with patch("src.llm.anthropic.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(ANTHROPIC_API_KEY="test-key")

            with patch("src.llm.anthropic.AsyncAnthropic") as mock_anthropic:
                mock_client = AsyncMock()
                mock_anthropic.return_value = mock_client

                mock_client.models.list = AsyncMock(
                    return_value=MagicMock(
                        data=[
                            MagicMock(
                                id="claude-sonnet-4-20250514",
                                display_name="Claude Sonnet 4",
                            ),
                            MagicMock(
                                id="claude-opus-4-20250514",
                                display_name="Claude Opus 4",
                            ),
                        ]
                    )
                )

                from src.llm.anthropic import AnthropicClient

                client = AnthropicClient(model="claude-sonnet-4")
                models = await client.list_models()

                assert len(models) == 2
                assert models[0].id == "anthropic/claude-sonnet-4-20250514"
                assert models[0].display_name == "Claude Sonnet 4"
                assert models[0].provider == "anthropic"
