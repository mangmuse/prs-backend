"""POST /llm/verify-key 엔드포인트 테스트."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from src.llm.schemas import VerifyKeyResponse


@pytest.mark.asyncio
async def test_verify_key_endpoint_valid_key(
    client: AsyncClient,
    guest_cookies: dict[str, str],
) -> None:
    """POST /llm/verify-key — 유효한 키 성공."""
    mock_response = VerifyKeyResponse(valid=True, error=None)

    with patch(
        "src.llm.router.service.verify_api_key", new_callable=AsyncMock
    ) as mock_verify:
        mock_verify.return_value = mock_response

        response = await client.post(
            "/llm/verify-key",
            json={"provider": "openai", "apiKey": "sk-valid-key"},
        )

    assert response.status_code == 200
    assert response.json()["valid"] is True


@pytest.mark.asyncio
async def test_verify_key_endpoint_invalid_key(
    client: AsyncClient,
    guest_cookies: dict[str, str],
) -> None:
    """POST /llm/verify-key — 잘못된 키 실패."""
    mock_response = VerifyKeyResponse(valid=False, error="API 키가 유효하지 않습니다")

    with patch(
        "src.llm.router.service.verify_api_key", new_callable=AsyncMock
    ) as mock_verify:
        mock_verify.return_value = mock_response

        response = await client.post(
            "/llm/verify-key",
            json={"provider": "openai", "apiKey": "sk-invalid"},
        )

    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert response.json()["error"] is not None
