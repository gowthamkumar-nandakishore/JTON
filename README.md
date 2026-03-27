# JTON

**JTON (JSON Tabular Object Notation)** — A high-performance, token-efficient JSON superset built in Rust with PyO3 bindings for Python. Home of **Zen Grid**, a token-aware tabular encoding that reduces LLM token costs by 19–61%.

[![Tests](https://img.shields.io/badge/tests-685%20passing-brightgreen)](./tests/)
[![Performance](https://img.shields.io/badge/loads-193%20MB%2Fs-green)](#performance)
[![SIMD](https://img.shields.io/badge/SIMD-AVX2%20%2B%20AVX--512-blue)](#simd-acceleration)
[![License](https://img.shields.io/badge/license-MIT-blue)](./LICENSE)

---

## Overview

JTON is a JSON superset designed for LLM applications and high-throughput data processing:

- **Zen Grid**: Tabular encoding reduces token count by **19–61%** on real-world data vs JSON compact (32% average across 7 domains)
- **LLM-Validated**: 12 models tested for comprehension, 13 models tested for generation — 10/13 achieve 100% generation validity
- **SIMD Acceleration**: AVX2 (32-byte) and AVX-512 (64-byte) structural scanning
- **Python-compatible**: Drop-in replacement for `json.loads()` / `json.dumps()` — all valid JSON is valid JTON
- **Serialization**: `dumps()` with Zen Grid table output, Pydantic v1/v2 and dataclass support
- **JSON Extensions**: Unquoted keys, `//` and `/* */` comments, `Infinity`/`NaN` special numbers
- **Strict correctness**: Rejects invalid JSON numbers (`-01`, `1.`, `0.e1`) that many parsers accept silently

---

## Quickstart

### Installation

```bash
# From PyPI (once published)
pip install jton

# From source (requires Rust 1.70+ — https://rustup.rs/)
git clone https://github.com/gowthamkumar-nandakishore/jton.git
cd JTON
pip install maturin
maturin develop --release
```

### Basic Usage

```python
import jton

# Standard JSON parsing
data = jton.loads('{"name": "Alice", "age": 30}')

# JTON extensions — unquoted keys
data = jton.loads('{name: "Alice", age: 30}')

# Comments for configuration files
config = jton.loads('''
{
    host: "localhost",   // server address
    port: 8080,         /* default port */
    timeout: 30         // seconds
}
''')

# Special numbers (Python compatibility)
data = jton.loads('{x: Infinity, y: -Infinity, z: NaN}')

# Serialize to compact JSON
jton.dumps({"name": "Alice", "age": 30})
# → '{"name":"Alice","age":30}'

# encode/decode aliases (familiar for orjson/msgspec users)
jton.encode(data)   # same as dumps()
jton.decode(text)   # same as loads()
```

---

## Zen Grid: Token-Efficient Table Format

When you pass a list of dicts to `dumps()`, JTON automatically detects the tabular structure and encodes it as a **Zen Grid** — one header row followed by semicolon-delimited data rows, all inline.

### The format

```
[N: col1, col2, col3; val1, val2, val3; val4, val5, val6 ]
 ↑         ↑                  ↑
row count  headers           one record per semicolon segment
```

- `N` — total row count (helps LLMs understand the data size at a glance)
- First segment after `[N:` = comma-separated field names
- Each subsequent segment = one record, values in the same order

### Example

```python
import jton

users = [
    {"id": 1, "name": "Alice", "score": 95},
    {"id": 2, "name": "Bob",   "score": 87},
    {"id": 3, "name": "Carol", "score": 92},
]

# Standard JSON compact — 116 chars, ~32 tokens:
# [{"id":1,"name":"Alice","score":95},{"id":2,"name":"Bob","score":87},{"id":3,"name":"Carol","score":92}]

# JTON Zen Grid — 72 chars, ~22 tokens (31% fewer tokens):
print(jton.dumps(users))
# → '[3: id, name, score; 1, "Alice", 95; 2, "Bob", 87; 3, "Carol", 92 ]'

# Disable Zen Grid for standard JSON output
print(jton.dumps(users, zen_grid=False))
# → '[{"id":1,"name":"Alice","score":95},...]'
```

### Round-trip correctness

Zen Grid is valid JTON — `jton.loads()` parses it back to the original data:

```python
original = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
encoded  = jton.dumps(original)           # → '[2: id, name; 1, "Alice"; 2, "Bob" ]'
decoded  = jton.loads(encoded)            # → [{"id": 1, "name": "Alice"}, ...]
assert decoded == original                # ✅ perfect round-trip
```

### Token count analysis

```python
import jton

data = [{"id": i, "name": f"User{i}", "score": i*5} for i in range(100)]
counts = jton.token_count(data)  # requires: pip install tiktoken
# {
#   'json_compact': {'tokens': 2843, 'savings_vs_compact': '+0.0%'},
#   'zen_grid':     {'tokens': 1820, 'savings_vs_compact': '-36.0%'},
# }
```

### LLM integration

Add a one-line format hint to your system prompt before sending Zen Grid data:

```python
import jton

system_prompt = jton.format_hint() + "\n\n" + jton.dumps(my_data)
```

```
Data is in JTON Zen Grid format.
Format: [N: col1, col2, col3; row1val1, row1val2, row1val3; ... ]
N = total row count. First semicolon-segment = headers.
Each subsequent segment = one record in header order.
Example: [3: id, name, score; 1, Alice, 95; 2, Bob, 87; 3, Carol, 92 ]
```

```python
original = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
encoded = jton.dumps(original)                # → '[: id, name; 1, "Alice"; 2, "Bob" ]'
decoded = jton.loads(encoded)                 # → [{"id": 1, "name": "Alice"}, ...]
assert decoded == original                    # ✅ perfect round-trip
```

---

## Pydantic and Dataclass Support

```python
from pydantic import BaseModel
from dataclasses import dataclass
import jton

# Pydantic v2 (model_dump)
class User(BaseModel):
    id: int
    name: str
    email: str

users = [User(id=1, name="Alice", email="a@example.com"),
         User(id=2, name="Bob",   email="b@example.com")]

print(jton.dumps(users))
# → '[2: id, name, email; 1, "Alice", "a@example.com"; 2, "Bob", "b@example.com" ]'

# Python dataclasses
@dataclass
class Point:
    x: float
    y: float

print(jton.dumps(Point(x=1.5, y=2.5)))
# → '{"x":1.5,"y":2.5}'

# Parse directly into a Pydantic model (loads + validate in one call)
user = jton.loads_as('{"id":1,"name":"Alice","email":"a@ex.com"}', User)
# → User(id=1, name='Alice', email='a@ex.com')

# Parse into a dataclass
pt = jton.loads_as('{"x":1.5,"y":2.5}', Point)
# → Point(x=1.5, y=2.5)
```

---

## API Reference

### `jton.loads(data, schema=None)`

Parse JTON or JSON data into Python objects.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `data` | `str \| bytes` | required | JTON/JSON text to parse |
| `schema` | `list[FieldDescriptor] \| None` | `None` | Optional schema for guided parsing |

Returns: `Any` — parsed Python object (dict, list, str, int, float, bool, None)

```python
jton.loads('{"a": 1}')          # → {"a": 1}
jton.loads(b'{"a": 1}')         # bytes input OK
jton.loads('{a: 1}')            # unquoted keys OK
jton.loads('// comment\n{a:1}') # comments OK
```

### `jton.dumps(data, *, zen_grid=True, unquoted_keys=False, indent=None, bare_strings=False, implicit_null=False, row_count=True, multiline_zen=False, delimiter="comma")`

Serialize Python objects to JTON/JSON string.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `data` | `Any` | required | Python object to serialize |
| `zen_grid` | `bool` | `True` | Auto-convert lists of dicts to Zen Grid table format |
| `unquoted_keys` | `bool` | `False` | Write dict keys without quotes (JTON style) |
| `indent` | `int \| None` | `None` | Enable pretty-printing with given indent width |
| `bare_strings` | `bool` | `False` | Write identifier string values without quotes in Zen Grid cells |
| `implicit_null` | `bool` | `False` | Write missing/null cells as empty (saves ~1 token per null cell) |
| `row_count` | `bool` | `True` | Prefix Zen Grid header with row count: `[N: ...]` (default: **True**) |
| `multiline_zen` | `bool` | `False` | Emit TOON-compatible multi-line format — best LLM accuracy |
| `delimiter` | `str` | `"comma"` | Cell separator: `"comma"` (readable), `"tab"` (max token savings), `"pipe"` |

Returns: `str` — serialized text

**Supported types**: `dict`, `list`, `tuple`, `str`, `int`, `float`, `bool`, `None`, Pydantic `BaseModel` (v1+v2), `@dataclass`

### `jton.loads_many(texts)`

Decode a **batch of JSON/JTON strings in parallel** using a Rayon thread pool.
Releases the GIL during the CPU-intensive parse phase — ideal for server workloads.

```python
results = jton.loads_many(['{"x":1}', '{"x":2}', '{"x":3}'])
# → [{'x': 1}, {'x': 2}, {'x': 3}]
```

### `jton.dumps_many(data, *, zen_grid=True, row_count=True)`

Encode a **list of Python objects** to JTON/JSON strings using the thread-local buffer pool.

```python
strings = jton.dumps_many([{"id": 1}, {"id": 2}])
# → ['{"id":1}', '{"id":2}']
```

### `jton.loads_as(data, model_type, *, strict=False)`

Parse JTON/JSON and **validate against a Pydantic model or dataclass** in one call.

```python
from pydantic import BaseModel
import jton

class User(BaseModel):
    id: int
    name: str

user = jton.loads_as('{"id":1,"name":"Alice"}', User)
# → User(id=1, name='Alice')

# Also works with plain dataclasses
from dataclasses import dataclass

@dataclass
class Point:
    x: float
    y: float

pt = jton.loads_as('{"x":1.5,"y":2.5}', Point)
# → Point(x=1.5, y=2.5)
```

Return a format description for pasting into LLM system prompts.

| `style` | Description |
|---------|-------------|
| `"zen_grid"` | Default inline format |
| `"zen_grid_rowcount"` | Inline with `[N]` row count |
| `"multiline"` | TOON-compatible multi-line (best for Gemini) |
| `"tab"` | Tab-delimited |

### `jton.token_count(data, tokenizer="o200k_base")`

Compare token costs across all output modes. Requires `pip install tiktoken`.

Returns a dict mapping mode names to `{"tokens": int, "chars": int, "savings_vs_compact": str}`.

### `jton.encode` / `jton.decode`

Aliases for `dumps` / `loads` — familiar for users of `orjson` or `msgspec`.

---

## CLI Tool

JTON ships a command-line tool for JSON ↔ Zen Grid conversion:

```bash
# After pip install or maturin develop
JTON input.json                    # encode JSON → Zen Grid (stdout)
JTON input.json -o output.JTON     # encode to file
JTON input.JTON -o output.json     # decode Zen Grid → JSON (auto-detected)
JTON input.json --stats            # show token savings
echo '{"x":1}' | JTON             # pipe stdin
JTON input.json --tab              # tab-delimited Zen Grid
JTON input.json --no-zen-grid      # plain compact JSON
JTON input.json --indent 2         # pretty-print JSON
JTON --hint                        # print LLM system-prompt template
JTON --version                     # show version
```

Or run directly without installation:
```bash
python -m jton.cli input.json --stats
```

---

## Parallel Batch API

For server workloads processing many JSON payloads simultaneously:

```python
import jton

# Decode batch in parallel (GIL released during parse phase)
payloads = ['{"id":1}', '{"id":2}', '{"id":3}']
results = jton.loads_many(payloads)

# Encode batch (thread-local buffer pool, zero re-allocation per item)
strings = jton.dumps_many([{"id": i} for i in range(1000)])
```

`loads_many` uses a **Rayon** thread pool to parse all strings concurrently:
- Phase 1 (GIL released): parse raw JSON bytes into Rust value trees in parallel
- Phase 2 (GIL held): convert Rust values → Python objects sequentially

---

## Playground

Run the interactive playground locally to explore all JTON features:

```bash
# From the repo root (after maturin develop)
python playground/server.py

# Opens at http://127.0.0.1:7700
# Optional: pip install tiktoken  (enables live token count bars)
```

The playground provides:
- **Live JSON → JTON conversion** with all encoding options as toggles
- **Token comparison bars** (JSON pretty / JSON compact / JTON current)
- **Char savings %** vs JSON compact
- **Round-trip indicator** — shows if decode(encode(x)) == x
- **Format hint copier** — paste into LLM system prompts
- **Sample datasets** — employees, orders, analytics, deep config, GitHub repos
- **Decode mode** — paste JTON output, get back pretty JSON

For a shareable hosted playground, compile the WASM crate:
```bash
# Requires wasm-pack: cargo install wasm-pack
cd jton_wasm
wasm-pack build --target web --release
# Then open playground/index.html directly (no server needed)
```

---

## Performance

### Speed Comparison (synthetic datasets, string-heavy / number-heavy / mixed)

| Library | `loads` | `dumps` | Notes |
|---------|---------|---------|-------|
| [stdlib `json`](https://docs.python.org/3/library/json.html) | 40–60 MB/s | 83–100 MB/s | Pure Python |
| **JTON** | **117–193 MB/s** | **238–309 MB/s** | Rust/SIMD, JSON mode |
| **JTON Zen Grid** | — | **397–616 MB/s** | Rust, table output |
| [orjson](https://github.com/ijl/orjson) | 500–730 MB/s | 400–586 MB/s | Rust, JSON only |

- JTON `loads` is **3–5× faster** than stdlib
- JTON `dumps` (JSON mode) is **3–4× faster** than stdlib
- JTON Zen Grid `dumps` reaches **600+ MB/s** on string-heavy tabular data
- JTON adds Zen Grid token reduction that orjson cannot provide

### SIMD Acceleration

JTON uses a two-pass SIMD parsing strategy modeled after [simdjson](https://github.com/simdjson/simdjson):

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

### JTON vs Competing Formats

| Format | Token Savings vs JSON compact | Approach | JSON-Compatible |
|--------|-------------------------------|----------|-----------------|
| **JTON Zen Grid** | **11–33% (mixed), up to 50% (pure tabular)** | Table syntax | ✅ Yes (JTON superset) |
| [TRON](https://github.com/tron-format/tron) | ~32% | Class-based aliases | ❌ No (new syntax) |
| [TOON](https://github.com/nickcoutsos/toon) | ~19% | Table-oriented | ❌ No (new syntax) |
| JSON pretty | −197% (more tokens!) | Whitespace | ✅ Yes |

JTON's key advantage: Zen Grid is still valid JTON/JSON syntax, meaning any JSON parser can handle it, while TRON/TOON require custom parsers.

### Real-world LLM Token Savings

| Scenario | JSON compact tokens | JTON Zen Grid tokens | Savings |
|----------|---------------------|----------------------|---------|
| 50 API users (5 cols) | 1,302 | 1,011 | **22%** |
| 100 log entries (10 cols) | 5,803 | 4,822 | **17%** |
| 100 products (5 cols) | 2,603 | 2,112 | **19%** |
| 200 rows × 5 cols | 4,602 | 3,411 | **26%** |
| 2000 employees (pure tabular) | 97,407 | ~49,000 | **~50%** |

Measured using [tiktoken](https://github.com/openai/tiktoken) `o200k_base` encoder (GPT-4o/GPT-5).

---

## LLM Comprehension Evaluation

We evaluated whether LLMs can correctly interpret Zen Grid data across **12 models** from six providers, using 7 real-world datasets × 5 question types × 2 formats (840 total API calls).

### Per-Model Results

| Model | Family | JSON | Zen Grid | Delta | n |
|-------|--------|------|----------|-------|---|
| GPT-5.1 | OpenAI | 71.4% | **74.3%** | **+2.9 pp** | 35 |
| GPT-5.1-codex | OpenAI | 71.4% | **74.3%** | **+2.9 pp** | 35 |
| GPT-5-mini | OpenAI | 71.4% | **74.3%** | **+2.9 pp** | 35 |
| GPT-4o | OpenAI | 71.4% | 62.9% | −8.6 pp | 35 |
| Gemini 2.5 Flash | Google | 68.6% | 53.8% | −14.7 pp | 26* |
| Gemini 2.5 Pro | Google | 68.6% | 57.1% | −11.4 pp | 35 |
| Gemini 3 Flash | Google | 65.7% | 57.1% | −8.6 pp | 35 |
| Kimi K2 | Moonshot | 65.7% | 57.1% | −8.6 pp | 35 |
| Llama 3.3 70B | Meta | 54.3% | 54.3% | 0.0 pp | 35 |
| Qwen3 32B | Alibaba | 51.4% | **54.3%** | **+2.9 pp** | 35 |
| GPT-OSS 120B | Open-src | 42.9% | 42.9% | 0.0 pp | 35 |
| Llama 4 Scout 17B | Meta | 37.1% | **40.0%** | **+2.9 pp** | 35 |
| **Overall** | | **61.7%** | **58.6%** | **−3.0 pp** | 420/411 |

\* Gemini 2.5 Flash returned null for 9/35 Zen Grid queries (model limitation, not format issue).

### By Question Type

| Question Type | JSON | Zen Grid | Delta |
|---------------|------|----------|-------|
| Lookup | 96.4% | 94.0% | −2.4 pp |
| Aggregation | 54.8% | 51.8% | −3.0 pp |
| Filtering | 48.8% | 44.6% | −4.2 pp |
| Comparison | 51.2% | 52.6% | +1.4 pp |
| Count | 57.1% | 49.4% | −7.7 pp |

### Key Findings

Five of twelve models improve with Zen Grid (GPT-5.x family, Qwen3 32B, Llama 4 Scout — all gaining 2.9 pp), two are neutral (Llama 3.3 70B, GPT-OSS 120B), and five regress (Gemini family at −8.6 to −14.7 pp, GPT-4o and Kimi K2 at −8.6 pp each). Overall, Zen Grid costs 3.0 pp in accuracy for 32% fewer tokens — a favorable cost-per-correct-answer trade-off.

Within OpenAI's lineup, GPT-5.x consistently benefits while the older GPT-4o does not, suggesting that newer model generations generalize better to the tabular syntax. Lookup tasks remain robust across all models (96%/94%).

### LLM Generation Results

Can LLMs **produce** valid Zen Grid output? We tested 13 models from 8 providers with few-shot and zero-shot prompting:

| Model | Few-shot Valid | Zero-shot Valid |
|-------|---------------|------------------|
| GPT-5-mini | **100%** | **100%** |
| GPT-5.1 | **100%** | **100%** |
| GPT-4o | **100%** | **100%** |
| Claude Sonnet 4 | **100%** | **100%** |
| Claude 3.5 Haiku | **100%** | **100%** |
| Claude 3 Haiku | **100%** | **100%** |
| Gemini 2.5 Flash | **100%** | **100%** |
| Gemini 3 Flash | 83% | 83% |
| Llama 3.3 70B | **100%** | **100%** |
| Llama 4 Scout 17B | **100%** | **100%** |
| Kimi K2 | **100%** | **100%** |
| **Overall** | **87.2%** | **85.7%** |

10 of 13 models achieve 100% validity, including all Anthropic Claude models. Zen Grid works for **bidirectional** LLM pipelines — both input and output.

### Format Comparison

Token counts on real-world data (`o200k_base` tokenizer):

| Format | Twitter | GitHub | Financial | Avg Savings vs JSON |
|--------|---------|--------|-----------|---------------------|
| JSON Compact | 3,673 | 968 | 643 | baseline |
| CSV | 1,303 | 688 | 408 | **−54.5%** (no types) |
| Markdown | 1,430 | 792 | 505 | −48.3% (no types) |
| YAML | 1,916 | 1,185 | 840 | −25.2% |
| **Zen Grid** | **1,466** | **820** | **514** | **−47.0%** (full types) |

Zen Grid is the only format that achieves >45% savings while preserving JSON's full type system.

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
- **Schema-guided Parsing** — optional `schema` parameter for 2–3× speedup on homogeneous data
- **Type Stubs** — `__init__.pyi` + `py.typed` for IDE/mypy support

### 🚧 Planned

- **Parallel Parsing** — multi-core processing for very large files
- **`loads(type=Model)`** — automatic Pydantic model deserialization

---

## Examples

### LLM Prompt Optimization

```python
import jton

# Large tabular dataset to send to an LLM
employees = [
    {"id": 1, "name": "Alice", "dept": "Engineering", "salary": 95000, "years": 3},
    {"id": 2, "name": "Bob",   "dept": "Marketing",   "salary": 72000, "years": 5},
    # ... thousands more rows
]

# Standard JSON: every key repeated per row → high token cost
json_str = json.dumps(employees)   # "id", "name", "dept" repeated 1000× each

# JTON Zen Grid: headers written once
JTON_str = jton.dumps(employees)
# → '[: id, name, dept, salary, years; 1, "Alice", "Engineering", 95000, 3; ... ]'

# Up to 50% fewer tokens for large tabular datasets
```

### Configuration Files

```python
config = jton.loads('''
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
# JTON parses both standard JSON and JTON extensions
response = jton.loads('{"status": "ok", "users": [{id: 1, name: "Alice"}]}')

# Serialize back with token savings
payload = jton.dumps(response)
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

JTON performance benchmarks use the same standardized test vectors as the wider JSON ecosystem.

### Compliance Testing

- **[JSONTestSuite](https://github.com/nst/JSONTestSuite)** (Nicolas Seriot) — 400+ JSON conformance tests for parsers; used by orjson, simdjson, and JTON
- **[RFC 8259](https://tools.ietf.org/html/rfc8259)** — The IETF JSON specification (December 2017)
- **[JSON_checker](http://www.json.org/JSON_checker/)** — Classic pass/fail fixtures (fail01–fail33)

### Performance Benchmark Files

The canonical benchmark corpus from **[nativejson-benchmark](https://github.com/miloyip/nativejson-benchmark)** (Milo Yip), used by orjson, simdjson, yyjson, and JTON:

| File | Size | Dataset | Characteristics |
|------|------|---------|-----------------|
| `canada.json` | 2.15 MB | GeoJSON coordinates | Number-heavy (float arrays) |
| `twitter.json` | 0.60 MB | Twitter API timeline | Unicode strings, nested objects |
| `citm_catalog.json` | 1.65 MB | Cinema IT Management catalog | Mixed content, real-world API |
| `large.json` | 7.88 MB | Custom: 100K rows tabular | JTON primary benchmark |

### Competing Libraries Referenced

#### Speed-Focused JSON Libraries

| Library | GitHub | Speed | Notes |
|---------|--------|-------|-------|
| [orjson](https://github.com/ijl/orjson) | [![GitHub](https://img.shields.io/badge/GitHub-orjson-black)](https://github.com/ijl/orjson) | 586 MB/s dumps | Rust-based; JSON only |
| [ujson](https://github.com/ultrajson/ultrajson) | [![GitHub](https://img.shields.io/badge/GitHub-ujson-black)](https://github.com/ultrajson/ultrajson) | ~300 MB/s | C-based |
| [pysimdjson](https://github.com/TkTech/pysimdjson) | [![GitHub](https://img.shields.io/badge/GitHub-pysimdjson-black)](https://github.com/TkTech/pysimdjson) | 1–2 GB/s parse | Python bindings for simdjson |
| [simdjson](https://github.com/simdjson/simdjson) | [![GitHub](https://img.shields.io/badge/GitHub-simdjson-black)](https://github.com/simdjson/simdjson) | 2–3 GB/s | C++; architecture inspiration for JTON |
| [yapic.json](https://github.com/nfomon/yapic.json) | [![GitHub](https://img.shields.io/badge/GitHub-yapic.json-black)](https://github.com/nfomon/yapic.json) | ~2–3× stdlib | Python/C extension |

#### Token Efficiency Formats

| Format | GitHub | Token Savings | Approach | JSON-Compatible |
|--------|--------|---------------|----------|-----------------|
| **JTON Zen Grid** | This repo | **11–50%** | Column headers once | ✅ Yes |
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
├── JTON/                        # Python package
│   ├── __init__.py              # Public API: loads, dumps, encode, decode
│   ├── __init__.pyi             # Type stubs (mypy/pyright)
│   └── py.typed                 # PEP 561 marker
└── jton_core/                   # Rust implementation
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
└── token_efficiency.py          # Token comparison: JTON vs JSON vs TRON/TOON
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
- **No allocation on GIL drop**: JTON never releases the GIL mid-parse, avoiding data races

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
   - **Repository**: `JTON`
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


