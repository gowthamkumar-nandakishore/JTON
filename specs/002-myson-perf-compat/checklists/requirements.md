# Requirement Checklist: Performance and Compatibility Update

**Feature**: `002-myson-perf-compat`
**Focus**: Balanced (API Fidelity + Implementation Safety)
**Validation Depth**: Complex Scenarios
**Compatibility**: Full Fidelity

## 1. API Compatibility (Full Fidelity)

- [ ] **Signatures**: `loads`, `load`, `dumps`, `dump` MUST match Python 3.10+ `json` module signatures exactly.
- [ ] **Arguments**: All arguments MUST be accepted, even if some are no-ops (with warnings).
  - [ ] `cls` (Custom Encoder/Decoder) support.
  - [ ] `object_hook` and `object_pairs_hook` support.
  - [ ] `parse_float`, `parse_int`, `parse_constant` support.
  - [ ] `default` (for serialization) support.
  - [ ] `sort_keys`, `indent`, `separators` support.
- [ ] **Behavior**:
  - [ ] `NaN`, `Infinity`, `-Infinity` handling matches `json` (allow_nan=True default).
  - [ ] Large integer handling matches `json` (arbitrary precision).
  - [ ] Circular reference detection (`check_circular=True`).

## 2. Implementation Safety (The Core)

- [ ] **Memory Safety**:
  - [ ] Buffer protocol usage MUST be safe (no access after invalidation).
  - [ ] Internal buffers MUST be managed correctly (`malloc`/`free`).
- [ ] **Concurrency**:
  - [ ] GIL MUST be released during long parsing operations (where possible).
  - [ ] Thread-safety for shared internal state (if any).
- [ ] **Resilience**:
  - [ ] **Recursion Limit**: Fixed limit (e.g., 1024) MUST be enforced to prevent C stack overflow.
  - [ ] **Encoding**: Strict UTF-8 enforcement; reject UTF-16/32 immediately.
  - [ ] **Input Size**: Handle large inputs (>2GB) correctly (using `size_t` or `Py_ssize_t`).

## 3. MysonModel (Complex Scenarios)

- [ ] **Schema Definition**:
  - [ ] Support standard types: `int`, `float`, `bool`, `str`, `bytes`.
  - [ ] Support extended types: `datetime`, `date`, `uuid` (ISO 8601).
  - [ ] Support nesting: `MysonModel` inside `MysonModel`.
  - [ ] Support generics: `list[T]`, `dict[K, V]`, `Optional[T]`.
- [ ] **Validation Logic**:
  - [ ] **Extra Fields**: Silently ignore fields not in schema.
  - [ ] **Type Coercion**: Strict or lenient? (Spec implies strict for performance, but `json` is loose. Clarified as: validation raises error on mismatch).
- [ ] **Zero-Copy**:
  - [ ] `bytes` fields point to input buffer (when input is bytes/bytearray).
  - [ ] `str` fields are optimized (interning or efficient decoding).

## 4. Performance & Constitution

- [ ] **Throughput**: >1GB/s on reference hardware.
- [ ] **Zen Grid**:
  - [ ] Header arity enforcement.
  - [ ] **Resilience**: Null-fill missing cells, drop extra cells.
  - [ ] Nested objects/lists in cells parsed atomically.
- [ ] **Unquoted Keys**: ASCII alphanumeric only.

## 5. Edge Cases & Limits

- [ ] **Empty Inputs**: Handle empty strings/files gracefully (raise JSONDecodeError).
- [ ] **Trailing Commas**: Allowed (per Constitution/Spec).
- [ ] **Comments**: `//` and `/* */` allowed and stripped.
- [ ] **Deep Nesting**: Trigger `RecursionError` at limit.
- [ ] **Invalid UTF-8**: Raise `UnicodeDecodeError` or `JSONDecodeError`.
