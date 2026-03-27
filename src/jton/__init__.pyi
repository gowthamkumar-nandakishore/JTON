"""
Type stubs for JTON — JSON Tabular Object Notation.
Drop-in replacement for the stdlib `json` module.
"""

from typing import Any, Callable, IO, Literal, Optional, Union

__version__: str
__simd__: str

def loads(
    data: Union[str, bytes],
    schema: Optional[list] = None,
) -> Any:
    """Parse a JTON or JSON string/bytes into a Python object."""
    ...

def load(fp: IO[Any], **kwargs: Any) -> Any:
    """Parse JTON/JSON from a file-like object. Drop-in for json.load()."""
    ...

def dumps(
    data: Any,
    *,
    zen_grid: bool = True,
    unquoted_keys: bool = False,
    indent: Optional[int] = None,
    bare_strings: bool = False,
    implicit_null: bool = False,
    row_count: bool = True,
    multiline_zen: bool = False,
    delimiter: Literal["comma", "tab", "pipe"] = "comma",
    default: Optional[Callable[[Any], Any]] = None,
) -> str:
    """
    Serialize a Python object to a JTON/JSON string. Drop-in for json.dumps().

    Args:
        data:          Any serializable Python object.
        zen_grid:      Enable Zen Grid table encoding (default: True).
        unquoted_keys: Write identifier-safe keys without quotes.
        indent:        Pretty-print with this many spaces per level.
        bare_strings:  Write identifier string values without quotes in Zen Grid cells.
        implicit_null: Write null Zen Grid cells as empty (saves ~1 token/cell).
        row_count:     Prefix Zen Grid header with ``[N: ...]`` row count (default: True).
        multiline_zen: Emit multi-line Zen Grid format.
        delimiter:     "comma" (default), "tab" (max token savings), "pipe".
        default:       Callable for non-serializable objects (like json.dumps default=).
    """
    ...

def dump(obj: Any, fp: IO[Any], **kwargs: Any) -> None:
    """Serialize a Python object to a file-like object. Drop-in for json.dump()."""
    ...

def format_hint(
    style: Literal["zen_grid", "zen_grid_rowcount", "multiline", "tab"] = "zen_grid",
) -> str:
    """Return a concise format description for pasting into LLM system prompts."""
    ...

def token_count(
    data: Any,
    tokenizer: str = "o200k_base",
) -> dict[str, dict[str, Union[int, str]]]:
    """
    Compare token costs across all JTON output modes. Requires tiktoken.

    Returns dict mapping mode names to {"tokens": int, "chars": int, "savings_vs_compact": str}.
    Modes: json_pretty, json_compact, zen_grid, zen_grid_rowcount, zen_grid_tab, zen_grid_plus.
    """
    ...

# Aliases
encode = dumps
decode = loads
