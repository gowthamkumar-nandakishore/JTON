import pytest
import json
import myson
from hypothesis import given, strategies as st

def test_simple_types():
    cases = [
        "true", "false", "null",
        "123", "-123", "12.34", "1e5",
        '"string"', '"escaped \\" quote"',
        "[]", "{}",
        "[1, 2, 3]",
        '{"key": "value"}',
        '{"nested": [1, 2, {"k": "v"}]}'
    ]
    for case in cases:
        assert myson.loads(case) == json.loads(case)

def test_zen_grid_output():
    data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    zen = myson.dumps(data, zen=True)
    assert zen.startswith("[:")
    assert zen.endswith("]")
    # Parse back
    assert myson.loads(zen) == data

@given(st.recursive(
    st.none() | st.booleans() | st.floats(allow_nan=False, allow_infinity=False) | st.text(),
    lambda children: st.lists(children) | st.dictionaries(st.text(), children)
))
def test_hypothesis_json(data):
    # Dump with json, load with myson
    s = json.dumps(data)
    try:
        loaded = myson.loads(s)
        # Normalize lists/tuples for comparison if needed, but json.loads produces lists
        assert loaded == json.loads(s)
    except Exception as e:
        pytest.fail(f"Failed to parse: {s!r} -> {e}")
