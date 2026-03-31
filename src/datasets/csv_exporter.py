"""데이터셋 행을 CSV 문자열로 변환하는 모듈."""

import csv
import io
from typing import Any


def rows_to_csv(rows: list[dict[str, Any]]) -> str:
    """행 목록을 CSV 문자열로 변환한다."""
    if not rows:
        return "expected_output,tags\n"

    all_keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row["input_data"]:
            if key not in seen:
                all_keys.append(key)
                seen.add(key)

    fieldnames = all_keys + ["expected_output", "tags"]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for row in rows:
        csv_row: dict[str, str] = {}
        for key in all_keys:
            csv_row[key] = str(row["input_data"].get(key, ""))
        csv_row["expected_output"] = row["expected_output"]
        tags = row.get("tags")
        csv_row["tags"] = ",".join(tags) if tags else ""
        writer.writerow(csv_row)

    return output.getvalue().replace("\r\n", "\n")
