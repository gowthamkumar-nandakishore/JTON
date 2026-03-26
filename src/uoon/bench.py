#!/usr/bin/env python3
"""
python -m uoon.bench <file.json>

Quick benchmark comparing UOON vs stdlib json vs orjson for:
  - Parse speed (MB/s)
  - Serialize speed (MB/s)
  - Token count (requires tiktoken)
  - Character count

Usage:
    python -m uoon.bench benchmarks/twitter.json
    python -m uoon.bench benchmarks/canada.json
    python -m uoon.bench my_data.json
"""

import sys
import json
import time
import os
from pathlib import Path

# Add src to path for development installs
_src = Path(__file__).parent.parent.parent
if (_src / "uoon").exists():
    sys.path.insert(0, str(_src))

import uoon


def bench_parse(parser, data_bytes: bytes, iters: int) -> float:
    """Returns MB/s throughput."""
    # Warmup
    for _ in range(min(3, iters)):
        parser(data_bytes)
    t = time.perf_counter()
    for _ in range(iters):
        parser(data_bytes)
    elapsed = time.perf_counter() - t
    return len(data_bytes) * iters / elapsed / 1e6


def bench_serialize(serializer, obj, iters: int) -> float:
    """Returns MB/s throughput (based on output size)."""
    result = serializer(obj)
    out_bytes = len(result.encode() if isinstance(result, str) else result)
    # Warmup
    for _ in range(min(3, iters)):
        serializer(obj)
    t = time.perf_counter()
    for _ in range(iters):
        serializer(obj)
    elapsed = time.perf_counter() - t
    return out_bytes * iters / elapsed / 1e6


def count_tokens(text: str) -> int:
    try:
        import tiktoken
        enc = tiktoken.get_encoding("o200k_base")
        return len(enc.encode(text))
    except ImportError:
        return -1  # tiktoken not installed


def format_bar(value: float, max_value: float, width: int = 30) -> str:
    filled = int((value / max_value) * width) if max_value > 0 else 0
    return "█" * filled + "░" * (width - filled)


def run(path: str):
    file_path = Path(path)
    if not file_path.exists():
        print(f"❌ File not found: {path}")
        sys.exit(1)

    data_bytes = file_path.read_bytes()
    data_mb = len(data_bytes) / 1e6
    print(f"\n{'═' * 65}")
    print(f" UOON Benchmark: {file_path.name}  ({data_mb:.2f} MB)")
    print(f"{'═' * 65}\n")

    # Determine iteration count based on file size
    iters = max(3, min(100, int(50 / data_mb)))

    # Parse the data first
    try:
        obj = json.loads(data_bytes)
    except Exception as e:
        print(f"❌ Failed to parse file as JSON: {e}")
        sys.exit(1)

    # ── Parse speed ────────────────────────────────────────────────────────────
    print("📖 PARSE SPEED")
    print("-" * 65)

    results = {}

    # stdlib json
    try:
        results["stdlib"] = bench_parse(json.loads, data_bytes, iters)
    except Exception as e:
        results["stdlib"] = 0.0
        print(f"  stdlib json: ERROR {e}")

    # orjson
    try:
        import orjson
        results["orjson"] = bench_parse(orjson.loads, data_bytes, iters)
    except ImportError:
        results["orjson"] = 0.0

    # uoon
    try:
        results["uoon"] = bench_parse(uoon.loads, data_bytes, iters)
    except Exception as e:
        results["uoon"] = 0.0
        print(f"  UOON: ERROR {e}")

    max_speed = max(results.values()) or 1
    for name, speed in results.items():
        if speed == 0:
            print(f"  {'UOON' if name=='uoon' else name.ljust(9)}: N/A")
            continue
        bar = format_bar(speed, max_speed)
        ratio = f"({speed/results.get('orjson', speed)*100:.0f}% of orjson)" if results.get("orjson") else ""
        print(f"  {name.ljust(9)}: {bar}  {speed:6.1f} MB/s  {ratio}")

    # ── Serialize speed ────────────────────────────────────────────────────────
    print("\n📝 SERIALIZE SPEED")
    print("-" * 65)

    ser_results = {}

    try:
        ser_results["json compact"] = bench_serialize(
            lambda o: json.dumps(o, separators=(",", ":")), obj, iters
        )
    except Exception:
        ser_results["json compact"] = 0.0

    try:
        import orjson
        ser_results["orjson"] = bench_serialize(
            lambda o: orjson.dumps(o).decode(), obj, iters
        )
    except ImportError:
        pass

    try:
        ser_results["uoon(zen)"] = bench_serialize(
            lambda o: uoon.dumps(o, zen_grid=True), obj, iters
        )
        ser_results["uoon(json)"] = bench_serialize(
            lambda o: uoon.dumps(o, zen_grid=False), obj, iters
        )
    except Exception as e:
        print(f"  UOON serialize: ERROR {e}")

    max_ser = max(ser_results.values()) or 1
    for name, speed in ser_results.items():
        if speed == 0:
            continue
        bar = format_bar(speed, max_ser)
        print(f"  {name.ljust(12)}: {bar}  {speed:6.1f} MB/s")

    # ── Token / character comparison ───────────────────────────────────────────
    print("\n🪙 TOKEN EFFICIENCY")
    print("-" * 65)

    formats = {
        "JSON pretty": json.dumps(obj, indent=2),
        "JSON compact": json.dumps(obj, separators=(",", ":")),
        "UOON (zen)": uoon.dumps(obj, zen_grid=True),
        "UOON (keys)": uoon.dumps(obj, unquoted_keys=True, zen_grid=True),
    }

    try:
        import orjson
        formats["orjson"] = orjson.dumps(obj).decode()
    except ImportError:
        pass

    max_chars = max(len(v) for v in formats.values())
    token_results = {}
    for name, text in formats.items():
        chars = len(text)
        tokens = count_tokens(text)
        token_results[name] = (chars, tokens)

    json_compact_chars = token_results["JSON compact"][0]
    json_compact_tokens = token_results["JSON compact"][1]

    for name, (chars, tokens) in token_results.items():
        bar = format_bar(chars, max_chars, width=24)
        char_savings = (1 - chars / json_compact_chars) * 100 if json_compact_chars else 0
        if tokens > 0:
            tok_savings = (1 - tokens / json_compact_tokens) * 100 if json_compact_tokens > 0 else 0
            print(
                f"  {name.ljust(14)}: {bar}  {chars:8,} chars  {tokens:6,} tokens  "
                f"({char_savings:+.1f}% chars, {tok_savings:+.1f}% tokens vs JSON compact)"
            )
        else:
            print(
                f"  {name.ljust(14)}: {bar}  {chars:8,} chars  "
                f"({char_savings:+.1f}% vs JSON compact)  [install tiktoken for token counts]"
            )

    # ── Summary ────────────────────────────────────────────────────────────────
    uoon_zen_chars = token_results.get("UOON (zen)", (0, 0))[0]
    uoon_zen_tokens = token_results.get("UOON (zen)", (0, 0))[1]
    if uoon_zen_chars and json_compact_chars:
        char_reduction = (1 - uoon_zen_chars / json_compact_chars) * 100
        print(f"\n{'─' * 65}")
        if char_reduction > 0:
            print(f" ✅ UOON Zen Grid saves {char_reduction:.1f}% characters vs JSON compact")
        else:
            print(f" ℹ️  Data is not tabular — UOON Zen Grid is not applicable")
        if uoon_zen_tokens > 0 and json_compact_tokens > 0:
            tok_reduction = (1 - uoon_zen_tokens / json_compact_tokens) * 100
            print(f" ✅ UOON Zen Grid saves {tok_reduction:.1f}% LLM tokens vs JSON compact")
    print(f"{'═' * 65}\n")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("Available test files:")
        bench_dir = Path(__file__).parent.parent.parent / "benchmarks"
        if bench_dir.exists():
            for f in bench_dir.glob("*.json"):
                print(f"  {f}")
        sys.exit(0)
    run(sys.argv[1])


if __name__ == "__main__":
    main()
