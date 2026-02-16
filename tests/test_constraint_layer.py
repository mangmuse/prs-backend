from src.common.types import (
    ContainsConstraint,
    MaxLengthConstraint,
    NotContainsConstraint,
    RangeConstraint,
    RegexConstraint,
)
from src.runs.evaluator.constraint_layer import check_constraints


class TestCheckConstraintsContains:
    """contains constraint 테스트"""

    def test_contains_pass(self):
        """target 필드에 value가 포함되면 통과"""
        parsed_output = {"verdict": "TRUE", "reasoning": "정확한 판단입니다"}
        constraints = [
            ContainsConstraint(type="contains", target="verdict", value="TRUE")
        ]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is True
        assert len(result.results) == 1
        assert result.results[0].passed is True

    def test_contains_fail(self):
        """target 필드에 value가 없으면 실패"""
        parsed_output = {"verdict": "FALSE"}
        constraints = [
            ContainsConstraint(type="contains", target="verdict", value="TRUE")
        ]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is False
        assert result.results[0].passed is False
        assert result.results[0].message is not None


class TestCheckConstraintsNotContains:
    """not_contains constraint 테스트"""

    def test_not_contains_pass(self):
        """target 필드에 value가 없으면 통과"""
        parsed_output = {"verdict": "TRUE"}
        constraints = [
            NotContainsConstraint(type="not_contains", target="verdict", value="ERROR")
        ]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is True

    def test_not_contains_fail(self):
        """target 필드에 value가 포함되면 실패"""
        parsed_output = {"verdict": "TRUE"}
        constraints = [
            NotContainsConstraint(type="not_contains", target="verdict", value="TRUE")
        ]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is False


class TestCheckConstraintsRange:
    """range constraint 테스트"""

    def test_range_pass(self):
        """target 필드가 min~max 범위 내면 통과"""
        parsed_output = {"confidence": 0.85}
        constraints = [
            RangeConstraint(type="range", target="confidence", min=0.7, max=1.0)
        ]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is True

    def test_range_fail_below_min(self):
        """min보다 작으면 실패"""
        parsed_output = {"confidence": 0.5}
        constraints = [RangeConstraint(type="range", target="confidence", min=0.7)]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is False


class TestCheckConstraintsRegex:
    """regex constraint 테스트"""

    def test_regex_pass(self):
        """pattern과 매칭되면 통과"""
        parsed_output = {"verdict": "TRUE"}
        constraints = [
            RegexConstraint(type="regex", target="verdict", pattern="^(TRUE|FALSE)$")
        ]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is True

    def test_regex_fail(self):
        """pattern과 매칭되지 않으면 실패"""
        parsed_output = {"verdict": "MAYBE"}
        constraints = [
            RegexConstraint(type="regex", target="verdict", pattern="^(TRUE|FALSE)$")
        ]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is False


class TestCheckConstraintsMaxLength:
    """max_length constraint 테스트"""

    def test_max_length_pass(self):
        """길이가 max 이하면 통과"""
        parsed_output = {"reasoning": "짧은 설명"}
        constraints = [
            MaxLengthConstraint(type="max_length", target="reasoning", max=100)
        ]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is True

    def test_max_length_fail(self):
        """길이가 max 초과면 실패"""
        parsed_output = {"reasoning": "이것은 매우 긴 설명 텍스트입니다"}
        constraints = [
            MaxLengthConstraint(type="max_length", target="reasoning", max=10)
        ]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is False


class TestCheckConstraintsEdgeCases:
    """엣지 케이스 테스트"""

    def test_empty_constraints_pass(self):
        """constraints가 비어있으면 통과"""
        parsed_output = {"verdict": "TRUE"}
        constraints = []

        result = check_constraints(parsed_output, constraints)

        assert result.passed is True

    def test_missing_target_field_fail(self):
        """target 필드가 없으면 실패"""
        parsed_output = {"verdict": "TRUE"}
        constraints = [
            ContainsConstraint(type="contains", target="nonexistent", value="x")
        ]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is False
        assert result.results[0].message is not None

    def test_multiple_constraints_all_pass(self):
        """모든 constraint 통과 시 pass"""
        parsed_output = {"verdict": "TRUE", "confidence": 0.9}
        constraints = [
            ContainsConstraint(type="contains", target="verdict", value="TRUE"),
            RangeConstraint(type="range", target="confidence", min=0.8),
        ]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is True
        assert len(result.results) == 2

    def test_multiple_constraints_one_fail(self):
        """하나라도 실패하면 fail"""
        parsed_output = {"verdict": "TRUE", "confidence": 0.5}
        constraints = [
            ContainsConstraint(type="contains", target="verdict", value="TRUE"),
            RangeConstraint(type="range", target="confidence", min=0.8),
        ]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is False


class TestCheckConstraintsRangeEdgeCases:
    """Range constraint 엣지 케이스 테스트"""

    def test_range_min_only_pass(self):
        """min만 설정, 값 >= min이면 통과"""
        parsed_output = {"score": 0.8}
        constraints = [RangeConstraint(type="range", target="score", min=0.5)]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is True

    def test_range_min_only_fail(self):
        """min만 설정, 값 < min이면 실패"""
        parsed_output = {"score": 0.3}
        constraints = [RangeConstraint(type="range", target="score", min=0.5)]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is False

    def test_range_max_only_pass(self):
        """max만 설정, 값 <= max이면 통과"""
        parsed_output = {"score": 0.7}
        constraints = [RangeConstraint(type="range", target="score", max=1.0)]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is True

    def test_range_max_only_fail(self):
        """max만 설정, 값 > max이면 실패"""
        parsed_output = {"score": 1.5}
        constraints = [RangeConstraint(type="range", target="score", max=1.0)]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is False

    def test_range_exact_min_boundary_pass(self):
        """값 == min이면 통과 (< 비교이므로 경계값 포함)"""
        parsed_output = {"score": 0.5}
        constraints = [RangeConstraint(type="range", target="score", min=0.5)]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is True

    def test_range_exact_max_boundary_pass(self):
        """값 == max이면 통과 (> 비교이므로 경계값 포함)"""
        parsed_output = {"score": 1.0}
        constraints = [RangeConstraint(type="range", target="score", max=1.0)]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is True

    def test_range_non_numeric_value_fails(self):
        """문자열 입력 시 '숫자가 아닌 값' 에러"""
        parsed_output = {"score": "not_a_number"}
        constraints = [RangeConstraint(type="range", target="score", min=0.0)]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is False
        assert result.results[0].message is not None
        assert "숫자가 아닌 값" in result.results[0].message


class TestCheckConstraintsMiscEdgeCases:
    """기타 constraint 엣지 케이스 테스트"""

    def test_contains_case_sensitive(self):
        """대소문자 구분하여 'TRUE'가 'true'에 포함되지 않으면 실패"""
        parsed_output = {"verdict": "true"}
        constraints = [
            ContainsConstraint(type="contains", target="verdict", value="TRUE")
        ]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is False

    def test_max_length_exact_boundary_pass(self):
        """len(value) == max이면 통과 (<= 비교)"""
        parsed_output = {"text": "12345"}
        constraints = [MaxLengthConstraint(type="max_length", target="text", max=5)]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is True

    def test_multiple_constraints_same_type(self):
        """같은 타입 contains 2개가 모두 검사되는지"""
        parsed_output = {"text": "hello world foo"}
        constraints = [
            ContainsConstraint(type="contains", target="text", value="hello"),
            ContainsConstraint(type="contains", target="text", value="foo"),
        ]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is True
        assert len(result.results) == 2

    def test_not_contains_case_sensitive(self):
        """대소문자 구분: 'TRUE' not in 'true' → 통과"""
        parsed_output = {"verdict": "true"}
        constraints = [
            NotContainsConstraint(type="not_contains", target="verdict", value="TRUE")
        ]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is True

    def test_regex_invalid_pattern_fails(self):
        """잘못된 정규식 패턴 처리"""
        parsed_output = {"text": "anything"}
        constraints = [
            RegexConstraint(type="regex", target="text", pattern="[unclosed")
        ]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is False
        assert result.results[0].message is not None
        assert "잘못된 정규식" in result.results[0].message

    def test_constraint_none_value_in_field_fails(self):
        """대상 필드 값이 None일 때 range constraint 실패"""
        parsed_output = {"score": None}
        constraints = [RangeConstraint(type="range", target="score", min=0.0)]

        result = check_constraints(parsed_output, constraints)

        assert result.passed is False
        assert result.results[0].message is not None
        assert "숫자가 아닌 값" in result.results[0].message
