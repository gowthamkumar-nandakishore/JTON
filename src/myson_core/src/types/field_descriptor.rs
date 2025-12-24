// Field type enumeration for schema-guided parsing
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
#[derive(Debug, Clone)]
pub struct FieldDescriptor {
    /// Field name (will use InternedString in future)
    pub name: String,
    
    /// Expected type for validation
    pub ty: FieldType,
    
    /// Position in schema-defined field order (0-indexed)
    pub position: usize,
    
    /// Whether field is nullable
    pub nullable: bool,
}

impl FieldDescriptor {
    pub fn new(name: String, ty: FieldType, position: usize, nullable: bool) -> Self {
        Self {
            name,
            ty,
            position,
            nullable,
        }
    }
}
