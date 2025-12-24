"""Tests for MYSON Zen Grid serializer."""

import pytest
from src.serializer import dumps, serialize, _is_homogeneous_array
from src.tokenizer import Tokenizer
from src.parser import Parser


def myson_parse(text: str):
    """Parse MYSON string to Python object."""
    tokenizer = Tokenizer(text)
    parser = Parser(tokenizer.tokens())
    return parser.parse()


def test_serialize_primitives():
    """Test basic primitive serialization."""
    assert serialize(None) == "null"
    assert serialize(True) == "true"
    assert serialize(False) == "false"
    assert serialize(42) == "42"
    assert serialize(3.14) == "3.14"
    assert serialize("hello") == '"hello"'


def test_serialize_simple_object():
    """Test simple object serialization."""
    obj = {"name": "Alice", "age": 30}
    result = serialize(obj, use_tables=False)
    # Should be valid MYSON that can be parsed back
    parsed = myson_parse(result)
    assert parsed == obj


def test_serialize_simple_array():
    """Test simple array serialization without tables."""
    arr = [1, 2, 3]
    result = serialize(arr, use_tables=False)
    parsed = myson_parse(result)
    assert parsed == arr


def test_homogeneous_array_detection():
    """Test detection of homogeneous arrays."""
    # Homogeneous array
    arr1 = [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
    ]
    is_homog, keys = _is_homogeneous_array(arr1)
    assert is_homog is True
    assert set(keys) == {"name", "age"}
    
    # Non-homogeneous array (different keys)
    arr2 = [
        {"name": "Alice", "age": 30},
        {"city": "NYC", "country": "USA"},
    ]
    is_homog, keys = _is_homogeneous_array(arr2)
    assert is_homog is False
    
    # Array of non-dicts
    arr3 = [1, 2, 3]
    is_homog, keys = _is_homogeneous_array(arr3)
    assert is_homog is False


def test_serialize_table_basic():
    """Test basic table serialization."""
    data = [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
        {"name": "Charlie", "age": 35},
    ]
    result = dumps(data, use_tables=True)
    
    # Should contain table syntax
    assert "[:" in result
    assert "name" in result
    assert "age" in result
    
    # Should round-trip correctly
    parsed = myson_parse(result)
    assert parsed == data


def test_serialize_table_with_missing_values():
    """Test table serialization with some missing keys."""
    data = [
        {"name": "Alice", "age": 30, "city": "NYC"},
        {"name": "Bob", "age": 25},  # missing city
        {"name": "Charlie", "city": "LA"},  # missing age
    ]
    result = dumps(data, use_tables=True)
    
    # Should round-trip (null for missing values)
    parsed = myson_parse(result)
    # Note: missing keys will be null in the table
    assert parsed[0]["name"] == "Alice"
    assert parsed[1]["name"] == "Bob"


def test_serialize_nested_structures():
    """Test tables with nested objects/arrays."""
    data = [
        {"id": 1, "data": {"x": 10, "y": 20}, "tags": ["a", "b"]},
        {"id": 2, "data": {"x": 30, "y": 40}, "tags": ["c", "d"]},
    ]
    result = dumps(data, use_tables=True)
    
    # Should contain table syntax
    assert "[:" in result
    
    # Should round-trip correctly
    parsed = myson_parse(result)
    assert parsed == data


def test_serialize_mixed_data():
    """Test complex nested structure with mix of tables and objects."""
    data = {
        "version": "1.0",
        "users": [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ],
        "metadata": {"created": "2024-01-01", "count": 2}
    }
    result = dumps(data, use_tables=True)
    
    # Should round-trip correctly
    parsed = myson_parse(result)
    assert parsed == data


def test_disable_tables():
    """Test that use_tables=False produces pure JSON."""
    data = [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
    ]
    result = dumps(data, use_tables=False)
    
    # Should NOT contain table syntax
    assert "[:" not in result
    
    # Should still round-trip
    parsed = myson_parse(result)
    assert parsed == data


def test_empty_array():
    """Test serialization of empty array."""
    assert serialize([]) == "[]"


def test_empty_object():
    """Test serialization of empty object."""
    assert serialize({}) == "{}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
