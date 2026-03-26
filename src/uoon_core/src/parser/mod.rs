// Core parser module for UOON/JSON

pub mod error;
pub mod fast_number;
pub mod index_parser;
pub mod string_cache;

use crate::types::ParseContext;
use pyo3::prelude::*;

/// Parse UOON/JSON data into Python objects
///
/// This is the main entry point for parsing. It will:
/// 1. Run SIMD structural character scanner
/// 2. Use fast index-jumping parser for maximum performance
/// 3. Return parsed Python object
pub fn parse(py: Python, input: &[u8], ctx: &mut ParseContext) -> PyResult<PyObject> {
    // Step 1: SIMD scan for structural characters
    let index = unsafe { crate::simd::scan_structural_chars(input) };

    // Step 2: Parse using ultra-fast index-jumping parser
    let mut parser = index_parser::FastIndexParser::new(input, &index);
    parser.parse(py, ctx)
}
