# MYSON

**A high-efficiency, LLM-resilient JSON superset featuring Zen Grid tables.**

---

## Quickstart

### Setup
1. Ensure Python 3.11 available on Linux.
2. Create venv: `python -m venv .venv && source .venv/bin/activate`.
3. Install dev deps (pytest only): `pip install -U pip pytest`.

### Usage
**Parse string (REPL):**
```python
from src.parser import parse_string
print(parse_string('[: h1, h2; v1, v2 ]'))
```

**Parse file:**
```bash
python -m src.cli path/to/file.myson
```

### Examples
**Table with nesting:**
```myson
[: name, meta; "a", {"k": [1,2]}; "b", {"k": [3,4]}]
```

**Trailing delimiters tolerated:**
```myson
[: h1, h2; v1, v2, ; ]
```

**Unquoted spaces allowed:**
```myson
[: name; Alice Smith ]
```

---

## Features

- **Zen Grid Tables**: A compact, delimiter-lite syntax for dense tabular data (`[: header; row ]`).
- **C-Style Comments**: Support for `// line` and `/* block */` comments.
- **Unquoted Alphanumeric Keys**: Cleaner syntax for object keys (e.g., `{ key: "value" }`).
- **Recursive Depth Guard**: Built-in protection against deeply nested structures.

## Safety & Resilience

MYSON is designed for production safety and resilience against LLM-generated content:

- **Recursive Depth Guard**: Enforces `MAX_NESTING_DEPTH=100` to prevent stack overflow attacks or runaway recursion.
- **Lenient Arity**: The "Extra Column Drop" policy automatically handles table rows with more cells than headers, ensuring robust parsing even when LLMs hallucinate extra fields.

## API Reference

### `parse_string`
```python
def parse_string(source: str) -> Any:
    """Parse MYSON from a string."""
```

### `parse_file`
```python
def parse_file(path: str | Path, encoding: str = "utf-8") -> Any:
    """Parse MYSON from a file path."""
```

## Performance & Research

MYSON is engineered for high performance, sustaining **$O(n)$ single-pass parsing**.

- **Benchmark**: Parses 5MB of data in under 3 seconds on reference hardware.
- **Analysis**: See our [Technical Paper](specs/001-short-name-myson/technical-paper.md) for detailed token savings and byte reduction analysis.

## Project Metadata

### License
This project is licensed under the **MIT License** (or Apache 2.0, as applicable).

### Contributing
Please refer to the [Constitution](.specify/memory/constitution.md) for contribution guidelines and project governance.
