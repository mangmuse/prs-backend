from unittest.mock import patch

from src.prompts.models import OutputSchemaType
from src.runs.evaluator.semantic_layer import check_semantic


EMBEDDING_PATH = "src.runs.evaluator.semantic_layer.get_embedding"


class TestCheckSemanticBasic:
    """기본 Semantic 검증 테스트"""

    @patch(EMBEDDING_PATH)
    def test_identical_vectors_pass(self, mock_get_embedding):
        """동일한 벡터는 유사도 1.0으로 통과"""
        mock_get_embedding.side_effect = [
            [0.1, 0.2, 0.3],
            [0.1, 0.2, 0.3],
        ]

        result = check_semantic(
            raw_output='{"verdict": "TRUE"}',
            expected_output='{"verdict": "TRUE"}',
            output_schema=OutputSchemaType.JSON_OBJECT,
            threshold=0.8,
        )

        assert result.passed is True
        assert result.semantic_score == 1.0

    @patch(EMBEDDING_PATH)
    def test_different_vectors_fail(self, mock_get_embedding):
        """다른 벡터는 낮은 유사도로 실패"""
        mock_get_embedding.side_effect = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ]

        result = check_semantic(
            raw_output='{"verdict": "TRUE"}',
            expected_output='{"verdict": "FALSE"}',
            output_schema=OutputSchemaType.JSON_OBJECT,
            threshold=0.8,
        )

        assert result.passed is False
        assert result.semantic_score == 0.0

    @patch(EMBEDDING_PATH)
    def test_api_error_returns_error_message(self, mock_get_embedding):
        """API 오류 시 error_message 반환"""
        mock_get_embedding.side_effect = Exception("API rate limit exceeded")

        result = check_semantic(
            raw_output='{"verdict": "TRUE"}',
            expected_output='{"verdict": "TRUE"}',
            output_schema=OutputSchemaType.JSON_OBJECT,
            threshold=0.8,
        )

        assert result.passed is False
        assert result.semantic_score == 0.0
        assert result.error_message is not None

    @patch(EMBEDDING_PATH)
    def test_score_exactly_at_threshold_passes(self, mock_get_embedding):
        """점수가 threshold와 정확히 같으면 통과"""
        mock_get_embedding.side_effect = [
            [1.0, 0.0],
            [0.8, 0.6],
        ]

        result = check_semantic(
            raw_output="test",
            expected_output="test",
            output_schema=OutputSchemaType.JSON_OBJECT,
            threshold=0.8,
        )

        assert result.passed is True


class TestCheckSemanticLabelSkip:
    """Label 타입은 Semantic Layer 스킵"""

    @patch(EMBEDDING_PATH)
    def test_label_type_always_passes(self, mock_get_embedding):
        """Label 타입은 embedding 호출 없이 통과"""
        result = check_semantic(
            raw_output="TRUE",
            expected_output="TRUE",
            output_schema=OutputSchemaType.LABEL,
            threshold=0.8,
        )

        assert result.passed is True
        assert result.semantic_score == 1.0
        mock_get_embedding.assert_not_called()
