import pytest
from pydantic import TypeAdapter, ValidationError

from src.common.types import (
    ContainsConstraint,
    LogicConstraint,
    RangeConstraint,
)

LogicConstraintAdapter = TypeAdapter(LogicConstraint)


class TestLogicConstraintDiscriminatedUnion:
    """LogicConstraint discriminated union 검증"""

    def test_logic_constraint_contains_valid(self):
        """contains 타입 생성 성공"""
        result = LogicConstraintAdapter.validate_python(
            {"type": "contains", "target": "verdict", "value": "TRUE"}
        )

        assert isinstance(result, ContainsConstraint)
        assert result.value == "TRUE"

    def test_logic_constraint_range_min_only_valid(self):
        """min만 있는 range 생성 성공"""
        result = LogicConstraintAdapter.validate_python(
            {"type": "range", "target": "score", "min": 0.5}
        )

        assert isinstance(result, RangeConstraint)
        assert result.min == 0.5
        assert result.max is None

    def test_logic_constraint_range_max_only_valid(self):
        """max만 있는 range 생성 성공"""
        result = LogicConstraintAdapter.validate_python(
            {"type": "range", "target": "score", "max": 1.0}
        )

        assert isinstance(result, RangeConstraint)
        assert result.min is None
        assert result.max == 1.0

    def test_logic_constraint_invalid_type_raises_validation_error(self):
        """type='invalid' → ValidationError"""
        with pytest.raises(ValidationError):
            LogicConstraintAdapter.validate_python(
                {"type": "invalid", "target": "x", "value": "y"}
            )

    def test_logic_constraint_missing_discriminator_raises_error(self):
        """type 필드 누락 → ValidationError"""
        with pytest.raises(ValidationError):
            LogicConstraintAdapter.validate_python(
                {"target": "verdict", "value": "TRUE"}
            )

    def test_logic_constraint_contains_missing_value_raises_error(self):
        """contains에 value 누락 → ValidationError"""
        with pytest.raises(ValidationError):
            LogicConstraintAdapter.validate_python(
                {"type": "contains", "target": "verdict"}
            )

    def test_logic_constraint_regex_missing_pattern_raises_error(self):
        """regex에 pattern 누락 → ValidationError"""
        with pytest.raises(ValidationError):
            LogicConstraintAdapter.validate_python(
                {"type": "regex", "target": "verdict"}
            )
