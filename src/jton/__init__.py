"""
JTON (JSON Tabular Object Notation) — high-performance JSON superset
with SIMD-accelerated parsing and Zen Grid token-efficient serialization.

Drop-in replacement for `import json`:
  load(fp)                 — parse JTON/JSON from file object
  loads(data)              — parse JTON/JSON string/bytes → Python object
  dump(obj, fp, **opts)    — serialize Python object → file object
  dumps(data, **opts)      — serialize Python object → JTON/JSON string
  format_hint(style)       — LLM system-prompt primer for Zen Grid format
  token_count(data)        — compare token costs across all formats

Zen Grid format automatically converts homogeneous arrays of dicts to a
compact table syntax that reduces LLM token counts by 15–67%:

    [3: id, name, score; 1, Alice, 95; 2, Bob, 87; 3, Carol, 92 ]

dumps() options:
  zen_grid=True           — Enable Zen Grid table output (default: True)
  unquoted_keys=False     — Write identifier keys without quotes
  bare_strings=False      — Write identifier string VALUES without quotes
  implicit_null=False     — Write missing Zen Grid cells as empty
  indent=None             — Pretty-print with N spaces per indent level
  row_count=True          — Add [N] row count to Zen Grid header (default: True)
  delimiter="comma"       — "comma" (default), "tab" (max tokens), or "pipe"
  default=None            — Callable for non-serializable objects (like json.dumps)
"""

from .jton_core import __version__, __simd__, loads
from .jton_core import dumps as _core_dumps
from .jton_core import format_hint

# Convenient aliases
encode = _core_dumps
decode = loads


def _apply_default(obj, default_fn):
    """Recursively replace non-JSON-native objects using a default callable."""
    if isinstance(obj, dict):
        return {k: _apply_default(v, default_fn) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_apply_default(v, default_fn) for v in obj]
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    return _apply_default(default_fn(obj), default_fn)


def dumps(
    data,
    *,
    zen_grid: bool = True,
    unquoted_keys: bool = False,
    indent=None,
    bare_strings: bool = False,
    implicit_null: bool = False,
    row_count: bool = True,
    multiline_zen: bool = False,
    delimiter: str = "comma",
    default=None,
) -> str:
    """
    Serialize a Python object to a JTON/JSON string.

    Drop-in replacement for ``json.dumps()``.  All standard options are
    supported, plus JTON-specific Zen Grid options.

    Args:
        data:          Any serializable Python object.
        zen_grid:      Enable Zen Grid table encoding (default: True).
        unquoted_keys: Write identifier-safe keys without quotes.
        indent:        Pretty-print with this many spaces per level.
        bare_strings:  Write identifier string values without quotes in cells.
        implicit_null: Write null Zen Grid cells as empty.
        row_count:     Prefix Zen Grid header with ``[N: ...]`` row count.
        multiline_zen: Emit multi-line Zen Grid format.
        delimiter:     Cell separator: "comma", "tab", or "pipe".
        default:       Callable for non-serializable objects, same as
                       ``json.dumps(default=...)``.  Called with the object,
                       must return a JSON-serializable value.
    """
    if default is not None:
        data = _apply_default(data, default)
    return _core_dumps(
        data,
        zen_grid=zen_grid,
        unquoted_keys=unquoted_keys,
        indent=indent,
        bare_strings=bare_strings,
        implicit_null=implicit_null,
        row_count=row_count,
        multiline_zen=multiline_zen,
        delimiter=delimiter,
    )


def load(fp, **kwargs):
    """
    Parse JTON/JSON from a file-like object.

    Drop-in replacement for ``json.load()``.

    Args:
        fp:      A readable file-like object (``str`` or ``bytes`` ``.read()``).
        **kwargs: Passed to ``loads()``.

    Returns:
        Parsed Python object.
    """
    return loads(fp.read(), **kwargs)


def dump(obj, fp, **kwargs):
    """
    Serialize a Python object to a file-like object as JTON/JSON.

    Drop-in replacement for ``json.dump()``.

    Args:
        obj:     Python object to serialize.
        fp:      A writable file-like object.
        **kwargs: Passed to ``dumps()``.
    """
    fp.write(dumps(obj, **kwargs))


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
    "load",
    "dump",
    "encode",
    "decode",
    "format_hint",
    "token_count",
    "__version__",
    "__simd__",
]


