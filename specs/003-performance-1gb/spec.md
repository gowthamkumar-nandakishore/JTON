# Feature Specification: MYSON Parser Performance Optimization to 700+ MB/s

**Feature Branch**: `003-performance-1gb`  
**Created**: 2025-12-24  
**Status**: Draft  
**Input**: User description: "MYSON Parser - Road to 700+ MB/s: Optimize parser from 136 MB/s to 700+ MB/s (5-7x improvement) through pre-allocation, raw pointer arithmetic, lookup tables, and other extreme optimizations inspired by msgspec and orjson. Stretch goal: 1 GB/s with additional SIMD optimizations (future Phase 4)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - List Pre-allocation Eliminates Append Overhead (Priority: P1)

A developer parsing large JSON arrays experiences significantly faster parsing because the parser pre-scans to determine array sizes and pre-allocates lists, using direct `PyList_SET_ITEM` instead of `append()`.

**Why this priority**: This is the single largest bottleneck (30-40% of parsing time). Pre-allocation eliminates Python protocol overhead, refcount operations, and resize checks. This phase alone should deliver 2-3x speedup.

**Independent Test**: Parse a large array-heavy JSON file (e.g., list of 100,000 objects). Measure throughput before and after pre-allocation. Verify correctness by comparing output with standard library.

**Acceptance Scenarios**:

1. **Given** a JSON array with 10,000 elements, **When** parsed with pre-allocation, **Then** throughput increases by at least 2x compared to current implementation.
2. **Given** a nested array structure, **When** parsed, **Then** all arrays use `PyList_SET_ITEM` with zero `append()` calls in the hot loop.
3. **Given** any valid JSON with arrays, **When** parsed, **Then** output matches standard library `json.loads()` exactly.

---

### User Story 2 - Raw Pointer Arithmetic Eliminates Bounds Checks (Priority: P2)

A developer parsing any JSON document experiences faster parsing because the parser uses raw `const unsigned char*` pointer arithmetic throughout, eliminating per-access bounds checks.

**Why this priority**: After pre-allocation, pointer arithmetic is the next largest bottleneck (20-30% of time). Direct pointer access is significantly faster than indexed access. This phase should deliver an additional 1.5-2x speedup on top of Phase 1.

**Independent Test**: Parse the 294 MB super_long.json file. Measure throughput with raw pointers vs indexed access. Profile to verify elimination of bounds check overhead.

**Acceptance Scenarios**:

1. **Given** any JSON document, **When** parsing with raw pointers, **Then** throughput increases by at least 1.5x over the pre-allocation baseline.
2. **Given** the parser implementation, **When** reviewing code, **Then** all hot loop access uses `const unsigned char* p` with `p[0]`, `p++` instead of `self.buf[self.pos]`.
3. **Given** whitespace skipping, **When** processing a document, **Then** pointer is advanced in-place with minimal position tracking.

---

### User Story 3 - Lookup Tables and Batch Processing Accelerate Character Classification (Priority: P3)

A developer parsing JSON with significant whitespace experiences faster parsing because the parser uses lookup tables for character classification and processes whitespace in 8-byte batches when possible.

**Why this priority**: Character-by-character processing causes branch mispredictions and cache misses (15-25% of time). Lookup tables and batching improve CPU pipeline efficiency. This phase should deliver an additional 1.3-1.5x speedup.

**Independent Test**: Parse a JSON document with varying amounts of whitespace. Measure throughput with lookup tables vs character-by-character checks. Verify batching activates on aligned data.

**Acceptance Scenarios**:

1. **Given** a JSON document with extensive whitespace, **When** parsed with lookup tables, **Then** throughput increases by at least 1.3x over the pointer arithmetic baseline.
2. **Given** whitespace skipping on aligned data, **When** processing, **Then** parser processes 8 bytes at a time where possible.
3. **Given** any character classification (digit, whitespace, alpha), **When** checking, **Then** lookup table is used instead of conditional branches.

---

### Edge Cases

Performance-specific edge cases:

- **Large arrays**: Arrays with 100,000+ elements must pre-allocate correctly without overflow
- **Deeply nested structures**: Recursion depth guard (1024 levels) must still work with pointer arithmetic
- **Unaligned data**: Batch processing must fall back to byte-by-byte when data is not 8-byte aligned
- **Empty structures**: Empty arrays `[]` and objects `{}` must not attempt to pre-allocate or scan
- **Mixed content**: Documents mixing arrays, objects, strings, numbers must benefit proportionally from each optimization
- **UTF-8 strings**: String decoding must remain correct with pointer arithmetic (no buffer overruns)
- **Number parsing**: Integer and float parsing must maintain accuracy while using zero-copy techniques
- **Infinity/NaN**: Special numeric values must parse correctly with optimized number parsing

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Parser MUST maintain 100% compatibility with existing MYSON/JSON parsing semantics - all existing tests must pass.
- **FR-002**: Parser MUST achieve measurable performance improvements at each optimization phase: Phase 1 (2-3x), Phase 2 (1.5-2x additional), Phase 3 (1.3-1.5x additional).
- **FR-003**: Array parsing MUST use pre-scanning to count elements, then `PyList_New(size)` to pre-allocate, then `PyList_SET_ITEM(list, index, value)` for zero-overhead insertion.
- **FR-004**: All parsing functions MUST use `const unsigned char*` pointers for buffer access instead of indexed access.
- **FR-005**: Whitespace skipping MUST use a 256-element lookup table for O(1) character classification.
- **FR-006**: Whitespace skipping MUST process 8 bytes at a time when data is 8-byte aligned and within bounds.
- **FR-007**: Character classification MUST use bitfield lookup tables with constants: `WHITESPACE_BIT`, `DIGIT_BIT`, `ALPHA_BIT`, `NUMBER_CHAR_BIT`.
- **FR-008**: Position tracking MUST be minimized - pointers advance in-place, with position calculation only when needed for errors.
- **FR-009**: Parser MUST support `nogil` blocks in pure pointer arithmetic functions: `prescan_array_size()`, `skip_whitespace_fast()`, and batch processing loops (functions with no Python object access).
- **FR-010**: Number parsing SHOULD use zero-copy techniques - parse directly from buffer without creating temporary strings.
- **FR-011**: Dictionary key interning MUST be retained from existing implementation for memory efficiency.
- **FR-012**: Recursion depth guard MUST remain at 1024 levels and work correctly with pointer-based parsing.
- **FR-013**: Error reporting MUST continue to provide line/column information despite pointer arithmetic optimizations.
- **FR-014**: Compiler optimizations MUST include `-O3 -march=native -ffast-math` for maximum performance.
- **FR-015**: Parser context MUST include `end_ptr` field pointing to end of buffer for bounds checking.
- **FR-016**: All pointer advancement operations MUST use bounds-checking functions (`check_bounds(p, end)` before dereferencing, `safe_increment(p, end)` for advancement).
- **FR-017**: Pointer arithmetic MUST validate `p < end` before accessing `p[0]` to prevent buffer overruns.
- **FR-018**: Memory allocation failures during `PyList_New()` MUST trigger cleanup of all temporary buffers via try...finally pattern.
- **FR-019**: Pre-scan failures (e.g., malformed arrays) MUST not leak temporary state or allocated memory.
- **FR-020**: All `nogil` blocks MUST ensure proper exception handling and resource cleanup on early exit.

### Assumptions

- Target hardware: Modern x86-64 CPU with standard instruction set
- File sizes: Optimizations target files from 1 MB to 500 MB (sweet spot for in-memory parsing)
- Memory: Sufficient RAM to load entire file into memory (no streaming)
- Python version: CPython 3.10+ with standard C-API
- Single-threaded: Optimizations focus on single-thread performance first
- Correctness over speed: Any optimization that breaks compatibility will be rejected

### Key Entities

- **Parser Context**: Buffer pointers (`const unsigned char* buf`, `const unsigned char* end_ptr`), current position, recursion depth, minimal state
- **Character Lookup Table**: 256-byte array mapping ASCII values to classification bitfields
- **Pre-scan Result**: Count of array elements determined by fast pre-scan before allocation
- **Pointer State**: Raw pointers (`p`, `start`, `end`) used throughout hot loop to minimize bounds checks

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Parser throughput increases from 136 MB/s to at least 300 MB/s after Phase 1 (pre-allocation).
- **SC-002**: Parser throughput increases to at least 500 MB/s after Phase 2 (raw pointers).
- **SC-003**: Parser throughput reaches 700 MB/s or higher after Phase 3 (lookup tables).
- **SC-004**: All existing tests (28 unit + integration tests) pass with 100% success rate.
- **SC-005**: Parsing correctness on super_long.json (294 MB) matches standard library output exactly.
- **SC-006**: Peak memory usage remains linear (O(n)) and increases by no more than 10% vs current implementation.
- **SC-007**: Benchmark results show consistent performance (standard deviation < 5% of mean).
- **SC-008**: Phase 1 eliminates all `list.append()` calls from array parsing hot loop.
- **SC-009**: Phase 2 eliminates all `self.buf[index]` access from hot loop.
- **SC-010**: Phase 3 implements lookup tables and batch whitespace skipping.
