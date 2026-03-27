//! JTON WebAssembly bindings.
//!
//! Exposes `encode` and `decode` functions callable from JavaScript.
//! Build with: `wasm-pack build --target web --release`
//!
//! Output: pkg/JTON_wasm.js + pkg/JTON_wasm_bg.wasm

use wasm_bindgen::prelude::*;

// ── Re-use the pure-Rust Zen Grid encoder/decoder from c_api logic ────────────
// (Duplicated here to keep JTON_wasm fully self-contained without PyO3.)

#[wasm_bindgen]
pub fn encode(
    json_str: &str,
    zen_grid: bool,
    bare_strings: bool,
    implicit_null: bool,
    row_count: bool,
    multiline_zen: bool,
    delimiter: &str,
) -> Result<String, JsValue> {
    let v: serde_json::Value = serde_json::from_str(json_str)
        .map_err(|e| JsValue::from_str(&format!("JSON parse error: {e}")))?;

    let delim = match delimiter {
        "tab" | "\t" => Delimiter::Tab,
        "pipe" | "|" => Delimiter::Pipe,
        _ => Delimiter::Comma,
    };

    Ok(encode_value(
        &v,
        zen_grid,
        bare_strings,
        implicit_null,
        row_count,
        multiline_zen,
        false,
        delim,
    ))
}

#[wasm_bindgen]
pub fn decode(JTON_str: &str) -> Result<String, JsValue> {
    // Decode Zen Grid back to canonical JSON
    let trimmed = JTON_str.trim();
    let json = if looks_like_zen_grid(trimmed) {
        decode_zen_grid(trimmed)
            .map_err(|_| JsValue::from_str("Failed to decode Zen Grid"))?
    } else {
        // Already valid JSON — re-format it canonically
        let v: serde_json::Value = serde_json::from_str(trimmed)
            .map_err(|e| JsValue::from_str(&format!("Parse error: {e}")))?;
        serde_json::to_string_pretty(&v)
            .map_err(|e| JsValue::from_str(&format!("Encode error: {e}")))?
    };
    Ok(json)
}

#[wasm_bindgen]
pub fn format_hint(style: &str) -> String {
    match style {
        "multiline" => concat!(
            "Data is in JTON Multiline Zen Grid format (TOON-compatible).\n",
            "Header line: [N]{col1,col2,col3}: where N is the row count.\n",
            "Each following indented line is one row with comma-separated values.\n",
            "Example:\n  [3]{id,name,score}:\n    1,Alice,95\n    2,Bob,87\n    3,Carol,92"
        ).to_string(),
        "zen_grid_rowcount" => concat!(
            "Data is in JTON Zen Grid format with explicit row count.\n",
            "Format: [N: col1, col2; val1, val2; ... ] where N = total rows.\n",
            "Example: [3: id, name, score; 1, Alice, 95; 2, Bob, 87; 3, Carol, 92 ]"
        ).to_string(),
        "tab" => concat!(
            "Data is in JTON Zen Grid tab-delimited format.\n",
            "Fields/values separated by tab characters (\\t).\n",
            "Example: [: id\\tname\\tscore; 1\\tAlice\\t95; 2\\tBob\\t87 ]"
        ).to_string(),
        _ => concat!(
            "Data is in JTON Zen Grid format.\n",
            "Format: [: col1, col2; row1val1, row1val2; row2val1, row2val2 ]\n",
            "The first semicolon-delimited segment = headers. Each subsequent = one record.\n",
            "Example: [: id, name, score; 1, Alice, 95; 2, Bob, 87; 3, Carol, 92 ]"
        ).to_string(),
    }
}

// ── Internal encoder ──────────────────────────────────────────────────────────

#[derive(Clone, Copy)]
enum Delimiter { Comma, Tab, Pipe }

impl Delimiter {
    fn sep(self) -> &'static str {
        match self { Delimiter::Comma => ", ", Delimiter::Tab => "\t", Delimiter::Pipe => " | " }
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
    delimiter: Delimiter,
) -> String {
    use serde_json::Value;
    match v {
        Value::Null => "null".into(),
        Value::Bool(b) => if *b { "true".into() } else { "false".into() },
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
                    c if (c as u32) < 0x20 => { out.push_str(&format!("\\u{:04x}", c as u32)); }
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
                    out.push('"'); out.push_str(k); out.push('"');
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
        Some(c) if c.is_ascii_alphabetic() || c == '_' || c == '$' => {}
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
    delimiter: Delimiter,
) -> Option<String> {
    let first = arr[0].as_object()?;
    let headers: Vec<&str> = first.keys().map(|k| k.as_str()).collect();
    // Verify all rows are objects with compatible keys
    for item in arr {
        if !item.is_object() { return None; }
    }
    let n = arr.len();
    let sep = delimiter.sep();

    if multiline_zen {
        let mut out = std::string::String::new();
        out.push('[');
        out.push_str(&n.to_string());
        out.push_str("]{");
        for (i, h) in headers.iter().enumerate() {
            if i > 0 { out.push(','); }
            out.push_str(h);
        }
        out.push_str("}:\n");
        for row in arr {
            let obj = row.as_object()?;
            out.push_str("  ");
            for (i, h) in headers.iter().enumerate() {
                if i > 0 { out.push_str(sep); }
                match obj.get(*h) {
                    None | Some(serde_json::Value::Null) => {
                        if !implicit_null { out.push_str("null"); }
                    }
                    Some(v) => out.push_str(&encode_cell(v, bare_strings)),
                }
            }
            out.push('\n');
        }
        // Remove trailing newline
        if out.ends_with('\n') { out.pop(); }
        return Some(out);
    }

    let mut out = std::string::String::from("[");
    if row_count {
        out.push_str(&n.to_string());
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
            match obj.get(*h) {
                None | Some(serde_json::Value::Null) => {
                    if !implicit_null { out.push_str("null"); }
                }
                Some(v) => out.push_str(&encode_cell(v, bare_strings)),
            }
        }
    }
    out.push_str(" ]");
    Some(out)
}

fn encode_cell(v: &serde_json::Value, bare_strings: bool) -> String {
    match v {
        serde_json::Value::String(s) if bare_strings && is_identifier(s) => s.clone(),
        other => encode_value(other, false, false, false, false, false, false, Delimiter::Comma),
    }
}

// ── Internal decoder ──────────────────────────────────────────────────────────

fn looks_like_zen_grid(s: &str) -> bool {
    let s = s.trim_start();
    if !s.starts_with('[') { return false; }
    // Matches [: or [N: or [N]{
    let inner = &s[1..];
    inner.starts_with(':') || inner.starts_with(|c: char| c.is_ascii_digit())
}

fn decode_zen_grid(s: &str) -> Result<String, ()> {
    let s = s.trim();
    // Multiline: [N]{fields}:\n  rows
    if let Some(brace) = s.find("]{") {
        return decode_multiline(s, brace);
    }
    decode_inline(s)
}

fn decode_inline(s: &str) -> Result<String, ()> {
    let inner = s.trim_start_matches('[');
    let inner = match inner.rfind(']') {
        Some(i) => &inner[..i],
        None => return Err(()),
    };
    let colon_pos = inner.find(':').ok_or(())?;
    let rest = &inner[colon_pos + 1..];
    let segments: Vec<&str> = rest.split(';').collect();
    if segments.is_empty() { return Err(()); }

    let detect_delim = |seg: &str| -> &'static str {
        if seg.contains('\t') { "\t" } else if seg.contains(" | ") { " | " } else { "," }
    };
    let delim = detect_delim(segments[0]);
    let headers: Vec<&str> = segments[0].split(delim).map(str::trim).collect();

    let mut rows = Vec::new();
    for seg in &segments[1..] {
        let seg = seg.trim();
        if seg.is_empty() { continue; }
        let values: Vec<&str> = seg.split(delim).map(str::trim).collect();
        let mut obj = std::collections::BTreeMap::new();
        for (h, v) in headers.iter().zip(values.iter().chain(std::iter::repeat(&"null"))) {
            let key = h.trim_matches('"').to_string();
            let val: serde_json::Value = if v.is_empty() {
                serde_json::Value::Null
            } else {
                serde_json::from_str(v).unwrap_or_else(|_| serde_json::Value::String(v.to_string()))
            };
            obj.insert(key, val);
        }
        rows.push(serde_json::Value::Object(obj.into_iter().collect()));
    }
    serde_json::to_string_pretty(&serde_json::Value::Array(rows)).map_err(|_| ())
}

fn decode_multiline(s: &str, brace_end: usize) -> Result<String, ()> {
    let field_start = brace_end + 2;
    let field_end = s[field_start..].find("}:").ok_or(())?;
    let fields_str = &s[field_start..field_start + field_end];
    let headers: Vec<&str> = fields_str.split(',').map(str::trim).collect();
    let data_start = field_start + field_end + 2;
    let data = &s[data_start..];
    let mut rows = Vec::new();
    for line in data.lines() {
        let line = line.trim();
        if line.is_empty() { continue; }
        let values: Vec<&str> = line.split(',').map(str::trim).collect();
        let mut obj = std::collections::BTreeMap::new();
        for (h, v) in headers.iter().zip(values.iter().chain(std::iter::repeat(&"null"))) {
            let key = h.trim_matches('"').to_string();
            let val: serde_json::Value = if v.is_empty() {
                serde_json::Value::Null
            } else {
                serde_json::from_str(v).unwrap_or_else(|_| serde_json::Value::String(v.to_string()))
            };
            obj.insert(key, val);
        }
        rows.push(serde_json::Value::Object(obj.into_iter().collect()));
    }
    serde_json::to_string_pretty(&serde_json::Value::Array(rows)).map_err(|_| ())
}

