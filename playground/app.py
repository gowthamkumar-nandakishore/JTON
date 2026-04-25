"""
JTON Playground — Flask app for Render deployment.

Wraps the same encode/decode/hint/tokens logic from server.py
in a Flask app suitable for production hosting.
"""

import json
import os
import sys
import time
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory

# ── Ensure the package is importable ──────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
import jton  # noqa: E402
from benchmarks.formatters import format_toon  # noqa: E402

# ── Optional: tiktoken for live token counts ──────────────────────────────────
try:
    import tiktoken
    _enc = tiktoken.get_encoding("o200k_base")
    def _count(text: str) -> int:
        return len(_enc.encode(text))
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False
    def _count(text: str) -> int:
        return len(text) // 4

PLAYGROUND_DIR = Path(__file__).parent

app = Flask(__name__, static_folder=None)

# ── Limit request size to 1 MB ────────────────────────────────────────────────
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024


@app.route("/")
@app.route("/index.html")
def index():
    return send_from_directory(PLAYGROUND_DIR, "index.html")


@app.route("/encode", methods=["POST"])
def encode():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid request JSON"}), 400
    try:
        inp = data.get("input", "")
        if len(inp) > 500_000:
            return jsonify({"error": "Input too large (max 500 KB)"}), 400

        opts = {
            "zen_grid":      bool(data.get("zen_grid", True)),
            "row_count":     bool(data.get("row_count", True)),
            "multiline_zen": bool(data.get("multiline_zen", False)),
            "bare_strings":  bool(data.get("bare_strings", False)),
            "implicit_null": bool(data.get("implicit_null", False)),
            "unquoted_keys": bool(data.get("unquoted_keys", False)),
            "delimiter":     str(data.get("delimiter", "comma")),
        }
        indent = data.get("indent")
        if indent:
            opts["indent"] = int(indent)

        import json as _json

        bench_loops = 50 if len(inp) < 50_000 else 10

        def _bench(fn, loops=bench_loops):
            t0 = time.perf_counter()
            result = None
            for _ in range(loops):
                result = fn()
            return result, ((time.perf_counter() - t0) * 1000 / loops)

        parsed_json, json_parse_ms = _bench(lambda: _json.loads(inp))
        parsed, jton_parse_ms = _bench(lambda: jton.loads(inp))

        t0 = time.perf_counter()
        output = jton.dumps(parsed, **opts)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        try:
            rt_parsed = jton.loads(output)
            roundtrip_ok = (rt_parsed == parsed)
        except Exception:
            roundtrip_ok = False

        json_compact = _json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
        char_savings = (len(json_compact) - len(output)) / max(len(json_compact), 1) * 100

        json_dump_kwargs = {"ensure_ascii": False}
        if indent:
            json_dump_kwargs["indent"] = int(indent)
        else:
            json_dump_kwargs["separators"] = (",", ":")

        _, json_encode_ms = _bench(lambda: _json.dumps(parsed_json, **json_dump_kwargs))
        _, jton_encode_ms = _bench(lambda: jton.dumps(parsed, **opts))

        json_pretty = _json.dumps(parsed, indent=2, ensure_ascii=False)
        toon_ref = format_toon(parsed)
        token_counts = {
            "json_pretty":  _count(json_pretty),
            "json_compact": _count(json_compact),
            "TOON":         _count(toon_ref),
            "JTON":         _count(output),
        }

        return jsonify({
            "output": output,
            "elapsed_ms": round(elapsed_ms, 2),
            "char_savings": round(char_savings, 2),
            "token_counts": token_counts,
            "roundtrip_ok": roundtrip_ok,
            "speed_metrics": {
                "json_parse_ms": round(json_parse_ms, 4),
                "jton_parse_ms": round(jton_parse_ms, 4),
                "json_encode_ms": round(json_encode_ms, 4),
                "jton_encode_ms": round(jton_encode_ms, 4),
            },
            "has_tiktoken": HAS_TIKTOKEN,
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/decode", methods=["POST"])
def decode():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid request JSON"}), 400
    try:
        inp = data.get("input", "")
        if len(inp) > 500_000:
            return jsonify({"error": "Input too large (max 500 KB)"}), 400
        parsed = jton.loads(inp)
        import json as _json
        output = _json.dumps(parsed, indent=2, ensure_ascii=False)
        return jsonify({"output": output})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/hint", methods=["POST"])
def hint():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid request JSON"}), 400
    style = data.get("style", "zen_grid")
    h = jton.format_hint(style)
    return jsonify({"hint": h})


@app.route("/tokens", methods=["POST"])
def tokens():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid request JSON"}), 400
    try:
        import json as _json
        inp = data.get("input", "")
        if len(inp) > 500_000:
            return jsonify({"error": "Input too large (max 500 KB)"}), 400
        parsed = jton.loads(inp)

        json_compact = _json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
        json_pretty  = _json.dumps(parsed, indent=2, ensure_ascii=False)
        toon_ref     = format_toon(parsed)
        jton_default = jton.dumps(parsed, zen_grid=True, row_count=True)
        jton_tab     = jton.dumps(parsed, zen_grid=True, row_count=True, delimiter="tab")
        jton_bare    = jton.dumps(parsed, zen_grid=True, row_count=True, bare_strings=True, implicit_null=True)
        jton_multi   = jton.dumps(parsed, zen_grid=True, multiline_zen=True)

        baseline = _count(json_compact)
        def _entry(text, label):
            t = _count(text)
            savings = (baseline - t) / baseline * 100 if baseline else 0.0
            return {
                "label":   label,
                "tokens":  t,
                "chars":   len(text),
                "savings": round(savings, 1),
            }

        return jsonify({
            "has_tiktoken": HAS_TIKTOKEN,
            "formats": [
                _entry(json_pretty,  "JSON (pretty)"),
                _entry(json_compact, "JSON (compact)"),
                _entry(toon_ref,     "TOON (not JSON-compatible)"),
                _entry(jton_default, "JTON Zen Grid"),
                _entry(jton_tab,     "JTON Zen Grid (tab)"),
                _entry(jton_bare,    "JTON Zen Grid (bare+null)"),
                _entry(jton_multi,   "JTON Multiline"),
            ],
        })
    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7700))
    app.run(host="0.0.0.0", port=port)
