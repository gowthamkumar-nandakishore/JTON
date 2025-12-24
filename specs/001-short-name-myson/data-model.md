# Data Model: MYSON Parser

## Entities

### Token
- Fields: type (enum: brace, bracket, colon, comma, semicolon, table_open, table_close, string, number, boolean, null, identifier, comment), lexeme, line, column, mode (JSON|TABLE), value (parsed primitive when applicable), trivia (comment/whitespace flags).
- Relationships: Produced by tokenizer; consumed by parser.
- Validation: Line/column must advance monotonically; mode reflects origin context; literals true/false/null classified as boolean/null tokens before string fallback.

### TableRow
- Fields: headers (list of strings), values (list of any), line_origin (line where row starts), arity (int).
- Relationships: Built by parser when in TABLE mode; uses headers inferred from first row.
- Validation: Missing values padded with null to header length; extra values dropped; nested objects/lists preserved.

### AST Nodes (JSON-compatible)
- Object: ordered mapping of string keys to Node values.
- Array: ordered list of Node values.
- Value: number | string | boolean | null | Object | Array.
- Relationships: Parser outputs standard Python dict/list equivalents for these nodes; TableRow values feed into list[dict].

### ParseError
- Fields: category (lexical|syntax|arity), message, line, column, lexeme, mode_context (JSON|TABLE), hint.
- Relationships: Emitted on fatal parse/tokenization errors.
- Validation: Line/column must reference offending token/character; category set consistently.

### ParserState
- Fields: current_depth (int), max_depth (int, default 100), mode (JSON|TABLE), header_context (list
	of strings for active table), position (line/column trackers as needed).
- Relationships: Maintained by parser to enforce nesting constraints and context-aware behavior.
- Validation: Increment depth on entering object/array/table, decrement on exit; raise ParseError
	when current_depth exceeds max_depth.

## Derived Structures

- Parsed Document: Any JSON value or table array resulting in a Python dict/list; table arrays always produce list[dict].
- Headers: List[str] captured from first row of a table; reused for subsequent rows.
