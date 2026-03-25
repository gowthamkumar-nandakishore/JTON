"""
ZSON (Zero-overhead Serialized Object Notation) — high-performance JSON superset
with SIMD-accelerated parsing and Zen Grid token-efficient serialization.

Key functions:
  loads(data)              — parse ZSON/JSON → Python object
  dumps(data, **opts)      — serialize Python object → ZSON/JSON string

Zen Grid format automatically converts homogeneous arrays of dicts to a
compact table syntax that reduces LLM token counts by 40-60%:

    [: id, name, score; 1, "Alice", 95; 2, "Bob", 87 ]

instead of:

    [{"id":1,"name":"Alice","score":95},{"id":2,"name":"Bob","score":87}]
"""

from .zson_core import __version__, __simd__, loads, dumps

# Convenient aliases
encode = dumps   # familiar for users coming from orjson / msgspec
decode = loads

__all__ = [
    "loads",
    "dumps",
    "encode",
    "decode",
    "__version__",
    "__simd__",
]

