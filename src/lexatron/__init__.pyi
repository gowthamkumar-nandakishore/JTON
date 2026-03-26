"""
Type stubs for LEXATRON — Zero-overhead Serialized Object Notation.
"""

from typing import Any, Optional, Union

__version__: str
__simd__: str

def loads(
    data: Union[str, bytes],
    schema: Optional[list] = None,
) -> Any:
    """
    Parse a LEXATRON or JSON string/bytes into a Python object.

    Args:
        data:   Input string or bytes.  bytes avoids a UTF-8 copy.
        schema: Optional list of field names for schema-guided parsing
                (activates the Nitro fast-path on homogeneous object arrays).

    Returns:
        Parsed Python value: dict, list, str, int, float, bool, or None.

    Raises:
        ValueError:  Invalid LEXATRON/JSON syntax.
        TypeError:   data is not str or bytes.
    """
    ...

def dumps(
    data: Any,
    *,
    zen_grid: bool = True,
    unquoted_keys: bool = False,
    indent: Optional[int] = None,
) -> str:
    """
    Serialize a Python object to a LEXATRON or JSON string.

    Args:
        data:           Any serializable Python object (dict, list, str, int,
                        float, bool, None, Pydantic BaseModel, dataclass).
        zen_grid:       If True (default), homogeneous arrays of dicts are
                        encoded as Zen Grid tables — 40-60% fewer LLM tokens.
        unquoted_keys:  If True, identifier-safe dict keys are written without
                        surrounding quotes (e.g. {name:"Alice"}).
        indent:         Pretty-print with this many spaces per level.
                        None (default) → compact output.

    Returns:
        A str containing the LEXATRON/JSON representation.

    Raises:
        TypeError:  An object is not serializable.
        ValueError: Nesting exceeds 256 levels.

    Examples:
        >>> lexatron.dumps({"name": "Alice", "score": 95})
        '{"name":"Alice","score":95}'

        >>> lexatron.dumps([{"id":1,"v":10},{"id":2,"v":20}])
        '[: id, v; 1, 10; 2, 20 ]'

        >>> lexatron.dumps({"key": "val"}, unquoted_keys=True)
        '{key:"val"}'
    """
    ...

# Aliases
encode = dumps
decode = loads
