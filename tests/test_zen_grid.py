"""
Tests for Zen Grid table format:
  - Serialization (dumps with zen_grid=True)
  - Parsing (loads of [: ... ] syntax)
  - Round-trip correctness
  - Edge cases (missing cells, extra cells, nested values)
  - Token efficiency comparison
"""

import json
import re
import pytest
import jton


def _is_zen_grid(s: str) -> bool:
    """Accept both [: and [N: prefixes (row_count is now default)."""
    return bool(re.match(r'^\[\d*:', s))


# ── Serialization tests ──────────────────────────────────────────────────────

class TestDumpsBasic:
    def test_simple_object(self):
        result = jton.dumps({"name": "Alice", "age": 30})
        assert result == '{"name":"Alice","age":30}'

    def test_simple_array_non_uniform(self):
        """Non-uniform arrays stay as JSON."""
        result = jton.dumps([1, 2, 3])
        assert result == "[1,2,3]"

    def test_null(self):
        assert jton.dumps(None) == "null"

    def test_bool(self):
        assert jton.dumps(True) == "true"
        assert jton.dumps(False) == "false"

    def test_integer(self):
        assert jton.dumps(42) == "42"
        assert jton.dumps(-999) == "-999"
        assert jton.dumps(0) == "0"

    def test_float(self):
        assert jton.dumps(3.14) == "3.14"
        assert jton.dumps(1.0) == "1.0"
        assert jton.dumps(float("inf")) == "Infinity"
        assert jton.dumps(float("-inf")) == "-Infinity"
        assert jton.dumps(float("nan")) == "NaN"

    def test_string_escape(self):
        assert jton.dumps('say "hi"') == r'"say \"hi\""'
        assert jton.dumps("new\nline") == r'"new\nline"'
        assert jton.dumps("tab\there") == r'"tab\there"'

    def test_nested_dict(self):
        result = jton.dumps({"a": {"b": 1}})
        assert json.loads(result) == {"a": {"b": 1}}

    def test_empty_dict(self):
        assert jton.dumps({}) == "{}"

    def test_empty_list(self):
        assert jton.dumps([]) == "[]"


class TestDumpsUnquotedKeys:
    def test_simple_identifier(self):
        result = jton.dumps({"name": "Alice"}, unquoted_keys=True)
        assert result == '{name:"Alice"}'

    def test_non_identifier_stays_quoted(self):
        result = jton.dumps({"my-key": 1}, unquoted_keys=True)
        # hyphen is valid in JTON identifiers
        assert result == '{my-key:1}'

    def test_numeric_key_stays_quoted(self):
        result = jton.dumps({"123": 1}, unquoted_keys=True)
        assert result == '{"123":1}'

    def test_space_key_stays_quoted(self):
        result = jton.dumps({"my key": 1}, unquoted_keys=True)
        assert result == '{"my key":1}'


class TestDumpsIndent:
    def test_indent_simple(self):
        result = jton.dumps({"a": 1}, indent=2)
        assert '"a": 1' in result
        assert '\n' in result

    def test_indent_array(self):
        result = jton.dumps([1, 2, 3], indent=2)
        assert '\n' in result


# ── Zen Grid serialization tests ─────────────────────────────────────────────

class TestZenGridDumps:
    def test_two_row_table(self):
        data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        result = jton.dumps(data, zen_grid=True)
        assert _is_zen_grid(result)
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
        result = jton.dumps(data, zen_grid=True)
        assert _is_zen_grid(result)
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
        result = jton.dumps(data, zen_grid=False)
        assert result.startswith("[{") or result.startswith('[{')
        # Should be parseable as standard JSON
        parsed = json.loads(result)
        assert parsed == data

    def test_single_item_no_table(self):
        """Single item arrays don't qualify for Zen Grid (need ≥2 rows)."""
        data = [{"id": 1, "name": "Alice"}]
        result = jton.dumps(data, zen_grid=True)
        # Still valid JSON array, just not a table
        assert json.loads(result) == data

    def test_mixed_types_no_table(self):
        """Mixed-type arrays don't get Zen Grid."""
        data = [1, "hello", None]
        result = jton.dumps(data, zen_grid=True)
        assert result == '[1,"hello",null]'

    def test_token_savings_vs_json(self):
        """Zen Grid should produce fewer characters than JSON for tabular data."""
        data = [
            {"employee_id": i, "first_name": f"Name{i}", "department": "Engineering"}
            for i in range(20)
        ]
        zen_result  = jton.dumps(data, zen_grid=True)
        json_result = json.dumps(data, separators=(",", ":"))
        # Zen Grid should be shorter
        assert len(zen_result) < len(json_result), (
            f"Expected Zen Grid ({len(zen_result)}) < JSON ({len(json_result)})"
        )

    def test_indent_zen_grid(self):
        data = [{"id": 1, "x": 10}, {"id": 2, "x": 20}]
        result = jton.dumps(data, zen_grid=True, indent=2)
        assert _is_zen_grid(result)
        assert '\n' in result


# ── Parsing tests (Zen Grid → Python) ────────────────────────────────────────

class TestZenGridLoads:
    def test_basic_table(self):
        src = '[: name, age; "Alice", 30; "Bob", 25 ]'
        result = jton.loads(src)
        assert result == [
            {"name": "Alice", "age": 30},
            {"name": "Bob",   "age": 25},
        ]

    def test_empty_table(self):
        result = jton.loads('[:]')
        assert result == []

    def test_single_row(self):
        result = jton.loads('[: x, y; 1, 2 ]')
        assert result == [{"x": 1, "y": 2}]

    def test_nested_dict_in_cell(self):
        result = jton.loads('[: id, meta; 1, {"k": 10}; 2, {"k": 20} ]')
        assert result == [
            {"id": 1, "meta": {"k": 10}},
            {"id": 2, "meta": {"k": 20}},
        ]

    def test_nested_list_in_cell(self):
        result = jton.loads('[: id, tags; 1, ["a","b"]; 2, ["c"] ]')
        assert result == [
            {"id": 1, "tags": ["a", "b"]},
            {"id": 2, "tags": ["c"]},
        ]

    def test_null_values(self):
        result = jton.loads('[: id, val; 1, null; 2, null ]')
        assert result == [{"id": 1, "val": None}, {"id": 2, "val": None}]

    def test_bool_values(self):
        result = jton.loads('[: name, active; "Alice", true; "Bob", false ]')
        assert result == [
            {"name": "Alice", "active": True},
            {"name": "Bob",   "active": False},
        ]

    def test_float_values(self):
        result = jton.loads('[: x, y; 1.5, 2.7; 3.0, 4.1 ]')
        assert len(result) == 2
        assert abs(result[0]["x"] - 1.5) < 1e-9


# ── Round-trip tests ──────────────────────────────────────────────────────────

class TestRoundTrip:
    def _roundtrip(self, data, **kwargs):
        serialized = jton.dumps(data, **kwargs)
        return jton.loads(serialized)

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

    def test_nested_cells_fallback_to_json(self):
        data = [
            {"id": 1, "meta": {"k": 10}, "tags": ["a", "b"]},
            {"id": 2, "meta": {"k": 20}, "tags": ["c"]},
        ]
        serialized = jton.dumps(data, zen_grid=True)
        assert serialized.startswith('[{"id":1')
        assert jton.loads(serialized) == data

    def test_structural_string_cells_fallback_to_json(self):
        data = [
            {"id": 1, "value": "line1\nline2", "note": "[json-like]"},
            {"id": 2, "value": "plain", "note": "a:semicolon"},
        ]
        serialized = jton.dumps(data, zen_grid=True)
        assert serialized.startswith('[{"id":1')
        assert jton.loads(serialized) == data

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
            result = jton.dumps(user)
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
            result = jton.dumps(points, zen_grid=True)
            # Should be a Zen Grid since all items are uniform dicts
            assert _is_zen_grid(result)
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
        result = jton.dumps(p)
        parsed = json.loads(result)
        assert parsed == {"x": 1.5, "y": 2.5}

    def test_list_of_dataclasses(self):
        from dataclasses import dataclass

        @dataclass
        class Row:
            id: int
            val: str

        rows = [Row(id=1, val="a"), Row(id=2, val="b")]
        result = jton.dumps(rows, zen_grid=True)
        assert _is_zen_grid(result)


# ── Token efficiency tests ────────────────────────────────────────────────────

class TestTokenEfficiency:
    def _char_reduction(self, data):
        zen_len  = len(jton.dumps(data, zen_grid=True))
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


# ── Row count option tests ─────────────────────────────────────────────────────

class TestRowCount:
    DATA = [{"id": i, "name": f"U{i}"} for i in range(1, 4)]

    def test_row_count_prefix(self):
        result = jton.dumps(self.DATA, row_count=True)
        assert result.startswith("[3:")

    def test_row_count_round_trip(self):
        enc = jton.dumps(self.DATA, row_count=True)
        assert jton.loads(enc) == self.DATA

    def test_row_count_various_sizes(self):
        for n in [2, 5, 10, 50, 100]:
            data = [{"x": i} for i in range(n)]
            enc = jton.dumps(data, row_count=True)
            assert enc.startswith(f"[{n}:")
            assert jton.loads(enc) == data

    def test_row_count_with_tab_delimiter(self):
        enc = jton.dumps(self.DATA, row_count=True, delimiter="tab")
        assert enc.startswith("[3:")
        assert jton.loads(enc) == self.DATA

    def test_row_count_with_pipe_delimiter(self):
        enc = jton.dumps(self.DATA, row_count=True, delimiter="pipe")
        assert enc.startswith("[3:")
        assert jton.loads(enc) == self.DATA

    def test_row_count_no_regression_without_flag(self):
        """With row_count=False the legacy [: prefix is produced."""
        enc = jton.dumps(self.DATA, row_count=False)
        assert enc.startswith("[:")
        assert not enc.startswith("[3:")


# ── Multiline Zen Grid tests ───────────────────────────────────────────────────

class TestMultilineZen:
    DATA = [{"id": 1, "name": "Alice", "score": 95},
            {"id": 2, "name": "Bob",   "score": 87}]

    def test_header_format(self):
        result = jton.dumps(self.DATA, multiline_zen=True)
        # First line: [N]{col1,col2,...}:
        first_line = result.split("\n")[0]
        assert first_line.startswith("[2]{")
        assert first_line.endswith("}:")

    def test_header_contains_all_fields(self):
        result = jton.dumps(self.DATA, multiline_zen=True)
        first_line = result.split("\n")[0]
        assert "id" in first_line
        assert "name" in first_line
        assert "score" in first_line

    def test_correct_row_count(self):
        for n in [2, 5, 10]:
            data = [{"x": i} for i in range(n)]
            result = jton.dumps(data, multiline_zen=True)
            assert result.startswith(f"[{n}]{{")

    def test_rows_are_indented(self):
        result = jton.dumps(self.DATA, multiline_zen=True)
        lines = result.split("\n")
        # All lines after the header must be indented
        for line in lines[1:]:
            assert line.startswith("  "), f"Row line not indented: {line!r}"

    def test_newline_separated_rows(self):
        result = jton.dumps(self.DATA, multiline_zen=True)
        lines = [l for l in result.split("\n") if l.strip()]
        # 1 header + N data rows
        assert len(lines) == 1 + len(self.DATA)

    def test_token_savings_vs_default(self):
        """multiline_zen uses slightly more chars than compact but far fewer than JSON."""
        import json as _json
        data = [{"id": i, "v": i} for i in range(50)]
        ml_len  = len(jton.dumps(data, multiline_zen=True))
        json_len = len(_json.dumps(data, separators=(",", ":")))
        assert ml_len < json_len, "multiline_zen should use fewer chars than JSON"


# ── Delimiter tests ────────────────────────────────────────────────────────────

class TestDelimiters:
    DATA = [{"id": i, "name": f"U{i}", "score": i * 10} for i in range(1, 4)]

    def _roundtrip(self, data, **kw):
        return jton.loads(jton.dumps(data, **kw))

    # Comma (default)
    def test_comma_is_default(self):
        enc = jton.dumps(self.DATA)
        assert ", " in enc  # comma-space separator

    def test_comma_round_trip(self):
        assert self._roundtrip(self.DATA) == self.DATA

    # Tab delimiter
    def test_tab_in_output(self):
        enc = jton.dumps(self.DATA, delimiter="tab")
        assert "\t" in enc

    def test_tab_fewer_chars_than_comma(self):
        comma_len = len(jton.dumps(self.DATA, delimiter="comma"))
        tab_len   = len(jton.dumps(self.DATA, delimiter="tab"))
        assert tab_len < comma_len

    def test_tab_round_trip(self):
        assert self._roundtrip(self.DATA, delimiter="tab") == self.DATA

    def test_tab_large_table(self):
        data = [{"id": i, "name": f"Name{i}", "dept": "Eng", "val": i} for i in range(50)]
        assert self._roundtrip(data, delimiter="tab") == data

    def test_tab_with_row_count(self):
        assert self._roundtrip(self.DATA, delimiter="tab", row_count=True) == self.DATA

    # Pipe delimiter
    def test_pipe_in_output(self):
        enc = jton.dumps(self.DATA, delimiter="pipe")
        assert " | " in enc

    def test_pipe_round_trip(self):
        assert self._roundtrip(self.DATA, delimiter="pipe") == self.DATA

    def test_pipe_large_table(self):
        data = [{"a": i, "b": i * 2, "c": f"x{i}"} for i in range(30)]
        assert self._roundtrip(data, delimiter="pipe") == data

    # Quoted string values with all delimiters
    def test_quoted_strings_with_tab(self):
        data = [{"name": "Alice Smith", "city": "New York"} for _ in range(3)]
        assert self._roundtrip(data, delimiter="tab") == data

    def test_quoted_strings_with_pipe(self):
        data = [{"name": "Alice | Bob", "val": 1}, {"name": "Carol | Dave", "val": 2}]
        # Pipe IN string values must be properly quoted
        enc = jton.dumps(data, delimiter="pipe")
        # Quoted strings survive round-trip
        result = jton.loads(enc)
        assert result == data


# ── Format hint tests ─────────────────────────────────────────────────────────

class TestFormatHint:
    def test_default_style(self):
        hint = jton.format_hint()
        assert "Zen Grid" in hint
        assert ";" in hint  # shows example with semicolons

    def test_zen_grid_style(self):
        hint = jton.format_hint("zen_grid")
        assert "[:" in hint or "[ :" in hint or "col" in hint

    def test_zen_grid_rowcount_style(self):
        hint = jton.format_hint("zen_grid_rowcount")
        assert "[N:" in hint or "row count" in hint.lower()

    def test_multiline_style(self):
        hint = jton.format_hint("multiline")
        assert "[N]{" in hint
        assert "}:" in hint

    def test_tab_style(self):
        hint = jton.format_hint("tab")
        assert "tab" in hint.lower()
        assert "\\t" in hint

    def test_all_styles_non_empty(self):
        for style in ["zen_grid", "zen_grid_rowcount", "multiline", "tab"]:
            hint = jton.format_hint(style)
            assert len(hint) > 50, f"format_hint({style!r}) too short"

    def test_unknown_style_returns_default(self):
        hint = jton.format_hint("unknown_style_xyz")
        assert len(hint) > 50  # Falls through to default


# ── Bare strings and implicit null ────────────────────────────────────────────

class TestBareStrings:
    def test_identifier_values_unquoted(self):
        data = [{"name": "Alice", "dept": "Eng"}, {"name": "Bob", "dept": "Mkt"}]
        result = jton.dumps(data, bare_strings=True)
        # Alice, Bob, Eng, Mkt should appear without quotes
        assert '"Alice"' not in result
        assert 'Alice' in result

    def test_non_identifier_stays_quoted(self):
        data = [{"name": "Alice Smith"}, {"name": "Bob Jones"}]
        result = jton.dumps(data, bare_strings=True)
        # Spaces → must remain quoted
        assert '"Alice Smith"' in result

    def test_bare_strings_round_trip(self):
        data = [{"status": "active", "role": "admin"}, {"status": "inactive", "role": "user"}]
        enc = jton.dumps(data, bare_strings=True)
        assert jton.loads(enc) == data


class TestImplicitNull:
    def test_null_cells_empty(self):
        data = [{"id": 1, "val": None}, {"id": 2, "val": None}]
        enc = jton.dumps(data, implicit_null=True)
        # "null" should not appear in Zen Grid rows
        # The commas will still be there but cells are empty
        assert enc.count("null") == 0

    def test_implicit_null_round_trip(self):
        data = [{"id": 1, "val": None}, {"id": 2, "val": None}]
        enc = jton.dumps(data, implicit_null=True)
        result = jton.loads(enc)
        # Empty cells decode back to None
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2
        # val may be None or missing key — both acceptable


# ── Conformance: mixed options ────────────────────────────────────────────────

class TestMixedOptions:
    """Verify combinations of new options work together."""

    DATA = [{"id": i, "name": f"User{i}", "score": i * 5} for i in range(1, 6)]

    def _rt(self, **kw):
        return jton.loads(jton.dumps(self.DATA, **kw))

    def test_row_count_plus_bare_strings(self):
        enc = jton.dumps(self.DATA, row_count=True, bare_strings=True)
        assert enc.startswith("[5:")

    def test_tab_plus_row_count_round_trip(self):
        assert self._rt(delimiter="tab", row_count=True) == self.DATA

    def test_pipe_plus_row_count_round_trip(self):
        assert self._rt(delimiter="pipe", row_count=True) == self.DATA

    def test_tab_plus_bare_strings(self):
        data = [{"name": "Alice", "dept": "Eng"}, {"name": "Bob", "dept": "Mkt"}]
        enc = jton.dumps(data, delimiter="tab", bare_strings=True)
        assert "\t" in enc
        assert jton.loads(enc) == data

    def test_zen_grid_false_ignores_all_grid_options(self):
        enc = jton.dumps(self.DATA, zen_grid=False, row_count=True, multiline_zen=True)
        # Falls back to pure JSON array
        assert enc.startswith("[{")
        assert json.loads(enc) == self.DATA


# ── Common json API compatibility tests ─────────────────────────────────────

class TestDropInCompatibility:
    """jton must support the common json API surface — load, dump, loads, dumps."""

    def test_load_from_file(self, tmp_path):
        f = tmp_path / "test.json"
        f.write_text('{"x": 1, "y": 2}')
        with open(f) as fp:
            result = jton.load(fp)
        assert result == {"x": 1, "y": 2}

    def test_load_from_bytes_file(self, tmp_path):
        f = tmp_path / "test.json"
        f.write_bytes(b'[1, 2, 3]')
        with open(f, "rb") as fp:
            result = jton.load(fp)
        assert result == [1, 2, 3]

    def test_dump_to_file(self, tmp_path):
        f = tmp_path / "out.json"
        with open(f, "w") as fp:
            jton.dump({"a": 1}, fp, zen_grid=False)
        assert json.loads(f.read_text()) == {"a": 1}

    def test_dump_round_trip(self, tmp_path):
        data = [{"id": i, "val": f"v{i}"} for i in range(5)]
        f = tmp_path / "rt.jton"
        with open(f, "w") as fp:
            jton.dump(data, fp)
        with open(f) as fp:
            result = jton.load(fp)
        assert result == data

    def test_dumps_default_datetime(self):
        from datetime import date
        result = jton.dumps({"d": date(2025, 1, 1)}, default=str, zen_grid=False)
        assert json.loads(result) == {"d": "2025-01-01"}

    def test_dumps_default_custom_object(self):
        class MyObj:
            def __init__(self, v): self.v = v
        result = jton.dumps({"x": MyObj(42)}, default=lambda o: o.v, zen_grid=False)
        assert json.loads(result) == {"x": 42}

    def test_dumps_default_in_nested_list(self):
        from decimal import Decimal
        data = [{"price": Decimal("9.99")}, {"price": Decimal("14.50")}]
        result = jton.dumps(data, default=float, zen_grid=False)
        parsed = json.loads(result)
        assert abs(parsed[0]["price"] - 9.99) < 0.001

    def test_dumps_default_with_zen_grid(self):
        from datetime import date
        data = [{"id": 1, "date": date(2025, 1, 1)}, {"id": 2, "date": date(2025, 1, 2)}]
        result = jton.dumps(data, default=str)
        assert _is_zen_grid(result)
        parsed = jton.loads(result)
        assert parsed[0]["date"] == "2025-01-01"

    def test_dumps_no_default_raises_on_unserializable(self):
        class BadObj: pass
        with pytest.raises((TypeError, ValueError)):
            jton.dumps({"x": BadObj()})

    def test_loads_is_same_as_json_loads_for_standard_json(self):
        cases = ['{}', '[]', '"hello"', '42', '3.14', 'true', 'false', 'null',
                 '{"a":1,"b":[1,2,3]}', '[{"x":1},{"x":2}]']
        for s in cases:
            assert jton.loads(s) == json.loads(s), f"Mismatch for: {s}"


# ── CLI tests ─────────────────────────────────────────────────────────────────

class TestCLI:
    """Smoke-test the JTON CLI module."""

    def _run(self, *args, stdin=None):
        import subprocess
        import sys
        return subprocess.run(
            [sys.executable, "-m", "jton.cli", *args],
            input=stdin, capture_output=True, text=True
        )

    def test_version_flag(self):
        r = self._run("--version")
        assert r.returncode == 0
        assert "jton" in r.stdout.lower()

    def test_encode_from_stdin(self):
        r = self._run(stdin='[{"id":1,"name":"Alice"},{"id":2,"name":"Bob"}]')
        assert r.returncode == 0
        assert "[2:" in r.stdout or "[:" in r.stdout

    def test_hint_flag(self):
        r = self._run("--hint")
        assert r.returncode == 0
        assert "Zen Grid" in r.stdout

    def test_no_zen_grid_gives_compact_json(self):
        r = self._run("--no-zen-grid", stdin='{"x":1}')
        assert r.returncode == 0
        assert json.loads(r.stdout.strip()) == {"x": 1}

    def test_decode_round_trip(self):
        enc = jton.dumps([{"id": 1, "v": "a"}, {"id": 2, "v": "b"}])
        r = self._run("--decode", stdin=enc)
        assert r.returncode == 0
        assert json.loads(r.stdout) == [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}]



