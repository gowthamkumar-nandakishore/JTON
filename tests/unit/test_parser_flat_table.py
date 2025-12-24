from src.parser import parse_string


def test_parses_flat_table_exact_arity():
    data = parse_string('[: h1, h2; v1, v2 ]')
    assert data == [{"h1": "v1", "h2": "v2"}]


def test_empty_table_returns_empty_list():
    assert parse_string('[: ]') == []
