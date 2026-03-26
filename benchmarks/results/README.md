# LEXATRON Benchmarks - Complete Index

## 📚 Documentation

### Quick Links

- **[SUMMARY.md](./SUMMARY.md)** - Executive summary with key findings and recommendations
- **[BENCHMARK_GUIDE.md](./BENCHMARK_GUIDE.md)** - Complete guide with methodology and detailed analysis
- **[token_efficiency.md](./token_efficiency.md)** - Raw benchmark results with ASCII charts
- **[benchmark_summary.md](./benchmark_summary.md)** - Overall benchmark report

### Benchmark Scripts

#### Core Benchmarks
- **[run_all_benchmarks.py](../run_all_benchmarks.py)** - Master script to run all benchmarks
- **[token_efficiency.py](../token_efficiency.py)** - Token efficiency comparison
- **[detailed_analysis.py](../detailed_analysis.py)** - In-depth token analysis with cost calculations
- **[benchmark_final.py](../benchmark_final.py)** - Comprehensive parsing speed benchmark
- **[benchmark_throughput.py](../benchmark_throughput.py)** - Quick throughput test

#### Supporting Modules
- **[datasets.py](../datasets.py)** - Dataset generators (employees, analytics, orders, etc.)
- **[formatters.py](../formatters.py)** - Format converters (JSON, YAML, XML, TOON, LEXATRON)

#### Utilities
- **[verify_organization.py](../verify_organization.py)** - Verify benchmark organization

---

## 🏆 Key Results

### Token Efficiency Rankings

**Overall** (180,725 tokens across 6 datasets):
1. **TOON**: 146,113 tokens (best)
2. **LEXATRON**: 180,725 tokens (baseline - currently JSON-compact)
3. **YAML**: 220,129 tokens
4. **JSON**: 282,332 tokens
5. **XML**: 332,171 tokens

### Cost Savings (vs JSON)

Using GPT-4o pricing:
- **TOON**: $0.34 saved per request
- **LEXATRON**: $0.25 saved per request  
- **YAML**: $0.16 saved per request

**Annual Savings** (1M API calls): $254,000 (LEXATRON vs JSON)

### Performance by Structure

| Structure | Best Format | LEXATRON Position |
|-----------|-------------|----------------|
| 100% Tabular | TOON (91,642) | 2nd (123,376) |
| Mixed (40-60%) | TOON (54,136) | 2nd (57,126) |
| Deeply Nested | **LEXATRON (223)** | **1st** ⭐ |

---

## 📖 How to Use This Benchmark Suite

### 1. Run Benchmarks

```bash
# All benchmarks
python benchmarks/run_all_benchmarks.py

# Specific benchmarks
python benchmarks/token_efficiency.py       # Token comparison
python benchmarks/detailed_analysis.py      # Cost analysis
python benchmarks/benchmark_final.py        # Parsing speed
```

### 2. View Results

```bash
# Quick summary
cat benchmarks/results/SUMMARY.md

# Complete guide
cat benchmarks/results/BENCHMARK_GUIDE.md

# Raw data
cat benchmarks/results/token_efficiency.md
```

### 3. Verify Organization

```bash
python benchmarks/verify_organization.py
```

---

## 🎯 Datasets Tested

1. **👥 Uniform Employee Records** (2,000 employees, 100% tabular)
2. **📈 Time-Series Analytics** (365 days, 100% tabular)
3. **⭐ GitHub Repositories** (100 repos, 100% tabular)
4. **🛒 E-commerce Orders** (500 orders with nested items, 60% tabular)
5. **🧾 Event Logs** (300 semi-uniform events, 40% tabular)
6. **🧩 Nested Configuration** (complex config, 0% tabular)

---

## 🔬 Formats Compared

- **JSON** - 2-space indented (human-readable baseline)
- **JSON-compact** - Minified (current LEXATRON implementation)
- **YAML** - Indentation-based format
- **XML** - Tag-based markup
- **TOON** - Token-Oriented Object Notation (community format)
- **LEXATRON** - Minimalist YSON (this project)
- **CSV** - For 100% tabular data only

---

## 🚀 Future Roadmap

### Phase 1: Benchmarking ✅ COMPLETE
- [x] Comprehensive dataset generation
- [x] Multi-format comparison (JSON, YAML, XML, TOON, LEXATRON)
- [x] Token efficiency analysis using GPT tokenizer
- [x] Cost savings calculations
- [x] Detailed reports and visualization

### Phase 2: Zen Grid Implementation ⏳ IN PROGRESS
- [ ] Design Zen Grid serialization format
- [ ] Implement tabular encoding
- [ ] Smart format auto-detection
- [ ] Hybrid tabular/nested optimization

### Phase 3: Optimization 🔮 PLANNED
- [ ] Parsing speed benchmarks
- [ ] Performance profiling
- [ ] SIMD optimization for Zen Grid
- [ ] Memory efficiency analysis

---

## 📊 Benchmark Methodology

### Token Counting
- **Tool**: tiktoken library
- **Encoding**: `o200k_base` (GPT-4o, GPT-5)
- **Measurement**: Total tokens per format at string level

### Cost Calculation
- **Input**: $2.50 per 1M tokens (GPT-4o pricing)
- **Output**: $10.00 per 1M tokens
- **Basis**: Real-world API pricing

### Data Generation
- Synthetic but realistic datasets
- Reproducible random generation
- Covers full spectrum: 0% to 100% tabular

---

## 🎓 References

- [toon-format/toon](https://github.com/toon-format/toon) - Token-oriented format inspiration
- [OpenAI tiktoken](https://github.com/openai/tiktoken) - Tokenizer library
- [LEXATRON Specs](../../specs/001-short-name-LEXATRON/) - Format specification

---

## 📝 Notes

### Current Limitations
- LEXATRON currently uses JSON-compact format
- Zen Grid serialization not yet implemented
- Parsing speed benchmarks require test data files

### Expected Improvements
Once Zen Grid is implemented:
- **20-35% token reduction** for 100% tabular data
- **Competitive with or better than TOON** for flat structures
- **Smart auto-selection** between formats

---

**Last Updated**: December 25, 2025  
**Benchmark Suite Version**: 1.0.0  
**LEXATRON Version**: 0.1.0

---

## Quick Start

```bash
# Clone and setup
git clone <repo>
cd LEXATRON
pip install -r requirements.txt

# Run all benchmarks
python benchmarks/run_all_benchmarks.py

# Read results
cat benchmarks/results/SUMMARY.md
```

For questions or issues, see the [main README](../../README.md).
