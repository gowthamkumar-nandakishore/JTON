from src.parser import parse_string


def test_jagged_rows_pad_and_drop():
    data = parse_string('[: a, b, c; 1, 2; 3, 4, 5, 6 ]')
    assert data == [
        {"a": 1, "b": 2, "c": None},
        {"a": 3, "b": 4, "c": 5},
    ]
