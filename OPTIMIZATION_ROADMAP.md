# MYSON Parser - Road to 1 GB/s

## Current Status
- **Current**: 136 MB/s on 294 MB file
- **Target**: 1000 MB/s (7.4x improvement needed)
- **Reference**: Python's `json` module at ~112 MB/s

## Performance Analysis

### Bottlenecks Identified (via profiling patterns from msgspec/orjson)

1. **Python API Overhead** (30-40% of time)
   - `PyList_Append()` has refcount overhead
   - `dict[key] = value` uses __setitem__ protocol
   - String decoding creates temporary objects

2. **Memory Allocation** (20-30% of time)
   - Frequent malloc/free cycles
   - No pre-allocation of containers
   - String interning not used

3. **Character Processing** (15-25% of time)
   - Whitespace skip is byte-by-byte
   - No lookup tables
   - Branch mispredictions

4. **Number Parsing** (10-15% of time)
   - Creating temp buffers
   - strtod/strtoll overhead

## Optimization Strategy (Inspired by msgspec & orjson)

### Phase 1: Eliminate Python API Calls in Hot Loop (**2-3x speedup**)

```cython
# BEFORE (slow)
list.append(value)  # Python protocol, refcount, resize checks

# AFTER (fast)
Py_INCREF(value)
PyList_SET_ITEM(list, index, value)  # Direct C-API, no overhead
```

**Implementation**:
- Pre-scan arrays to count elements
- Use `PyList_New(size)` to pre-allocate
- Use `PyList_SET_ITEM()` instead of `append()`
- Use direct `PyDict_SetItem()` (already done)

### Phase 2: Raw Pointer Arithmetic (**1.5-2x speedup**)

```cython
# BEFORE (slow)
while self.pos < self.length:
    c = self.buf[self.pos]  # Bounds check on every access
    self.pos += 1

# AFTER (fast)
cdef const unsigned char* p = self.buf + self.pos
cdef const unsigned char* end = self.buf + self.length
while p < end:
    c = p[0]  # Direct pointer access, no bounds check
    p += 1
self.pos = p - self.buf
```

**Implementation**:
- Pass `const unsigned char*` pointers throughout
- Use `nogil` where possible
- Minimize position updates

### Phase 3: Lookup Tables & Batching (**1.3-1.5x speedup**)

```cython
# Character classification lookup table
cdef unsigned char[256] CHAR_TYPE
# Bits: 0=digit, 1=whitespace, 2=alpha, 3=structural

# Fast whitespace skip (8 bytes at a time on aligned data)
cdef const unsigned char* skip_ws_fast(const unsigned char* p, const unsigned char* end) nogil:
    # Check 8 bytes at once when possible
    cdef unsigned long long* p8
    while p + 8 <= end:
        p8 = <unsigned long long*>p
        if p8[0] & 0x8080808080808080ULL:  # Has non-ASCII
            break
        # Check all 8 bytes are whitespace
        if (CHAR_TYPE[p[0]] & CHAR_TYPE[p[1]] & ... & CHAR_TYPE[p[7]]) & WS_BIT:
            p += 8
        else:
            break
    # Finish remaining bytes
    while p < end and CHAR_TYPE[p[0]] & WS_BIT:
        p += 1
    return p
```

### Phase 4: String Interning & Pooling (**1.2x speedup on dict-heavy data**)

```cython
# Intern all dict keys
cdef object key = PyUnicode_FromStringAndSize(...)
cdef PyObject* pkey = <PyObject*>key
PyUnicode_InternInPlace(&pkey)
key = <object>pkey
```

**Already implemented** ✓

### Phase 5: Zero-Copy Number Parsing (**1.1-1.2x speedup**)

```cython
# Parse number directly from buffer without creating temp string
cdef double parse_float_direct(const unsigned char* start, Py_ssize_t len) nogil:
    # Hand-rolled float parser (or optimized strtod with no copy)
    ...
```

### Phase 6: Compiler Optimizations

```python
# setup.py
extra_compile_args=[
    "-O3",                    # Max optimization
    "-march=native",          # Use all CPU features
    "-ffast-math",           # Aggressive float opts
    "-flto",                 # Link-time optimization
    "-funroll-loops",        # Loop unrolling
]
```

## Implementation Priority

### High Priority (Must Have for 1 GB/s)
1. ✅ PyList_SET_ITEM pre-allocation
2. ✅ Raw pointer arithmetic everywhere
3. ✅ Lookup tables for char classification  
4. ✅ Batch whitespace skipping

### Medium Priority (Nice to Have)
5. ✅ String interning (already done)
6. Zero-copy number parsing
7. Object pooling

### Low Priority (Diminishing Returns)
8. SIMD instructions
9. Custom allocator
10. Profile-guided optimization

## Realistic Target

With Phases 1-3 implemented:
- **Phase 1**: 136 → 300 MB/s (2.2x)
- **Phase 2**: 300 → 500 MB/s (1.67x)
- **Phase 3**: 500 → 700 MB/s (1.4x)

**Achievable**: **700-800 MB/s** with pure Cython optimizations

**1 GB/s** would require:
- Rust/C implementation (like orjson)
- SIMD (like simdjson)
- Or extreme micro-optimizations

## Next Steps

1. Implement Phase 1 (Pre-allocation)
2. Implement Phase 2 (Pointer arithmetic)
3. Implement Phase 3 (Lookup tables)
4. Benchmark each phase
5. Profile to find remaining bottlenecks

## References

- **msgspec**: https://github.com/jcrist/msgspec
  - Uses pre-allocation extensively
  - Raw pointer arithmetic throughout
  - Minimal Python API calls

- **orjson**: https://github.com/ijl/orjson  
  - Written in Rust for maximum performance
  - Uses SIMD via simd-json
  - Achieves 3-4x speedup vs stdlib json

- **simdjson**: https://github.com/simdjson/simdjson
  - C++ library using SIMD
  - Processes multiple bytes per instruction
  - Requires deep architectural knowledge
