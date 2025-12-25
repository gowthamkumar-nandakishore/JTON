// Ultra-fast number parsing inspired by yyjson and orjson
// Three-path strategy: UINT (unsigned) / SINT (signed) / REAL (float)
// Uses power-of-10 tables and direct FFI for maximum performance

use pyo3::prelude::*;
use pyo3::ffi;

// Power-of-10 table for fast integer multiplication (10^0 through 10^19)
// This avoids repeated multiplication and is the key to fast integer parsing
const POW10_U64: [u64; 20] = [
    1,
    10,
    100,
    1_000,
    10_000,
    100_000,
    1_000_000,
    10_000_000,
    100_000_000,
    1_000_000_000,
    10_000_000_000,
    100_000_000_000,
    1_000_000_000_000,
    10_000_000_000_000,
    100_000_000_000_000,
    1_000_000_000_000_000,
    10_000_000_000_000_000,
    100_000_000_000_000_000,
    1_000_000_000_000_000_000,
    10_000_000_000_000_000_000,
];

#[inline(always)]
fn equals_ascii_ci(bytes: &[u8], keyword: &[u8]) -> bool {
    bytes.len() == keyword.len()
        && bytes
            .iter()
            .zip(keyword.iter())
            .all(|(&candidate, &expected)| candidate.to_ascii_lowercase() == expected.to_ascii_lowercase())
}

/// Three-path number parser: detect type early and route to specialized parser
#[inline]
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

    // TYPE DETECTION: Scan to detect if this is integer or float
    // This is the key optimization - we determine the path early
    let start = pos;
    let mut has_dot = false;
    let mut has_exp = false;
    
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
                b'0'..=b'9' => pos += 1,
                b'e' | b'E' if has_dot && !has_exp => {
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

    // Route to specialized parser based on detected type
    if !has_dot && !has_exp {
        // INTEGER PATH (UINT or SINT)
        parse_integer_direct(py, &bytes[start..pos], is_negative)
    } else {
        // FLOAT PATH (REAL)
        parse_float_direct(py, bytes)
    }
}

/// Fast integer parsing using power-of-10 table
/// This is dramatically faster than character-by-character multiplication
#[inline(always)]
fn parse_integer_direct(py: Python, bytes: &[u8], is_negative: bool) -> PyResult<PyObject> {
    let len = bytes.len();
    
    if len == 0 {
        return Err(pyo3::exceptions::PyValueError::new_err("Invalid number"));
    }

    // Fast path for small integers (up to 19 digits fits in u64)
    if len <= 19 {
        let mut value: u64 = 0;
        
        // Parse digits using power-of-10 table (much faster than repeated *10)
        for (i, &b) in bytes.iter().enumerate() {
            if !b.is_ascii_digit() {
                return Err(pyo3::exceptions::PyValueError::new_err("Invalid integer"));
            }
            let digit = (b - b'0') as u64;
            value += digit * POW10_U64[len - i - 1];
        }

        // Check for overflow when applying sign
        if is_negative {
            // i64::MIN is -9223372036854775808
            if value > 9_223_372_036_854_775_808 {
                // Too large for i64, fall through to string conversion
                return parse_large_integer(py, bytes, is_negative);
            }
            let signed_value = -(value as i64);
            
            // DIRECT FFI: PyLong_FromLongLong
            unsafe {
                let py_obj = ffi::PyLong_FromLongLong(signed_value);
                if py_obj.is_null() {
                    ffi::PyErr_Clear();
                    return Err(pyo3::exceptions::PyValueError::new_err("Failed to create integer"));
                }
                Ok(PyObject::from_owned_ptr(py, py_obj))
            }
        } else {
            // Positive integer
            if value > i64::MAX as u64 {
                // Use unsigned path
                unsafe {
                    let py_obj = ffi::PyLong_FromUnsignedLongLong(value);
                    if py_obj.is_null() {
                        ffi::PyErr_Clear();
                        return Err(pyo3::exceptions::PyValueError::new_err("Failed to create integer"));
                    }
                    Ok(PyObject::from_owned_ptr(py, py_obj))
                }
            } else {
                // Fits in signed i64
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
        // Large integer (>19 digits) - use Python's string conversion
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
#[inline]
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
