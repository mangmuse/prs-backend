from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.llm.schemas import ModelInfo, ModelsResponse
from src.main import app


class TestGetModels:
    """GET /llm/models 테스트."""

    def test_returns_models_list(self):
        """모델 목록을 반환해야 한다."""
        mock_response = ModelsResponse(
            models=[
                ModelInfo(id="openai/gpt-4o", display_name="gpt-4o", provider="openai"),
                ModelInfo(
                    id="anthropic/claude-sonnet-4",
                    display_name="Claude Sonnet 4",
                    provider="anthropic",
                ),
            ]
        )

        with patch(
            "src.llm.router.service.list_models", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = mock_response

            client = TestClient(app)
            response = client.get("/llm/models")

            assert response.status_code == 200
            data = response.json()
            assert len(data["models"]) == 2
            assert data["models"][0]["id"] == "openai/gpt-4o"

    def test_returns_empty_when_no_keys(self):
        """API 키가 없으면 빈 배열을 반환해야 한다."""
        mock_response = ModelsResponse(models=[])

        with patch(
            "src.llm.router.service.list_models", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = mock_response

            client = TestClient(app)
            response = client.get("/llm/models")

            assert response.status_code == 200
            data = response.json()
            assert data["models"] == []
