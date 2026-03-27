"""
JTON (JSON Tabular Object Notation) — high-performance JSON superset
with SIMD-accelerated parsing and Zen Grid token-efficient serialization.

Key functions:
  loads(data)              — parse JTON/JSON → Python object
  dumps(data, **opts)      — serialize Python object → JTON/JSON string
  format_hint(style)       — LLM system-prompt primer for Zen Grid format
  token_count(data)        — compare token costs across all formats

Zen Grid format automatically converts homogeneous arrays of dicts to a
compact table syntax that reduces LLM token counts by 15–36%:

    [3: id, name, score; 1, Alice, 95; 2, Bob, 87; 3, Carol, 92 ]

dumps() options:
  zen_grid=True           — Enable Zen Grid table output (default: True)
  unquoted_keys=False     — Write identifier keys without quotes
  bare_strings=False      — Write identifier string VALUES without quotes
  implicit_null=False     — Write missing Zen Grid cells as empty
  indent=None             — Pretty-print with N spaces per indent level
  row_count=True          — Add [N] row count to Zen Grid header (default: True)
  delimiter="comma"       — "comma" (default), "tab" (max tokens), or "pipe"
"""

from .jton_core import __version__, __simd__, loads, dumps, format_hint

# Convenient aliases
encode = dumps   # familiar for users coming from orjson / msgspec
decode = loads


def token_count(data, tokenizer: str = "o200k_base") -> dict:
    """
    Compare token costs for a Python object across all JTON output modes.

    Requires the ``tiktoken`` package (pip install tiktoken).

    Args:
        data:      Any Python object serialisable by jton.dumps().
        tokenizer: tiktoken encoding name — default ``"o200k_base"``
                   (GPT-4o / GPT-5 tokenizer).

    Returns:
        dict with keys:
          json_pretty, json_compact, zen_grid, zen_grid_rowcount,
          zen_grid_tab, zen_grid_multiline, zen_grid_plus
          Each value is a dict: {"tokens": int, "chars": int, "savings_vs_compact": str}

    Example::

        >>> import jton
        >>> jton.token_count([{"id": i, "name": f"User{i}"} for i in range(50)])
        {
          'json_compact':       {'tokens': 853,  'chars': 1402, 'savings_vs_compact': '0.0%'},
          'zen_grid':           {'tokens': 612,  'chars': 782,  'savings_vs_compact': '-28.3%'},
          'zen_grid_rowcount':  {'tokens': 614,  'chars': 786,  'savings_vs_compact': '-28.0%'},
          'zen_grid_tab':       {'tokens': 498,  'chars': 681,  'savings_vs_compact': '-41.6%'},
          'zen_grid_multiline': {'tokens': 610,  'chars': 778,  'savings_vs_compact': '-28.5%'},
          'zen_grid_plus':      {'tokens': 488,  'chars': 660,  'savings_vs_compact': '-42.8%'},
        }
    """
    try:
        import tiktoken
    except ImportError:
        raise ImportError(
            "token_count() requires tiktoken. Install with: pip install tiktoken"
        )
    import json

    enc = tiktoken.get_encoding(tokenizer)

    def _count(text: str) -> dict:
        tokens = len(enc.encode(text))
        return {"tokens": tokens, "chars": len(text)}

    json_compact = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    baseline = len(enc.encode(json_compact))

    results = {}

    def _entry(text: str, label: str) -> None:
        info = _count(text)
        savings = (info["tokens"] - baseline) / baseline * 100 if baseline else 0.0
        info["savings_vs_compact"] = f"{savings:+.1f}%"
        results[label] = info

    _entry(
        json.dumps(data, indent=2, ensure_ascii=False),
        "json_pretty",
    )
    _entry(json_compact, "json_compact")
    _entry(dumps(data, zen_grid=True, row_count=False), "zen_grid")
    _entry(dumps(data, zen_grid=True, row_count=True), "zen_grid_rowcount")
    _entry(dumps(data, zen_grid=True, delimiter="tab"), "zen_grid_tab")
    _entry(dumps(data, zen_grid=True, multiline_zen=True), "zen_grid_multiline")
    _entry(
        dumps(data, zen_grid=True, bare_strings=True, implicit_null=True),
        "zen_grid_plus",
    )

    return results


__all__ = [
    "loads",
    "dumps",
    "encode",
    "decode",
    "format_hint",
    "token_count",
    "__version__",
    "__simd__",
]


