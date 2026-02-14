from unittest.mock import MagicMock, patch

import pytest


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

        with (
            patch.dict(
                "src.llm.factory.PROVIDER_CLIENTS",
                {"gemini": mock_client_class},
            ),
            patch("src.llm.factory.resolve_api_key", return_value="resolved-key"),
        ):
            from src.llm.factory import get_llm_client

            client = get_llm_client("gemini/gemini-2.5-flash")
            mock_client_class.assert_called_once_with(
                model="gemini-2.5-flash", api_key="resolved-key"
            )
            assert client is mock_client_instance

    def test_openai_provider_returns_openai_client(self):
        """openai/ prefix는 OpenAIClient를 반환해야 한다."""
        mock_client_class = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance

        with (
            patch.dict(
                "src.llm.factory.PROVIDER_CLIENTS",
                {"openai": mock_client_class},
            ),
            patch("src.llm.factory.resolve_api_key", return_value="resolved-key"),
        ):
            from src.llm.factory import get_llm_client

            client = get_llm_client("openai/gpt-4o")
            mock_client_class.assert_called_once_with(
                model="gpt-4o", api_key="resolved-key"
            )
            assert client is mock_client_instance

    def test_anthropic_provider_returns_anthropic_client(self):
        """anthropic/ prefix는 AnthropicClient를 반환해야 한다."""
        mock_client_class = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance

        with (
            patch.dict(
                "src.llm.factory.PROVIDER_CLIENTS",
                {"anthropic": mock_client_class},
            ),
            patch("src.llm.factory.resolve_api_key", return_value="resolved-key"),
        ):
            from src.llm.factory import get_llm_client

            client = get_llm_client("anthropic/claude-sonnet-4")
            mock_client_class.assert_called_once_with(
                model="claude-sonnet-4", api_key="resolved-key"
            )
            assert client is mock_client_instance


class TestGetLLMClientWithApiKey:
    """get_llm_client에 api_key 파라미터 전달 테스트."""

    def test_api_key_is_passed_to_resolve(self):
        """외부 api_key가 resolve_api_key에 전달되어야 한다."""
        mock_client_class = MagicMock()
        with (
            patch.dict(
                "src.llm.factory.PROVIDER_CLIENTS",
                {"openai": mock_client_class},
            ),
            patch(
                "src.llm.factory.resolve_api_key", return_value="sk-test-key"
            ) as mock_resolve,
        ):
            from src.llm.factory import get_llm_client

            get_llm_client("openai/gpt-4o", api_key="sk-test-key")
            mock_resolve.assert_called_once_with("openai", "sk-test-key")
            mock_client_class.assert_called_once_with(
                model="gpt-4o", api_key="sk-test-key"
            )

    def test_api_key_none_calls_resolve_with_none(self):
        """api_key 미지정 시 resolve_api_key에 None이 전달되어야 한다."""
        mock_client_class = MagicMock()
        with (
            patch.dict(
                "src.llm.factory.PROVIDER_CLIENTS",
                {"openai": mock_client_class},
            ),
            patch(
                "src.llm.factory.resolve_api_key", return_value="env-key"
            ) as mock_resolve,
        ):
            from src.llm.factory import get_llm_client

            get_llm_client("openai/gpt-4o")
            mock_resolve.assert_called_once_with("openai", None)


class TestResolveApiKey:
    """resolve_api_key 환경별 폴백 로직 테스트."""

    def test_returns_user_key_when_provided(self):
        """사용자 키가 주어지면 그대로 반환해야 한다."""
        from src.llm.factory import resolve_api_key

        result = resolve_api_key("openai", "user-key")
        assert result == "user-key"

    def test_falls_back_to_env_in_debug_mode(self):
        """DEBUG 모드에서 사용자 키가 없으면 환경 키를 사용해야 한다."""
        from src.llm.factory import resolve_api_key

        with patch("src.llm.factory.get_settings") as mock:
            mock.return_value = MagicMock(DEBUG=True, OPENAI_API_KEY="env-key")
            result = resolve_api_key("openai", None)
            assert result == "env-key"

    def test_raises_in_production_without_key(self):
        """프로덕션에서 사용자 키가 없으면 에러가 발생해야 한다."""
        from src.llm.factory import resolve_api_key

        with patch("src.llm.factory.get_settings") as mock:
            mock.return_value = MagicMock(DEBUG=False, OPENAI_API_KEY="env-key")
            with pytest.raises(ValueError, match="API Key가 필요합니다"):
                resolve_api_key("openai", None)

    def test_raises_in_debug_without_any_key(self):
        """DEBUG 모드에서도 환경 키가 없으면 에러가 발생해야 한다."""
        from src.llm.factory import resolve_api_key

        with patch("src.llm.factory.get_settings") as mock:
            mock.return_value = MagicMock(DEBUG=True, OPENAI_API_KEY=None)
            with pytest.raises(ValueError, match="API Key가 필요합니다"):
                resolve_api_key("openai", None)

    def test_anthropic_provider_key_mapping(self):
        """anthropic provider는 ANTHROPIC_API_KEY를 참조해야 한다."""
        from src.llm.factory import resolve_api_key

        with patch("src.llm.factory.get_settings") as mock:
            mock.return_value = MagicMock(DEBUG=True, ANTHROPIC_API_KEY="anth-key")
            result = resolve_api_key("anthropic", None)
            assert result == "anth-key"

    def test_gemini_provider_key_mapping(self):
        """gemini provider는 GOOGLE_API_KEY를 참조해야 한다."""
        from src.llm.factory import resolve_api_key

        with patch("src.llm.factory.get_settings") as mock:
            mock.return_value = MagicMock(DEBUG=True, GOOGLE_API_KEY="google-key")
            result = resolve_api_key("gemini", None)
            assert result == "google-key"
