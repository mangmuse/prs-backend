from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestVerifyApiKey:
    """verify_api_key 서비스 함수 테스트."""

    @pytest.mark.asyncio
    async def test_valid_key_returns_true(self):
        """유효한 키는 valid=True를 반환해야 한다."""
        mock_client = AsyncMock()
        mock_client.list_models.return_value = [MagicMock()]
        mock_client_class = MagicMock(return_value=mock_client)

        with patch.dict(
            "src.llm.factory.PROVIDER_CLIENTS", {"openai": mock_client_class}
        ):
            from src.llm.service import verify_api_key

            result = await verify_api_key("openai", "valid-key")
            assert result.valid is True
            assert result.error is None

    @pytest.mark.asyncio
    async def test_invalid_key_returns_false(self):
        """유효하지 않은 키는 valid=False를 반환해야 한다."""
        mock_client = AsyncMock()
        mock_client.list_models.side_effect = Exception("Invalid API key")
        mock_client_class = MagicMock(return_value=mock_client)

        with patch.dict(
            "src.llm.factory.PROVIDER_CLIENTS", {"openai": mock_client_class}
        ):
            from src.llm.service import verify_api_key

            result = await verify_api_key("openai", "invalid-key")
            assert result.valid is False
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_error_message_does_not_leak_key(self):
        """에러 메시지에 API Key가 노출되지 않아야 한다."""
        mock_client = AsyncMock()
        mock_client.list_models.side_effect = Exception(
            "Invalid API key: sk-abc123def456"
        )
        mock_client_class = MagicMock(return_value=mock_client)

        with patch.dict(
            "src.llm.factory.PROVIDER_CLIENTS", {"openai": mock_client_class}
        ):
            from src.llm.service import verify_api_key

            result = await verify_api_key("openai", "sk-abc123def456")
            assert result.valid is False
            assert "sk-abc123def456" not in (result.error or "")

    @pytest.mark.asyncio
    async def test_unsupported_provider_returns_false(self):
        """지원하지 않는 provider는 valid=False를 반환해야 한다."""
        from src.llm.service import verify_api_key

        result = await verify_api_key("unknown", "some-key")
        assert result.valid is False
        assert "지원하지 않는 provider" in (result.error or "")
