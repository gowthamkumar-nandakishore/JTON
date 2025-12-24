# Feature Specification: MYSON Parser Specification

**Feature Branch**: `001-short-name-myson`  
**Created**: 2025-12-23  
**Status**: Draft  
**Input**: User description: "Draft a technical specification for the MYSON Parser covering tokenizer, table parsing, schema inference, errors, performance."

## Clarifications

### Session 2025-12-23

- Q: Can unquoted strings include spaces without escaping? → A: Yes; spaces are allowed unescaped while reserved delimiters still require escaping or quoting.
- Q: How to handle extra columns beyond headers in a table row? → A: Extra columns are ignored/dropped silently.
- Q: Do literals true/false/null win over strings? → A: Yes; recognize bare `true`/`false`/`null` as literals before treating as strings.

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Parse JSON and simple MYSON tables (Priority: P1)

A developer can feed valid JSON or a flat MYSON table array and receive equivalent Python
structures (dicts/lists) with schema inferred from the first row of the table.

**Why this priority**: Establishes JSON superset fidelity and baseline table support, enabling
immediate utility and backward compatibility.

**Independent Test**: Provide a JSON document and a single-level table array; verify outputs match
expected dicts/lists and table rows map headers to values.

**Acceptance Scenarios**:

1. **Given** valid JSON with comments removed, **When** parsed, **Then** output equals the JSON
  semantic tree (types preserved).
2. **Given** a table array `[: h1, h2; v1, v2 ]`, **When** parsed, **Then** output is
  `[{"h1": "v1", "h2": "v2"}]`.

---

### User Story 2 - Nested structures inside tables (Priority: P2)

A developer can embed objects or arrays inside table cells, and the parser correctly nests them
while ignoring table delimiters inside the nested structures.

**Why this priority**: Unlocks mixed JSON/table documents for compact LLM-friendly data formats.

**Independent Test**: Provide a table with cells containing nested arrays/objects; verify the nested
structures are parsed via the JSON parser and attached to each row correctly.

**Acceptance Scenarios**:

1. **Given** `[: name, meta; "a", { "k": [1,2] }; "b", { "k": [3,4] }]`, **When** parsed,
  **Then** output is `[{"name": "a", "meta": {"k": [1,2]}}, {"name": "b", "meta": {"k": [3,4]}}]`.
2. **Given** nested structures containing commas/semicolons, **When** parsed, **Then** table row and
  column boundaries are unaffected by delimiters inside the nested scopes.

---

### User Story 3 - Robust errors and edge handling (Priority: P3)

A developer receives deterministic, line/column-specific errors for jagged tables, illegal unquoted
keys/strings, and unsupported trailing delimiters while the parser still accepts benign trailing
commas/semicolons.

**Why this priority**: Ensures production-grade reliability and debuggability at scale.

**Independent Test**: Supply malformed inputs (header/value arity mismatches, bad unquoted strings,
unterminated structures) and verify precise error locations and recovery behavior; supply inputs
with trailing delimiters to ensure they are ignored.

**Acceptance Scenarios**:

1. **Given** a table with a shorter row than headers, **When** parsed, **Then** missing cells are
  filled with `null` and parsing continues for that row.
2. **Given** an unquoted key containing punctuation, **When** parsed, **Then** parsing fails with an
  error that includes line and column.

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

Capture the MYSON-specific boundaries at minimum:

- JSON compatibility for numbers, strings, escapes, and deeply nested arrays/objects.
- Unquoted key handling for ASCII alphanumeric names and rejection of punctuation/Unicode.
- Zen Grid tables: header arity enforcement, nested object/list cells, empty tables, delimiter
  collisions with strings.
- Comment handling (`//`, `/* */`) including adjacency to values and prohibition inside strings.
- Trailing commas around tables, arrays, objects, and mixed with comments.
- Jagged rows in tables and how missing cells are filled with null.
- Table headers containing reserved characters when quoted vs unquoted.
- Unquoted string escaping for reserved delimiters inside table cells or object values.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Parser MUST accept all valid JSON with identical semantics and data types.
- **FR-002**: Parser MUST accept unquoted object keys composed solely of ASCII alphanumerics; all
  other unquoted keys MUST be rejected with clear errors.
- **FR-003**: Parser MUST support Zen Grid table arrays (`[: ... ]`) with header arity enforcement and
  nested value protection.
- **FR-004**: Parser MUST support `//` and `/* */` comments wherever whitespace is valid without
  altering line/column fidelity.
- **FR-005**: Tokenizer MUST use a state-machine main loop (no regex) and feed a recursive descent
  parser; outputs MUST be Python dicts/lists.
- **FR-006**: Lexer MUST track modes: JSON Mode (default) and Table Mode; `[:` transitions into Table
  Mode, `]` exits; row delimiters are `;`, column delimiters are `,` only while in Table Mode.
- **FR-007**: While in Table Mode, encountering `{` or `[` MUST delegate to the JSON parser recursively
  and ignore `,`/`;` within that nested scope until closed.
- **FR-008**: Table schema inference: tokens before the first `;` define headers; subsequent rows map
  to headers positionally; missing cells in a row MUST be filled with `null`; extra cells are
  ignored/dropped.
- **FR-009**: Trailing commas and semicolons immediately before closing `]` or `}` or end-of-row MUST
  be ignored; other stray delimiters MUST raise a syntax error with location.
- **FR-010**: Unquoted string values MAY include spaces without escaping; reserved delimiters are
  allowed only when escaped with a backslash (`,` `;` `]` `}` `:` `[` `{` `"` `\\`); otherwise they MUST be
  rejected; quoted strings follow JSON escaping rules unchanged.
- **FR-011**: Error reporting MUST include line and column and the offending lexeme/category for
  invalid tokens, arity mismatches, unterminated structures, or illegal unquoted strings.
- **FR-012**: Performance MUST be single-pass O(n) in input size without exponential blowups on nested
  tables/objects; streaming-friendly design (no full backtracking) is required.
- **FR-013**: Lexer MUST classify bare `true`/`false`/`null` as literals before considering them as
  unquoted strings, to preserve JSON parity and avoid surprising stringification.
- **FR-014**: Parser MUST enforce a MAX_NESTING_DEPTH of 100 (objects, arrays, tables combined) and
  raise a ParseError with line/column when exceeded to avoid RecursionErrors.

*Assumptions (implicit unless revised later):*

- Maximum practical input size: up to 10 MB per document for performance targets.
- Error messages include: "line X, col Y: <category> - <hint>" with the offending token excerpt when
  available.
- Streaming requirement allows buffered I/O but no random-access backtracking beyond one token of
  lookahead.

### Key Entities *(include if feature involves data)*

- **Token**: Carries type, lexeme, line, column, mode (JSON/Table), and trivia flags for comments.
- **TableRow**: Represents a single parsed row with header-aligned values (with null fills for missing
  cells) and original line references.
- **ParseError**: Contains category (lexical, syntax, arity), message, line, column, offending
  lexeme, and mode context.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes
- **SC-001**: 100% of valid JSON corpus samples parse identically to standard JSON output (types and
  values) with no additional errors.
- **SC-002**: Table inference produces correct header/value alignment for at least 50 diverse cases
  (including empty tables and nested values) with zero mismatches.
- **SC-003**: Error reports for malformed inputs pinpoint the offending location within ±1 column and
  include a category in 100% of negative test cases.
- **SC-004**: Parsing throughput sustains O(n) behavior with at least 5 MB of mixed JSON/table data
  processed in under 3 seconds on a reference machine, with memory usage remaining linear to input
  size.
