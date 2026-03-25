// AVX-512 SIMD scanner for structural characters
// Processes 64 bytes per cycle using AVX-512 intrinsics
//
// Each CMPEQ produces a 64-bit mask directly. We combine all 8 masks with OR
// and iterate over structural positions once, instead of running 8 separate loops.

#[cfg(target_arch = "x86_64")]
use std::arch::x86_64::*;

use crate::types::StructuralIndex;

/// Scan input using AVX-512 (64-byte chunks)
///
/// Uses `_mm512_cmpeq_epi8_mask` (returns a 64-bit mask per comparison).
/// All 8 masks are OR'd together → one combined iteration over structural positions.
#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx512f", enable = "avx512bw")]
pub unsafe fn scan_avx512(input: &[u8]) -> StructuralIndex {
    let mut index = StructuralIndex::with_input_capacity(input.len());
    let len = input.len();
    let mut pos = 0;

    // Hoist constant vectors out of the loop
    let v_open_brace    = _mm512_set1_epi8(b'{' as i8);
    let v_close_brace   = _mm512_set1_epi8(b'}' as i8);
    let v_open_bracket  = _mm512_set1_epi8(b'[' as i8);
    let v_close_bracket = _mm512_set1_epi8(b']' as i8);
    let v_colon         = _mm512_set1_epi8(b':' as i8);
    let v_semicolon     = _mm512_set1_epi8(b';' as i8);
    let v_comma         = _mm512_set1_epi8(b',' as i8);
    let v_quote         = _mm512_set1_epi8(b'"' as i8);

    while pos + 64 <= len {
        let chunk = _mm512_loadu_si512(input.as_ptr().add(pos) as *const __m512i);

        // Get individual 64-bit masks for each structural char
        let m_ob  = _mm512_cmpeq_epi8_mask(chunk, v_open_brace);
        let m_cb  = _mm512_cmpeq_epi8_mask(chunk, v_close_brace);
        let m_obr = _mm512_cmpeq_epi8_mask(chunk, v_open_bracket);
        let m_cbr = _mm512_cmpeq_epi8_mask(chunk, v_close_bracket);
        let m_col = _mm512_cmpeq_epi8_mask(chunk, v_colon);
        let m_sc  = _mm512_cmpeq_epi8_mask(chunk, v_semicolon);
        let m_com = _mm512_cmpeq_epi8_mask(chunk, v_comma);
        let m_q   = _mm512_cmpeq_epi8_mask(chunk, v_quote);

        // Combine into single structural mask, then iterate ONCE over all positions
        let mut mask = m_ob | m_cb | m_obr | m_cbr | m_col | m_sc | m_com | m_q;

        while mask != 0 {
            let offset = mask.trailing_zeros() as usize;
            match *input.get_unchecked(pos + offset) {
                b'{' => index.open_braces.push(pos + offset),
                b'}' => index.close_braces.push(pos + offset),
                b'[' => index.open_brackets.push(pos + offset),
                b']' => index.close_brackets.push(pos + offset),
                b':' => index.colons.push(pos + offset),
                b';' => index.semicolons.push(pos + offset),
                b',' => index.commas.push(pos + offset),
                b'"' => index.quotes.push(pos + offset),
                _   => {}
            }
            mask &= mask - 1;
        }

        pos += 64;
    }

    // Scalar tail (< 64 bytes remaining)
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

