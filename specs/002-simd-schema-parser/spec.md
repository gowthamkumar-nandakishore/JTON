# Feature Specification: SIMD-Accelerated MYSON with Schema-Guided Optimization

**Feature Branch**: `002-simd-schema-parser`  
**Created**: December 24, 2025  
**Status**: Draft  
**Input**: User description: "Replace Cython extensions with Rust+SIMD implementation targeting >1.5 GB/s. Zero tolerance for performance regression below current 233.9 MB/s baseline. Explicit schema-only for maximum throughput. AVX2 mandatory baseline, text-only format, approximate error positions."

## Clarifications

### Session 2025-12-24

- Q: Schema mode behavior for regular JSON arrays - should schema parameter only apply to Zen Grid tables, or also optimize regular JSON arrays like `[{"id":1,"name":"Alice"}]`? → A: Apply schema to regular JSON arrays when provided, using field-position mapping from object keys (Option B)
- Q: Zen Grid header arity mismatch - what happens when row has more values than headers (e.g., `[: a,b; 1,2,3 ]`)? → A: Ignore extra values (truncate to header count). Matches current myson_core.pyx implementation which drops values once column index exceeds header arity.
- Q: Memory allocation upper bound for pre-allocation safety - should parser limit pre-allocation when SIMD scan detects millions of semicolons to prevent OOM attacks? → A: Limit pre-allocation to 1 million rows maximum, fall back to incremental allocation beyond that. Covers 99.9% of real workloads while preventing DoS via malformed input.

## Glossary & Definitions

**Large Files**: Defined strictly as files ≥100,000,000 bytes (100 MB exactly). Performance requirements referencing "large files" use this threshold.

**Homogeneous Arrays**: Arrays where every element possesses an identical key set AND identical data types per key. Example: `[{"id":1,"name":"A"}, {"id":2,"name":"B"}]` is homogeneous (both have `id` as int, `name` as str).

**Linear Scaling**: Parallel parsing performance achieving ≥14x speedup on 16 cores (87.5% efficiency). Accounts for thread overhead and memory bandwidth limits.

**Zen Grid Optimization**: Schema-guided parsing optimization for Zen Grid tables. Triggers at ≥10,000 rows; speedup scales proportionally with row count (more rows = greater benefit from pre-allocation and interning).

## User Scenarios & Testing

### User Story 1 - High-Throughput Data Ingestion (Priority: P1)

A machine learning engineer is preprocessing large JSON datasets (100+ MB) containing training data. They need to parse millions of records per second to feed their data pipeline without I/O becoming the bottleneck.

**Why this priority**: Core value proposition. The entire feature exists to eliminate parsing as a bottleneck in high-throughput LLM and data processing systems. Without this, the feature has no purpose.

**Independent Test**: Can be fully tested by parsing test_data/super_long.json (294 MB) and measuring throughput in MB/s. Success = ≥1.5 GB/s on AVX2 hardware.

**Acceptance Scenarios**:

1. **Given** a 294 MB JSON file with homogeneous array data, **When** user calls `myson.loads(data)`, **Then** parsing completes at ≥1.5 GB/s on AVX2-capable CPU
2. **Given** a 2.2 MB JSON file (canada.json), **When** user calls `myson.loads(data)`, **Then** parsing completes at ≥1.5 GB/s with zero memory allocations beyond output structures
3. **Given** the current benchmark baseline of 233.9 MB/s, **When** running the same benchmark suite on the new implementation, **Then** performance never drops below 233.9 MB/s on any test payload

---

### User Story 2 - Schema-Guided Fast Path (Priority: P2)

A backend engineer is deserializing API responses with known structure (User objects with id, name, email fields). They want to skip the overhead of dictionary key hashing by providing the schema upfront.

**Why this priority**: Differentiating feature that enables the 1.5+ GB/s target. Without schema guidance, we cannot skip key hashing and achieve maximum throughput. However, the parser must still work without schemas for compatibility.

**Independent Test**: Can be tested by defining a Python dataclass `User(id: int, name: str, active: bool)`, parsing a Zen Grid table `[: id,name,active; 1,Alice,true ]` with `myson.loads(data, schema=User)`, and verifying >1 GB/s throughput with zero key lookups.

**Acceptance Scenarios**:

1. **Given** a Python dataclass with typed fields, **When** user calls `myson.loads(zen_grid_data, schema=UserClass)`, **Then** parser uses positional field mapping and skips dictionary key hashing entirely
2. **Given** a msgspec.Struct schema, **When** user calls `myson.loads(data, schema=MyStruct)`, **Then** parser compiles schema to Rust FieldDescriptor vector and uses specialized type-specific parsers
3. **Given** a schema with string fields marked as categorical, **When** parsing repeated values like "active"/"inactive", **Then** parser interns strings and reuses Python string objects via reference counting

---

### User Story 3 - Backward Compatibility with Existing Tests (Priority: P1)

An existing MYSON user has 400+ JSON test fixtures and a comprehensive test suite validating edge cases (JSONTestSuite parsing files, jsonchecker validation, roundtrip tests). They need the new implementation to pass all existing tests without modification.

**Why this priority**: Critical for adoption. Breaking existing users is unacceptable. This is a rewrite of the implementation, not the specification.

**Independent Test**: Run `pytest tests/test_comprehensive.py -q` and verify 100% pass rate on all 400+ JSON fixtures.

**Acceptance Scenarios**:

1. **Given** the test_comprehensive.py suite with 315 JSONTestSuite parsing files, **When** running pytest, **Then** all y_ files (should pass) parse successfully and all n_ files (should fail) raise appropriate errors
2. **Given** the jsonchecker validation suite (33 fail files, 3 pass files), **When** running tests, **Then** parser correctly rejects ≥26/33 invalid files and accepts all 3 valid files
3. **Given** existing benchmarks in benchmarks/benchmark_comparison.py, **When** running the suite, **Then** token efficiency remains identical (48.8% reduction vs JSON pretty, 19.6% vs compact) because wire format is unchanged

---

### User Story 4 - Zen Grid Table Parsing Optimization (Priority: P2)

A data scientist is working with tabular data in MYSON Zen Grid format (`[: col1,col2; val1,val2; val3,val4 ]`). They need the parser to handle tables with thousands of rows efficiently by pre-allocating memory and reusing header strings.

**Why this priority**: Tables are the primary token-saving feature of MYSON (19.6% reduction). Optimizing their parsing is essential for maintaining competitive performance against orjson while preserving token efficiency.

**Independent Test**: Create a Zen Grid with 10,000 rows and 5 columns, parse it, and verify (a) memory is pre-allocated after scanning semicolons, (b) header strings are allocated once and reused via Py_INCREF, (c) throughput exceeds 500 MB/s.

**Acceptance Scenarios**:

1. **Given** a Zen Grid table `[: h1,h2,h3; ... ]` with 10,000 rows, **When** parser encounters the opening `[:`, **Then** it SIMD-scans for `;` delimiters to count rows and pre-allocates Vec<PyDict> with exact capacity before parsing values
2. **Given** a Zen Grid with header `id,name,status`, **When** parsing 10,000 rows, **Then** the three header strings are allocated exactly once and reused for all rows via Python reference counting
3. **Given** a Zen Grid with nested JSON objects in cells `[: data; {"x":1}; {"x":2} ]`, **When** parsing, **Then** parser delegates nested `{...}` to JSON parser and ignores table delimiters inside braces

---

### User Story 5 - Multi-Threaded Parsing for Server Workloads (Priority: P3)

A cloud infrastructure engineer is running a data processing service on AWS Graviton (16 cores) that ingests large JSON batches (500+ MB). They want to leverage parallelism to achieve >10 GB/s throughput by splitting input at row boundaries.

**Why this priority**: Phase 2 feature. Not required for MVP. Provides scaling for extreme workloads but adds implementation complexity. Must not compromise single-threaded performance.

**Independent Test**: Parse a 500 MB Zen Grid file with `myson.loads(data, schema=X, parallel=True)` on a 16-core machine, verify linear scaling (16x speedup), and confirm >10 GB/s aggregate throughput.

**Acceptance Scenarios**:

1. **Given** a 500 MB Zen Grid file and a 16-core CPU, **When** user calls `myson.loads(data, schema=User, parallel=True)`, **Then** parser splits input at `]` or `\n` boundaries, spawns Rayon worker threads, and achieves near-linear scaling (>14x speedup)
2. **Given** parallel mode is enabled, **When** no schema is provided, **Then** parser raises an error explaining that parallel mode requires explicit schema (schema-free parsing is inherently serial due to context dependency)
3. **Given** parallel mode is enabled, **When** running on a single-core machine, **Then** parser gracefully degrades to single-threaded execution without crashing or performance penalty

---

### Edge Cases

#### JSON Compatibility
- **Numbers**: Parser must handle integers, floats, scientific notation (1e10), negative zero (-0), and edge cases like 9223372036854775807 (max int64) with exact equality to stdlib json
- **Strings**: Parser must handle all escape sequences (`\r\n\t\b\f\\"`, `\u0000`, `\uD834\uDD1E` surrogate pairs), UTF-8 encoding, and reject invalid escapes like `\x`
- **Nesting**: Parser must handle deeply nested arrays/objects up to reasonable limits (current implementation supports 1000 levels) without stack overflow
- **Whitespace**: Parser must accept JSON with any combination of spaces, tabs, newlines, carriage returns between structural elements

#### Unquoted Keys (MYSON Extension)
- **Valid**: Alphanumeric ASCII keys like `id`, `userName123` must parse without quotes
- **Invalid**: Keys with punctuation (`user-name`), Unicode (`名前`), or starting with digits (`123id`) must be rejected with clear error messages
- **Collision**: Unquoted key `true` must be treated as identifier, not boolean literal

#### Zen Grid Tables (MYSON Extension)
- **Header Arity - Too Many Values**: Table `[: a,b; 1,2,3 ]` with 3 values but 2 headers must ignore extra values (parse as `[{"a":1,"b":2}]`), matching current implementation
- **Header Arity - Too Few Values**: Table `[: a,b,c; 1,2 ]` with 2 values but 3 headers must null-fill missing cells (parse as `[{"a":1,"b":2,"c":null}]`), matching current implementation
- **Empty Tables**: `[: ]` and `[: h1,h2; ]` (header with no rows) must parse as empty list `[]`
- **Delimiter Collision**: String value containing `;` or `,` must be properly escaped or quoted: `[: name; "Smith, John" ]`
- **Nested Structures**: Cells containing `{...}` or `[...]` must delegate to JSON parser: `[: data; {"x":1,"y":[2,3]} ]` must parse nested object correctly
- **Trailing Delimiters**: `[: a,b,; 1,2, ]` with trailing commas must match current behavior (likely ignored)

#### Comments (MYSON Extension)
- **Line Comments**: `// comment` must be treated as whitespace and not affect parsing
- **Block Comments**: `/* multi\nline */` must be treated as whitespace
- **Adjacent to Values**: `[1 // comment\n, 2]` must parse as `[1, 2]`
- **Inside Strings**: `"text // not a comment"` must preserve literal text
- **Nested Block Comments**: Implementation-defined (likely not supported, but must not crash)

#### Error Reporting with Approximate Positions
- **Syntax Errors**: Invalid JSON like `{key: value}` (unquoted value) must report error with approximate position (±32 bytes due to SIMD vector width)
- **Unexpected EOF**: Unclosed string or object must report position near end of input
- **Type Mismatches (Schema Mode)**: If schema expects int but input has string, error must indicate field name and approximate byte offset

#### Performance Regressions
- **Small Files**: Parsing small JSON files (<1 KB) must not be slower than current implementation (overhead of SIMD setup must be amortized)
- **Worst-Case Inputs**: Deeply nested structures, long strings, large numbers must not trigger pathological slowdowns
- **Memory Pressure**: Parser must not allocate excessive temporary buffers (zero-copy principle must apply wherever possible)

## Requirements

### Functional Requirements

- **FR-001**: Parser MUST accept all valid JSON (RFC 8259) with identical semantics to Python stdlib json.loads, including numbers, strings, booleans, null, arrays, and objects.

- **FR-002**: Parser MUST accept unquoted object keys composed solely of ASCII alphanumerics (a-z, A-Z, 0-9, underscore); all other unquoted keys MUST be rejected with error messages indicating approximate position.

- **FR-003**: Parser MUST support MYSON Zen Grid table arrays with syntax `[: header_fields; row_values ]` where semicolons separate rows and commas separate columns. When row has more values than headers, extra values are ignored (truncated). When row has fewer values than headers, missing values are null-filled. This matches current myson_core.pyx implementation.

- **FR-004**: Parser MUST support single-line comments (`//`) and multi-line block comments (`/* ... */`) as whitespace-equivalent tokens, preserving exact parsing semantics of commented structures.

- **FR-005**: Parser MUST use SIMD vector instructions (AVX2 baseline, AVX-512 fast path) to scan for structural characters (`{`, `[`, `:`, `;`, `,`, `]`, `}`), processing 32 bytes per cycle on AVX2 and 64 bytes per cycle on AVX-512.

- **FR-006**: Parser MUST fail the build on CPUs without AVX2 support (pre-2013 hardware) with a clear error message stating the minimum CPU requirement.

- **FR-007**: Parser MUST provide an optional `schema` parameter accepting Python dataclass or msgspec.Struct types, enabling schema-guided parsing that skips dictionary key hashing and uses positional field mapping for both regular JSON arrays of objects and Zen Grid tables.

- **FR-008**: When schema is provided, parser MUST compile schema to Rust FieldDescriptor vector and use specialized type-specific parsers for zero-copy deserialization: `parse_int_simd` (integers), `parse_float_simd` (floating-point), `parse_bool_byte` (booleans), `parse_string_view` (zero-copy strings), and `parse_null` (null values). For regular JSON arrays, parser maps object keys to schema field positions on first object, then uses positional parsing for remaining objects.

- **FR-009**: Parser MUST implement string interning for dictionary keys and categorical string values, allocating each unique string once and reusing via Python reference counting (Py_INCREF).

- **FR-010**: Parser MUST use Python Buffer Protocol to access input bytes without copying when input is an immutable bytes object.

- **FR-011**: Parser MUST provide a parallel parsing mode (`parallel=True` parameter) that requires explicit schema, splits input at table row boundaries, and uses Rayon thread pool for multi-core execution (Phase 2).

- **FR-012**: Error messages MUST report approximate byte offsets (±32 bytes due to SIMD vector width) and include excerpt of malformed input for debugging.

- **FR-013**: Parser MUST maintain identical wire format to current MYSON implementation, ensuring token efficiency metrics (48.8% reduction vs JSON pretty, 19.6% vs compact) are preserved.

### Performance Requirements

- **PR-001**: Parser MUST achieve ≥1.5 GB/s throughput on AVX2-capable CPUs when parsing large JSON files (>100 MB) with homogeneous arrays.

- **PR-002**: Parser MUST achieve ≥1.5 GB/s throughput on both test_data/canada.json (2.2 MB) and test_data/super_long.json (294 MB) payloads, measured via benchmark_comparison.py.

- **PR-003**: Parser MUST NEVER regress below 233.9 MB/s (current baseline) on any existing benchmark payload; CI pipeline MUST fail if this threshold is violated.

- **PR-004**: Schema-guided parsing MUST achieve >1 GB/s throughput on Zen Grid tables with homogeneous rows (10,000+ rows) by eliminating key hashing overhead.

- **PR-005**: Zen Grid table parsing MUST pre-allocate output Vec<PyDict> with exact row count by SIMD-scanning for semicolons in a single pass before parsing values. Pre-allocation is capped at 1 million rows maximum; tables exceeding this threshold fall back to incremental allocation to prevent OOM attacks.

- **PR-006**: Parser MUST use AVX2 instructions to skip whitespace in 32-byte batches, reducing instruction count compared to byte-by-byte iteration.

- **PR-007**: Number parsing MUST use 256-byte lookup tables for digit validation instead of conditional branches to minimize CPU pipeline stalls.

- **PR-008**: Parallel mode (Phase 2) MUST achieve >10 GB/s aggregate throughput on 16-core AVX-512 CPUs with linear scaling (near 16x speedup).

- **PR-009**: Parser MUST minimize Python object allocations by using unsafe fast paths like PyList_SET_ITEM and bulk dictionary construction where safe.

- **PR-010**: Parser MUST NOT regress on small files (<1 KB); SIMD setup overhead must be <10% compared to baseline. Performance on <1 KB payloads must maintain ≥233.9 MB/s floor to avoid pathological slowdowns.

### Compatibility Requirements

- **CR-001**: Parser MUST pass 100% of existing test_comprehensive.py test suite (400+ JSON fixtures) without modification.

- **CR-002**: Parser MUST correctly handle JSONTestSuite parsing files: all y_ files (should pass) must parse successfully, all n_ files (should fail) must raise exceptions.

- **CR-003**: Parser MUST correctly handle jsonchecker validation suite: ≥26/33 fail files must be rejected, all 3 pass files must be accepted.

- **CR-004**: Parser MUST handle roundtrip and transform test suites with 100% pass rate, ensuring parse(dumps(x)) == x equivalence.

- **CR-005**: Parser MUST maintain API compatibility with current `myson.loads(data)` signature, with optional `schema` and `parallel` parameters.

- **CR-006**: Build system MUST transition from setuptools + Cython to maturin + Rust, removing all references to myson_core.pyx from pyproject.toml.

- **CR-007**: Existing benchmarks (benchmark_comparison.py, combined_benchmark_report.py, token_savings_analysis.py) MUST run without modification and report metrics in identical format.

### Key Entities

- **SIMD Scanner**: Hardware-accelerated module that processes 32-byte (AVX2) or 64-byte (AVX-512) chunks of input to locate structural characters using vector comparison instructions (`_mm256_cmpeq_epi8`, `_mm512_cmpeq_epi8`). Returns bitmask of delimiter positions.

- **FieldDescriptor**: Rust representation of Python dataclass or msgspec.Struct, compiled to a vector of FieldType entries (Int, Bool, String, etc.) with metadata (field name, offset, nullability). Used for positional parsing without key lookup.

- **String Interner**: Cache mapping raw UTF-8 byte slices to Python string objects (PyString). Maintains reference count to prevent duplicate allocations for repeated keys or categorical values.

- **Zero-Copy String View**: Python string object backed by input buffer memory via Buffer Protocol. Eliminates allocation for immutable strings by referencing original bytes object.

- **Zen Grid Table**: MYSON syntax extension for homogeneous arrays: `[: header; rows ]`. Parsed by pre-scanning semicolons to count rows, pre-allocating output list, then parsing each row as dictionary with interned header keys.

- **FieldDescriptor**: Rust struct containing field metadata for schema-guided parsing: field name (interned string), type tag (Int/Float/Bool/String/Null), byte offset in output struct, and parser function pointer.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Parser achieves ≥1.5 GB/s throughput on test_data/canada.json (2.2 MB) and test_data/super_long.json (294 MB) when measured with benchmark_comparison.py on AVX2 hardware.

- **SC-002**: Parser never regresses below 233.9 MB/s on any existing benchmark payload; CI pipeline fails builds violating this threshold.

- **SC-003**: All 400+ existing tests in test_comprehensive.py pass without modification, including 315 JSONTestSuite parsing files, 36 jsonchecker files, 27 roundtrip files, and 18 transform files.

- **SC-004**: Schema-guided parsing (with `schema=UserClass` parameter) achieves >1 GB/s throughput on Zen Grid tables with 10,000+ homogeneous rows by eliminating dictionary key hashing.

- **SC-005**: Token efficiency metrics remain identical to current implementation: 48.8% reduction vs JSON pretty-print, 19.6% reduction vs JSON compact, as measured by token_savings_analysis.py.

- **SC-006**: Parallel parsing mode (Phase 2, `parallel=True` parameter) achieves >10 GB/s aggregate throughput on 16-core AVX-512 hardware with near-linear scaling (≥14x speedup).

- **SC-007**: Build system successfully transitions from setuptools + Cython to maturin + Rust, with pyproject.toml updated and myson_core.pyx deleted, and zero build failures on CI.

- **SC-008**: Efficiency score (Speed × Token Reduction Factor) improves from current 279.69 to ≥2400 (calculated as 1500 MB/s × 1.60 reduction factor).

- **SC-009**: 95% of parsing errors report approximate byte positions within ±32 bytes of actual error location, with excerpt of malformed input included in error message.


## Assumptions

- **A-001**: Target hardware has AVX2 support (Intel Haswell 2013+ or AMD Excavator 2015+). Pre-2013 CPUs are explicitly unsupported.

- **A-002**: Input JSON data is provided as immutable bytes objects, enabling zero-copy string views via Python Buffer Protocol.

- **A-003**: Zen Grid tables contain homogeneous rows (all rows have same schema), which is the common case and enables schema-guided optimization.

- **A-004**: Parallel parsing (Phase 2) is only used for payloads >10 MB where multi-threading overhead is amortized.

- **A-005**: Error position approximation (±32 bytes) is acceptable for high-throughput use cases where performance is prioritized over exact error diagnostics.

- **A-006**: Existing test suite (400+ fixtures) provides sufficient coverage to validate correctness during Cython-to-Rust migration.

- **A-007**: Benchmark payloads (canada.json, super_long.json) are representative of real-world workloads for LLM data ingestion.

- **A-008**: Text-only serialization format is sufficient; binary formats like MessagePack are not needed for LLM token efficiency.

## Out of Scope

- **OS-001**: Scalar fallback for CPUs without AVX2 support. Pre-2013 hardware will not be supported.

- **OS-002**: Binary serialization formats (MessagePack, Protocol Buffers). MYSON remains text-only to preserve BPE tokenization advantages.

- **OS-003**: Automatic schema inference from sample data. Users must provide explicit schema for schema-guided mode via `schema=` parameter.

- **OS-004**: Support for non-Python languages. While Rust core is language-agnostic, only Python bindings via PyO3 will be provided.

- **OS-005**: Streaming/incremental parsing. Parser requires full input in memory (bytes object).

- **OS-006**: Custom number precision (arbitrary-precision integers, decimal types). Parser uses Python's built-in int/float types matching stdlib json behavior.

- **OS-007**: SIMD implementations for non-AVX2/AVX-512 architectures (ARM NEON will be Phase 3, not covered in this spec).

- **OS-008**: Exact error positions (byte-level precision). Error reporting provides approximate positions (±32 bytes) due to SIMD batch processing.

## Dependencies

- **D-001**: Rust toolchain (1.70+) with maturin for building Python extensions.

- **D-002**: PyO3 crate for Rust-Python interop and Python C-API bindings.

- **D-003**: Python 3.10+ with support for Buffer Protocol and dataclasses.

- **D-004**: AVX2-capable CPU (Intel Haswell 2013+ or AMD Excavator 2015+) for baseline build.

- **D-005**: AVX-512 CPU (Intel Skylake-X 2017+ or AMD Zen 4 2022+) for fast path optimization (optional).

- **D-006**: msgspec library for schema definition compatibility (optional, only if users want msgspec.Struct support).

- **D-007**: Rayon crate for multi-threaded parsing (Phase 2 only).

- **D-008**: Existing test infrastructure (pytest, tiktoken for token counting).

## Risks & Mitigations

- **R-001**: **Risk**: SIMD implementation complexity may introduce bugs not covered by existing test suite. **Mitigation**: Add fuzzing with cargo-fuzz to test malformed inputs. Run all 400+ existing tests on every commit.

- **R-002**: **Risk**: Approximate error positions (±32 bytes) may hinder debugging for users. **Mitigation**: Include excerpt of malformed input in error message. Document trade-off clearly in API documentation.

- **R-003**: **Risk**: Zero-copy string views may cause memory leaks if input buffer is not properly managed. **Mitigation**: Document requirement that input must be immutable bytes object. Add runtime checks to prevent use-after-free.

- **R-004**: **Risk**: Performance regression during incremental development (e.g., Step 1 may be slower than Cython baseline). **Mitigation**: CI fails if any commit drops below 233.9 MB/s. Maintain strict performance discipline from first commit.

- **R-005**: **Risk**: Build system migration from setuptools to maturin may break existing user workflows. **Mitigation**: Maintain identical API (`myson.loads`). Provide migration guide documenting build changes. Test wheel packaging on Linux/macOS/Windows.

- **R-006**: **Risk**: AVX2 requirement may exclude users on old hardware. **Mitigation**: Document CPU requirements prominently in README. Provide clear build error message on unsupported hardware.

- **R-007**: **Risk**: Schema-guided mode may be confusing for users unfamiliar with dataclasses. **Mitigation**: Provide extensive examples in documentation. Schema parameter is optional; default behavior remains schema-free for backward compatibility.

- **R-008**: **Risk**: Parallel mode (Phase 2) may introduce race conditions or memory safety issues. **Mitigation**: Use Rust's ownership system to prevent data races. Extensive testing with ThreadSanitizer. Gate behind `parallel=True` flag so default path remains single-threaded and safe.

- **R-009**: **Risk**: Malicious input with millions of semicolons could trigger OOM during pre-allocation scan. **Mitigation**: Cap pre-allocation at 1 million rows maximum. Fall back to incremental allocation for larger tables. Add input size validation rejecting payloads >1 GB without explicit configuration.

