from src.parser import parse_string


def test_mixed_json_and_table_document():
    text = '{"meta": 1, "data": [: h1, h2; v1, v2 ]}'
    parsed = parse_string(text)
    assert parsed["meta"] == 1
    assert parsed["data"] == [{"h1": "v1", "h2": "v2"}]
