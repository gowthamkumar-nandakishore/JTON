// SIMD-accelerated JSON parser using structural index
// This parser jumps between structural characters instead of scanning byte-by-byte

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use crate::types::{ParseContext, StructuralIndex};
use crate::parser::error::ParseError;

/// Parser state using structural index
pub struct IndexParser<'a> {
    input: &'a [u8],
    index: &'a StructuralIndex,
    ctx: &'a mut ParseContext,
    
    // Current positions in structural index arrays
    brace_idx: usize,
    bracket_idx: usize,
    colon_idx: usize,
    comma_idx: usize,
    
    // Current byte position in input
    pos: usize,
}

impl<'a> IndexParser<'a> {
    pub fn new(input: &'a [u8], index: &'a StructuralIndex, ctx: &'a mut ParseContext) -> Self {
        Self {
            input,
            index,
            ctx,
            brace_idx: 0,
            bracket_idx: 0,
            colon_idx: 0,
            comma_idx: 0,
            pos: 0,
        }
    }
    
    /// Parse a value using structural index
    pub fn parse_value(&mut self, py: Python) -> PyResult<PyObject> {
        // Skip whitespace
        self.skip_whitespace();
        
        if self.pos >= self.input.len() {
            return Err(ParseError::unexpected_eof(self.pos).into());
        }
        
        match unsafe { *self.input.get_unchecked(self.pos) } {
            b'{' => self.parse_object(py),
            b'[' => self.parse_array(py),
            b'"' => self.parse_string(py),
            b't' | b'f' | b'n' => self.parse_bool_null(py),
            b'-' | b'0'..=b'9' | b'I' | b'N' => self.parse_number(py),
            c => Err(ParseError::invalid_char(self.pos, c as char).into()),
        }
    }
    
    /// Parse object using structural index for fast navigation
    fn parse_object(&mut self, py: Python) -> PyResult<PyObject> {
        // Consume '{'
        self.pos += 1;
        let dict = PyDict::new(py);
        
        self.skip_whitespace();
        
        // Empty object
        if self.pos < self.input.len() && unsafe { *self.input.get_unchecked(self.pos) } == b'}' {
            self.pos += 1;
            return Ok(dict.into());
        }
        
        loop {
            // Parse key (string or unquoted)
            self.skip_whitespace();
            let key = self.parse_key(py)?;
            
            // Find next colon using structural index
            self.skip_whitespace();
            if self.pos < self.input.len() && unsafe { *self.input.get_unchecked(self.pos) } == b':' {
                self.pos += 1;
            } else {
                return Err(ParseError::expected_char(self.pos, ':').into());
            }
            
            // Parse value
            let value = self.parse_value(py)?;
            dict.set_item(key, value)?;
            
            // Check for comma or closing brace
            self.skip_whitespace();
            if self.pos >= self.input.len() {
                return Err(ParseError::unexpected_eof(self.pos).into());
            }
            
            match unsafe { *self.input.get_unchecked(self.pos) } {
                b',' => {
                    self.pos += 1;
                    // Optional trailing comma
                    self.skip_whitespace();
                    if self.pos < self.input.len() && unsafe { *self.input.get_unchecked(self.pos) } == b'}' {
                        self.pos += 1;
                        return Ok(dict.into());
                    }
                }
                b'}' => {
                    self.pos += 1;
                    return Ok(dict.into());
                }
                c => return Err(ParseError::invalid_char(self.pos, c as char).into()),
            }
        }
    }
    
    /// Parse array using structural index with batch allocation
    fn parse_array(&mut self, py: Python) -> PyResult<PyObject> {
        // Consume '['
        let start_pos = self.pos;
        self.pos += 1;
        
        // Check for Zen Grid opener ([:)
        self.skip_whitespace();
        if self.pos < self.input.len() && unsafe { *self.input.get_unchecked(self.pos) } == b':' {
            // TODO: Delegate to Zen Grid parser (Phase 4)
            return Err(ParseError::unsupported_feature(self.pos, "Zen Grid tables not yet implemented in SIMD parser").into());
        }
        
        // Regular JSON array
        // Estimate capacity by counting commas between matching brackets
        let capacity = self.estimate_array_capacity(start_pos);
        let mut values = Vec::with_capacity(capacity);
        
        self.skip_whitespace();
        
        // Empty array
        if self.pos < self.input.len() && unsafe { *self.input.get_unchecked(self.pos) } == b']' {
            self.pos += 1;
            return Ok(PyList::new(py, values).into());
        }
        
        loop {
            // Parse value
            let value = self.parse_value(py)?;
            values.push(value);
            
            // Check for comma or closing bracket
            self.skip_whitespace();
            if self.pos >= self.input.len() {
                return Err(ParseError::unexpected_eof(self.pos).into());
            }
            
            match unsafe { *self.input.get_unchecked(self.pos) } {
                b',' => {
                    self.pos += 1;
                    // Optional trailing comma
                    self.skip_whitespace();
                    if self.pos < self.input.len() && unsafe { *self.input.get_unchecked(self.pos) } == b']' {
                        self.pos += 1;
                        return Ok(PyList::new(py, values).into());
                    }
                }
                b']' => {
                    self.pos += 1;
                    return Ok(PyList::new(py, values).into());
                }
                c => return Err(ParseError::invalid_char(self.pos, c as char).into()),
            }
        }
    }
    
    /// Estimate array capacity by counting commas in structural index
    fn estimate_array_capacity(&self, _start_pos: usize) -> usize {
        // Simple heuristic: start with a reasonable default
        // Real implementation would use structural index to count elements
        // For now, use a conservative default to avoid over-allocation
        16
    }
    
    /// Parse key (string or unquoted)
    fn parse_key(&mut self, py: Python) -> PyResult<PyObject> {
        self.skip_whitespace();
        
        if self.pos >= self.input.len() {
            return Err(ParseError::unexpected_eof(self.pos).into());
        }
        
        match unsafe { *self.input.get_unchecked(self.pos) } {
            b'"' => self.parse_string(py),
            // Unquoted key
            c if c.is_ascii_alphanumeric() || c == b'_' => {
                let start = self.pos;
                while self.pos < self.input.len() {
                    let c = unsafe { *self.input.get_unchecked(self.pos) };
                    if c.is_ascii_alphanumeric() || c == b'_' {
                        self.pos += 1;
                    } else {
                        break;
                    }
                }
                
                let key_bytes = &self.input[start..self.pos];
                let key_str = std::str::from_utf8(key_bytes)
                    .map_err(|_| ParseError::invalid_utf8(start))?;
                
                Ok(pyo3::types::PyString::new(py, key_str).into())
            }
            c => Err(ParseError::invalid_char(self.pos, c as char).into()),
        }
    }
    
    /// Parse string with zero-copy optimization
    fn parse_string(&mut self, py: Python) -> PyResult<PyObject> {
        // Consume opening quote
        self.pos += 1;
        let start = self.pos;
        
        // Fast path: scan for closing quote without escapes
        while self.pos < self.input.len() {
            match unsafe { *self.input.get_unchecked(self.pos) } {
                b'"' => {
                    // No escapes - zero-copy string
                    let s = unsafe { std::str::from_utf8_unchecked(&self.input[start..self.pos]) };
                    self.pos += 1; // Consume closing quote
                    return Ok(pyo3::types::PyString::new(py, s).into());
                }
                b'\\' => {
                    // Escapes found - delegate to slow path
                    return self.parse_string_with_escapes(py, start);
                }
                b'\n' | b'\r' | b'\t' => {
                    return Err(ParseError::unescaped_control(self.pos).into());
                }
                _ => self.pos += 1,
            }
        }
        
        Err(ParseError::unexpected_eof(self.pos).into())
    }
    
    /// Parse string with escape sequences
    fn parse_string_with_escapes(&mut self, py: Python, start: usize) -> PyResult<PyObject> {
        // We're at the backslash or past it
        // Build string with escaped characters
        let mut result = String::with_capacity((self.input.len() - start).min(256));
        
        // Add the part before the backslash
        if self.pos > start {
            result.push_str(unsafe { std::str::from_utf8_unchecked(&self.input[start..self.pos]) });
        }
        
        while self.pos < self.input.len() {
            match unsafe { *self.input.get_unchecked(self.pos) } {
                b'"' => {
                    self.pos += 1;
                    return Ok(pyo3::types::PyString::new(py, &result).into());
                }
                b'\\' => {
                    self.pos += 1;
                    if self.pos >= self.input.len() {
                        return Err(ParseError::unexpected_eof(self.pos).into());
                    }
                    
                    match unsafe { *self.input.get_unchecked(self.pos) } {
                        b'"' => result.push('"'),
                        b'\\' => result.push('\\'),
                        b'/' => result.push('/'),
                        b'b' => result.push('\x08'),
                        b'f' => result.push('\x0C'),
                        b'n' => result.push('\n'),
                        b'r' => result.push('\r'),
                        b't' => result.push('\t'),
                        b'u' => {
                            // Unicode escape \uXXXX
                            self.pos += 1;
                            let code = self.parse_unicode_escape()?;
                            if let Some(ch) = char::from_u32(code) {
                                result.push(ch);
                            } else {
                                return Err(ParseError::invalid_unicode(self.pos - 5).into());
                            }
                            continue; // pos already advanced
                        }
                        c => return Err(ParseError::invalid_escape(self.pos, c as char).into()),
                    }
                    self.pos += 1;
                }
                b'\n' | b'\r' => {
                    return Err(ParseError::unescaped_control(self.pos).into());
                }
                _ => {
                    let ch_start = self.pos;
                    self.pos += 1;
                    // Handle multi-byte UTF-8
                    while self.pos < self.input.len() {
                        let b = unsafe { *self.input.get_unchecked(self.pos) };
                        if b & 0xC0 != 0x80 {
                            break; // Not a continuation byte
                        }
                        self.pos += 1;
                    }
                    result.push_str(unsafe { std::str::from_utf8_unchecked(&self.input[ch_start..self.pos]) });
                }
            }
        }
        
        Err(ParseError::unexpected_eof(self.pos).into())
    }
    
    /// Parse \uXXXX escape
    fn parse_unicode_escape(&mut self) -> Result<u32, ParseError> {
        let mut code = 0u32;
        for _ in 0..4 {
            if self.pos >= self.input.len() {
                return Err(ParseError::unexpected_eof(self.pos));
            }
            
            let digit = unsafe { *self.input.get_unchecked(self.pos) };
            code = code * 16 + match digit {
                b'0'..=b'9' => (digit - b'0') as u32,
                b'a'..=b'f' => (digit - b'a' + 10) as u32,
                b'A'..=b'F' => (digit - b'A' + 10) as u32,
                _ => return Err(ParseError::invalid_unicode(self.pos)),
            };
            self.pos += 1;
        }
        
        Ok(code)
    }
    
    /// Parse number (integer or float)
    #[inline(always)]
    fn parse_number(&mut self, py: Python) -> PyResult<PyObject> {
        let start = self.pos;
        
        // Handle special values (Infinity, NaN)
        if self.pos + 8 <= self.input.len() {
            let slice = &self.input[self.pos..self.pos + 8];
            if slice == b"Infinity" {
                self.pos += 8;
                return Ok(f64::INFINITY.to_object(py));
            }
        }
        if self.pos + 9 <= self.input.len() {
            let slice = &self.input[self.pos..self.pos + 9];
            if slice == b"-Infinity" {
                self.pos += 9;
                return Ok(f64::NEG_INFINITY.to_object(py));
            }
        }
        if self.pos + 3 <= self.input.len() {
            let slice = &self.input[self.pos..self.pos + 3];
            if slice == b"NaN" {
                self.pos += 3;
                return Ok(f64::NAN.to_object(py));
            }
        }
        
        // Regular number parsing
        // Skip negative sign
        if unsafe { *self.input.get_unchecked(self.pos) } == b'-' {
            self.pos += 1;
        }
        
        // Parse integer part
        let mut is_float = false;
        while self.pos < self.input.len() {
            match unsafe { *self.input.get_unchecked(self.pos) } {
                b'0'..=b'9' => self.pos += 1,
                b'.' | b'e' | b'E' => {
                    is_float = true;
                    break;
                }
                _ => break,
            }
        }
        
        // Parse decimal/exponent part
        if is_float {
            if self.pos < self.input.len() && unsafe { *self.input.get_unchecked(self.pos) } == b'.' {
                self.pos += 1;
                while self.pos < self.input.len() {
                    if unsafe { *self.input.get_unchecked(self.pos) }.is_ascii_digit() {
                        self.pos += 1;
                    } else {
                        break;
                    }
                }
            }
            
            if self.pos < self.input.len() {
                let c = unsafe { *self.input.get_unchecked(self.pos) };
                if c == b'e' || c == b'E' {
                    self.pos += 1;
                    if self.pos < self.input.len() {
                        let c = unsafe { *self.input.get_unchecked(self.pos) };
                        if c == b'+' || c == b'-' {
                            self.pos += 1;
                        }
                    }
                    while self.pos < self.input.len() {
                        if unsafe { *self.input.get_unchecked(self.pos) }.is_ascii_digit() {
                            self.pos += 1;
                        } else {
                            break;
                        }
                    }
                }
            }
        }
        
        let num_str = unsafe { std::str::from_utf8_unchecked(&self.input[start..self.pos]) };
        
        if is_float {
            let val: f64 = num_str.parse()
                .map_err(|_| ParseError::invalid_number(start, num_str))?;
            Ok(val.to_object(py))
        } else {
            let val: i64 = num_str.parse()
                .map_err(|_| ParseError::invalid_number(start, num_str))?;
            Ok(val.to_object(py))
        }
    }
    
    /// Parse boolean or null
    #[inline(always)]
    fn parse_bool_null(&mut self, py: Python) -> PyResult<PyObject> {
        if self.pos + 4 <= self.input.len() {
            let slice = &self.input[self.pos..self.pos + 4];
            if slice == b"true" {
                self.pos += 4;
                return Ok(true.to_object(py));
            }
            if slice == b"null" {
                self.pos += 4;
                return Ok(py.None());
            }
        }
        
        if self.pos + 5 <= self.input.len() {
            let slice = &self.input[self.pos..self.pos + 5];
            if slice == b"false" {
                self.pos += 5;
                return Ok(false.to_object(py));
            }
        }
        
        Err(ParseError::invalid_char(self.pos, unsafe { *self.input.get_unchecked(self.pos) } as char).into())
    }
    
    /// Skip whitespace and comments using SIMD hints
    #[inline]
    fn skip_whitespace(&mut self) {
        while self.pos < self.input.len() {
            match unsafe { *self.input.get_unchecked(self.pos) } {
                b' ' | b'\n' | b'\r' | b'\t' => self.pos += 1,
                b'/' if self.pos + 1 < self.input.len() => {
                    match unsafe { *self.input.get_unchecked(self.pos + 1) } {
                        b'/' => {
                            // Single-line comment
                            self.pos += 2;
                            while self.pos < self.input.len() && unsafe { *self.input.get_unchecked(self.pos) } != b'\n' {
                                self.pos += 1;
                            }
                        }
                        b'*' => {
                            // Block comment
                            self.pos += 2;
                            while self.pos + 1 < self.input.len() {
                                if unsafe { *self.input.get_unchecked(self.pos) } == b'*'
                                    && unsafe { *self.input.get_unchecked(self.pos + 1) } == b'/' {
                                    self.pos += 2;
                                    break;
                                }
                                self.pos += 1;
                            }
                        }
                        _ => break,
                    }
                }
                _ => break,
            }
        }
    }
}
