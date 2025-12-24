"""Command-line parser entrypoint for MYSON files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.parser import ParseError, parse_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse a MYSON file")
    parser.add_argument("path", type=str, help="Path to a MYSON file")
    args = parser.parse_args(argv)

    try:
        result = parse_file(Path(args.path))
    except ParseError as exc:
        sys.stderr.write(f"{exc.category} error at line {exc.line}, col {exc.column}\n")
        return 1

    print(result)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
