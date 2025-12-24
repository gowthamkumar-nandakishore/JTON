# MYSON Benchmarks

Comprehensive benchmark suite measuring MYSON's **token efficiency** and **parsing speed**, inspired by [toon-format/toon](https://github.com/toon-format/toon/tree/main/benchmarks) and [ijl/orjson](https://github.com/ijl/orjson).

## Quick Start

```bash
# Run all benchmarks and generate comprehensive report
python benchmarks/combined_benchmark_report.py

# Run token efficiency benchmark only
python benchmarks/token_efficiency_benchmark.py

# Run existing performance benchmarks
python benchmarks/orjson_benchmark.py
python benchmarks/comprehensive_benchmark.py
```

## Benchmark Types

### 1. Token Efficiency Benchmark

Measures token count reduction across different formats using tiktoken `o200k_base` encoding (GPT-4o/GPT-5 tokenizer).

**Datasets:**
- 👥 Uniform employee records (2000 employees)
- 📈 Time-series analytics data (365 days)
- 🛒 E-commerce orders with nested structures (500 orders)
- ⭐ GitHub repositories (100 repos)

**Formats Compared:**
- JSON (2-space indentation)
- JSON compact (minified)
- MYSON Zen Grid (TBD)

**Output:** ASCII bar charts showing token counts and % reduction

### 2. Parsing Speed Benchmark

Measures deserialization throughput (MB/s) and latency (microseconds).

**Test Files:**
- `canada.json` (2.2 MB) - Number-heavy
- `citm_catalog.json` (1.7 MB) - Mixed
- `github.json` (55 KB) - String-heavy
- `twitter.json` (617 KB) - Unicode/objects

**Metrics:**
- Latency (median of 10 iterations)
- Throughput (MB/s)
- Speedup vs stdlib json

### 3. Combined Efficiency Ranking

**Formula:** `Efficiency Score = (Parsing Speed MB/s) × (Token Reduction %)`

Combines fast parsing with compact representation for an overall efficiency metric.

## Results

Latest comprehensive report: [`results/comprehensive-report.md`](results/comprehensive-report.md)

**Current Performance (Phase 1 - Correctness Complete):**
- ✅ Token reduction: **36.3%** (JSON compact baseline)
- ⚠️  Parsing speed: **199.6 MB/s** (~0.95x stdlib)
- 🎯 Efficiency score: **72.47**

**Target Performance (Phase 2 - Optimization):**
- 🚀 Token reduction: **40-60%** (with MYSON Zen Grid)
- 🚀 Parsing speed: **1000+ MB/s** (7-10x stdlib)
- 🚀 Efficiency score: **400-600**

## Comparison to Other Libraries

### vs orjson

| Library | Speed (MB/s) | Correctness | Notes |
|---------|--------------|-------------|-------|
| orjson  | 1000-3000    | ✅ 100%     | Industry standard |
| MYSON (current) | 140-200 | ✅ 100% | Phase 1 complete |
| MYSON (target) | 1000+ | ✅ 100% | Phase 2 goal |

### vs TOON

| Format | Token Reduction | Use Case |
|--------|----------------|----------|
| TOON   | 30-60%         | LLM context optimization |
| JSON compact | 36%     | Baseline |
| MYSON Zen Grid | 40-60% (est) | Token-efficient serialization |

## Project Structure

```
benchmarks/
├── README.md                          # This file
├── combined_benchmark_report.py       # Comprehensive report generator
├── token_efficiency_benchmark.py      # Token counting (toon-style)
├── orjson_benchmark.py                # Speed benchmarks (orjson-style)
├── comprehensive_benchmark.py         # Detailed performance analysis
├── token_savings_analysis.py          # Original token analysis
├── results/
│   └── comprehensive-report.md        # Latest benchmark results
└── test_data/
    ├── canada.json
    ├── citm_catalog.json
    ├── github.json
    └── twitter.json
```

## Methodology

### Token Counting
- **Tokenizer:** tiktoken `o200k_base` (GPT-4o/GPT-5)
- **Process:**
  1. Generate synthetic datasets
  2. Serialize to JSON (pretty & compact)
  3. Count tokens using tiktoken
  4. Calculate reduction percentages

### Parsing Speed
- **Hardware:** Linux x86_64
- **Compiler:** GCC -O3 -march=native -ffast-math
- **Method:**
  1. Warmup iterations (5x)
  2. Timed iterations (10-50x)
  3. Median latency calculation
  4. Throughput = File Size / Median Latency

### Statistical Analysis
- **Metric:** Median (robust to outliers)
- **Iterations:** 10-50 per test
- **Files:** Real-world JSON from orjson benchmarks

## Roadmap

### Phase 1: Correctness ✅ COMPLETE
- [x] Fix integer overflow handling
- [x] Reject trailing commas
- [x] Validate leading zeros
- [x] Add depth limiting (DoS protection)
- [x] 100% test pass rate (403 test files)
- [x] Validate against real-world JSON

### Phase 2: Optimization 🚧 IN PROGRESS
- [ ] Fast number parsing (2-3x speedup)
- [ ] SIMD string scanning (1.3-1.5x)
- [ ] String interning for keys (1.2-1.3x)
- [ ] Memory optimization (1.2x)
- [ ] Target: **1 GB/s+ throughput**

### Phase 3: Token Efficiency 📋 PLANNED
- [ ] Design MYSON Zen Grid format
- [ ] Implement serializer/deserializer
- [ ] Benchmark against TOON, MessagePack
- [ ] Target: **40-60% token reduction**

## Running Benchmarks

### Prerequisites

```bash
# Install dependencies
pip install -e .
pip install tiktoken

# Ensure test data exists
ls test_data/*.json
```

### Quick Benchmarks

```bash
# All-in-one comprehensive report
python benchmarks/combined_benchmark_report.py

# View results
cat benchmarks/results/comprehensive-report.md
```

### Individual Benchmarks

```bash
# Token efficiency (toon-style)
python benchmarks/token_efficiency_benchmark.py

# Speed comparison (orjson-style)
python benchmarks/orjson_benchmark.py

# Detailed performance analysis
python benchmarks/comprehensive_benchmark.py
```

## Contributing

To add new benchmarks:

1. **Add dataset generators** in `token_efficiency_benchmark.py`
2. **Add test files** to `test_data/`
3. **Update benchmarks** in respective scripts
4. **Regenerate report** with `combined_benchmark_report.py`

## References

- [toon-format/toon benchmarks](https://github.com/toon-format/toon/tree/main/benchmarks) - Token efficiency methodology
- [ijl/orjson README](https://github.com/ijl/orjson/blob/master/README.md) - Speed benchmarking approach
- [nativejson-benchmark](https://github.com/miloyip/nativejson-benchmark) - Comprehensive JSON parser testing
- [JSONTestSuite](https://github.com/nst/JSONTestSuite) - JSON correctness testing

---

*Last updated: 2025-12-24*
