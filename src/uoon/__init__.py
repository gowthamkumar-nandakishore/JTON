"""
UOON (Ultra-Optimized Object Notation) — high-performance JSON superset
with SIMD-accelerated parsing and Zen Grid token-efficient serialization.

Key functions:
  loads(data)              — parse UOON/JSON → Python object
  dumps(data, **opts)      — serialize Python object → UOON/JSON string

Zen Grid format automatically converts homogeneous arrays of dicts to a
compact table syntax that reduces LLM token counts by 40-65%:

    [: id, name, score; 1, Alice, 95; 2, Bob, 87 ]   (bare_strings=True)

instead of:

    [{"id":1,"name":"Alice","score":95},{"id":2,"name":"Bob","score":87}]

dumps() options:
  zen_grid=True         — Enable Zen Grid table output (default: True)
  unquoted_keys=False   — Write identifier keys without quotes
  bare_strings=False    — Write identifier string VALUES without quotes in Zen Grid
  implicit_null=False   — Write missing Zen Grid cells as empty (saves null tokens)
  indent=None           — Pretty-print with N spaces per indent level
"""

from .uoon_core import __version__, __simd__, loads, dumps

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

