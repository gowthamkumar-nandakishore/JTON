use crate::parser::error::ParseError;
use crate::types::{ParseContext, StructuralIndex};
use pyo3::ffi;
use pyo3::prelude::*;

/// Ultra-fast parser that jumps between structural character positions
pub struct FastIndexParser<'a> {
    input: &'a [u8],
    index: &'a StructuralIndex,
    pos: usize,
    // Monotonic structural cursors — advance forward-only, never search backwards
    quote_idx: usize,
    comma_idx: usize,
    colon_idx: usize,
    semicolon_idx: usize,
    open_brace_idx: usize,
    close_brace_idx: usize,
    open_bracket_idx: usize,
    close_bracket_idx: usize,
}

impl<'a> FastIndexParser<'a> {
    pub fn new(input: &'a [u8], index: &'a StructuralIndex) -> Self {
        Self {
            input,
            index,
            pos: 0,
            quote_idx: 0,
            comma_idx: 0,
            colon_idx: 0,
            semicolon_idx: 0,
            open_brace_idx: 0,
            close_brace_idx: 0,
            open_bracket_idx: 0,
            close_bracket_idx: 0,
        }
    }

    #[inline(always)]
    fn consume_open_brace(&mut self, pos: usize) {
        debug_assert!(self.open_brace_idx < self.index.open_braces.len());
        debug_assert!(self.index.open_braces[self.open_brace_idx] >= pos);
        if self.open_brace_idx < self.index.open_braces.len() {
            self.open_brace_idx += 1;
        }
    }

    #[inline(always)]
    fn consume_close_brace(&mut self, pos: usize) {
        debug_assert!(self.close_brace_idx < self.index.close_braces.len());
        debug_assert!(self.index.close_braces[self.close_brace_idx] >= pos);
        if self.close_brace_idx < self.index.close_braces.len() {
            self.close_brace_idx += 1;
        }
    }

    #[inline(always)]
    fn consume_open_bracket(&mut self, pos: usize) {
        debug_assert!(self.open_bracket_idx < self.index.open_brackets.len());
        debug_assert!(self.index.open_brackets[self.open_bracket_idx] >= pos);
        if self.open_bracket_idx < self.index.open_brackets.len() {
            self.open_bracket_idx += 1;
        }
    }

    #[inline(always)]
    fn consume_close_bracket(&mut self, pos: usize) {
        debug_assert!(self.close_bracket_idx < self.index.close_brackets.len());
        debug_assert!(self.index.close_brackets[self.close_bracket_idx] >= pos);
        if self.close_bracket_idx < self.index.close_brackets.len() {
            self.close_bracket_idx += 1;
        }
    }

    #[inline(always)]
    fn consume_comma(&mut self, pos: usize) {
        debug_assert!(self.comma_idx < self.index.commas.len());
        debug_assert!(self.index.commas[self.comma_idx] >= pos);
        if self.comma_idx < self.index.commas.len() {
            self.comma_idx += 1;
        }
    }

    #[inline(always)]
    fn consume_semicolon(&mut self, pos: usize) {
        debug_assert!(self.semicolon_idx < self.index.semicolons.len());
        debug_assert!(self.index.semicolons[self.semicolon_idx] >= pos);
        if self.semicolon_idx < self.index.semicolons.len() {
            self.semicolon_idx += 1;
        }
    }

    #[inline(always)]
    fn take_colon(&mut self) -> PyResult<usize> {
        self.sync_structural_cursors();
        if self.colon_idx >= self.index.colons.len() {
            return Err(ParseError::unexpected_eof(self.pos).into());
        }
        let pos = self.index.colons[self.colon_idx];
        self.colon_idx += 1;
        Ok(pos)
    }

    /// Monotonic cursor sync to keep structural indices aligned with byte cursor.
    #[inline(always)]
    fn sync_structural_cursors(&mut self) {
        let p = self.pos;
        while self.quote_idx < self.index.quotes.len() && self.index.quotes[self.quote_idx] < p {
            self.quote_idx += 1;
        }
        while self.colon_idx < self.index.colons.len() && self.index.colons[self.colon_idx] < p {
            self.colon_idx += 1;
        }
        while self.comma_idx < self.index.commas.len() && self.index.commas[self.comma_idx] < p {
            self.comma_idx += 1;
        }
        while self.semicolon_idx < self.index.semicolons.len()
            && self.index.semicolons[self.semicolon_idx] < p
        {
            self.semicolon_idx += 1;
        }
        while self.open_brace_idx < self.index.open_braces.len()
            && self.index.open_braces[self.open_brace_idx] < p
        {
            self.open_brace_idx += 1;
        }
        while self.close_brace_idx < self.index.close_braces.len()
            && self.index.close_braces[self.close_brace_idx] < p
        {
            self.close_brace_idx += 1;
        }
        while self.open_bracket_idx < self.index.open_brackets.len()
            && self.index.open_brackets[self.open_bracket_idx] < p
        {
            self.open_bracket_idx += 1;
        }
        while self.close_bracket_idx < self.index.close_brackets.len()
            && self.index.close_brackets[self.close_bracket_idx] < p
        {
            self.close_bracket_idx += 1;
        }
    }

    #[inline(always)]
    fn skip_ws(&mut self) {
        // AVX2 is verified at module import time; call directly without runtime detection.
        #[cfg(target_arch = "x86_64")]
        {
            if std::is_x86_feature_detected!("avx2") {
                unsafe { crate::simd::whitespace::skip_whitespace_simd(self.input, &mut self.pos) };
                return;
            }
        }
        crate::simd::whitespace::skip_whitespace_scalar(self.input, &mut self.pos);
    }

    /// Skip only ASCII spaces (0x20). Used between Zen Grid cells so that tab/pipe
    /// delimiters are NOT consumed as whitespace and can be detected as separators.
    #[inline(always)]
    fn skip_spaces_only(&mut self) {
        while self.pos < self.input.len()
            && unsafe { *self.input.get_unchecked(self.pos) } == b' '
        {
            self.pos += 1;
        }
    }

    /// Parse top-level value
    pub fn parse(&mut self, py: Python, ctx: &mut ParseContext) -> PyResult<PyObject> {
        self.skip_ws();

        if self.pos >= self.input.len() {
            return Err(ParseError::unexpected_eof(self.pos).into());
        }

        let value = self.parse_value(py, ctx)?;
        self.skip_ws();
        if self.pos < self.input.len() {
            return Err(
                ParseError::new(self.pos, "Trailing content after document".to_string()).into(),
            );
        }
        Ok(value)
    }

    fn parse_value(&mut self, py: Python, ctx: &mut ParseContext) -> PyResult<PyObject> {
        self.skip_ws();
        self.sync_structural_cursors();

        if self.pos >= self.input.len() {
            return Err(ParseError::unexpected_eof(self.pos).into());
        }

        match unsafe { *self.input.get_unchecked(self.pos) } {
            b'{' => self.parse_object_indexed(py, ctx),
            b'[' => self.parse_array_indexed(py, ctx),
            b'"' => self.parse_string_fast(py),
            b't' | b'f' | b'n' => self.parse_literal(py),
            b'-' | b'0'..=b'9' | b'I' | b'N' => self.parse_number_fast(py),
            c => Err(ParseError::invalid_char(self.pos, c as char).into()),
        }
    }

    /// Parse a JSON object using direct FFI dictionary operations (zero PyO3 overhead)
    fn parse_object_indexed(&mut self, py: Python, ctx: &mut ParseContext) -> PyResult<PyObject> {
        let brace_pos = self.pos;

        let dict_ptr = unsafe { ffi::PyDict_New() };
        if dict_ptr.is_null() {
            return Err(pyo3::exceptions::PyMemoryError::new_err(
                "Failed to create dict",
            ));
        }

        // Nitro-Path (Schema-Mode): bypass key parsing/interning
        if ctx.schema.is_some() {
            let schema_owned = ctx.schema.take().unwrap();
            let result = self.parse_object_schema(py, ctx, dict_ptr, &schema_owned, brace_pos);
            ctx.schema = Some(schema_owned);
            return result;
        }

        self.pos += 1; // Skip '{'
        self.consume_open_brace(brace_pos);

        let dict = unsafe { PyObject::from_owned_ptr(py, dict_ptr) };

        self.skip_ws();

        // Empty object
        if self.pos < self.input.len() && unsafe { *self.input.get_unchecked(self.pos) } == b'}' {
            let close_pos = self.pos;
            self.pos += 1;
            self.consume_close_brace(close_pos);
            return Ok(dict);
        }

        // Parse key-value pairs
        loop {
            self.skip_ws();

            if self.pos >= self.input.len() {
                return Err(ParseError::unexpected_eof(self.pos).into());
            }

            // Check for closing brace
            if unsafe { *self.input.get_unchecked(self.pos) } == b'}' {
                let close_pos = self.pos;
                self.pos += 1;
                self.consume_close_brace(close_pos);
                return Ok(dict);
            }

            // Parse key (using cached/interned strings)
            let key = self.parse_key(py)?;

            // Jump to ':' using monotonic colon cursor (no searching)
            let colon_pos = self.take_colon()?;
            if colon_pos >= self.input.len()
                || unsafe { *self.input.get_unchecked(colon_pos) } != b':'
            {
                return Err(ParseError::expected_char(self.pos, ':').into());
            }
            self.pos = colon_pos + 1;

            // Parse value
            let value = self.parse_value(py, ctx)?;

            // Direct FFI insertion — bypasses Python hashing overhead
            unsafe {
                if ffi::PyDict_SetItem(dict_ptr, key.as_ptr(), value.as_ptr()) < 0 {
                    return Err(pyo3::exceptions::PyRuntimeError::new_err(
                        "Dict insertion failed",
                    ));
                }
            }

            // Check for ',' or '}'
            self.skip_ws();

            if self.pos >= self.input.len() {
                return Err(ParseError::unexpected_eof(self.pos).into());
            }

            match unsafe { *self.input.get_unchecked(self.pos) } {
                b',' => {
                    let comma_pos = self.pos;
                    self.pos += 1;
                    self.consume_comma(comma_pos);
                    self.skip_ws();
                    if self.pos < self.input.len()
                        && unsafe { *self.input.get_unchecked(self.pos) } == b'}'
                    {
                        let close_pos = self.pos;
                        self.pos += 1;
                        self.consume_close_brace(close_pos);
                        return Ok(dict);
                    }
                }
                b'}' => {
                    let close_pos = self.pos;
                    self.pos += 1;
                    self.consume_close_brace(close_pos);
                    return Ok(dict);
                }
                c => return Err(ParseError::invalid_char(self.pos, c as char).into()),
            }
        }
    }

    /// Parse a JSON array using direct FFI for maximum performance.
    /// Uses PyList_New + PyList_SET_ITEM to bypass bounds checking.
    fn parse_array_indexed(&mut self, py: Python, ctx: &mut ParseContext) -> PyResult<PyObject> {
        let opening_bracket = self.pos;
        self.pos += 1; // Skip '['
        self.consume_open_bracket(opening_bracket);

        // Check for Zen Grid: `[: ...]` or `[N: ...]` (optional row count prefix)
        self.skip_ws();
        if self.pos < self.input.len() {
            let b = unsafe { *self.input.get_unchecked(self.pos) };
            if b == b':' {
                return self.parse_zen_grid_indexed(py, ctx, opening_bracket);
            }
            // [N: ...] — skip the row count digits (metadata, ignored on decode) then colon
            if b.is_ascii_digit() {
                let mut p = self.pos + 1;
                while p < self.input.len() && unsafe { *self.input.get_unchecked(p) }.is_ascii_digit() {
                    p += 1;
                }
                while p < self.input.len() && unsafe { *self.input.get_unchecked(p) } == b' ' {
                    p += 1;
                }
                if p < self.input.len() && unsafe { *self.input.get_unchecked(p) } == b':' {
                    self.pos = p; // advance to ':' so parse_zen_grid_indexed finds it
                    return self.parse_zen_grid_indexed(py, ctx, opening_bracket);
                }
            }
        }

        // Empty array check
        self.skip_ws();
        if self.pos < self.input.len() && unsafe { *self.input.get_unchecked(self.pos) } == b']' {
            let close_pos = self.pos;
            self.pos += 1;
            self.consume_close_bracket(close_pos);
            let empty_list = unsafe { ffi::PyList_New(0) };
            return Ok(unsafe { PyObject::from_owned_ptr(py, empty_list) });
        }

        // Homogeneous array fast-path:
        // Only use PyList_New + PyList_SET_ITEM when we can prove there are no nested
        // arrays/objects before the next matching ']'. This avoids heavy prescans for
        // canada-like nested workloads.
        let next_close = self
            .index
            .close_brackets
            .get(self.close_bracket_idx)
            .copied();
        let next_open_bracket = self.index.open_brackets.get(self.open_bracket_idx).copied();
        let next_open_brace = self.index.open_braces.get(self.open_brace_idx).copied();

        let can_use_homogeneous = match next_close {
            Some(close_pos) => {
                let has_nested_bracket = matches!(next_open_bracket, Some(p) if p < close_pos);
                let has_nested_brace = matches!(next_open_brace, Some(p) if p < close_pos);
                let span = close_pos.saturating_sub(opening_bracket);
                !has_nested_bracket && !has_nested_brace && span >= 256
            }
            None => false,
        };

        if can_use_homogeneous {
            let end_bracket = next_close.unwrap();

            // Count commas until end bracket (no nesting => exact)
            let mut comma_i = self.comma_idx;
            let mut commas = 0usize;
            let mut last_comma: Option<usize> = None;
            while comma_i < self.index.commas.len() {
                let p = self.index.commas[comma_i];
                if p >= end_bracket {
                    break;
                }
                commas += 1;
                last_comma = Some(p);
                comma_i += 1;
            }

            let mut capacity = commas + 1;
            if let Some(last) = last_comma {
                let mut p = last + 1;
                while p < end_bracket {
                    let b = self.input[p];
                    if b.is_ascii_whitespace() {
                        p += 1;
                        continue;
                    }
                    break;
                }
                if p == end_bracket {
                    capacity = capacity.saturating_sub(1);
                }
            }

            let list_ptr = unsafe { ffi::PyList_New(capacity as isize) };
            if list_ptr.is_null() {
                return Err(pyo3::exceptions::PyMemoryError::new_err(
                    "Failed to create list",
                ));
            }

            let mut idx: usize = 0;
            loop {
                if idx >= capacity {
                    // Consume optional trailing comma and close.
                    self.skip_ws();
                    if self.pos < self.input.len()
                        && unsafe { *self.input.get_unchecked(self.pos) } == b','
                    {
                        let comma_pos = self.pos;
                        self.pos += 1;
                        self.consume_comma(comma_pos);
                        self.skip_ws();
                    }
                    if self.pos < self.input.len()
                        && unsafe { *self.input.get_unchecked(self.pos) } == b']'
                    {
                        let close_pos = self.pos;
                        self.pos += 1;
                        self.consume_close_bracket(close_pos);
                        break;
                    }
                    unsafe { ffi::Py_DECREF(list_ptr) };
                    return Err(ParseError::expected_char(self.pos, ']').into());
                }

                let value = self.parse_value(py, ctx)?;
                let value_ptr = value.into_ptr();
                unsafe {
                    ffi::PyList_SetItem(list_ptr, idx as isize, value_ptr);
                }
                idx += 1;

                self.skip_ws();
                if self.pos >= self.input.len() {
                    unsafe { ffi::Py_DECREF(list_ptr) };
                    return Err(ParseError::unexpected_eof(self.pos).into());
                }

                match unsafe { *self.input.get_unchecked(self.pos) } {
                    b',' => {
                        let comma_pos = self.pos;
                        self.pos += 1;
                        self.consume_comma(comma_pos);
                        self.skip_ws();
                        if self.pos < self.input.len()
                            && unsafe { *self.input.get_unchecked(self.pos) } == b']'
                        {
                            // Trailing comma
                            let close_pos = self.pos;
                            self.pos += 1;
                            self.consume_close_bracket(close_pos);
                            unsafe {
                                ffi::PyList_SetSlice(
                                    list_ptr,
                                    idx as isize,
                                    capacity as isize,
                                    std::ptr::null_mut(),
                                );
                            }
                            break;
                        }
                    }
                    b']' => {
                        let close_pos = self.pos;
                        self.pos += 1;
                        self.consume_close_bracket(close_pos);
                        if idx < capacity {
                            unsafe {
                                ffi::PyList_SetSlice(
                                    list_ptr,
                                    idx as isize,
                                    capacity as isize,
                                    std::ptr::null_mut(),
                                );
                            }
                        }
                        break;
                    }
                    c => {
                        unsafe { ffi::Py_DECREF(list_ptr) };
                        return Err(ParseError::invalid_char(self.pos, c as char).into());
                    }
                }
            }

            return Ok(unsafe { PyObject::from_owned_ptr(py, list_ptr) });
        }

        // Default (nested/small arrays): fast append path
        let list_ptr = unsafe { ffi::PyList_New(0) };
        if list_ptr.is_null() {
            return Err(pyo3::exceptions::PyMemoryError::new_err(
                "Failed to create list",
            ));
        }

        loop {
            let value = self.parse_value(py, ctx)?;
            unsafe {
                if ffi::PyList_Append(list_ptr, value.as_ptr()) < 0 {
                    ffi::Py_DECREF(list_ptr);
                    return Err(pyo3::exceptions::PyRuntimeError::new_err(
                        "List append failed",
                    ));
                }
            }

            self.skip_ws();
            if self.pos >= self.input.len() {
                unsafe { ffi::Py_DECREF(list_ptr) };
                return Err(ParseError::unexpected_eof(self.pos).into());
            }

            match unsafe { *self.input.get_unchecked(self.pos) } {
                b',' => {
                    let comma_pos = self.pos;
                    self.pos += 1;
                    self.consume_comma(comma_pos);
                    self.skip_ws();
                    if self.pos < self.input.len()
                        && unsafe { *self.input.get_unchecked(self.pos) } == b']'
                    {
                        let close_pos = self.pos;
                        self.pos += 1;
                        self.consume_close_bracket(close_pos);
                        return Ok(unsafe { PyObject::from_owned_ptr(py, list_ptr) });
                    }
                }
                b']' => {
                    let close_pos = self.pos;
                    self.pos += 1;
                    self.consume_close_bracket(close_pos);
                    return Ok(unsafe { PyObject::from_owned_ptr(py, list_ptr) });
                }
                c => {
                    unsafe { ffi::Py_DECREF(list_ptr) };
                    return Err(ParseError::invalid_char(self.pos, c as char).into());
                }
            }
        }
    }

    fn parse_object_schema(
        &mut self,
        py: Python,
        ctx: &mut ParseContext,
        dict_ptr: *mut ffi::PyObject,
        schema: &[crate::types::FieldDescriptor],
        brace_pos: usize,
    ) -> PyResult<PyObject> {
        self.pos += 1; // Skip '{'
        self.consume_open_brace(brace_pos);

        self.skip_ws();
        self.sync_structural_cursors();
        if self.pos < self.input.len() && unsafe { *self.input.get_unchecked(self.pos) } == b'}' {
            let close_pos = self.pos;
            self.pos += 1;
            self.consume_close_brace(close_pos);
            return Ok(unsafe { PyObject::from_owned_ptr(py, dict_ptr) });
        }

        for (idx, field) in schema.iter().enumerate() {
            self.skip_ws();
            if self.pos >= self.input.len() {
                return Err(ParseError::unexpected_eof(self.pos).into());
            }
            self.sync_structural_cursors();

            let colon_pos = self.take_colon()?;
            if colon_pos >= self.input.len()
                || unsafe { *self.input.get_unchecked(colon_pos) } != b':'
            {
                return Err(ParseError::expected_char(self.pos, ':').into());
            }
            self.pos = colon_pos + 1;

            let saved_schema = ctx.schema.take();
            let value = self.parse_value(py, ctx);
            ctx.schema = saved_schema;
            let value = value?;

            unsafe {
                if ffi::PyDict_SetItem(dict_ptr, field.interned_key.as_ptr(), value.as_ptr()) < 0 {
                    return Err(pyo3::exceptions::PyRuntimeError::new_err(
                        "Dict insertion failed",
                    ));
                }
            }

            self.skip_ws();
            if self.pos >= self.input.len() {
                return Err(ParseError::unexpected_eof(self.pos).into());
            }

            let is_last = idx + 1 == schema.len();
            match unsafe { *self.input.get_unchecked(self.pos) } {
                b',' => {
                    let comma_pos = self.pos;
                    self.pos += 1;
                    self.consume_comma(comma_pos);
                    self.skip_ws();
                    if is_last {
                        continue;
                    }
                }
                b'}' => {
                    let close_pos = self.pos;
                    self.pos += 1;
                    self.consume_close_brace(close_pos);
                    return Ok(unsafe { PyObject::from_owned_ptr(py, dict_ptr) });
                }
                c => {
                    if is_last && c == b',' {
                        let comma_pos = self.pos;
                        self.pos += 1;
                        self.consume_comma(comma_pos);
                        self.skip_ws();
                        continue;
                    }
                    return Err(ParseError::invalid_char(self.pos, c as char).into());
                }
            }
        }

        self.skip_ws();
        if self.pos < self.input.len() && unsafe { *self.input.get_unchecked(self.pos) } == b'}' {
            let close_pos = self.pos;
            self.pos += 1;
            self.consume_close_brace(close_pos);
            return Ok(unsafe { PyObject::from_owned_ptr(py, dict_ptr) });
        }

        Err(ParseError::expected_char(self.pos, '}').into())
    }

    fn parse_zen_grid_indexed(
        &mut self,
        py: Python,
        ctx: &mut ParseContext,
        opening_bracket: usize,
    ) -> PyResult<PyObject> {
        // We are at ':' (after '[')
        let colon_pos = self.take_colon()?;
        if colon_pos != self.pos {
            self.pos = colon_pos;
        }
        if colon_pos >= self.input.len() || unsafe { *self.input.get_unchecked(colon_pos) } != b':'
        {
            return Err(ParseError::expected_char(self.pos, ':').into());
        }
        self.pos = colon_pos + 1;
        self.skip_ws();

        // Empty table: [:]
        if self.pos < self.input.len() && unsafe { *self.input.get_unchecked(self.pos) } == b']' {
            let close_pos = self.pos;
            self.pos += 1;
            self.consume_close_bracket(close_pos);
            let empty_list = unsafe { ffi::PyList_New(0) };
            return Ok(unsafe { PyObject::from_owned_ptr(py, empty_list) });
        }

        let closing_bracket = self.find_matching_bracket_cursor(opening_bracket)?;

        // Parse headers until first ';'
        let mut headers: Vec<*mut ffi::PyObject> = Vec::with_capacity(32);
        loop {
            self.skip_ws();
            if self.pos >= self.input.len() {
                return Err(ParseError::unexpected_eof(self.pos).into());
            }

            if unsafe { *self.input.get_unchecked(self.pos) } == b';' {
                let semi_pos = self.pos;
                self.pos += 1;
                self.consume_semicolon(semi_pos);
                break;
            }

            let key_ptr = self.parse_table_header_key(py)?;
            headers.push(key_ptr);

            self.skip_spaces_only();
            if self.pos >= self.input.len() {
                for k in &headers {
                    unsafe { ffi::Py_DECREF(*k) };
                }
                return Err(ParseError::unexpected_eof(self.pos).into());
            }
            match unsafe { *self.input.get_unchecked(self.pos) } {
                b',' | b'\t' | b'|' => {
                    self.pos += 1; // consume delimiter (not a structural char, no cursor update)
                }
                b';' => {
                    let semi_pos = self.pos;
                    self.pos += 1;
                    self.consume_semicolon(semi_pos);
                    break;
                }
                c => {
                    for k in &headers {
                        unsafe { ffi::Py_DECREF(*k) };
                    }
                    return Err(ParseError::invalid_char(self.pos, c as char).into());
                }
            }
        }

        // SIMD prescan: count row separators at table depth (cap 1M)
        let estimated_rows = self.count_zen_grid_rows(self.pos, closing_bracket);
        if estimated_rows > 1_000_000 {
            for k in headers {
                unsafe { ffi::Py_DECREF(k) };
            }
            return Err(
                ParseError::new(self.pos, "Zen Grid exceeds 1M rows limit".to_string()).into(),
            );
        }

        let list_ptr = unsafe { ffi::PyList_New(estimated_rows as isize) };
        if list_ptr.is_null() {
            for k in headers {
                unsafe { ffi::Py_DECREF(k) };
            }
            return Err(pyo3::exceptions::PyMemoryError::new_err(
                "Failed to create list",
            ));
        }

        let mut row_idx: usize = 0;
        while row_idx < estimated_rows {
            self.skip_ws();
            if self.pos >= self.input.len() {
                unsafe { ffi::Py_DECREF(list_ptr) };
                for k in headers {
                    unsafe { ffi::Py_DECREF(k) };
                }
                return Err(ParseError::unexpected_eof(self.pos).into());
            }

            // End of table
            if unsafe { *self.input.get_unchecked(self.pos) } == b']' {
                let close_pos = self.pos;
                self.pos += 1;
                self.consume_close_bracket(close_pos);
                break;
            }

            let row_dict_ptr = unsafe { ffi::PyDict_New() };
            if row_dict_ptr.is_null() {
                unsafe { ffi::Py_DECREF(list_ptr) };
                for k in headers {
                    unsafe { ffi::Py_DECREF(k) };
                }
                return Err(pyo3::exceptions::PyMemoryError::new_err(
                    "Failed to create row dict",
                ));
            }

            // Parse row values
            for col in 0..headers.len() {
                self.skip_spaces_only();

                // Row ended early
                if self.pos < self.input.len() {
                    let ch = unsafe { *self.input.get_unchecked(self.pos) };
                    if ch == b';' {
                        // Fill remaining with None
                        for k in headers.iter().skip(col) {
                            unsafe {
                                let none = py.None().into_ptr();
                                if ffi::PyDict_SetItem(row_dict_ptr, *k, none) < 0 {
                                    ffi::Py_DECREF(row_dict_ptr);
                                    ffi::Py_DECREF(list_ptr);
                                    for kk in headers {
                                        ffi::Py_DECREF(kk)
                                    }
                                    return Err(pyo3::exceptions::PyRuntimeError::new_err(
                                        "Row dict insertion failed",
                                    ));
                                }
                                ffi::Py_DECREF(none);
                            }
                        }
                        let semi_pos = self.pos;
                        self.pos += 1;
                        self.consume_semicolon(semi_pos);
                        break;
                    }
                    if ch == b']' {
                        // Treat as end of table (no more rows)
                        for k in headers.iter().skip(col) {
                            unsafe {
                                let none = py.None().into_ptr();
                                ffi::PyDict_SetItem(row_dict_ptr, *k, none);
                                ffi::Py_DECREF(none);
                            }
                        }
                        // We'll close after pushing row
                    }
                }

                let value = self.parse_table_cell_value(py, ctx)?;
                unsafe {
                    if ffi::PyDict_SetItem(row_dict_ptr, headers[col], value.as_ptr()) < 0 {
                        ffi::Py_DECREF(row_dict_ptr);
                        ffi::Py_DECREF(list_ptr);
                        for k in headers {
                            ffi::Py_DECREF(k)
                        }
                        return Err(pyo3::exceptions::PyRuntimeError::new_err(
                            "Row dict insertion failed",
                        ));
                    }
                }

                self.skip_spaces_only();
                if self.pos >= self.input.len() {
                    unsafe { ffi::Py_DECREF(row_dict_ptr) };
                    unsafe { ffi::Py_DECREF(list_ptr) };
                    for k in headers {
                        unsafe { ffi::Py_DECREF(k) };
                    }
                    return Err(ParseError::unexpected_eof(self.pos).into());
                }

                match unsafe { *self.input.get_unchecked(self.pos) } {
                    b',' | b'\t' | b'|' => {
                        self.pos += 1; // consume cell delimiter
                    }
                    b';' => {
                        let semi_pos = self.pos;
                        self.pos += 1;
                        self.consume_semicolon(semi_pos);
                        // Fill remaining with None
                        for k in headers.iter().skip(col + 1) {
                            unsafe {
                                let none = py.None().into_ptr();
                                ffi::PyDict_SetItem(row_dict_ptr, *k, none);
                                ffi::Py_DECREF(none);
                            }
                        }
                        break;
                    }
                    b']' => {
                        // End of table without trailing ';'
                        for k in headers.iter().skip(col + 1) {
                            unsafe {
                                let none = py.None().into_ptr();
                                ffi::PyDict_SetItem(row_dict_ptr, *k, none);
                                ffi::Py_DECREF(none);
                            }
                        }
                        // We'll consume ']' after pushing rows.
                        break;
                    }
                    c => {
                        unsafe { ffi::Py_DECREF(row_dict_ptr) };
                        unsafe { ffi::Py_DECREF(list_ptr) };
                        for k in headers {
                            unsafe { ffi::Py_DECREF(k) };
                        }
                        return Err(ParseError::invalid_char(self.pos, c as char).into());
                    }
                }
            }

            // Push row dict into list via SetItem (steals ref)
            unsafe {
                ffi::PyList_SetItem(list_ptr, row_idx as isize, row_dict_ptr);
            }
            row_idx += 1;

            self.skip_ws();
            if self.pos < self.input.len() && unsafe { *self.input.get_unchecked(self.pos) } == b']'
            {
                let close_pos = self.pos;
                self.pos += 1;
                self.consume_close_bracket(close_pos);
                break;
            }
        }

        // Shrink in case of trailing separators / early close
        if row_idx < estimated_rows {
            unsafe {
                ffi::PyList_SetSlice(
                    list_ptr,
                    row_idx as isize,
                    estimated_rows as isize,
                    std::ptr::null_mut(),
                );
            }
        }

        // Release our header key references (dicts hold their own refs)
        for k in headers {
            unsafe { ffi::Py_DECREF(k) };
        }

        Ok(unsafe { PyObject::from_owned_ptr(py, list_ptr) })
    }

    fn parse_table_cell_value(&mut self, py: Python, ctx: &mut ParseContext) -> PyResult<PyObject> {
        self.skip_ws();
        if self.pos >= self.input.len() {
            return Err(ParseError::unexpected_eof(self.pos).into());
        }

        // Delegate nested/typed values to JSON parser.
        match unsafe { *self.input.get_unchecked(self.pos) } {
            b'{' | b'[' | b'"' | b't' | b'f' | b'n' | b'-' | b'0'..=b'9' | b'I' | b'N' => {
                return self.parse_value(py, ctx);
            }
            _ => {}
        }

        // Unquoted string cell: read until ',', ';', or ']' (table delimiters)
        let start = self.pos;
        let mut saw_escape = false;
        while self.pos < self.input.len() {
            match unsafe { *self.input.get_unchecked(self.pos) } {
                b',' | b';' | b']' | b'\t' | b'|' => break,
                b'\\' => {
                    saw_escape = true;
                    self.pos += 1;
                    if self.pos >= self.input.len() {
                        return Err(ParseError::unexpected_eof(self.pos).into());
                    }
                    // Skip escaped char
                    self.pos += 1;
                }
                _ => self.pos += 1,
            }
        }

        let mut end = self.pos;
        while end > start && self.input[end - 1].is_ascii_whitespace() {
            end -= 1;
        }

        if !saw_escape {
            let slice = &self.input[start..end];
            // Empty cell = implicit null
            if slice.is_empty() {
                return Ok(unsafe { PyObject::from_borrowed_ptr(py, ffi::Py_None()) });
            }
            // Use ASCII fast path or UTF-8 decoder directly (avoid PyO3 overhead)
            let py_str = unsafe {
                if slice.iter().all(|&b| b < 0x80) {
                    ffi::PyUnicode_DecodeASCII(
                        slice.as_ptr() as *const std::os::raw::c_char,
                        slice.len() as isize,
                        std::ptr::null(),
                    )
                } else {
                    ffi::PyUnicode_DecodeUTF8(
                        slice.as_ptr() as *const std::os::raw::c_char,
                        slice.len() as isize,
                        std::ptr::null(),
                    )
                }
            };
            if py_str.is_null() {
                unsafe { ffi::PyErr_Clear() };
                return Err(ParseError::new(start, "Invalid UTF-8 in cell".to_string()).into());
            }
            return Ok(unsafe { PyObject::from_owned_ptr(py, py_str) });
        }

        // Escape path: build unescaped string
        let mut out = String::with_capacity(end.saturating_sub(start));
        let mut i = start;
        while i < end {
            let b = unsafe { *self.input.get_unchecked(i) };
            if b == b'\\' {
                i += 1;
                if i >= end {
                    break;
                }
                let esc = unsafe { *self.input.get_unchecked(i) };
                out.push(esc as char);
                i += 1;
                continue;
            }
            out.push(b as char);
            i += 1;
        }

        Ok(unsafe {
            let s = out.as_str();
            let py_obj = ffi::PyUnicode_DecodeUTF8(
                s.as_ptr() as *const std::os::raw::c_char,
                s.len() as isize,
                std::ptr::null(),
            );
            if py_obj.is_null() {
                ffi::PyErr_Clear();
                return Err(pyo3::exceptions::PyValueError::new_err(
                    "Invalid UTF-8 in string",
                ));
            }
            PyObject::from_owned_ptr(py, py_obj)
        })
    }

    fn parse_table_header_key(&mut self, py: Python) -> PyResult<*mut ffi::PyObject> {
        self.skip_ws();
        self.sync_structural_cursors();
        if self.pos >= self.input.len() {
            return Err(ParseError::unexpected_eof(self.pos).into());
        }
        match unsafe { *self.input.get_unchecked(self.pos) } {
            b'"' => {
                // Fast path: quoted header without escapes -> cache by bytes
                let opening = self.pos;
                if self.quote_idx >= self.index.quotes.len() {
                    return Err(ParseError::unexpected_eof(self.pos).into());
                }

                #[cfg(debug_assertions)]
                {
                    debug_assert_eq!(self.index.quotes[self.quote_idx], opening);
                }

                let start = opening + 1;
                let quote_cursor_start = self.quote_idx;
                self.quote_idx += 1;
                let closing = self
                    .index
                    .quotes
                    .get(self.quote_idx)
                    .copied()
                    .ok_or_else(|| ParseError::unexpected_eof(self.pos))?;
                let slice = &self.input[start..closing];
                self.pos = closing + 1;
                self.quote_idx += 1;

                if !slice.contains(&b'\\') {
                    let key_ptr = crate::parser::string_cache::get_cached_key(slice);
                    if key_ptr.is_null() {
                        return Err(
                            ParseError::new(start, "Invalid UTF-8 in header".to_string()).into(),
                        );
                    }
                    Ok(key_ptr)
                } else {
                    self.pos = opening;
                    self.quote_idx = quote_cursor_start;
                    let key_obj = self.parse_string_fast(py)?;
                    Ok(key_obj.into_ptr())
                }
            }
            _ => {
                // Unquoted header token: read until ',', ';', ']', '\t', or '|'
                let start = self.pos;
                while self.pos < self.input.len() {
                    match unsafe { *self.input.get_unchecked(self.pos) } {
                        b',' | b';' | b']' | b'\t' | b'|' => break,
                        _ => self.pos += 1,
                    }
                }
                let mut end = self.pos;
                while end > start && self.input[end - 1].is_ascii_whitespace() {
                    end -= 1;
                }
                let slice = &self.input[start..end];
                let key_ptr = crate::parser::string_cache::get_cached_key(slice);
                if key_ptr.is_null() {
                    return Err(
                        ParseError::new(start, "Invalid UTF-8 in header".to_string()).into(),
                    );
                }
                Ok(key_ptr)
            }
        }
    }

    fn find_matching_bracket_cursor(&mut self, _start: usize) -> Result<usize, ParseError> {
        // Cursor-based matching without O(log N) searches.
        let mut depth = 1;

        let mut open_idx = self.open_bracket_idx;
        let mut close_idx = self.close_bracket_idx;

        loop {
            let next_open = self.index.open_brackets.get(open_idx).copied();
            let next_close = self.index.close_brackets.get(close_idx).copied();
            match (next_open, next_close) {
                (Some(open_pos), Some(close_pos)) if open_pos < close_pos => {
                    depth += 1;
                    open_idx += 1;
                }
                (_, Some(close_pos)) => {
                    depth -= 1;
                    if depth == 0 {
                        return Ok(close_pos);
                    }
                    close_idx += 1;
                }
                _ => return Err(ParseError::unexpected_eof(self.input.len())),
            }
        }
    }

    fn count_zen_grid_rows(&mut self, start_after_header: usize, closing_bracket: usize) -> usize {
        // Count semicolons at table depth (ignoring nested arrays/objects).
        let mut semi_idx = self.semicolon_idx;

        let mut open_b_idx = self.open_bracket_idx;
        let mut close_b_idx = self.close_bracket_idx;
        let mut open_o_idx = self.open_brace_idx;
        let mut close_o_idx = self.close_brace_idx;

        let mut depth: isize = 0;
        let mut rows_by_semis: usize = 0;
        let mut last_semicolon: Option<usize> = None;

        loop {
            let next_semi = self.index.semicolons.get(semi_idx).copied();
            let next_open_bracket = self.index.open_brackets.get(open_b_idx).copied();
            let next_close_bracket = self.index.close_brackets.get(close_b_idx).copied();
            let next_open_brace = self.index.open_braces.get(open_o_idx).copied();
            let next_close_brace = self.index.close_braces.get(close_o_idx).copied();

            let mut next_pos = closing_bracket;
            let mut kind = 0u8;
            for (k, p) in [
                (1u8, next_semi),
                (2u8, next_open_bracket),
                (3u8, next_close_bracket),
                (4u8, next_open_brace),
                (5u8, next_close_brace),
            ] {
                if let Some(pp) = p {
                    if pp < next_pos {
                        next_pos = pp;
                        kind = k;
                    }
                }
            }

            if next_pos >= closing_bracket {
                break;
            }

            match kind {
                1 => {
                    if depth == 0 {
                        rows_by_semis += 1;
                        last_semicolon = Some(next_pos);
                    }
                    semi_idx += 1;
                }
                2 => {
                    depth += 1;
                    open_b_idx += 1;
                }
                3 => {
                    depth -= 1;
                    close_b_idx += 1;
                }
                4 => {
                    depth += 1;
                    open_o_idx += 1;
                }
                5 => {
                    depth -= 1;
                    close_o_idx += 1;
                }
                _ => break,
            }
        }

        // If there is content after the last semicolon before closing ']', add one row.
        let mut rows = rows_by_semis;
        let scan_from = last_semicolon.map(|p| p + 1).unwrap_or(start_after_header);
        let mut p = scan_from;
        while p < closing_bracket {
            let b = self.input[p];
            if b.is_ascii_whitespace() {
                p += 1;
                continue;
            }
            // Any non-ws content implies a final row without trailing ';'
            rows += 1;
            break;
        }

        rows
    }

    /// Parse key (quoted or unquoted)
    fn parse_key(&mut self, py: Python) -> PyResult<PyObject> {
        crate::simd::whitespace::skip_whitespace(self.input, &mut self.pos);
        self.sync_structural_cursors();

        if self.pos >= self.input.len() {
            return Err(ParseError::unexpected_eof(self.pos).into());
        }

        match unsafe { *self.input.get_unchecked(self.pos) } {
            b'"' => {
                if self.quote_idx >= self.index.quotes.len() {
                    return Err(ParseError::unexpected_eof(self.pos).into());
                }

                #[cfg(debug_assertions)]
                {
                    debug_assert_eq!(self.index.quotes[self.quote_idx], self.pos);
                }

                let start = self.pos + 1;
                self.quote_idx += 1;
                let closing = self
                    .index
                    .quotes
                    .get(self.quote_idx)
                    .copied()
                    .ok_or_else(|| ParseError::unexpected_eof(self.pos))?;
                let slice = &self.input[start..closing];
                self.pos = closing + 1;
                self.quote_idx += 1;

                if !slice.contains(&b'\\') {
                    let cached_key = crate::parser::string_cache::get_cached_key(slice);
                    if cached_key.is_null() {
                        return Err(
                            ParseError::new(start, "Invalid UTF-8 in key".to_string()).into()
                        );
                    }
                    return Ok(unsafe { PyObject::from_owned_ptr(py, cached_key) });
                }

                self.pos = start;
                let parsed = self.parse_string_with_escapes(py, start)?;
                Ok(parsed)
            }
            c if c.is_ascii_alphanumeric() || c == b'_' => {
                // Unquoted keys - also cache these
                let start = self.pos;
                while self.pos < self.input.len() {
                    let ch = unsafe { *self.input.get_unchecked(self.pos) };
                    if ch.is_ascii_alphanumeric() || ch == b'_' {
                        self.pos += 1;
                    } else {
                        break;
                    }
                }
                let key_bytes = &self.input[start..self.pos];
                let cached_key = crate::parser::string_cache::get_cached_key(key_bytes);
                if cached_key.is_null() {
                    return Err(ParseError::new(start, "Invalid UTF-8 in key".to_string()).into());
                }
                Ok(unsafe { PyObject::from_owned_ptr(py, cached_key) })
            }
            c => Err(ParseError::invalid_char(self.pos, c as char).into()),
        }
    }

    /// Fast string parsing using the pre-built quote index for zero-copy extraction.
    /// Assumes the quote cursor always points at the current opening quote.
    fn parse_string_fast(&mut self, py: Python) -> PyResult<PyObject> {
        self.sync_structural_cursors();
        if self.quote_idx >= self.index.quotes.len() {
            return Err(ParseError::unexpected_eof(self.pos).into());
        }

        #[cfg(debug_assertions)]
        {
            debug_assert_eq!(self.index.quotes[self.quote_idx], self.pos);
        }

        let start = self.pos + 1;
        self.quote_idx += 1;
        let closing = self
            .index
            .quotes
            .get(self.quote_idx)
            .copied()
            .ok_or_else(|| ParseError::unexpected_eof(self.pos))?;
        let slice = &self.input[start..closing];
        self.pos = closing + 1;
        self.quote_idx += 1;

        if !slice.contains(&b'\\') {
            // No escape sequences — use direct FFI to create Python string.
            // Single-pass: check for ASCII-only while we already scanned for '\\'.
            let all_ascii = slice.iter().all(|&b| b < 0x80);
            let py_str = unsafe {
                if all_ascii {
                    ffi::PyUnicode_DecodeASCII(
                        slice.as_ptr() as *const std::os::raw::c_char,
                        slice.len() as isize,
                        std::ptr::null(),
                    )
                } else {
                    ffi::PyUnicode_DecodeUTF8(
                        slice.as_ptr() as *const std::os::raw::c_char,
                        slice.len() as isize,
                        std::ptr::null(),
                    )
                }
            };
            if py_str.is_null() {
                unsafe { ffi::PyErr_Clear() };
                return Err(
                    ParseError::new(start - 1, "Invalid UTF-8 in string".to_string()).into(),
                );
            }
            return Ok(unsafe { PyObject::from_owned_ptr(py, py_str) });
        }

        self.pos = start;
        self.parse_string_with_escapes(py, start)
    }

    /// String parsing with escape handling
    fn parse_string_with_escapes(&mut self, py: Python, start: usize) -> PyResult<PyObject> {
        let mut result = String::with_capacity(256);

        // Add content before backslash
        if self.pos > start {
            result.push_str(unsafe { std::str::from_utf8_unchecked(&self.input[start..self.pos]) });
        }

        while self.pos < self.input.len() {
            match unsafe { *self.input.get_unchecked(self.pos) } {
                b'"' => {
                    self.pos += 1;
                    self.sync_structural_cursors();
                    return Ok(unsafe {
                        let s = result.as_str();
                        let py_obj = ffi::PyUnicode_DecodeUTF8(
                            s.as_ptr() as *const std::os::raw::c_char,
                            s.len() as isize,
                            std::ptr::null(),
                        );
                        if py_obj.is_null() {
                            ffi::PyErr_Clear();
                            return Err(pyo3::exceptions::PyValueError::new_err(
                                "Invalid UTF-8 in string",
                            ));
                        }
                        PyObject::from_owned_ptr(py, py_obj)
                    });
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
                            let escape_pos = self.pos - 1;
                            self.pos += 1;
                            let code = self.parse_unicode_escape()?;
                            if (0xD800..=0xDBFF).contains(&code) {
                                if self.pos + 1 < self.input.len()
                                    && unsafe { *self.input.get_unchecked(self.pos) } == b'\\'
                                    && unsafe { *self.input.get_unchecked(self.pos + 1) } == b'u'
                                {
                                    self.pos += 2;
                                    let low = self.parse_unicode_escape()?;
                                    if (0xDC00..=0xDFFF).contains(&low) {
                                        let scalar =
                                            0x1_0000 + (((code - 0xD800) << 10) | (low - 0xDC00));
                                        if let Some(ch) = char::from_u32(scalar) {
                                            result.push(ch);
                                            continue;
                                        }
                                    }
                                }
                                return Err(ParseError::invalid_unicode(escape_pos).into());
                            } else if (0xDC00..=0xDFFF).contains(&code) {
                                return Err(ParseError::invalid_unicode(escape_pos).into());
                            } else if let Some(ch) = char::from_u32(code) {
                                result.push(ch);
                            } else {
                                return Err(ParseError::invalid_unicode(escape_pos).into());
                            }
                            continue; // pos already advanced
                        }
                        c => return Err(ParseError::invalid_escape(self.pos, c as char).into()),
                    }
                    self.pos += 1;
                }
                ch if ch < 32 => return Err(ParseError::unescaped_control(self.pos).into()),
                _ => {
                    let ch_start = self.pos;
                    self.pos += 1;
                    while self.pos < self.input.len()
                        && (unsafe { *self.input.get_unchecked(self.pos) } & 0xC0 == 0x80)
                    {
                        self.pos += 1;
                    }
                    result.push_str(unsafe {
                        std::str::from_utf8_unchecked(&self.input[ch_start..self.pos])
                    });
                }
            }
        }

        Err(ParseError::unexpected_eof(self.pos).into())
    }

    fn parse_unicode_escape(&mut self) -> Result<u32, ParseError> {
        let mut code = 0u32;
        for _ in 0..4 {
            if self.pos >= self.input.len() {
                return Err(ParseError::unexpected_eof(self.pos));
            }
            let digit = unsafe { *self.input.get_unchecked(self.pos) };
            code = code * 16
                + match digit {
                    b'0'..=b'9' => (digit - b'0') as u32,
                    b'a'..=b'f' => (digit - b'a' + 10) as u32,
                    b'A'..=b'F' => (digit - b'A' + 10) as u32,
                    _ => return Err(ParseError::invalid_unicode(self.pos)),
                };
            self.pos += 1;
        }
        Ok(code)
    }

    /// Fast number parsing — single-pass scan then delegate to fast_number
    #[inline(always)]
    fn parse_number_fast(&mut self, py: Python) -> PyResult<PyObject> {
        let start = self.pos;
        // Single pass: advance pos to the first byte that cannot be part of a number.
        // fast_number::parse_number_fast handles all validation internally, so we only
        // need to find the token boundary here.
        while self.pos < self.input.len() {
            match unsafe { *self.input.get_unchecked(self.pos) } {
                b'-'
                | b'+'
                | b'0'..=b'9'
                | b'.'
                | b'e'
                | b'E'
                | b'I'
                | b'N'
                | b'a'
                | b'f'
                | b'n'
                | b'i'
                | b't'
                | b'y' => self.pos += 1,
                _ => break,
            }
        }
        let bytes = &self.input[start..self.pos];
        crate::parser::fast_number::parse_number_fast(py, bytes)
    }

    /// Parse literal (true, false, null)
    fn parse_literal(&mut self, py: Python) -> PyResult<PyObject> {
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

        if self.pos + 5 <= self.input.len() && &self.input[self.pos..self.pos + 5] == b"false" {
            self.pos += 5;
            return Ok(false.to_object(py));
        }

        Err(
            ParseError::invalid_char(self.pos, unsafe { *self.input.get_unchecked(self.pos) }
                as char)
            .into(),
        )
    }
}
