pub mod field_descriptor;
pub mod structural_index;

pub use field_descriptor::{FieldDescriptor, FieldType};
pub use structural_index::StructuralIndex;

/// Parse context for stateful parsing
pub struct ParseContext {
    /// Optional schema for guided parsing
    pub schema: Option<Vec<FieldDescriptor>>,
}

impl ParseContext {
    pub fn new(schema: Option<Vec<FieldDescriptor>>) -> Self {
        Self { schema }
    }
}
