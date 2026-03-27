// Pure scalar structural character scanner — portable fallback for any architecture.
// Processes the input one byte at a time; used on platforms without SIMD support.

use crate::types::StructuralIndex;

pub fn scan_scalar(input: &[u8]) -> StructuralIndex {
    let mut index = StructuralIndex::with_input_capacity(input.len());

    for (pos, &byte) in input.iter().enumerate() {
        match byte {
            b'{' => index.open_braces.push(pos),
            b'}' => index.close_braces.push(pos),
            b'[' => index.open_brackets.push(pos),
            b']' => index.close_brackets.push(pos),
            b':' => index.colons.push(pos),
            b';' => index.semicolons.push(pos),
            b',' => index.commas.push(pos),
            b'"' => index.quotes.push(pos),
            _ => {}
        }
    }

    index
}
