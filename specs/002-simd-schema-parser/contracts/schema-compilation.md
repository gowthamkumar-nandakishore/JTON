# Schema Compilation Contract

**Feature**: 002-simd-schema-parser  
**Date**: 2025-12-24  
**Purpose**: Convert Python dataclass/msgspec.Struct to Rust `Vec<FieldDescriptor>`

## Compilation Pipeline

```
Python schema (dataclass/Struct) 
  → introspect via typing.get_type_hints()
  → PyO3 extract field metadata
  → Rust Vec<FieldDescriptor>
  → Cache in ParseContext
```

## FieldDescriptor Rust Type

From [data-model.md](../data-model.md):

```rust
pub struct FieldDescriptor {
    pub name: InternedString,      // Field name (interned once)
    pub field_type: FieldType,      // Expected type (int, str, bool, etc.)
    pub position: u16,              // 0-based position in schema
    pub optional: bool,             // Nullable field
}

pub enum FieldType {
    Int,     // i64
    Float,   // f64
    String,  // Cow<str>
    Bool,
    List,    // Vec<Value>
    Dict,    // HashMap
}
```

## Input: Python Dataclass

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    id: int
    name: str
    email: Optional[str]
    age: int
```

**Compiled Output**:

```rust
vec![
    FieldDescriptor {
        name: InternedString::new("id"),
        field_type: FieldType::Int,
        position: 0,
        optional: false,
    },
    FieldDescriptor {
        name: InternedString::new("name"),
        field_type: FieldType::String,
        position: 1,
        optional: false,
    },
    FieldDescriptor {
        name: InternedString::new("email"),
        field_type: FieldType::String,
        position: 2,
        optional: true,  // Optional[str]
    },
    FieldDescriptor {
        name: InternedString::new("age"),
        field_type: FieldType::Int,
        position: 3,
        optional: false,
    },
]
```

## Input: msgspec.Struct

```python
import msgspec

class Product(msgspec.Struct):
    sku: str
    price: float
    in_stock: bool
```

**Compiled Output**:

```rust
vec![
    FieldDescriptor {
        name: InternedString::new("sku"),
        field_type: FieldType::String,
        position: 0,
        optional: false,
    },
    FieldDescriptor {
        name: InternedString::new("price"),
        field_type: FieldType::Float,
        position: 1,
        optional: false,
    },
    FieldDescriptor {
        name: InternedString::new("in_stock"),
        field_type: FieldType::Bool,
        position: 2,
        optional: false,
    },
]
```

## Type Mapping

| Python Type | Rust FieldType | Validation |
|-------------|----------------|------------|
| `int` | `FieldType::Int` | Parse as i64 |
| `float` | `FieldType::Float` | Parse as f64 |
| `str` | `FieldType::String` | Zero-copy `Cow<str>` |
| `bool` | `FieldType::Bool` | true/false/null |
| `list` | `FieldType::List` | Recursive parsing |
| `dict` | `FieldType::Dict` | Recursive parsing |
| `Optional[T]` | Same as T, `optional=true` | null-fill on missing |

## Parsing Modes

### Mode 1: Zen Grid Positional

```
Input: [: id,name,email; 1,Alice,null ]
Schema: User(id: int, name: str, email: Optional[str])

Parse:
- Column 0 → id (int) → parse "1" as i64
- Column 1 → name (str) → intern "Alice"
- Column 2 → email (str, optional) → store None
```

**Benefit**: Skip key parsing entirely, 2-3x speedup on large tables.

### Mode 2: JSON Array Key Mapping

```
Input: [{"name": "Bob", "id": 2}, {"name": "Alice", "id": 1}]
Schema: User(id: int, name: str)

Parse first object to build key→position map:
- "name" → position 1
- "id" → position 0

Then for each object:
- Find "name" → write to schema position 1
- Find "id" → write to schema position 0
```

**Benefit**: Type-guided parsing (skip float validation for int fields), 1.5-2x speedup.

## Error Handling

### Type Mismatch

```python
>>> myson.loads('[: id; "string"]', schema=User)
TypeError: Field 'id' at position 0 expects int, got str at ~byte 8
```

### Missing Required Field (Zen Grid)

```
Input: [: id; ]  # Missing value
Schema: User(id: int, name: str)

Result:
- id → null-fill (violates schema, raise TypeError)
```

### Extra Columns (Zen Grid)

```
Input: [: id,name,extra; 1,Alice,ignored ]
Schema: User(id: int, name: str)

Result:
- id → 1
- name → "Alice"
- "extra" → truncated (per constitution)
```

## Caching Contract

```rust
pub struct ParseContext<'py> {
    py: Python<'py>,
    schema: Option<Arc<Vec<FieldDescriptor>>>,  // Immutable, cached
    interner: StringInterner<'py>,
    input: &'py [u8],
}
```

- Schema compiled **once** per `loads()` call
- `Arc<Vec<FieldDescriptor>>` enables cheap cloning for parallel parsing
- Field names interned into `StringInterner` for reuse across rows

## Performance Impact

| Scenario | Without Schema | With Schema | Speedup |
|----------|----------------|-------------|---------|
| Zen Grid 10K rows | Parse keys every row | Positional only | 3x |
| JSON array 1K objects | Validate all types | Pre-validated types | 2x |
| Repeated keys (50+ objects) | Hash lookup every key | Interned strings | 1.5x |

## Validation Rules

1. **At compile time**:
   - Schema must be dataclass or msgspec.Struct
   - All fields must have type annotations
   - Max 65,535 fields (u16::MAX limit)

2. **At parse time**:
   - Type mismatches raise `TypeError` with approximate position
   - Missing required fields raise `TypeError` (after null-filling attempt)
   - Extra Zen Grid columns are silently truncated (per constitution clarification)

## Thread Safety (Phase 2)

```rust
fn parallel_parse_rows(
    rows: &[ZenGridRow],
    schema: Arc<Vec<FieldDescriptor>>,
) -> Vec<PyObject> {
    rows.par_iter()  // Rayon parallel iterator
        .map(|row| parse_row_with_schema(row, &schema))
        .collect()
}
```

`Arc<Vec<FieldDescriptor>>` allows sharing schema across threads without cloning data.
