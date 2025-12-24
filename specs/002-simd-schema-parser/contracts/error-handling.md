# Error Handling Contract

**Feature**: 002-simd-schema-parser  
**Date**: 2025-12-24  
**Purpose**: Error types, position tracking, and user-facing messages

## Error Types

### 1. ParseError (Syntax)

```python
class ParseError(ValueError):
    """Invalid JSON/MYSON syntax"""
    
    def __init__(self, message: str, position: int, excerpt: str):
        self.message = message
        self.position = position  # Approximate byte offset (±32 bytes)
        self.excerpt = excerpt    # 40-char context window
```

**Examples**:

```python
>>> myson.loads('{invalid}')
ParseError: Unexpected token 'i' at byte ~1:
  {invalid}
   ^

>>> myson.loads('[: id; 1, ]')  # Trailing comma in Zen Grid row
ParseError: Unexpected delimiter at byte ~10:
  [: id; 1, ]
           ^
```

### 2. SchemaError (Type Mismatch)

```python
class SchemaError(TypeError):
    """Type validation failure during schema-guided parse"""
    
    def __init__(self, field: str, expected: str, actual: str, position: int):
        self.field = field
        self.expected = expected
        self.actual = actual
        self.position = position
```

**Examples**:

```python
>>> @dataclass
... class User:
...     id: int
...     name: str

>>> myson.loads('[: id,name; "string",Alice ]', schema=User)
SchemaError: Field 'id' expects int, got str at byte ~13:
  [: id,name; "string",Alice ]
              ^

>>> myson.loads('[{"id": 1.5, "name": "Bob"}]', schema=User)
SchemaError: Field 'id' expects int, got float at byte ~9:
  [{"id": 1.5, "name": "Bob"}]
           ^
```

### 3. MemoryError (Safety Limits)

```python
class MemorySafetyError(MemoryError):
    """Input exceeds safety limits to prevent OOM"""
    
    def __init__(self, limit: str, actual: str):
        self.limit = limit
        self.actual = actual
```

**Examples**:

```python
>>> myson.loads(b'[: id; ' + b'1;' * 11_000_000)  # 11M rows
MemorySafetyError: Zen Grid exceeds 10M row hard limit (detected 11M rows)

>>> huge_data = b'{' + b'"key": "value",' * 100_000_000 + b'}'
>>> myson.loads(huge_data)
MemorySafetyError: Input size 1.2 GB exceeds 1 GB safety limit
```

### 4. ConfigurationError (API Misuse)

```python
class ConfigurationError(TypeError):
    """Invalid parameter combination"""
```

**Examples**:

```python
>>> myson.loads(data, parallel=True)  # Missing schema
ConfigurationError: parallel=True requires schema parameter

>>> myson.loads(data, schema=int)  # Invalid schema type
ConfigurationError: schema must be dataclass or msgspec.Struct, got <class 'int'>
```

## Position Tracking

### Approximate Positions (±32 bytes)

Per constitution requirement, error positions are accurate within ±32 bytes:

```rust
pub struct ErrorContext {
    approximate_position: usize,  // Byte offset in input
    excerpt_start: usize,         // Start of 40-char excerpt
    excerpt_end: usize,           // End of 40-char excerpt
}

impl ErrorContext {
    pub fn from_simd_index(index: usize, structural_index: &StructuralIndex) -> Self {
        // Find nearest structural character from SIMD scan
        let approx = structural_index.find_nearest(index);
        
        // Extract 40-char context window
        let start = approx.saturating_sub(20);
        let end = (approx + 20).min(input.len());
        
        ErrorContext {
            approximate_position: approx,
            excerpt_start: start,
            excerpt_end: end,
        }
    }
}
```

**Rationale**: SIMD scans process 32-64 bytes per iteration. Rather than track exact positions (expensive), we report the nearest structural character. This trades precision for speed while remaining useful for debugging.

### Excerpt Formatting

```python
def format_error_excerpt(position: int, excerpt: str) -> str:
    """Format error with caret pointing to approximate position"""
    marker_pos = min(position - excerpt_start, 40)
    marker = ' ' * marker_pos + '^'
    return f"{excerpt}\n{marker}"
```

**Example**:

```
ParseError: Unexpected token at byte ~45:
  "key": "value", invalid_token, "another": 1
                  ^
```

## Error Recovery

MYSON parser does **not** attempt error recovery. On first error, parsing stops immediately:

```rust
pub fn parse_with_simd(input: &[u8]) -> Result<Value, ParseError> {
    match scan_structural_chars(input) {
        Ok(index) => parse_recursive(input, &index, 0),
        Err(e) => Err(e),  // Stop immediately
    }
}
```

**Rationale**: Error recovery adds complexity and slows happy path. Users prefer fast failure with clear messages over partial results.

## Error Messages

### Guidelines

1. **Be specific**: "Unexpected token 'x'" not "Parse error"
2. **Show context**: Include excerpt with caret
3. **Suggest fix**: "Did you mean...?" when applicable
4. **Approximate**: Always prefix position with `~byte` to indicate approximation

### Examples

**Good**:
```
ParseError: Unexpected delimiter ';' in JSON mode at ~byte 23:
  {"key": "value"; "other": 1}
                  ^
Hint: Use ',' to separate object fields in JSON
```

**Bad**:
```
ParseError: Invalid syntax at position 23
```

## Performance Impact

- **Zero-allocation errors**: Error contexts reuse existing input buffer (no copying)
- **Lazy formatting**: Excerpt/marker only computed on error path
- **Fast failure**: Parser aborts on first error (no backtracking)

**Benchmark**: Error construction <1μs, negligible impact on happy path.

## Testing Contract

Error handling requires 50+ dedicated tests:

```python
# tests/unit/test_error_positions.py
def test_approximate_position_within_tolerance():
    """Error positions accurate within ±32 bytes"""
    data = '{"key": ' + ' ' * 100 + 'invalid}'
    with pytest.raises(ParseError) as exc:
        myson.loads(data)
    
    # Actual error at byte 108, allow ±32
    assert 76 <= exc.value.position <= 140

# tests/unit/test_schema_errors.py
def test_type_mismatch_helpful_message():
    """Schema errors include field name and types"""
    @dataclass
    class User:
        id: int
    
    with pytest.raises(SchemaError) as exc:
        myson.loads('[{"id": "string"}]', schema=User)
    
    assert exc.value.field == "id"
    assert exc.value.expected == "int"
    assert exc.value.actual == "str"
    assert "expects int, got str" in str(exc.value)
```

## Compatibility with Existing Tests

All 400+ existing tests must pass. Error messages can improve, but error **types** must match:

```python
# Current behavior
>>> myson.loads('{invalid}')
ValueError: ...

# New behavior (maintains ValueError base)
>>> myson.loads('{invalid}')
ParseError: ...  # ParseError(ValueError)
isinstance(ParseError(), ValueError)  # True
```

## Parallel Mode Errors (Phase 2)

When `parallel=True`, errors from worker threads are collected and reported:

```python
>>> myson.loads(large_data, schema=User, parallel=True)
SchemaError: 3 rows failed validation:
  - Row 142: Field 'id' expects int, got str at ~byte 8234
  - Row 891: Field 'age' expects int, got str at ~byte 52103
  - Row 1523: Field 'id' expects int, got float at ~byte 89234
```

Workers detect errors independently and aggregate before raising.
