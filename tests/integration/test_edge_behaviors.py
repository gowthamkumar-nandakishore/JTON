import pytest

from src.parser import ParseError, parse_string


def test_combined_edge_cases():
    text = '[: h1, h2; 1, 2, ; 3; 4, 5 ]'
    parsed = parse_string(text)
    assert parsed == [
        {"h1": 1, "h2": 2},
        {"h1": 3, "h2": None},
        {"h1": 4, "h2": 5},
    ]


def test_invalid_cell_raises():
    with pytest.raises(ParseError):
        parse_string('[: h1; {] } ]')
