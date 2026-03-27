# JTON

**JTON (JSON Tabular Object Notation)** — A high-performance, token-efficient JSON superset built in Rust with PyO3 bindings for Python. Home of **Zen Grid**, a token-aware tabular encoding that reduces LLM token costs by 15–60%.

[![Tests](https://img.shields.io/badge/tests-683%20passing-brightgreen)](./tests/)
[![Performance](https://img.shields.io/badge/loads-193%20MB%2Fs-green)](#performance)
[![SIMD](https://img.shields.io/badge/SIMD-AVX2%20%2B%20AVX--512-blue)](#simd-acceleration)
[![License](https://img.shields.io/badge/license-MIT-blue)](./LICENSE)

---

## Overview

JTON is a JSON superset designed for LLM applications and high-throughput data processing:

- **Zen Grid**: Tabular encoding reduces token count by **15–60%** on benchmarked data vs JSON compact (23% average across 6 datasets, ~60% on highly-tabular Twitter-style rows)
- **LLM-Validated**: 10 models tested for comprehension, 13 models tested for generation -- all achieve 100% generation validity (100% few-shot, 100% zero-shot)
- **SIMD Acceleration**: AVX2 (32-byte) and AVX-512 (64-byte) structural scanning
- **JSON-compatible**: supports `load()` / `loads()` / `dump()` / `dumps()` for common JSON workflows — all valid JSON is valid JTON
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

## Using JTON with existing `json`-based code

JTON works well with existing JSON-heavy codebases — with one important rule:

- **Parsing is the easy win**: `jton.load()` / `jton.loads()` accept normal JSON unchanged
- **Serialization is JSON-compatible for common usage**, but JTON's serializer has an extra default: `zen_grid=True`
- That means if you simply replace `import json` with `import jton as json`, some `list[dict]` payloads may serialize as **Zen Grid** instead of strict RFC 8259 JSON

### What happens if you just replace `json` with `jton`?

```python
import jton as json

# Existing JSON input still works
obj = json.loads('{"name":"Alice","age":30}')

# Existing file APIs still work
with open("data.json") as f:
    obj = json.load(f)
```

For output:

```python
import jton as json

json.dumps({"name": "Alice", "age": 30})
# -> '{"name":"Alice","age":30}'   # still normal JSON

json.dumps([
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"},
])
# -> '[2: id, name; 1, "Alice"; 2, "Bob" ]'   # JTON Zen Grid, not strict JSON
```

So the practical behavior is:

- **`load()` / `loads()`**: safe replacement for existing JSON parsing
- **`dump()` / `dumps()`** on ordinary objects: usually still emits JSON
- **`dump()` / `dumps()`** on homogeneous arrays of objects: may emit **Zen Grid** by default

### Recommended migration path

#### 1. Parsing-only replacement

If you want a no-risk first step, replace only parsing:

```python
import jton

data = jton.loads(existing_json_text)
```

This gives you faster parsing plus JTON extensions on input, without changing output format anywhere.

#### 2. Full json-module replacement, but keep strict JSON output

If you want `import jton as json`, but still need normal JSON output:

```python
import jton as json

text = json.dumps(obj, zen_grid=False)
with open("out.json", "w") as f:
    json.dump(obj, f, zen_grid=False)
```

This is the safest pattern for APIs, files, and systems that expect standard JSON.

#### 3. Enable JTON only where it helps

Use strict JSON for machines, and JTON for LLM-facing payloads:

```python
api_payload = jton.dumps(data, zen_grid=False)   # strict JSON
llm_payload = jton.dumps(data)                   # JTON / Zen Grid when eligible
```

### JSON-in / JSON-out compatibility cheat sheet

If you want output that stays valid JSON, use:

```python
jton.dumps(
    obj,
    zen_grid=False,
    unquoted_keys=False,
    bare_strings=False,
    implicit_null=False,
    multiline_zen=False,
)
```

Notes:

- **Only `zen_grid=False` is required** for strict JSON output in normal use
- `row_count` and `delimiter` matter **only** when `zen_grid=True`
- `indent=2` or `indent=4` still gives valid pretty JSON
- `default=` works like `json.dumps(default=...)`

### When output stops being strict JSON

These options move you out of plain JSON output:

- `zen_grid=True` on homogeneous `list[dict]` values
- `unquoted_keys=True`
- `multiline_zen=True`
- `bare_strings=True` inside Zen Grid cells
- `implicit_null=True` inside Zen Grid cells

So the short rule is:

- **Use `jton.loads()` everywhere**
- **Use `jton.dumps(..., zen_grid=False)` anywhere strict JSON is required**
- **Use default `jton.dumps()` for LLM/token-optimized payloads**

### Current compatibility scope

JTON supports the common Python JSON workflow:

- `load`
- `loads`
- `dump`
- `dumps`
- `default=...`
- file objects

It is **not** a byte-for-byte clone of every stdlib `json` keyword argument yet. Think of it as:

- **fully compatible parser for JSON input**
- **mostly compatible serializer for common usage**
- **plus opt-in JTON/Zen Grid output when you want it**

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
encoded = jton.dumps(original)                # → '[2: id, name; 1, "Alice"; 2, "Bob" ]'
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

# Parse directly into a Pydantic model
user_data = jton.loads('{"id":1,"name":"Alice","email":"a@ex.com"}')
user = User(**user_data)
# → User(id=1, name='Alice', email='a@ex.com')

# Parse into a dataclass
pt_data = jton.loads('{"x":1.5,"y":2.5}')
pt = Point(**pt_data)
# → Point(x=1.5, y=2.5)
```

---

## API Reference

JTON provides the core `load`, `dump`, `loads`, and `dumps` APIs used in common JSON workflows. The main behavioral difference is that `dumps()` defaults to `zen_grid=True`, which may emit JTON Zen Grid for homogeneous arrays of objects.

### `jton.loads(data, schema=None)`

Parse JTON or JSON data into Python objects.

```python
jton.loads('{"a": 1}')          # → {"a": 1}
jton.loads(b'{"a": 1}')         # bytes input OK
jton.loads('{a: 1}')            # unquoted keys OK
jton.loads('// comment\n{a:1}') # comments OK
```

### `jton.load(fp)`

Parse JTON/JSON from a **file object** — compatible with normal `json.load()` usage.

```python
with open("data.json") as f:
    data = jton.load(f)
```

### `jton.dumps(data, *, zen_grid=True, ..., default=None)`

Serialize Python objects to JTON/JSON string — compatible with common `json.dumps()` usage.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `data` | `Any` | required | Python object to serialize |
| `zen_grid` | `bool` | `True` | Auto-convert lists of dicts to Zen Grid table format |
| `unquoted_keys` | `bool` | `False` | Write dict keys without quotes |
| `indent` | `int \| None` | `None` | Pretty-print with given indent width |
| `bare_strings` | `bool` | `False` | Write identifier string values without quotes in cells |
| `implicit_null` | `bool` | `False` | Write null cells as empty (saves ~1 token per cell) |
| `row_count` | `bool` | `True` | Prefix Zen Grid header with `[N: ...]` row count |
| `delimiter` | `str` | `"comma"` | `"comma"` (readable), `"tab"` (max savings), `"pipe"` |
| `default` | `callable \| None` | `None` | For non-serializable objects, same as `json.dumps(default=...)` |

If you want **strict JSON output**, set `zen_grid=False`.

```python
# Standard usage
jton.dumps({"a": 1}, zen_grid=False)         # → '{"a":1}'

# Custom types with default=
from datetime import date
jton.dumps({"d": date(2025,1,1)}, default=str)
# → '{"d":"2025-01-01"}'

# Works with Zen Grid too
jton.dumps([{"id":1,"d":date(2025,1,1)}], default=str)
# → '[1: id, d; 1, "2025-01-01" ]'
```

**Supported types natively**: `dict`, `list`, `tuple`, `str`, `int`, `float`, `bool`, `None`, Pydantic `BaseModel` (v1+v2), `@dataclass`

### `jton.dump(obj, fp, **kwargs)`

Serialize to a **file object** — compatible with common `json.dump()` usage.

```python
with open("out.jton", "w") as f:
    jton.dump(data, f)
```

### `jton.format_hint(style="zen_grid")`

Return a format description for pasting into LLM system prompts.

| `style` | Description |
|---------|-------------|
| `"zen_grid"` | Default inline format (mentions both `[:` and `[N:` forms) |
| `"zen_grid_rowcount"` | Inline with explicit `[N]` row count |
| `"multiline"` | Multi-line format |
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

---

## Performance

### Speed Comparison (real-world files: canada.json 2.25 MB, citm_catalog.json 1.78 MB, twitter.json 0.65 MB)

| Library | `loads` | `dumps` (JSON mode) | Notes |
|---------|---------|---------------------|-------|
| [stdlib `json`](https://docs.python.org/3/library/json.html) | 63–184 MB/s | 46–268 MB/s | Pure Python/C |
| **JTON** | **132–346 MB/s** | **197–276 MB/s** | Rust/SIMD, JSON mode |
| **JTON Zen Grid** | — | **81–240 MB/s** | Rust, table output |
| [orjson](https://github.com/ijl/orjson) | 235–458 MB/s | 440–533 MB/s | Rust, JSON only |

- JTON `loads` is **1.5–2.1× faster** than stdlib (`json.loads`)
- JTON `dumps` JSON mode is **1.0–4.3× faster** than stdlib
- JTON Zen Grid `dumps` saves **14–60% tokens** (depending on data shape) while maintaining competitive throughput
- orjson is faster on raw JSON; JTON's advantage is Zen Grid token reduction which orjson cannot provide

### Large-file static benchmark: `akbe_doc_classifier.json` (338.1 MB)

Measured on this machine using the repository's `akbe_doc_classifier.json` payload in JSON-compatible mode (`zen_grid=False` for JTON dump):

| Operation | stdlib `json` | JTON | Result |
|-----------|---------------|------|--------|
| Parse / decode | **1.75 s** (193.5 MB/s) | 2.43 s (138.9 MB/s) | stdlib faster on this file |
| Dump / encode | 1.78 s (57.3 MB/s) | **0.81 s** (126.5 MB/s) | **JTON 2.2× faster** |

Notes:

- This file is a large, object-heavy classifier payload rather than a tabular Zen Grid sweet spot
- On this benchmark, JTON wins strongly on **dump/encode**
- Stdlib `json` wins on **parse/decode** for this specific file shape
- Output benchmarking used JSON-compatible serialization (`jton.dumps(..., zen_grid=False)`)

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

Benchmarked on 6 real-world datasets using tiktoken `o200k_base` encoder:

| Format | Total Tokens | vs JSON compact | JSON-Compatible |
|--------|-------------|-----------------|-----------------|
| [TRON](https://github.com/tron-format/tron) | 122,097 | **−32.4%** | ❌ No (new syntax) |
| **JTON Zen Grid** | **144,159** | **−20.2%** | ✅ Yes (JTON superset) |
| [TOON](https://github.com/nickcoutsos/toon) | 146,113 | −19.2% | ❌ No (new syntax) |
| JSON compact | 180,725 | — | ✅ Yes |

**JTON is #2 most token-efficient** and the **only JSON-superset format in the top 3** — TRON and TOON require custom parsers.

### Real-world LLM Token Savings

| Dataset | JSON compact | JTON Zen Grid | Savings |
|---------|-------------|---------------|---------|
| 👥 2,000 employees (7 cols) | 97,407 | 77,226 | **−20.7%** |
| 📈 365 days analytics | 14,240 | 10,604 | **−25.5%** |
| ⭐ 100 GitHub repos | 11,729 | 9,626 | **−17.9%** |
| 🛒 500 orders (nested) | 46,381 | 39,565 | **−14.7%** |
| 🧾 300 event logs (semi-uniform) | 10,745 | 6,915 | **−35.6%** |

---

## LLM Comprehension Evaluation

We evaluated whether LLMs can correctly interpret Zen Grid data across **10 models** from six providers, using 7 real-world datasets × 5 question types × 2 formats (700 total API calls). Uses JTON 1.0 `[N: ...]` syntax with `bare_strings=True`.

### Per-Model Results

| Model | Family | JSON | Zen Grid | Delta | n |
|-------|--------|------|----------|-------|---|
| GPT-5.1-codex | OpenAI | 74.3% | 71.4% | −2.9 pp | 35 |
| GPT-5.1 | OpenAI | 71.4% | 62.9% | −8.6 pp | 35 |
| GPT-5-mini | OpenAI | 71.4% | 71.4% | 0.0 pp | 35 |
| Gemini 3 Pro Preview | Google | 68.6% | 68.6% | 0.0 pp | 35 |
| Kimi K2 | Moonshot | 62.9% | **68.6%** | **+5.7 pp** | 35 |
| Qwen3 32B | Alibaba | 60.0% | 57.1% | −2.9 pp | 35 |
| Llama 3.3 70B | Meta | 54.3% | 54.3% | 0.0 pp | 35 |
| Llama 3.1 8B | Meta | 45.7% | **48.6%** | **+2.9 pp** | 35 |
| GPT-OSS 120B | Open-src | 42.9% | **45.7%** | **+2.9 pp** | 35 |
| Llama 4 Scout 17B | Meta | 40.0% | **45.7%** | **+5.7 pp** | 35 |
| **Overall** | | **59.1%** | **59.4%** | **+0.3 pp** | 350 |

### By Question Type

| Question Type | JSON | Zen Grid | Delta |
|---------------|------|----------|-------|
| Lookup | 95.7% | 95.7% | 0.0 pp |
| Filtering | 52.9% | 51.4% | −1.4 pp |
| Count | 51.4% | 48.6% | −2.9 pp |
| Aggregation | 47.1% | 51.4% | +4.3 pp |
| Comparison | 48.6% | 50.0% | +1.4 pp |

### Key Findings

Four of ten models improve with Zen Grid (Kimi K2 +5.7pp, Llama 4 Scout +5.7pp, Llama 3.1 8B +2.9pp, GPT-OSS 120B +2.9pp), three are neutral (GPT-5-mini, Gemini 3 Pro, Llama 3.3 70B), and three regress (GPT-5.1 −8.6pp being the worst). Overall, Zen Grid is **+0.3 pp** ahead of JSON for ~20% fewer tokens — a clear win on cost-per-correct-answer. Lookup tasks (95.7%) are perfectly preserved across formats.

### LLM Generation Results

Can LLMs **produce** valid Zen Grid output? We tested 13 models from 7 providers with few-shot and zero-shot prompting on the JTON 1.0 `[N: ...]` syntax:

| Model | Few-shot Valid | Zero-shot Valid |
|-------|---------------|------------------|
| GPT-5-mini (WTG) | **100%** | **100%** |
| GPT-5-mini (Azure) | **100%** | **100%** |
| GPT-5.1 | **100%** | **100%** |
| GPT-4o | **100%** | **100%** |
| Claude Sonnet 4 | **100%** | **100%** |
| Claude 3.5 Haiku | **100%** | **100%** |
| Claude 3 Haiku | **100%** | **100%** |
| Gemini 2.5 Flash | **100%** | **100%** |
| Gemini 2.5 Pro | **100%** | **100%** |
| Gemini 3 Flash Preview | **100%** | **100%** |
| Llama 3.3 70B | **100%** | **100%** |
| Llama 4 Scout 17B | **100%** | **100%** |
| Kimi K2 | **100%** | **100%** |
| **Overall** | **100%** | **100%** |

All 13 models achieve 100% validity in both modes. Zen Grid works for **bidirectional** LLM pipelines — both input and output.

### Format Comparison

Token counts on real-world data (`o200k_base` tokenizer):

| Format | Twitter | GitHub | Financial | Avg Savings vs JSON |
|--------|---------|--------|-----------|---------------------|
| JSON Compact | 3,673 | 968 | 643 | baseline |
| CSV | 1,303 | 688 | 408 | **−43.3%** (no types) |
| Markdown | 1,430 | 792 | 505 | −33.6% (no types) |
| YAML | 1,916 | 1,185 | 840 | +1.7% |
| **Zen Grid** | **1,653** | **968** | **516** | **−24.9%** (full types) |

**Zen Grid is the only JSON-compatible format that achieves significant token savings while preserving JSON's full type system.**

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
├── jton/                        # Python package (pip install jton)
│   ├── __init__.py              # Public API: loads, dumps, encode, decode, token_count
│   ├── __init__.pyi             # Type stubs (mypy/pyright)
│   ├── cli.py                   # jton CLI entry point
│   └── py.typed                 # PEP 561 marker
└── jton_core/                   # Rust implementation
    └── src/
        ├── lib.rs               # PyO3 module: loads(), dumps(), format_hint()
        ├── serializer.rs        # Zen Grid + JSON serializer, AVX-512 escape path
        ├── types/               # StructuralIndex, FieldDescriptor
        ├── simd/                # AVX2 / AVX-512 structural scanners
        └── parser/              # SIMD indexed parser, string_cache, number parsing

tests/
├── test_json_compatibility.py   # JSON spec conformance
├── test_zen_grid.py             # Zen Grid encoding/decoding + CLI
└── test_reference_vectors.py    # JSONTestSuite corpus (600+ vectors)

benchmarks/
├── run_all_benchmarks.py        # Token efficiency benchmark (8 formats × 6 datasets)
└── results/token_efficiency.md  # Latest benchmark results
```

---

## Language Support

**JTON officially supports Python only.**

The SIMD-accelerated parser (AVX2/AVX-512 structural scanning, VPSHUFB nibble classifier, thread-local string cache) is a PyO3 native extension. The performance advantage is inseparable from the Python binding. The format spec is in [`SPEC.md`](./SPEC.md) for anyone who wants to implement JTON in another language.

| Language | Status | Install |
|----------|--------|---------|
| **Python 3.11+** | ✅ Official | `pip install jton` |
| All others | — | Implement from `SPEC.md` |

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


