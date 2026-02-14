import logging
import re

from src.common.types import (
    ConstraintType,
    ContainsConstraint,
    LogicConstraint,
    NotContainsConstraint,
    RangeConstraint,
    RegexConstraint,
)
from src.runs.schemas import ConstraintLayerResult, ConstraintResult

logger = logging.getLogger(__name__)

FieldValue = str | int | float | bool | None


def check_constraints(
    parsed_output: dict[str, FieldValue],
    constraints: list[LogicConstraint],
) -> ConstraintLayerResult:
    """Constraint Layer: constraint 기반 규칙 검증"""
    logger.debug("Constraint 검증 시작 | constraints=%d개", len(constraints))

    if not constraints:
        logger.debug("Constraint 검증 생략 | 제약조건 없음")
        return ConstraintLayerResult(passed=True)

    results: list[ConstraintResult] = []

    for constraint in constraints:
        target = constraint.target

        if target not in parsed_output:
            logger.debug("Constraint 실패 | 필드 '%s' 없음", target)
            results.append(
                ConstraintResult(
                    constraint_type=constraint.type,
                    target=target,
                    passed=False,
                    message=f"필드 '{target}'이(가) 출력에 존재하지 않습니다",
                )
            )
            continue

        value = parsed_output[target]
        result = _check_constraint(constraint, value)
        result.target = target
        results.append(result)
        logger.debug(
            "Constraint 제약조건 | type=%s, target=%s, value=%s, passed=%s",
            constraint.type,
            target,
            value,
            result.passed,
        )

    all_passed = all(r.passed for r in results)
    logger.debug("Constraint 결과 | passed=%s, results=%d개", all_passed, len(results))
    return ConstraintLayerResult(passed=all_passed, results=results)


def _check_constraint(
    constraint: LogicConstraint,
    value: FieldValue,
) -> ConstraintResult:
    """개별 constraint 타입별 검사 (isinstance 기반 타입 narrowing)"""
    if isinstance(constraint, ContainsConstraint):
        return _check_contains(value, constraint.value)

    if isinstance(constraint, NotContainsConstraint):
        return _check_not_contains(value, constraint.value)

    if isinstance(constraint, RangeConstraint):
        return _check_range(value, constraint.min, constraint.max)

    if isinstance(constraint, RegexConstraint):
        return _check_regex(value, constraint.pattern)

    return _check_max_length(value, constraint.max)


def _check_contains(value: FieldValue, expected: str) -> ConstraintResult:
    str_value = str(value)
    passed = expected in str_value
    return ConstraintResult(
        constraint_type=ConstraintType.CONTAINS,
        target="",
        passed=passed,
        message=None if passed else f"'{expected}'이(가) 포함되지 않음",
    )


def _check_not_contains(value: FieldValue, expected: str) -> ConstraintResult:
    str_value = str(value)
    passed = expected not in str_value
    return ConstraintResult(
        constraint_type=ConstraintType.NOT_CONTAINS,
        target="",
        passed=passed,
        message=None if passed else f"'{expected}'이(가) 포함됨",
    )


def _check_range(
    value: FieldValue, min_val: float | None, max_val: float | None
) -> ConstraintResult:
    if value is None:
        return ConstraintResult(
            constraint_type=ConstraintType.RANGE,
            target="",
            passed=False,
            message="숫자가 아닌 값: None",
        )
    try:
        num_value = float(value)
    except (TypeError, ValueError):
        return ConstraintResult(
            constraint_type=ConstraintType.RANGE,
            target="",
            passed=False,
            message=f"숫자가 아닌 값: {value}",
        )

    if min_val is not None and num_value < min_val:
        return ConstraintResult(
            constraint_type=ConstraintType.RANGE,
            target="",
            passed=False,
            message=f"{num_value} < {min_val} (최소값 미달)",
        )

    if max_val is not None and num_value > max_val:
        return ConstraintResult(
            constraint_type=ConstraintType.RANGE,
            target="",
            passed=False,
            message=f"{num_value} > {max_val} (최대값 초과)",
        )

    return ConstraintResult(
        constraint_type=ConstraintType.RANGE, target="", passed=True
    )


def _check_regex(value: FieldValue, pattern: str) -> ConstraintResult:
    str_value = str(value)
    try:
        passed = bool(re.match(pattern, str_value))
    except re.error as e:
        return ConstraintResult(
            constraint_type=ConstraintType.REGEX,
            target="",
            passed=False,
            message=f"잘못된 정규식 패턴: {e}",
        )

    return ConstraintResult(
        constraint_type=ConstraintType.REGEX,
        target="",
        passed=passed,
        message=None if passed else f"패턴 '{pattern}'과 불일치",
    )


def _check_max_length(value: FieldValue, max_len: int) -> ConstraintResult:
    str_value = str(value)
    actual_len = len(str_value)
    passed = actual_len <= max_len
    return ConstraintResult(
        constraint_type=ConstraintType.MAX_LENGTH,
        target="",
        passed=passed,
        message=None if passed else f"길이 {actual_len} > {max_len}",
    )
