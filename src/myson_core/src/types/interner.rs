use pyo3::prelude::*;
use pyo3::types::PyString;
use std::collections::HashMap;
use std::hash::{Hash, Hasher};
use std::collections::hash_map::DefaultHasher;

/// Interned string wrapper for deduplicated storage
#[derive(Debug, Clone)]
pub struct InternedString {
    /// Pointer to Python PyString object
    py_str: Py<PyString>,
    
    /// Cached hash for fast dict key insertion
    hash: u64,
}

impl InternedString {
    pub fn intern(py: Python, s: &str) -> Self {
        // Use PyString::intern() for repeated keys
        let py_str: Py<PyString> = PyString::intern(py, s).into();
        
        // Calculate and cache hash
        let mut hasher = DefaultHasher::new();
        s.hash(&mut hasher);
        let hash = hasher.finish();
        
        Self { py_str, hash }
    }
    
    pub fn as_py(&self) -> &Py<PyString> {
        &self.py_str
    }
    
    pub fn hash(&self) -> u64 {
        self.hash
    }
}

/// String interner for efficient key reuse
pub struct StringInterner {
    map: HashMap<String, Py<PyString>>,
}

impl StringInterner {
    pub fn new() -> Self {
        Self {
            map: HashMap::new(),
        }
    }
    
    /// Intern a string, returning cached PyString if already seen
    pub fn intern(&mut self, py: Python, s: &str) -> Py<PyString> {
        if let Some(cached) = self.map.get(s) {
            cached.clone()
        } else {
            let py_str: Py<PyString> = PyString::intern(py, s).into();
            self.map.insert(s.to_string(), py_str.clone());
            py_str
        }
    }
    
    /// Clear all interned strings
    pub fn clear(&mut self) {
        self.map.clear();
    }
}

impl Default for StringInterner {
    fn default() -> Self {
        Self::new()
    }
}
