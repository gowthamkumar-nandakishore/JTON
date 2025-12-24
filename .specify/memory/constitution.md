<!--
Sync Impact Report:
- Version: 1.0.0 -> 1.1.0
- Modified principles: Added "Nitro" Performance Mandate, Zen Grid Resilience Update
- Added sections: Implementation Constraints & Deliverables, Quality Gates & CI
- Removed sections: none
- Templates requiring updates: none
- Follow-ups: Rust migration, Cython deprecation
-->

# MYSON Constitution

## Core Principles

### I. JSON Superset Fidelity (NON-NEGOTIABLE)
Every valid JSON document MUST parse as-is under MYSON with identical semantics. Extension features (comments, tables) MUST NOT break backward compatibility. Error messaging MUST distinguish between JSON and MYSON-only violations.

### II. The "Nitro" Performance Mandate
The core engine MUST target a minimum throughput of 1.5 GB/s. Implementation MUST prioritize Rust with AVX2/AVX-512 SIMD intrinsics. Scalar fallbacks are rejected; hardware that does not support AVX2 (pre-2013) is explicitly unsupported to prevent code bloat.

### III. Zen Grid Arrays (Resilience Update)
Zen Grid arrays use `[:` to open, `]` to close, `;` for row separation, and `,` for column separation.

**Arity Enforcement**: The first row defines the header. Subsequent rows MUST match header count.

**Resilience**: Missing cells are null-filled; extra cells are silently truncated (±32 byte error margin accepted for SIMD speed).

**Pre-allocation**: The parser MUST pre-allocate memory based on a semicolon scan, capped at 1 million rows for OOM safety.

### IV. Unquoted Alphanumeric Keys
Object keys MAY omit quotes if they consist strictly of ASCII letters and digits. Tokenization MUST reject unquoted keys containing punctuation, whitespace, or Unicode.

### V. Comment & Whitespace Discipline
C-style line (`//`) and block (`/* */`) comments are accepted wherever whitespace is valid. The SIMD scanner MUST skip comments and whitespace at a rate of 32 bytes per cycle.

## Implementation Constraints & Deliverables

- **Language**: Rust (via PyO3 and maturin). The Python `myson_core.pyx` is officially deprecated and removed.
- **Memory Model**: Zero-copy utilizing the Python Buffer Protocol. String interning is mandatory for headers and categorical fields.
- **Parallelism**: Phase 2 introduces Rayon-based multi-threading for chunked parsing of Zen Grids.
- **Schema-Guided Mode**: When a schema is provided, the parser MUST bypass key-hashing and positional-scan JSON/Tables directly.

## Quality Gates & CI

- **Performance Gate**: Every PR MUST pass a benchmark check. Throughput MUST NOT drop below the 233.9 MB/s baseline; final merges require ≥1.5 GB/s.
- **Test Parity**: All 400+ comprehensive tests (Zen Grid nesting, empty tables, unquoted keys) MUST pass 100% in the Rust engine.
- **Approximate Errors**: For a 20% speed gain, error locations are permitted a ±32 byte variance from the exact point of failure.

## Governance

- **Authoritative Source**: This document overrides all other specifications, plans, or READMEs.
- **Versioning**: Minor bump (1.1.0) for the Rust transition and Zen Grid truncation logic. Major bump required for any change breaking JSON compatibility.

**Version**: 1.1.0 | **Ratified**: 2025-12-23 | **Last Amended**: 2025-12-24