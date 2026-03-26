// LEXATRON Serializer — high-performance JSON/LEXATRON dumps()
//
// Three output modes:
//   1. JSON compact   (zen_grid=false, unquoted_keys=false)
//   2. LEXATRON compact   (zen_grid=false, unquoted_keys=true)
//   3. LEXATRON Zen Grid  (zen_grid=true) — homogeneous arrays of dicts → table syntax
//
// Speed strategy:
//   • itoa  — fastest integer → string (no heap alloc for small numbers)
//   • ryu   — fastest f64 → shortest-round-trip string (same as orjson)
//   • pyo3 direct FFI type checks — minimal Python overhead for dispatch
//   • Pre-allocated Vec<u8> output buffer — single allocation per call
//   • SIMD escape scan (AVX2) — scan 32 bytes/cycle for chars needing escaping

use pyo3::ffi;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyTuple};

#[cfg(target_arch = "x86_64")]
use std::arch::x86_64::*;

// ── Public options struct ─────────────────────────────────────────────────────

pub struct DumpsOptions {
    pub zen_grid: bool,
    pub unquoted_keys: bool,
    pub indent: Option<usize>,
    /// Write identifier-like string values without surrounding quotes in Zen Grid cells.
    /// Identifiers: start with [a-zA-Z_$], followed by [a-zA-Z0-9_$-].
    /// Saves ~2 tokens per bare string cell (e.g. `Alice` instead of `"Alice"`).
    pub bare_strings: bool,
    /// Write missing Zen Grid cells as empty (`,,,`) instead of explicit `null`.
    /// Empty cell = null on decode. Saves 1 token per null cell — significant for
    /// sparse tables (e.g. optional columns with 30%+ null rate).
    pub implicit_null: bool,
}

// ── Main entry point ──────────────────────────────────────────────────────────

/// Serialize a Python object to a LEXATRON/JSON string.
pub fn serialize(py: Python, obj: &PyObject, opts: &DumpsOptions) -> PyResult<String> {
    let mut buf = Vec::with_capacity(4096);
    write_value(py, obj.as_ref(py), &mut buf, opts, 0)?;
    // SAFETY: we only write valid UTF-8 sequences
    Ok(unsafe { String::from_utf8_unchecked(buf) })
}

// ── Recursive value writer ────────────────────────────────────────────────────

fn write_value<'py>(
    py: Python<'py>,
    obj: &'py PyAny,
    buf: &mut Vec<u8>,
    opts: &DumpsOptions,
    depth: usize,
) -> PyResult<()> {
    const MAX_DEPTH: usize = 256;
    if depth > MAX_DEPTH {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Object too deeply nested (max 256 levels)",
        ));
    }

    // Type dispatch using pyo3's is_instance_of — the compiler inlines these
    // to simple PyTypeObject pointer comparisons.
    use pyo3::types::{PyBool, PyBytes as PyBytesType, PyFloat, PyLong, PyString};

    if obj.is_none() {
        buf.extend_from_slice(b"null");
        return Ok(());
    }
    // Bool must come before Int (bool is a subtype of int in Python)
    if obj.is_instance_of::<PyBool>() {
        let v: bool = obj.extract()?;
        buf.extend_from_slice(if v { b"true" } else { b"false" });
        return Ok(());
    }
    if obj.is_instance_of::<PyString>() {
        return unsafe { write_str(obj.as_ptr(), buf) };
    }
    if obj.is_instance_of::<PyLong>() {
        return unsafe { write_int(py, obj.as_ptr(), buf) };
    }
    if obj.is_instance_of::<PyFloat>() {
        return unsafe { write_float(obj.as_ptr(), buf) };
    }
    if obj.is_instance_of::<PyDict>() {
        return write_dict(py, obj, buf, opts, depth);
    }
    if obj.is_instance_of::<PyList>() {
        return write_list_or_table(py, obj, buf, opts, depth);
    }
    if obj.is_instance_of::<PyTuple>() {
        return write_tuple(py, obj, buf, opts, depth);
    }
    if obj.is_instance_of::<PyBytesType>() {
        return unsafe { write_bytes(obj.as_ptr(), buf) };
    }

    // Slow path: Pydantic, dataclass, or TypeError
    write_fallback(py, obj, buf, opts, depth)
}

// ── String serialization ──────────────────────────────────────────────────────

/// Write a Python str as a JSON-quoted, escaped string.
/// Uses PyUnicode_AsUTF8AndSize for zero-copy UTF-8 access.
#[inline]
unsafe fn write_str(ptr: *mut ffi::PyObject, buf: &mut Vec<u8>) -> PyResult<()> {
    let mut len: ffi::Py_ssize_t = 0;
    let data = ffi::PyUnicode_AsUTF8AndSize(ptr, &mut len);
    if data.is_null() {
        // Clear error and fall back to safer path
        ffi::PyErr_Clear();
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Failed to encode string as UTF-8",
        ));
    }
    let bytes = std::slice::from_raw_parts(data as *const u8, len as usize);
    buf.push(b'"');
    write_escaped_str(bytes, buf);
    buf.push(b'"');
    Ok(())
}

/// Write raw bytes as JSON string value with JSON escape sequences.
/// AVX2 fast path: scans 32 bytes/cycle for characters needing escaping.
/// Falls back to scalar for non-AVX2 or tail bytes.
#[inline]
fn write_escaped_str(s: &[u8], buf: &mut Vec<u8>) {
    #[cfg(target_arch = "x86_64")]
    {
        if std::is_x86_feature_detected!("avx2") {
            return unsafe { write_escaped_str_avx2(s, buf) };
        }
    }
    write_escaped_str_scalar(s, buf);
}

/// SIMD AVX2 escape scanner: finds the next byte requiring escaping in
/// 32-byte chunks, bulk-copies clean spans with `extend_from_slice`.
#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2")]
unsafe fn write_escaped_str_avx2(s: &[u8], buf: &mut Vec<u8>) {
    // Characters requiring escaping: < 0x20 (control), 0x22 ('"'), 0x5C ('\\')
    let v_quote = _mm256_set1_epi8(b'"' as i8);
    let v_slash = _mm256_set1_epi8(b'\\' as i8);
    // Detect control chars (0x00–0x1F) using bias trick:
    //   add 0x80 to each byte, then compare with signed 0x80+0x20 = 0xA0 (as i8: -96)
    //   bytes 0x00-0x1F become 0x80-0x9F, which are all < 0xA0 in unsigned / < -96 in signed

    let mut i = 0usize;
    let mut start = 0usize;

    while i + 32 <= s.len() {
        let chunk = _mm256_loadu_si256(s.as_ptr().add(i) as *const __m256i);

        // Detect '"' and '\\'
        let m_quote = _mm256_cmpeq_epi8(chunk, v_quote);
        let m_slash = _mm256_cmpeq_epi8(chunk, v_slash);

        // Detect control chars (0x00–0x1F): _mm256_cmpgt_epi8(0x20, chunk) but signed
        // Add 0x80 to both sides to make unsigned comparison via signed gt:
        //   byte + 0x80 < 0xA0  →  byte < 0x20
        let biased = _mm256_add_epi8(chunk, _mm256_set1_epi8(-128_i8)); // +0x80
        let v_ctrl_biased = _mm256_set1_epi8((-128_i8).wrapping_add(0x20)); // 0x80+0x20-0x100 as i8
        let m_ctrl = _mm256_cmpgt_epi8(v_ctrl_biased, biased);

        let m_any = _mm256_or_si256(m_quote, _mm256_or_si256(m_slash, m_ctrl));
        let mask = _mm256_movemask_epi8(m_any) as u32;

        if mask == 0 {
            // No escape needed in this 32-byte chunk — just advance
            i += 32;
            continue;
        }

        // Process up to the first byte that needs escaping
        let first = mask.trailing_zeros() as usize;
        if start < i + first {
            buf.extend_from_slice(&s[start..i + first]);
        }
        // Handle the single escape at position i + first
        write_escaped_str_scalar(&s[i + first..i + first + 1], buf);
        i += first + 1;
        start = i;
    }

    // Scalar tail (< 32 bytes remaining)
    if start < s.len() {
        write_escaped_str_scalar(&s[start..], buf);
    }
}

/// Scalar fallback for write_escaped_str (used on non-AVX2 and for tail bytes).
#[inline]
fn write_escaped_str_scalar(s: &[u8], buf: &mut Vec<u8>) {
    let mut i = 0;
    let mut start = 0;

    while i < s.len() {
        let b = s[i];
        let escape: &[u8] = match b {
            b'"' => b"\\\"",
            b'\\' => b"\\\\",
            b'\n' => b"\\n",
            b'\r' => b"\\r",
            b'\t' => b"\\t",
            0x08 => b"\\b",
            0x0C => b"\\f",
            0x00..=0x1F => {
                buf.extend_from_slice(&s[start..i]);
                write_unicode_escape(b, buf);
                i += 1;
                start = i;
                continue;
            }
            _ => {
                i += 1;
                continue;
            }
        };
        buf.extend_from_slice(&s[start..i]);
        buf.extend_from_slice(escape);
        i += 1;
        start = i;
    }
    buf.extend_from_slice(&s[start..]);
}

#[inline(always)]
fn write_unicode_escape(b: u8, buf: &mut Vec<u8>) {
    const HEX: &[u8] = b"0123456789abcdef";
    buf.extend_from_slice(b"\\u00");
    buf.push(HEX[(b >> 4) as usize]);
    buf.push(HEX[(b & 0xF) as usize]);
}

// ── Number serialization ──────────────────────────────────────────────────────

/// Write a Python int using itoa (fastest integer serialization).
#[inline]
unsafe fn write_int(py: Python, ptr: *mut ffi::PyObject, buf: &mut Vec<u8>) -> PyResult<()> {
    // Try signed i64 first (covers the vast majority of real-world integers)
    let v = ffi::PyLong_AsLongLong(ptr);
    if v != -1 || ffi::PyErr_Occurred().is_null() {
        let mut tmp = itoa::Buffer::new();
        buf.extend_from_slice(tmp.format(v).as_bytes());
        return Ok(());
    }
    ffi::PyErr_Clear();

    // Try unsigned u64
    let uv = ffi::PyLong_AsUnsignedLongLong(ptr);
    if uv != u64::MAX || ffi::PyErr_Occurred().is_null() {
        let mut tmp = itoa::Buffer::new();
        buf.extend_from_slice(tmp.format(uv).as_bytes());
        return Ok(());
    }
    ffi::PyErr_Clear();

    // Arbitrary-precision fallback: wrap as PyObject and call str()
    let py_obj = PyObject::from_borrowed_ptr(py, ptr);
    let s = py_obj.as_ref(py).str()?;
    buf.extend_from_slice(s.to_str()?.as_bytes());
    Ok(())
}

/// Write a Python float using ryu (fastest shortest-round-trip f64 → string).
#[inline]
unsafe fn write_float(ptr: *mut ffi::PyObject, buf: &mut Vec<u8>) -> PyResult<()> {
    // PyFloat_AsDouble is the C function (always available in FFI, unlike the AS_DOUBLE macro)
    let v = ffi::PyFloat_AsDouble(ptr);
    if v == -1.0 && !ffi::PyErr_Occurred().is_null() {
        ffi::PyErr_Clear();
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Failed to read float value",
        ));
    }
    if v.is_nan() {
        buf.extend_from_slice(b"NaN");
    } else if v.is_infinite() {
        buf.extend_from_slice(if v > 0.0 { b"Infinity" } else { b"-Infinity" });
    } else {
        let mut tmp = ryu::Buffer::new();
        buf.extend_from_slice(tmp.format(v).as_bytes());
    }
    Ok(())
}

/// Encode Python bytes as a hex-encoded JSON string.
#[inline]
unsafe fn write_bytes(ptr: *mut ffi::PyObject, buf: &mut Vec<u8>) -> PyResult<()> {
    // Use PyBytes_AsString / PyBytes_Size (C functions, not macros)
    let data = ffi::PyBytes_AsString(ptr) as *const u8;
    let len = ffi::PyBytes_Size(ptr) as usize;
    if data.is_null() {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Failed to read bytes value",
        ));
    }
    let bytes = std::slice::from_raw_parts(data, len);
    buf.push(b'"');
    for &b in bytes {
        const HEX: &[u8] = b"0123456789abcdef";
        buf.push(HEX[(b >> 4) as usize]);
        buf.push(HEX[(b & 0xF) as usize]);
    }
    buf.push(b'"');
    Ok(())
}

// ── Dict serialization ────────────────────────────────────────────────────────

fn write_dict<'py>(
    py: Python<'py>,
    obj: &'py PyAny,
    buf: &mut Vec<u8>,
    opts: &DumpsOptions,
    depth: usize,
) -> PyResult<()> {
    let dict: &PyDict = obj.downcast()?;
    let len = dict.len();

    buf.push(b'{');

    if let Some(indent_width) = opts.indent {
        write_dict_indented(py, dict, buf, opts, depth, indent_width, len)
    } else {
        write_dict_compact(py, dict, buf, opts, depth, len)
    }
}

fn write_dict_compact<'py>(
    py: Python<'py>,
    dict: &'py PyDict,
    buf: &mut Vec<u8>,
    opts: &DumpsOptions,
    depth: usize,
    len: usize,
) -> PyResult<()> {
    let mut i = 0;
    for (k, v) in dict.iter() {
        write_key(py, k, buf, opts)?;
        buf.push(b':');
        write_value(py, v, buf, opts, depth + 1)?;
        i += 1;
        if i < len {
            buf.push(b',');
        }
    }
    buf.push(b'}');
    Ok(())
}

fn write_dict_indented<'py>(
    py: Python<'py>,
    dict: &'py PyDict,
    buf: &mut Vec<u8>,
    opts: &DumpsOptions,
    depth: usize,
    indent_width: usize,
    len: usize,
) -> PyResult<()> {
    let child_indent = depth + 1;
    let mut i = 0;
    for (k, v) in dict.iter() {
        buf.push(b'\n');
        write_indent(buf, child_indent * indent_width);
        write_key(py, k, buf, opts)?;
        buf.extend_from_slice(b": ");
        write_value(py, v, buf, opts, child_indent)?;
        i += 1;
        if i < len {
            buf.push(b',');
        }
    }
    if len > 0 {
        buf.push(b'\n');
        write_indent(buf, depth * indent_width);
    }
    buf.push(b'}');
    Ok(())
}

/// Write a dict key — either quoted JSON string or unquoted LEXATRON identifier.
#[inline]
fn write_key<'py>(
    _py: Python<'py>,
    key: &'py PyAny,
    buf: &mut Vec<u8>,
    opts: &DumpsOptions,
) -> PyResult<()> {
    use pyo3::types::PyString;

    // Fast path: string keys — use FFI directly to avoid PyO3 UTF-8 validation overhead
    if key.is_instance_of::<PyString>() {
        let mut len: ffi::Py_ssize_t = 0;
        let data = unsafe { ffi::PyUnicode_AsUTF8AndSize(key.as_ptr(), &mut len) };
        if !data.is_null() {
            let bytes = unsafe { std::slice::from_raw_parts(data as *const u8, len as usize) };
            if opts.unquoted_keys && is_valid_identifier(bytes) {
                buf.extend_from_slice(bytes);
            } else {
                buf.push(b'"');
                write_escaped_str(bytes, buf);
                buf.push(b'"');
            }
            return Ok(());
        }
        unsafe { ffi::PyErr_Clear() };
    }

    // Non-string key: convert to str, then recurse once
    let s = key.str()?;
    write_key(_py, s.as_ref(), buf, opts)
}

/// Returns true if `bytes` is a valid unquoted LEXATRON identifier.
/// Rules: starts with [a-zA-Z_$], followed by [a-zA-Z0-9_$-]
#[inline]
fn is_valid_identifier(bytes: &[u8]) -> bool {
    if bytes.is_empty() {
        return false;
    }
    let first = bytes[0];
    if !first.is_ascii_alphabetic() && first != b'_' && first != b'$' {
        return false;
    }
    for &b in &bytes[1..] {
        if !b.is_ascii_alphanumeric() && b != b'_' && b != b'$' && b != b'-' {
            return false;
        }
    }
    true
}

// ── List / Zen Grid serialization ─────────────────────────────────────────────

fn write_list_or_table<'py>(
    py: Python<'py>,
    obj: &'py PyAny,
    buf: &mut Vec<u8>,
    opts: &DumpsOptions,
    depth: usize,
) -> PyResult<()> {
    let list: &PyList = obj.downcast()?;
    let len = list.len();

    if len == 0 {
        buf.extend_from_slice(b"[]");
        return Ok(());
    }

    // Try Zen Grid if enabled and the list qualifies
    if opts.zen_grid && len >= 2 {
        if let Some(headers) = detect_zen_grid_candidate(list)? {
            return write_zen_grid(py, list, &headers, buf, opts, depth);
        }

        // Slow path: items might be Pydantic models or dataclasses — materialize as dicts.
        // Guard: only attempt if first item is NOT a known basic Python type
        // (int/float/str/bool/None/list/tuple/dict). This avoids O(n) getattr calls
        // on lists like [0, 1, 2] or ["a", "b"] which can never be tables.
        let first = list.get_item(0)?;
        use pyo3::types::{PyBool, PyFloat, PyLong, PyString as PyStr};
        let is_basic = first.is_none()
            || first.is_instance_of::<PyBool>()
            || first.is_instance_of::<PyLong>()
            || first.is_instance_of::<PyFloat>()
            || first.is_instance_of::<PyStr>()
            || first.is_instance_of::<PyList>()
            || first.is_instance_of::<PyTuple>()
            || first.is_instance_of::<PyDict>();

        if !is_basic {
            if let Some(dicts) = materialize_as_dicts(py, list)? {
                let normalized = PyList::new(py, dicts.iter().map(|d| d.as_ref(py)));
                if let Some(headers) = detect_zen_grid_candidate(normalized)? {
                    return write_zen_grid(py, normalized, &headers, buf, opts, depth);
                }
            }
        }
    }

    // Standard array
    write_array(py, list.iter(), len, buf, opts, depth)
}

fn write_tuple<'py>(
    py: Python<'py>,
    obj: &'py PyAny,
    buf: &mut Vec<u8>,
    opts: &DumpsOptions,
    depth: usize,
) -> PyResult<()> {
    let tup: &PyTuple = obj.downcast()?;
    write_array(py, tup.iter(), tup.len(), buf, opts, depth)
}

fn write_array<'py, I>(
    py: Python<'py>,
    iter: I,
    len: usize,
    buf: &mut Vec<u8>,
    opts: &DumpsOptions,
    depth: usize,
) -> PyResult<()>
where
    I: Iterator<Item = &'py PyAny>,
{
    buf.push(b'[');
    let mut i = 0;
    for item in iter {
        if let Some(indent_width) = opts.indent {
            buf.push(b'\n');
            write_indent(buf, (depth + 1) * indent_width);
        }
        write_value(py, item, buf, opts, depth + 1)?;
        i += 1;
        if i < len {
            buf.push(b',');
        }
    }
    if let Some(indent) = opts.indent {
        if len > 0 {
            buf.push(b'\n');
            write_indent(buf, depth * indent);
        }
    }
    buf.push(b']');
    Ok(())
}

// ── Zen Grid detection + serialization ───────────────────────────────────────

/// Detect if a PyList qualifies as a Zen Grid candidate.
/// Returns the ordered header keys if yes, None if the list should stay as JSON.
///
/// Qualifying conditions:
///   - len >= 2
///   - all items are dicts
///   - first item has at least 1 key
///   - ≥70% of items contain all the header keys from the first item
fn detect_zen_grid_candidate(list: &PyList) -> PyResult<Option<Vec<String>>> {
    let len = list.len();
    if len < 2 {
        return Ok(None);
    }

    // First item must be a non-empty dict
    let first = list.get_item(0)?;
    if !first.is_instance_of::<PyDict>() {
        return Ok(None);
    }
    let first_dict: &PyDict = first.downcast()?;
    if first_dict.is_empty() {
        return Ok(None);
    }

    // Collect ordered headers from first row
    let headers: Vec<String> = first_dict
        .keys()
        .iter()
        .map(|k| k.extract::<String>())
        .collect::<PyResult<Vec<_>>>()?;
    let n_headers = headers.len();

    // Fast path: sample up to 10 items. If all have exactly the same keys
    // (same count + all header keys present), accept immediately.
    // This covers the common case of homogeneous API/DB results.
    let sample = len.min(10);
    let mut all_exact = true;

    for i in 1..sample {
        let item = list.get_item(i)?;
        if !item.is_instance_of::<PyDict>() {
            return Ok(None); // non-dict in list → never a table
        }
        let item_dict: &PyDict = item.downcast()?;
        if item_dict.len() != n_headers {
            all_exact = false;
            break;
        }
        for h in &headers {
            if item_dict.get_item(h.as_str())?.is_none() {
                all_exact = false;
                break;
            }
        }
        if !all_exact {
            break;
        }
    }

    if all_exact {
        // All sampled rows matched exactly — accept (also covers len <= 10)
        return Ok(Some(headers));
    }

    // Slow path: coverage check on up to 50 rows (avoids O(n) scan on huge lists)
    let check_size = len.min(50);
    let threshold = (check_size * 7).div_ceil(10); // ceil(check_size * 0.7)
    let mut matching = 0usize;

    for i in 0..check_size {
        let item = list.get_item(i)?;
        if !item.is_instance_of::<PyDict>() {
            return Ok(None);
        }
        let item_dict: &PyDict = item.downcast()?;
        let mut found = 0usize;
        for h in &headers {
            if item_dict.get_item(h.as_str())?.is_some() {
                found += 1;
            }
        }
        if found == n_headers {
            matching += 1;
        }
    }

    if matching >= threshold {
        Ok(Some(headers))
    } else {
        Ok(None)
    }
}

/// Write a Zen Grid table:
///   [: key1, key2, key3; val1, val2, val3; val1, val2, val3 ]
/// With indent:
///   [:
///     key1, key2, key3
///     val1, val2, val3
///   ]
fn write_zen_grid<'py>(
    py: Python<'py>,
    list: &'py PyList,
    headers: &[String],
    buf: &mut Vec<u8>,
    opts: &DumpsOptions,
    depth: usize,
) -> PyResult<()> {
    use pyo3::types::PyString;

    let n_rows = list.len();

    // Pre-create Python key objects ONCE for the whole table.
    // This avoids allocating a temporary PyString per lookup per row
    // (e.g. 100,000 rows × 3 headers → 300,000 allocations saved).
    let py_keys: Vec<PyObject> = headers
        .iter()
        .map(|h| PyString::new(py, h.as_str()).to_object(py))
        .collect();

    if let Some(indent_width) = opts.indent {
        // Multi-line form
        buf.extend_from_slice(b"[:");
        buf.push(b'\n');
        write_indent(buf, (depth + 1) * indent_width);
        // Header row
        for (i, h) in headers.iter().enumerate() {
            if i > 0 {
                buf.extend_from_slice(b", ");
            }
            write_zen_grid_header_key(h, buf, opts);
        }
        // Data rows
        for row_i in 0..n_rows {
            buf.push(b'\n');
            write_indent(buf, (depth + 1) * indent_width);
            write_zen_grid_row(
                py,
                list.get_item(row_i)?.downcast()?,
                &py_keys,
                buf,
                opts,
                depth,
            )?;
        }
        buf.push(b'\n');
        write_indent(buf, depth * indent_width);
        buf.push(b']');
    } else {
        // Compact single-line form: [: h1, h2; v1, v2; v1, v2 ]
        buf.extend_from_slice(b"[: ");
        for (i, h) in headers.iter().enumerate() {
            if i > 0 {
                buf.extend_from_slice(b", ");
            }
            write_zen_grid_header_key(h, buf, opts);
        }
        for row_i in 0..n_rows {
            buf.extend_from_slice(b"; ");
            write_zen_grid_row(
                py,
                list.get_item(row_i)?.downcast()?,
                &py_keys,
                buf,
                opts,
                depth,
            )?;
        }
        buf.extend_from_slice(b" ]");
    }
    Ok(())
}

/// Write a Zen Grid row: val1, val2, val3
/// Uses pre-created PyObject keys and direct FFI dict lookup (no per-call allocation).
fn write_zen_grid_row<'py>(
    py: Python<'py>,
    row: &'py PyDict,
    keys: &[PyObject],
    buf: &mut Vec<u8>,
    opts: &DumpsOptions,
    depth: usize,
) -> PyResult<()> {
    use pyo3::types::PyString;
    for (i, key) in keys.iter().enumerate() {
        if i > 0 {
            buf.extend_from_slice(b", ");
        }
        let val_ptr = unsafe { ffi::PyDict_GetItemWithError(row.as_ptr(), key.as_ptr()) };
        if val_ptr.is_null() {
            if unsafe { ffi::PyErr_Occurred().is_null() } {
                // Key not found → emit empty cell (implicit null) or "null"
                if !opts.implicit_null {
                    buf.extend_from_slice(b"null");
                }
                // If implicit_null: write nothing — empty cell means null on decode
            } else {
                return Err(PyErr::fetch(py));
            }
        } else {
            let val: &PyAny = unsafe { py.from_borrowed_ptr(val_ptr) };
            // implicit_null: treat explicit None values as empty cells too
            if opts.implicit_null && val.is_none() {
                continue; // empty cell = null on decode
            }
            // bare_strings: write identifier-like string values without quotes
            if opts.bare_strings && val.is_instance_of::<PyString>() {
                let mut str_len: ffi::Py_ssize_t = 0;
                let data = unsafe { ffi::PyUnicode_AsUTF8AndSize(val_ptr, &mut str_len) };
                if !data.is_null() {
                    let bytes =
                        unsafe { std::slice::from_raw_parts(data as *const u8, str_len as usize) };
                    if is_valid_identifier(bytes) {
                        buf.extend_from_slice(bytes);
                        continue;
                    }
                } else {
                    unsafe { ffi::PyErr_Clear() };
                }
            }
            write_value(py, val, buf, opts, depth + 1)?;
        }
    }
    Ok(())
}

/// Write a Zen Grid header key (unquoted if valid identifier, quoted otherwise).
#[inline]
fn write_zen_grid_header_key(key: &str, buf: &mut Vec<u8>, _opts: &DumpsOptions) {
    let bytes = key.as_bytes();
    if is_valid_identifier(bytes) {
        buf.extend_from_slice(bytes);
    } else {
        buf.push(b'"');
        write_escaped_str(bytes, buf);
        buf.push(b'"');
    }
}

// ── Pydantic / dataclass fallback ─────────────────────────────────────────────

/// Try to convert all items in a list to dicts (for Zen Grid detection).
/// Handles dicts (pass-through), Pydantic v2 (model_dump), Pydantic v1 (dict()),
/// and dataclasses (dataclasses.asdict). Returns None if any item can't convert.
fn materialize_as_dicts(py: Python, list: &PyList) -> PyResult<Option<Vec<PyObject>>> {
    let len = list.len();
    let mut result = Vec::with_capacity(len);

    for i in 0..len {
        let item = list.get_item(i)?;
        if item.is_instance_of::<PyDict>() {
            result.push(item.to_object(py));
        } else if let Ok(method) = item.getattr("model_dump") {
            // Pydantic v2
            if method.is_callable() {
                let d = method.call0()?;
                result.push(d.to_object(py));
            } else {
                return Ok(None);
            }
        } else if item.hasattr("__dataclass_fields__")? {
            // Python dataclass
            let dc = py.import("dataclasses")?;
            let d = dc.getattr("asdict")?.call1((item,))?;
            result.push(d.to_object(py));
        } else if item.hasattr("__fields__")? {
            // Pydantic v1
            if let Ok(method) = item.getattr("dict") {
                if method.is_callable() {
                    let d = method.call0()?;
                    result.push(d.to_object(py));
                } else {
                    return Ok(None);
                }
            } else {
                return Ok(None);
            }
        } else {
            return Ok(None);
        }
    }
    Ok(Some(result))
}

fn write_fallback<'py>(
    py: Python<'py>,
    obj: &'py PyAny,
    buf: &mut Vec<u8>,
    opts: &DumpsOptions,
    depth: usize,
) -> PyResult<()> {
    // Try Pydantic v2: .model_dump()
    if let Ok(method) = obj.getattr("model_dump") {
        if method.is_callable() {
            let d = method.call0()?;
            return write_value(py, d, buf, opts, depth);
        }
    }
    // Try Pydantic v1: .dict()
    if let Ok(method) = obj.getattr("dict") {
        if method.is_callable() {
            // Guard against plain dicts that happen to have a .dict attr
            if obj.hasattr("__fields__")? {
                let d = method.call0()?;
                return write_value(py, d, buf, opts, depth);
            }
        }
    }
    // Try Python dataclass: dataclasses.asdict()
    if obj.hasattr("__dataclass_fields__")? {
        let dc = py.import("dataclasses")?;
        let d = dc.getattr("asdict")?.call1((obj,))?;
        return write_value(py, d, buf, opts, depth);
    }
    // Final fallback: raise a descriptive TypeError
    Err(pyo3::exceptions::PyTypeError::new_err(format!(
        "Object of type '{}' is not JSON serializable",
        obj.get_type().name().unwrap_or("unknown")
    )))
}

// ── Indent helper ─────────────────────────────────────────────────────────────

#[inline]
fn write_indent(buf: &mut Vec<u8>, count: usize) {
    for _ in 0..count {
        buf.push(b' ');
    }
}
