"""CRUD 부분 업데이트/조회 엣지 케이스 테스트."""

import pytest
from httpx import AsyncClient


class TestPartialUpdate:
    """Step 19: PATCH 엔드포인트 부분 업데이트 (exclude_unset)."""

    @pytest.mark.asyncio
    async def test_update_dataset_name_only(
        self,
        client: AsyncClient,
        guest_cookies: dict[str, str],
    ) -> None:
        """name만 업데이트하면 description은 유지."""
        create_resp = await client.post(
            "/datasets",
            json={"name": "원래 이름", "description": "원래 설명"},
        )
        dataset_id = create_resp.json()["id"]

        response = await client.patch(
            f"/datasets/{dataset_id}",
            json={"name": "수정된 이름"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "수정된 이름"
        assert data["description"] == "원래 설명"

    @pytest.mark.asyncio
    async def test_update_prompt_name_only(
        self,
        client: AsyncClient,
        guest_cookies: dict[str, str],
    ) -> None:
        """name만 업데이트하면 description은 유지."""
        create_resp = await client.post(
            "/prompts",
            json={"name": "원래 이름", "description": "원래 설명"},
        )
        prompt_id = create_resp.json()["id"]

        response = await client.patch(
            f"/prompts/{prompt_id}",
            json={"name": "수정된 이름"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "수정된 이름"
        assert data["description"] == "원래 설명"

    @pytest.mark.asyncio
    async def test_update_profile_semantic_threshold_only(
        self,
        client: AsyncClient,
        guest_cookies: dict[str, str],
    ) -> None:
        """threshold만 업데이트하면 name은 유지."""
        create_resp = await client.post(
            "/evaluator-profiles",
            json={"name": "원래 프로필", "semanticThreshold": 0.8},
        )
        profile_id = create_resp.json()["id"]

        response = await client.patch(
            f"/evaluator-profiles/{profile_id}",
            json={"semanticThreshold": 0.95},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "원래 프로필"
        assert data["semanticThreshold"] == 0.95


class TestQueryEdgeCases:
    """Step 20: 조회 엣지 케이스."""

    @pytest.mark.asyncio
    async def test_get_dataset_detail_page_beyond_total(
        self,
        client: AsyncClient,
        guest_cookies: dict[str, str],
    ) -> None:
        """총 페이지 초과 요청 시 빈 rows."""
        create_resp = await client.post("/datasets", json={"name": "페이지 테스트"})
        dataset_id = create_resp.json()["id"]

        await client.post(
            f"/datasets/{dataset_id}/rows",
            json=[{"inputData": {"claim": "행1"}, "expectedOutput": "TRUE"}],
        )

        response = await client.get(f"/datasets/{dataset_id}?page=999")

        assert response.status_code == 200
        data = response.json()
        assert data["rows"] == []
        assert data["pagination"]["totalCount"] == 1
        assert data["pagination"]["page"] == 999

    @pytest.mark.asyncio
    async def test_get_version_wrong_prompt_id_returns_404(
        self,
        client: AsyncClient,
        guest_cookies: dict[str, str],
    ) -> None:
        """다른 prompt의 version 접근 시 404."""
        prompt_a = await client.post("/prompts", json={"name": "프롬프트A"})
        prompt_a_id = prompt_a.json()["id"]

        version_resp = await client.post(
            f"/prompts/{prompt_a_id}/versions",
            json={
                "systemInstruction": "테스트",
                "userTemplate": "{{input}}",
            },
        )
        version_id = version_resp.json()["id"]

        prompt_b = await client.post("/prompts", json={"name": "프롬프트B"})
        prompt_b_id = prompt_b.json()["id"]

        response = await client.get(f"/prompts/{prompt_b_id}/versions/{version_id}")

        assert response.status_code == 404
