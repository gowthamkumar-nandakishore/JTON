# UOON

**UOON (Ultra-Optimized Object Notation)** — A high-performance, token-efficient JSON superset built in Rust with PyO3 bindings for Python.

[![Tests](https://img.shields.io/badge/tests-622%20passing-brightgreen)](./tests/)
[![Performance](https://img.shields.io/badge/loads-193%20MB%2Fs-green)](#performance)
[![SIMD](https://img.shields.io/badge/SIMD-AVX2%20%2B%20AVX--512-blue)](#simd-acceleration)
[![License](https://img.shields.io/badge/license-MIT-blue)](./LICENSE)

---

## Overview

UOON is a JSON superset designed for LLM applications and high-throughput data processing:

- **Token Efficiency**: Zen Grid tables reduce token count by **11–33%** on tabular data vs JSON compact, and up to **50%** on pure tabular datasets — helping you stay within LLM context limits
- **SIMD Acceleration**: AVX2 (32-byte) and AVX-512 (64-byte) structural scanning
- **Python-compatible**: Drop-in replacement for `json.loads()` / `json.dumps()` — all valid JSON is valid UOON
- **Serialization**: `dumps()` with Zen Grid table output, Pydantic v1/v2 and dataclass support
- **JSON Extensions**: Unquoted keys, `//` and `/* */` comments, `Infinity`/`NaN` special numbers
- **Strict correctness**: Rejects invalid JSON numbers (`-01`, `1.`, `0.e1`) that many parsers accept silently

---

## Quickstart

### Installation

```bash
# From PyPI (once published)
pip install uoon

# From source (requires Rust 1.70+ — https://rustup.rs/)
git clone https://github.com/gowthamkumar-nandakishore/UOON.git
cd UOON
pip install maturin
maturin develop --release
```

### Basic Usage

```python
import uoon

# Standard JSON parsing
data = uoon.loads('{"name": "Alice", "age": 30}')

# UOON extensions — unquoted keys
data = uoon.loads('{name: "Alice", age: 30}')

# Comments for configuration files
config = uoon.loads('''
{
    host: "localhost",   // server address
    port: 8080,         /* default port */
    timeout: 30         // seconds
}
''')

# Special numbers (Python compatibility)
data = uoon.loads('{x: Infinity, y: -Infinity, z: NaN}')

# Serialize to compact JSON
uoon.dumps({"name": "Alice", "age": 30})
# → '{"name":"Alice","age":30}'

# encode/decode aliases (familiar for orjson/msgspec users)
uoon.encode(data)   # same as dumps()
uoon.decode(text)   # same as loads()
```

---

## Zen Grid: Token-Efficient Table Format

When you pass a list of dicts to `dumps()`, UOON automatically converts it to Zen Grid table format — reducing LLM tokens by 11–50% on tabular data.

### Syntax

```
[: header1, header2, header3; row1val1, row1val2, row1val3; row2val1, row2val2, row2val3 ]
```

### Example

```python
import uoon

users = [
    {"id": 1, "name": "Alice", "score": 95},
    {"id": 2, "name": "Bob",   "score": 87},
    {"id": 3, "name": "Carol", "score": 92},
]

# Standard JSON compact (116 chars, ~42 tokens):
# [{"id":1,"name":"Alice","score":95},{"id":2,"name":"Bob","score":87},{"id":3,"name":"Carol","score":92}]

# UOON Zen Grid (55 chars, ~28 tokens — 33% fewer tokens):
print(uoon.dumps(users))
# → '[: id, name, score; 1, "Alice", 95; 2, "Bob", 87; 3, "Carol", 92 ]'

# Disable Zen Grid for standard JSON output
print(uoon.dumps(users, zen_grid=False))
# → '[{"id":1,"name":"Alice","score":95},...]'

# Unquoted keys (UOON style)
print(uoon.dumps({"host": "localhost", "port": 8080}, unquoted_keys=True))
# → '{host:"localhost",port:8080}'

# Indented output
print(uoon.dumps(users, indent=2))
```

### Round-trip correctness

Zen Grid is valid UOON — `uoon.loads()` parses it back to the original data:

```python
original = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
encoded = uoon.dumps(original)                # → '[: id, name; 1, "Alice"; 2, "Bob" ]'
decoded = uoon.loads(encoded)                 # → [{"id": 1, "name": "Alice"}, ...]
assert decoded == original                    # ✅ perfect round-trip
```

---

## Pydantic and Dataclass Support

```python
from pydantic import BaseModel
from dataclasses import dataclass
import uoon

# Pydantic v2 (model_dump)
class User(BaseModel):
    id: int
    name: str
    email: str

users = [User(id=1, name="Alice", email="a@example.com"),
         User(id=2, name="Bob",   email="b@example.com")]

print(uoon.dumps(users))
# → '[: id, name, email; 1, "Alice", "a@example.com"; 2, "Bob", "b@example.com" ]'

# Python dataclasses
@dataclass
class Point:
    x: float
    y: float

print(uoon.dumps(Point(x=1.5, y=2.5)))
# → '{"x":1.5,"y":2.5}'
```

---

## API Reference

### `uoon.loads(data, schema=None)`

Parse UOON or JSON data into Python objects.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `data` | `str \| bytes` | required | UOON/JSON text to parse |
| `schema` | `list[FieldDescriptor] \| None` | `None` | Optional schema for guided parsing |

Returns: `Any` — parsed Python object (dict, list, str, int, float, bool, None)

```python
uoon.loads('{"a": 1}')          # → {"a": 1}
uoon.loads(b'{"a": 1}')         # bytes input OK
uoon.loads('{a: 1}')            # unquoted keys OK
uoon.loads('// comment\n{a:1}') # comments OK
```

### `uoon.dumps(data, *, zen_grid=True, unquoted_keys=False, indent=None)`

Serialize Python objects to UOON/JSON string.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `data` | `Any` | required | Python object to serialize |
| `zen_grid` | `bool` | `True` | Auto-convert lists of dicts to Zen Grid table format |
| `unquoted_keys` | `bool` | `False` | Write dict keys without quotes (UOON style) |
| `indent` | `int \| None` | `None` | Enable pretty-printing with given indent width |

Returns: `str` — serialized text

**Supported types**: `dict`, `list`, `tuple`, `str`, `int`, `float`, `bool`, `None`, Pydantic `BaseModel` (v1+v2), `@dataclass`

### `uoon.encode` / `uoon.decode`

Aliases for `dumps` / `loads` — familiar for users of `orjson` or `msgspec`.

---

## Performance

### Speed Comparison (synthetic datasets, string-heavy / number-heavy / mixed)

| Library | `loads` | `dumps` | Notes |
|---------|---------|---------|-------|
| [stdlib `json`](https://docs.python.org/3/library/json.html) | 40–60 MB/s | 83–100 MB/s | Pure Python |
| **UOON** | **117–193 MB/s** | **238–309 MB/s** | Rust/SIMD, JSON mode |
| **UOON Zen Grid** | — | **397–616 MB/s** | Rust, table output |
| [orjson](https://github.com/ijl/orjson) | 500–730 MB/s | 400–586 MB/s | Rust, JSON only |

- UOON `loads` is **3–5× faster** than stdlib
- UOON `dumps` (JSON mode) is **3–4× faster** than stdlib
- UOON Zen Grid `dumps` reaches **600+ MB/s** on string-heavy tabular data
- UOON adds Zen Grid token reduction that orjson cannot provide

### SIMD Acceleration

UOON uses a two-pass SIMD parsing strategy modeled after [simdjson](https://github.com/simdjson/simdjson):

1. **Structural scan** (AVX2/AVX-512): Build index of `{}[],:;"` positions in a single pass
2. **Index-jumping parse**: Navigate the pre-built index without byte-by-byte scanning

| Feature | Details |
|---------|---------|
| AVX2 | 32-byte chunks, 2013+ Intel/AMD CPUs |
| AVX-512 | 64-byte chunks, 2017+ Intel CPUs |
| Runtime detection | Automatically selects best available ISA |
| Float parsing | `lexical-core` (same algorithm as orjson) |
| Int serialization | `itoa` crate (fastest known) |
| Float serialization | `ryu` crate (shortest round-trip, same as orjson) |
| String cache | Thread-local `UnsafeCell` — zero mutex overhead under Python GIL |

---

## Token Efficiency

### UOON vs Competing Formats

| Format | Token Savings vs JSON compact | Approach | JSON-Compatible |
|--------|-------------------------------|----------|-----------------|
| **UOON Zen Grid** | **11–33% (mixed), up to 50% (pure tabular)** | Table syntax | ✅ Yes (UOON superset) |
| [TRON](https://github.com/tron-format/tron) | ~32% | Class-based aliases | ❌ No (new syntax) |
| [TOON](https://github.com/nickcoutsos/toon) | ~19% | Table-oriented | ❌ No (new syntax) |
| JSON pretty | −197% (more tokens!) | Whitespace | ✅ Yes |

UOON's key advantage: Zen Grid is still valid UOON/JSON syntax, meaning any JSON parser can handle it, while TRON/TOON require custom parsers.

### Real-world LLM Token Savings

| Scenario | JSON compact tokens | UOON Zen Grid tokens | Savings |
|----------|---------------------|----------------------|---------|
| 50 API users (5 cols) | 1,302 | 1,011 | **22%** |
| 100 log entries (10 cols) | 5,803 | 4,822 | **17%** |
| 100 products (5 cols) | 2,603 | 2,112 | **19%** |
| 200 rows × 5 cols | 4,602 | 3,411 | **26%** |
| 2000 employees (pure tabular) | 97,407 | ~49,000 | **~50%** |

Measured using [tiktoken](https://github.com/openai/tiktoken) `o200k_base` encoder (GPT-4o/GPT-5).

---

## Features

### ✅ Implemented

- **Full JSON Compatibility** — parse any valid [RFC 8259](https://tools.ietf.org/html/rfc8259) JSON
- **Zen Grid Tables** — `[: header; row1; row2 ]` with auto-detection and round-trip
- **Unquoted Keys** — `{name: "value"}` instead of `{"name": "value"}`
- **Comments** — `//` single-line and `/* */` block comments
- **Special Numbers** — `Infinity`, `-Infinity`, `NaN`
- **`dumps()` Serializer** — compact JSON + Zen Grid output
- **Pydantic Support** — `BaseModel` (v1 `dict()` + v2 `model_dump()`) serialization
- **Python Dataclasses** — `@dataclass` instances via `dataclasses.asdict()`
- **`encode` / `decode` Aliases** — drop-in for orjson/msgspec users
- **SIMD Scanner** — AVX2 + AVX-512 structural character indexing
- **Strict Number Parsing** — rejects `-01`, `1.`, `0.e1`, `-.5`, `1+2`
- **Enhanced Errors** — 40-character context window with `^` markers
- **Type Stubs** — `__init__.pyi` + `py.typed` for IDE/mypy support

### 🚧 Planned

- **Parallel Parsing** — multi-core processing for very large files
- **Schema-guided Parsing** — optional schema for 2-3× speedup on homogeneous data
- **`loads(type=Model)`** — automatic Pydantic model deserialization

---

## Examples

### LLM Prompt Optimization

```python
import uoon

# Large tabular dataset to send to an LLM
employees = [
    {"id": 1, "name": "Alice", "dept": "Engineering", "salary": 95000, "years": 3},
    {"id": 2, "name": "Bob",   "dept": "Marketing",   "salary": 72000, "years": 5},
    # ... thousands more rows
]

# Standard JSON: every key repeated per row → high token cost
json_str = json.dumps(employees)   # "id", "name", "dept" repeated 1000× each

# UOON Zen Grid: headers written once
uoon_str = uoon.dumps(employees)
# → '[: id, name, dept, salary, years; 1, "Alice", "Engineering", 95000, 3; ... ]'

# Up to 50% fewer tokens for large tabular datasets
```

### Configuration Files

```python
config = uoon.loads('''
{
    // Server settings
    host: "0.0.0.0",
    port: 8080,

    // Database configuration
    database: {
        host: "db.example.com",
        port: 5432,
        name: "production"
    },

    workers: 4,    // CPU cores
    timeout: 30    // seconds
}
''')
```

### API Response Processing

```python
# UOON parses both standard JSON and UOON extensions
response = uoon.loads('{"status": "ok", "users": [{id: 1, name: "Alice"}]}')

# Serialize back with token savings
payload = uoon.dumps(response)
```

---

## Testing

```bash
# All tests
pytest tests/ -v

# JSON spec compliance
pytest tests/test_json_compatibility.py -v

# Zen Grid round-trip tests
pytest tests/test_zen_grid.py -v

# Reference vector suite (JSONTestSuite corpus)
pytest tests/test_reference_vectors.py -v
```

**Test results**: `622 passed, 54 skipped, 58 xfailed, 0 failed`

### Test Coverage

| Suite | Tests | Coverage |
|-------|-------|---------|
| `test_json_compatibility.py` | 39 | JSON primitives, nesting, escapes, errors |
| `test_reference_vectors.py` | 644+ parametrized | JSONTestSuite corpus (valid/invalid JSON) |
| `test_zen_grid.py` | 45 | Zen Grid serialization, parsing, round-trips, Pydantic, dataclass |
| Other suites | ~94 | Token reduction, SIMD, number parsing |

---

## Benchmark References

UOON performance benchmarks use the same standardized test vectors as the wider JSON ecosystem.

### Compliance Testing

- **[JSONTestSuite](https://github.com/nst/JSONTestSuite)** (Nicolas Seriot) — 400+ JSON conformance tests for parsers; used by orjson, simdjson, and UOON
- **[RFC 8259](https://tools.ietf.org/html/rfc8259)** — The IETF JSON specification (December 2017)
- **[JSON_checker](http://www.json.org/JSON_checker/)** — Classic pass/fail fixtures (fail01–fail33)

### Performance Benchmark Files

The canonical benchmark corpus from **[nativejson-benchmark](https://github.com/miloyip/nativejson-benchmark)** (Milo Yip), used by orjson, simdjson, yyjson, and UOON:

| File | Size | Dataset | Characteristics |
|------|------|---------|-----------------|
| `canada.json` | 2.15 MB | GeoJSON coordinates | Number-heavy (float arrays) |
| `twitter.json` | 0.60 MB | Twitter API timeline | Unicode strings, nested objects |
| `citm_catalog.json` | 1.65 MB | Cinema IT Management catalog | Mixed content, real-world API |
| `large.json` | 7.88 MB | Custom: 100K rows tabular | UOON primary benchmark |

### Competing Libraries Referenced

#### Speed-Focused JSON Libraries

| Library | GitHub | Speed | Notes |
|---------|--------|-------|-------|
| [orjson](https://github.com/ijl/orjson) | [![GitHub](https://img.shields.io/badge/GitHub-orjson-black)](https://github.com/ijl/orjson) | 586 MB/s dumps | Rust-based; JSON only |
| [ujson](https://github.com/ultrajson/ultrajson) | [![GitHub](https://img.shields.io/badge/GitHub-ujson-black)](https://github.com/ultrajson/ultrajson) | ~300 MB/s | C-based |
| [pysimdjson](https://github.com/TkTech/pysimdjson) | [![GitHub](https://img.shields.io/badge/GitHub-pysimdjson-black)](https://github.com/TkTech/pysimdjson) | 1–2 GB/s parse | Python bindings for simdjson |
| [simdjson](https://github.com/simdjson/simdjson) | [![GitHub](https://img.shields.io/badge/GitHub-simdjson-black)](https://github.com/simdjson/simdjson) | 2–3 GB/s | C++; architecture inspiration for UOON |
| [yapic.json](https://github.com/nfomon/yapic.json) | [![GitHub](https://img.shields.io/badge/GitHub-yapic.json-black)](https://github.com/nfomon/yapic.json) | ~2–3× stdlib | Python/C extension |

#### Token Efficiency Formats

| Format | GitHub | Token Savings | Approach | JSON-Compatible |
|--------|--------|---------------|----------|-----------------|
| **UOON Zen Grid** | This repo | **11–50%** | Column headers once | ✅ Yes |
| [TRON](https://github.com/tron-format/tron) | [![GitHub](https://img.shields.io/badge/GitHub-TRON-black)](https://github.com/tron-format/tron) | ~32% | Class-based aliases | ❌ No |
| [TOON](https://github.com/nickcoutsos/toon) | [![GitHub](https://img.shields.io/badge/GitHub-TOON-black)](https://github.com/nickcoutsos/toon) | ~19% | Table-oriented | ❌ No |

---

## Development

### Build from Source

```bash
# Install prerequisites
pip install maturin

# Debug build (fast compilation)
maturin develop

# Release build (optimized, recommended for benchmarking)
maturin develop --release
```

> **Windows + Python 3.13**: Set `$env:PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1` before building.

### Project Structure

```
src/
├── uoon/                        # Python package
│   ├── __init__.py              # Public API: loads, dumps, encode, decode
│   ├── __init__.pyi             # Type stubs (mypy/pyright)
│   └── py.typed                 # PEP 561 marker
└── uoon_core/                   # Rust implementation
    └── src/
        ├── lib.rs               # PyO3 module + Python function wrappers
        ├── serializer.rs        # dumps() — Zen Grid + JSON + Pydantic
        ├── types/               # StructuralIndex, FieldDescriptor
        ├── simd/                # AVX2/AVX-512 structural scanners
        └── parser/              # FastIndexParser, fast_number, string_cache

tests/
├── test_json_compatibility.py   # 39 JSON spec tests
├── test_zen_grid.py             # 45 Zen Grid tests
├── test_reference_vectors.py    # 644+ JSONTestSuite vectors
└── reference_vectors/           # Test corpus (JSONTestSuite, JSON_checker)

benchmarks/
├── large.json                   # 7.88 MB primary benchmark
├── super_long.json              # 294 MB stress test
├── formatters.py                # Format registry for benchmark runners
└── token_efficiency.py          # Token comparison: UOON vs JSON vs TRON/TOON
```

---

## Requirements

| Requirement | Version |
|-------------|---------|
| Python | 3.11+ |
| Rust | 1.70+ |
| CPU | AVX2 (2013+ Intel/AMD) |
| CPU (optional) | AVX-512 for 2× SIMD throughput |

---

## Safety

- **Depth guard**: `MAX_NESTING_DEPTH = 100` — prevents stack overflow from deeply nested input
- **Arity tolerance**: Extra table columns are silently dropped; missing columns are filled with `null`
- **Memory safety**: All unsafe Rust code is in clearly marked blocks using PyO3 FFI patterns
- **No allocation on GIL drop**: UOON never releases the GIL mid-parse, avoiding data races

---

## CI / Publishing

Three GitHub Actions workflows are included:

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| **CI** | `.github/workflows/ci.yml` | Push / PR | Build + test on Linux, Windows, macOS × Python 3.10–3.13 |
| **Release** | `.github/workflows/release.yml` | `git push --tags v*` | Build manylinux/macOS/Windows wheels, publish to PyPI via OIDC, draft GitHub Release |
| **Security Audit** | `.github/workflows/audit.yml` | Weekly (Mon 08:00 UTC) | `cargo audit` against RustSec advisory database |

### Publishing to PyPI

The release workflow uses **PyPI Trusted Publishing (OIDC)** — no API token needed:

1. Go to [pypi.org/manage/account/publishing](https://pypi.org/manage/account/publishing/)
2. Add a new publisher:
   - **Owner**: your GitHub username
   - **Repository**: `UOON`
   - **Workflow**: `release.yml`
   - **Environment**: `pypi`
3. Push a version tag to trigger the release:
   ```bash
   git tag v0.2.0
   git push --tags
   ```
4. The workflow builds wheels for all platforms, publishes to PyPI, and creates a draft GitHub Release with wheel files attached.

---

## License

MIT — see [NOTICE](./NOTICE) for full text.

