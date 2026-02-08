import pytest

from src.llm.base import BaseLLMClient
from src.llm.schemas import ModelInfo


class TestBaseLLMClient:
    """BaseLLMClient ABC 테스트."""

    def test_init_without_api_key_raises_error(self):
        """API 키가 없으면 ValueError를 발생시켜야 한다."""

        class TestClient(BaseLLMClient):
            async def generate(
                self,
                system_instruction: str,
                user_message: str,
                temperature: float = 1.0,
            ) -> str:
                return "test"

            async def list_models(self) -> list[ModelInfo]:
                return []

        with pytest.raises(ValueError, match="TEST_KEY가 설정되지 않았습니다"):
            TestClient(api_key=None, key_name="TEST_KEY", model="test-model")

    def test_init_with_api_key_succeeds(self):
        """API 키가 있으면 정상 생성되어야 한다."""

        class TestClient(BaseLLMClient):
            async def generate(
                self,
                system_instruction: str,
                user_message: str,
                temperature: float = 1.0,
            ) -> str:
                return "test"

            async def list_models(self) -> list[ModelInfo]:
                return []

        client = TestClient(
            api_key="valid-key", key_name="TEST_KEY", model="test-model"
        )
        assert client.model_name == "test-model"

    @pytest.mark.asyncio
    async def test_ensure_response_with_none_raises_error(self):
        """None 응답은 에러를 발생시켜야 한다."""

        class TestClient(BaseLLMClient):
            async def generate(
                self,
                system_instruction: str,
                user_message: str,
                temperature: float = 1.0,
            ) -> str:
                return self._ensure_response(None, "TestProvider")

            async def list_models(self) -> list[ModelInfo]:
                return []

        client = TestClient(api_key="key", key_name="KEY", model="model")

        with pytest.raises(ValueError, match="TestProvider 응답이 비어 있습니다"):
            await client.generate("sys", "user")

    @pytest.mark.asyncio
    async def test_ensure_response_with_content_returns_content(self):
        """유효한 응답은 그대로 반환해야 한다."""

        class TestClient(BaseLLMClient):
            async def generate(
                self,
                system_instruction: str,
                user_message: str,
                temperature: float = 1.0,
            ) -> str:
                return self._ensure_response("valid response", "TestProvider")

            async def list_models(self) -> list[ModelInfo]:
                return []

        client = TestClient(api_key="key", key_name="KEY", model="model")
        result = await client.generate("sys", "user")
        assert result == "valid response"
