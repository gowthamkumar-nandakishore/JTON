use pyo3::prelude::*;
use pyo3::types::PyBytes;

mod parser;
mod serializer;
mod simd;
mod types;

use types::{FieldDescriptor, FieldType, ParseContext};

/// Parse JTON/JSON data from bytes or string
///
/// Args:
///     data: Input as bytes (zero-copy) or str (will encode to UTF-8)
///
/// Returns:
///     Parsed Python object (dict, list, str, int, float, bool, None)
///
/// Raises:
///     ValueError: Invalid JSON/JTON syntax
///
/// Examples:
///     >>> import jton
///     >>> jton.loads('{"key": "value"}')
///     {'key': 'value'}
///     >>> jton.loads(b'[1, 2, 3]')
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
            "data must be bytes or str",
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

/// Serialize a Python object to a JTON or JSON string.
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
///     bare_strings: If True, string values that are valid identifiers are written
///                   without surrounding quotes in Zen Grid cells (e.g. `Alice`
///                   instead of `"Alice"`). Saves ~2 tokens per eligible cell.
///     implicit_null: If True, missing Zen Grid cells are written as empty instead
///                    of explicit `null` (saves 1 token per null/missing cell).
///
/// Returns:
///     str — the serialized JTON/JSON string
///
/// Examples:
///     >>> import jton
///     >>> jton.dumps({"name": "Alice", "age": 30})
///     '{"name":"Alice","age":30}'
///
///     >>> jton.dumps([{"id": 1, "x": 10}, {"id": 2, "x": 20}])
///     '[: id, x; 1, 10; 2, 20 ]'
///
///     >>> jton.dumps([{"name":"Alice","dept":"Eng"},{"name":"Bob","dept":"Mkt"}], bare_strings=True)
///     '[: name, dept; Alice, Eng; Bob, Mkt ]'
#[pyfunction(signature = (data, *, zen_grid=true, unquoted_keys=false, indent=None, bare_strings=false, implicit_null=false, row_count=true, multiline_zen=false, delimiter="comma"))]
fn dumps(
    py: Python,
    data: &PyAny,
    zen_grid: bool,
    unquoted_keys: bool,
    indent: Option<usize>,
    bare_strings: bool,
    implicit_null: bool,
    row_count: bool,
    multiline_zen: bool,
    delimiter: &str,
) -> PyResult<String> {
    let delim = match delimiter {
        "tab" | "\t" => serializer::ZenGridDelimiter::Tab,
        "pipe" | "|" => serializer::ZenGridDelimiter::Pipe,
        _ => serializer::ZenGridDelimiter::Comma,
    };
    let opts = serializer::DumpsOptions {
        zen_grid,
        unquoted_keys,
        indent,
        bare_strings,
        implicit_null,
        row_count,
        multiline_zen,
        delimiter: delim,
    };
    let obj: PyObject = data.to_object(py);
    serializer::serialize(py, &obj, &opts)
}

/// Return a concise format description for pasting into LLM system prompts.
///
/// Use this to teach an LLM how to read JTON Zen Grid data before sending it.
///
/// Args:
///     style: One of "zen_grid" (default), "zen_grid_rowcount", "multiline", "tab"
///
/// Returns:
///     A short natural-language description + example the LLM can use.
///
/// Example:
///     >>> import jton
///     >>> print(jton.format_hint())
///     Data is in JTON Zen Grid format. ...
#[pyfunction(signature = (style = "zen_grid"))]
fn format_hint(style: &str) -> String {
    match style {
        "multiline" => concat!(
            "Data is in JTON Multiline Zen Grid format (TOON-compatible).\n",
            "Header line: [N]{col1,col2,col3}: where N is the row count and col1,col2,col3 are field names.\n",
            "Each following indented line is one row with values separated by commas.\n",
            "Example:\n",
            "  [3]{id,name,score}:\n",
            "    1,Alice,95\n",
            "    2,Bob,87\n",
            "    3,Carol,92\n",
            "Decode: each comma-separated row maps to {id: ..., name: ..., score: ...}."
        ).to_string(),
        "zen_grid_rowcount" => concat!(
            "Data is in JTON Zen Grid format with explicit row count.\n",
            "Format: [N: col1, col2, col3; row1val1, row1val2, row1val3; row2val1, ... ]\n",
            "where N is the total number of data rows and col1, col2, col3 are field names.\n",
            "Each semicolon-separated segment after the first is one record.\n",
            "Example: [3: id, name, score; 1, Alice, 95; 2, Bob, 87; 3, Carol, 92 ]\n",
            "Decode: map each semicolon segment to {id: ..., name: ..., score: ...}."
        ).to_string(),
        "tab" => concat!(
            "Data is in JTON Zen Grid tab-delimited format.\n",
            "Format: [: col1\\tcol2\\tcol3; row1val1\\trow1val2\\trow1val3; ... ]\n",
            "Fields and values are separated by tab characters (\\t).\n",
            "Each semicolon-separated segment after the headers is one record.\n",
            "Example: [: id\\tname\\tscore; 1\\tAlice\\t95; 2\\tBob\\t87 ]\n",
            "Decode: map each tab-separated segment to the corresponding field names."
        ).to_string(),
        _ => concat!(
            "Data is in JTON Zen Grid format.\n",
            "Format: [N: col1, col2, col3; row1val1, row1val2, row1val3; row2val1, row2val2, row2val3 ]\n",
            "N is the optional row count prefix (may be omitted: [: col1, col2; ...]).\n",
            "The first semicolon-separated segment is the header (field names).\n",
            "Each subsequent semicolon-separated segment is one data record.\n",
            "Values within each segment are comma-separated and correspond to the header fields in order.\n",
            "Example: [3: id, name, score; 1, Alice, 95; 2, Bob, 87; 3, Carol, 92 ]\n",
            "Decode: {id: 1, name: 'Alice', score: 95}, {id: 2, name: 'Bob', score: 87}, ..."
        ).to_string(),
    }
}

/// JTON (JSON Tabular Object Notation) — SIMD-accelerated parser for Python
///
/// This module provides high-performance parsing of JTON/JSON data using
/// Rust with AVX2/AVX-512 SIMD intrinsics.
#[pymodule]
fn jton_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    // On x86_64, require at least AVX2.  On other architectures (aarch64, etc.)
    // check_cpu_features() always returns true — NEON / scalar are always available.
    if !simd::check_cpu_features() {
        return Err(pyo3::exceptions::PyRuntimeError::new_err(
            "CPU does not support AVX2 (requires Intel Haswell 2013+ or AMD Excavator 2015+)",
        ));
    }

    // Add SIMD implementation info
    m.add("__simd__", simd::get_simd_implementation())?;

    // Add loads() and dumps() functions
    m.add_function(wrap_pyfunction!(loads, m)?)?;
    m.add_function(wrap_pyfunction!(dumps, m)?)?;
    m.add_function(wrap_pyfunction!(format_hint, m)?)?;

    Ok(())
}
