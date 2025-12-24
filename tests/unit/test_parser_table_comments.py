from src.parser import parse_string


def test_empty_table():
    assert parse_string('[: ]') == []


def test_comments_inside_table_are_ignored():
    text = '[: h1, h2; /*c*/ 1, // row value\n 2 ]'
    parsed = parse_string(text)
    assert parsed == [{"h1": 1, "h2": 2}]
