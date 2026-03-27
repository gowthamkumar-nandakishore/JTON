"""
Type stubs for JTON — Ultra-Optimized Object Notation.
"""

from typing import Any, Literal, Optional, TypeVar, Union

__version__: str
__simd__: str

T = TypeVar("T")

def loads(
    data: Union[str, bytes],
    schema: Optional[list] = None,
) -> Any:
    """
    Parse a JTON or JSON string/bytes into a Python object.

    Args:
        data:   Input string or bytes.  bytes avoids a UTF-8 copy.
        schema: Optional list of field names for schema-guided parsing
                (activates the Nitro fast-path on homogeneous object arrays).

    Returns:
        Parsed Python value: dict, list, str, int, float, bool, or None.

    Raises:
        ValueError:  Invalid JTON/JSON syntax.
        TypeError:   data is not str or bytes.
    """
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
) -> str:
    """
    Serialize a Python object to a JTON or JSON string.

    Args:
        data:           Any serializable Python object.
        zen_grid:       Enable Zen Grid table encoding (default: True).
        unquoted_keys:  Write identifier-safe keys without quotes.
        indent:         Pretty-print with this many spaces per level.
        bare_strings:   Write identifier string values without quotes in Zen Grid cells.
        implicit_null:  Write missing/null Zen Grid cells as empty (saves ~1 token/cell).
        row_count:      Prefix Zen Grid header with row count: ``[N: col1, col2; ...]``.
                        Improves LLM comprehension (+3–5 pp on Gemini models).
        multiline_zen:  Emit TOON-compatible multi-line format::

                            [N]{col1,col2}:
                              val1,val2
                              val3,val4

                        Proven +1.4 pp LLM accuracy over JSON. Best for Gemini models.
        delimiter:      Cell separator in Zen Grid headers and rows.
                        "comma" (default, readable), "tab" (5–15% fewer tokens),
                        "pipe" (alternative readable format).

    Returns:
        A str containing the JTON/JSON representation.

    Raises:
        TypeError:  An object is not serializable.
        ValueError: Nesting exceeds 256 levels.
    """
    ...

def format_hint(
    style: Literal["zen_grid", "zen_grid_rowcount", "multiline", "tab"] = "zen_grid",
) -> str:
    """
    Return a concise format description for pasting into LLM system prompts.

    Use this to prime an LLM before sending Zen Grid data in a prompt.

    Args:
        style: One of:
            "zen_grid"          — default inline format
            "zen_grid_rowcount" — inline with [N] row count
            "multiline"         — TOON-compatible multi-line (best for Gemini)
            "tab"               — tab-delimited

    Returns:
        A natural-language description + example the LLM can reference.

    Example::

        >>> import jton
        >>> print(jton.format_hint())
        Data is in JTON Zen Grid format.
        Format: [: col1, col2, col3; row1val1, row1val2, row1val3; ... ]
        ...
    """
    ...

def token_count(
    data: Any,
    tokenizer: str = "o200k_base",
) -> dict[str, dict[str, Union[int, str]]]:
    """
    Compare token costs across all JTON output modes.

    Requires ``tiktoken`` (pip install tiktoken).

    Args:
        data:      Any serialisable Python object.
        tokenizer: tiktoken encoding name (default: "o200k_base" for GPT-4o/GPT-5).

    Returns:
        Dict mapping mode names to {"tokens": int, "chars": int, "savings_vs_compact": str}.
        Modes: json_pretty, json_compact, zen_grid, zen_grid_rowcount,
               zen_grid_tab, zen_grid_multiline, zen_grid_plus.
    """
    ...

def loads_many(
    texts: list[Union[str, bytes]],
) -> list[Any]:
    """
    Decode a batch of JSON/JTON strings in parallel using a Rayon thread pool.

    Releases the Python GIL during the CPU-intensive parse phase, then
    converts results to Python objects (GIL re-acquired).  Ideal for server
    workloads receiving batches of JSON payloads simultaneously.

    Args:
        texts: List of JSON/JTON strings (or bytes) to decode.

    Returns:
        List of parsed Python values in the same order as ``texts``.

    Raises:
        ValueError: If any string contains invalid JSON/jton.

    Example::

        >>> import jton
        >>> jton.loads_many(['{"x":1}', '{"x":2}', '{"x":3}'])
        [{'x': 1}, {'x': 2}, {'x': 3}]
    """
    ...

def dumps_many(
    data: list[Any],
    *,
    zen_grid: bool = True,
    row_count: bool = True,
) -> list[str]:
    """
    Encode a list of Python objects to JTON/JSON strings.

    Uses the thread-local serialization buffer pool for each item, giving
    zero-allocation reuse across the batch.

    Args:
        data:      List of Python objects to serialise.
        zen_grid:  Enable Zen Grid table encoding (default: True).
        row_count: Prepend row count in Zen Grid header (default: True).

    Returns:
        List of JTON/JSON strings in the same order as ``data``.

    Raises:
        TypeError: An object is not serializable.

    Example::

        >>> import jton
        >>> jton.dumps_many([{"x": 1}, {"x": 2}])
        ['{"x":1}', '{"x":2}']
    """
    ...

def loads_as(
    data: Union[str, bytes],
    model_type: type[T],
    *,
    strict: bool = False,
) -> T:
    """
    Parse JTON/JSON and validate against a Pydantic model or dataclass.

    Combines ``jton.loads()`` with Pydantic ``model_validate()`` (v2) or
    ``parse_obj()`` (v1).  Falls back to ``model_type(**parsed)`` for plain
    dataclasses and other callables.

    Args:
        data:       JTON/JSON string or bytes.
        model_type: Pydantic BaseModel subclass, dataclass, or callable.
        strict:     Passed to Pydantic v2 ``model_validate(strict=...)``.

    Returns:
        Validated instance of ``model_type``.

    Raises:
        ValidationError: Pydantic validation failure.
        TypeError:        model_type cannot be constructed from parsed data.

    Example::

        >>> from pydantic import BaseModel
        >>> import jton
        >>> class User(BaseModel):
        ...     id: int
        ...     name: str
        >>> jton.loads_as('{"id":1,"name":"Alice"}', User)
        User(id=1, name='Alice')
    """
    ...

# Aliases
encode = dumps
decode = loads


