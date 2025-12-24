"""
Analysis of current bottlenecks and optimization strategy.

Target: 1 GB/s (7x improvement from 145 MB/s)

Key bottlenecks in current implementation:
1. String parsing: Multiple Python API calls, decode overhead
2. Number parsing: strtod/strtoll with temporary buffers
3. Dictionary/List operations: Not pre-allocated, append calls
4. Whitespace skipping: Character-by-character with GIL
5. Memory allocation: Frequent malloc/free cycles

Learnings from msgspec and orjson:
- msgspec: Uses raw pointer arithmetic, minimal PyObject creation
- orjson: SIMD for validation, pre-allocation, direct memory writes
- Both: Complete nogil for parsing, defer PyObject creation

Optimization strategy:
1. Complete nogil wrapper around entire parse
2. Raw pointer arithmetic (no self.buf[index])
3. Pre-allocate all containers based on scanning
4. Manual PyUnicode construction from char*
5. Inline all hot functions
6. Use lookup tables for character classification
7. SIMD-like tricks (process 8 bytes at once where possible)
"""
print(__doc__)
