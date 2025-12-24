# Research Notes: MYSON Parser

## Unquoted strings may include spaces
- Decision: Allow spaces in unquoted strings; reserved delimiters still require escaping or quoting.
- Rationale: Improves table readability and authoring ergonomics while keeping delimiter safety.
- Alternatives considered: Require escaping spaces (rejected for ergonomics); disallow spaces (forces quoting and reduces compactness).

## Extra table columns beyond headers
- Decision: Drop/ignore extra cells beyond header count per row.
- Rationale: Avoids failure for occasional overlong rows and prevents schema drift while keeping output arity stable.
- Alternatives considered: Hard error on extra cells (rejected for flexibility); spillover map for extras (adds complexity and non-uniform schema).

## Literal precedence (true/false/null)
- Decision: Classify bare `true`/`false`/`null` as literals before treating them as unquoted strings.
- Rationale: Preserves JSON parity and avoids surprising stringification; keeps tokenizer deterministic.
- Alternatives considered: Treat as strings unless quoted (breaks JSON superset); mode-dependent heuristics (adds ambiguity and inconsistency).
