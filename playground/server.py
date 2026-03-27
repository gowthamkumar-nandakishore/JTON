#!/usr/bin/env python3
"""
JTON Playground Server
======================
Serves the playground UI and handles encode/decode/hint API calls.

Usage:
    python playground/server.py          # default port 7700
    python playground/server.py --port 8080

Then open http://localhost:7700 in your browser.

Optional: pip install tiktoken  (enables live token counts)
"""

import argparse
import json
import os
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

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
    def _count(text: str) -> int:  # fallback: char/4 approximation
        return len(text) // 4

PLAYGROUND_DIR = Path(__file__).parent


class PlaygroundHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quiet log
        pass

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._serve_file(PLAYGROUND_DIR / "index.html", "text/html")
        else:
            self._404()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
        except Exception:
            self._json({"error": "Invalid request JSON"}, 400)
            return

        path = self.path.split("?")[0]
        if path == "/encode":
            self._handle_encode(data)
        elif path == "/decode":
            self._handle_decode(data)
        elif path == "/hint":
            self._handle_hint(data)
        elif path == "/tokens":
            self._handle_tokens(data)
        else:
            self._404()

    def _handle_encode(self, data: dict):
        try:
            inp = data.get("input", "")
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

            # Round-trip check
            try:
                rt_parsed = jton.loads(output)
                roundtrip_ok = (rt_parsed == parsed)
            except Exception:
                roundtrip_ok = False

            # Char savings vs compact JSON
            json_compact = _json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
            char_savings = (len(json_compact) - len(output)) / max(len(json_compact), 1) * 100

            json_dump_kwargs = {"ensure_ascii": False}
            if indent:
                json_dump_kwargs["indent"] = int(indent)
            else:
                json_dump_kwargs["separators"] = (",", ":")

            _, json_encode_ms = _bench(lambda: _json.dumps(parsed_json, **json_dump_kwargs))
            _, jton_encode_ms = _bench(lambda: jton.dumps(parsed, **opts))

            # Token counts (if tiktoken available)
            json_pretty = _json.dumps(parsed, indent=2, ensure_ascii=False)
            TOON_ref = format_toon(parsed)
            token_counts = {
                "json_pretty":  _count(json_pretty),
                "json_compact": _count(json_compact),
                "TOON":         _count(TOON_ref),
                "JTON":         _count(output),
            }

            self._json({
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
            self._json({"error": str(e)})

    def _handle_decode(self, data: dict):
        try:
            inp = data.get("input", "")
            parsed = jton.loads(inp)
            import json as _json
            output = _json.dumps(parsed, indent=2, ensure_ascii=False)
            self._json({"output": output})
        except Exception as e:
            self._json({"error": str(e)})

    def _handle_hint(self, data: dict):
        style = data.get("style", "zen_grid")
        hint = jton.format_hint(style)
        self._json({"hint": hint})

    def _handle_tokens(self, data: dict):
        """Return detailed token breakdown across all formats for comparison."""
        try:
            import json as _json
            inp = data.get("input", "")
            parsed = jton.loads(inp)

            json_compact = _json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
            json_pretty  = _json.dumps(parsed, indent=2, ensure_ascii=False)
            TOON_ref     = format_toon(parsed)
            JTON_default = jton.dumps(parsed, zen_grid=True, row_count=True)
            JTON_tab     = jton.dumps(parsed, zen_grid=True, row_count=True, delimiter="tab")
            JTON_bare    = jton.dumps(parsed, zen_grid=True, row_count=True, bare_strings=True, implicit_null=True)
            JTON_multi   = jton.dumps(parsed, zen_grid=True, multiline_zen=True)

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

            self._json({
                "has_tiktoken": HAS_TIKTOKEN,
                "formats": [
                    _entry(json_pretty,  "JSON (pretty)"),
                    _entry(json_compact, "JSON (compact)"),
                    _entry(TOON_ref,     "TOON (not JSON-compatible)"),
                    _entry(JTON_default, "JTON Zen Grid"),
                    _entry(JTON_tab,     "JTON Zen Grid (tab)"),
                    _entry(JTON_bare,    "JTON Zen Grid (bare+null)"),
                    _entry(JTON_multi,   "JTON Multiline"),
                ],
            })
        except Exception as e:
            self._json({"error": str(e)})

    def _serve_file(self, path: Path, content_type: str):
        try:
            content = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self._404()

    def _json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _404(self):
        self.send_response(404)
        self.end_headers()


def main():
    parser = argparse.ArgumentParser(description="JTON Playground Server")
    parser.add_argument("--port", type=int, default=7700)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    print(f"\nJTON Playground")
    print(f"   JTON v{jton.__version__}  |  SIMD: {jton.__simd__}")
    print(f"   Token counts: {'tiktoken (o200k_base)' if HAS_TIKTOKEN else 'approximation (pip install tiktoken)'}")
    print(f"\n   Open -> http://{args.host}:{args.port}\n")

    server = HTTPServer((args.host, args.port), PlaygroundHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n   Stopped.")


if __name__ == "__main__":
    main()


