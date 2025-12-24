import pytest

from src.parser import ParseError, parse_string


def test_depth_guard_triggers():
    nested = "[" * 101 + "]" * 101
    with pytest.raises(ParseError):
        parse_string(nested)
