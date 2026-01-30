import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_prompt(
    client: AsyncClient, guest_cookies: dict[str, str]
) -> None:
    """POST /prompts - 프롬프트 생성 성공."""
    response = await client.post(
        "/prompts",
        json={"name": "팩트체커", "description": "사실 여부 판단용 프롬프트"},
        cookies=guest_cookies,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "팩트체커"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_list_prompts_with_version_count(
    client: AsyncClient, guest_cookies: dict[str, str]
) -> None:
    """GET /prompts - 목록 조회, version_count 포함."""
    create_resp = await client.post(
        "/prompts",
        json={"name": "테스트 프롬프트"},
        cookies=guest_cookies,
    )
    prompt_id = create_resp.json()["id"]

    await client.post(
        f"/prompts/{prompt_id}/versions",
        json={
            "system_instruction": "당신은 도우미입니다.",
            "user_template": "{{input}}을 처리하세요.",
        },
        cookies=guest_cookies,
    )

    response = await client.get("/prompts", cookies=guest_cookies)

    assert response.status_code == 200
    prompts = response.json()
    assert len(prompts) >= 1

    target = next(p for p in prompts if p["id"] == prompt_id)
    assert target["version_count"] == 1
    assert target["latest_version"] == 1


@pytest.mark.asyncio
async def test_create_version_auto_increment(
    client: AsyncClient, guest_cookies: dict[str, str]
) -> None:
    """POST /prompts/{id}/versions - 버전 번호 자동 증가."""
    prompt_resp = await client.post(
        "/prompts",
        json={"name": "버전 테스트"},
        cookies=guest_cookies,
    )
    prompt_id = prompt_resp.json()["id"]

    v1 = await client.post(
        f"/prompts/{prompt_id}/versions",
        json={
            "system_instruction": "v1 시스템",
            "user_template": "v1 유저",
            "memo": "첫 버전",
        },
        cookies=guest_cookies,
    )
    assert v1.status_code == 201
    assert v1.json()["version_number"] == 1

    v2 = await client.post(
        f"/prompts/{prompt_id}/versions",
        json={
            "system_instruction": "v2 시스템",
            "user_template": "v2 유저",
            "memo": "두번째 버전",
        },
        cookies=guest_cookies,
    )
    assert v2.status_code == 201
    assert v2.json()["version_number"] == 2


@pytest.mark.asyncio
async def test_get_version_detail(
    client: AsyncClient, guest_cookies: dict[str, str]
) -> None:
    """GET /prompts/{id}/versions/{ver_id} - 버전 상세 조회."""
    prompt_resp = await client.post(
        "/prompts",
        json={"name": "상세 조회 테스트"},
        cookies=guest_cookies,
    )
    prompt_id = prompt_resp.json()["id"]

    ver_resp = await client.post(
        f"/prompts/{prompt_id}/versions",
        json={
            "system_instruction": "시스템 지시",
            "user_template": "유저 템플릿",
            "model": "gpt-4",
            "temperature": 0.7,
        },
        cookies=guest_cookies,
    )
    version_id = ver_resp.json()["id"]

    response = await client.get(
        f"/prompts/{prompt_id}/versions/{version_id}",
        cookies=guest_cookies,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["system_instruction"] == "시스템 지시"
    assert data["user_template"] == "유저 템플릿"
    assert data["model"] == "gpt-4"
    assert data["temperature"] == 0.7


@pytest.mark.asyncio
async def test_list_versions(
    client: AsyncClient, guest_cookies: dict[str, str]
) -> None:
    """GET /prompts/{id}/versions - 버전 히스토리 조회."""
    prompt_resp = await client.post(
        "/prompts",
        json={"name": "히스토리 테스트"},
        cookies=guest_cookies,
    )
    prompt_id = prompt_resp.json()["id"]

    for i in range(3):
        await client.post(
            f"/prompts/{prompt_id}/versions",
            json={
                "system_instruction": f"시스템 {i}",
                "user_template": f"유저 {i}",
            },
            cookies=guest_cookies,
        )

    response = await client.get(f"/prompts/{prompt_id}/versions", cookies=guest_cookies)

    assert response.status_code == 200
    versions = response.json()
    assert len(versions) == 3
    assert versions[0]["version_number"] == 3
    assert versions[2]["version_number"] == 1


@pytest.mark.asyncio
async def test_access_other_user_prompt_returns_404(client: AsyncClient) -> None:
    """다른 사용자 프롬프트 접근 시 404."""
    guest1_resp = await client.post("/auth/guest")
    cookies1 = {"guest_id": guest1_resp.json()["guest_id"]}

    prompt_resp = await client.post(
        "/prompts",
        json={"name": "비밀 프롬프트"},
        cookies=cookies1,
    )
    prompt_id = prompt_resp.json()["id"]

    client.cookies.clear()
    guest2_resp = await client.post("/auth/guest")
    cookies2 = {"guest_id": guest2_resp.json()["guest_id"]}

    response = await client.get(f"/prompts/{prompt_id}/versions", cookies=cookies2)

    assert response.status_code == 404
