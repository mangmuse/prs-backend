"""CSV 파일을 DatasetRow 형태로 파싱하는 모듈."""

import csv
import io
from typing import Any

import chardet

RESERVED_COLUMNS = {"expected_output", "tags"}


def parse_csv(raw_bytes: bytes) -> list[dict[str, Any]]:
    """CSV 바이트 데이터를 파싱하여 행 목록을 반환한다."""
    text = _decode(raw_bytes)
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        raise ValueError("CSV 헤더가 없습니다")

    headers = list(reader.fieldnames)
    _validate_headers(headers)

    input_columns = [h for h in headers if h not in RESERVED_COLUMNS]
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for i, raw_row in enumerate(reader, start=2):
        if _is_empty_row(raw_row):
            continue

        row_errors = _validate_row(raw_row, i, input_columns)
        if row_errors:
            errors.extend(row_errors)
            continue

        input_data = {col: raw_row[col] for col in input_columns}
        expected_output = raw_row["expected_output"]
        tags = _parse_tags(raw_row.get("tags"))

        rows.append(
            {
                "input_data": input_data,
                "expected_output": expected_output,
                "tags": tags,
            }
        )

    if errors:
        raise ValueError(errors)

    return rows


def _decode(raw_bytes: bytes) -> str:
    detected = chardet.detect(raw_bytes)
    encoding = detected.get("encoding") or "utf-8"
    text = raw_bytes.decode(encoding)
    return text.lstrip("\ufeff")


def _validate_headers(headers: list[str]) -> None:
    if "expected_output" not in headers:
        raise ValueError("CSV에 'expected_output' 컬럼이 필요합니다")

    if len(headers) != len(set(headers)):
        duplicates = [h for h in headers if headers.count(h) > 1]
        raise ValueError(f"중복된 컬럼명이 있습니다: {set(duplicates)}")

    input_columns = [h for h in headers if h not in RESERVED_COLUMNS]
    if not input_columns:
        raise ValueError("input_data가 될 컬럼이 최소 1개 필요합니다")


def _is_empty_row(row: dict[str, str | None]) -> bool:
    return all(not v or not v.strip() for v in row.values())


def _validate_row(
    row: dict[str, str | None], row_num: int, input_columns: list[str]
) -> list[dict[str, Any]]:
    errors = []
    expected = row.get("expected_output") or ""
    if not expected.strip():
        errors.append({"row": row_num, "reason": "expected_output이 비어있습니다"})

    for col in input_columns:
        value = row.get(col) or ""
        if not value.strip():
            errors.append({"row": row_num, "reason": f"{col}이(가) 비어있습니다"})

    return errors


def _parse_tags(value: str | None) -> list[str] | None:
    if not value or not value.strip():
        return None
    return [tag.strip() for tag in value.split(",") if tag.strip()]
