"""Shared type definitions for the PRS backend."""

from typing import TypedDict


class HealthResponse(TypedDict):
    """Health check endpoint response."""

    status: str
    timestamp: str


class LogicConstraint(TypedDict, total=False):
    """Logic constraint definition for dataset rows and evaluator profiles.

    Types:
    - contains: target string must be present
    - not_contains: target string must be absent
    - range: numeric value must be within min/max
    - regex: must match pattern
    - max_length: string length limit
    """

    type: str  # contains, not_contains, range, regex, max_length
    value: str | int | float
    field: str | None
    min: float | None
    max: float | None
    pattern: str | None


class LogicCheckResult(TypedDict):
    """Result of a single logic constraint check."""

    constraint_type: str
    passed: bool
    message: str | None


class ParsedOutput(TypedDict, total=False):
    """Parsed LLM output structure.

    The actual structure varies by output_schema type,
    but common fields are defined here.
    """

    verdict: str | None
    confidence: float | None
    reasoning: str | None
