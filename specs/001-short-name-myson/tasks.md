---

description: "Tasks for MYSON parser implementation"
---

# Tasks: MYSON Parser Specification

**Input**: Design documents from `/specs/001-short-name-myson/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included per user story (unit + integration) to satisfy constitution and FRs.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Constitution Alignment (must be reflected in generated tasks)

- Keep spec/grammar.ebnf in sync with tokenizer/parser changes.
- Enforce JSON superset compatibility, unquoted ASCII-alphanumeric keys, Zen Grid tables, C-style comments, literal precedence for true/false/null, and MAX_NESTING_DEPTH=100.
- Tokenizer main loop MUST be a state machine (no regex); parser MUST be recursive descent with depth guard.
- Tests MUST cover empty tables, header arity (null fill, extra drop), trailing delimiters, nested mixes, comments, unquoted spacing/escaping, and depth overflow.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project layout (src/, tests/) with placeholders in src/tokenizer.py, src/parser.py, tests/unit/, tests/integration/
- [X] T002 Configure pytest settings and minimal pyproject.toml in repo root for test discovery

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

- [X] T003 Author base grammar in spec/grammar.ebnf covering JSON superset, table open/close, row/col delimiters, comments, and literal precedence
- [X] T004 [P] Define Token, ParseError, and ParserState (with max_depth=100) structures in src/tokenizer.py and src/parser.py
- [X] T005 [P] Implement tokenizer state machine in src/tokenizer.py (JSON mode, Table mode, comments, unquoted keys/strings with escaping, literal detection)
- [X] T006 [P] Scaffold recursive descent parser skeleton with depth tracking in src/parser.py
- [X] T007 Establish shared test fixtures and utilities in tests/conftest.py
- [X] T008 Seed baseline tokenizer tests for JSON tokens, comment stripping, and mode transitions in tests/unit/test_tokenizer.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Parse JSON and simple MYSON tables (Priority: P1) 🎯 MVP

**Goal**: Parse JSON and flat table arrays with header/value mapping.

**Independent Test**: Parsing valid JSON and a single-level table returns correct Python dict/list structures with headers mapped to values.

### Tests for User Story 1

- [X] T009 [P] [US1] Add JSON parity tests (primitives, arrays, objects) in tests/unit/test_parser_json_parity.py
- [X] T010 [P] [US1] Add flat table tests with exact arity and simple strings in tests/unit/test_parser_flat_table.py
- [X] T011 [P] [US1] Add integration test combining JSON document and single table in tests/integration/test_json_and_table_basic.py

### Implementation for User Story 1

- [X] T012 [P] [US1] Implement JSON value parsing (objects, arrays, strings, numbers, booleans, null) in src/parser.py
- [X] T013 [P] [US1] Implement table detection and header/value mapping (exact arity) in src/parser.py
- [X] T014 [US1] Wire tokenizer/parser integration and comment handling flow in src/parser.py and src/tokenizer.py
- [X] T015 [US1] Update spec/grammar.ebnf for any adjustments from implementation feedback

**Checkpoint**: User Story 1 fully functional and independently testable

---

## Phase 4: User Story 2 - Nested structures inside tables (Priority: P2)

**Goal**: Support nested objects/arrays inside table cells while ignoring table delimiters inside nested scopes.

**Independent Test**: Tables with nested JSON values parse correctly; commas/semicolons inside nested structures do not split rows/columns.

### Tests for User Story 2

- [X] T016 [P] [US2] Add nested table cell cases (objects/arrays) in tests/unit/test_parser_table_nesting.py
- [X] T017 [P] [US2] Add integration test with mixed nested tables and JSON wrappers in tests/integration/test_table_nesting_mix.py

### Implementation for User Story 2

- [X] T018 [P] [US2] Extend tokenizer to respect nested structure boundaries in Table mode in src/tokenizer.py
- [X] T019 [US2] Implement recursive parsing of nested cells, ignoring row/col delimiters inside nested scopes in src/parser.py
- [X] T020 [US2] Update spec/grammar.ebnf to reflect nested cell allowances and delimiter shielding

**Checkpoint**: User Story 2 fully functional and independently testable

---

## Phase 5: User Story 3 - Robust errors and edge handling (Priority: P3)

**Goal**: Deterministic errors and edge behavior: jagged rows (null fill, extra drop), invalid unquoted strings, trailing delimiters, and depth limits.

**Independent Test**: Malformed inputs surface precise errors; benign trailing delimiters are tolerated; depth overflow is blocked with a clear ParseError.

### Tests for User Story 3

- [X] T021 [P] [US3] Add jagged row cases (null fill, extra drop) in tests/unit/test_parser_table_arity.py
- [X] T022 [P] [US3] Add invalid unquoted string and key cases (punctuation/Unicode) in tests/unit/test_parser_unquoted_errors.py
- [X] T023 [P] [US3] Add trailing delimiter tolerance/violation cases in tests/unit/test_parser_trailing_delimiters.py
- [X] T024 [P] [US3] Add max-depth overflow cases in tests/unit/test_parser_depth_guard.py
- [X] T025 [P] [US3] Add integration test exercising combined edge scenarios in tests/integration/test_edge_behaviors.py

### Implementation for User Story 3

- [X] T026 [P] [US3] Implement jagged row handling (null padding, extra drop) with arity checks in src/parser.py
- [X] T027 [P] [US3] Enforce unquoted string/key validation and escaping rules in src/tokenizer.py
- [X] T028 [US3] Implement trailing delimiter tolerance and error reporting with line/column in src/parser.py
- [X] T029 [US3] Enforce MAX_NESTING_DEPTH=100 with ParseError on overflow in src/parser.py
- [X] T030 [US3] Finalize error formatting (category, lexeme, hint) and ensure tokenizer supplies positions in src/tokenizer.py and src/parser.py
- [X] T031 [US3] Update spec/grammar.ebnf if edge handling adjusts productions

**Checkpoint**: User Story 3 fully functional and independently testable

---

## Phase N: Polish & Cross-Cutting Concerns

- [X] T032 [P] Add CLI demo entrypoint in src/cli/__init__.py (myson-parse) matching contracts/api.md
- [X] T033 [P] Update docs in specs/001-short-name-myson/quickstart.md with final examples and CLI usage
- [X] T034 Add coverage for empty tables and mixed comments in tests/unit/test_parser_table_comments.py
- [X] T035 Perform refactor/cleanup and ensure spec/grammar.ebnf, src/tokenizer.py, src/parser.py stay in sync
- [ ] T036 Add performance benchmark in benchmarks/performance_test.py generating a 5MB mixed JSON/table MYSON file and assert parse time <3s on reference 4-core/8GB machine
- [ ] T037 Add token/byte savings analysis in benchmarks/token_savings_analysis.py comparing JSON vs MYSON (Zen table) representations

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → User Stories (Phase 3/4/5) → Polish.
- User stories proceed in priority order (P1 then P2 then P3), but P2/P3 can start after Phase 2 if P1 is staffed separately.
- Tests in each story should be authored before implementation within that story.

## Parallel Execution Examples

- User Story 1: Run T009, T010, T011 in parallel; in implementation, T012 and T013 can proceed concurrently, then T014.
- User Story 2: T016 and T017 in parallel; T018 and T019 can proceed concurrently once tests are in place.
- User Story 3: T021–T024 in parallel; T026–T030 can be split by tokenizer vs parser ownership after tests exist.

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Complete Phase 1 and Phase 2.
2. Deliver User Story 1 (JSON parity + flat tables) and validate independently.

### Incremental Delivery
1. Foundation done → US1 (MVP) → US2 (nested tables) → US3 (edge/error hardening).
2. Keep grammar/tokenizer/parser/tests synchronized after each story.

### Parallel Team Strategy
- After foundation, split by user story or by tokenizer vs parser/test roles; adhere to [P] markings to avoid file contention.
