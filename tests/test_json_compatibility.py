"""
Comprehensive JSON compatibility tests for ZSON SIMD parser
Tests compliance with JSON specification and Python json module behavior
"""

import pytest
import zson
import json
import math


class TestJSONPrimitives:
    """Test basic JSON data types"""
    
    def test_null(self):
        assert zson.loads('null') is None
    
    def test_bool_true(self):
        assert zson.loads('true') is True
    
    def test_bool_false(self):
        assert zson.loads('false') is False
    
    def test_integers(self):
        assert zson.loads('0') == 0
        assert zson.loads('42') == 42
        assert zson.loads('-17') == -17
        assert zson.loads('9223372036854775807') == 9223372036854775807
    
    def test_floats(self):
        assert zson.loads('3.14') == 3.14
        assert zson.loads('-0.5') == -0.5
        assert zson.loads('0.0') == 0.0
    
    def test_scientific_notation(self):
        assert zson.loads('1e10') == 1e10
        assert zson.loads('1.5e-5') == 1.5e-5
        assert zson.loads('-2.3e+7') == -2.3e+7
    
    def test_special_numbers(self):
        """Test JavaScript number extensions that Python json supports"""
        result = zson.loads('Infinity')
        assert math.isinf(result) and result > 0
        
        result = zson.loads('-Infinity')
        assert math.isinf(result) and result < 0
        
        result = zson.loads('NaN')
        assert math.isnan(result)


class TestJSONStrings:
    """Test JSON string handling"""
    
    def test_empty_string(self):
        assert zson.loads('""') == ""
    
    def test_simple_string(self):
        assert zson.loads('"hello"') == "hello"
    
    def test_escape_sequences(self):
        assert zson.loads(r'"\n"') == "\n"
        assert zson.loads(r'"\t"') == "\t"
        assert zson.loads(r'"\r"') == "\r"
        assert zson.loads(r'"\b"') == "\b"
        assert zson.loads(r'"\f"') == "\f"
        assert zson.loads(r'"\\"') == "\\"
        assert zson.loads(r'"\""') == "\""
        assert zson.loads(r'"\/"') == "/"
    
    def test_unicode_escapes(self):
        assert zson.loads(r'"\u0041"') == "A"
        assert zson.loads(r'"\u2764"') == "❤"
        assert zson.loads(r'"\u0048\u0065\u006C\u006C\u006F"') == "Hello"


class TestJSONArrays:
    """Test JSON array parsing"""
    
    def test_empty_array(self):
        assert zson.loads('[]') == []
    
    def test_single_element(self):
        assert zson.loads('[1]') == [1]
    
    def test_multiple_elements(self):
        assert zson.loads('[1, 2, 3]') == [1, 2, 3]
    
    def test_mixed_types(self):
        result = zson.loads('[1, "two", true, null, 3.14]')
        assert result == [1, "two", True, None, 3.14]
    
    def test_nested_arrays(self):
        assert zson.loads('[[1, 2], [3, 4]]') == [[1, 2], [3, 4]]
        assert zson.loads('[[[1]]]') == [[[1]]]


class TestJSONObjects:
    """Test JSON object parsing"""
    
    def test_empty_object(self):
        assert zson.loads('{}') == {}
    
    def test_single_property(self):
        assert zson.loads('{"key": "value"}') == {"key": "value"}
    
    def test_multiple_properties(self):
        result = zson.loads('{"a": 1, "b": 2, "c": 3}')
        assert result == {"a": 1, "b": 2, "c": 3}
    
    def test_mixed_value_types(self):
        result = zson.loads('{"num": 42, "str": "hello", "bool": true, "null": null}')
        assert result == {"num": 42, "str": "hello", "bool": True, "null": None}
    
    def test_nested_objects(self):
        result = zson.loads('{"outer": {"inner": {"value": 123}}}')
        assert result == {"outer": {"inner": {"value": 123}}}


class TestZSONExtensions:
    """Test ZSON-specific extensions"""
    
    def test_unquoted_keys(self):
        """Test unquoted object keys (ZSON extension)"""
        result = zson.loads('{name: "Alice", age: 30}')
        assert result == {"name": "Alice", "age": 30}
    
    def test_single_line_comments(self):
        """Test single-line comments"""
        result = zson.loads('''
        {
            "x": 1, // comment here
            "y": 2  // another comment
        }
        ''')
        assert result == {"x": 1, "y": 2}
    
    def test_block_comments(self):
        """Test block comments"""
        result = zson.loads('''
        {
            "x": /* comment */ 1,
            /* multi-line
               comment */
            "y": 2
        }
        ''')
        assert result == {"x": 1, "y": 2}


class TestComplexStructures:
    """Test complex nested structures"""
    
    def test_array_of_objects(self):
        data = '''
        [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"}
        ]
        '''
        result = zson.loads(data)
        assert len(result) == 3
        assert result[0] == {"id": 1, "name": "Alice"}
        assert result[2] == {"id": 3, "name": "Charlie"}
    
    def test_object_with_arrays(self):
        data = '''
        {
            "name": "Test",
            "values": [1, 2, 3],
            "nested": {
                "items": [4, 5, 6]
            }
        }
        '''
        result = zson.loads(data)
        assert result["values"] == [1, 2, 3]
        assert result["nested"]["items"] == [4, 5, 6]
    
    def test_deeply_nested(self):
        """Test reasonable nesting depth"""
        data = '{"a": {"b": {"c": {"d": {"e": 5}}}}}'
        result = zson.loads(data)
        assert result["a"]["b"]["c"]["d"]["e"] == 5


class TestWhitespace:
    """Test whitespace handling"""
    
    def test_no_whitespace(self):
        assert zson.loads('{"a":1,"b":2}') == {"a": 1, "b": 2}
    
    def test_various_whitespace(self):
        data = '''
        {
            "a"  :  1  ,
            "b"  :  2
        }
        '''
        assert zson.loads(data) == {"a": 1, "b": 2}
    
    def test_tabs_and_newlines(self):
        data = '{\t"a"\t:\t1\n,\n"b"\n:\n2\n}'
        assert zson.loads(data) == {"a": 1, "b": 2}


class TestErrorHandling:
    """Test error conditions"""
    
    def test_invalid_syntax(self):
        with pytest.raises(ValueError):
            zson.loads('{invalid}')
    
    def test_unclosed_object(self):
        with pytest.raises(ValueError):
            zson.loads('{"key": "value"')
    
    def test_unclosed_array(self):
        with pytest.raises(ValueError):
            zson.loads('[1, 2, 3')
    
    def test_unclosed_string(self):
        with pytest.raises(ValueError):
            zson.loads('{"key": "value}')
    
    def test_trailing_comma_in_array(self):
        """Trailing commas should be handled gracefully"""
        # Note: This might be a ZSON extension
        try:
            result = zson.loads('[1, 2, 3,]')
            # If it parses, verify result
            assert result == [1, 2, 3] or result == [1, 2, 3, None]
        except ValueError:
            # Strict JSON parsing is also acceptable
            pass


class TestPerformancePayloads:
    """Test with realistic performance benchmark payloads"""
    
    def test_homogeneous_array(self):
        """Test array of identical-structure objects"""
        data = '[' + ','.join(
            '{"id": %d, "name": "Item %d", "values": [0, 1, 2, 3, 4]}' % (i, i)
            for i in range(100)
        ) + ']'
        
        result = zson.loads(data)
        assert len(result) == 100
        assert result[0]["id"] == 0
        assert result[99]["id"] == 99
        assert all(len(item["values"]) == 5 for item in result)
    
    def test_large_string_array(self):
        """Test array with large strings"""
        data = '["' + ('x' * 1000) + '", "' + ('y' * 1000) + '"]'
        result = zson.loads(data)
        assert len(result) == 2
        assert len(result[0]) == 1000
        assert len(result[1]) == 1000


class TestCompatibilityWithPythonJSON:
    """Ensure compatibility with Python's json module"""
    
    def test_json_roundtrip(self):
        """Test that standard JSON roundtrips correctly"""
        test_data = {
            "string": "hello",
            "number": 42,
            "float": 3.14,
            "bool": True,
            "null": None,
            "array": [1, 2, 3],
            "object": {"nested": "value"}
        }
        
        json_str = json.dumps(test_data)
        result = zson.loads(json_str)
        
        # Compare results
        assert result == test_data
    
    def test_various_json_formats(self):
        """Test various JSON formatting styles"""
        test_cases = [
            '{"key":"value"}',
            '{ "key" : "value" }',
            '{\n  "key": "value"\n}',
            '[1,2,3]',
            '[ 1 , 2 , 3 ]',
            '[\n  1,\n  2,\n  3\n]',
        ]
        
        for json_str in test_cases:
            zson_result = zson.loads(json_str)
            json_result = json.loads(json_str)
            assert zson_result == json_result, f"Mismatch for: {json_str}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
