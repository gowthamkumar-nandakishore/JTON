use pyo3::prelude::*;
use pyo3::types::PyBytes;

mod types;
mod simd;
mod parser;
mod serializer;

use types::{ParseContext, FieldDescriptor, FieldType};

/// Parse ZSON/JSON data from bytes or string
/// 
/// Args:
///     data: Input as bytes (zero-copy) or str (will encode to UTF-8)
/// 
/// Returns:
///     Parsed Python object (dict, list, str, int, float, bool, None)
/// 
/// Raises:
///     ValueError: Invalid JSON/ZSON syntax
/// 
/// Examples:
///     >>> import zson
///     >>> zson.loads('{"key": "value"}')
///     {'key': 'value'}
///     >>> zson.loads(b'[1, 2, 3]')
///     [1, 2, 3]
#[pyfunction(signature = (data, schema=None))]
fn loads(py: Python, data: &PyAny, schema: Option<&PyAny>) -> PyResult<PyObject> {
    // Convert input to bytes
    let bytes: &[u8] = if let Ok(py_bytes) = data.downcast::<PyBytes>() {
        // Zero-copy path for bytes input
        py_bytes.as_bytes()
    } else if let Ok(py_str) = data.extract::<&str>() {
        // String input - convert to UTF-8
        py_str.as_bytes()
    } else {
        return Err(pyo3::exceptions::PyTypeError::new_err(
            "data must be bytes or str"
        ));
    };
    
    // Optional schema-mode: schema is a sequence of field names
    // (position is inferred from order). This activates the Nitro-Path in the index parser.
    let schema_vec: Option<Vec<FieldDescriptor>> = match schema {
        None => None,
        Some(s) if s.is_none() => None,
        Some(s) => {
            let mut out: Vec<FieldDescriptor> = Vec::new();
            for (pos, item) in s.iter()?.enumerate() {
                let name: String = item?.extract()?;
                out.push(FieldDescriptor::new(py, name, FieldType::String, pos, true));
            }
            Some(out)
        }
    };

    let mut ctx = ParseContext::new(schema_vec);
    
    // Parse the input
    parser::parse(py, bytes, &mut ctx)
}

/// Serialize a Python object to a ZSON or JSON string.
///
/// Args:
///     data: Python object to serialize (dict, list, str, int, float, bool, None,
///           Pydantic BaseModel, or dataclass)
///     zen_grid: If True (default), homogeneous arrays of dicts are emitted as
///               compact Zen Grid tables  [: h1, h2; v1, v2; ... ]
///               which use 40-60% fewer tokens than JSON on tabular data.
///     unquoted_keys: If True, dict keys that are valid identifiers are written
///                    without surrounding quotes (saves ~2 chars/key).
///     indent: If an integer, pretty-print with that many spaces per indent level.
///
/// Returns:
///     str — the serialized ZSON/JSON string
///
/// Examples:
///     >>> import zson
///     >>> zson.dumps({"name": "Alice", "age": 30})
///     '{"name":"Alice","age":30}'
///
///     >>> zson.dumps([{"id": 1, "x": 10}, {"id": 2, "x": 20}])
///     '[: id, x; 1, 10; 2, 20 ]'
///
///     >>> zson.dumps({"key": "val"}, unquoted_keys=True)
///     '{key:"val"}'
#[pyfunction(signature = (data, *, zen_grid=true, unquoted_keys=false, indent=None))]
fn dumps(
    py: Python,
    data: &PyAny,
    zen_grid: bool,
    unquoted_keys: bool,
    indent: Option<usize>,
) -> PyResult<String> {
    let opts = serializer::DumpsOptions { zen_grid, unquoted_keys, indent };
    let obj: PyObject = data.to_object(py);
    serializer::serialize(py, &obj, &opts)
}

/// ZSON (Zero-overhead Serialized Object Notation) SIMD-accelerated parser for Python
/// 
/// This module provides high-performance parsing of ZSON/JSON data using
/// Rust with AVX2/AVX-512 SIMD intrinsics.
#[pymodule]
fn zson_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    
    // Check CPU features at module import
    if !simd::check_cpu_features() {
        return Err(pyo3::exceptions::PyRuntimeError::new_err(
            "CPU does not support AVX2 (requires Intel Haswell 2013+ or AMD Excavator 2015+)"
        ));
    }
    
    // Add SIMD implementation info
    m.add("__simd__", simd::get_simd_implementation())?;
    
    // Add loads() and dumps() functions
    m.add_function(wrap_pyfunction!(loads, m)?)?;
    m.add_function(wrap_pyfunction!(dumps, m)?)?;
    
    Ok(())
}


