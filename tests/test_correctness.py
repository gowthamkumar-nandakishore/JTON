#!/usr/bin/env python3
"""
Pytest-based correctness tests using real-world JSON files.
Compares stdlib json vs myson_fast for parity.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    import myson_fast  # type: ignore
except ImportError:  # pragma: no cover - fallback for local runs without extension built
    from src.tokenizer import Tokenizer
    from src.parser import Parser

    class myson_fast:  # type: ignore
        @staticmethod
        def loads(text: str):
            tokenizer = Tokenizer(text)
            parser = Parser(tokenizer.tokens())
            return parser.parse()


TEST_FILES = [
    "canada.json",
    "citm_catalog.json",
    "github.json",
    "twitter.json",
]


def _load_test_file(filename: str) -> str:
    path = Path(__file__).parent.parent / "test_data" / filename
    if not path.exists():
        pytest.skip(f"missing test data: {filename}")
    return path.read_text()


@pytest.mark.parametrize("filename", TEST_FILES)
def test_parse_correctness(filename: str) -> None:
    data = _load_test_file(filename)

    stdlib_result = json.loads(data)
    myson_result = myson_fast.loads(data)

    assert myson_result == stdlib_result
