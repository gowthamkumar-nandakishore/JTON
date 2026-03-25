// NEON SIMD scanner for structural characters — aarch64 (Apple Silicon, ARM servers).
// Processes 16 bytes per iteration using ARM NEON intrinsics.
//
// Strategy: compare each 16-byte chunk against all 8 structural characters in parallel,
// OR the results together, then use a bit-position trick to build a u16 movemask so we
// can iterate only over structural positions (same bit-drain loop as the AVX2 scanner).

#[cfg(target_arch = "aarch64")]
use std::arch::aarch64::*;

#[cfg(target_arch = "aarch64")]
use crate::types::StructuralIndex;

#[cfg(target_arch = "aarch64")]
pub fn scan_neon(input: &[u8]) -> StructuralIndex {
    // SAFETY: NEON is always available on aarch64.
    unsafe { scan_neon_unsafe(input) }
}

#[cfg(target_arch = "aarch64")]
unsafe fn scan_neon_unsafe(input: &[u8]) -> StructuralIndex {
    let mut index = StructuralIndex::with_input_capacity(input.len());
    let len = input.len();
    let mut pos = 0;

    // Bit-position lookup for the movemask simulation.
    // For a uint8x8_t whose elements are 0xFF or 0x00, masking with these values
    // and summing gives a bitmask where bit i = 1 iff element i was 0xFF.
    let bit_vals: [u8; 8] = [1, 2, 4, 8, 16, 32, 64, 128];
    let bit_lut = vld1_u8(bit_vals.as_ptr());

    while pos + 16 <= len {
        let chunk = vld1q_u8(input.as_ptr().add(pos));

        // Compare against all 8 structural characters.
        let eq_open_brace = vceqq_u8(chunk, vdupq_n_u8(b'{'));
        let eq_close_brace = vceqq_u8(chunk, vdupq_n_u8(b'}'));
        let eq_open_bracket = vceqq_u8(chunk, vdupq_n_u8(b'['));
        let eq_close_bracket = vceqq_u8(chunk, vdupq_n_u8(b']'));
        let eq_colon = vceqq_u8(chunk, vdupq_n_u8(b':'));
        let eq_semicolon = vceqq_u8(chunk, vdupq_n_u8(b';'));
        let eq_comma = vceqq_u8(chunk, vdupq_n_u8(b','));
        let eq_quote = vceqq_u8(chunk, vdupq_n_u8(b'"'));

        let any_a = vorrq_u8(
            vorrq_u8(eq_open_brace, eq_close_brace),
            vorrq_u8(eq_open_bracket, eq_close_bracket),
        );
        let any_b = vorrq_u8(
            vorrq_u8(eq_colon, eq_semicolon),
            vorrq_u8(eq_comma, eq_quote),
        );
        let any_structural = vorrq_u8(any_a, any_b);

        // Fast skip when no structural chars exist in the chunk.
        if vmaxvq_u8(any_structural) == 0 {
            pos += 16;
            continue;
        }

        // Build a 16-bit movemask: bit i = 1 iff byte i is structural.
        // Split into low (bytes 0-7) and high (bytes 8-15) halves.
        let lo_masked = vand_u8(vget_low_u8(any_structural), bit_lut);
        let hi_masked = vand_u8(vget_high_u8(any_structural), bit_lut);
        // vaddv_u8: sum all 8 lanes → u8.  Bits are distinct powers-of-2, so no overflow.
        let mask_lo = vaddv_u8(lo_masked) as u16;
        let mask_hi = vaddv_u8(hi_masked) as u16;
        let mut mask = mask_lo | (mask_hi << 8);

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
                _ => {}
            }
            mask &= mask - 1;
        }

        pos += 16;
    }

    // Scalar tail (< 16 bytes remaining).
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
