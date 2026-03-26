// AVX2 SIMD scanner for structural characters
// Processes 32 bytes per cycle using AVX2 intrinsics
//
// Uses a VPSHUFB nibble-classifier technique (inspired by simdjson) to detect
// all 8 structural characters in ONE pass:
//   - 2× VPSHUFB table lookups on lo/hi nibbles
//   - 1× VPAND   → non-zero byte = structural char
//   - 1× VPCMPEQ + MOVEMASK → bitmask of structural positions
// Replaces the previous 8 independent CMPEQ+MOVEMASK passes.

#[cfg(target_arch = "x86_64")]
use std::arch::x86_64::*;

use crate::types::StructuralIndex;

/// Scan input using AVX2 (32-byte chunks) with VPSHUFB nibble classifier.
///
/// Structural chars: `{` `}` `[` `]` `:` `;` `,` `"`
/// Nibble assignment (bits 0-7 in classification byte):
///   bit0 = `"` (0x22), bit1 = `,` (0x2C), bit2 = `:` (0x3A), bit3 = `;` (0x3B)
///   bit4 = `[` (0x5B), bit5 = `]` (0x5D), bit6 = `{` (0x7B), bit7 = `}` (0x7D)
#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2")]
pub unsafe fn scan_avx2(input: &[u8]) -> StructuralIndex {
    let mut index = StructuralIndex::with_input_capacity(input.len());
    let len = input.len();
    let mut pos = 0;

    // ── Nibble classifier tables (16 bytes each, duplicated into both 128-bit lanes) ──
    //
    // lo_lut[nibble] = OR of bits for structural chars with this low nibble:
    //   nibble 0x2 → bit0 (`"`)           = 1
    //   nibble 0xA → bit2 (`:`)           = 4
    //   nibble 0xB → bit3|bit4|bit6       = 88  (`;`, `[`, `{`)
    //   nibble 0xC → bit1 (`,`)           = 2
    //   nibble 0xD → bit5|bit7            = 160 (`]`, `}`)
    //   all others → 0
    //
    // _mm256_set_epi8 takes bytes from index 31 (first arg) down to 0 (last arg).
    // Each 128-bit lane uses the same 16-byte table (VPSHUFB is lane-independent).
    let lo_lut = _mm256_set_epi8(
        //  [15]  [14]  [13]      [12]  [11]  [10]  [9][8][7][6][5][4][3]  [2] [1][0]
        0, 0, -96_i8, 2, 88_i8, 4_i8, 0, 0, 0, 0, 0, 0, 0, 1_i8, 0, 0, // lane 1
        0, 0, -96_i8, 2, 88_i8, 4_i8, 0, 0, 0, 0, 0, 0, 0, 1_i8, 0, 0, // lane 0
    );
    // hi_lut[nibble] = OR of bits for structural chars with this high nibble:
    //   nibble 0x2 → bit0|bit1             = 3  (`"`, `,`)
    //   nibble 0x3 → bit2|bit3             = 12 (`:`, `;`)
    //   nibble 0x5 → bit4|bit5             = 48 (`[`, `]`)
    //   nibble 0x7 → bit6|bit7             = 192 (`{`, `}`)
    let hi_lut = _mm256_set_epi8(
        //  [15][14][13][12][11][10][9][8]  [7]     [6]  [5]   [4]  [3]   [2] [1][0]
        0, 0, 0, 0, 0, 0, 0, 0, -64_i8, 0, 48_i8, 0, 12_i8, 3_i8, 0, 0, // lane 1
        0, 0, 0, 0, 0, 0, 0, 0, -64_i8, 0, 48_i8, 0, 12_i8, 3_i8, 0, 0, // lane 0
    );
    let v_0f = _mm256_set1_epi8(0x0F_u8 as i8);
    let v_zero = _mm256_setzero_si256();

    while pos + 32 <= len {
        let chunk = _mm256_loadu_si256(input.as_ptr().add(pos) as *const __m256i);

        // Extract nibbles for each byte
        let lo_nibble = _mm256_and_si256(chunk, v_0f);
        // _mm256_srli_epi16 >> 4 moves the high nibble of each byte into the low position
        let hi_nibble = _mm256_and_si256(_mm256_srli_epi16(chunk, 4), v_0f);

        // Classify: result[i] != 0  ⟺  byte i is a structural character
        let lo_class = _mm256_shuffle_epi8(lo_lut, lo_nibble);
        let hi_class = _mm256_shuffle_epi8(hi_lut, hi_nibble);
        let structural = _mm256_and_si256(lo_class, hi_class);

        // Bitmask of structural positions (bit i = 1 if byte i is structural)
        let mut mask = !(_mm256_movemask_epi8(_mm256_cmpeq_epi8(structural, v_zero)) as u32);

        // Single pass over structural positions — branch on actual byte value to classify
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
                _ => {} // nibble false-positive (none expected for valid UTF-8)
            }
            mask &= mask - 1; // clear lowest set bit
        }

        pos += 32;
    }

    // Scalar tail (< 32 bytes remaining)
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
