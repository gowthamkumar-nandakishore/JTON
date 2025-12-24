# API Contract: myson.loads()

**Feature**: 002-simd-schema-parser  
**Date**: 2025-12-24  
**Purpose**: Python API surface for Rust SIMD parser

## Function Signature

```python
def loads(
    data: bytes | str,
    *,
    schema: type[DataclassProtocol] | type[msgspec.Struct] | None = None,
    parallel: bool = False,
) -> Any:
    """
    Parse MYSON/JSON data using Rust SIMD engine.
    
    Args:
        data: Input as bytes (zero-copy) or str (will encode to UTF-8)
        schema: Optional dataclass/Struct for schema-guided parsing
        parallel: Enable multi-threaded parsing (requires schema, Phase 2)
    
    Returns:
        Parsed Python object (dict, list, str, int, float, bool, None)
    
    Raises:
        ValueError: Invalid JSON/MYSON syntax
        TypeError: parallel=True without schema
        MemoryError: Input exceeds safety limits (>1GB or >10M Zen Grid rows)
    
    Examples:
        >>> myson.loads('{"key": "value"}')
        {'key': 'value'}
        
        >>> myson.loads(b'[: id,name; 1,Alice ]')
        [{'id': 1, 'name': 'Alice'}]
        
        >>> from dataclasses import dataclass
        >>> @dataclass
        ... class User:
        ...     id: int
        ...     name: str
        >>> myson.loads(b'[: id,name; 1,Alice ]', schema=User)
        [User(id=1, name='Alice')]
    """
```

## Performance Contract

| Scenario | Throughput | Constraint |
|----------|------------|------------|
| Schema-free JSON (canada.json 2.2 MB) | ≥1.5 GB/s | AVX2 CPU |
| Schema-free JSON (super_long.json 294 MB) | ≥1.5 GB/s | AVX2 CPU |
| Schema-guided Zen Grid (10K rows) | >1 GB/s | AVX2 + schema |
| Parallel mode (500 MB, 16 cores) | >10 GB/s | AVX-512 + schema |
| Minimum (any payload) | ≥233.9 MB/s | Never regress |

**CI Gate**: Benchmark must pass on every PR. Build fails if throughput drops below 233.9 MB/s.

## Error Contract

All errors include approximate byte position (±32 bytes) and excerpt:

```python
>>> myson.loads('{invalid}')
ValueError: Unexpected token 'i' at ~byte 1:
  Excerpt: '{invalid}'
           ~^
```

For schema mismatches:

```python
>>> myson.loads('[: id; "string"]', schema=User)  # id expects int
TypeError: Field 'id' expects int, got str at ~byte 8:
  Excerpt: '[: id; "string"]'
                ~^
```

## Compatibility Contract

- **JSON Superset**: 100% compatible with `json.loads()` for valid JSON
- **Test Parity**: All 400+ existing tests pass without modification
- **Token Efficiency**: Identical to current (48.8% reduction vs JSON pretty, 19.6% vs compact)
- **Wire Format**: No changes - existing MYSON data parses identically

## Memory Contract

- **Zero-Copy**: Input as `bytes` avoids allocation for unescaped strings
- **Interning**: Repeated keys allocated once, reused via `Py_INCREF`
- **Pre-allocation**: Zen Grid pre-allocates exact row count (capped at 1M rows)
- **Safety**: Hard abort at 1 GB input or 10M Zen Grid rows

## Schema Contract

```python
# Supported schema types
from dataclasses import dataclass
import msgspec

@dataclass
class User:
    id: int
    name: str
    active: bool

class UserStruct(msgspec.Struct):
    id: int
    name: str
    active: bool

# Both work identically
myson.loads(data, schema=User)
myson.loads(data, schema=UserStruct)
```

**Requirements**:
- Schema must have type annotations (`int`, `str`, `bool`, `float`, `list`, `dict`)
- Field order matters for positional parsing
- For Zen Grid, header order must match schema field order
- For JSON arrays, first object establishes key→position mapping

## Backward Compatibility

```python
# Old API (current)
import myson
myson.loads(data)

# New API (after Rust migration)
import myson
myson.loads(data)  # Identical behavior, 6x faster

# Schema mode (new feature)
myson.loads(data, schema=User)  # Optional performance boost
```

**Migration**: Zero changes required. Existing code runs faster with no modifications.
