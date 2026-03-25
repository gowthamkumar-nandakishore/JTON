// Ultra-fast number parsing inspired by yyjson and orjson
// Three-path strategy: UINT (unsigned) / SINT (signed) / REAL (float)
// Integers: streaming accumulation (value = value * 10 + digit)
// Floats: lexical-core (same algorithm used by orjson)

use pyo3::prelude::*;
use pyo3::ffi;

#[inline(always)]
fn equals_ascii_ci(bytes: &[u8], keyword: &[u8]) -> bool {
    bytes.len() == keyword.len()
        && bytes
            .iter()
            .zip(keyword.iter())
            .all(|(&candidate, &expected)| candidate.to_ascii_lowercase() == expected.to_ascii_lowercase())
}

/// Three-path number parser: detect type early and route to specialized parser
#[inline(always)]
pub fn parse_number_fast(py: Python, bytes: &[u8]) -> PyResult<PyObject> {
    if bytes.is_empty() {
        return Err(pyo3::exceptions::PyValueError::new_err("Empty number"));
    }

    if bytes[0] == b'+' {
        return Err(pyo3::exceptions::PyValueError::new_err("Invalid number"));
    }

    let mut pos = 0;
    let is_negative = bytes[0] == b'-';
    
    if is_negative {
        pos = 1;
        if pos >= bytes.len() {
            return Err(pyo3::exceptions::PyValueError::new_err("Invalid number"));
        }
    }

    let literal = &bytes[pos..];
    if equals_ascii_ci(literal, b"nan") {
        let mut value = f64::NAN;
        if is_negative {
            value = -value;
        }
        return unsafe {
            let py_obj = ffi::PyFloat_FromDouble(value);
            if py_obj.is_null() {
                ffi::PyErr_Clear();
                return Err(pyo3::exceptions::PyValueError::new_err("Failed to create float"));
            }
            Ok(PyObject::from_owned_ptr(py, py_obj))
        };
    }
    if equals_ascii_ci(literal, b"inf") || equals_ascii_ci(literal, b"infinity") {
        let value = if is_negative { f64::NEG_INFINITY } else { f64::INFINITY };
        return unsafe {
            let py_obj = ffi::PyFloat_FromDouble(value);
            if py_obj.is_null() {
                ffi::PyErr_Clear();
                return Err(pyo3::exceptions::PyValueError::new_err("Failed to create float"));
            }
            Ok(PyObject::from_owned_ptr(py, py_obj))
        };
    }

    // JSON validation: first char after sign must be a digit (rejects `-.5`)
    if !bytes[pos].is_ascii_digit() {
        return Err(pyo3::exceptions::PyValueError::new_err("Invalid number"));
    }

    // JSON validation: no leading zeros (`01`, `-01`, `-012`)
    // Exception: `0` alone, `0.x`, `0ex` are valid
    if bytes[pos] == b'0' {
        if let Some(&next) = bytes.get(pos + 1) {
            if next.is_ascii_digit() {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    "Invalid number: leading zeros not allowed",
                ));
            }
        }
    }

    // TYPE DETECTION: Scan to detect if this is integer or float
    // This is the key optimization - we determine the path early
    let start = pos;
    let mut has_dot = false;
    let mut has_exp = false;
    let mut has_frac_digit = false; // tracks whether we see a digit after the decimal point

    while pos < bytes.len() {
        match bytes[pos] {
            b'0'..=b'9' => pos += 1,
            b'.' => {
                has_dot = true;
                pos += 1;
                break;
            }
            b'e' | b'E' => {
                has_exp = true;
                pos += 1;
                break;
            }
            _ => break,
        }
    }

    // Finish scanning if we found . or e
    if has_dot || has_exp {
        while pos < bytes.len() {
            match bytes[pos] {
                b'0'..=b'9' => {
                    // Track digits in the fractional part (before any exponent)
                    if has_dot && !has_exp {
                        has_frac_digit = true;
                    }
                    pos += 1;
                }
                b'e' | b'E' if has_dot && !has_exp => {
                    // JSON requires at least one digit after '.' before 'e'
                    // Rejects `1.e5`, `0.e1`, `2.e3`
                    if !has_frac_digit {
                        return Err(pyo3::exceptions::PyValueError::new_err(
                            "Invalid number: decimal point must be followed by digits",
                        ));
                    }
                    has_exp = true;
                    pos += 1;
                    if pos < bytes.len() && (bytes[pos] == b'+' || bytes[pos] == b'-') {
                        pos += 1;
                    }
                }
                b'+' | b'-' if has_exp => pos += 1,
                _ => break,
            }
        }
    }

    // JSON validation: trailing decimal point is invalid (`1.`, `-2.`)
    if has_dot && !has_frac_digit {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Invalid number: decimal point must be followed by digits",
        ));
    }

    // Validate all bytes were consumed.
    // The boundary scanner in index_parser.rs includes '+'/'-' as number chars
    // (needed for `1e+5`) but this can greedily consume `1+2` as one token.
    // This check ensures the full slice forms a valid number.
    if pos < bytes.len() {
        return Err(pyo3::exceptions::PyValueError::new_err("Invalid number"));
    }

    // Route to specialized parser based on detected type
    if !has_dot && !has_exp {
        // INTEGER PATH (UINT or SINT)
        parse_integer_direct(py, &bytes[start..], is_negative)
    } else {
        // FLOAT PATH (REAL)
        parse_float_direct(py, bytes)
    }
}

/// Fast integer parsing — accumulates decimal digits into u64, then routes to FFI.
#[inline(always)]
fn parse_integer_direct(py: Python, bytes: &[u8], is_negative: bool) -> PyResult<PyObject> {
    let len = bytes.len();

    if len == 0 {
        return Err(pyo3::exceptions::PyValueError::new_err("Invalid number"));
    }

    // Fast path for integers up to 19 digits.
    // u64::MAX = 18_446_744_073_709_551_615 (20 digits), so any 19-digit decimal
    // fits. We still use checked arithmetic as a safety net — if a bug upstream
    // somehow passed a larger value, we fall through to parse_large_integer
    // rather than producing silently-wrapped garbage.
    if len <= 19 {
        let mut value: u64 = 0;
        let mut overflow = false;

        for &b in bytes {
            if !b.is_ascii_digit() {
                return Err(pyo3::exceptions::PyValueError::new_err("Invalid integer"));
            }
            match value.checked_mul(10).and_then(|v| v.checked_add((b - b'0') as u64)) {
                Some(v) => value = v,
                None => {
                    overflow = true;
                    break;
                }
            }
        }

        if overflow {
            return parse_large_integer(py, bytes, is_negative);
        }

        // Apply sign and choose the right Python int type
        if is_negative {
            // i64::MIN = -9_223_372_036_854_775_808
            if value > 9_223_372_036_854_775_808 {
                return parse_large_integer(py, bytes, is_negative);
            }
            let signed_value = -(value as i64);
            unsafe {
                let py_obj = ffi::PyLong_FromLongLong(signed_value);
                if py_obj.is_null() {
                    ffi::PyErr_Clear();
                    return Err(pyo3::exceptions::PyValueError::new_err("Failed to create integer"));
                }
                Ok(PyObject::from_owned_ptr(py, py_obj))
            }
        } else {
            if value > i64::MAX as u64 {
                // Positive but too large for i64 — use unsigned path
                unsafe {
                    let py_obj = ffi::PyLong_FromUnsignedLongLong(value);
                    if py_obj.is_null() {
                        ffi::PyErr_Clear();
                        return Err(pyo3::exceptions::PyValueError::new_err("Failed to create integer"));
                    }
                    Ok(PyObject::from_owned_ptr(py, py_obj))
                }
            } else {
                unsafe {
                    let py_obj = ffi::PyLong_FromLongLong(value as i64);
                    if py_obj.is_null() {
                        ffi::PyErr_Clear();
                        return Err(pyo3::exceptions::PyValueError::new_err("Failed to create integer"));
                    }
                    Ok(PyObject::from_owned_ptr(py, py_obj))
                }
            }
        }
    } else {
        parse_large_integer(py, bytes, is_negative)
    }
}

/// Large integer parsing via Python's string API
#[inline]
fn parse_large_integer(py: Python, bytes: &[u8], is_negative: bool) -> PyResult<PyObject> {
    let num_str = unsafe { std::str::from_utf8_unchecked(bytes) };
    let py_str = if is_negative {
        format!("-{}", num_str)
    } else {
        num_str.to_string()
    };
    
    unsafe {
        let c_str = std::ffi::CString::new(py_str).unwrap();
        let py_obj = ffi::PyLong_FromString(c_str.as_ptr(), std::ptr::null_mut(), 10);
        if py_obj.is_null() {
            ffi::PyErr_Clear();
            return Err(pyo3::exceptions::PyValueError::new_err("Failed to create large integer"));
        }
        Ok(PyObject::from_owned_ptr(py, py_obj))
    }
}

/// Fast float parsing using lexical-core
/// This is much faster than Rust's standard str::parse
#[inline(always)]
fn parse_float_direct(py: Python, bytes: &[u8]) -> PyResult<PyObject> {
    // Use lexical-core for fast float parsing (same as orjson uses)
    match lexical_core::parse::<f64>(bytes) {
        Ok(value) => unsafe {
            // DIRECT FFI: PyFloat_FromDouble
            let py_obj = ffi::PyFloat_FromDouble(value);
            if py_obj.is_null() {
                ffi::PyErr_Clear();
                return Err(pyo3::exceptions::PyValueError::new_err("Failed to create float"));
            }
            Ok(PyObject::from_owned_ptr(py, py_obj))
        },
        Err(_) => Err(pyo3::exceptions::PyValueError::new_err("Invalid float")),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_integer() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let result = parse_number_fast(py, b"123").unwrap();
            assert_eq!(result.extract::<i64>(py).unwrap(), 123);

            let result = parse_number_fast(py, b"-456").unwrap();
            assert_eq!(result.extract::<i64>(py).unwrap(), -456);
        });
    }

    #[test]
    fn test_parse_float() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let result = parse_number_fast(py, b"123.456").unwrap();
            assert!((result.extract::<f64>(py).unwrap() - 123.456).abs() < 0.001);

            let result = parse_number_fast(py, b"1.5e2").unwrap();
            assert!((result.extract::<f64>(py).unwrap() - 150.0).abs() < 0.001);
        });
    }

    #[test]
    fn test_parse_special() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let result = parse_number_fast(py, b"Infinity").unwrap();
            assert!(result.extract::<f64>(py).unwrap().is_infinite());

            let result = parse_number_fast(py, b"NaN").unwrap();
            assert!(result.extract::<f64>(py).unwrap().is_nan());
        });
    }
}
