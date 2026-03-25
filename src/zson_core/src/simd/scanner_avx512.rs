// AVX-512 SIMD scanner for structural characters
// Processes 64 bytes per cycle using AVX-512 intrinsics

#[cfg(target_arch = "x86_64")]
use std::arch::x86_64::*;

use crate::types::StructuralIndex;

/// Scan input using AVX-512 (64-byte chunks)
/// 
/// This is the high-performance implementation for modern CPUs (2017+).
/// Scans for the same structural characters as AVX2 but with 64-byte chunks.
/// 
/// Performance target: ≥64 bytes/cycle
#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx512f", enable = "avx512bw")]
pub unsafe fn scan_avx512(input: &[u8]) -> StructuralIndex {
    // Pre-allocate index vectors based on input size to avoid repeated reallocations
    let mut index = StructuralIndex::with_input_capacity(input.len());

    let len = input.len();
    let mut pos = 0;

    // Hoist constant comparison vectors out of the loop
    let v_open_brace    = _mm512_set1_epi8(b'{' as i8);
    let v_close_brace   = _mm512_set1_epi8(b'}' as i8);
    let v_open_bracket  = _mm512_set1_epi8(b'[' as i8);
    let v_close_bracket = _mm512_set1_epi8(b']' as i8);
    let v_colon         = _mm512_set1_epi8(b':' as i8);
    let v_semicolon     = _mm512_set1_epi8(b';' as i8);
    let v_comma         = _mm512_set1_epi8(b',' as i8);
    let v_quote         = _mm512_set1_epi8(b'"' as i8);

    // Process 64-byte chunks with AVX-512
    while pos + 64 <= len {
        // Load 64 bytes
        let chunk = _mm512_loadu_si512(input.as_ptr().add(pos) as *const __m512i);
        
        // Compare and extract bitmasks (64-bit masks)
        let mask_open_brace    = _mm512_cmpeq_epi8_mask(chunk, v_open_brace);
        let mask_close_brace   = _mm512_cmpeq_epi8_mask(chunk, v_close_brace);
        let mask_open_bracket  = _mm512_cmpeq_epi8_mask(chunk, v_open_bracket);
        let mask_close_bracket = _mm512_cmpeq_epi8_mask(chunk, v_close_bracket);
        let mask_colon         = _mm512_cmpeq_epi8_mask(chunk, v_colon);
        let mask_semicolon     = _mm512_cmpeq_epi8_mask(chunk, v_semicolon);
        let mask_comma         = _mm512_cmpeq_epi8_mask(chunk, v_comma);
        let mask_quote         = _mm512_cmpeq_epi8_mask(chunk, v_quote);
        
        // Process bitmasks to extract positions
        process_mask_64(mask_open_brace,    pos, &mut index.open_braces);
        process_mask_64(mask_close_brace,   pos, &mut index.close_braces);
        process_mask_64(mask_open_bracket,  pos, &mut index.open_brackets);
        process_mask_64(mask_close_bracket, pos, &mut index.close_brackets);
        process_mask_64(mask_colon,         pos, &mut index.colons);
        process_mask_64(mask_semicolon,     pos, &mut index.semicolons);
        process_mask_64(mask_comma,         pos, &mut index.commas);
        process_mask_64(mask_quote,         pos, &mut index.quotes);
        
        pos += 64;
    }
    
    // Handle remaining bytes with scalar fallback
    while pos < len {
        match input[pos] {
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
        pos += 1;
    }
    
    index
}

/// Process a 64-bit bitmask and extract positions
#[inline]
fn process_mask_64(mut mask: u64, base_pos: usize, positions: &mut Vec<usize>) {
    while mask != 0 {
        let offset = mask.trailing_zeros() as usize;
        positions.push(base_pos + offset);
        mask &= mask - 1; // Clear lowest set bit
    }
}
