# MYSON-Next Quickstart Guide

**Feature**: 002-simd-schema-parser  
**Date**: 2025-12-24  
**Audience**: Contributors implementing Rust migration

## Prerequisites

### Required

- **Rust 1.70+**: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- **Python 3.10+**: `python3 --version`
- **AVX2 CPU**: Intel Haswell (2013+) or AMD Excavator (2015+)
  - Verify: `lscpu | grep avx2` (Linux) or `sysctl -a | grep AVX2` (macOS)
- **maturin**: `pip install maturin`

### Optional

- **AVX-512 CPU**: Intel Skylake-X (2017+) for max performance
- **pytest**: `pip install pytest pytest-benchmark` (for testing)
- **hyperfine**: `cargo install hyperfine` (for benchmarking)

## Project Structure

```
MYSON/
├── src/
│   ├── myson_core/           # NEW: Rust crate
│   │   ├── Cargo.toml        # Rust dependencies
│   │   ├── src/
│   │   │   ├── lib.rs        # PyO3 module definition
│   │   │   ├── simd/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── avx2.rs   # AVX2 SIMD implementations
│   │   │   │   └── avx512.rs # AVX-512 (opt-in at runtime)
│   │   │   ├── parser/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── json.rs   # JSON parser
│   │   │   │   ├── zen_grid.rs  # Zen Grid parser
│   │   │   │   └── schema.rs    # Schema-guided parsing
│   │   │   └── types/
│   │   │       ├── mod.rs
│   │   │       ├── field_descriptor.rs
│   │   │       ├── interner.rs
│   │   │       └── structural_index.rs
│   ├── parser.py             # KEEP: High-level Python API
│   └── tokenizer.py          # KEEP: Existing logic
├── tests/
│   ├── rust/                 # NEW: Rust unit tests
│   │   ├── test_simd.rs
│   │   ├── test_schema.rs
│   │   └── test_interner.rs
│   ├── unit/                 # KEEP: Python unit tests (400+)
│   └── integration/          # KEEP: End-to-end tests
├── benchmarks/
│   ├── benchmark_comparison.py  # KEEP: Performance validation
│   └── data/                    # canada.json, super_long.json
├── pyproject.toml            # UPDATE: Replace setuptools with maturin
└── README.md                 # UPDATE: Add Rust build instructions
```

## Build & Install

### Development Build (Debug)

```bash
# Clone and enter repo
cd /home/gowthamkumar/Projects/MYSON

# Build Rust extension (debug, fast compile)
maturin develop

# Verify installation
python -c "import myson; print(myson.loads('{\"key\": \"value\"}'))"
# Output: {'key': 'value'}
```

**Build time**: ~30s (debug), incremental rebuilds ~5s

### Release Build (Optimized)

```bash
# Build with full optimizations + LTO
maturin develop --release

# Or build wheel for distribution
maturin build --release
```

**Build time**: ~3min (release), produces wheel in `target/wheels/`

### Build Options

```bash
# Target specific CPU (AVX-512)
RUSTFLAGS="-C target-cpu=native" maturin develop --release

# Enable runtime CPU feature detection
RUSTFLAGS="-C target-feature=+avx2,+avx512f" maturin develop --release

# Verbose build (show compilation steps)
maturin develop --release -vv
```

## Running Tests

### Python Tests (400+ fixtures)

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/unit/test_parser_json_parity.py

# Run with benchmark comparison
pytest tests/integration/ --benchmark-compare

# Verbose output
pytest tests/ -v
```

**Expected**: All 400+ tests pass, 0 failures. Build fails if any test regresses.

### Rust Unit Tests

```bash
# Run Rust tests
cd src/myson_core
cargo test

# Run with output
cargo test -- --nocapture

# Test specific module
cargo test simd::avx2
```

**Expected**: 50+ Rust unit tests pass (SIMD correctness, schema compilation, interner)

### Test Coverage

```bash
# Python coverage
pytest --cov=src --cov-report=html tests/

# Rust coverage (requires cargo-tarpaulin)
cargo install cargo-tarpaulin
cd src/myson_core
cargo tarpaulin --out Html
```

**Target**: ≥90% line coverage for new Rust code

## Benchmarking

### Performance Validation

```bash
# Run official benchmark suite
python benchmarks/benchmark_comparison.py

# Expected output:
# canada.json (2.2 MB):     1.52 GB/s ✅ (target: 1.5 GB/s)
# super_long.json (294 MB): 1.68 GB/s ✅ (target: 1.5 GB/s)
# Zen Grid (10K rows):      1.21 GB/s ✅ (target: 1.0 GB/s)
# Efficiency score:         2487 ✅ (target: 2400)
```

### CI Performance Gate

```bash
# Verify minimum performance (233.9 MB/s floor)
python benchmarks/benchmark_comparison.py --min-throughput=233.9

# Exit code 0 = pass, 1 = fail (blocks PR merge)
```

**Failure mode**: If throughput drops below 233.9 MB/s, build fails with error message and benchmark report.

### Comparative Benchmarks

```bash
# Compare against orjson, msgspec
pip install orjson msgspec
python benchmarks/benchmark_comparison.py --compare-all

# Output:
# | Library | canada.json | super_long.json |
# |---------|-------------|-----------------|
# | myson   | 1.52 GB/s   | 1.68 GB/s       |
# | orjson  | 1.01 GB/s   | 1.15 GB/s       |
# | msgspec | 0.89 GB/s   | 0.94 GB/s       |
```

### Microbenchmarks

```bash
# Benchmark SIMD structural scanning only
cd src/myson_core
cargo bench

# Output (criterion.rs):
# avx2_scan/1KB:    234 ns/iter (4.27 GB/s)
# avx2_scan/1MB:    234 μs/iter (4.27 GB/s)
# avx512_scan/1MB:  167 μs/iter (5.98 GB/s)
```

## Development Workflow

### 1. Make Changes

```bash
# Edit Rust code
vim src/myson_core/src/parser/json.rs

# Rebuild (incremental)
maturin develop

# Test
pytest tests/unit/test_parser_json_parity.py
```

### 2. Verify Performance

```bash
# Quick check (canada.json only)
python -m timeit -s "import myson; data = open('benchmarks/data/canada.json', 'rb').read()" \
    "myson.loads(data)"

# Expected: ~1.4ms (1.52 GB/s for 2.2 MB)
```

### 3. Format & Lint

```bash
# Rust formatting
cd src/myson_core
cargo fmt
cargo clippy -- -D warnings

# Python formatting
black src/ tests/
ruff check src/ tests/
```

### 4. Commit

```bash
git add src/myson_core/
git commit -m "feat: implement AVX2 structural scanning"
git push origin feature/002-simd-schema-parser
```

## Debugging

### Rust Panics

```bash
# Enable backtraces
RUST_BACKTRACE=full python -c "import myson; myson.loads('{invalid}')"

# Expected output:
# thread '<unnamed>' panicked at 'Unexpected token', src/parser/json.rs:142:9
# stack backtrace:
#   0: rust_begin_unwind
#   1: myson_core::parser::json::parse_value
#   ...
```

### Performance Regression

```bash
# Profile with perf (Linux)
perf record -g python benchmarks/benchmark_comparison.py
perf report

# Profile with Instruments (macOS)
instruments -t "Time Profiler" python benchmarks/benchmark_comparison.py
```

### SIMD Intrinsic Issues

```bash
# Verify CPU features at runtime
python -c "
import myson
print(myson._simd_features())
# Output: {'avx2': True, 'avx512f': False, 'sse4.2': True}
"
```

## Common Issues

### Issue: `maturin: command not found`

```bash
pip install maturin
# Or: pip install --user maturin && export PATH="$HOME/.local/bin:$PATH"
```

### Issue: `error: SIMD intrinsics require AVX2`

**Cause**: CPU lacks AVX2 (pre-2013 hardware)  
**Solution**: Per constitution, pre-2013 CPUs are **not supported**. Upgrade hardware or use Python fallback (not provided).

### Issue: `test_parser_json_parity.py::test_canada_performance FAILED`

```bash
# Verify release build
maturin develop --release

# Check CPU throttling (Linux)
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
# Should be "performance", not "powersave"
```

### Issue: `MemoryError: Input exceeds 1 GB safety limit`

**Cause**: Input file >1 GB  
**Solution**: Per constitution, 1 GB limit is intentional. Split large files or request limit increase via spec amendment.

## Next Steps

1. **Read**: [spec.md](spec.md) for full requirements
2. **Study**: [research.md](research.md) for SIMD techniques
3. **Review**: [data-model.md](data-model.md) for Rust types
4. **Implement**: Start with `src/myson_core/src/simd/avx2.rs` (structural scanning)
5. **Validate**: Run `pytest tests/` + `python benchmarks/benchmark_comparison.py` after each milestone

## Support

- **Issues**: GitHub Issues for bugs/questions
- **Performance**: Post benchmark results in PR comments
- **Constitution**: See `.specify/memory/constitution.md` for mandates and constraints
