# API Contracts: Performance-Optimized Parser

**Feature**: MYSON Parser Performance Optimization to 700+ MB/s  
**Date**: 2025-12-24
**Stretch Goal**: 1 GB/s with future SIMD optimizations (Phase 4)

## Overview

The performance optimization maintains 100% API compatibility with the existing MYSON parser. No external API changes - all optimizations are internal implementation details.

---

## Public API (Unchanged)

### `myson.loads(s, *, cls=None, object_hook=None, ...)`

**Purpose**: Parse MYSON/JSON data into Python objects

**Signature**:
```python
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
) -> Any
```

**Parameters**:
- `s`: Input data (string or bytes)
- `cls`: Custom decoder class (optional)
- `object_hook`: Custom object transformation (optional)
- `parse_float`: Custom float parser (optional)
- `parse_int`: Custom integer parser (optional)
- `parse_constant`: Custom constant parser (optional)
- `object_pairs_hook`: Custom pairs transformation (optional)

**Returns**: Parsed Python object (dict, list, str, int, float, bool, None)

**Raises**:
- `ValueError`: Invalid JSON/MYSON syntax
- `RecursionError`: Nesting depth exceeds 1024 levels
- `TypeError`: Invalid input type

**Performance Contract**:
- **Phase 1**: 2-3x faster for array-heavy documents
- **Phase 2**: 1.5-2x faster for all documents (cumulative 3-6x)
- **Phase 3**: 1.3-1.5x faster for whitespace-heavy documents (cumulative 4-9x)

**Compatibility Contract**:
- Output identical to pre-optimization version
- All 28 existing tests must pass
- Error messages unchanged (same line/column reporting)

---

## Internal API Changes (Implementation Only)

### Phase 1: Pre-allocation

#### `Parser.parse_array()`

**Before**:
```cython
cdef object parse_array(self):
    arr = []
    while not at_end:
        value = self.parse_value()
        arr.append(value)  # Python protocol, refcount, resize checks
    return arr
```

**After**:
```cython
cdef object parse_array(self):
    # Pre-scan to get size
    size = self.prescan_array_size()
    
    # Allocate exact size
    cdef list arr = PyList_New(size)
    
    # Fill with zero overhead
    cdef Py_ssize_t i = 0
    while i < size:
        value = self.parse_value()
        Py_INCREF(value)
        PyList_SET_ITEM(arr, i, value)  # Direct memory write
        i += 1
    return arr
```

**Contract**:
- Must call `prescan_array_size()` before allocation
- Must use `PyList_New(size)` for allocation
- Must use `PyList_SET_ITEM()` for insertion (never `append()`)
- Must `Py_INCREF()` before `SET_ITEM` (C-API requirement)

---

### Phase 2: Pointer Arithmetic

#### `Parser.skip_whitespace()`

**Before**:
```cython
cdef void skip_whitespace(self):
    while self.pos < self.length:
        c = self.buf[self.pos]  # Bounds check on every access
        if c in (' ', '\t', '\n', '\r'):
            self.pos += 1
        else:
            break
```

**After**:
```cython
cdef void skip_whitespace(self):
    cdef const unsigned char* p = self.buf + self.pos
    cdef const unsigned char* end = self.buf + self.length
    
    # No bounds checks in loop
    while p < end:
        c = p[0]  # Direct pointer dereference
        if c == b' ' or c == b'\t' or c == b'\n' or c == b'\r':
            p += 1
        else:
            break
    
    # Update position only once
    self.pos = p - self.buf
```

**Contract**:
- All functions must use `const unsigned char*` for buffer access
- Must check `p < end` before every `p[0]` dereference
- Must update `self.pos` only when needed (errors, return)
- Must pass pointers between functions, not positions

---

### Phase 3: Lookup Tables

#### Character Classification Table

**Structure**:
```cython
# Global lookup table (initialized at module load)
cdef unsigned char[256] CHAR_TABLE

# Bit constants
cdef enum:
    WHITESPACE_BIT = 0x01
    DIGIT_BIT = 0x02
    ALPHA_BIT = 0x04
    NUMBER_CHAR_BIT = 0x08
    STRUCTURAL_BIT = 0x10
```

**Initialization**:
```cython
cdef void init_char_table():
    # Initialize all to 0
    for i in range(256):
        CHAR_TABLE[i] = 0
    
    # Set whitespace bits
    CHAR_TABLE[ord(' ')] = WHITESPACE_BIT
    CHAR_TABLE[ord('\t')] = WHITESPACE_BIT
    CHAR_TABLE[ord('\n')] = WHITESPACE_BIT
    CHAR_TABLE[ord('\r')] = WHITESPACE_BIT
    
    # Set digit bits
    for i in range(ord('0'), ord('9') + 1):
        CHAR_TABLE[i] = DIGIT_BIT | NUMBER_CHAR_BIT
    
    # ... etc for all categories
```

**Usage**:
```cython
# Replace conditional checks with lookup
if CHAR_TABLE[c] & WHITESPACE_BIT:
    # is whitespace
```

**Contract**:
- Must initialize `CHAR_TABLE` before any parsing
- Must use bitwise AND (`&`) for checks, never equality
- Never modify table after initialization
- Must handle all 256 ASCII values

---

#### Batch Whitespace Skipping

**Function**:
```cython
cdef const unsigned char* skip_whitespace_fast(
    const unsigned char* p, 
    const unsigned char* end
) nogil:
    # Process 8 bytes at a time when possible
    while p + 8 <= end:
        # Check if all 8 bytes are whitespace
        if (CHAR_TABLE[p[0]] & CHAR_TABLE[p[1]] & CHAR_TABLE[p[2]] & 
            CHAR_TABLE[p[3]] & CHAR_TABLE[p[4]] & CHAR_TABLE[p[5]] & 
            CHAR_TABLE[p[6]] & CHAR_TABLE[p[7]]) & WHITESPACE_BIT:
            p += 8
        else:
            break
    
    # Process remaining bytes individually
    while p < end and CHAR_TABLE[p[0]] & WHITESPACE_BIT:
        p += 1
    
    return p
```

**Contract**:
- Must check `p + 8 <= end` before batch processing
- Must fall back to byte-by-byte for remaining bytes
- Must be marked `nogil` for future parallelization
- Returns new pointer position

---

## Performance Contracts by Document Type

### Array-Heavy Documents
```json
[1, 2, 3, ..., 10000]
```
- **Phase 1 impact**: High (2-3x speedup)
- **Phase 2 impact**: Medium (1.5x additional)
- **Phase 3 impact**: Low (1.1x additional)

### Object-Heavy Documents
```json
{"key1": "value1", "key2": "value2", ...}
```
- **Phase 1 impact**: Low (no array pre-allocation)
- **Phase 2 impact**: High (2x speedup from pointer arithmetic)
- **Phase 3 impact**: Medium (1.3x from lookup tables)

### Whitespace-Heavy Documents
```json
{
  "key": [
    1,
    2,
    3
  ]
}
```
- **Phase 1 impact**: Medium (some array benefit)
- **Phase 2 impact**: Medium (pointer benefit)
- **Phase 3 impact**: High (1.5x from batch whitespace skipping)

### Mixed Documents (Realistic)
```json
{
  "users": [
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"}
  ]
}
```
- **Phase 1 impact**: Medium (array pre-allocation)
- **Phase 2 impact**: High (universal benefit)
- **Phase 3 impact**: Medium (lookup tables)
- **Overall**: 4-7x cumulative speedup expected

---

## Compatibility Guarantees

### 1. Output Compatibility
```python
# Before and after must be identical
import json
import myson

data = '{"key": [1, 2, 3]}'
assert myson.loads(data) == json.loads(data)
```

### 2. Error Compatibility
```python
# Same errors with same messages
try:
    myson.loads('[1, 2,')  # Unterminated array
except ValueError as e:
    assert "Unexpected EOF" in str(e)
    # Line/column information preserved
```

### 3. Feature Compatibility
```python
# All existing features work identically
myson.loads('[: a, b; 1, 2]')  # Zen Grid tables
myson.loads('{"x": Infinity}')  # Special values
myson.loads('// comment\n[1]')  # Comments
```

---

## Non-Breaking Changes

### What Changes:
- Internal parsing loop implementation
- Memory allocation strategy
- Character classification implementation
- Whitespace skipping algorithm

### What Doesn't Change:
- Public API signatures
- Return value types and content
- Error types and messages
- Supported syntax and features
- Line/column error reporting

---

## Versioning

**Version**: 1.0.0 → 1.1.0 (Minor bump)
- **Major**: 1 (unchanged - no breaking changes)
- **Minor**: 0 → 1 (performance improvements)
- **Patch**: 0 (no bug fixes)

**Changelog**:
```
## [1.1.0] - 2025-12-24
### Added
- Phase 1: Pre-allocation for arrays (2-3x speedup)
- Phase 2: Pointer arithmetic (1.5-2x additional speedup)
- Phase 3: Lookup tables and batch processing (1.3-1.5x additional speedup)

### Changed
- Internal parser implementation (no API changes)

### Deprecated
- None

### Removed
- None

### Fixed
- None

### Security
- None
```
