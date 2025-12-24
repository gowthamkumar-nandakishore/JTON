"""Recursive descent parser for the MYSON format."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, List, Optional

from .tokenizer import ParseError, Token, Tokenizer


MAX_NESTING_DEPTH = 100


@dataclass
class ParserState:
    current_depth: int = 0
    max_depth: int = MAX_NESTING_DEPTH
    mode: str = "JSON"
    headers: Optional[list[str]] = None


class Parser:
    def __init__(self, tokens: Iterable[Token]) -> None:
        self.tokens: List[Token] = list(tokens)
        self.index = 0
        self.state = ParserState()

    def _peek(self) -> Optional[Token]:
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index]

    def _advance(self) -> Token:
        token = self._peek()
        if token is None:
            raise ParseError("syntax", "Unexpected end of input", 0, 0)
        self.index += 1
        return token

    def _enter(self) -> None:
        self.state.current_depth += 1
        if self.state.current_depth > self.state.max_depth:
            tok = self._peek() or Token("", "", 0, 0)
            raise ParseError(
                "syntax",
                f"Exceeded max nesting depth {self.state.max_depth}",
                tok.line,
                tok.column,
            )

    def _exit(self) -> None:
        self.state.current_depth -= 1

    def parse(self) -> Any:
        value = self._parse_value()
        if self._peek() is not None:
            tok = self._peek()
            raise ParseError("syntax", "Trailing content after document", tok.line, tok.column, tok.lexeme)
        return value

    def _expect(self, expected: str) -> Token:
        tok = self._advance()
        if tok.type != expected:
            raise ParseError("syntax", f"Expected {expected}", tok.line, tok.column, tok.lexeme)
        return tok

    def _parse_value(self) -> Any:
        tok = self._peek()
        if tok is None:
            raise ParseError("syntax", "Unexpected end of input", 0, 0)
        if tok.type == "LBRACE":
            return self._parse_object()
        if tok.type == "LBRACKET":
            return self._parse_array()
        if tok.type == "TABLE_OPEN":
            return self._parse_table()
        if tok.type == "STRING":
            self._advance()
            return tok.value
        if tok.type == "NUMBER":
            self._advance()
            return tok.value
        if tok.type == "BOOLEAN":
            self._advance()
            return tok.value
        if tok.type == "NULL":
            self._advance()
            return None
        if tok.type == "IDENT":
            self._advance()
            return tok.value
        raise ParseError("syntax", f"Unexpected token {tok.type}", tok.line, tok.column, tok.lexeme)

    def _parse_object(self) -> dict[str, Any]:
        self._enter()
        self._expect("LBRACE")
        obj: dict[str, Any] = {}
        if self._peek() and self._peek().type == "RBRACE":
            self._advance()
            self._exit()
            return obj
        while True:
            key_token = self._peek()
            if key_token is None:
                raise ParseError("syntax", "Unterminated object", 0, 0)
            if key_token.type == "IDENT":
                if not key_token.lexeme.isalnum():
                    raise ParseError("lexical", "Unquoted keys must be ASCII alphanumerics", key_token.line, key_token.column, key_token.lexeme)
            elif key_token.type != "STRING":
                raise ParseError("syntax", "Expected string or unquoted key", key_token.line, key_token.column, key_token.lexeme)
            key = key_token.value if key_token.type == "STRING" else key_token.lexeme
            self._advance()
            self._expect("COLON")
            value = self._parse_value()
            obj[key] = value
            tok = self._peek()
            if tok is None:
                raise ParseError("syntax", "Unterminated object", 0, 0)
            if tok.type == "COMMA":
                self._advance()
                nxt = self._peek()
                if nxt and nxt.type == "RBRACE":
                    self._advance()
                    break
                continue
            if tok.type == "RBRACE":
                self._advance()
                break
            raise ParseError("syntax", "Expected ',' or '}'", tok.line, tok.column, tok.lexeme)
        self._exit()
        return obj

    def _parse_array(self) -> list[Any]:
        self._enter()
        self._expect("LBRACKET")
        items: list[Any] = []
        if self._peek() and self._peek().type == "RBRACKET":
            self._advance()
            self._exit()
            return items
        while True:
            items.append(self._parse_value())
            tok = self._peek()
            if tok is None:
                raise ParseError("syntax", "Unterminated array", 0, 0)
            if tok.type == "COMMA":
                self._advance()
                nxt = self._peek()
                if nxt and nxt.type == "RBRACKET":
                    self._advance()
                    break
                continue
            if tok.type == "RBRACKET":
                self._advance()
                break
            raise ParseError("syntax", "Expected ',' or ']'", tok.line, tok.column, tok.lexeme)
        self._exit()
        return items

    def _parse_table(self) -> list[dict[str, Any]]:
        self._enter()
        opener = self._advance()
        if opener.type != "TABLE_OPEN":
            raise ParseError("syntax", "Expected table opener", opener.line, opener.column)
        headers: list[str] = []
        rows: list[list[Any]] = []

        # header row (may be empty)
        if self._peek() and self._peek().type == "RBRACKET":
            self._advance()
            self._exit()
            return []

        headers = self._parse_table_row(is_header=True)
        rows.append(headers)

        while True:
            tok = self._peek()
            if tok is None:
                raise ParseError("syntax", "Unterminated table", 0, 0)
            if tok.type == "SEMICOLON":
                self._advance()
                # Allow trailing semicolons
                if self._peek() and self._peek().type == "RBRACKET":
                    self._advance()
                    break
                if self._peek() and self._peek().type != "RBRACKET":
                    row = self._parse_table_row(is_header=False)
                    rows.append(row)
                continue
            if tok.type == "RBRACKET":
                self._advance()
                break
            # Data rows without leading semicolon (after header)
            row = self._parse_table_row(is_header=False)
            rows.append(row)
            continue

        header_values = rows[0]
        data_rows = rows[1:]
        result: list[dict[str, Any]] = []
        for data in data_rows:
            filled = list(data)[: len(header_values)]
            if len(filled) < len(header_values):
                filled.extend([None] * (len(header_values) - len(filled)))
            row_obj = {header_values[i]: filled[i] for i in range(len(header_values))}
            result.append(row_obj)
        self._exit()
        return result

    def _parse_table_row(self, is_header: bool) -> list[Any]:
        values: list[Any] = []
        while True:
            tok = self._peek()
            if tok is None:
                raise ParseError("syntax", "Unterminated table row", 0, 0)
            if tok.type in {"SEMICOLON", "RBRACKET"} and not is_header:
                break
            if tok.type == "RBRACKET" and is_header:
                break
            values.append(self._parse_table_cell(is_header))
            tok = self._peek()
            if tok is None:
                raise ParseError("syntax", "Unterminated table row", 0, 0)
            if tok.type == "COMMA":
                self._advance()
                # permit trailing comma before row end
                nxt = self._peek()
                if nxt and nxt.type in {"SEMICOLON", "RBRACKET"}:
                    continue
                continue
            if tok.type in {"SEMICOLON", "RBRACKET"}:
                break
            raise ParseError("syntax", "Expected ',' or row boundary", tok.line, tok.column, tok.lexeme)
        return values

    def _parse_table_cell(self, is_header: bool) -> Any:
        tok = self._peek()
        if tok is None:
            raise ParseError("syntax", "Unexpected end of table cell", 0, 0)
        if tok.type == "IDENT" and is_header:
            self._advance()
            if not tok.lexeme.isalnum():
                raise ParseError("lexical", "Header must be ASCII alphanumerics when unquoted", tok.line, tok.column, tok.lexeme)
            return tok.lexeme
        if tok.type in {"IDENT", "STRING", "NUMBER", "BOOLEAN", "NULL"}:
            return self._parse_value()
        if tok.type in {"LBRACE", "LBRACKET", "TABLE_OPEN"}:
            return self._parse_value()
        raise ParseError("syntax", "Invalid table cell", tok.line, tok.column, tok.lexeme)


def parse_string(source: str) -> Any:
    """Parse MYSON from a string."""

    tokens = Tokenizer(source).tokens()
    parser = Parser(tokens)
    return parser.parse()


def parse_file(path: str | Path, encoding: str = "utf-8") -> Any:
    """Parse MYSON from a file path."""

    with open(Path(path), "r", encoding=encoding) as handle:
        return parse_string(handle.read())
