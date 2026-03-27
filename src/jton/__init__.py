"""
JTON (JSON Tabular Object Notation) — high-performance JSON superset
with SIMD-accelerated parsing and Zen Grid token-efficient serialization.

Key functions:
  loads(data)              — parse JTON/JSON → Python object
  dumps(data, **opts)      — serialize Python object → JTON/JSON string
  format_hint(style)       — LLM system-prompt primer for Zen Grid format
  token_count(data)        — compare token costs across all formats

Zen Grid format automatically converts homogeneous arrays of dicts to a
compact table syntax that reduces LLM token counts by 22–55%:

    [: id, name, score; 1, Alice, 95; 2, Bob, 87 ]   (default)
    [3: id, name, score; 1, Alice, 95; 2, Bob, 87 ]  (row_count=True)
    [2]{id,name}:                                      (multiline_zen=True)
      1, Alice
      2, Bob

dumps() options:
  zen_grid=True           — Enable Zen Grid table output (default: True)
  unquoted_keys=False     — Write identifier keys without quotes
  bare_strings=False      — Write identifier string VALUES without quotes
  implicit_null=False     — Write missing Zen Grid cells as empty
  indent=None             — Pretty-print with N spaces per indent level
  row_count=True          — Add [N] row count to Zen Grid header (default: True)
  multiline_zen=False     — TOON-compatible multi-line output (best LLM accuracy)
  delimiter="comma"       — "comma" (default), "tab" (max tokens), or "pipe"
"""

from .jton_core import __version__, __simd__, loads, dumps, loads_many, dumps_many, format_hint

# Convenient aliases
encode = dumps   # familiar for users coming from orjson / msgspec
decode = loads


def loads_as(data, model_type, *, strict: bool = False):
    """
    Parse a JTON/JSON string and validate against a Pydantic model or dataclass.

    This combines ``jton.loads()`` with Pydantic v2 ``model_validate()`` (or
    Pydantic v1 ``parse_obj()``), giving you a fully validated model instance
    in one call.

    Args:
        data:       JTON/JSON string or bytes to parse.
        model_type: A Pydantic BaseModel subclass, dataclass, or any callable
                    that accepts a single dict/list argument.
        strict:     Passed to Pydantic v2 ``model_validate(strict=...)``.
                    Ignored for non-Pydantic types.

    Returns:
        An instance of ``model_type`` populated with the parsed data.

    Raises:
        ValidationError: If Pydantic validation fails.
        TypeError:        If ``model_type`` cannot be constructed from parsed data.

    Example::

        >>> from pydantic import BaseModel
        >>> import jton
        >>> class User(BaseModel):
        ...     id: int
        ...     name: str
        >>> jton.loads_as('[{"id":1,"name":"Alice"},{"id":2,"name":"Bob"}]', list)
        [{'id': 1, 'name': 'Alice'}, {'id': 2, 'name': 'Bob'}]
        >>> jton.loads_as('{"id":1,"name":"Alice"}', User)
        User(id=1, name='Alice')
    """
    parsed = loads(data)
    # Pydantic v2
    if hasattr(model_type, "model_validate"):
        return model_type.model_validate(parsed, strict=strict)
    # Pydantic v1
    if hasattr(model_type, "parse_obj"):
        return model_type.parse_obj(parsed)
    # Dataclass or plain callable
    if isinstance(parsed, dict):
        return model_type(**parsed)
    return model_type(parsed)


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
    _entry(dumps(data, zen_grid=True, row_count=True), "zen_grid")
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
    "loads_many",
    "dumps_many",
    "loads_as",
    "encode",
    "decode",
    "format_hint",
    "token_count",
    "__version__",
    "__simd__",
]


