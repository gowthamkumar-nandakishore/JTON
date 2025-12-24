# Research: Performance and Compatibility Update

**Feature**: `002-myson-perf-compat`
**Status**: Complete

## Findings

### 1. Standard JSON Module Compatibility
**Decision**: We must support the following signatures exactly:
- `loads(s, *, cls=None, object_hook=None, parse_float=None, parse_int=None, parse_constant=None, object_pairs_hook=None, **kw)`
- `load(fp, *, cls=None, object_hook=None, parse_float=None, parse_int=None, parse_constant=None, object_pairs_hook=None, **kw)`
- `dumps(obj, *, skipkeys=False, ensure_ascii=True, check_circular=True, allow_nan=True, cls=None, indent=None, separators=None, default=None, sort_keys=False, **kw)`
- `dump(obj, fp, *, skipkeys=False, ensure_ascii=True, check_circular=True, allow_nan=True, cls=None, indent=None, separators=None, default=None, sort_keys=False, **kw)`

**Rationale**: These are the standard signatures in Python 3.10+. `**kw` is often used for subclass arguments but we should accept and ignore (or warn) if we don't support them, to be a drop-in replacement.

### 2. MysonModel Design & Zero-Copy
**Decision**: `MysonModel` will be a Cython `cdef class`.
- It will use Python type hints for schema definition.
- **Extended Types**: It will support `datetime`, `date`, and `uuid` parsing from ISO 8601 strings.
- **Extra Fields**: It will silently ignore any fields in the input JSON that are not defined in the model schema.
- Zero-copy will be supported when parsing from `bytes` or `bytearray`. String fields will be created as new Python strings (decoding is unavoidable for `str` unless we return a custom string-like object, which breaks compatibility). However, `bytes` fields can be memory views or slices of the original buffer.
- *Correction*: `msgspec` achieves "zero-copy" for strings by decoding directly from the buffer into the string object without an intermediate bytes object, or by interning. True zero-copy is mostly for `bytes`.
- We will implement `MysonModel` to hold a reference to the source buffer if needed for delayed decoding (lazy parsing), but for now, eager parsing with efficient decoding is the goal.

### 3. Cython/C Implementation Strategy
**Decision**: Implement the tokenizer and parser as a single pass in Cython (`myson_core.pyx`).
- **Encoding**: Strictly enforce UTF-8. Reject UTF-16/32.
- **Recursion**: Enforce a fixed recursion limit (e.g., 1024) and raise `RecursionError` to prevent stack overflows.
- **Integers**: Support arbitrary precision integers by converting to Python `int` on overflow of 64-bit types.
- Use `libc.stdlib.malloc`/`free` for internal buffers if needed.
- Use `cdef` classes for the Parser and Serializer.
- Avoid Python function calls in the hot loop.
- Use `const unsigned char*` pointers for traversing the input buffer.

### 4. Benchmarking Methodology
**Decision**:
- **Throughput**: Parse `twitter.json`, `canada.json`, and `citm_catalog.json` (standard JSON benchmark suite). Measure MB/s.
- **Token Reduction**: Measure the size of the parsed Python object structure vs the raw JSON text size (though this is less about performance and more about memory).
- **Comparison**: Compare against `json` (stdlib), `orjson`, and `msgspec`.

## Technology Choices

### Build System
**Decision**: `setuptools` with `Cython`.
**Rationale**: Standard for Python C extensions.

### Parser Implementation
**Decision**: Cython (possibly wrapping C).
**Rationale**: Easier to maintain than pure C, but offers C-level performance.

### Validation
**Decision**: `MysonModel` (custom implementation).
**Rationale**: Need tight integration with the parser for zero-copy performance, which Pydantic doesn't natively offer in the same way.
