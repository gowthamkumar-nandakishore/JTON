<!--
Sync Impact Report:
- Version: 1.0.0 -> 1.1.0
- Modified principles: Zen Grid Table Arrays (Resilience Update)
- Added sections: none
- Removed sections: none
- Templates requiring updates: none
- Follow-ups: none
-->

# MYSON Constitution

## Core Principles

### I. JSON Superset Fidelity (NON-NEGOTIABLE)
Every valid JSON document MUST parse as-is under MYSON with identical semantics and data types.
No extension (comments, unquoted keys, tables) may introduce ambiguity or break JSON compatibility.
Error messaging MUST clearly distinguish JSON violations from MYSON-only violations to protect
backward compatibility.

### II. Unquoted Alphanumeric Keys
Object keys MAY omit quotes only when composed of ASCII letters and digits; quoted keys remain
accepted. The tokenizer MUST reject keys containing punctuation, whitespace, or Unicode when
unquoted. Key ordering and duplicates follow standard JSON semantics.

### III. Zen Grid Table Arrays
Table arrays use `[:` to open, `]` to close, `;` for row separation, and `,` for column separation.
The first row defines headers. Subsequent rows MUST match header arity; missing cells are filled
with null and extra cells are silently dropped to ensure LLM-resilience. Nested objects or lists
inside a cell MUST be parsed as atomic values, ignoring internal commas or semicolons. Empty tables
are allowed and yield an empty list.

### IV. Comment Support
C-style line (`//`) and block (`/* ... */`) comments are accepted wherever whitespace is valid and
MUST be removed prior to semantic parsing. Comments inside string literals are forbidden. Line and
column tracking MUST remain accurate after comment stripping.

### V. Deterministic Parser Discipline
Tokenization uses an explicit state machine (no regex-driven main loop) with modes for JSON,
strings, numbers, comments, and table arrays. Parsing is recursive descent that preserves
structure, emits precise errors with line/column, and resists exponential blowups on nested input.
Tests MUST pin behavior for empty tables, trailing commas, deeply nested mixes of JSON and tables,
and comment interactions.

## Implementation Constraints & Deliverables
- Python implementation targeting the active toolchain for this repo; use only deterministic,
	library-free parsing in the core loop.
- Authoritative grammar lives in spec/grammar.ebnf and MUST stay in sync with tokenizer and parser.
- Tokenizer implementation resides in src/tokenizer.py and follows the state-machine discipline.
- Recursive descent parser resides in src/parser.py and outputs Python dicts/lists with JSON fidelity
	plus table array semantics.
- Tests in tests/ MUST cover JSON superset compatibility, unquoted key boundaries, Zen Grid table
	arrays (including nesting and empty tables), comment handling, and trailing delimiter cases.

## Development Workflow & Quality Gates
- Constitution Check precedes design and coding: prove JSON compatibility is preserved, unquoted key
	constraints are enforced, table array semantics are covered, comments do not alter semantics, and
	tokenizer/parser discipline is respected.
- Test-first: add failing cases for grammar updates (JSON parity, tables, comments, edge nesting),
	then implement, then refactor while keeping grammar.ebnf synchronized.
- Each change MUST document impacts on grammar, tokenizer states, and parser productions in the
	relevant plan/spec/tasks artifacts before merge.

## Governance
- This constitution is the authoritative contract for MYSON. Conflicts with other docs resolve in
	favor of this file.
- Amendments require an explicit PR note, updated grammar/test coverage, and a semantic version bump
	here. Backward-incompatible governance or principle changes bump MAJOR; new principles or material
	expansions bump MINOR; clarifications bump PATCH.
- Compliance review is required on every PR touching grammar, tokenizer, parser, or tests; reviewers
	must confirm Constitution Check items are satisfied and cite relevant test additions.

**Version**: 1.1.0 | **Ratified**: 2025-12-23 | **Last Amended**: 2025-12-24
