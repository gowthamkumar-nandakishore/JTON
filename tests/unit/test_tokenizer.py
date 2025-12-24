import pytest

from src.tokenizer import ParseError, Tokenizer


def collect_types(source: str):
    return [t.type for t in Tokenizer(source).tokens()]


def collect_lexemes(source: str):
    return [t.lexeme for t in Tokenizer(source).tokens()]


def test_tokenizer_skips_comments_and_whitespace():
    tokens = list(Tokenizer("// comment\n{ /*b*/ }"))
    assert [t.type for t in tokens] == ["LBRACE", "RBRACE"]


def test_tokenizer_detects_table_open_and_mode_switch():
    tokens = list(Tokenizer("[: a, b ]"))
    assert tokens[0].type == "TABLE_OPEN"
    assert tokens[0].mode == "TABLE"
    assert tokens[-1].type == "RBRACKET"


def test_tokenizer_literal_precedence():
    tokens = list(Tokenizer("true, false, null"))
    assert [t.type for t in tokens if t.type != "COMMA"] == ["BOOLEAN", "BOOLEAN", "NULL"]
    assert [t.value for t in tokens if t.type != "COMMA"] == [True, False, None]


def test_tokenizer_unquoted_with_spaces_allowed():
    tokens = list(Tokenizer("[: name; Alice Smith ]"))
    lexemes = [t.lexeme for t in tokens if t.type == "IDENT"]
    assert "Alice Smith" in lexemes


def test_tokenizer_invalid_unterminated_string():
    with pytest.raises(ParseError):
        list(Tokenizer('"oops'))
