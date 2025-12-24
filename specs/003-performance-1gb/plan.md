# Implementation Plan: MYSON Parser Performance Optimization to 700+ MB/s

**Branch**: `003-performance-1gb` | **Date**: 2025-12-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-performance-1gb/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Optimize MYSON parser from current 136 MB/s to 700+ MB/s through three phased optimizations: (1) Pre-allocation using PyList_New + PyList_SET_ITEM to eliminate append overhead (2x-3x speedup), (2) Raw pointer arithmetic with const unsigned char* to eliminate bounds checks (1.5x-2x additional speedup), and (3) Lookup tables and batch whitespace processing for character classification (1.3x-1.5x additional speedup). Inspired by msgspec and orjson architectures, maintaining 100% compatibility with existing MYSON/JSON semantics.

## Technical Context

**Language/Version**: Python 3.10+ with Cython 3.0+ for C-extension compilation  
**Primary Dependencies**: 
- Cython 3.0+ (C-extension builder)
- Python C-API (PyList_*, PyDict_*, PyUnicode_* functions)
- libc (malloc, free, strtod, strtoll, memcpy, memchr)
- GCC/Clang compiler with -O3, -march=native, -ffast-math support

**Storage**: N/A (in-memory parsing only)  
**Testing**: 
- pytest for test orchestration (28 existing unit + integration tests)
- Benchmark scripts using time.perf_counter() for throughput measurement
- super_long.json (294 MB) as primary performance validation file

**Target Platform**: Linux/macOS x86-64 with CPython 3.10+ runtime  
**Project Type**: Single project (Cython extension module)  
**Performance Goals**: 
- Phase 1: 136 → 300 MB/s (2.2x speedup)
- Phase 2: 300 → 500 MB/s (1.67x additional)
- Phase 3: 500 → 700 MB/s (1.4x additional)
- Ultimate: 700+ MB/s sustained throughput

**Constraints**: 
- 100% backward compatibility (all 28 existing tests must pass)
- Memory increase ≤10% from current baseline
- Correctness over speed (any optimization breaking compatibility is rejected)
- Single-threaded performance (multi-threading deferred to future work)

**Scale/Scope**: 
- Target file sizes: 1 MB to 500 MB (in-memory parsing sweet spot)
- Array sizes: Up to 100,000+ elements requiring pre-allocation
- Nesting depth: Maintain 1024-level recursion guard
- Test coverage: Maintain 100% pass rate on existing test suite

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **JSON superset fidelity**: Performance optimizations are internal implementation changes only. Parser continues to accept all valid JSON with identical semantics and data types. No changes to grammar or parsing logic - only to internal data structure allocation and memory access patterns.

✅ **Unquoted keys**: No changes to tokenizer key validation logic. Existing ASCII alphanumeric enforcement remains unchanged. Optimizations apply to all key types equally.

✅ **Zen Grid tables**: Table parsing logic unchanged. Pre-allocation applies to table row lists. Header arity enforcement, nesting protection, and empty table handling remain identical.

✅ **Comments**: Comment stripping logic unchanged. Line/column tracking remains accurate. Pointer arithmetic in whitespace skipping does not affect comment handling semantics.

✅ **Deterministic parser discipline**: 
- Tokenizer state machine remains unchanged
- Recursive descent structure preserved
- Pointer arithmetic replaces indexed access but maintains same parsing logic
- grammar.ebnf unchanged (no new syntax)
- Error reporting with line/column maintained via position calculation when needed

✅ **Tests**: All 28 existing tests must pass (100% requirement in SC-004). No new grammar features means no new test requirements. Performance benchmarks added but do not replace existing correctness tests.

**Gate Status**: ✅ **PASS** - No constitution violations. All optimizations are internal implementation changes that preserve external semantics.

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
# Single project structure (Cython extension)
src/
├── myson_core.pyx          # Main Cython parser (to be optimized)
├── __init__.py             # Python API wrapper
├── cli/
│   ├── __init__.py
│   └── parse.py
└── __pycache__/

tests/
├── conftest.py             # Shared fixtures
├── integration/
│   ├── test_edge_behaviors.py
│   ├── test_json_and_table_basic.py
│   └── test_table_nesting_mix.py
└── unit/
    ├── test_parser_*.py    # 28 existing parser tests
    └── test_tokenizer.py

benchmarks/
├── super_long.json         # 294 MB validation file
├── benchmark_throughput.py # Performance measurement script
└── performance_test.py     # Baseline benchmarks

setup.py                    # Cython build configuration
pyproject.toml              # Package metadata
specs/003-performance-1gb/  # This feature documentation
```

**Structure Decision**: Single project using existing Cython extension architecture. All optimizations apply to `src/myson_core.pyx`. No new files needed - only internal refactoring of existing parser implementation. Benchmarks already exist in `benchmarks/` directory.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**No violations detected** - All constitution principles satisfied. Performance optimizations are internal implementation changes that preserve external semantics.
