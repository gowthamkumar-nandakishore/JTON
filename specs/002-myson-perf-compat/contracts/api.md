# API Contract: myson

**Feature**: `002-myson-perf-compat`

## Module: `myson`

The top-level module acts as a drop-in replacement for `json`.

```python
# myson/__init__.py

from typing import Any, IO, Optional, Callable, Type

def loads(
    s: str | bytes | bytearray,
    *,
    cls: Optional[Type[Any]] = None,
    object_hook: Optional[Callable[[dict], Any]] = None,
    parse_float: Optional[Callable[[str], Any]] = None,
    parse_int: Optional[Callable[[str], Any]] = None,
    parse_constant: Optional[Callable[[str], Any]] = None,
    object_pairs_hook: Optional[Callable[[list[tuple[Any, Any]]], Any]] = None,
    **kw: Any
) -> Any:
    """
    Deserialize s (a ``str``, ``bytes`` or ``bytearray`` instance containing a JSON
    document) to a Python object.
    """
    ...

def load(
    fp: IO[str] | IO[bytes],
    *,
    cls: Optional[Type[Any]] = None,
    object_hook: Optional[Callable[[dict], Any]] = None,
    parse_float: Optional[Callable[[str], Any]] = None,
    parse_int: Optional[Callable[[str], Any]] = None,
    parse_constant: Optional[Callable[[str], Any]] = None,
    object_pairs_hook: Optional[Callable[[list[tuple[Any, Any]]], Any]] = None,
    **kw: Any
) -> Any:
    """
    Deserialize fp (a ``.read()``-supporting file-like object containing a
    JSON document) to a Python object.
    """
    ...

def dumps(
    obj: Any,
    *,
    skipkeys: bool = False,
    ensure_ascii: bool = True,
    check_circular: bool = True,
    allow_nan: bool = True,
    cls: Optional[Type[Any]] = None,
    indent: Optional[int | str] = None,
    separators: Optional[tuple[str, str]] = None,
    default: Optional[Callable[[Any], Any]] = None,
    sort_keys: bool = False,
    **kw: Any
) -> str:
    """
    Serialize obj to a JSON formatted ``str``.
    """
    ...

def dump(
    obj: Any,
    fp: IO[str],
    *,
    skipkeys: bool = False,
    ensure_ascii: bool = True,
    check_circular: bool = True,
    allow_nan: bool = True,
    cls: Optional[Type[Any]] = None,
    indent: Optional[int | str] = None,
    separators: Optional[tuple[str, str]] = None,
    default: Optional[Callable[[Any], Any]] = None,
    sort_keys: bool = False,
    **kw: Any
) -> None:
    """
    Serialize obj as a JSON formatted stream to fp.
    """
    ...

class MysonModel:
    """
    Base class for schema-based validation.
    """
    ...
```

## Module: `myson.myson_core` (Internal)

This is the Cython extension module. It is not intended for direct public use, but `myson` exposes its functionality.

```python
# myson/myson_core.pyx

def loads(s, ...): ...
def dumps(obj, ...): ...
```
