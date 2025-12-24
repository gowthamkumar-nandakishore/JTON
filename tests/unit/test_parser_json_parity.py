from src.parser import parse_string


def test_parses_json_object():
    data = parse_string('{"a": 1, "b": [2, 3]}')
    assert data == {"a": 1, "b": [2, 3]}


def test_parses_json_array_with_trailing_comma():
    data = parse_string('[1, 2, 3,]')
    assert data == [1, 2, 3]
