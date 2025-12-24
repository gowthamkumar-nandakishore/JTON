import pytest

from src.parser import ParseError, parse_string


def test_trailing_semicolon_and_comma_are_tolerated():
    data = parse_string('[: h1, h2; v1, v2, ; ]')
    assert data == [{"h1": "v1", "h2": "v2"}]


def test_stray_delimiter_errors():
    with pytest.raises(ParseError):
        parse_string('[: h1, h2 v1 v2 ]')
