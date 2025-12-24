# Quickstart: MYSON Parser

## Setup
1. Ensure Python 3.11 available on Linux.
2. Create venv: `python -m venv .venv && source .venv/bin/activate`.
3. Install dev deps (pytest only): `pip install -U pip pytest`.

## Run parser (when implemented)
- Parse string (REPL):
```python
from src.parser import parse_string
print(parse_string('[: h1, h2; v1, v2 ]'))
```
- Parse file:
```bash
python -m src.cli path/to/file.myson
```

## Test
- Run unit/integration suite:
```bash
pytest
```

## Examples
- Table with nesting:
```
[: name, meta; "a", {"k": [1,2]}; "b", {"k": [3,4]}]
```
- Trailing delimiters tolerated:
```
[: h1, h2; v1, v2, ; ]
```
- Unquoted spaces allowed:
```
[: name; Alice Smith ]
```
