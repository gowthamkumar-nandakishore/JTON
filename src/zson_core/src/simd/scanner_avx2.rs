// AVX2 SIMD scanner for structural characters
// Processes 32 bytes per cycle using AVX2 intrinsics

#[cfg(target_arch = "x86_64")]
use std::arch::x86_64::*;

use crate::types::StructuralIndex;

/// Scan input using AVX2 (32-byte chunks)
/// 
/// This is the baseline implementation that scans for:
/// - `{` `}` (JSON objects)
/// - `[` `]` (JSON arrays, Zen Grid opener)
/// - `:` (JSON key-value separator)
/// - `;` (Zen Grid row separator)
/// - `,` (JSON/Zen Grid value separator)
/// 
/// Performance target: ≥32 bytes/cycle
#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2")]
pub unsafe fn scan_avx2(input: &[u8]) -> StructuralIndex {
    // Pre-allocate index vectors based on input size to avoid repeated reallocations
    let mut index = StructuralIndex::with_input_capacity(input.len());

    let len = input.len();
    let mut pos = 0;

    // Hoist constant comparison vectors out of the loop
    let v_open_brace    = _mm256_set1_epi8(b'{' as i8);
    let v_close_brace   = _mm256_set1_epi8(b'}' as i8);
    let v_open_bracket  = _mm256_set1_epi8(b'[' as i8);
    let v_close_bracket = _mm256_set1_epi8(b']' as i8);
    let v_colon         = _mm256_set1_epi8(b':' as i8);
    let v_semicolon     = _mm256_set1_epi8(b';' as i8);
    let v_comma         = _mm256_set1_epi8(b',' as i8);
    let v_quote         = _mm256_set1_epi8(b'"' as i8);

    // Process 32-byte chunks with AVX2
    while pos + 32 <= len {
        // Load 32 bytes (unaligned is safe and often as fast as aligned on modern CPUs)
        let chunk = _mm256_loadu_si256(input.as_ptr().add(pos) as *const __m256i);
        
        // Compare and extract bitmasks
        let mask_open_brace    = _mm256_movemask_epi8(_mm256_cmpeq_epi8(chunk, v_open_brace))    as u32;
        let mask_close_brace   = _mm256_movemask_epi8(_mm256_cmpeq_epi8(chunk, v_close_brace))   as u32;
        let mask_open_bracket  = _mm256_movemask_epi8(_mm256_cmpeq_epi8(chunk, v_open_bracket))  as u32;
        let mask_close_bracket = _mm256_movemask_epi8(_mm256_cmpeq_epi8(chunk, v_close_bracket)) as u32;
        let mask_colon         = _mm256_movemask_epi8(_mm256_cmpeq_epi8(chunk, v_colon))         as u32;
        let mask_semicolon     = _mm256_movemask_epi8(_mm256_cmpeq_epi8(chunk, v_semicolon))     as u32;
        let mask_comma         = _mm256_movemask_epi8(_mm256_cmpeq_epi8(chunk, v_comma))         as u32;
        let mask_quote         = _mm256_movemask_epi8(_mm256_cmpeq_epi8(chunk, v_quote))         as u32;
        
        // Process bitmasks to extract positions
        process_mask(mask_open_brace,    pos, &mut index.open_braces);
        process_mask(mask_close_brace,   pos, &mut index.close_braces);
        process_mask(mask_open_bracket,  pos, &mut index.open_brackets);
        process_mask(mask_close_bracket, pos, &mut index.close_brackets);
        process_mask(mask_colon,         pos, &mut index.colons);
        process_mask(mask_semicolon,     pos, &mut index.semicolons);
        process_mask(mask_comma,         pos, &mut index.commas);
        process_mask(mask_quote,         pos, &mut index.quotes);
        
        pos += 32;
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
            b'"' => index.quotes.push(pos), // NITRO: Handle remaining quotes
            _ => {}
        }
        pos += 1;
    }
    
    index
}

/// Process a bitmask and extract positions
#[inline]
fn process_mask(mut mask: u32, base_pos: usize, positions: &mut Vec<usize>) {
    while mask != 0 {
        let offset = mask.trailing_zeros() as usize;
        positions.push(base_pos + offset);
        mask &= mask - 1; // Clear lowest set bit
    }
}
