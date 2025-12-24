# Tasks: SIMD-Accelerated MYSON with Schema-Guided Optimization

**Feature Branch**: `002-simd-schema-parser`  
**Input**: Design documents from `/specs/002-simd-schema-parser/`  
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/)

**Implementation Strategy**: MVP-first with incremental delivery. User Story 1 (P1) delivers baseline performance, User Story 2 (P2) adds schema optimization, remaining stories build on foundation.

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Rust build system and project structure

- [X] T001 Create Rust crate structure at src/myson_core/ per plan.md project structure
- [X] T002 Initialize Cargo.toml with PyO3, maturin dependencies (Rust 1.70+)
- [X] T003 [P] Create pyproject.toml entry points for maturin build system
- [X] T004 [P] Create src/myson_core/src/lib.rs with PyO3 module definition
- [X] T005 [P] Add .gitignore entries for target/, Cargo.lock, *.so bindings
- [X] T006 Verify maturin develop builds successfully on AVX2 hardware

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Build & Tooling Foundation

- [X] T007 Configure CPU feature detection in src/myson_core/src/lib.rs (AVX2 required, AVX-512 optional)
- [X] T008 [P] Add build.rs script to fail on pre-2013 CPUs without AVX2 support
- [X] T009 [P] Configure pytest in tests/ to run 400+ existing test fixtures
- [X] T010 [P] Configure cargo test for Rust unit tests in src/myson_core/src/

### Core Type Definitions

- [X] T011 [P] Implement FieldType enum in src/myson_core/src/types/field_descriptor.rs
- [X] T012 [P] Implement FieldDescriptor struct in src/myson_core/src/types/field_descriptor.rs
- [X] T013 [P] Implement InternedString wrapper in src/myson_core/src/types/interner.rs
- [X] T014 [P] Implement StructuralIndex struct in src/myson_core/src/types/structural_index.rs
- [X] T015 [P] Implement ZenGridHeader struct in src/myson_core/src/types/mod.rs
- [X] T016 [P] Implement ParseContext struct in src/myson_core/src/types/mod.rs

### SIMD Structural Scanner (Blocking for All Parsing)

- [X] T017 Create src/myson_core/src/simd/mod.rs module with public scanner API
- [X] T018 Implement AVX2 structural character scanner in src/myson_core/src/simd/scanner_avx2.rs (scaffold with scalar fallback)
- [ ] T019 Add AVX2 bitmask extraction (_mm256_movemask_epi8) in src/myson_core/src/simd/scanner_avx2.rs (TODO: full implementation)
- [ ] T020 [P] Implement AVX-512 fast path in src/myson_core/src/simd/scanner_avx512.rs (64-byte chunks)
- [ ] T021 Add runtime CPU feature detection in src/myson_core/src/simd/mod.rs (prefer AVX-512, fallback AVX2)
- [ ] T022 Implement unaligned load handling for chunk boundaries in src/myson_core/src/simd/scanner_avx2.rs

### SIMD Scanner Tests

- [X] T023 [P] Add unit test for AVX2 scanner with structural characters in tests/rust/test_simd_scanner.rs (scaffolding)
- [X] T024 [P] Add unit test for AVX-512 scanner correctness parity in tests/rust/test_simd_scanner.rs (scaffolding)
- [X] T025 [P] Add test for cross-lane boundary handling (31-byte chunks) in tests/rust/test_simd_scanner.rs (scaffolding)
- [X] T026 [P] Add benchmark for SIMD throughput (bytes/cycle) in tests/rust/benches/simd_bench.rs. Verify AVX2 ≥32 bytes/cycle and AVX-512 ≥64 bytes/cycle on structural character scanning (scaffolding)
- [X] T026.1 [P] Benchmark standalone SIMD scanner on uniform structural character density; verify ≥1.2 GB/s AVX2 and ≥1.6 GB/s AVX-512 in tests/rust/benches/simd_bench.rs (scaffolding)

### String Interner Foundation

- [X] T027 [P] Implement StringInterner HashMap in src/myson_core/src/types/interner.rs
- [X] T028 [P] Add PyString::intern() integration with Py_INCREF in src/myson_core/src/types/interner.rs
- [ ] T029 [P] Add interner unit tests (deduplication, reference counting) in tests/rust/test_interner.rs

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - High-Throughput Data Ingestion (Priority: P1) 🎯 MVP

**Goal**: Achieve ≥1.5 GB/s throughput on canada.json (2.2 MB) and super_long.json (294 MB) with schema-free parsing, never regress below 233.9 MB/s baseline.

**Independent Test**: Run `python benchmarks/benchmark_comparison.py` and verify ≥1.5 GB/s throughput on both payloads.

### Core JSON Parser (Schema-Free Mode)

- [X] T030 [P] [US1] Create src/myson_core/src/parser/mod.rs with public parse API
- [X] T031 [P] [US1] Implement recursive descent skeleton in src/myson_core/src/parser/json.rs
- [X] T032 [US1] Implement parse_object() using structural index in src/myson_core/src/parser/json.rs - supports quoted and unquoted keys
- [X] T033 [US1] Implement parse_array() using structural index in src/myson_core/src/parser/json.rs - full implementation
- [X] T034 [P] [US1] Implement parse_string() with zero-copy via Buffer Protocol in src/myson_core/src/parser/json.rs - zero-copy for non-escaped strings
- [X] T035 [P] [US1] Implement parse_number() with 256-byte lookup table in src/myson_core/src/parser/json.rs - using std::str::parse
- [X] T036 [P] [US1] Implement parse_bool_null() with single-byte fast path in src/myson_core/src/parser/json.rs - full implementation

### Escape Sequence Handling

- [X] T037 [P] [US1] Add escape sequence handling (\r\n\t\b\f\\") in src/myson_core/src/parser/json.rs - full implementation with unescape_string()
- [X] T038 [P] [US1] Add Unicode escape handling (\uXXXX, surrogate pairs) in src/myson_core/src/parser/json.rs - full \uXXXX support
- [X] T039 [P] [US1] Add invalid escape rejection (\x) in src/myson_core/src/parser/json.rs - validates all escapes

### Whitespace & Comments

- [ ] T040 [P] [US1] Implement SIMD whitespace skipping (32-byte batches) in src/myson_core/src/parser/json.rs - using scalar for now
- [X] T041 [P] [US1] Add single-line comment handling (//) in src/myson_core/src/parser/json.rs - full implementation in skip_whitespace
- [X] T042 [P] [US1] Add block comment handling (/* */) in src/myson_core/src/parser/json.rs - full implementation in skip_whitespace

### Unquoted Keys (MYSON Extension)

- [ ] T043 [P] [US1] Add unquoted key parser (ASCII alphanumeric only) in src/myson_core/src/parser/json.rs
- [ ] T044 [P] [US1] Add unquoted key validation (reject punctuation, Unicode) in src/myson_core/src/parser/json.rs
- [ ] T045 [P] [US1] Add test for unquoted key collision with literals (true, false, null) in tests/unit/test_parser_unquoted_errors.py

### PyO3 Integration & API

- [X] T046 [US1] Expose myson.loads(data) in src/myson_core/src/lib.rs via PyO3
- [X] T047 [US1] Implement Python Buffer Protocol integration for bytes input in src/myson_core/src/lib.rs
- [X] T048 [US1] Add str→bytes conversion for string input in src/myson_core/src/lib.rs
- [X] T049 [P] [US1] Add Python exception wrapping (ValueError for ParseError) in src/myson_core/src/lib.rs

### Error Handling (Approximate Positions)

- [X] T050 [P] [US1] Implement ParseError with ±32 byte position tracking in src/myson_core/src/parser/error.rs
- [X] T051 [P] [US1] Add error excerpt extraction (40-char context window) in src/myson_core/src/parser/error.rs - extract_context() function
- [X] T052 [P] [US1] Add caret marker formatting for error display in src/myson_core/src/parser/error.rs - with_context() constructor with caret

### Performance Optimization

- [ ] T053 [P] [US1] Use PyList_SET_ITEM unsafe fast path in src/myson_core/src/parser/json.rs
- [ ] T054 [P] [US1] Use bulk PyDict construction where safe in src/myson_core/src/parser/json.rs
- [ ] T055 [P] [US1] Minimize allocations via Cow<str> for unescaped strings in src/myson_core/src/parser/json.rs

### Compatibility Testing

- [ ] T056 [US1] Run existing test_comprehensive.py suite (400+ fixtures) and fix failures
- [ ] T057 [US1] Validate 315 JSONTestSuite files (all y_ pass, all n_ fail) in tests/integration/test_json_and_table_basic.py
- [ ] T058 [US1] Validate jsonchecker suite (≥26/33 fail files rejected, 3/3 pass files accepted) in tests/integration/test_json_and_table_basic.py
- [ ] T059 [US1] Verify roundtrip tests (parse(dumps(x)) == x) in existing test suite

### Performance Gate

- [ ] T060 [US1] Run benchmarks/benchmark_comparison.py on canada.json (2.2 MB) - verify ≥1.5 GB/s
- [ ] T061 [US1] Run benchmarks/benchmark_comparison.py on super_long.json (294 MB) - verify ≥1.5 GB/s
- [ ] T062 [US1] Validate performance floor ≥233.9 MB/s on all existing benchmark payloads
- [ ] T062.1 [P] [US1] Profile canada.json parse with memory allocator instrumentation (e.g., mimalloc stats) and verify zero temporary heap allocations beyond PyDict/PyList output objects
- [ ] T062.5 [P] [US1] Validate small-file (<1 KB) overhead to ensure no SIMD setup regression; verify throughput ≥233.9 MB/s with <10% overhead vs baseline on tiny payloads
- [ ] T063 [US1] Add CI gate in .github/workflows/ to fail builds <233.9 MB/s

**Checkpoint**: User Story 1 complete - baseline ≥1.5 GB/s achieved, 100% test compatibility verified

---

## Phase 4: User Story 2 - Schema-Guided Fast Path (Priority: P2)

**Goal**: Achieve >1 GB/s throughput on Zen Grid tables and JSON arrays by skipping key hashing with dataclass/msgspec.Struct schemas.

**Independent Test**: Create dataclass User(id: int, name: str), parse Zen Grid `[: id,name; 1,Alice ]` with `myson.loads(data, schema=User)`, verify >1 GB/s with zero key lookups.

### Schema Compilation

- [ ] T064 [P] [US2] Create src/myson_core/src/parser/schema.rs with schema compiler
- [ ] T065 [P] [US2] Implement dataclass introspection via typing.get_type_hints() in src/myson_core/src/parser/schema.rs
- [ ] T066 [P] [US2] Implement msgspec.Struct introspection in src/myson_core/src/parser/schema.rs
- [ ] T067 [US2] Compile Python schema → Vec<FieldDescriptor> in src/myson_core/src/parser/schema.rs
- [ ] T068 [P] [US2] Map Python types (int, str, bool, float) → FieldType enum in src/myson_core/src/parser/schema.rs
- [ ] T069 [P] [US2] Handle Optional[T] → nullable=true mapping in src/myson_core/src/parser/schema.rs

### Schema-Guided JSON Array Parsing

- [ ] T070 [P] [US2] Implement first-object key→position mapping in src/myson_core/src/parser/schema.rs
- [ ] T071 [US2] Implement positional field parsing for subsequent objects in src/myson_core/src/parser/schema.rs
- [ ] T072 [P] [US2] Add type-specific fast paths (parse_int_simd, parse_bool_byte) in src/myson_core/src/parser/schema.rs
- [ ] T073 [P] [US2] Add schema validation errors (TypeError for type mismatches) in src/myson_core/src/parser/error.rs

### Zen Grid Table Parser

- [ ] T074 [P] [US2] Create src/myson_core/src/parser/table.rs with Zen Grid parser
- [ ] T075 [US2] Implement [: opener detection in src/myson_core/src/parser/table.rs
- [ ] T076 [US2] SIMD-scan for semicolons to count rows in src/myson_core/src/parser/table.rs
- [ ] T077 [US2] Pre-allocate Vec<PyDict> with exact row count (capped at 1M rows) in src/myson_core/src/parser/table.rs
- [ ] T078 [US2] Implement incremental allocation fallback for >1M rows in src/myson_core/src/parser/table.rs
- [ ] T079 [US2] Add hard abort at 10M rows or 1 GB input in src/myson_core/src/parser/table.rs
- [ ] T079.1 [US2] Implement Semicolon-Bomb guard in ZenGridParser: if SIMD row-count exceeds 1,000,000, immediately switch allocation strategy to incremental Vec::new() and log performance warning in src/myson_core/src/parser/table.rs

### Zen Grid Header Parsing

- [ ] T080 [US2] Parse header row (comma-separated field names) in src/myson_core/src/parser/table.rs
- [ ] T081 [US2] Intern header strings with StringInterner in src/myson_core/src/parser/table.rs
- [ ] T082 [P] [US2] Store header as ZenGridHeader with arity count in src/myson_core/src/parser/table.rs

### Zen Grid Row Parsing

- [ ] T083 [US2] Parse row values (comma-separated) in src/myson_core/src/parser/table.rs
- [ ] T084 [US2] Reuse interned header strings via Py_INCREF for 10K+ rows in src/myson_core/src/parser/table.rs
- [ ] T085 [US2] Handle arity mismatch: truncate extra values in src/myson_core/src/parser/table.rs
- [ ] T086 [US2] Handle arity mismatch: null-fill missing values in src/myson_core/src/parser/table.rs

### Zen Grid Nested Structures

- [ ] T087 [P] [US2] Delegate nested {...} in Zen Grid cells to JSON parser in src/myson_core/src/parser/table.rs
- [ ] T088 [P] [US2] Delegate nested [...] in Zen Grid cells to JSON parser in src/myson_core/src/parser/table.rs
- [ ] T089 [P] [US2] Handle delimiter collision (quoted strings with ; or ,) in src/myson_core/src/parser/table.rs

### Zen Grid Edge Cases

- [ ] T090 [P] [US2] Handle empty Zen Grid ([: ]) → return [] in src/myson_core/src/parser/table.rs
- [ ] T091 [P] [US2] Handle header-only table ([: h1,h2; ]) → return [] in src/myson_core/src/parser/table.rs
- [ ] T092 [P] [US2] Handle trailing delimiters ([: a,b,; 1,2, ]) per current behavior in src/myson_core/src/parser/table.rs

### Schema Parameter API

- [ ] T093 [US2] Add schema parameter to myson.loads() in src/myson_core/src/lib.rs
- [ ] T094 [US2] Add schema compilation on parse call in src/myson_core/src/lib.rs
- [ ] T095 [US2] Cache Arc<Vec<FieldDescriptor>> in ParseContext in src/myson_core/src/lib.rs
- [ ] T096 [P] [US2] Add schema validation (must be dataclass or msgspec.Struct) in src/myson_core/src/lib.rs

### Schema-Guided Tests

- [ ] T097 [P] [US2] Add schema compilation tests (dataclass → FieldDescriptor) in tests/rust/test_schema_compiler.rs
- [ ] T098 [P] [US2] Add Zen Grid positional parsing test (10K rows) in tests/integration/test_table_nesting_mix.py
- [ ] T099 [P] [US2] Add JSON array schema test (key→position mapping) in tests/integration/test_json_and_table_basic.py
- [ ] T100 [P] [US2] Add schema type mismatch test (int vs str) in tests/unit/test_parser_json_parity.py

### Performance Validation

- [ ] T101 [US2] Create Zen Grid benchmark (10K rows, 5 columns) and verify >1 GB/s with schema
- [ ] T102 [US2] Verify string interning reduces allocations for 10K+ row tables
- [ ] T103 [US2] Measure pre-allocation vs incremental allocation speedup

**Checkpoint**: User Story 2 complete - schema-guided parsing delivers >1 GB/s on tables

---

## Phase 5: User Story 3 - Backward Compatibility (Priority: P1)

**Goal**: Pass 100% of existing 400+ test fixtures without modification, maintaining API compatibility.

**Independent Test**: Run `pytest tests/test_comprehensive.py -q` and verify 0 failures.

### Test Suite Integration

- [ ] T104 [US3] Run tests/test_comprehensive.py and document all failures
- [ ] T105 [US3] Fix JSONTestSuite parsing failures in src/myson_core/src/parser/json.rs
- [ ] T106 [US3] Fix jsonchecker validation failures in src/myson_core/src/parser/json.rs
- [ ] T107 [US3] Fix roundtrip test failures in src/myson_core/src/parser/json.rs
- [ ] T108 [US3] Fix transform test failures in src/myson_core/src/parser/json.rs

### Edge Case Fixes

- [ ] T109 [P] [US3] Fix deeply nested structure handling (1000 levels) in src/myson_core/src/parser/json.rs
- [ ] T110 [P] [US3] Fix large number handling (9223372036854775807) in src/myson_core/src/parser/json.rs
- [ ] T111 [P] [US3] Fix scientific notation (1e10, -0) in src/myson_core/src/parser/json.rs
- [ ] T112 [P] [US3] Fix Unicode surrogate pairs (\uD834\uDD1E) in src/myson_core/src/parser/json.rs

### API Compatibility

- [ ] T113 [P] [US3] Verify myson.loads(data) signature unchanged in src/myson_core/src/lib.rs
- [ ] T114 [P] [US3] Verify exception types match (ValueError for syntax errors) in src/myson_core/src/lib.rs
- [ ] T115 [P] [US3] Verify return types match existing implementation in src/myson_core/src/lib.rs

### Build System Migration

- [ ] T116 [US3] Update pyproject.toml to use maturin instead of setuptools
- [ ] T117 [US3] Remove setup.py (replaced by maturin)
- [ ] T118 [US3] Remove myson_core.pyx and myson_fast.pyx (Cython files)
- [ ] T119 [US3] Update README.md with maturin build instructions
- [ ] T120 [P] [US3] Verify wheel packaging on Linux/macOS/Windows in CI

### Token Efficiency Validation

- [ ] T121 [P] [US3] Run benchmarks/token_savings_analysis.py and verify 48.8% reduction vs JSON pretty
- [ ] T122 [P] [US3] Verify 19.6% reduction vs JSON compact in benchmarks/token_savings_analysis.py
- [ ] T123 [P] [US3] Confirm wire format unchanged (identical output to current implementation)

**Checkpoint**: User Story 3 complete - 100% test compatibility, API unchanged, build system migrated

---

## Phase 6: User Story 4 - Zen Grid Optimization (Priority: P2)

**Goal**: Optimize Zen Grid tables with 10,000+ rows by pre-allocating memory and reusing header strings.

**Independent Test**: Create 10K-row Zen Grid, verify (a) pre-allocation happens, (b) headers allocated once, (c) >500 MB/s throughput.

### Memory Pre-allocation

- [ ] T124 [P] [US4] Verify SIMD semicolon counting accuracy in tests/rust/test_simd_scanner.rs
- [ ] T125 [P] [US4] Verify Vec<PyDict> pre-allocation with exact capacity in tests/integration/test_table_nesting_mix.py
- [ ] T126 [P] [US4] Test 1M row pre-allocation cap enforcement in tests/integration/test_table_nesting_mix.py
- [ ] T127 [P] [US4] Test incremental allocation fallback for >1M rows in tests/integration/test_table_nesting_mix.py

### String Interning Validation

- [ ] T128 [P] [US4] Instrument Py_INCREF calls for header reuse in src/myson_core/src/types/interner.rs
- [ ] T129 [P] [US4] Verify 3 header strings allocated for 10K rows (not 30K) in tests/rust/test_interner.rs
- [ ] T130 [P] [US4] Measure memory reduction from interning in benchmarks

### Nested Structure Handling

- [ ] T131 [P] [US4] Test Zen Grid with nested JSON objects ([: data; {"x":1} ]) in tests/integration/test_table_nesting_mix.py
- [ ] T132 [P] [US4] Test Zen Grid with nested arrays ([: items; [1,2,3] ]) in tests/integration/test_table_nesting_mix.py
- [ ] T133 [P] [US4] Verify delimiter context tracking (ignore ; inside {...}) in tests/integration/test_table_nesting_mix.py

**Checkpoint**: User Story 4 complete - Zen Grid tables optimized with pre-allocation and interning

---

## Phase 7: User Story 5 - Parallel Parsing (Priority: P3)

**Goal**: Achieve >10 GB/s throughput on 16-core AVX-512 CPUs with parallel=True parameter.

**Independent Test**: Parse 500 MB Zen Grid with `myson.loads(data, schema=User, parallel=True)` on 16 cores, verify >10 GB/s.

### Rayon Integration

- [ ] T134 [P] [US5] Add rayon dependency to Cargo.toml
- [ ] T135 [P] [US5] Create src/myson_core/src/parallel/mod.rs with parallel parser
- [ ] T136 [US5] Implement row boundary splitting in src/myson_core/src/parallel/rayon_chunker.rs
- [ ] T137 [US5] Implement Rayon parallel iterator over chunks in src/myson_core/src/parallel/rayon_chunker.rs

### Thread-Safe Schema Sharing

- [ ] T138 [P] [US5] Wrap Vec<FieldDescriptor> in Arc for thread-safe sharing in src/myson_core/src/parser/schema.rs
- [ ] T139 [P] [US5] Clone Arc<Schema> for each worker thread in src/myson_core/src/parallel/rayon_chunker.rs

### Parallel API

- [ ] T140 [US5] Add parallel parameter to myson.loads() in src/myson_core/src/lib.rs
- [ ] T141 [US5] Validate parallel=True requires schema in src/myson_core/src/lib.rs
- [ ] T142 [P] [US5] Add ConfigurationError for parallel without schema in src/myson_core/src/parser/error.rs
- [ ] T143 [P] [US5] Implement graceful degradation for single-core machines in src/myson_core/src/parallel/rayon_chunker.rs

### Parallel Testing

- [ ] T144 [P] [US5] Add parallel parsing test (2 cores) in tests/integration/test_edge_behaviors.py
- [ ] T145 [P] [US5] Add parallel parsing test (8 cores) in tests/integration/test_edge_behaviors.py
- [ ] T146 [P] [US5] Add parallel parsing test (16 cores) in tests/integration/test_edge_behaviors.py
- [ ] T147 [P] [US5] Verify near-linear scaling (≥14x speedup on 16 cores) in benchmarks

### Thread Safety Validation

- [ ] T148 [P] [US5] Run ThreadSanitizer on parallel parsing tests
- [ ] T149 [P] [US5] Verify no data races in Rayon worker threads
- [ ] T150 [P] [US5] Test error aggregation from multiple worker threads

### Performance Validation

- [ ] T151 [US5] Create 500 MB Zen Grid benchmark payload
- [ ] T152 [US5] Verify >10 GB/s throughput on 16-core AVX-512 hardware
- [ ] T153 [US5] Measure overhead for small payloads (<10 MB) with parallel=True

**Checkpoint**: User Story 5 complete - parallel parsing achieves >10 GB/s on multi-core systems

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements affecting multiple user stories

### Documentation

- [ ] T154 [P] Update README.md with Rust migration details, AVX2 requirements
- [ ] T155 [P] Add examples/ directory with schema usage examples
- [ ] T156 [P] Update docs/ with performance benchmarks and comparisons
- [ ] T157 [P] Document ±32 byte error position trade-off in API docs

### Error Message Improvements

- [ ] T158 [P] Improve ParseError messages with helpful hints in src/myson_core/src/parser/error.rs
- [ ] T159 [P] Add "Did you mean?" suggestions for common mistakes in src/myson_core/src/parser/error.rs

### Performance Tuning

- [ ] T160 [P] Profile with perf/VTune and optimize hotspots
- [ ] T161 [P] Tune SIMD chunk sizes for cache efficiency
- [ ] T162 [P] Optimize PyObject allocation patterns

### Security Hardening

- [ ] T163 [P] Add input size validation (reject >1 GB without explicit config) in src/myson_core/src/lib.rs
- [ ] T164 [P] Add fuzzing with cargo-fuzz for malformed inputs
- [ ] T165 [P] Review unsafe code blocks for memory safety

### CI/CD

- [ ] T166 [P] Add GitHub Actions workflow for Linux/macOS/Windows builds
- [ ] T167 [P] Add performance regression tests (fail if <233.9 MB/s) to CI
- [ ] T168 [P] Add nightly cargo-fuzz runs to CI

### Quickstart Validation

- [ ] T169 Run quickstart.md build instructions and fix any issues
- [ ] T170 Verify all quickstart.md examples work on AVX2 hardware
- [ ] T171 Test quickstart.md on AVX-512 hardware for fast path validation

### Efficiency Score Validation

- [ ] T172 [P] Calculate and verify final Efficiency Score (Throughput × 1.60 token reduction factor) ≥2400 in benchmarks/combined_benchmark_report.py

---

## Dependencies & Execution Order

### Phase Dependencies

1. **Setup (Phase 1)**: No dependencies - start immediately
2. **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
3. **User Story 1 (Phase 3)**: Depends on Foundational - can start after Phase 2 complete
4. **User Story 2 (Phase 4)**: Depends on Foundational - independent of US1, can run in parallel
5. **User Story 3 (Phase 5)**: Depends on US1 (tests validate US1 implementation)
6. **User Story 4 (Phase 6)**: Depends on US2 (Zen Grid optimization builds on table parser)
7. **User Story 5 (Phase 7)**: Depends on US2 (parallel requires schema-guided parsing)
8. **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Completion Order

**Recommended MVP sequence** (for single developer or small team):

1. **Phase 1** → **Phase 2** (Setup + Foundation) - 1-2 weeks
2. **Phase 3** (User Story 1: High-Throughput) - 1 week
3. **Phase 5** (User Story 3: Compatibility) - validate US1 works - 3 days
4. **Phase 4** (User Story 2: Schema) - 1 week
5. **Phase 6** (User Story 4: Zen Grid Optimization) - 3 days
6. **Phase 7** (User Story 5: Parallel) - optional Phase 2 feature - 1 week
7. **Phase 8** (Polish) - 3 days

**Total Timeline**: 3-4 weeks for Phase 1-6 (MVP), additional 1-2 weeks for Phase 7-8 (parallel + polish)

### Parallel Opportunities Within Phases

**Phase 2 (Foundational)** - can parallelize:
- T011-T016 (Core types) + T017-T022 (SIMD scanner) + T027-T029 (String interner)

**Phase 3 (User Story 1)** - can parallelize:
- T034-T036 (parse primitives) + T037-T039 (escapes) + T040-T042 (comments/whitespace) + T043-T045 (unquoted keys)

**Phase 4 (User Story 2)** - can parallelize:
- T064-T069 (schema compilation) + T074-T092 (Zen Grid parser)

**Phase 8 (Polish)** - all tasks marked [P] can run in parallel

### Critical Path (Longest Dependency Chain)

Setup → Foundational → US1 Core Parser → US1 Tests → US2 Schema → US4 Zen Grid → US5 Parallel

**Estimated duration**: 20-25 days (assuming sequential execution)

---

## Implementation Strategy

### MVP Scope (Minimum Viable Product)

**Target**: User Stories 1 + 3 (High-Throughput + Compatibility)

- ✅ Baseline ≥1.5 GB/s throughput without schema
- ✅ 100% test compatibility (400+ fixtures pass)
- ✅ AVX2 SIMD scanning operational
- ✅ Build system migrated to maturin
- ❌ Schema-guided parsing (Phase 4, User Story 2)
- ❌ Parallel mode (Phase 7, User Story 5)

**Delivery Timeline**: 2-3 weeks

### Incremental Delivery Milestones

**Milestone 1**: Foundation + US1 (Weeks 1-2)
- SIMD scanner working
- JSON parser achieving ≥1.5 GB/s
- Basic tests passing

**Milestone 2**: US3 Compatibility (Week 2-3)
- All 400+ tests pass
- API compatibility verified
- Build system migrated

**Milestone 3**: US2 Schema (Week 3-4)
- Schema compilation working
- Zen Grid parser operational
- >1 GB/s with schema

**Milestone 4**: US4+US5 Advanced (Week 4-5, optional)
- Pre-allocation optimization
- Parallel mode (if needed)

### Performance Gates at Each Milestone

- **After Milestone 1**: Verify ≥1.5 GB/s on canada.json
- **After Milestone 2**: Verify ≥233.9 MB/s floor on all benchmarks
- **After Milestone 3**: Verify >1 GB/s on 10K-row Zen Grid
- **After Milestone 4**: Verify >10 GB/s parallel (if implemented)

### Risk Mitigation

- **SIMD complexity**: Extensive unit tests (T023-T026), fuzzing (T164)
- **Performance regression**: CI gate fails <233.9 MB/s (T063, T167)
- **Test compatibility**: Run full suite after every milestone (T056-T059, T104-T108)
- **Build system**: Test wheels on 3 platforms (T120)

---

**Total Tasks**: 171  
**Parallelizable Tasks**: 87 (marked with [P])  
**Critical Path Tasks**: 84 (sequential dependencies)

**Suggested MVP**: Phases 1-3, 5 (Setup + Foundation + US1 + US3) = 69 tasks = 2-3 weeks  
**Full Feature**: All phases = 171 tasks = 4-5 weeks