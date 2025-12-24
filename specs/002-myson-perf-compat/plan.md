# Implementation Plan: Performance and Compatibility Update

**Branch**: `002-myson-perf-compat` | **Date**: December 24, 2025 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-myson-perf-compat/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement a high-performance Cython/C core for MYSON to achieve >1GB/s parsing speed while providing a drop-in replacement for the standard `json` module. Introduce `MysonModel` for schema-based validation and zero-copy hydration, and ensure license compliance with a NOTICE file.

## Technical Context

**Language/Version**: Python 3.10+, Cython 3.0+
**Primary Dependencies**: setuptools, Cython, C Compiler (GCC/Clang)
**Storage**: N/A
**Testing**: pytest, benchmarks (custom scripts)
**Target Platform**: Linux, macOS, Windows
**Project Type**: Python Library (C Extension)
**Performance Goals**: Parsing >1GB/s, within 10% of msgspec/orjson
**Constraints**: Drop-in replacement for `json` module (identical signatures), UTF-8 only, fixed recursion limit.
**Scale/Scope**: Core library replacement

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- JSON superset fidelity: The Cython implementation MUST pass all existing JSON compatibility tests and support standard `json` module behavior (including arbitrary precision integers).
- Unquoted keys: The Cython tokenizer MUST implement the state machine to support unquoted ASCII alphanumeric keys.
- Zen Grid tables: The Cython parser MUST support Zen Grid table arrays with header arity checks and nesting (resilient behavior: null fill/drop extra).
- Comments: The Cython tokenizer MUST handle `//` and `/* */` comments correctly.
- Deterministic parser discipline: The Cython implementation will use a state-machine based tokenizer and recursive descent parser with a fixed recursion limit (1024) to ensure correctness and safety.
- Tests: New benchmark tests and compatibility tests will be added. Existing tests will be run against the new implementation.

## Project Structure

### Documentation (this feature)

```text
specs/002-myson-perf-compat/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── myson_core.pyx       # Cython implementation of tokenizer and parser
├── __init__.py          # API Shadow (proxy for standard json module)
└── ...                  # Existing Python files (kept for reference/fallback or removed if fully replaced)

benchmarks/
├── benchmark_throughput.py # Throughput benchmark (jcrist/msgspec style)
└── benchmark_tokens.py     # Token reduction benchmark (toon-format/toon style)
```
