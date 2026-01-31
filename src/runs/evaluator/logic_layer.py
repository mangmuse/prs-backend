import logging
import re

from src.common.types import ConstraintType, LogicConstraint
from src.runs.schemas import ConstraintResult, LogicLayerResult

logger = logging.getLogger(__name__)

FieldValue = str | int | float | bool | None


def check_logic(
    parsed_output: dict[str, FieldValue],
    constraints: list[LogicConstraint],
) -> LogicLayerResult:
    """Logic Layer: constraint 기반 규칙 검증"""
    logger.debug("Logic 검증 시작 | constraints=%d개", len(constraints))

    if not constraints:
        logger.debug("Logic 검증 생략 | 제약조건 없음")
        return LogicLayerResult(passed=True)

    results: list[ConstraintResult] = []

    for constraint in constraints:
        constraint_type = constraint.get("type", "")
        target = constraint.get("target", "")

        if target not in parsed_output:
            logger.debug("Logic 실패 | 필드 '%s' 없음", target)
            results.append(
                ConstraintResult(
                    constraint_type=constraint_type,
                    target=target,
                    passed=False,
                    message=f"필드 '{target}'이(가) 출력에 존재하지 않습니다",
                )
            )
            continue

        value = parsed_output[target]
        result = _check_constraint(constraint_type, value, constraint)
        result.target = target
        results.append(result)
        logger.debug(
            "Logic 제약조건 | type=%s, target=%s, value=%s, passed=%s",
            constraint_type,
            target,
            value,
            result.passed,
        )

    all_passed = all(r.passed for r in results)
    logger.debug("Logic 결과 | passed=%s, results=%d개", all_passed, len(results))
    return LogicLayerResult(passed=all_passed, results=results)


def _check_constraint(
    constraint_type: str,
    value: FieldValue,
    constraint: LogicConstraint,
) -> ConstraintResult:
    """개별 constraint 타입별 검사"""
    if constraint_type == ConstraintType.CONTAINS:
        return _check_contains(value, constraint.get("value", ""))

    if constraint_type == ConstraintType.NOT_CONTAINS:
        return _check_not_contains(value, constraint.get("value", ""))

    if constraint_type == ConstraintType.RANGE:
        return _check_range(value, constraint.get("min"), constraint.get("max"))

    if constraint_type == ConstraintType.REGEX:
        pattern = constraint.get("pattern")
        if pattern is None:
            pattern = ""
        return _check_regex(value, pattern)

    if constraint_type == ConstraintType.MAX_LENGTH:
        max_len = constraint.get("value", 0)
        return _check_max_length(value, int(max_len) if max_len else 0)

    return ConstraintResult(
        constraint_type=constraint_type,
        target="",
        passed=False,
        message=f"알 수 없는 constraint 타입: {constraint_type}",
    )


def _check_contains(value: FieldValue, expected: str | int | float) -> ConstraintResult:
    str_value = str(value)
    str_expected = str(expected)
    passed = str_expected in str_value
    return ConstraintResult(
        constraint_type=ConstraintType.CONTAINS,
        target="",
        passed=passed,
        message=None if passed else f"'{str_expected}'이(가) 포함되지 않음",
    )


def _check_not_contains(value: FieldValue, expected: str | int | float) -> ConstraintResult:
    str_value = str(value)
    str_expected = str(expected)
    passed = str_expected not in str_value
    return ConstraintResult(
        constraint_type=ConstraintType.NOT_CONTAINS,
        target="",
        passed=passed,
        message=None if passed else f"'{str_expected}'이(가) 포함됨",
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

    return ConstraintResult(constraint_type=ConstraintType.RANGE, target="", passed=True)


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
