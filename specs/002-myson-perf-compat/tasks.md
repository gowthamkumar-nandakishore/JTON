# Implementation Tasks: Performance and Compatibility Update

**Feature Branch**: `002-myson-perf-compat`
**Spec**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)

## Phase 1: Setup
*Goal: Initialize the build environment for Cython extensions.*

- [x] T001 Configure `setup.py` to build `myson_core` Cython extension
- [x] T002 Create `src/myson_core.pyx` skeleton with basic `cdef` definitions
- [x] T003 Create `src/__init__.py` skeleton with `json` module API stubs

## Phase 2: Foundational (The Core)
*Goal: Implement the high-performance Cython tokenizer and parser (T040) with strict safety constraints.*

- [x] T004 Implement Cython Tokenizer state machine in `src/myson_core.pyx` enforcing UTF-8 only and Unquoted Keys support
- [x] T005 Implement Cython Parser (recursive descent) in `src/myson_core.pyx` with fixed recursion limit (1024)
- [x] T006 Implement parsing for basic JSON types in `src/myson_core.pyx` handling arbitrary precision integers
- [x] T007 Implement parsing for container types (list, dict) in `src/myson_core.pyx`
- [x] T008 Implement Zen Grid table parsing logic in `src/myson_core.pyx` (resilient: null-fill/drop-extra)
- [x] T009 Implement comment stripping/handling in `src/myson_core.pyx`

## Phase 3: User Story 1 - Drop-in JSON Replacement
*Goal: Provide a fully compatible API that mimics the standard `json` module (T041, T042).*

- [x] T010 [US1] Implement `loads` in `src/__init__.py` supporting all args (`cls`, `object_hook`, etc.)
- [x] T011 [US1] Implement `load` in `src/__init__.py` handling file objects
- [x] T012 [US1] Implement `dumps` in `src/__init__.py` supporting all args (`default`, `sort_keys`, etc.)
- [x] T013 [US1] Implement `dump` in `src/__init__.py` handling file objects
- [x] T014 [US1] Implement `dumps(zen=True)` auto-formatting logic in `src/myson_core.pyx` (T042)
- [x] T015 [US1] Create compatibility test suite running standard `json` tests against `myson`

## Phase 4: User Story 2 - High Performance Parsing
*Goal: Optimize for speed and verify performance with benchmarks (T043).*

- [x] T016 [US2] Optimize `myson_core.pyx` using typed C-variables and `nogil` blocks
- [x] T017 [US2] Create `benchmarks/` directory structure
- [x] T018 [US2] Port `benchmark.py` logic from msgspec to `benchmarks/benchmark_throughput.py` (T043)
- [x] T019 [US2] Implement token reduction benchmark in `benchmarks/benchmark_tokens.py`
- [x] T020 [US2] Run benchmarks to verify >1GB/s throughput target

## Phase 5: User Story 3 - Schema-based Validation
*Goal: Implement `MysonModel` for type-safe, zero-copy validation.*

- [x] T021 [US3] Define `MysonModel` cdef class in `src/myson_core.pyx` supporting extended types (`datetime`, `uuid`)
- [x] T022 [US3] Implement `MysonModel.from_json` with zero-copy string/bytes handling and extra field ignoring
- [x] T023 [US3] Implement `MysonModel.to_json` serialization
- [x] T024 [US3] Create tests for `MysonModel` validation, type coercion, and nesting

## Phase 6: User Story 4 - License Compliance
*Goal: Ensure legal compliance for reused code.*

- [x] T025 [US4] Create `NOTICE` file in repository root
- [x] T026 [US4] Add attributions for msgspec, orjson, and toon in `NOTICE` file

## Dependencies

- **Phase 1** blocks all other phases.
- **Phase 2** blocks Phase 3, 4, and 5.
- **Phase 3** (API) is required for Phase 4 (Benchmarks) to run easily.
- **Phase 5** (Models) depends on Phase 2 (Core).

## Implementation Strategy

1.  **Core First**: We must get the Cython parser working correctly before wrapping it.
2.  **API Layer**: Once the core parses strings, we wrap it in `__init__.py` to match `json` signatures.
3.  **Optimization**: We iterate on `myson_core.pyx` to remove Python overhead (GIL, object creation) to hit the 1GB/s target.
4.  **Models**: `MysonModel` is built on top of the optimized core, leveraging the low-level parsing logic.
