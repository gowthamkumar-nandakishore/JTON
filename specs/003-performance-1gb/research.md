# Research: Performance Optimization Techniques

**Feature**: MYSON Parser Performance Optimization to 700+ MB/s  
**Date**: 2025-12-24
**Stretch Goal**: 1 GB/s with future SIMD optimizations (Phase 4)  
**Status**: Complete

## Research Questions

### 1. How does msgspec achieve high performance?

**Decision**: Use pre-allocation with direct C-API calls

**Rationale**: 
- msgspec pre-scans arrays to determine size before allocation
- Uses `PyList_New(size)` to allocate exact size upfront
- Uses `PyList_SET_ITEM(list, index, value)` which has zero overhead (no refcount checks, no resize checks)
- Eliminates all `append()` calls from hot loop

**Alternatives considered**:
- Keep using `append()`: Rejected - 30-40% overhead from Python protocol
- Use `PyList_Append()` C-API: Rejected - still has refcount and resize overhead
- Pre-allocate conservatively: Rejected - requires accurate count from pre-scan

**Implementation approach**: Two-pass parsing for arrays - first pass counts elements, second pass allocates and fills using SET_ITEM.

---

### 2. How does orjson achieve >3x speedup over stdlib?

**Decision**: Combination of Rust (memory safety + performance) and SIMD, but we'll use Cython with pointer arithmetic

**Rationale**:
- orjson is written in Rust which compiles to highly optimized native code
- Uses simd-json crate for SIMD-accelerated parsing
- We can't rewrite in Rust, but we can adopt pointer arithmetic principles
- Cython with raw pointers (`const unsigned char*`) eliminates bounds checks
- Achieves similar benefits without full Rust rewrite

**Alternatives considered**:
- Full Rust rewrite: Rejected - too much effort, breaks existing Cython infrastructure
- Keep indexed access: Rejected - 20-30% overhead from bounds checks
- Use Python buffer protocol: Rejected - still has overhead vs raw pointers

**Implementation approach**: Convert all `self.buf[self.pos]` to pointer arithmetic with `const unsigned char* p` and `p[0]`, `p++`.

---

### 3. What are the best character classification techniques?

**Decision**: Use lookup tables with bitfield encoding

**Rationale**:
- Lookup table: `CHAR_TABLE[c] & WHITESPACE_BIT` is O(1) with no branches
- Eliminates branch mispredictions from `if c == ' ' or c == '\t' or ...`
- Cache-friendly: 256-byte table fits in L1 cache
- Bitfields allow combining classifications (e.g., `DIGIT_BIT | NUMBER_CHAR_BIT`)

**Alternatives considered**:
- Character-by-character `if` chains: Rejected - 15-25% overhead from branches
- Range checks (`c >= '0' && c <= '9'`): Rejected - still has branches
- Switch statements: Rejected - compiler may not optimize perfectly

**Implementation approach**: 
```c
# Declare as static const to ensure L1 cache residency
cdef unsigned char CHAR_TABLE[256]  # Static at module level
CHAR_TABLE[' '] = WHITESPACE_BIT
CHAR_TABLE['\t'] = WHITESPACE_BIT
// ... etc
if CHAR_TABLE[c] & WHITESPACE_BIT: skip
```

**Note**: Declaring `CHAR_TABLE` as a module-level `cdef` array makes it static in the generated C code. Combined with read-only access patterns, modern compilers will keep this 256-byte table in L1 cache for optimal performance.

---

### 4. How can we batch-process whitespace?

**Decision**: Process 8 bytes at a time on aligned data

**Rationale**:
- Modern CPUs can load 8 bytes (uint64_t) in a single instruction
- Check if all 8 bytes are ASCII whitespace before processing individually
- Significantly faster for documents with extensive whitespace
- Fallback to byte-by-byte for unaligned data or when near end of buffer

**Alternatives considered**:
- SIMD instructions (SSE/AVX): Rejected - too complex, non-portable
- Process 4 bytes at a time: Rejected - 8 bytes is optimal for x86-64
- Always byte-by-byte: Rejected - misses optimization opportunity

**Implementation approach**:
```c
while p + 8 <= end:
    if all_8_bytes_are_whitespace(p):
        p += 8
    else:
        break
while p < end and is_whitespace(p[0]):
    p++
```

---

### 5. How to maintain line/column tracking with pointers?

**Decision**: Minimize tracking - only calculate when error occurs

**Rationale**:
- Current implementation updates `self.pos` after every character
- With pointers, we can advance freely and only calculate position for errors
- Position = `p - self.buf` (simple pointer subtraction)
- Line/column calculation is expensive but only needed for error messages

**Alternatives considered**:
- Update position after every character: Rejected - defeats pointer optimization purpose
- Track line/column separately: Rejected - adds overhead to hot loop
- Remove error positions: Rejected - violates FR-013 requirement

**Implementation approach**: Advance pointer freely, calculate `self.pos = p - self.buf` only when calling error handler or returning.

---

### 6. Can we use nogil for parallelization?

**Decision**: Add nogil blocks as preparation for future work, but don't parallelize yet

**Rationale**:
- Most parsing functions can be marked `nogil` since they don't call Python APIs
- Enables future multi-threaded parsing of multiple documents
- No overhead to add nogil declarations
- Actual parallelization deferred to future work (out of scope for this feature)

**Alternatives considered**:
- Implement multi-threading now: Rejected - out of scope, adds complexity
- Don't prepare for nogil: Rejected - simple to add, future-proofs code

**Implementation approach**: Mark hot loop functions with `nogil` where possible. Don't implement threading infrastructure yet.

---

### 7. How to optimize number parsing?

**Decision**: Use strtod/strtoll directly on buffer without copying

**Rationale**:
- Current implementation creates temporary string then parses
- Can use temporary null-terminated buffer on stack (char temp[64])
- For numbers <64 chars, no malloc/free needed
- strtod/strtoll are highly optimized C library functions

**Alternatives considered**:
- Hand-rolled float parser: Rejected - reinventing wheel, error-prone
- Keep creating Python string: Rejected - unnecessary allocation overhead
- Use sscanf: Rejected - slower than strtod

**Implementation approach**:
```c
char temp[64];
memcpy(temp, start, length);
temp[length] = '\0';
return strtod(temp, NULL);
```

---

### 8. How to handle dictionary key interning?

**Decision**: Keep existing interning implementation

**Rationale**:
- Already implemented using `PyUnicode_InternInPlace`
- Reduces memory usage for repeated keys
- Small overhead but significant memory savings on dict-heavy documents
- Compatible with all optimization phases

**Alternatives considered**:
- Remove interning: Rejected - loses memory efficiency
- Custom string pool: Rejected - more complex, marginal benefit

**Implementation approach**: No changes needed - existing implementation is optimal.

---

## Technology Selection

### Core Technologies

| Technology | Version | Purpose | Justification |
|------------|---------|---------|---------------|
| Cython | 3.0+ | C-extension compilation | Required for Python C-API access and pointer arithmetic |
| Python C-API | 3.10+ | Direct object manipulation | Required for PyList_SET_ITEM, PyDict_SetItem |
| GCC/Clang | Latest | Compiler | Required for -O3, -march=native, -ffast-math optimizations |

### Build Configuration

```python
# setup.py compiler flags
extra_compile_args=[
    "-O3",              # Maximum optimization
    "-march=native",    # Use all available CPU instructions
    "-ffast-math",      # Aggressive floating point optimizations
]
```

**Rationale**: These flags enable compiler-level optimizations that complement our code-level optimizations. `-march=native` allows compiler to use CPU-specific instructions. `-ffast-math` enables aggressive math optimizations safe for our use case.

---

## Best Practices Summary

### Phase 1: Pre-allocation
1. Pre-scan arrays by counting commas between opening `[` and closing `]`
2. Allocate with `PyList_New(count)`
3. Fill with `PyList_SET_ITEM(list, index, value)`
4. Never use `append()` in hot loop

### Phase 2: Pointer Arithmetic
1. Convert all `self.buf[self.pos]` to `const unsigned char* p` with `p[0]`
2. Advance with `p++` instead of `self.pos++`
3. Calculate position only for errors: `self.pos = p - self.buf`
4. Pass pointers between functions, not positions

### Phase 3: Lookup Tables
1. Initialize 256-byte character classification table at module load
2. Use bitfields for multiple characteristics (e.g., `WHITESPACE_BIT | NEWLINE_BIT`)
3. Replace all character checks with `CHAR_TABLE[c] & CATEGORY_BIT`
4. Batch-process whitespace 8 bytes at a time when aligned

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing tests | Run full test suite after each phase, 100% pass rate required |
| Memory regression | Monitor memory usage with tracemalloc, <10% increase allowed |
| Platform-specific bugs | Test on Linux and macOS, avoid non-portable code |
| Pointer arithmetic errors | Bounds check end pointer, use assertions in development |
| Performance regression | Benchmark after each change, revert if no improvement |

---

## Performance Expectations

Based on msgspec and orjson analysis:

| Phase | Technique | Expected Speedup | Cumulative Throughput |
|-------|-----------|------------------|----------------------|
| Baseline | Current implementation | 1.0x | 136 MB/s |
| Phase 1 | Pre-allocation | 2.0-2.5x | 272-340 MB/s |
| Phase 2 | Pointer arithmetic | 1.5-2.0x | 408-680 MB/s |
| Phase 3 | Lookup tables | 1.3-1.5x | 530-1020 MB/s |

**Conservative target**: 700 MB/s (5.1x improvement)
**Optimistic target**: 1000 MB/s (7.4x improvement)

---

## References

- **msgspec**: https://github.com/jcrist/msgspec - Python library using pre-allocation and minimal C-API calls
- **orjson**: https://github.com/ijl/orjson - Rust-based JSON parser with SIMD, 3-4x faster than stdlib
- **simdjson**: https://github.com/simdjson/simdjson - C++ SIMD JSON parser, inspiration for batching techniques
- **Python C-API**: https://docs.python.org/3/c-api/ - Official documentation for PyList_*, PyDict_* functions
- **Cython**: https://cython.readthedocs.io/ - Documentation for pointer arithmetic and nogil
