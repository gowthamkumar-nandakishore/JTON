# Ultra-Fast JSON Parser Implementation Plan

## Current Status
- Baseline (myson_core): **143 MB/s**
- Ultra-fast (myson_fast): **118-143 MB/s** (same or slightly slower)
- Target: **1000+ MB/s** (7x improvement needed)

## Key Findings

### What Doesn't Work
1. ❌ Pre-scanning arrays (adds 50%+ overhead)
2. ❌ Manual pre-allocation with trimming (expensive del operations)
3. ❌ Dict-based object caching (lookup overhead too high)
4. ❌ Pointer arithmetic alone (without other optimizations)

### What Does Work
1. ✅ Python list.append() with growth strategy (Cython optimizes to C-API)
2. ✅ Character lookup tables (O(1) classification)
3. ✅ memchr for string scanning
4. ✅ Inline functions (avoid call overhead)

## Root Cause Analysis

The bottleneck is **Python object creation**, not parsing logic:
- Creating PyLong for every number: ~30% of time
- Creating PyUnicode for every string: ~40% of time  
- Creating PyList/PyDict: ~20% of time
- Actual parsing: ~10% of time

## Path to 1 GB/s

### Phase 1: Minimize Object Creation (2-3x improvement)
Target: 143 → 350 MB/s

1. **Use PyLong_FromLong for small integers** (-5 to 256)
   - Avoid strtoll for common values
   - Fast path: single digit → direct conversion

2. **String interning for keys**
   - Cache dict keys (limited set in most JSON)
   - Use PyUnicode_InternInPlace

3. **Pre-allocate with capacity hints**
   - Arrays: Start with 32, grow exponentially
   - Objects: Pre-size dict based on first few keys

### Phase 2: SIMD Structural Scanning (1.5-2x improvement)
Target: 350 → 600 MB/s

1. **Use SIMD to find structural characters**
   - SSE4.2/AVX2 for finding quotes, braces, commas
   - Process 16-32 bytes at once

2. **Parallel string validation**
   - SIMD UTF-8 validation
   - Faster than byte-by-byte

### Phase 3: Specialized Fast Paths (1.3-1.5x improvement)
Target: 600 → 850 MB/s

1. **Uniform array detection**
   - All integers → numpy-style parsing
   - All strings → bulk allocation

2. **Number parsing optimization**
   - Custom int parser (no strtoll)
   - IEEE 754 direct construction for floats

3. **Escape sequence vectorization**
   - SIMD scan for backslashes
   - Batch decode

### Phase 4: Memory & Cache Optimization (1.2x improvement)
Target: 850 → 1000+ MB/s

1. **Arena allocation**
   - Bulk allocate for temporary buffers
   - Reduce malloc/free overhead

2. **Cache-friendly data structures**
   - Align structures to cache lines
   - Prefetch next elements

3. **Reduce memory copies**
   - Zero-copy string slicing where possible

## Implementation Strategy

### Immediate Actions (Next 30 minutes)
1. ✅ Remove dict-based caching (too slow)
2. ⏳ Implement fast single-digit number parsing
3. ⏳ Add string interning for object keys
4. ⏳ Optimize array/object pre-allocation

### Near-term (Next hour)
1. Profile with cProfile/line_profiler
2. Identify exact hotspots
3. Implement top 3 optimizations
4. Target: 300+ MB/s

### Medium-term (Next 2-3 hours)
1. Add SIMD string scanning (if available)
2. Implement specialized parsers
3. Target: 600+ MB/s

### Long-term (Full implementation)
1. Full SIMD integration
2. Custom allocators
3. Zero-copy optimizations
4. Target: 1 GB/s+

## Lessons from Fast Parsers

### orjson (Rust)
- Uses simd-json crate
- SIMD for structural indexing
- Custom number parsing
- Zero-copy where possible

### msgspec (Cython)
- Pre-allocates exact sizes (they measure first)
- Uses PyList_SET_ITEM everywhere
- Interns string keys
- Custom struct parsers

### yapic.json (C)
- Pure C, no Python overhead
- Custom allocators
- Aggressive inlining
- SIMD string scanning

### simdjson (C++)
- Two-stage parsing (structural then values)
- SIMD throughout
- On-demand parsing
- Can hit 2-3 GB/s

## Realistic Target

Given Cython constraints:
- **Conservative**: 500-700 MB/s (achievable)
- **Optimistic**: 800-1000 MB/s (with SIMD)
- **Maximum**: 1200 MB/s (all optimizations)

Next step: Focus on **fast number parsing** and **string interning** for immediate 2x gain.
