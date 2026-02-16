"""POST /runs E2E 테스트 스크립트."""

import time
from datetime import datetime
from typing import Any

import httpx

BASE_URL = "http://localhost:8000"


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def create_guest_session(client: httpx.Client) -> str:
    """게스트 세션 생성 및 쿠키 자동 저장."""
    resp = client.post(f"{BASE_URL}/auth/guest")
    resp.raise_for_status()
    guest_id = resp.json()["guest_id"]
    log(f"✓ 게스트 세션: {guest_id}")
    return guest_id


def create_prompt(client: httpx.Client, name: str) -> int:
    """프롬프트 생성."""
    resp = client.post(f"{BASE_URL}/prompts", json={"name": name})
    resp.raise_for_status()
    prompt_id = resp.json()["id"]
    log(f"✓ 프롬프트 생성: {name} (id={prompt_id})")
    return prompt_id


def create_version(
    client: httpx.Client,
    prompt_id: int,
    system_instruction: str,
    user_template: str,
    model: str = "gemini-2.0-flash",
    output_schema: str = "json_object",
    temperature: float = 0.3,
) -> int:
    """프롬프트 버전 생성."""
    resp = client.post(
        f"{BASE_URL}/prompts/{prompt_id}/versions",
        json={
            "system_instruction": system_instruction,
            "user_template": user_template,
            "model": model,
            "output_schema": output_schema,
            "temperature": temperature,
        },
    )
    resp.raise_for_status()
    version_id = resp.json()["id"]
    log(f"  → 버전 생성: v{resp.json()['version_number']} (id={version_id})")
    return version_id


def create_dataset(client: httpx.Client, name: str) -> int:
    """데이터셋 생성."""
    resp = client.post(f"{BASE_URL}/datasets", json={"name": name})
    resp.raise_for_status()
    dataset_id = resp.json()["id"]
    log(f"✓ 데이터셋 생성: {name} (id={dataset_id})")
    return dataset_id


def add_row(
    client: httpx.Client,
    dataset_id: int,
    input_data: dict[str, Any],
    expected_output: dict[str, Any] | list[str] | str,
    tags: list[str] | None = None,
) -> None:
    """데이터셋에 행 추가."""
    import json

    # expected_output이 dict 또는 list면 JSON 문자열로 변환
    if isinstance(expected_output, (dict, list)):
        expected_output = json.dumps(expected_output, ensure_ascii=False)

    # API는 배열을 기대함
    resp = client.post(
        f"{BASE_URL}/datasets/{dataset_id}/rows",
        json=[
            {
                "input_data": input_data,
                "expected_output": expected_output,
                "tags": tags or [],
            }
        ],
    )
    resp.raise_for_status()
    created_count = resp.json()["created_count"]
    log(f"  → 행 추가: {input_data} (count={created_count})")


def create_profile(
    client: httpx.Client,
    name: str,
    semantic_threshold: float = 0.75,
    global_constraints: list[dict[str, Any]] | None = None,
) -> int:
    """평가 프로필 생성."""
    resp = client.post(
        f"{BASE_URL}/evaluator-profiles",
        json={
            "name": name,
            "semantic_threshold": semantic_threshold,
            "global_constraints": global_constraints or [],
        },
    )
    resp.raise_for_status()
    profile_id = resp.json()["id"]
    log(f"✓ 프로필 생성: {name} (id={profile_id})")
    return profile_id


def create_run(
    client: httpx.Client, version_id: int, dataset_id: int, profile_id: int
) -> int:
    """Run 실행."""
    resp = client.post(
        f"{BASE_URL}/runs",
        json={
            "prompt_version_id": version_id,
            "dataset_id": dataset_id,
            "profile_id": profile_id,
        },
    )
    resp.raise_for_status()
    run_id = resp.json()["id"]
    status = resp.json()["status"]
    log(f"✓ Run 생성: id={run_id}, status={status}")
    return run_id


def get_run_status(client: httpx.Client, run_id: int) -> str:
    """Run 상태 조회 (목록에서)."""
    resp = client.get(f"{BASE_URL}/runs")
    resp.raise_for_status()
    for run in resp.json():
        if run["id"] == run_id:
            return run["status"]
    raise ValueError(f"Run {run_id} not found")


def get_run_detail(client: httpx.Client, run_id: int) -> dict[str, Any]:
    """Run 상세 조회."""
    resp = client.get(f"{BASE_URL}/runs/{run_id}")
    resp.raise_for_status()
    return resp.json()


def wait_for_completion(
    client: httpx.Client, run_id: int, timeout: int = 60
) -> dict[str, Any]:
    """Run 완료 대기."""
    start = time.time()
    while time.time() - start < timeout:
        status = get_run_status(client, run_id)
        if status != "running":
            detail = get_run_detail(client, run_id)
            detail["status"] = status  # 상세에 status 추가
            return detail
        log(f"  ⏳ 대기 중... (status={status})")
        time.sleep(2)
    raise TimeoutError(f"Run {run_id} 타임아웃 ({timeout}초)")


def print_results(run: dict[str, Any]) -> None:
    """결과 출력."""
    print("\n" + "=" * 60)
    print(f"Run ID: {run['id']}")
    print(f"Status: {run['status']}")
    print(f"Pass Rate: {run.get('pass_rate', 'N/A')}")
    print(f"Avg Semantic: {run.get('avg_semantic', 'N/A')}")
    print("-" * 60)

    if "results" in run:
        for i, result in enumerate(run["results"], 1):
            status_emoji = "✅" if result["status"] == "pass" else "❌"
            print(f"\n[{i}] {status_emoji} {result['status']}")
            print(f"    Input: {result.get('input_snapshot', {})}")
            print(f"    Expected: {result.get('expected_snapshot', {})}")
            print(f"    Raw Output: {result.get('raw_output', '')[:100]}...")
            print(f"    Format: {'✓' if result.get('is_format_passed') else '✗'}")
            print(f"    Semantic: {result.get('semantic_score', 'N/A')}")

    print("=" * 60 + "\n")


# =============================================================================
# 테스트 케이스
# =============================================================================


def test_case_1_json_factcheck(client: httpx.Client) -> dict[str, Any]:
    """
    케이스 1: JSON 팩트체크
    - output_schema: json_object
    - 성공/실패 케이스 혼합
    """
    log("\n📋 케이스 1: JSON 팩트체크")

    prompt_id = create_prompt(client, "팩트체크-JSON")
    version_id = create_version(
        client,
        prompt_id,
        system_instruction="""당신은 팩트체커입니다.
주어진 문장의 사실 여부를 판단하세요.
반드시 JSON 형식으로만 응답하세요: {"verdict": "TRUE" 또는 "FALSE", "confidence": 0~1 사이 숫자}""",
        user_template="검증할 문장: {{claim}}",
        output_schema="JSON Object",
    )

    dataset_id = create_dataset(client, "팩트체크-테스트셋")
    add_row(
        client,
        dataset_id,
        {"claim": "서울은 대한민국의 수도입니다"},
        {"verdict": "TRUE"},
    )
    add_row(
        client,
        dataset_id,
        {"claim": "지구는 평평합니다"},
        {"verdict": "FALSE"},
    )
    add_row(
        client,
        dataset_id,
        {"claim": "물은 H2O입니다"},
        {"verdict": "TRUE"},
    )

    profile_id = create_profile(client, "기본-0.75", semantic_threshold=0.75)

    run_id = create_run(client, version_id, dataset_id, profile_id)
    run = wait_for_completion(client, run_id)
    print_results(run)
    return run


def test_case_2_label(client: httpx.Client) -> dict[str, Any]:
    """
    케이스 2: Label 분류
    - output_schema: label
    - 감정 분석
    """
    log("\n📋 케이스 2: Label 감정 분석")

    prompt_id = create_prompt(client, "감정분석-Label")
    version_id = create_version(
        client,
        prompt_id,
        system_instruction="""당신은 감정 분석기입니다.
주어진 텍스트의 감정을 분류하세요.
반드시 POSITIVE, NEGATIVE, NEUTRAL 중 하나만 응답하세요.""",
        user_template="분석할 텍스트: {{text}}",
        output_schema="Label",
    )

    dataset_id = create_dataset(client, "감정분석-테스트셋")
    add_row(
        client,
        dataset_id,
        {"text": "이 제품 정말 최고예요! 너무 좋아요!"},
        "POSITIVE",
    )
    add_row(
        client,
        dataset_id,
        {"text": "최악이에요. 다시는 안 삽니다."},
        "NEGATIVE",
    )
    add_row(
        client,
        dataset_id,
        {"text": "그냥 그래요. 보통이에요."},
        "NEUTRAL",
    )

    profile_id = create_profile(client, "Label-0.8", semantic_threshold=0.8)

    run_id = create_run(client, version_id, dataset_id, profile_id)
    run = wait_for_completion(client, run_id)
    print_results(run)
    return run


def test_case_3_with_constraints(client: httpx.Client) -> dict[str, Any]:
    """
    케이스 3: Logic Constraints 검증
    - contains, range 제약조건
    """
    log("\n📋 케이스 3: Logic Constraints")

    prompt_id = create_prompt(client, "요약-Constraints")
    version_id = create_version(
        client,
        prompt_id,
        system_instruction="""당신은 요약 전문가입니다.
주어진 텍스트를 한 문장으로 요약하세요.
반드시 JSON 형식으로 응답: {"summary": "요약 내용", "word_count": 단어수}""",
        user_template="요약할 텍스트: {{content}}",
        output_schema="JSON Object",
    )

    dataset_id = create_dataset(client, "요약-Constraints셋")
    add_row(
        client,
        dataset_id,
        {
            "content": "인공지능은 컴퓨터 과학의 한 분야로, 기계가 인간처럼 학습하고 문제를 해결할 수 있게 하는 기술입니다."
        },
        {"summary": "인공지능은 기계가 학습하고 문제를 해결하는 기술입니다."},
    )

    profile_id = create_profile(
        client,
        "Constraints-0.5",
        semantic_threshold=0.5,
        global_constraints=[
            {"type": "not_contains", "field": "summary", "value": "인공지능"}
        ],
    )

    run_id = create_run(client, version_id, dataset_id, profile_id)
    run = wait_for_completion(client, run_id)
    print_results(run)
    return run


def test_case_4_freeform(client: httpx.Client) -> dict[str, Any]:
    """
    케이스 4: Freeform (자유 형식)
    - Format 검증 스킵
    """
    log("\n📋 케이스 4: Freeform 자유응답")

    prompt_id = create_prompt(client, "질문응답-Freeform")
    version_id = create_version(
        client,
        prompt_id,
        system_instruction="당신은 친절한 도우미입니다. 질문에 자연스럽게 답변하세요.",
        user_template="질문: {{question}}",
        output_schema="Freeform",
    )

    dataset_id = create_dataset(client, "QA-Freeform셋")
    add_row(
        client,
        dataset_id,
        {"question": "파이썬이란 무엇인가요?"},
        "파이썬은 프로그래밍 언어입니다",
    )

    profile_id = create_profile(client, "Freeform-0.6", semantic_threshold=0.6)

    run_id = create_run(client, version_id, dataset_id, profile_id)
    run = wait_for_completion(client, run_id)
    print_results(run)
    return run


def test_case_5_json_array(client: httpx.Client) -> dict[str, Any]:
    """
    케이스 5: JSON Array
    - output_schema: json_array
    - 배열 파싱 검증
    """
    log("\n📋 케이스 5: JSON Array")

    prompt_id = create_prompt(client, "키워드추출-Array")
    version_id = create_version(
        client,
        prompt_id,
        system_instruction="""당신은 키워드 추출기입니다.
주어진 텍스트에서 핵심 키워드 3개를 추출하세요.
반드시 JSON 배열 형식으로만 응답하세요: ["키워드1", "키워드2", "키워드3"]""",
        user_template="텍스트: {{text}}",
        output_schema="JSON Array",
    )

    dataset_id = create_dataset(client, "키워드추출-테스트셋")
    add_row(
        client,
        dataset_id,
        {"text": "인공지능과 머신러닝이 데이터 분석에 혁신을 가져오고 있습니다."},
        ["인공지능", "머신러닝", "데이터"],
    )

    profile_id = create_profile(client, "Array-0.6", semantic_threshold=0.6)

    run_id = create_run(client, version_id, dataset_id, profile_id)
    run = wait_for_completion(client, run_id)
    print_results(run)
    return run


def test_case_6_logic_contains(client: httpx.Client) -> dict[str, Any]:
    """
    케이스 6: Logic contains 제약
    - 특정 문자열 포함 검증
    """
    log("\n📋 케이스 6: Logic contains")

    prompt_id = create_prompt(client, "분석-Contains")
    version_id = create_version(
        client,
        prompt_id,
        system_instruction="""당신은 분석가입니다.
주어진 주제에 대해 분석하세요.
반드시 JSON 형식으로 응답: {"analysis": "분석 내용", "conclusion": "결론"}
결론에는 반드시 '추천' 또는 '비추천'이라는 단어가 포함되어야 합니다.""",
        user_template="분석 주제: {{topic}}",
        output_schema="JSON Object",
    )

    dataset_id = create_dataset(client, "분석-Contains셋")
    add_row(
        client,
        dataset_id,
        {"topic": "재택근무의 효과성"},
        {"analysis": "재택근무는 생산성 향상에 기여합니다", "conclusion": "추천합니다"},
    )

    profile_id = create_profile(
        client,
        "Contains-0.5",
        semantic_threshold=0.5,
        global_constraints=[
            {"type": "contains", "field": "conclusion", "value": "추천"}
        ],
    )

    run_id = create_run(client, version_id, dataset_id, profile_id)
    run = wait_for_completion(client, run_id)
    print_results(run)
    return run


def test_case_7_logic_range(client: httpx.Client) -> dict[str, Any]:
    """
    케이스 7: Logic range 제약
    - 숫자 범위 검증
    """
    log("\n📋 케이스 7: Logic range")

    prompt_id = create_prompt(client, "평가-Range")
    version_id = create_version(
        client,
        prompt_id,
        system_instruction="""당신은 평가자입니다.
주어진 항목을 1~10점으로 평가하세요.
반드시 JSON 형식으로 응답: {"item": "항목명", "score": 1~10 숫자, "reason": "이유"}""",
        user_template="평가 대상: {{item}}",
        output_schema="JSON Object",
    )

    dataset_id = create_dataset(client, "평가-Range셋")
    add_row(
        client,
        dataset_id,
        {"item": "ChatGPT의 사용자 경험"},
        {"item": "ChatGPT의 사용자 경험", "score": 8, "reason": "직관적인 UI"},
    )

    profile_id = create_profile(
        client,
        "Range-0.5",
        semantic_threshold=0.5,
        global_constraints=[{"type": "range", "field": "score", "min": 1, "max": 10}],
    )

    run_id = create_run(client, version_id, dataset_id, profile_id)
    run = wait_for_completion(client, run_id)
    print_results(run)
    return run


def test_case_8_logic_regex(client: httpx.Client) -> dict[str, Any]:
    """
    케이스 8: Logic regex 제약
    - 정규식 패턴 검증
    """
    log("\n📋 케이스 8: Logic regex")

    prompt_id = create_prompt(client, "코드생성-Regex")
    version_id = create_version(
        client,
        prompt_id,
        system_instruction="""당신은 코드 생성기입니다.
주어진 요청에 대해 간단한 Python 함수명을 생성하세요.
반드시 JSON 형식으로 응답: {"function_name": "snake_case_함수명", "description": "설명"}
함수명은 반드시 snake_case 형식이어야 합니다 (예: get_user_info).""",
        user_template="요청: {{request}}",
        output_schema="JSON Object",
    )

    dataset_id = create_dataset(client, "코드생성-Regex셋")
    add_row(
        client,
        dataset_id,
        {"request": "사용자 정보를 가져오는 함수"},
        {"function_name": "get_user_info", "description": "사용자 정보 조회"},
    )

    profile_id = create_profile(
        client,
        "Regex-0.5",
        semantic_threshold=0.5,
        global_constraints=[
            {"type": "regex", "field": "function_name", "pattern": "^[a-z][a-z0-9_]*$"}
        ],
    )

    run_id = create_run(client, version_id, dataset_id, profile_id)
    run = wait_for_completion(client, run_id)
    print_results(run)
    return run


def main():
    """메인 테스트 실행."""
    print("\n" + "=" * 60)
    print("🚀 POST /runs 실제 테스트 시작")
    print("=" * 60)

    with httpx.Client(timeout=120.0) as client:
        create_guest_session(client)

        results = []

        try:
            results.append(
                ("케이스1: JSON 팩트체크", test_case_1_json_factcheck(client))
            )
        except Exception as e:
            log(f"❌ 케이스1 실패: {e}")
            results.append(("케이스1: JSON 팩트체크", {"error": str(e)}))

        try:
            results.append(("케이스2: Label 감정분석", test_case_2_label(client)))
        except Exception as e:
            log(f"❌ 케이스2 실패: {e}")
            results.append(("케이스2: Label 감정분석", {"error": str(e)}))

        try:
            results.append(
                ("케이스3: Constraints", test_case_3_with_constraints(client))
            )
        except Exception as e:
            log(f"❌ 케이스3 실패: {e}")
            results.append(("케이스3: Constraints", {"error": str(e)}))

        try:
            results.append(("케이스4: Freeform", test_case_4_freeform(client)))
        except Exception as e:
            log(f"❌ 케이스4 실패: {e}")
            results.append(("케이스4: Freeform", {"error": str(e)}))

        try:
            results.append(("케이스5: JSON Array", test_case_5_json_array(client)))
        except Exception as e:
            log(f"❌ 케이스5 실패: {e}")
            results.append(("케이스5: JSON Array", {"error": str(e)}))

        try:
            results.append(
                ("케이스6: Logic contains", test_case_6_logic_contains(client))
            )
        except Exception as e:
            log(f"❌ 케이스6 실패: {e}")
            results.append(("케이스6: Logic contains", {"error": str(e)}))

        try:
            results.append(("케이스7: Logic range", test_case_7_logic_range(client)))
        except Exception as e:
            log(f"❌ 케이스7 실패: {e}")
            results.append(("케이스7: Logic range", {"error": str(e)}))

        try:
            results.append(("케이스8: Logic regex", test_case_8_logic_regex(client)))
        except Exception as e:
            log(f"❌ 케이스8 실패: {e}")
            results.append(("케이스8: Logic regex", {"error": str(e)}))

        # 최종 요약
        print("\n" + "=" * 60)
        print("📊 테스트 요약")
        print("=" * 60)
        for name, run in results:
            if "error" in run:
                print(f"❌ {name}: 에러 - {run['error']}")
            else:
                status = run.get("status", "unknown")
                pass_rate = run.get("pass_rate", "N/A")
                print(
                    f"{'✅' if status == 'completed' else '⚠️'} {name}: {status}, pass_rate={pass_rate}"
                )


if __name__ == "__main__":
    main()
