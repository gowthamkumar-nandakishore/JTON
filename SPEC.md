# JTON Specification
## Version 1.0

---

## 1. Introduction

**JTON (JSON Tabular Object Notation)** is a strict superset of JSON. Every valid JSON document is a valid JTON document with identical semantics. JTON extends JSON with:

1. **Extensions** — syntactic conveniences (unquoted keys, comments, special numbers)
2. **Zen Grid** — a token-efficient tabular encoding for homogeneous arrays of objects

JTON's primary goals are:
- **Speed**: SIMD-accelerated parsing (AVX2 / AVX-512 / NEON)
- **Token efficiency**: Zen Grid reduces LLM token counts by 20–60% vs JSON
- **LLM accuracy**: `[N: headers; rows ]` format with structural metadata

---

## 2. Conformance

A conforming JTON **parser** MUST:
- Accept all inputs described in this specification
- Produce Python/host-language objects identical to the semantics defined here
- Reject all syntactically invalid inputs with a `ValueError`

A conforming JTON **serializer** MUST:
- Produce output that round-trips through a conforming parser
- Default to the Zen Grid encoding for homogeneous arrays of dicts when `zen_grid=True`

---

## 3. Lexical Grammar

### 3.1 Character Encoding

JTON input MUST be valid UTF-8. Byte-order marks (BOM) are permitted and ignored.

### 3.2 Whitespace

Whitespace characters (U+0020, U+0009, U+000A, U+000D) are insignificant outside strings.

### 3.3 Comments (JTON Extension)

JTON parsers MUST accept:
- **Line comments**: `// text` — extends to end of line
- **Block comments**: `/* text */` — may span lines, may NOT be nested

Comments are ignored. Example:
```
{
    host: "localhost",   // server address
    port: 8080,         /* default port */
}
```

### 3.4 Numbers

JTON parsers MUST accept:
- All RFC 8259 §6 number literals
- `Infinity`, `-Infinity` → mapped to host language infinity (Python `float('inf')`)
- `NaN` → mapped to host language NaN (Python `float('nan')`)

JTON parsers MUST reject:
- Leading zeros in integers: `-01`, `00`
- Trailing decimal points: `1.`
- Exponent without mantissa digits: `0.e1`

### 3.5 Strings

Identical to JSON RFC 8259 §7. All JSON escape sequences are supported.

---

## 4. Value Types

JTON defines the same value types as JSON:
- **null** → Python `None`
- **true** / **false** → Python `bool`
- **number** → Python `int` or `float`
- **string** → Python `str`
- **array** → Python `list`
- **object** → Python `dict`

---

## 5. JTON extensions

### 5.1 Unquoted Keys (JTON Extension)

Object keys that are valid ECMAScript identifiers MAY be written without quotes.

An identifier consists of:
- First character: `[A-Za-z_$]`
- Subsequent characters: `[A-Za-z0-9_$]`

```
{name: "Alice", age: 30}   // ✅ valid JTON
{"name": "Alice", "age": 30} // ✅ valid JSON and JTON
```

### 5.2 Trailing Commas (JTON Extension)

A single trailing comma after the last element/member in an array or object MUST be accepted.

```
[1, 2, 3,]     // ✅ valid JTON
{"a": 1, }     // ✅ valid JTON
```

---

## 6. Zen Grid Format

The **Zen Grid** is JTON's primary LLM optimisation. It encodes a homogeneous array of objects as a compact inline table.

### 6.1 Canonical Form

```
[N: header1, header2, ..., headerK; row1val1, row1val2, ..., row1valK; ... rowNval1, ..., rowNvalK ]
```

Where:
- `N` is the count of data rows (a non-negative integer)
- `header1, ..., headerK` are the field names in declaration order
- Each subsequent semicolon-delimited segment contains `K` values for one record
- Values within a segment are separated by the configured delimiter (default: `, `)
- The closing `]` is always preceded by a space

### 6.2 Eligibility

A Zen Grid is emitted if and only if:
1. The input is a `list` with ≥ 2 elements
2. Every element is an `object` (dict)
3. Every element has **identical** keys in **identical** order (homogeneous schema)
4. `zen_grid=True` (the default)

If eligibility is not met, the serializer falls back to standard JSON array output.

### 6.3 Row Count

The leading `N` is always present when `row_count=True` (the default).

When `row_count=False`, the header segment immediately follows `[:`

```
[: col1, col2; val1, val2; val3, val4 ]   # row_count=False
[2: col1, col2; val1, val2; val3, val4 ]  # row_count=True (default)
```

Both forms are valid and MUST be parseable by a conforming parser.

### 6.4 Delimiters

Three delimiter modes are defined:

| Mode | Separator | Token cost | Use case |
|------|-----------|-----------|----------|
| `comma` (default) | `, ` | standard | Human-readable, LLM-friendly |
| `tab` | `\t` | 5–15% fewer | Maximum token savings |
| `pipe` | ` \| ` | similar to comma | Alternative table style |

The delimiter applies to both the header segment and all value segments.

### 6.5 Value Encoding in Zen Grid Cells

Each cell value is serialized as follows:

| Python type | Cell encoding | Notes |
|-------------|---------------|-------|
| `None` | `null` | or empty string if `implicit_null=True` |
| `bool` | `true` / `false` | |
| `int` | decimal digits | |
| `float` | shortest round-trip (ryu) | |
| `str` (identifier) | `"quoted"` | or unquoted if `bare_strings=True` |
| `str` (non-identifier) | `"quoted"` | always quoted |
| Nested object/array | JSON-encoded | sub-objects serialized inline |

An **identifier string** is any string matching `^[A-Za-z_$][A-Za-z0-9_$]*$` with length ≤ 64.

### 6.6 Multiline Zen Grid (TOON-compatible)

When `multiline_zen=True`, the serializer emits a multi-line format compatible with TOON:

```
[N]{col1,col2,col3}:
  val1,val2,val3
  val4,val5,val6
```

- First line: `[N]{col1,col2,...}:` where `N` is the row count
- Each subsequent line: two-space indented comma-separated values
- Provides proven +1.4 pp LLM accuracy over standard JSON on Gemini models
- **Note**: This format is serializer-only; `JTON.loads()` does not parse multiline Zen Grid

### 6.7 Parser Requirements for Zen Grid

A conforming parser MUST:

1. Recognize the `[:` or `[N:` prefix and enter Zen Grid parsing mode
2. Read the first segment as a comma-separated list of field name strings
3. Read each subsequent semicolon-delimited segment as one record
4. Map values positionally to field names from the header
5. Handle all three delimiter modes (comma, tab, pipe) via auto-detection
6. Produce a Python list of dicts with string keys matching the header

A conforming parser MUST handle:
- Quoted string values: `"Alice"`, `"New York"`
- Unquoted numeric values: `42`, `3.14`, `-7`
- Unquoted boolean values: `true`, `false`
- Unquoted null: `null`
- Empty cells (when `implicit_null=True`): maps to `None`

### 6.8 Format Hint

Parsers expose `format_hint(style)` which returns a natural-language description for use in LLM system prompts. The canonical hint for the default format is:

```
Data is in JTON Zen Grid format.
Format: [N: col1, col2, col3; row1val1, row1val2, row1val3; row2val1, ... ]
N is the total row count. The first segment contains header field names.
Each subsequent semicolon-separated segment is one data record, values in header order.
Example: [3: id, name, score; 1, Alice, 95; 2, Bob, 87; 3, Carol, 92 ]
```

---

## 7. Serializer Behaviour

### 7.1 Type Dispatch Priority

The serializer MUST check types in this order (to handle Python's `bool` → `int` subtype):

1. `None` → `null`
2. `bool` → `true` / `false`
3. `str` → JSON string with escape sequences
4. `int` → decimal string (itoa)
5. `float` → shortest round-trip string (ryu); `inf` → `Infinity`; `nan` → `NaN`
6. `dict` → JSON object (or Zen Grid if eligible)
7. `list` → JSON array (or Zen Grid if eligible)
8. `tuple` → treated as `list`
9. `bytes` → UTF-8 decoded, then serialized as JSON string
10. Pydantic `BaseModel` → `model_dump()` (v2) or `dict()` (v1), then re-dispatched
11. `@dataclass` → `dataclasses.asdict()`, then re-dispatched

### 7.2 Depth Limit

Serialization MUST raise `ValueError` when object nesting exceeds 256 levels.

### 7.3 String Escaping

The following byte values MUST be escaped in JSON strings:

| Byte | Escape |
|------|--------|
| 0x22 (`"`) | `\"` |
| 0x5C (`\`) | `\\` |
| 0x0A | `\n` |
| 0x0D | `\r` |
| 0x09 | `\t` |
| 0x08 | `\b` |
| 0x0C | `\f` |
| 0x00–0x1F (other) | `\u00XX` |

JTON uses SIMD acceleration for escape detection:
- **AVX-512BW** (64-byte chunks): Intel Ice Lake+ / AMD Zen 4+
- **AVX2** (32-byte chunks): Intel Haswell+ / AMD Excavator+
- **Scalar fallback**: All architectures

---

## 8. SIMD Requirements

### 8.1 Minimum CPU Features

| Architecture | Minimum | Notes |
|---|---|---|
| x86_64 | AVX2 | Required; detected at runtime |
| x86_64 | AVX-512BW | Optional; auto-selected when available |
| aarch64 | NEON | Always available on AArch64 |
| Other | Scalar | Always available |

If AVX2 is not available on x86_64, the module MUST raise `RuntimeError` at import time.

### 8.2 Runtime Detection

Feature detection uses `std::is_x86_feature_detected!()` at call time. The best available ISA is selected automatically:

```
AVX-512BW → AVX2 → NEON → Scalar
```

---

## 9. Versioning

This document describes JTON Specification version **1.0**.

Backward-compatible changes (new optional features) increment the minor version.  
Breaking changes (format incompatibilities) increment the major version.

The format version is accessible at runtime:
```python
import jton
print(jton.__version__)  # "1.0.0"
```

---

*JTON Specification 1.0 — MIT License*

