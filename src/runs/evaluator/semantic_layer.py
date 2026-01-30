import numpy as np
from openai import OpenAI

from src.prompts.models import OutputSchemaType
from src.runs.schemas import SemanticCheckResult

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def get_embedding(text: str) -> list[float]:
    """OpenAI API로 텍스트를 벡터로 변환"""
    client = _get_client()
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """두 벡터 간 코사인 유사도 계산"""
    a = np.array(vec1)
    b = np.array(vec2)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(np.dot(a, b) / (norm_a * norm_b))


def check_semantic(
    raw_output: str,
    expected_output: str,
    output_schema: OutputSchemaType,
    threshold: float,
) -> SemanticCheckResult:
    """Semantic Layer: embedding 기반 유사도 검증"""
    if output_schema == OutputSchemaType.LABEL:
        return SemanticCheckResult(passed=True, semantic_score=1.0)

    try:
        raw_embedding = get_embedding(raw_output)
        expected_embedding = get_embedding(expected_output)
    except Exception as e:
        return SemanticCheckResult(
            passed=False,
            semantic_score=0.0,
            error_message=f"Embedding API 오류: {e}",
        )

    score = cosine_similarity(raw_embedding, expected_embedding)

    passed = score >= threshold

    return SemanticCheckResult(passed=passed, semantic_score=score)
