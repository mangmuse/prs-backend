from unittest.mock import patch

from src.common.types import ContainsConstraint
from src.prompts.models import OutputSchemaType
from src.runs.evaluator.waterfall import evaluate_waterfall, re_evaluate_from_stored
from src.runs.models import ResultStatus


class TestWaterfallFormatFail:
    """Format 단계 실패 시 fail-fast"""

    def test_format_fail_returns_format_status(self):
        """Format 실패 시 status=format, semantic/constraint 실행 안 함"""
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
        assert result.constraint_result is None


class TestWaterfallSemanticFail:
    """Semantic 단계 실패 시 fail-fast"""

    @patch("src.runs.evaluator.semantic_layer.get_embedding")
    def test_semantic_fail_returns_semantic_status(self, mock_embedding):
        """Semantic 실패 시 status=semantic, constraint 실행 안 함"""
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
        assert result.constraint_result is None


class TestWaterfallConstraintFail:
    """Constraint 단계 실패 시"""

    @patch("src.runs.evaluator.semantic_layer.get_embedding")
    def test_constraint_fail_returns_logic_status(self, mock_embedding):
        """Constraint 실패 시 status=constraint"""
        mock_embedding.return_value = [1.0, 0.0, 0.0]

        constraints = [
            ContainsConstraint(type="contains", target="verdict", value="TRUE")
        ]

        result = evaluate_waterfall(
            raw_output='{"verdict": "FALSE"}',
            output_schema=OutputSchemaType.JSON_OBJECT,
            expected_output='{"verdict": "TRUE"}',
            threshold=0.5,
            constraints=constraints,
        )

        assert result.status == ResultStatus.CONSTRAINT
        assert result.format_result.passed is True
        assert result.semantic_result is not None
        assert result.semantic_result.passed is True
        assert result.constraint_result is not None
        assert result.constraint_result.passed is False


class TestWaterfallPass:
    """모든 단계 통과"""

    @patch("src.runs.evaluator.semantic_layer.get_embedding")
    def test_all_pass_returns_pass_status(self, mock_embedding):
        """모든 레이어 통과 시 status=pass"""
        mock_embedding.return_value = [1.0, 0.0, 0.0]

        constraints = [
            ContainsConstraint(type="contains", target="verdict", value="TRUE")
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
        assert result.constraint_result is not None
        assert result.constraint_result.passed is True


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


class TestReEvaluateFromStored:
    """re_evaluate_from_stored 4개 분기 테스트"""

    def test_re_evaluate_format_failed_returns_format(self):
        """is_format_passed=False → FORMAT 즉시 반환"""
        status, constraint_result = re_evaluate_from_stored(
            is_format_passed=False,
            parsed_output=None,
            semantic_score=0.9,
            threshold=0.8,
            constraints=[],
        )

        assert status == ResultStatus.FORMAT
        assert constraint_result is None

    def test_re_evaluate_semantic_below_threshold_returns_semantic(self):
        """score < threshold → SEMANTIC"""
        status, constraint_result = re_evaluate_from_stored(
            is_format_passed=True,
            parsed_output={"verdict": "TRUE"},
            semantic_score=0.5,
            threshold=0.8,
            constraints=[],
        )

        assert status == ResultStatus.SEMANTIC
        assert constraint_result is None

    def test_re_evaluate_constraint_fail_returns_constraint(self):
        """constraint 실패 → CONSTRAINT + 결과"""
        constraints = [
            ContainsConstraint(type="contains", target="verdict", value="TRUE")
        ]

        status, constraint_result = re_evaluate_from_stored(
            is_format_passed=True,
            parsed_output={"verdict": "FALSE"},
            semantic_score=0.9,
            threshold=0.8,
            constraints=constraints,
        )

        assert status == ResultStatus.CONSTRAINT
        assert constraint_result is not None
        assert constraint_result.passed is False

    def test_re_evaluate_all_pass_returns_pass(self):
        """전부 통과 → PASS + constraint 결과"""
        constraints = [
            ContainsConstraint(type="contains", target="verdict", value="TRUE")
        ]

        status, constraint_result = re_evaluate_from_stored(
            is_format_passed=True,
            parsed_output={"verdict": "TRUE"},
            semantic_score=0.9,
            threshold=0.8,
            constraints=constraints,
        )

        assert status == ResultStatus.PASS
        assert constraint_result is not None
        assert constraint_result.passed is True
