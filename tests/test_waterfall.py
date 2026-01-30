from unittest.mock import patch

from src.common.types import LogicConstraint
from src.prompts.models import OutputSchemaType
from src.runs.evaluator.waterfall import evaluate_waterfall
from src.runs.models import ResultStatus


class TestWaterfallFormatFail:
    """Format 단계 실패 시 fail-fast"""

    def test_format_fail_returns_format_status(self):
        """Format 실패 시 status=format, semantic/logic 실행 안 함"""
        result = evaluate_waterfall(
            raw_output="invalid json",
            output_schema=OutputSchemaType.JSON_OBJECT,
            expected_output='{"verdict": "TRUE"}',
            threshold=0.8,
            constraints=[],
        )

        assert result.status == ResultStatus.FORMAT
        assert result.format_result.passed is False
        assert result.semantic_result is None
        assert result.logic_result is None


class TestWaterfallSemanticFail:
    """Semantic 단계 실패 시 fail-fast"""

    @patch("src.runs.evaluator.semantic_layer.get_embedding")
    def test_semantic_fail_returns_semantic_status(self, mock_embedding):
        """Semantic 실패 시 status=semantic, logic 실행 안 함"""
        mock_embedding.side_effect = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ]

        result = evaluate_waterfall(
            raw_output='{"verdict": "FALSE"}',
            output_schema=OutputSchemaType.JSON_OBJECT,
            expected_output='{"verdict": "TRUE"}',
            threshold=0.9,
            constraints=[],
        )

        assert result.status == ResultStatus.SEMANTIC
        assert result.format_result.passed is True
        assert result.semantic_result is not None
        assert result.semantic_result.passed is False
        assert result.logic_result is None


class TestWaterfallLogicFail:
    """Logic 단계 실패 시"""

    @patch("src.runs.evaluator.semantic_layer.get_embedding")
    def test_logic_fail_returns_logic_status(self, mock_embedding):
        """Logic 실패 시 status=logic"""
        mock_embedding.return_value = [1.0, 0.0, 0.0]

        constraints: list[LogicConstraint] = [
            {"type": "contains", "target": "verdict", "value": "TRUE"}
        ]

        result = evaluate_waterfall(
            raw_output='{"verdict": "FALSE"}',
            output_schema=OutputSchemaType.JSON_OBJECT,
            expected_output='{"verdict": "TRUE"}',
            threshold=0.5,
            constraints=constraints,
        )

        assert result.status == ResultStatus.LOGIC
        assert result.format_result.passed is True
        assert result.semantic_result is not None
        assert result.semantic_result.passed is True
        assert result.logic_result is not None
        assert result.logic_result.passed is False


class TestWaterfallPass:
    """모든 단계 통과"""

    @patch("src.runs.evaluator.semantic_layer.get_embedding")
    def test_all_pass_returns_pass_status(self, mock_embedding):
        """모든 레이어 통과 시 status=pass"""
        mock_embedding.return_value = [1.0, 0.0, 0.0]

        constraints: list[LogicConstraint] = [
            {"type": "contains", "target": "verdict", "value": "TRUE"}
        ]

        result = evaluate_waterfall(
            raw_output='{"verdict": "TRUE"}',
            output_schema=OutputSchemaType.JSON_OBJECT,
            expected_output='{"verdict": "TRUE"}',
            threshold=0.5,
            constraints=constraints,
        )

        assert result.status == ResultStatus.PASS
        assert result.format_result.passed is True
        assert result.semantic_result is not None
        assert result.semantic_result.passed is True
        assert result.logic_result is not None
        assert result.logic_result.passed is True


class TestWaterfallFreeform:
    """Freeform은 Format 검사 생략"""

    @patch("src.runs.evaluator.semantic_layer.get_embedding")
    def test_freeform_skips_format_parsing(self, mock_embedding):
        """Freeform은 항상 Format 통과"""
        mock_embedding.return_value = [1.0, 0.0, 0.0]

        result = evaluate_waterfall(
            raw_output="자유 형식 텍스트",
            output_schema=OutputSchemaType.FREEFORM,
            expected_output="기대 텍스트",
            threshold=0.5,
            constraints=[],
        )

        assert result.format_result.passed is True
        assert result.status == ResultStatus.PASS


class TestWaterfallLabel:
    """Label은 Semantic 검사 생략"""

    def test_label_skips_semantic(self):
        """Label 타입은 Semantic 검사 생략 (score=1.0 고정)"""
        result = evaluate_waterfall(
            raw_output="TRUE",
            output_schema=OutputSchemaType.LABEL,
            expected_output="TRUE",
            threshold=0.5,
            constraints=[],
        )

        assert result.format_result.passed is True
        assert result.semantic_result is not None
        assert result.semantic_result.semantic_score == 1.0
        assert result.status == ResultStatus.PASS
