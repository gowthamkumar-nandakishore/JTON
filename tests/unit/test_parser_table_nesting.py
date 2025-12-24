from src.parser import parse_string


def test_nested_values_inside_table_cells():
    text = '[: name, meta; "a", {"k": [1,2]}; "b", {"k": [3,4]} ]'
    data = parse_string(text)
    assert data == [
        {"name": "a", "meta": {"k": [1, 2]}},
        {"name": "b", "meta": {"k": [3, 4]}},
    ]
