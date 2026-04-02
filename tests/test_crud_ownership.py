"""CRUD 소유권 격리/할당 테스트."""

import pytest
from httpx import AsyncClient


class TestListOwnershipIsolation:
    """Step 14: Guest A는 Guest B의 리소스를 list에서 볼 수 없다."""

    @pytest.mark.asyncio
    async def test_list_datasets_only_own_data(
        self,
        client: AsyncClient,
        guest_factory,
        dataset_factory,
    ) -> None:
        """Guest A는 Guest B의 데이터셋 조회 불가."""
        guest_a_resp = await client.post("/auth/guest")
        client.cookies.set("guest_id", guest_a_resp.json()["guestId"])

        await client.post("/datasets", json={"name": "A의 데이터셋"})

        guest_b = await guest_factory()
        await dataset_factory(guest_b.id, name="B의 데이터셋")

        response = await client.get("/datasets")

        assert response.status_code == 200
        datasets = response.json()
        assert len(datasets) == 1
        assert datasets[0]["name"] == "A의 데이터셋"

    @pytest.mark.asyncio
    async def test_list_prompts_only_own_data(
        self,
        client: AsyncClient,
        guest_factory,
        prompt_factory,
    ) -> None:
        """Guest A는 Guest B의 프롬프트 조회 불가."""
        guest_a_resp = await client.post("/auth/guest")
        client.cookies.set("guest_id", guest_a_resp.json()["guestId"])

        await client.post("/prompts", json={"name": "A의 프롬프트"})

        guest_b = await guest_factory()
        await prompt_factory(guest_b.id, name="B의 프롬프트")

        response = await client.get("/prompts")

        assert response.status_code == 200
        prompts = response.json()
        assert len(prompts) == 1
        assert prompts[0]["name"] == "A의 프롬프트"

    @pytest.mark.asyncio
    async def test_list_profiles_only_own_data(
        self,
        client: AsyncClient,
        guest_factory,
        profile_factory,
    ) -> None:
        """Guest A는 Guest B의 프로필 조회 불가."""
        guest_a_resp = await client.post("/auth/guest")
        client.cookies.set("guest_id", guest_a_resp.json()["guestId"])

        await client.post(
            "/evaluator-profiles",
            json={"name": "A의 프로필", "semanticThreshold": 0.8},
        )

        guest_b = await guest_factory()
        await profile_factory(guest_b.id, name="B의 프로필")

        response = await client.get("/evaluator-profiles")

        assert response.status_code == 200
        profiles = response.json()
        profile_names = [p["name"] for p in profiles]
        assert "A의 프로필" in profile_names
        assert "B의 프로필" not in profile_names


class TestCreateOwnershipAssignment:
    """Step 15: 리소스 생성 시 올바른 소유권 할당."""

    @pytest.mark.asyncio
    async def test_create_dataset_sets_guest_id(
        self,
        client: AsyncClient,
        guest_cookies: dict[str, str],
    ) -> None:
        """생성 시 guest_id 올바르게 할당."""
        response = await client.post("/datasets", json={"name": "소유권 테스트"})

        assert response.status_code == 201
        dataset_id = response.json()["id"]

        detail = await client.get(f"/datasets/{dataset_id}")
        assert detail.status_code == 200

        list_resp = await client.get("/datasets")
        ids = [d["id"] for d in list_resp.json()]
        assert dataset_id in ids

    @pytest.mark.asyncio
    async def test_create_prompt_sets_guest_id(
        self,
        client: AsyncClient,
        guest_cookies: dict[str, str],
    ) -> None:
        """생성 시 guest_id 올바르게 할당."""
        response = await client.post("/prompts", json={"name": "소유권 테스트"})

        assert response.status_code == 201
        prompt_id = response.json()["id"]

        list_resp = await client.get("/prompts")
        ids = [p["id"] for p in list_resp.json()]
        assert prompt_id in ids

    @pytest.mark.asyncio
    async def test_create_rows_other_owner_returns_403(
        self,
        client: AsyncClient,
        guest_cookies: dict[str, str],
        guest_factory,
        dataset_factory,
    ) -> None:
        """다른 사용자 데이터셋에 row 추가 시 403."""
        other_guest = await guest_factory()
        dataset = await dataset_factory(other_guest.id)

        response = await client.post(
            f"/datasets/{dataset.id}/rows",
            json=[{"inputData": {"claim": "침입"}, "expectedOutput": "TRUE"}],
        )

        assert response.status_code == 403
