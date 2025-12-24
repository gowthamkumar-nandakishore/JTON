pub mod field_descriptor;
pub mod interner;
pub mod structural_index;

pub use field_descriptor::{FieldDescriptor, FieldType};
pub use interner::{InternedString, StringInterner};
pub use structural_index::StructuralIndex;

use pyo3::prelude::*;

/// Zen Grid table header
#[derive(Debug)]
pub struct ZenGridHeader {
    /// Field names (interned)
    pub fields: Vec<String>,
    
    /// Number of columns (arity)
    pub arity: usize,
    
    /// Estimated row count from semicolon scan
    pub estimated_rows: usize,
}

impl ZenGridHeader {
    pub fn new(fields: Vec<String>, estimated_rows: usize) -> Self {
        let arity = fields.len();
        Self {
            fields,
            arity,
            estimated_rows,
        }
    }
}

/// Parse context for stateful parsing
pub struct ParseContext {
    /// Optional schema for guided parsing
    pub schema: Option<Vec<FieldDescriptor>>,
    
    /// String interner for key deduplication
    pub interner: StringInterner,
}

impl ParseContext {
    pub fn new(schema: Option<Vec<FieldDescriptor>>) -> Self {
        Self {
            schema,
            interner: StringInterner::new(),
        }
    }
}
