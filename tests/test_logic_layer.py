from src.common.types import LogicConstraint
from src.runs.evaluator.logic_layer import check_logic


class TestCheckLogicContains:
    """contains constraint 테스트"""

    def test_contains_pass(self):
        """target 필드에 value가 포함되면 통과"""
        parsed_output = {"verdict": "TRUE", "reasoning": "정확한 판단입니다"}
        constraints: list[LogicConstraint] = [
            {"type": "contains", "target": "verdict", "value": "TRUE"}
        ]

        result = check_logic(parsed_output, constraints)

        assert result.passed is True
        assert len(result.results) == 1
        assert result.results[0].passed is True

    def test_contains_fail(self):
        """target 필드에 value가 없으면 실패"""
        parsed_output = {"verdict": "FALSE"}
        constraints: list[LogicConstraint] = [
            {"type": "contains", "target": "verdict", "value": "TRUE"}
        ]

        result = check_logic(parsed_output, constraints)

        assert result.passed is False
        assert result.results[0].passed is False
        assert result.results[0].message is not None


class TestCheckLogicNotContains:
    """not_contains constraint 테스트"""

    def test_not_contains_pass(self):
        """target 필드에 value가 없으면 통과"""
        parsed_output = {"verdict": "TRUE"}
        constraints: list[LogicConstraint] = [
            {"type": "not_contains", "target": "verdict", "value": "ERROR"}
        ]

        result = check_logic(parsed_output, constraints)

        assert result.passed is True

    def test_not_contains_fail(self):
        """target 필드에 value가 포함되면 실패"""
        parsed_output = {"verdict": "TRUE"}
        constraints: list[LogicConstraint] = [
            {"type": "not_contains", "target": "verdict", "value": "TRUE"}
        ]

        result = check_logic(parsed_output, constraints)

        assert result.passed is False


class TestCheckLogicRange:
    """range constraint 테스트"""

    def test_range_pass(self):
        """target 필드가 min~max 범위 내면 통과"""
        parsed_output = {"confidence": 0.85}
        constraints: list[LogicConstraint] = [
            {"type": "range", "target": "confidence", "min": 0.7, "max": 1.0}
        ]

        result = check_logic(parsed_output, constraints)

        assert result.passed is True

    def test_range_fail_below_min(self):
        """min보다 작으면 실패"""
        parsed_output = {"confidence": 0.5}
        constraints: list[LogicConstraint] = [
            {"type": "range", "target": "confidence", "min": 0.7}
        ]

        result = check_logic(parsed_output, constraints)

        assert result.passed is False


class TestCheckLogicRegex:
    """regex constraint 테스트"""

    def test_regex_pass(self):
        """pattern과 매칭되면 통과"""
        parsed_output = {"verdict": "TRUE"}
        constraints: list[LogicConstraint] = [
            {"type": "regex", "target": "verdict", "pattern": "^(TRUE|FALSE)$"}
        ]

        result = check_logic(parsed_output, constraints)

        assert result.passed is True

    def test_regex_fail(self):
        """pattern과 매칭되지 않으면 실패"""
        parsed_output = {"verdict": "MAYBE"}
        constraints: list[LogicConstraint] = [
            {"type": "regex", "target": "verdict", "pattern": "^(TRUE|FALSE)$"}
        ]

        result = check_logic(parsed_output, constraints)

        assert result.passed is False


class TestCheckLogicMaxLength:
    """max_length constraint 테스트"""

    def test_max_length_pass(self):
        """길이가 value 이하면 통과"""
        parsed_output = {"reasoning": "짧은 설명"}
        constraints: list[LogicConstraint] = [
            {"type": "max_length", "target": "reasoning", "value": 100}
        ]

        result = check_logic(parsed_output, constraints)

        assert result.passed is True

    def test_max_length_fail(self):
        """길이가 value 초과면 실패"""
        parsed_output = {"reasoning": "이것은 매우 긴 설명 텍스트입니다"}
        constraints: list[LogicConstraint] = [
            {"type": "max_length", "target": "reasoning", "value": 10}
        ]

        result = check_logic(parsed_output, constraints)

        assert result.passed is False


class TestCheckLogicEdgeCases:
    """엣지 케이스 테스트"""

    def test_empty_constraints_pass(self):
        """constraints가 비어있으면 통과"""
        parsed_output = {"verdict": "TRUE"}
        constraints: list[LogicConstraint] = []

        result = check_logic(parsed_output, constraints)

        assert result.passed is True

    def test_missing_target_field_fail(self):
        """target 필드가 없으면 실패"""
        parsed_output = {"verdict": "TRUE"}
        constraints: list[LogicConstraint] = [
            {"type": "contains", "target": "nonexistent", "value": "x"}
        ]

        result = check_logic(parsed_output, constraints)

        assert result.passed is False
        assert result.results[0].message is not None

    def test_multiple_constraints_all_pass(self):
        """모든 constraint 통과 시 pass"""
        parsed_output = {"verdict": "TRUE", "confidence": 0.9}
        constraints: list[LogicConstraint] = [
            {"type": "contains", "target": "verdict", "value": "TRUE"},
            {"type": "range", "target": "confidence", "min": 0.8},
        ]

        result = check_logic(parsed_output, constraints)

        assert result.passed is True
        assert len(result.results) == 2

    def test_multiple_constraints_one_fail(self):
        """하나라도 실패하면 fail"""
        parsed_output = {"verdict": "TRUE", "confidence": 0.5}
        constraints: list[LogicConstraint] = [
            {"type": "contains", "target": "verdict", "value": "TRUE"},
            {"type": "range", "target": "confidence", "min": 0.8},
        ]

        result = check_logic(parsed_output, constraints)

        assert result.passed is False
