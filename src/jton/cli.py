"""
JTON — command-line tool for JSON ↔ JTON / Zen Grid conversion.

Usage examples
--------------
  JTON input.json                      # encode JSON → Zen Grid (stdout)
  JTON input.json -o output.JTON       # encode to file
  JTON input.JTON -o output.json       # decode Zen Grid → JSON
  JTON input.json --stats              # show token savings
  echo '{"x":1}' | JTON               # pipe stdin
  JTON input.json --no-zen-grid        # plain compact JSON (no Zen Grid)
  JTON input.json --tab                # tab-delimited Zen Grid
  JTON input.json --indent 2           # pretty-print JSON
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="JTON",
        description=(
            "JTON — ultra-fast JSON parser with token-efficient Zen Grid encoding.\n"
            "Encodes JSON to Zen Grid by default; auto-detects decode from .JTON/.toon extension."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "input",
        nargs="?",
        metavar="FILE",
        help="Input file (.json → encode, .JTON/.toon → decode). Reads stdin if omitted.",
    )
    p.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="Write output to FILE instead of stdout.",
    )
    p.add_argument(
        "--decode",
        action="store_true",
        help="Force decode mode: Zen Grid → JSON (auto-detected from .JTON/.toon extension).",
    )
    p.add_argument(
        "--no-zen-grid",
        dest="zen_grid",
        action="store_false",
        default=True,
        help="Disable Zen Grid; emit compact JSON instead.",
    )
    p.add_argument(
        "--no-row-count",
        dest="row_count",
        action="store_false",
        default=True,
        help="Omit [N] row count from Zen Grid header.",
    )
    p.add_argument(
        "--tab",
        action="store_true",
        help="Use tab delimiter in Zen Grid (maximum token savings).",
    )
    p.add_argument(
        "--pipe",
        action="store_true",
        help="Use pipe (|) delimiter in Zen Grid.",
    )
    p.add_argument(
        "--bare-strings",
        action="store_true",
        help="Write identifier string values without quotes in Zen Grid cells.",
    )
    p.add_argument(
        "--implicit-null",
        action="store_true",
        help="Write missing/null Zen Grid cells as empty.",
    )
    p.add_argument(
        "--indent",
        type=int,
        metavar="N",
        help="Pretty-print output with N spaces per indent level.",
    )
    p.add_argument(
        "--stats",
        action="store_true",
        help="Print token and byte savings summary to stderr.",
    )
    p.add_argument(
        "--hint",
        metavar="STYLE",
        nargs="?",
        const="zen_grid",
        help=(
            "Print an LLM system-prompt hint and exit. "
            "STYLE: zen_grid (default), zen_grid_rowcount, multiline, tab."
        ),
    )
    p.add_argument(
        "--version",
        action="store_true",
        help="Print JTON version and exit.",
    )
    return p


def _detect_decode(path: str | None, force: bool) -> bool:
    """Return True if we should decode (Zen Grid → JSON)."""
    if force:
        return True
    if path and Path(path).suffix.lower() in (".JTON", ".toon"):
        return True
    return False


def _token_stats(original: str, encoded: str) -> None:
    """Print a simple token-savings summary using tiktoken (if installed)."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("o200k_base")
        t_orig = len(enc.encode(original))
        t_new  = len(enc.encode(encoded))
        saved  = t_orig - t_new
        pct    = saved / t_orig * 100 if t_orig else 0.0
        print(
            f"  Tokens:  {t_orig:,} → {t_new:,}  (−{pct:.1f}%,  {saved:+,} tokens)\n"
            f"  Chars:   {len(original):,} → {len(encoded):,}",
            file=sys.stderr,
        )
    except ImportError:
        chars_pct = (len(original) - len(encoded)) / len(original) * 100 if original else 0.0
        saved_c   = len(original) - len(encoded)
        print(
            f"  Chars:   {len(original):,} → {len(encoded):,}  (−{chars_pct:.1f}%,  {saved_c:+,} chars)\n"
            "  (install tiktoken for token counts: pip install tiktoken)",
            file=sys.stderr,
        )


def main() -> None:
    import jton  # imported here to avoid circular import at module level

    args = _build_parser().parse_args()

    # --version
    if args.version:
        print(f"JTON {jton.__version__} [{jton.__simd__}]")
        return

    # --hint
    if args.hint is not None:
        print(jton.format_hint(args.hint))
        return

    # Read input
    if args.input:
        raw = Path(args.input).read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()

    decode_mode = _detect_decode(args.input, args.decode)

    if decode_mode:
        # Zen Grid / JTON → JSON
        parsed = jton.loads(raw)
        if args.indent is not None:
            result = json.dumps(parsed, indent=args.indent, ensure_ascii=False)
        else:
            result = json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
    else:
        # JSON → Zen Grid
        # If input is JSON, parse it first so we handle pretty-JSON, comments-free, etc.
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            # Might already be JTON — round-trip it
            parsed = jton.loads(raw)

        delimiter = "tab" if args.tab else ("pipe" if args.pipe else "comma")
        result = jton.dumps(
            parsed,
            zen_grid=args.zen_grid,
            row_count=args.row_count,
            bare_strings=args.bare_strings,
            implicit_null=args.implicit_null,
            indent=args.indent,
            delimiter=delimiter,
        )

    # --stats
    if args.stats and not decode_mode:
        print("── JTON token savings ──────────────────", file=sys.stderr)
        _token_stats(raw, result)

    # Write output
    if args.output:
        Path(args.output).write_text(result, encoding="utf-8")
    else:
        print(result)


if __name__ == "__main__":
    main()


