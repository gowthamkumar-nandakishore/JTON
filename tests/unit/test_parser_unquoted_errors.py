import pytest

from src.parser import ParseError, parse_string


def test_invalid_unquoted_key_rejected():
    with pytest.raises(ParseError):
        parse_string('{bad-key: 1}')


def test_literal_precedence_over_unquoted_strings():
    data = parse_string('{"t": true, "s": false, "n": null}')
    assert data == {"t": True, "s": False, "n": None}
