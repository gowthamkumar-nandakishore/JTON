from typing import Any, IO, Optional, Callable, Type

# Import core implementation (will be available after build)
try:
    from .myson_core import loads as _core_loads, dumps as _core_dumps, MysonModel
except ImportError:
    # Fallback or placeholder for development
    def _core_loads(*args, **kwargs): raise NotImplementedError("Extension not built")
    def _core_dumps(*args, **kwargs): raise NotImplementedError("Extension not built")
    class MysonModel: pass

# Import Zen Grid serializer (Phase 3)
from .serializer import dumps as zen_dumps, dump as zen_dump

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
    return _core_loads(
        s, 
        cls=cls, 
        object_hook=object_hook, 
        parse_float=parse_float, 
        parse_int=parse_int, 
        parse_constant=parse_constant, 
        object_pairs_hook=object_pairs_hook, 
        **kw
    )

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
    zen: bool = False,
    **kw: Any
) -> str:
    return _core_dumps(
        obj,
        skipkeys=skipkeys,
        ensure_ascii=ensure_ascii,
        check_circular=check_circular,
        allow_nan=allow_nan,
        cls=cls,
        indent=indent,
        separators=separators,
        default=default,
        sort_keys=sort_keys,
        zen=zen,
        **kw
    )

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
    return loads(
        fp.read(),
        cls=cls,
        object_hook=object_hook,
        parse_float=parse_float,
        parse_int=parse_int,
        parse_constant=parse_constant,
        object_pairs_hook=object_pairs_hook,
        **kw
    )

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
    zen: bool = False,
    **kw: Any
) -> None:
    fp.write(dumps(
        obj,
        skipkeys=skipkeys,
        ensure_ascii=ensure_ascii,
        check_circular=check_circular,
        allow_nan=allow_nan,
        cls=cls,
        indent=indent,
        separators=separators,
        default=default,
        sort_keys=sort_keys,
        zen=zen,
        **kw
    ))
