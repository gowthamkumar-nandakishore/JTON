# Data Model: Performance Optimization Structures

**Feature**: MYSON Parser Performance Optimization to 700+ MB/s  
**Date**: 2025-12-24
**Stretch Goal**: 1 GB/s with future SIMD optimizations (Phase 4)

## Core Entities

### 1. Parser Context

**Purpose**: Minimal state for pointer-based parsing

**Attributes**:
- `buf: const char*` - Pointer to start of input buffer (immutable)
- `end_ptr: const unsigned char*` - Pointer to end of buffer (buf + length, immutable)
- `length: Py_ssize_t` - Total buffer length in bytes
- `pos: Py_ssize_t` - Current position (updated minimally, only for errors)
- `recursion_depth: int` - Current nesting level (0-1024)
- `max_recursion_depth: int` - Maximum allowed nesting (1024)

**Lifecycle**:
- Created: Once at start of parsing via `__cinit__`
- Updated: `pos` updated only when needed for error reporting
- Destroyed: Automatic when Parser object deallocated

**Validation Rules**:
- `recursion_depth < max_recursion_depth` - enforced before each recursive call
- `0 <= pos <= length` - maintained by pointer arithmetic
- `buf` never NULL during parsing

---

### 2. Character Lookup Table

**Purpose**: O(1) character classification for hot loop

**Structure**:
```cython
cdef unsigned char[256] CHAR_TABLE
```

**Bit Fields**:
- `WHITESPACE_BIT = 0x01` - Space, tab, newline, carriage return
- `DIGIT_BIT = 0x02` - ASCII digits 0-9
- `ALPHA_BIT = 0x04` - ASCII letters a-z, A-Z
- `NUMBER_CHAR_BIT = 0x08` - Valid number characters (+, -, ., e, E)
- `STRUCTURAL_BIT = 0x10` - JSON structural characters ({, }, [, ], :, ,)

**Initialization**: Module load time, before any parsing
```cython
def init_char_table():
    CHAR_TABLE[ord(' ')] = WHITESPACE_BIT
    CHAR_TABLE[ord('\t')] = WHITESPACE_BIT
    # ... etc for all 256 values
```

**Usage**:
```cython
if CHAR_TABLE[c] & WHITESPACE_BIT:  # O(1) whitespace check
    # skip whitespace
```

---

### 3. Pointer State

**Purpose**: Efficient buffer traversal without bounds checks

**Fields** (local variables, not struct):
- `p: const unsigned char*` - Current read position
- `start: const unsigned char*` - Start of current token
- `end: const unsigned char*` - End of buffer (immutable)

**Lifecycle**:
- Created: At start of each parsing function
- Updated: Advanced with `p++` or `p += n`
- Validated: Always `p <= end` before dereference
- Synchronized: `self.pos = p - self.buf` when needed

**Constraints**:
- Never dereference if `p >= end`
- Always check `p < end` before `p[0]`
- Use `IF_SAFE_INCREMENT(p, end)` macro for all pointer advancement
- Macro expands to: `if (p < end) p++; else raise_buffer_error()`

**Safety Invariant**: `buf <= p <= end` maintained throughout parsing

---

### 4. Bounds Checking Functions

**Purpose**: Prevent buffer overruns in pointer arithmetic via inline functions

**Definition**:
```cython
# File: src/myson_core.pyx (module level)

cdef inline void check_bounds(const unsigned char* p, const unsigned char* end) except *:
    if p >= end:
        raise ValueError("Unexpected end of input")

cdef inline const unsigned char* safe_increment(
    const unsigned char* p,
    const unsigned char* end
) except NULL:
    """Safely increment pointer with bounds checking."""
    if p >= end:
        raise ValueError("Unexpected end of input")
    return p + 1
```

**Usage Pattern**:
```cython
# Before every pointer dereference
check_bounds(p, end)
c = p[0]

# Before pointer increment
p = safe_increment(p, end)

# Combined: check then read then increment
check_bounds(p, end)
if p[0] == b'[':
    p = safe_increment(p, end)
```

**Performance Impact**: Inline expansion means zero function call overhead. Bounds check is single comparison, typically ~0.1-0.3ns on modern CPUs.

---

### 5. Memory Recovery Pattern

**Purpose**: Ensure cleanup on allocation failures

**Pattern** (try...finally in Cython):
```cython
cdef object parse_array(self):
    """Parse array with safe memory management."""
    cdef:
        const unsigned char* p = self.buf + self.pos
        Py_ssize_t count
        object result = None
        object* temp_items = NULL
    
    try:
        # Pre-scan for array size
        count = self.prescan_array_size()
        
        # Allocate Python list
        result = PyList_New(count)  # May raise MemoryError
        if result is NULL:
            raise MemoryError("Failed to allocate array")
        
        # Parse elements
        for i in range(count):
            item = self.parse_value()  # May raise exceptions
            PyList_SET_ITEM(result, i, item)
            
        return result
        
    except (MemoryError, ValueError) as e:
        # Cleanup on failure
        if temp_items != NULL:
            free(temp_items)
        if result is not None:
            Py_DECREF(result)  # Release partial list
        raise
    
    finally:
        # Always cleanup temporary buffers
        if temp_items != NULL:
            free(temp_items)
            temp_items = NULL
```

**Guarantees**:
- All `malloc()`/`PyList_New()` calls paired with `free()`/`Py_DECREF()`
- No memory leaks on `MemoryError`, `ValueError`, or `RecursionError`
- Parser state left consistent for next parse attempt

---

### 6. Pre-scan Result
- Pointer arithmetic replaces index arithmetic

---

### 4. Pre-scan Result

**Purpose**: Determine array size before allocation

**Structure**: Simple integer count (not a separate entity)

**Algorithm**:
```cython
cdef Py_ssize_t prescan_array_size(const unsigned char* p, const unsigned char* end):
    count = 0
    depth = 0
    while p < end:
        if p[0] == '[' or p[0] == '{': depth++
        elif p[0] == ']' or p[0] == '}': depth--
        elif p[0] == ',' and depth == 0: count++
        p++
    return count + 1 if count > 0 else 0
```

**Usage**:
```cython
size = prescan_array_size(p, end)
list = PyList_New(size)
for i in range(size):
    value = parse_value()
    PyList_SET_ITEM(list, i, value)  # Zero overhead
```

---

## Data Flow

### Phase 1: Pre-allocation Flow

```
Input bytes → Parser.parse()
              ↓
         parse_value()
              ↓
    [detected] → prescan_array_size() → count
                        ↓
                  PyList_New(count) → pre-allocated list
                        ↓
                  for i in range(count):
                      parse_value() → value
                      PyList_SET_ITEM(list, i, value)
```

### Phase 2: Pointer Arithmetic Flow

```
Input bytes → Parser.parse()
              ↓
         const unsigned char* p = self.buf
         const unsigned char* end = self.buf + self.length
              ↓
         while p < end:
             c = p[0]      # Direct dereference, no bounds check
             if c == '{':
                 p++
                 parse_object(p, end)
             p++
              ↓
         self.pos = p - self.buf  # Only when needed
```

### Phase 3: Lookup Table Flow

```
Character c → CHAR_TABLE[c] → bitfield
                               ↓
                        if bitfield & WHITESPACE_BIT:
                            skip_whitespace_fast(p, end)
                               ↓
                        Batch processing (8 bytes at a time):
                        while p + 8 <= end:
                            check 8 bytes
                            if all whitespace: p += 8
                            else: break
```

---

## Memory Layout

### Parser Object (Cython class)
```
Parser (Python object)
├── buf: const char* ──────► [Input buffer in memory]
├── length: Py_ssize_t       (8 bytes)
├── pos: Py_ssize_t          (8 bytes)
├── recursion_depth: int     (4 bytes)
└── max_recursion_depth: int (4 bytes)

Total: ~32 bytes + Python object overhead
```

### Character Lookup Table (Global Static Const)
```
CHAR_TABLE[256]  // Module-level cdef array (static const in generated C)
  ├── [0...31]: Control characters (mostly 0x00)
  ├── [32]: Space (WHITESPACE_BIT = 0x01)
  ├── [48...57]: Digits (DIGIT_BIT = 0x02)
  ├── [65...90]: Uppercase (ALPHA_BIT = 0x04)
  ├── [97...122]: Lowercase (ALPHA_BIT = 0x04)
  └── [123...255]: Other (various bits)

Total: 256 bytes (fits in L1 cache)
Declaration: static const in generated C code (Cython module-level cdef)
Cache behavior: Read-only access ensures L1 cache residency
```

### Pre-allocated List (Phase 1)
```
Before (with append):
list = []
for value in values:
    list.append(value)  # Reallocates at 0, 4, 8, 16, 25, 35, 46, ...

After (with pre-allocation):
list = PyList_New(count)  # Allocate exact size once
for i, value in enumerate(values):
    PyList_SET_ITEM(list, i, value)  # Direct memory write, no realloc
```

**Memory Savings**: Eliminates over-allocation and multiple realloc cycles.

---

## State Transitions

### Recursion Depth Tracking

```
Initial: depth = 0

parse_value() → detect '{'
                depth++  (now 1)
                ↓
            parse_object()
                ↓
            detect nested '['
                depth++  (now 2)
                ↓
            parse_array()
                ↓
            detect nested '{'
                depth++  (now 3)
                ↓
            ... (up to depth 1024)
                ↓
            depth--  (when '}' found)
                ↓
            depth--  (when ']' found)
                ↓
            depth--  (when '}' found)

Final: depth = 0
```

**Guard**: `if depth >= 1024: raise RecursionError`

---

## Validation Rules

### Pre-allocation
- Array size calculation must account for nesting (ignore commas inside nested structures)
- Empty arrays must return count=0, allocate empty list
- Single-element arrays must return count=1

### Pointer Arithmetic
- Always check `p < end` before dereferencing `p[0]`
- Never advance `p` beyond `end`
- Position synchronization: `self.pos = p - self.buf` before error reporting

### Lookup Tables
- Initialize all 256 entries at module load
- Use bitwise AND for checks: `CHAR_TABLE[c] & BIT_MASK`
- Never modify table after initialization (read-only in hot loop)

---

## Performance Characteristics

| Entity | Memory Overhead | Access Time | Optimization |
|--------|----------------|-------------|--------------|
| Parser Context | ~32 bytes | O(1) field access | Minimal state |
| Character Table | 256 bytes | O(1) lookup | Fits in L1 cache |
| Pointer State | ~24 bytes stack | O(1) arithmetic | No heap allocation |
| Pre-scan Result | 8 bytes | O(n) one-time scan | Amortized over n inserts |

**Total overhead**: <512 bytes per parse operation (negligible)

---

## Entity Relationships

```
Parser
  │
  ├──[uses]──► CHAR_TABLE (global, read-only)
  │
  ├──[maintains]──► Pointer State (local, per function)
  │
  ├──[calls]──► prescan_array_size() → count
  │                                      ↓
  └──[creates]──► PyList_New(count) → Pre-allocated List
```

No complex entity relationships - all optimizations are local to parsing logic.
