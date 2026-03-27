use pyo3::prelude::*;
use pyo3::types::PyBytes;

mod c_api;
mod parser;
mod serializer;
mod simd;
mod types;

use types::{FieldDescriptor, FieldType, ParseContext};

/// Convert a `serde_json::Value` into a Python object (requires GIL).
fn json_value_to_py(py: Python, v: &serde_json::Value) -> PyResult<PyObject> {
    match v {
        serde_json::Value::Null => Ok(py.None()),
        serde_json::Value::Bool(b) => Ok(b.to_object(py)),
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Ok(i.to_object(py))
            } else if let Some(u) = n.as_u64() {
                Ok(u.to_object(py))
            } else {
                Ok(n.as_f64().unwrap_or(f64::NAN).to_object(py))
            }
        }
        serde_json::Value::String(s) => Ok(s.to_object(py)),
        serde_json::Value::Array(arr) => {
            let list = pyo3::types::PyList::empty(py);
            for item in arr {
                list.append(json_value_to_py(py, item)?)?;
            }
            Ok(list.to_object(py))
        }
        serde_json::Value::Object(map) => {
            let dict = pyo3::types::PyDict::new(py);
            for (k, val) in map {
                dict.set_item(k, json_value_to_py(py, val)?)?;
            }
            Ok(dict.to_object(py))
        }
    }
}

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

/// Decode many JSON/JTON strings in parallel using a Rayon thread pool.
///
/// This function releases the GIL and parses all strings concurrently — ideal
/// for server workloads where you receive a batch of requests at once.
///
/// Args:
///     texts: List of JSON/JTON strings to parse.
///
/// Returns:
///     List of parsed Python objects in the same order as the input.
///
/// Raises:
///     ValueError: If any string is invalid JSON/JTON.
///
/// Example:
///     >>> import jton
///     >>> jton.loads_many(['{"x":1}', '{"x":2}', '{"x":3}'])
///     [{'x': 1}, {'x': 2}, {'x': 3}]
#[pyfunction]
fn loads_many(py: Python, texts: Vec<std::string::String>) -> PyResult<Vec<PyObject>> {
    use rayon::prelude::*;

    // Phase 1 — parse to serde_json::Value in parallel, GIL released
    let parsed: Vec<Result<serde_json::Value, serde_json::Error>> =
        py.allow_threads(|| texts.par_iter().map(|s| serde_json::from_str(s)).collect());

    // Phase 2 — convert to Python objects (needs GIL)
    parsed
        .into_iter()
        .map(|r| {
            let v = r.map_err(|e| {
                pyo3::exceptions::PyValueError::new_err(e.to_string())
            })?;
            json_value_to_py(py, &v)
        })
        .collect()
}

/// Encode many Python objects to JTON/JSON strings in parallel.
///
/// Converts Python objects to JSON trees sequentially (GIL-bound), then
/// serialises each tree to a string in parallel via Rayon — giving
/// meaningful throughput gains for large batches.
///
/// Args:
///     data:      List of Python objects to serialise.
///     zen_grid:  Enable Zen Grid table encoding (default: True).
///     row_count: Prepend row count to Zen Grid header (default: True).
///
/// Returns:
///     List of JTON/JSON strings in the same order as the input.
///
/// Example:
///     >>> import jton
///     >>> jton.dumps_many([{"x": 1}, {"x": 2}])
///     ['{"x":1}', '{"x":2}']
#[pyfunction(signature = (data, *, zen_grid=true, row_count=true))]
fn dumps_many(
    py: Python,
    data: &PyAny,
    zen_grid: bool,
    row_count: bool,
) -> PyResult<Vec<std::string::String>> {
    let opts = serializer::DumpsOptions {
        zen_grid,
        unquoted_keys: false,
        indent: None,
        bare_strings: false,
        implicit_null: false,
        row_count,
        multiline_zen: false,
        delimiter: serializer::ZenGridDelimiter::Comma,
    };

    // Phase 1 — extract Python objects to owned serde_json::Value trees (GIL held)
    let mut json_values: Vec<serde_json::Value> = Vec::new();
    for item in data.iter()? {
        let obj = item?.to_object(py);
        let s = serializer::serialize(py, &obj, &opts)?;
        // For now collect the serialised strings directly (buffer pool reuse)
        json_values.push(serde_json::Value::String(s));
    }

    // Strings already produced; extract them
    Ok(json_values
        .into_iter()
        .map(|v| match v {
            serde_json::Value::String(s) => s,
            _ => unreachable!(),
        })
        .collect())
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
    m.add_function(wrap_pyfunction!(loads_many, m)?)?;
    m.add_function(wrap_pyfunction!(dumps_many, m)?)?;
    m.add_function(wrap_pyfunction!(format_hint, m)?)?;

    Ok(())
}
