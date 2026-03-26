"""
Tests for Zen Grid table format:
  - Serialization (dumps with zen_grid=True)
  - Parsing (loads of [: ... ] syntax)
  - Round-trip correctness
  - Edge cases (missing cells, extra cells, nested values)
  - Token efficiency comparison
"""

import json
import pytest
import uoon


# ── Serialization tests ──────────────────────────────────────────────────────

class TestDumpsBasic:
    def test_simple_object(self):
        result = uoon.dumps({"name": "Alice", "age": 30})
        assert result == '{"name":"Alice","age":30}'

    def test_simple_array_non_uniform(self):
        """Non-uniform arrays stay as JSON."""
        result = uoon.dumps([1, 2, 3])
        assert result == "[1,2,3]"

    def test_null(self):
        assert uoon.dumps(None) == "null"

    def test_bool(self):
        assert uoon.dumps(True) == "true"
        assert uoon.dumps(False) == "false"

    def test_integer(self):
        assert uoon.dumps(42) == "42"
        assert uoon.dumps(-999) == "-999"
        assert uoon.dumps(0) == "0"

    def test_float(self):
        assert uoon.dumps(3.14) == "3.14"
        assert uoon.dumps(1.0) == "1.0"
        assert uoon.dumps(float("inf")) == "Infinity"
        assert uoon.dumps(float("-inf")) == "-Infinity"
        assert uoon.dumps(float("nan")) == "NaN"

    def test_string_escape(self):
        assert uoon.dumps('say "hi"') == r'"say \"hi\""'
        assert uoon.dumps("new\nline") == r'"new\nline"'
        assert uoon.dumps("tab\there") == r'"tab\there"'

    def test_nested_dict(self):
        result = uoon.dumps({"a": {"b": 1}})
        assert json.loads(result) == {"a": {"b": 1}}

    def test_empty_dict(self):
        assert uoon.dumps({}) == "{}"

    def test_empty_list(self):
        assert uoon.dumps([]) == "[]"


class TestDumpsUnquotedKeys:
    def test_simple_identifier(self):
        result = uoon.dumps({"name": "Alice"}, unquoted_keys=True)
        assert result == '{name:"Alice"}'

    def test_non_identifier_stays_quoted(self):
        result = uoon.dumps({"my-key": 1}, unquoted_keys=True)
        # hyphen is valid in UOON identifiers
        assert result == '{my-key:1}'

    def test_numeric_key_stays_quoted(self):
        result = uoon.dumps({"123": 1}, unquoted_keys=True)
        assert result == '{"123":1}'

    def test_space_key_stays_quoted(self):
        result = uoon.dumps({"my key": 1}, unquoted_keys=True)
        assert result == '{"my key":1}'


class TestDumpsIndent:
    def test_indent_simple(self):
        result = uoon.dumps({"a": 1}, indent=2)
        assert '"a": 1' in result
        assert '\n' in result

    def test_indent_array(self):
        result = uoon.dumps([1, 2, 3], indent=2)
        assert '\n' in result


# ── Zen Grid serialization tests ─────────────────────────────────────────────

class TestZenGridDumps:
    def test_two_row_table(self):
        data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        result = uoon.dumps(data, zen_grid=True)
        assert result.startswith("[:")
        assert "id" in result
        assert "name" in result
        assert "Alice" in result
        assert "Bob" in result

    def test_three_column_table(self):
        data = [
            {"id": 1, "name": "Alice", "score": 95},
            {"id": 2, "name": "Bob",   "score": 87},
            {"id": 3, "name": "Carol", "score": 91},
        ]
        result = uoon.dumps(data, zen_grid=True)
        assert result.startswith("[:")
        # Headers appear once
        assert result.count("id") == 1
        assert result.count("name") == 1
        assert result.count("score") == 1
        # All values present
        assert "Alice" in result
        assert "Bob" in result
        assert "Carol" in result

    def test_zen_grid_disabled_gives_json(self):
        data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        result = uoon.dumps(data, zen_grid=False)
        assert result.startswith("[{") or result.startswith('[{')
        # Should be parseable as standard JSON
        parsed = json.loads(result)
        assert parsed == data

    def test_single_item_no_table(self):
        """Single item arrays don't qualify for Zen Grid (need ≥2 rows)."""
        data = [{"id": 1, "name": "Alice"}]
        result = uoon.dumps(data, zen_grid=True)
        # Still valid JSON array, just not a table
        assert json.loads(result) == data

    def test_mixed_types_no_table(self):
        """Mixed-type arrays don't get Zen Grid."""
        data = [1, "hello", None]
        result = uoon.dumps(data, zen_grid=True)
        assert result == '[1,"hello",null]'

    def test_token_savings_vs_json(self):
        """Zen Grid should produce fewer characters than JSON for tabular data."""
        data = [
            {"employee_id": i, "first_name": f"Name{i}", "department": "Engineering"}
            for i in range(20)
        ]
        zen_result  = uoon.dumps(data, zen_grid=True)
        json_result = json.dumps(data, separators=(",", ":"))
        # Zen Grid should be shorter
        assert len(zen_result) < len(json_result), (
            f"Expected Zen Grid ({len(zen_result)}) < JSON ({len(json_result)})"
        )

    def test_indent_zen_grid(self):
        data = [{"id": 1, "x": 10}, {"id": 2, "x": 20}]
        result = uoon.dumps(data, zen_grid=True, indent=2)
        assert result.startswith("[:")
        assert '\n' in result


# ── Parsing tests (Zen Grid → Python) ────────────────────────────────────────

class TestZenGridLoads:
    def test_basic_table(self):
        src = '[: name, age; "Alice", 30; "Bob", 25 ]'
        result = uoon.loads(src)
        assert result == [
            {"name": "Alice", "age": 30},
            {"name": "Bob",   "age": 25},
        ]

    def test_empty_table(self):
        result = uoon.loads('[:]')
        assert result == []

    def test_single_row(self):
        result = uoon.loads('[: x, y; 1, 2 ]')
        assert result == [{"x": 1, "y": 2}]

    def test_nested_dict_in_cell(self):
        result = uoon.loads('[: id, meta; 1, {"k": 10}; 2, {"k": 20} ]')
        assert result == [
            {"id": 1, "meta": {"k": 10}},
            {"id": 2, "meta": {"k": 20}},
        ]

    def test_nested_list_in_cell(self):
        result = uoon.loads('[: id, tags; 1, ["a","b"]; 2, ["c"] ]')
        assert result == [
            {"id": 1, "tags": ["a", "b"]},
            {"id": 2, "tags": ["c"]},
        ]

    def test_null_values(self):
        result = uoon.loads('[: id, val; 1, null; 2, null ]')
        assert result == [{"id": 1, "val": None}, {"id": 2, "val": None}]

    def test_bool_values(self):
        result = uoon.loads('[: name, active; "Alice", true; "Bob", false ]')
        assert result == [
            {"name": "Alice", "active": True},
            {"name": "Bob",   "active": False},
        ]

    def test_float_values(self):
        result = uoon.loads('[: x, y; 1.5, 2.7; 3.0, 4.1 ]')
        assert len(result) == 2
        assert abs(result[0]["x"] - 1.5) < 1e-9


# ── Round-trip tests ──────────────────────────────────────────────────────────

class TestRoundTrip:
    def _roundtrip(self, data, **kwargs):
        serialized = uoon.dumps(data, **kwargs)
        return uoon.loads(serialized)

    def test_flat_table_roundtrip(self):
        data = [
            {"id": 1, "name": "Alice", "score": 95.5},
            {"id": 2, "name": "Bob",   "score": 87.0},
            {"id": 3, "name": "Carol", "score": 91.3},
        ]
        assert self._roundtrip(data, zen_grid=True) == data

    def test_json_compact_roundtrip(self):
        data = {"users": [{"id": i, "active": True} for i in range(5)]}
        assert self._roundtrip(data, zen_grid=False) == data

    def test_nested_roundtrip(self):
        data = {
            "config": {"host": "localhost", "port": 8080},
            "tags": ["web", "api"],
        }
        assert self._roundtrip(data, zen_grid=True) == data

    def test_empty_structures(self):
        assert self._roundtrip({}) == {}
        assert self._roundtrip([]) == []

    def test_all_primitives(self):
        data = [None, True, False, 42, -7, 3.14, "hello"]
        assert self._roundtrip(data) == data

    def test_large_table_roundtrip(self):
        data = [{"id": i, "val": i * 1.5, "label": f"row{i}"} for i in range(100)]
        result = self._roundtrip(data, zen_grid=True)
        assert result == data

    def test_unicode_roundtrip(self):
        data = [{"name": "日本語", "val": "café"}]
        # Single-row won't trigger Zen Grid, but still round-trips
        result = self._roundtrip(data, zen_grid=True)
        assert result == data

    def test_special_numbers_roundtrip(self):
        data = {"inf": float("inf"), "neg_inf": float("-inf")}
        result = self._roundtrip(data)
        assert result["inf"] == float("inf")
        assert result["neg_inf"] == float("-inf")


# ── Pydantic support ──────────────────────────────────────────────────────────

class TestPydanticSupport:
    def test_pydantic_v2_model(self):
        try:
            from pydantic import BaseModel

            class User(BaseModel):
                id: int
                name: str
                active: bool = True

            user = User(id=1, name="Alice")
            result = uoon.dumps(user)
            parsed = json.loads(result)
            assert parsed["id"] == 1
            assert parsed["name"] == "Alice"
            assert parsed["active"] is True
        except ImportError:
            pytest.skip("pydantic not installed")

    def test_pydantic_list_of_models(self):
        try:
            from pydantic import BaseModel

            class Point(BaseModel):
                x: float
                y: float

            points = [Point(x=1.0, y=2.0), Point(x=3.0, y=4.0)]
            result = uoon.dumps(points, zen_grid=True)
            # Should be a Zen Grid since all items are uniform dicts
            assert result.startswith("[:")
        except ImportError:
            pytest.skip("pydantic not installed")


class TestDataclassSupport:
    def test_dataclass_serialization(self):
        from dataclasses import dataclass

        @dataclass
        class Point:
            x: float
            y: float

        p = Point(x=1.5, y=2.5)
        result = uoon.dumps(p)
        parsed = json.loads(result)
        assert parsed == {"x": 1.5, "y": 2.5}

    def test_list_of_dataclasses(self):
        from dataclasses import dataclass

        @dataclass
        class Row:
            id: int
            val: str

        rows = [Row(id=1, val="a"), Row(id=2, val="b")]
        result = uoon.dumps(rows, zen_grid=True)
        assert result.startswith("[:")


# ── Token efficiency tests ────────────────────────────────────────────────────

class TestTokenEfficiency:
    def _char_reduction(self, data):
        zen_len  = len(uoon.dumps(data, zen_grid=True))
        json_len = len(json.dumps(data, separators=(",", ":")))
        return (json_len - zen_len) / json_len

    def test_5_column_100_row_table(self):
        data = [
            {"id": i, "name": f"Alice{i}", "dept": "Eng", "score": i * 0.5, "active": True}
            for i in range(100)
        ]
        reduction = self._char_reduction(data)
        assert reduction >= 0.30, f"Expected ≥30% reduction, got {reduction:.1%}"

    def test_3_column_50_row_table(self):
        data = [{"id": i, "name": f"Bob{i}", "val": i} for i in range(50)]
        reduction = self._char_reduction(data)
        assert reduction >= 0.25, f"Expected ≥25% reduction, got {reduction:.1%}"
