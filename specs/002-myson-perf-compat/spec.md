# Feature Specification: Performance and Compatibility Update

**Feature Branch**: `002-myson-perf-compat`  
**Created**: December 24, 2025  
**Status**: Draft  
**Input**: User description: "Requirement Update: Add FR-015: The library MUST be a drop-in replacement for the standard json module, supporting loads(), load(), dumps(), and dump() with identical signatures. Performance Update: Add FR-016: The core tokenizer and parser MUST be implemented in Cython or C to match the performance profiles of msgspec and orjson (parsing >1GB/s). Interoperability: Add FR-017: Support a MysonModel (inspired by Pydantic/msgspec.Struct) for schema-based validation and zero-copy hydration. License: Explicitly state that any logic reused from msgspec (MIT), orjson (Apache 2.0), or toon (MIT) must be attributed in a NOTICE file."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Drop-in JSON Replacement (Priority: P1)

As a Python developer, I want to replace `import json` with `import myson` in my existing projects so that I can gain performance benefits without rewriting my code.

**Why this priority**: This is the primary adoption driver. If it breaks existing code, users won't switch.

**Independent Test**: Can be fully tested by running the standard Python `json` module's test suite against the `myson` library.

**Acceptance Scenarios**:

1. **Given** a Python script using `json.loads()` and `json.dumps()`, **When** `json` is replaced with `myson`, **Then** the script runs without errors and produces identical output.
2. **Given** a call to `myson.load()` with a file object, **When** executed, **Then** it returns the parsed Python object matching `json.load()` behavior.
3. **Given** a call to `myson.dump()` with an object and file stream, **When** executed, **Then** it writes valid JSON to the stream matching `json.dump()` behavior.
4. **Given** a call to `myson.dumps(obj, zen=True)`, **When** executed with a list of dicts, **Then** it produces a Zen Grid formatted string (using `[:` and `]`) that achieves significant token reduction (target ~49.5%) compared to standard JSON.

---

### User Story 2 - High Performance Parsing (Priority: P1)

As a data engineer processing large datasets, I want the parser to handle gigabytes of data per second so that my pipelines run significantly faster than with standard `json`.

**Why this priority**: Performance is the key differentiator against the standard library.

**Independent Test**: Can be tested using a benchmark script with a large (>100MB) JSON file, measuring throughput.

**Acceptance Scenarios**:

1. **Given** a 100MB+ JSON file, **When** parsed with `myson.loads()`, **Then** the throughput exceeds 1GB/s on reference hardware.
2. **Given** a high-throughput scenario, **When** compared to `msgspec` or `orjson`, **Then** `myson` performance is within 10% of these libraries.

---

### User Story 3 - Schema-based Validation (Priority: P2)

As a backend developer, I want to define data schemas using `MysonModel` so that I can validate incoming JSON and get structured objects with zero-copy overhead where possible.

**Why this priority**: Provides modern developer experience similar to Pydantic/msgspec, enabling type safety.

**Independent Test**: Can be tested by defining a `MysonModel` subclass and parsing matching/mismatching JSON data.

**Acceptance Scenarios**:

1. **Given** a `MysonModel` definition with typed fields, **When** `myson.to_json(model_instance)` is called, **Then** it serializes to valid JSON matching the schema.
2. **Given** a `MysonModel` definition, **When** `myson.from_json(data, type=MyModel)` is called with valid JSON, **Then** it returns a hydrated instance of `MyModel`.
3. **Given** invalid JSON data (wrong types), **When** parsed into a `MysonModel`, **Then** it raises a clear validation error.

---

### User Story 4 - License Compliance (Priority: P1)

As an open-source maintainer, I want to ensure all reused code is properly attributed so that the project complies with MIT and Apache 2.0 licenses.

**Why this priority**: Legal and ethical requirement for open source projects.

**Independent Test**: Verify existence and content of `NOTICE` file.

**Acceptance Scenarios**:

1. **Given** the source code distribution, **When** inspected, **Then** a `NOTICE` file exists containing attributions for `msgspec`, `orjson`, and `toon`.

### Edge Cases

- **JSON Compatibility**: Handling of `NaN`, `Infinity`, `-Infinity` (supported by Python `json` but not standard JSON).
- **Type Coercion**: `MysonModel` behavior when input types don't match schema (e.g., string "123" for `int` field).
- **Zero-copy Safety**: Accessing string/bytes fields after the source buffer has been modified or deallocated.
- **Recursion Depth**: Handling of deeply nested JSON structures to prevent stack overflow in C implementation.
- **Encoding**: Input that is not valid UTF-8 (including UTF-16/32) must be rejected, unlike standard `json` which might attempt detection.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-015**: The library MUST provide `loads()`, `load()`, `dumps()`, and `dump()` functions with signatures identical to the Python standard `json` module (including `cls`, `object_hook`, `parse_float`, etc. arguments, even if some are no-ops with warnings).
- **FR-016**: The core tokenizer and parser MUST be implemented in Cython or C.
- **FR-017**: The library MUST support a `MysonModel` class that allows defining schemas with Python type hints.
- **FR-018**: `MysonModel` MUST support zero-copy hydration for string/bytes fields where possible.
- **FR-019**: The project MUST include a `NOTICE` file attributing any logic derived from `msgspec` (MIT), `orjson` (Apache 2.0), or `toon` (MIT).
- **FR-020**: `MysonModel` MUST silently ignore any fields in the input JSON that are not defined in the model schema.
- **FR-021**: `MysonModel` MUST support parsing `datetime`, `date`, and `uuid` fields from ISO 8601 formatted strings.
- **FR-022**: The parser MUST accept only UTF-8 encoded input (bytes or str); UTF-16 and UTF-32 MUST be rejected with a clear error.
- **FR-023**: The parser MUST enforce a fixed recursion limit (default 1024) and raise a `RecursionError` if exceeded, to prevent C stack overflows.
- **FR-024**: The parser MUST support arbitrary precision integers, converting JSON numbers that exceed 64-bit range into Python `int` objects without loss of precision.
- **FR-025**: The Cython parser MUST support Zen Grid table arrays (Constitution III), including header arity checks, null-filling for missing cells, and silent dropping of extra cells.
- **FR-026**: The Cython tokenizer MUST support unquoted ASCII alphanumeric keys (Constitution II) in addition to standard quoted keys.
- **FR-027**: The Cython tokenizer MUST support C-style line (`//`) and block (`/* ... */`) comments (Constitution IV), treating them as whitespace.
- **FR-028**: The parser MUST release the GIL (`nogil`) for any input buffer larger than 1MB to allow concurrency.
- **FR-029**: The parser MUST use `Py_ssize_t` for length/indexing to support inputs exceeding 2GB.
- **FR-030**: `MysonModel` validation MUST be strict; type mismatches MUST raise a `ValidationError` instead of attempting coercion.
- **FR-031**: The project MUST include a benchmark suite using `twitter.json`, `canada.json`, and `citm_catalog.json`, comparing against latest `msgspec`, `orjson`, and `ujson` (Dec 2025) with 5 warm-ups and 100 timed runs.

### Success Criteria

- **SC-001**: `myson` passes at least 95% of the standard library `json` test suite (excluding implementation-specific behaviors like exact error message text).
- **SC-002**: Parsing throughput exceeds 1GB/s on a GitHub Actions Standard Runner (Ubuntu Latest) for Small (1KB), Medium (100KB), and Large (10MB+) payloads.
- **SC-003**: `MysonModel` supports `int`, `float`, `str`, `bool`, `list`, `dict`, `datetime`, `date`, `uuid`, and nested `MysonModel` types.
- **SC-004**: `NOTICE` file is present in the root of the repository.
- **SC-005**: The Python wrapper overhead MUST be <5% compared to the raw C-extension call.
- **SC-006**: `MysonModel` parsing performance MUST be within 15% of raw dict parsing speed.
- **SC-007**: Peak memory usage MUST NOT exceed 2x the size of the input file.

### Key Entities

- **MysonModel**: A base class for defining data schemas.
- **Parser**: The C/Cython extension module handling low-level parsing.
- **Serializer**: The C/Cython extension module handling low-level serialization.

## Assumptions

- The user has a C compiler available for installing the package (or pre-built wheels will be provided later).
- "Identical signatures" for `json` compatibility implies best-effort support for extension hooks; some dynamic hooks might have performance penalties or be limited in the C implementation.
- Zero-copy hydration requires the input buffer to remain valid for the lifetime of the object; this is acceptable for the `MysonModel` use case.

## Clarifications

### Session 2025-12-24

- Q: How should MysonModel handle extra fields in the input JSON? → A: Ignore (silently discard extra fields).
- Q: Should MysonModel support extended types like datetime and UUID? → A: Yes, support datetime, date, and uuid parsing from ISO 8601 strings.
- Q: What text encodings must the parser support? → A: UTF-8 only (reject UTF-16/32).
- Q: How should the parser handle deep nesting? → A: Enforce a fixed recursion limit (e.g., 1024) and raise RecursionError.
- Q: How should the parser handle large integers? → A: Support arbitrary precision integers (Python int), matching json behavior.
