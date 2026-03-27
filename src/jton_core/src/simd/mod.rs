// SIMD module for high-performance structural character scanning.
// Dispatch order: AVX-512 / AVX2 on x86_64, NEON on aarch64, scalar elsewhere.

pub mod scanner_avx2;
pub mod scanner_avx512;
pub mod scanner_neon;
pub mod scanner_scalar;
pub mod whitespace;

#[cfg(target_arch = "x86_64")]
#[allow(unused_imports)]
use std::arch::x86_64::*;

use crate::types::StructuralIndex;

/// Scan input for structural characters using the best available SIMD backend.
///
/// Returns a `StructuralIndex` with positions of all delimiter characters.
pub unsafe fn scan_structural_chars(input: &[u8]) -> StructuralIndex {
    #[cfg(target_arch = "x86_64")]
    {
        if is_x86_feature_detected!("avx512f") && is_x86_feature_detected!("avx512bw") {
            scanner_avx512::scan_avx512(input)
        } else if is_x86_feature_detected!("avx2") {
            scanner_avx2::scan_avx2(input)
        } else {
            // Scalar fallback — pre-Haswell x86_64 (very rare in practice).
            scanner_scalar::scan_scalar(input)
        }
    }

    #[cfg(target_arch = "aarch64")]
    {
        // NEON is mandatory on all aarch64 targets (e.g. Apple Silicon, ARM servers).
        scanner_neon::scan_neon(input)
    }

    #[cfg(not(any(target_arch = "x86_64", target_arch = "aarch64")))]
    {
        scanner_scalar::scan_scalar(input)
    }
}

/// Returns `true` when the runtime supports at least the baseline SIMD tier.
///
/// On x86_64 we require AVX2 for the fast path (scalar is the fallback).
/// On every other architecture (aarch64, etc.) we always return `true` because
/// NEON / scalar are unconditionally available.
pub fn check_cpu_features() -> bool {
    #[cfg(target_arch = "x86_64")]
    {
        is_x86_feature_detected!("avx2")
    }

    #[cfg(not(target_arch = "x86_64"))]
    {
        true
    }
}

/// Returns a human-readable name for the active SIMD implementation.
pub fn get_simd_implementation() -> &'static str {
    #[cfg(target_arch = "x86_64")]
    {
        if is_x86_feature_detected!("avx512f") && is_x86_feature_detected!("avx512bw") {
            "AVX-512"
        } else if is_x86_feature_detected!("avx2") {
            "AVX2"
        } else {
            "Scalar (no AVX2)"
        }
    }

    #[cfg(target_arch = "aarch64")]
    {
        "NEON"
    }

    #[cfg(not(any(target_arch = "x86_64", target_arch = "aarch64")))]
    {
        "Scalar"
    }
}
