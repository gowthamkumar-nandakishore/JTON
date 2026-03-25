// SIMD module for high-performance structural character scanning
// Requires AVX2 (baseline) or AVX-512 (fast path)

pub mod scanner_avx2;
pub mod scanner_avx512;
pub mod whitespace;

#[cfg(target_arch = "x86_64")]
#[allow(unused_imports)]
use std::arch::x86_64::*;

use crate::types::StructuralIndex;

/// Scan input for structural characters using SIMD
/// 
/// This function uses runtime CPU feature detection to choose:
/// - AVX-512 (64-byte chunks) if available (2017+ CPUs)
/// - AVX2 (32-byte chunks) as baseline (2013+ CPUs)
/// 
/// Returns StructuralIndex with positions of all delimiters
pub unsafe fn scan_structural_chars(input: &[u8]) -> StructuralIndex {
    #[cfg(target_arch = "x86_64")]
    {
        // Runtime CPU feature detection - prefer AVX-512, fallback to AVX2
        if is_x86_feature_detected!("avx512f") && is_x86_feature_detected!("avx512bw") {
            scanner_avx512::scan_avx512(input)
        } else if is_x86_feature_detected!("avx2") {
            scanner_avx2::scan_avx2(input)
        } else {
            // Fallback to scalar (should never happen per Constitution)
            panic!("AVX2 not supported - this CPU is too old (pre-2013)");
        }
    }
    
    #[cfg(not(target_arch = "x86_64"))]
    {
        panic!("SIMD scanning only supported on x86_64");
    }
}

/// Check if AVX2 is available (should always be true per Constitution)
pub fn check_cpu_features() -> bool {
    #[cfg(target_arch = "x86_64")]
    {
        is_x86_feature_detected!("avx2")
    }
    
    #[cfg(not(target_arch = "x86_64"))]
    {
        false
    }
}

/// Get the active SIMD implementation name
pub fn get_simd_implementation() -> &'static str {
    #[cfg(target_arch = "x86_64")]
    {
        if is_x86_feature_detected!("avx512f") && is_x86_feature_detected!("avx512bw") {
            "AVX-512"
        } else if is_x86_feature_detected!("avx2") {
            "AVX2"
        } else {
            "None (unsupported CPU)"
        }
    }
    
    #[cfg(not(target_arch = "x86_64"))]
    {
        "None (non-x86_64)"
    }
}
