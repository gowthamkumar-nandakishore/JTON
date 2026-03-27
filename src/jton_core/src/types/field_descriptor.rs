use pyo3::prelude::*;
use pyo3::types::PyString;

// Field type enumeration for schema-guided parsing
#[allow(dead_code)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FieldType {
    Int,
    Float,
    Bool,
    String,
    Array,
    Object,
    Null,
}

// Field descriptor for schema compilation
#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct FieldDescriptor {
    /// Field name for diagnostics
    pub name: String,

    /// Interned PyUnicode handle used for zero-hash dict insertion
    pub interned_key: Py<PyString>,

    /// Expected type for validation
    pub ty: FieldType,

    /// Position in schema-defined field order (0-indexed)
    pub position: usize,

    /// Whether field is nullable
    pub nullable: bool,
}

impl FieldDescriptor {
    pub fn new(py: Python, name: String, ty: FieldType, position: usize, nullable: bool) -> Self {
        let key_ptr = crate::parser::string_cache::get_cached_key(name.as_bytes());
        let interned_key = unsafe { Py::from_owned_ptr(py, key_ptr) };
        Self {
            name,
            interned_key,
            ty,
            position,
            nullable,
        }
    }
}
