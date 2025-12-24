// SIMD whitespace skipping using AVX2
// Processes 32 bytes at a time to skip whitespace and comments

#[cfg(target_arch = "x86_64")]
use std::arch::x86_64::*;

/// Skip whitespace and comments using SIMD (32-byte batches)
/// 
/// This function uses AVX2 to skip whitespace characters much faster than
/// byte-by-byte iteration. It handles:
/// - Space, tab, newline, carriage return
/// - Single-line comments (//)
/// - Block comments (/* */)
#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2")]
pub unsafe fn skip_whitespace_simd(input: &[u8], pos: &mut usize) {
    let len = input.len();
    
    // Process 32-byte chunks with AVX2
    while *pos + 32 <= len {
        // Load 32 bytes
        let chunk = _mm256_loadu_si256(input.as_ptr().add(*pos) as *const __m256i);
        
        // Create comparison vectors for whitespace characters
        let space = _mm256_set1_epi8(b' ' as i8);
        let tab = _mm256_set1_epi8(b'\t' as i8);
        let newline = _mm256_set1_epi8(b'\n' as i8);
        let carriage = _mm256_set1_epi8(b'\r' as i8);
        
        // Compare and combine results
        let is_space = _mm256_cmpeq_epi8(chunk, space);
        let is_tab = _mm256_cmpeq_epi8(chunk, tab);
        let is_newline = _mm256_cmpeq_epi8(chunk, newline);
        let is_carriage = _mm256_cmpeq_epi8(chunk, carriage);
        
        // Combine all whitespace matches
        let is_ws = _mm256_or_si256(
            _mm256_or_si256(is_space, is_tab),
            _mm256_or_si256(is_newline, is_carriage)
        );
        
        // Extract bitmask
        let mask = _mm256_movemask_epi8(is_ws) as u32;
        
        // If all bytes are whitespace, skip entire chunk
        if mask == 0xFFFFFFFF {
            *pos += 32;
            continue;
        }
        
        // If no whitespace, we're done with SIMD
        if mask == 0 {
            break;
        }
        
        // Mixed whitespace - count leading whitespace bytes
        let trailing_ws = (!mask).trailing_zeros() as usize;
        *pos += trailing_ws;
        break;
    }
    
    // Handle remaining bytes with scalar loop
    skip_whitespace_scalar(input, pos);
}

/// Scalar whitespace skipping fallback
#[inline(always)]
pub fn skip_whitespace_scalar(input: &[u8], pos: &mut usize) {
    while *pos < input.len() {
        match unsafe { *input.get_unchecked(*pos) } {
            b' ' | b'\n' | b'\r' | b'\t' => *pos += 1,
            b'/' if *pos + 1 < input.len() => {
                match unsafe { *input.get_unchecked(*pos + 1) } {
                    b'/' => {
                        // Single-line comment
                        *pos += 2;
                        while *pos < input.len() && unsafe { *input.get_unchecked(*pos) } != b'\n' {
                            *pos += 1;
                        }
                        if *pos < input.len() {
                            *pos += 1; // Skip newline
                        }
                    }
                    b'*' => {
                        // Block comment
                        *pos += 2;
                        while *pos + 1 < input.len() {
                            if unsafe { *input.get_unchecked(*pos) } == b'*'
                                && unsafe { *input.get_unchecked(*pos + 1) } == b'/' {
                                *pos += 2;
                                break;
                            }
                            *pos += 1;
                        }
                    }
                    _ => break,
                }
            }
            _ => break,
        }
    }
}

/// Public entry point with runtime CPU detection
pub fn skip_whitespace(input: &[u8], pos: &mut usize) {
    #[cfg(target_arch = "x86_64")]
    {
        if is_x86_feature_detected!("avx2") {
            unsafe { skip_whitespace_simd(input, pos) }
        } else {
            skip_whitespace_scalar(input, pos)
        }
    }
    
    #[cfg(not(target_arch = "x86_64"))]
    {
        skip_whitespace_scalar(input, pos)
    }
}
