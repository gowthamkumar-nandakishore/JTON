# Data Model: SIMD-Accelerated MYSON Core Types

**Feature**: 002-simd-schema-parser  
**Date**: 2025-12-24  
**Purpose**: Define core Rust types for parsing pipeline

## Core Entities

### 1. FieldDescriptor
**Purpose**: Compiled schema metadata for positional field parsing

```rust
pub struct FieldDescriptor {
    /// Field name (interned string for zero-copy reuse)
    pub name: InternedString,
    
    /// Expected type for validation and fast-path selection
    pub ty: FieldType,
    
    /// Position in schema-defined field order (0-indexed)
    pub position: usize,
    
    /// Whether field is nullable (for validation)
    pub nullable: bool,
}

pub enum FieldType {
    Int,
    Float,
    Bool,
    String,
    Array,
    Object,
    Null,
}
```

**Relationships**: Used by SchemaCompiler to convert Python dataclass → Vec<FieldDescriptor>

---

### 2. InternedString
**Purpose**: Deduplicated string storage for repeated keys

```rust
pub struct InternedString {
    /// Pointer to Python PyString object
    py_str: Py<PyString>,
    
    /// Cached hash for fast dict key insertion
    hash: u64,
}

impl InternedString {
    pub fn intern(py: Python, s: &str) -> Self {
        // Use PyString::intern() for repeated keys
        let py_str = PyString::intern(py, s).into();
        let hash = calculate_hash(s);
        Self { py_str, hash }
    }
}
```

**Relationships**: Referenced by FieldDescriptor, used in ZenGridHeader

---

### 3. StructuralIndex
**Purpose**: Output of SIMD scanner - positions of all delimiters

```rust
pub struct StructuralIndex {
    /// Positions of `{`
    open_braces: Vec<usize>,
    
    /// Positions of `[`
    open_brackets: Vec<usize>,
    
    /// Positions of `:`
    colons: Vec<usize>,
    
    /// Positions of `;` (Zen Grid row separators)
    semicolons: Vec<usize>,
    
    /// Positions of `,`
    commas: Vec<usize>,
    
    /// Positions of `]`
    close_brackets: Vec<usize>,
    
    /// Positions of `}`
    close_braces: Vec<usize>,
}

impl StructuralIndex {
    /// Build from input using AVX2/AVX-512 scanner
    pub unsafe fn scan(input: &[u8]) -> Self {
        // SIMD implementation
    }
}
```

**Relationships**: Consumed by JsonParser and ZenGridParser

---

### 4. ZenGridHeader
**Purpose**: Parsed header row with arity enforcement metadata

```rust
pub struct ZenGridHeader {
    /// Field names (interned for reuse across rows)
    fields: Vec<InternedString>,
    
    /// Expected field count (for arity validation)
    arity: usize,
    
    /// Pre-allocation cap based on semicolon count
    estimated_rows: usize,
}

impl ZenGridHeader {
    pub fn parse(input: &[u8], colon_pos: usize) -> Result<Self, ParseError> {
        // Extract first row between `[:` and first `;`
        // Split on `,`, intern each field name
    }
    
    pub fn validate_row(&self, values: &[Value]) -> Result<(), ParseError> {
        match values.len().cmp(&self.arity) {
            std::cmp::Ordering::Less => {
                // Null-fill missing values (Constitution III)
                Ok(())
            },
            std::cmp::Ordering::Greater => {
                // Truncate extra values (Constitution III)
                Ok(())
            },
            std::cmp::Ordering::Equal => Ok(()),
        }
    }
}
```

**Relationships**: Used by ZenGridParser, references InternedString

---

### 5. ParseContext
**Purpose**: Stateful parser with schema, interner, error tracking

```rust
pub struct ParseContext<'py> {
    /// Python interpreter handle
    py: Python<'py>,
    
    /// Optional schema for guided parsing
    schema: Option<Vec<FieldDescriptor>>,
    
    /// String interner for keys
    interner: StringInterner<'py>,
    
    /// Input buffer (zero-copy reference)
    input: &'py [u8],
    
    /// Current byte offset
    cursor: usize,
    
    /// Approximate error positions (±32 bytes)
    last_structural_pos: usize,
}

impl<'py> ParseContext<'py> {
    pub fn new(py: Python<'py>, input: &'py [u8], schema: Option<Vec<FieldDescriptor>>) -> Self {
        Self {
            py,
            schema,
            interner: StringInterner::new(py),
            input,
            cursor: 0,
            last_structural_pos: 0,
        }
    }
    
    pub fn has_schema(&self) -> bool {
        self.schema.is_some()
    }
    
    pub fn error_excerpt(&self) -> &str {
        // Extract ±32 bytes around last_structural_pos
        let start = self.last_structural_pos.saturating_sub(32);
        let end = (self.last_structural_pos + 32).min(self.input.len());
        unsafe { std::str::from_utf8_unchecked(&self.input[start..end]) }
    }
}
```

**Relationships**: Owns StringInterner, holds schema Vec<FieldDescriptor>

---

### 6. StringInterner
**Purpose**: Cache for PyString objects to avoid duplicate allocations

```rust
pub struct StringInterner<'py> {
    /// Intern cache: raw bytes → Python string
    cache: HashMap<&'py [u8], Py<PyString>>,
    
    /// Python handle
    py: Python<'py>,
}

impl<'py> StringInterner<'py> {
    pub fn intern(&mut self, bytes: &'py [u8]) -> Py<PyString> {
        self.cache.entry(bytes).or_insert_with(|| {
            let s = unsafe { std::str::from_utf8_unchecked(bytes) };
            PyString::intern(self.py, s).into()
        }).clone()
    }
}
```

**Relationships**: Owned by ParseContext, produces Py<PyString>

---

## Validation Rules

1. **Field Arity**: ZenGridHeader enforces Constitution III (null-fill, truncate)
2. **Type Checking**: When schema present, FieldType validates parsed values
3. **Pre-allocation Cap**: 1M rows maximum (Constitution III), hard abort at 10M
4. **Zero-Copy Safety**: Input must be immutable PyBytes (runtime validation)

## Lifecycle

```
Input (PyBytes) 
  → StructuralIndex::scan() [SIMD]
  → ParseContext::new() [load schema if provided]
  → JsonParser::parse() OR ZenGridParser::parse()
     → StringInterner::intern() for keys
     → FieldDescriptor lookup if schema present
  → Output (PyDict/PyList)
```
