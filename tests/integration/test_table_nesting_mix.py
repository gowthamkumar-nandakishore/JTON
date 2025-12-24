from src.parser import parse_string


def test_table_inside_object_with_nested_cells():
    text = '{"table": [: name, meta; "a", {"k": [1,2]}; "b", {"k": [3,4]} ]}'
    parsed = parse_string(text)
    assert parsed["table"][1]["meta"] == {"k": [3, 4]}
