"""
MYSON - A compact, JSON-compatible data format with SIMD-accelerated parsing.

This package provides high-performance parsing of MYSON/JSON data using
Rust with AVX2/AVX-512 SIMD intrinsics.
"""

# Import the Rust extension module
from .myson_core import __version__, loads

__all__ = ['__version__', 'loads']
