# JTON Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-23

## Active Technologies
- Python 3.10+, Cython 3.0+ + setuptools, Cython, C Compiler (GCC/Clang) (002-JTON-perf-compat)
- Python 3.10+ with Cython 3.0+ for C-extension compilation (003-performance-1gb)
- N/A (in-memory parsing only) (003-performance-1gb)

- Python 3.11 (assumed Ubuntu toolchain) + Standard library only (state machine + recursive descent); pytest for tests (001-short-name-JTON)

## Project Structure

```text
src/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.11 (assumed Ubuntu toolchain): Follow standard conventions

## Recent Changes
- 003-performance-1gb: Added Python 3.10+ with Cython 3.0+ for C-extension compilation
- 002-JTON-perf-compat: Added Python 3.10+, Cython 3.0+ + setuptools, Cython, C Compiler (GCC/Clang)
- 002-JTON-perf-compat: Added Python 3.10+, Cython 3.0+ + setuptools, Cython, C Compiler (GCC/Clang)


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
