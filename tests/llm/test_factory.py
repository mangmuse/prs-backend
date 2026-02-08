import pytest
from unittest.mock import MagicMock, patch


class TestGetLLMClient:
    """get_llm_client 팩토리 함수 테스트."""

    def test_invalid_format_without_slash_raises_error(self):
        """'/' 없는 모델명은 ValueError를 발생시켜야 한다."""
        from src.llm.factory import get_llm_client

        with pytest.raises(ValueError, match="provider/model-name"):
            get_llm_client("gpt-4o")

    def test_unsupported_provider_raises_error(self):
        """지원하지 않는 provider는 ValueError를 발생시켜야 한다."""
        from src.llm.factory import get_llm_client

        with pytest.raises(ValueError, match="지원하지 않는 provider"):
            get_llm_client("unknown/model")

    def test_gemini_provider_returns_gemini_client(self):
        """gemini/ prefix는 GeminiClient를 반환해야 한다."""
        mock_client_class = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance

        with patch.dict(
            "src.llm.factory.PROVIDER_CLIENTS",
            {"gemini": mock_client_class},
        ):
            from src.llm.factory import get_llm_client

            client = get_llm_client("gemini/gemini-2.5-flash")
            mock_client_class.assert_called_once_with(model="gemini-2.5-flash")
            assert client is mock_client_instance

    def test_openai_provider_returns_openai_client(self):
        """openai/ prefix는 OpenAIClient를 반환해야 한다."""
        mock_client_class = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance

        with patch.dict(
            "src.llm.factory.PROVIDER_CLIENTS",
            {"openai": mock_client_class},
        ):
            from src.llm.factory import get_llm_client

            client = get_llm_client("openai/gpt-4o")
            mock_client_class.assert_called_once_with(model="gpt-4o")
            assert client is mock_client_instance

    def test_anthropic_provider_returns_anthropic_client(self):
        """anthropic/ prefix는 AnthropicClient를 반환해야 한다."""
        mock_client_class = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance

        with patch.dict(
            "src.llm.factory.PROVIDER_CLIENTS",
            {"anthropic": mock_client_class},
        ):
            from src.llm.factory import get_llm_client

            client = get_llm_client("anthropic/claude-sonnet-4")
            mock_client_class.assert_called_once_with(model="claude-sonnet-4")
            assert client is mock_client_instance
