// JTON C ABI — stable C-compatible interface for multi-language bindings.
//
// Exposes JTON encode/decode/token_count as `extern "C"` functions.
// Any language with C FFI can call these:
//   Ruby (FFI gem), Go (CGO), Java (JNA), PHP (FFI ext), .NET (P/Invoke),
//   Node.js (node-ffi-napi), R (Rcpp/ffi), Swift (bridging header), etc.
//
// Memory contract:
//   - All returned pointers are heap-allocated by Rust.
//   - Callers MUST call `jton_free(ptr, len)` when done.
//   - Input pointers (json_ptr / jton_ptr) must remain valid for the duration of the call.
//   - All strings are valid UTF-8.
//
// Build output: libjton.so (Linux), libjton.dylib (macOS), jton.dll (Windows)
// Header generation: run `cbindgen --crate jton_core --output include/jton.h`

use std::slice;

// ── Re-export option flags (mirrors DumpsOptions) ───────────────────────────

/// Flags for jton_encode — combine with bitwise OR.
/// Bit 0: ZEN_GRID (default: on when 0 — pass JTON_NO_ZEN_GRID to disable)
pub const JTON_ZEN_GRID: u32 = 0b0000_0001;
pub const JTON_BARE_STRINGS: u32 = 0b0000_0010;
pub const JTON_IMPLICIT_NULL: u32 = 0b0000_0100;
pub const JTON_ROW_COUNT: u32 = 0b0000_1000;
pub const JTON_MULTILINE_ZEN: u32 = 0b0001_0000;
pub const JTON_UNQUOTED_KEYS: u32 = 0b0010_0000;
pub const JTON_DELIMITER_TAB: u32 = 0b0100_0000;
pub const JTON_DELIMITER_PIPE: u32 = 0b1000_0000;
/// Disable zen grid (when this flag is set, output is compact JSON)
pub const JTON_NO_ZEN_GRID: u32 = 0b0001_0000_0000;

// ── encode ───────────────────────────────────────────────────────────────────

/// Encode a JSON string to JTON Zen Grid format.
///
/// # Parameters
/// - `json_ptr`: Pointer to UTF-8 JSON bytes (not null-terminated).
/// - `json_len`: Length of the JSON input in bytes.
/// - `flags`:    Bitwise OR of JTON_* constants. 0 = default (zen_grid=true, comma delimiter).
/// - `out_len`:  Out-parameter filled with the length of the returned string.
///
/// # Returns
/// Pointer to a heap-allocated UTF-8 string. Must be freed with `jton_free(ptr, out_len)`.
/// Returns null on error (invalid UTF-8 or JSON parse failure).
#[no_mangle]
pub extern "C" fn jton_encode(
    json_ptr: *const u8,
    json_len: usize,
    flags: u32,
    out_len: *mut usize,
) -> *mut u8 {
    let json_bytes = unsafe { slice::from_raw_parts(json_ptr, json_len) };
    let json_str = match std::str::from_utf8(json_bytes) {
        Ok(s) => s,
        Err(_) => return std::ptr::null_mut(),
    };

    // Parse JSON to serde_json::Value, then re-encode with Zen Grid logic.
    // For the C ABI we use serde_json (no PyO3 dependency) — pure Rust path.
    let value: serde_json::Value = match serde_json::from_str(json_str) {
        Ok(v) => v,
        Err(_) => return std::ptr::null_mut(),
    };

    let zen_grid = (flags & JTON_NO_ZEN_GRID) == 0;
    let bare_strings = (flags & JTON_BARE_STRINGS) != 0;
    let implicit_null = (flags & JTON_IMPLICIT_NULL) != 0;
    let row_count = (flags & JTON_ROW_COUNT) != 0;
    let multiline_zen = (flags & JTON_MULTILINE_ZEN) != 0;
    let unquoted_keys = (flags & JTON_UNQUOTED_KEYS) != 0;
    let delimiter = if (flags & JTON_DELIMITER_TAB) != 0 {
        CApiDelimiter::Tab
    } else if (flags & JTON_DELIMITER_PIPE) != 0 {
        CApiDelimiter::Pipe
    } else {
        CApiDelimiter::Comma
    };

    let result = encode_value(
        &value,
        zen_grid,
        bare_strings,
        implicit_null,
        row_count,
        multiline_zen,
        unquoted_keys,
        delimiter,
    );

    let bytes = result.into_bytes();
    unsafe { *out_len = bytes.len() };
    let mut boxed = bytes.into_boxed_slice();
    let ptr = boxed.as_mut_ptr();
    std::mem::forget(boxed);
    ptr
}

/// Decode a JTON string back to compact JSON.
///
/// # Parameters
/// - `jton_ptr`: Pointer to UTF-8 JTON bytes (not null-terminated).
/// - `jton_len`: Length in bytes.
/// - `out_len`:  Out-parameter filled with the length of the returned JSON string.
///
/// # Returns
/// Pointer to heap-allocated compact JSON UTF-8 string. Free with `jton_free(ptr, out_len)`.
/// Returns null on parse error.
#[no_mangle]
pub extern "C" fn jton_decode(
    jton_ptr: *const u8,
    jton_len: usize,
    out_len: *mut usize,
) -> *mut u8 {
    let jton_bytes = unsafe { slice::from_raw_parts(jton_ptr, jton_len) };
    let jton_str = match std::str::from_utf8(jton_bytes) {
        Ok(s) => s,
        Err(_) => return std::ptr::null_mut(),
    };

    // JTON Zen Grid is a superset of JSON — try direct JSON parse first,
    // then fall back to Zen Grid parse.
    let json_str = match decode_jton_to_json(jton_str) {
        Ok(s) => s,
        Err(_) => return std::ptr::null_mut(),
    };

    let bytes = json_str.into_bytes();
    unsafe { *out_len = bytes.len() };
    let mut boxed = bytes.into_boxed_slice();
    let ptr = boxed.as_mut_ptr();
    std::mem::forget(boxed);
    ptr
}

/// Free a string returned by `jton_encode` or `jton_decode`.
///
/// # Safety
/// `ptr` must have been returned by `jton_encode` or `jton_decode`, and
/// `len` must match the value written to `out_len` in that call.
#[no_mangle]
pub extern "C" fn jton_free(ptr: *mut u8, len: usize) {
    if !ptr.is_null() {
        let _ = unsafe { Box::from_raw(slice::from_raw_parts_mut(ptr, len)) };
    }
}

/// Return a null-terminated format hint string for the given style.
/// Caller does NOT need to free this — it points to a static string.
///
/// `style`: 0=zen_grid, 1=zen_grid_rowcount, 2=multiline, 3=tab
#[no_mangle]
pub extern "C" fn jton_format_hint(style: u32) -> *const u8 {
    let s: &'static str = match style {
        1 => "Data is in JTON Zen Grid format with explicit row count.\nFormat: [N: col1, col2; row1val1, row1val2; row2val1, ... ]\n\0",
        2 => "Data is in JTON Multiline Zen Grid format (TOON-compatible).\nHeader: [N]{col1,col2}: — each following line is one row.\n\0",
        3 => "Data is in JTON Zen Grid tab-delimited format.\nFormat: [: col1\\tcol2; val1\\tval2; ... ]\n\0",
        _ => "Data is in JTON Zen Grid format.\nFormat: [: col1, col2; row1val1, row1val2; ... ]\nThe first segment after [: is field names; each ; segment is one row.\n\0",
    };
    s.as_ptr()
}

// ── Internal pure-Rust encoder / decoder (no PyO3) ──────────────────────────

#[derive(Clone, Copy)]
enum CApiDelimiter { Comma, Tab, Pipe }

impl CApiDelimiter {
    fn sep(self) -> &'static str {
        match self {
            CApiDelimiter::Comma => ", ",
            CApiDelimiter::Tab => "\t",
            CApiDelimiter::Pipe => " | ",
        }
    }
}

fn encode_value(
    v: &serde_json::Value,
    zen_grid: bool,
    bare_strings: bool,
    implicit_null: bool,
    row_count: bool,
    multiline_zen: bool,
    unquoted_keys: bool,
    delimiter: CApiDelimiter,
) -> std::string::String {
    use serde_json::Value;
    match v {
        Value::Null => "null".to_string(),
        Value::Bool(b) => if *b { "true".to_string() } else { "false".to_string() },
        Value::Number(n) => n.to_string(),
        Value::String(s) => {
            let mut out = std::string::String::with_capacity(s.len() + 2);
            out.push('"');
            for c in s.chars() {
                match c {
                    '"' => out.push_str("\\\""),
                    '\\' => out.push_str("\\\\"),
                    '\n' => out.push_str("\\n"),
                    '\r' => out.push_str("\\r"),
                    '\t' => out.push_str("\\t"),
                    c if (c as u32) < 0x20 => {
                        out.push_str(&format!("\\u{:04x}", c as u32));
                    }
                    c => out.push(c),
                }
            }
            out.push('"');
            out
        }
        Value::Object(map) => {
            let mut out = std::string::String::from("{");
            for (i, (k, val)) in map.iter().enumerate() {
                if i > 0 { out.push(','); }
                if unquoted_keys && is_identifier(k) {
                    out.push_str(k);
                } else {
                    out.push('"');
                    out.push_str(k);
                    out.push('"');
                }
                out.push(':');
                out.push_str(&encode_value(val, zen_grid, bare_strings, implicit_null, row_count, multiline_zen, unquoted_keys, delimiter));
            }
            out.push('}');
            out
        }
        Value::Array(arr) => {
            if zen_grid && arr.len() >= 2 {
                if let Some(result) = try_zen_grid(arr, bare_strings, implicit_null, row_count, multiline_zen, delimiter) {
                    return result;
                }
            }
            let mut out = std::string::String::from("[");
            for (i, item) in arr.iter().enumerate() {
                if i > 0 { out.push(','); }
                out.push_str(&encode_value(item, zen_grid, bare_strings, implicit_null, row_count, multiline_zen, unquoted_keys, delimiter));
            }
            out.push(']');
            out
        }
    }
}

fn is_identifier(s: &str) -> bool {
    let mut chars = s.chars();
    match chars.next() {
        Some(c) if c.is_ascii_alphabetic() || c == '_' || c == '$' => {},
        _ => return false,
    }
    chars.all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '$' || c == '-')
}

fn try_zen_grid(
    arr: &[serde_json::Value],
    bare_strings: bool,
    implicit_null: bool,
    row_count: bool,
    multiline_zen: bool,
    delimiter: CApiDelimiter,
) -> Option<String> {
    // All items must be objects with the same keys
    let first = arr[0].as_object()?;
    if first.is_empty() { return None; }
    let headers: Vec<&str> = first.keys().map(|k| k.as_str()).collect();
    let n = headers.len();

    // Validate ≥ 70% of rows match
    let check = arr.len().min(50);
    let threshold = (check * 7).div_ceil(10);
    let matching = arr[..check].iter().filter(|item| {
        item.as_object().map_or(false, |obj| {
            headers.iter().all(|h| obj.contains_key(*h)) && obj.len() == n
        })
    }).count();
    if matching < threshold { return None; }

    let sep = delimiter.sep();
    let n_rows = arr.len();

    if multiline_zen {
        // [N]{h1,h2}:\n  v1,v2\n  v3,v4
        let mut out = format!("[{}]{{", n_rows);
        for (i, h) in headers.iter().enumerate() {
            if i > 0 { out.push(','); }
            out.push_str(h);
        }
        out.push_str("}:");
        for row in arr {
            out.push('\n');
            out.push_str("  ");
            let obj = row.as_object()?;
            for (i, h) in headers.iter().enumerate() {
                if i > 0 { out.push(','); }
                write_cell(&mut out, obj.get(*h), bare_strings, implicit_null);
            }
        }
        return Some(out);
    }

    // Compact inline
    let mut out = String::from("[");
    if row_count {
        out.push_str(&n_rows.to_string());
    }
    out.push_str(": ");
    for (i, h) in headers.iter().enumerate() {
        if i > 0 { out.push_str(sep); }
        out.push_str(h);
    }
    for row in arr {
        out.push_str("; ");
        let obj = row.as_object()?;
        for (i, h) in headers.iter().enumerate() {
            if i > 0 { out.push_str(sep); }
            write_cell(&mut out, obj.get(*h), bare_strings, implicit_null);
        }
    }
    out.push_str(" ]");
    Some(out)
}

fn write_cell(
    out: &mut String,
    val: Option<&serde_json::Value>,
    bare_strings: bool,
    implicit_null: bool,
) {
    match val {
        None | Some(serde_json::Value::Null) if implicit_null => {},
        None => out.push_str("null"),
        Some(v) => match v {
            serde_json::Value::Null => {
                if !implicit_null { out.push_str("null"); }
            }
            serde_json::Value::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
            serde_json::Value::Number(n) => out.push_str(&n.to_string()),
            serde_json::Value::String(s) if bare_strings && is_identifier(s) => out.push_str(s),
            serde_json::Value::String(s) => {
                out.push('"');
                for c in s.chars() {
                    match c {
                        '"' => out.push_str("\\\""),
                        '\\' => out.push_str("\\\\"),
                        '\n' => out.push_str("\\n"),
                        c => out.push(c),
                    }
                }
                out.push('"');
            }
            other => out.push_str(&serde_json::to_string(other).unwrap_or_else(|_| "null".to_string())),
        }
    }
}

fn decode_jton_to_json(input: &str) -> Result<String, ()> {
    // Try standard JSON parse first (JTON is a JSON superset for parsing)
    if let Ok(v) = serde_json::from_str::<serde_json::Value>(input) {
        return serde_json::to_string(&v).map_err(|_| ());
    }
    // Try Zen Grid parse: [N?: h1, h2; v1, v2; ... ] or [N]{h1,h2}:\n  v1,v2
    decode_zen_grid(input)
}

fn decode_zen_grid(input: &str) -> Result<String, ()> {
    let s = input.trim();

    // Multiline: [N]{fields}:\n  row1\n  row2
    if s.starts_with('[') && s.contains("]{") && s.contains("}:") {
        return decode_zen_grid_multiline(s);
    }

    // Inline: [N?: h1, h2; v1, v2; ... ]
    if s.starts_with('[') && s.contains(':') && s.ends_with(']') {
        return decode_zen_grid_inline(s);
    }

    Err(())
}

fn decode_zen_grid_inline(s: &str) -> Result<String, ()> {
    // Strip outer [ ... ]
    let inner = s.trim_start_matches('[');
    let inner = match inner.rfind(']') {
        Some(i) => &inner[..i],
        None => return Err(()),
    };

    // Find colon (may be preceded by optional row count)
    let colon_pos = inner.find(':').ok_or(())?;
    let rest = &inner[colon_pos + 1..]; // everything after the colon

    // Split by semicolons
    let segments: Vec<&str> = rest.split(';').collect();
    if segments.is_empty() { return Err(()); }

    // First segment: headers
    let detect_delimiter = |seg: &str| -> &'static str {
        if seg.contains('\t') { "\t" } else if seg.contains('|') { "|" } else { "," }
    };
    let delim = detect_delimiter(segments[0]);
    let headers: Vec<&str> = segments[0].split(delim).map(str::trim).collect();

    // Remaining segments: rows
    let mut rows = Vec::new();
    for seg in &segments[1..] {
        let seg = seg.trim();
        if seg.is_empty() { continue; }
        let values: Vec<&str> = seg.split(delim).map(str::trim).collect();
        let mut obj = String::from("{");
        for (i, (h, v)) in headers.iter().zip(values.iter().chain(std::iter::repeat(&"null"))).enumerate() {
            if i > 0 { obj.push(','); }
            obj.push('"');
            obj.push_str(h.trim_matches('"'));
            obj.push_str("\":");
            obj.push_str(&parse_cell_value(v));
        }
        obj.push('}');
        rows.push(obj);
    }

    Ok(format!("[{}]", rows.join(",")))
}

fn decode_zen_grid_multiline(s: &str) -> Result<String, ()> {
    let brace_end = s.find("]{").ok_or(())?;
    let field_start = brace_end + 2;
    let field_end = s[field_start..].find("}:").ok_or(())?;
    let fields_str = &s[field_start..field_start + field_end];
    let headers: Vec<&str> = fields_str.split(',').map(str::trim).collect();

    let data_start = field_start + field_end + 2; // skip }:
    let data = &s[data_start..];

    let mut rows = Vec::new();
    for line in data.lines() {
        let line = line.trim();
        if line.is_empty() { continue; }
        let values: Vec<&str> = line.split(',').map(str::trim).collect();
        let mut obj = String::from("{");
        for (i, (h, v)) in headers.iter().zip(values.iter().chain(std::iter::repeat(&"null"))).enumerate() {
            if i > 0 { obj.push(','); }
            obj.push('"');
            obj.push_str(h.trim_matches('"'));
            obj.push_str("\":");
            obj.push_str(&parse_cell_value(v));
        }
        obj.push('}');
        rows.push(obj);
    }

    Ok(format!("[{}]", rows.join(",")))
}

fn parse_cell_value(v: &str) -> String {
    let v = v.trim();
    if v.is_empty() || v == "null" { return "null".to_string(); }
    if v == "true" || v == "false" { return v.to_string(); }
    if v.starts_with('"') { return v.to_string(); }
    if v.parse::<i64>().is_ok() || v.parse::<f64>().is_ok() { return v.to_string(); }
    // Bare identifier string → quote it
    format!("\"{}\"", v.replace('"', "\\\""))
}
