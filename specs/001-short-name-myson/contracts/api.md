# Contract: MYSON Parser Library/CLI

## Library API (Python)

### parse_string(source: str) -> Any
- Input: MYSON text.
- Output: Python dict/list/primitive; table arrays become list[dict].
- Errors: Raises ParseError with category, line, column, lexeme, hint.
- Behavior: Single-pass; honors JSON parity; supports unquoted ASCII-alnum keys, comments, Zen Grid tables with null padding and dropped extras; literal precedence for true/false/null.

### parse_file(path: str, encoding: str = "utf-8") -> Any
- Input: File path to MYSON text.
- Output/Errors: Same as parse_string.
- Behavior: Streaming-friendly reading; same semantics as parse_string.

## CLI (optional demo)

### Command
```
myson-parse <path> [--ast-json]
```
- Reads file, prints parsed Python-JSON representation.
- Exit codes: 0 on success; non-zero on parse/token errors.
- Flags: `--ast-json` outputs JSON serialization of the parsed result.

## Error Schema (ParseError)
- category: enum [lexical, syntax, arity]
- message: string
- line: int (1-based)
- column: int (1-based)
- lexeme: string (offending token excerpt, if available)
- mode: enum [JSON, TABLE]
- hint: string (optional)
