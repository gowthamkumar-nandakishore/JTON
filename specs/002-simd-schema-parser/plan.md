# Implementation Plan: SIMD-Accelerated MYSON with Schema-Guided Optimization

**Branch**: `002-simd-schema-parser` | **Date**: 2025-12-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-simd-schema-parser/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Replace Cython extensions (`myson_core.pyx`) with Rust+SIMD implementation targeting ≥1.5 GB/s throughput while maintaining 100% backward compatibility with existing tests. Core approach: (1) AVX2/AVX-512 SIMD scanning for structural characters at 32-64 bytes/cycle, (2) optional schema-guided parsing to bypass key hashing via positional field mapping for both JSON arrays and Zen Grid tables, (3) zero-copy string views via Python Buffer Protocol with mandatory string interning, (4) pre-allocation capped at 1M rows to prevent OOM, (5) Phase 2 Rayon parallelism for >10 GB/s on multi-core systems. Performance gate: never regress below 233.9 MB/s baseline.

## Technical Context

**Language/Version**: Rust 1.70+ (via PyO3/maturin), Python 3.10+ for bindings  
**Primary Dependencies**: PyO3 (Rust-Python interop), maturin (build), std::arch (SIMD intrinsics), rayon (Phase 2 parallelism)  
**Storage**: N/A (in-memory parser only)  
**Testing**: pytest (existing 400+ test suite), cargo test (Rust unit tests), cargo-fuzz (malformed input fuzzing)  
**Target Platform**: Linux/macOS/Windows x86_64 with AVX2 (2013+ CPUs), AVX-512 optional fast path  
**Project Type**: Single library project (Python extension module)  
**Performance Goals**: ≥1.5 GB/s single-threaded, >10 GB/s Phase 2 parallel (16 cores), never <233.9 MB/s  
**Constraints**: Zero-copy where possible, ±32 byte error position tolerance, 1M row pre-allocation cap, AVX2 mandatory (no scalar fallback)  
**Scale/Scope**: 400+ existing test fixtures, benchmarks on 2.2 MB (canada.json) and 294 MB (super_long.json) payloads

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- ✅ **JSON superset fidelity**: Rust parser will pass all 315 JSONTestSuite y_ files (valid JSON), reject n_ files (invalid JSON), maintaining identical semantics to stdlib json.loads. No ambiguity introduced.
- ✅ **Unquoted keys**: Existing tokenizer logic (ASCII alphanumeric-only) will be ported to Rust SIMD scanner. Punctuation/Unicode rejection preserved.
- ✅ **Zen Grid tables**: Rust implementation will handle `[:` opener, `;` row separator, `,` column separator with arity enforcement (null-fill missing, truncate extra per Constitution III). Nesting via delegation to JSON parser preserved. Empty tables yield `[]`.
- ✅ **Comments**: `//` and `/* */` handling will use SIMD whitespace skipping (32 bytes/cycle). Line/column tracking via approximate positions (±32 bytes per Constitution and spec FR-012).
- ✅ **Deterministic parser discipline**: Rust SIMD scanner replaces Cython byte-by-byte loops but maintains explicit state machine (AVX2 vector ops, no regex). Recursive descent parser structure preserved. Grammar synchronization not required (wire format unchanged).
- ✅ **Tests**: Existing 400+ tests (test_comprehensive.py) will validate Rust implementation. Additional cargo-fuzz tests for malformed SIMD edge cases. No new MYSON grammar features added.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Single library project (Python extension via Rust)
src/
├── myson_core/           # Rust crate root
│   ├── lib.rs           # PyO3 module entry point
│   ├── simd/
│   │   ├── mod.rs
│   │   ├── scanner_avx2.rs    # AVX2 SIMD scanner (baseline)
│   │   ├── scanner_avx512.rs  # AVX-512 fast path
│   │   └── intrinsics.rs      # Shared SIMD utilities
│   ├── parser/
│   │   ├── mod.rs
│   │   ├── json.rs            # JSON parser (schema-free)
│   │   ├── table.rs           # Zen Grid parser
│   │   └── schema.rs          # Schema-guided parser
│   ├── types/
│   │   ├── mod.rs
│   │   ├── field_descriptor.rs # Schema field metadata
│   │   └── string_interner.rs  # String caching
│   └── parallel/              # Phase 2
│       ├── mod.rs
│       └── rayon_chunker.rs
├── __init__.py          # Python package
├── parser.py            # Pure Python fallback (deprecated, kept for reference)
└── tokenizer.py         # Pure Python fallback (deprecated, kept for reference)

tests/
├── test_comprehensive.py    # 400+ JSON fixtures (existing)
├── integration/             # Existing integration tests
├── unit/                    # Existing unit tests
└── rust/                    # New: Rust unit tests mirroring Python tests
    ├── test_simd_scanner.rs
    ├── test_schema_compiler.rs
    └── test_interner.rs

benchmarks/
├── benchmark_comparison.py       # Existing: orjson vs MYSON
├── combined_benchmark_report.py  # Existing: comprehensive metrics
└── token_savings_analysis.py     # Existing: BPE token counting

Cargo.toml               # New: Rust crate manifest
pyproject.toml           # Updated: maturin build, remove Cython
setup.py                 # Deleted: replaced by maturin
```

**Structure Decision**: Single library project. The Rust crate (`src/myson_core/`) compiles to a Python extension module (`myson.myson_core`) via maturin. Existing Python files (`parser.py`, `tokenizer.py`) are deprecated but temporarily kept for reference during migration. Build system transitions from setuptools+Cython to maturin+Rust. All existing tests and benchmarks run without modification.

## Complexity Tracking

> **No Constitution violations requiring justification**

This feature strictly adheres to Constitution 1.1.0:
- JSON superset fidelity maintained (no new syntax)
- Nitro Performance Mandate satisfied (Rust+SIMD, ≥1.5 GB/s target)
- Zen Grid resilience update implemented (null-fill, truncate, 1M cap)
- Unquoted key constraints preserved
- Comment/whitespace discipline enforced via SIMD

No additional complexity beyond constitutional requirements.

---

## Phase 0: Research Artifacts

**Objective**: Resolve all NEEDS CLARIFICATION from Technical Context via technical research.

**Status**: ✅ Completed (2025-12-24)

**Output**: [research.md](research.md) (483 lines)

### Research Findings Summary

1. **SIMD Techniques**:
   - AVX2 `_mm256_cmpeq_epi8` for 32-byte structural character scanning
   - AVX-512 `_mm512_cmpeq_epi8` for 64-byte scanning (1.4x speedup)
   - Bitmask extraction via `_mm256_movemask_epi8` for matched positions
   - Performance estimate: 1.21 GB/s (AVX2), 1.69 GB/s (AVX-512)

2. **Zero-Copy Strategy**:
   - Python Buffer Protocol via `PyBytes::as_bytes()` (no allocation)
   - `Cow<'a, str>` for unescaped strings (reference input buffer)
   - `PyString::intern()` for repeated keys (PyUnicode cache)

3. **Schema Optimization**:
   - Dataclass/msgspec.Struct → `Vec<FieldDescriptor>` at parse time
   - Zen Grid: positional field mapping (skip key hashing entirely, 3x speedup)
   - JSON arrays: first object builds key→position map (2x speedup)

4. **Pre-allocation Safety**:
   - Count semicolons in Zen Grid header scan (AVX2 vectorized)
   - Cap at 1M rows, fall back to incremental growth
   - Hard abort at 10M rows or 1 GB input

**Decision Log**: All in [research.md](research.md) with code sketches and performance estimates.

---

## Phase 1: Design Artifacts

**Objective**: Generate data model, API contracts, and developer onboarding guide.

**Status**: ✅ Completed (2025-12-24)

### Generated Files

1. **[data-model.md](data-model.md)** (150+ lines)
   - 6 core Rust types:
     - `FieldDescriptor`: Schema field metadata (name, type, position, optional flag)
     - `InternedString`: `Py<PyString>` wrapper with cached hash for O(1) lookups
     - `StructuralIndex`: SIMD scanner output (delimiter/bracket positions as Vec)
     - `ZenGridHeader`: Parsed table header (field names, arity, row count estimate)
     - `ParseContext`: Stateful parser state (schema, interner, input buffer ref)
     - `StringInterner`: `HashMap<&str, Py<PyString>>` for zero-copy string reuse
   - Validation rules: 1M row cap, type checking, zero-copy safety
   - Lifecycle diagram: schema compilation → SIMD scan → parse → interner cleanup

2. **[contracts/api.md](contracts/api.md)** (100+ lines)
   - `myson.loads(data, *, schema=None, parallel=False)` signature
   - Performance contract: ≥1.5 GB/s (schema-free), >10 GB/s (parallel), never <233.9 MB/s
   - Error contract: `ValueError`/`TypeError` with ±32 byte positions
   - Compatibility: 100% JSON superset, 400+ tests pass, identical token efficiency
   - Memory contract: zero-copy bytes input, interning, 1M row pre-alloc cap
   - Schema contract: dataclass/msgspec.Struct with type annotations

3. **[contracts/schema-compilation.md](contracts/schema-compilation.md)** (120+ lines)
   - Compilation pipeline: Python schema → `typing.get_type_hints()` → `Vec<FieldDescriptor>`
   - Type mapping: `int`→`FieldType::Int`, `str`→`FieldType::String`, `Optional[T]`→`optional=true`
   - Parsing modes:
     - Zen Grid positional: column index → schema position (3x speedup)
     - JSON array key mapping: first object builds key→position map (2x speedup)
   - Error handling: type mismatches, missing required fields, extra columns (truncate)
   - Caching: `Arc<Vec<FieldDescriptor>>` for thread-safe sharing (Phase 2)

4. **[contracts/error-handling.md](contracts/error-handling.md)** (110+ lines)
   - 4 error types:
     - `ParseError(ValueError)`: syntax errors with ±32 byte positions
     - `SchemaError(TypeError)`: type validation failures
     - `MemorySafetyError(MemoryError)`: 1 GB/10M row limit violations
     - `ConfigurationError(TypeError)`: invalid parameter combos (e.g., `parallel=True` without schema)
   - Position tracking: approximate via nearest SIMD structural character
   - Error recovery: none (fast failure on first error)
   - Testing: 50+ dedicated error tests, approximate position tolerance validation

5. **[quickstart.md](quickstart.md)** (200+ lines)
   - Prerequisites: Rust 1.70+, Python 3.10+, AVX2 CPU, maturin
   - Build instructions: `maturin develop` (debug), `maturin develop --release` (optimized)
   - Testing: `pytest tests/` (400+ Python tests), `cargo test` (50+ Rust unit tests)
   - Benchmarking: `python benchmarks/benchmark_comparison.py` (validates ≥1.5 GB/s)
   - Performance gate: exit code 1 if throughput <233.9 MB/s
   - Debugging: SIMD feature detection, `RUST_BACKTRACE=full`, perf profiling
   - Common issues: missing maturin, pre-2013 CPU, 1 GB limit

### Design Decisions

- **API Surface**: Single function (`myson.loads`) with optional `schema` and `parallel` (Phase 2)
- **Schema Format**: Dataclass/msgspec.Struct (familiar to Python users, introspectable via `typing`)
- **Error Philosophy**: Fast failure with helpful messages (no partial results)
- **Build System**: maturin (industry standard for PyO3, simpler than setuptools+Cython)

**Validation**: All contracts reference data-model.md types and research.md findings.

---

## Phase 2: Implementation Tasks

**Objective**: Generate granular task list for `/speckit.tasks` command.

**Status**: ⏳ Pending (not generated by `/speckit.plan`)

**Next Command**: `/speckit.tasks` to break down implementation into atomic tasks with test fixtures and acceptance criteria.

---

## Plan Completion Summary

**Artifacts Generated**:
- ✅ `research.md`: 483 lines, SIMD techniques + performance estimates
- ✅ `data-model.md`: 6 core Rust types with validation rules
- ✅ `contracts/api.md`: Public API contract with performance guarantees
- ✅ `contracts/schema-compilation.md`: Schema → FieldDescriptor compilation pipeline
- ✅ `contracts/error-handling.md`: Error types, position tracking, messages
- ✅ `quickstart.md`: Developer onboarding with build/test/benchmark instructions

**Constitution Re-Check**: ✅ No violations introduced during design phase. All decisions align with Constitution 1.1.0 mandates.

**Branch**: `002-simd-schema-parser` (ready for implementation tasks)

**Next Steps**:
1. Run `/speckit.tasks` to generate `tasks.md` with atomic implementation checklist
2. Begin Phase 0 implementation (SIMD structural scanner in `src/myson_core/src/simd/scanner_avx2.rs`)
3. Validate each task against test fixtures and performance benchmarks
4. Iterate through Phases 0-2 maintaining ≥233.9 MB/s performance floor

**Estimated Timeline** (from research.md):
- Phase 0 (SIMD foundation): 1-2 weeks
- Phase 1 (schema-guided parsing): 1 week
- Phase 2 (parallelism): 1 week
- Total: 3-4 weeks for full implementation

---

**Command**: This plan was generated by `/speckit.plan`. Implementation tasks will be generated by `/speckit.tasks`.
