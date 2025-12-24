# MYSON Zen Grid Serialization Format

## Goal
Achieve 40-60% token reduction vs JSON by using grid/table-based serialization for arrays of objects.

## Design Principles

1. **Grid Format for Homogeneous Arrays**
   - Arrays of objects with similar keys → table format
   - Headers (keys) listed once
   - Values in rows
   - Significant token savings for repeated keys

2. **Zen Grid Syntax**
   ```
   [:
   key1, key2, key3
   ---
   val1, val2, val3
   val1, val2, val3
   ]
   ```

3. **Token Savings Calculation**
   - JSON: `{"key1":"val1","key2":"val2"}` × N objects
   - Zen Grid: Headers once + values only
   - Expected: 50-70% reduction for tabular data

## Format Specification

### Basic Table
```myson
[:
name, age, city
---
"Alice", 30, "NYC"
"Bob", 25, "LA"
]
```

Equivalent JSON:
```json
[
  {"name": "Alice", "age": 30, "city": "NYC"},
  {"name": "Bob", "age": 25, "city": "LA"}
]
```

### Nested Values
```myson
[:
id, data, tags
---
1, {"x": 10}, ["a", "b"]
2, {"x": 20}, ["c", "d"]
]
```

### Mixed JSON Arrays
- Arrays with non-uniform structure → stay as JSON
- Only convert homogeneous arrays (>70% key overlap)

## Implementation Plan

### 1. Serializer (Python → MYSON Zen Grid)
   - Detect homogeneous arrays
   - Extract common keys
   - Generate table format
   - Fallback to JSON for heterogeneous data

### 2. Deserializer (MYSON Zen Grid → Python)
   - Already implemented! Parser handles table syntax
   - No changes needed

### 3. Token Efficiency Benchmarks
   - Compare token counts: JSON vs MYSON Zen Grid
   - Target: 40-60% reduction on tabular datasets

## Success Criteria
- ✅ Correctness: Round-trip (serialize → deserialize) preserves data
- ✅ Token reduction: 40-60% on employee, analytics, orders datasets
- ✅ Performance: Serialization within 2x of json.dumps
