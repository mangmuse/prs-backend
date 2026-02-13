import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_logout_clears_cookies(client: AsyncClient) -> None:
    """POST /auth/logout -> 204, refresh_token + guest_id 쿠키 삭제."""
    client.cookies.set("refresh_token", "some-refresh-token", domain="test")
    client.cookies.set("guest_id", "some-guest-id", domain="test")

    response = await client.post("/auth/logout")

    assert response.status_code == 204
    set_cookie_headers = response.headers.get_list("set-cookie")
    cookie_str = " ".join(set_cookie_headers)
    assert "refresh_token" in cookie_str
    assert "guest_id" in cookie_str
    assert 'Max-Age=0' in cookie_str or 'max-age=0' in cookie_str


@pytest.mark.asyncio
async def test_logout_without_auth(client: AsyncClient) -> None:
    """POST /auth/logout - 인증 없이 호출 -> 204 (idempotent)."""
    response = await client.post("/auth/logout")
    assert response.status_code == 204
