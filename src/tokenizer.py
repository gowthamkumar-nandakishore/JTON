"""Deterministic tokenizer for MYSON (JSON superset with tables and comments)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Generator, Iterable, Iterator, Optional


@dataclass
class Token:
    """Lexical token with location metadata."""

    type: str
    lexeme: str
    line: int
    column: int
    value: Optional[object] = None
    mode: str = "JSON"  # JSON or TABLE for context


class ParseError(Exception):
    """Parser/tokenizer error with category and source location."""

    def __init__(
        self,
        category: str,
        message: str,
        line: int,
        column: int,
        lexeme: str | None = None,
        mode: str = "JSON",
        hint: str | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.message = message
        self.line = line
        self.column = column
        self.lexeme = lexeme
        self.mode = mode
        self.hint = hint

    def __str__(self) -> str:  # pragma: no cover - trivial formatting
        base = f"{self.category} error at line {self.line}, col {self.column}: {self.message}"
        if self.lexeme:
            base += f" (lexeme: {self.lexeme})"
        if self.hint:
            base += f" | hint: {self.hint}"
        return base


class Tokenizer:
    """Deterministic state-machine tokenizer."""

    def __init__(self, source: str) -> None:
        self.source = source
        self.length = len(source)
        self.index = 0
        self.line = 1
        self.column = 1

    def _peek(self, offset: int = 0) -> str | None:
        pos = self.index + offset
        if pos >= self.length:
            return None
        return self.source[pos]

    def _advance(self) -> str | None:
        if self.index >= self.length:
            return None
        ch = self.source[self.index]
        self.index += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _starts_comment(self) -> bool:
        return self._peek() == "/" and self._peek(1) in {"/", "*"}

    def _skip_comment(self) -> None:
        if self._peek(1) == "/":
            # line comment
            while (ch := self._advance()) not in {None, "\n"}:
                continue
            return
        # block comment
        self._advance()  # /
        self._advance()  # *
        while True:
            ch = self._advance()
            if ch is None:
                raise ParseError(
                    "lexical",
                    "Unterminated block comment",
                    self.line,
                    self.column,
                    lexeme=None,
                )
            if ch == "*" and self._peek() == "/":
                self._advance()
                break

    def _consume_string(self) -> Token:
        start_line, start_col = self.line, self.column
        buf: list[str] = []
        self._advance()  # opening quote
        while True:
            ch = self._advance()
            if ch is None:
                raise ParseError("lexical", "Unterminated string", start_line, start_col, lexeme="\"")
            if ch == "\\":
                nxt = self._advance()
                if nxt is None:
                    raise ParseError("lexical", "Unterminated escape", self.line, self.column, lexeme="\\")
                buf.append("\\" + nxt)
                continue
            if ch == "\"":
                break
            buf.append(ch)
        literal = "\"" + "".join(buf) + "\""
        try:
            value = json.loads(literal)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise ParseError("lexical", "Invalid string escape", start_line, start_col, lexeme=literal) from exc
        return Token("STRING", literal, start_line, start_col, value=value)

    def _consume_number(self) -> Token:
        start_line, start_col = self.line, self.column
        buf: list[str] = []
        while True:
            ch = self._peek()
            if ch is None or ch not in "0123456789+-.eE":
                break
            buf.append(self._advance())
        literal = "".join(buf)
        try:
            value = json.loads(literal)
        except json.JSONDecodeError:
            raise ParseError("lexical", "Invalid number", start_line, start_col, lexeme=literal)
        return Token("NUMBER", literal, start_line, start_col, value=value)

    def _consume_unquoted(self) -> Token:
        start_line, start_col = self.line, self.column
        buf: list[str] = []
        while True:
            ch = self._peek()
            if ch is None:
                break
            if ch in {",", ";", "]", "}", ":", "[", "{", "\n"}:
                break
            if ch == "/" and self._peek(1) in {"/", "*"}:
                break
            if ch == "\\":
                self._advance()
                next_ch = self._advance()
                if next_ch is None:
                    raise ParseError("lexical", "Dangling escape", self.line, self.column, lexeme="\\")
                buf.append(next_ch)
                continue
            buf.append(self._advance())
        lexeme = "".join(buf).strip()
        if lexeme == "":
            raise ParseError("lexical", "Empty unquoted token", start_line, start_col, lexeme="")
        # literal precedence
        if lexeme in {"true", "false"}:
            return Token("BOOLEAN", lexeme, start_line, start_col, value=(lexeme == "true"))
        if lexeme == "null":
            return Token("NULL", lexeme, start_line, start_col, value=None)
        return Token("IDENT", lexeme, start_line, start_col, value=lexeme)

    def tokens(self) -> Iterable[Token]:
        mode = "JSON"
        while self.index < self.length:
            ch = self._peek()
            if ch is None:
                break
            if ch.isspace():
                self._advance()
                continue
            if self._starts_comment():
                self._skip_comment()
                continue
            if ch == "{" :
                yield Token("LBRACE", ch, self.line, self.column, mode=mode)
                self._advance()
                continue
            if ch == "}":
                yield Token("RBRACE", ch, self.line, self.column, mode=mode)
                self._advance()
                continue
            if ch == "[":
                if self._peek(1) == ":":
                    yield Token("TABLE_OPEN", "[:", self.line, self.column, mode="TABLE")
                    self._advance()
                    self._advance()
                    mode = "TABLE"
                    continue
                yield Token("LBRACKET", ch, self.line, self.column, mode=mode)
                self._advance()
                continue
            if ch == "]":
                yield Token("RBRACKET", ch, self.line, self.column, mode=mode)
                self._advance()
                mode = "JSON"
                continue
            if ch == ":":
                yield Token("COLON", ch, self.line, self.column, mode=mode)
                self._advance()
                continue
            if ch == ",":
                yield Token("COMMA", ch, self.line, self.column, mode=mode)
                self._advance()
                continue
            if ch == ";":
                yield Token("SEMICOLON", ch, self.line, self.column, mode=mode)
                self._advance()
                continue
            if ch == "\\":
                # Backslash must be part of an escape in an unquoted token
                token = self._consume_unquoted()
                token.mode = mode
                yield token
                continue
            if ch == "\"":
                token = self._consume_string()
                token.mode = mode
                yield token
                continue
            if ch in "-0123456789":
                token = self._consume_number()
                token.mode = mode
                yield token
                continue
            # Unquoted identifier/value
            token = self._consume_unquoted()
            token.mode = mode
            yield token

    def __iter__(self) -> Iterator[Token]:  # pragma: no cover - delegating helper
        return iter(self.tokens())
