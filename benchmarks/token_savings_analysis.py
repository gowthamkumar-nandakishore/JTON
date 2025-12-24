"""Token/byte savings comparison for MYSON Zen Grid vs JSON.

Generates 100 objects with 5 fields, renders JSON and MYSON (Zen table),
then reports byte-size reduction and token efficiency using a simple
delimiter split. Output is a markdown table suitable for the analysis report.
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterable


def build_dataset(count: int = 100) -> list[dict[str, Any]]:
    return [
        {
            "id": i,
            "name": f"user{i}",
            "active": i % 2 == 0,
            "team": f"team{(i % 5) + 1}",
            "score": round(50 + (i * 0.37), 2),
        }
        for i in range(count)
    ]


def to_json_text(records: Iterable[dict[str, Any]]) -> str:
    # Compact separators approximate on-wire JSON
    return json.dumps(list(records), separators=(",", ":"))


def format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(value)


def to_myson_table(records: list[dict[str, Any]]) -> str:
    if not records:
        return "[: ]"
    headers = list(records[0].keys())
    header_part = ", ".join(headers)
    row_parts = []
    for record in records:
        cells = [format_value(record.get(key)) for key in headers]
        row_parts.append(", ".join(cells))
    rows_str = "; ".join(row_parts)
    return f"[: {header_part}; {rows_str} ]"


def naive_tokens(text: str) -> int:
    # Split on common delimiters to approximate token count savings from removing quotes/braces
    parts = re.split(r"[\s\[\]\{\},:;]+", text)
    return len([p for p in parts if p])


def byte_size(text: str) -> int:
    return len(text.encode("utf-8"))


def main() -> int:
    data = build_dataset()

    json_text = to_json_text(data)
    myson_text = to_myson_table(data)

    json_tokens = naive_tokens(json_text)
    myson_tokens = naive_tokens(myson_text)

    json_bytes = byte_size(json_text)
    myson_bytes = byte_size(myson_text)

    byte_delta = json_bytes - myson_bytes
    byte_reduction_pct = (byte_delta / json_bytes * 100) if json_bytes else 0.0
    token_delta = json_tokens - myson_tokens
    token_reduction_pct = (token_delta / json_tokens * 100) if json_tokens else 0.0

    print("| Format | Tokens | Bytes | Byte Delta | Byte Reduction % | Token Reduction % |")
    print("|--------|--------|-------|------------|------------------|-------------------|")
    print(f"| JSON   | {json_tokens} | {json_bytes} | — | — | — |")
    print(
        f"| MYSON  | {myson_tokens} | {myson_bytes} | {byte_delta} | {byte_reduction_pct:.2f}% | {token_reduction_pct:.2f}% |"
    )

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
