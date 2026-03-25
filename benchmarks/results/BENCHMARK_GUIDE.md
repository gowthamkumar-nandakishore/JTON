# ZSON Token Efficiency Benchmark - Complete Guide

## Overview

This comprehensive benchmark suite compares ZSON's token efficiency against leading serialization formats: JSON, YAML, XML, and TOON. The analysis uses OpenAI's `o200k_base` tokenizer (GPT-4o/GPT-5) to measure real-world LLM API costs.

## Key Findings

### 🏆 Current Results

**Overall Token Efficiency Ranking:**

1. **TOON**: 146,113 tokens (most efficient)
2. **JSON-compact / ZSON**: 180,725 tokens 
3. **YAML**: 220,129 tokens
4. **JSON**: 282,332 tokens
5. **XML**: 332,171 tokens (least efficient)

### 💰 Cost Savings (vs JSON)

Using GPT-4o pricing ($2.50 per 1M input tokens):

- **TOON**: $0.34 saved per request (34% reduction)
- **ZSON**: $0.25 saved per request (36% reduction vs JSON, on par with JSON-compact)
- **YAML**: $0.16 saved per request (22% reduction)

### 📊 Structure-Based Performance

#### 100% Tabular Data (Flat Structures)
- **TOON**: 91,642 tokens (-34.6% vs ZSON) ⭐
- **ZSON**: 123,376 tokens (baseline)
- **JSON-compact**: 123,376 tokens (same as ZSON)
- **YAML**: 150,252 tokens (+17.9%)
- **JSON**: 189,384 tokens (+34.9%)
- **XML**: 223,364 tokens (+44.8%)

#### Mixed Structures (40-60% Tabular)
- **TOON**: 54,136 tokens (-5.5% vs ZSON) ⭐
- **ZSON**: 57,126 tokens (baseline)
- **JSON-compact**: 57,126 tokens (same as ZSON)
- **YAML**: 69,597 tokens (+17.9%)
- **JSON**: 92,567 tokens (+38.3%)
- **XML**: 108,339 tokens (+47.3%)

#### Deeply Nested (0% Tabular)
- **ZSON**: 223 tokens (baseline) ⭐
- **JSON-compact**: 223 tokens (same as ZSON)
- **YAML**: 280 tokens (+20.4%)
- **TOON**: 335 tokens (+33.4%)
- **JSON**: 381 tokens (+41.5%)
- **XML**: 468 tokens (+52.4%)

## Current Status: Why ZSON = JSON-compact?

⚠️ **Important Note**: ZSON currently uses JSON-compact format internally. The **Zen Grid** serialization format (ZSON's tabular optimization) is **not yet implemented**.

Once Zen Grid is complete, we expect:
- **20-35% token reduction** vs JSON-compact for 100% tabular data
- **Competitive with or better than TOON** for flat structures
- **Automatic format selection** based on data structure (tabular vs nested)

## Datasets Tested

### 1. 👥 Uniform Employee Records
- **Size**: 2,000 employees
- **Structure**: 100% tabular
- **Fields**: id, name, email, department, salary, active, hireDate, manager

**Results**:
- TOON: 71,421 tokens ⭐ (most efficient)
- ZSON: 97,407 tokens
- JSON: 151,211 tokens

### 2. 📈 Time-Series Analytics Data
- **Size**: 365 days
- **Structure**: 100% tabular
- **Fields**: date, views, clicks, conversions, revenue, bounceRate

**Results**:
- TOON: 10,965 tokens ⭐
- ZSON: 14,240 tokens
- JSON: 22,274 tokens

### 3. ⭐ Top 100 GitHub Repositories
- **Size**: 100 repos
- **Structure**: 100% tabular
- **Fields**: id, name, repo, description, dates, stars, watchers, forks, etc.

**Results**:
- TOON: 9,256 tokens ⭐
- ZSON: 11,729 tokens
- JSON: 15,899 tokens

### 4. 🛒 E-commerce Orders
- **Size**: 500 orders with nested items
- **Structure**: 60% tabular (orders) + 40% nested (items, shipping)
- **Fields**: orderId, customerId, dates, status, items[], shipping{}, total

**Results**:
- ZSON: 46,381 tokens ⭐ (most efficient)
- TOON: 47,526 tokens
- JSON: 76,898 tokens

### 5. 🧾 Semi-uniform Event Logs
- **Size**: 300 events
- **Structure**: 40% tabular (semi-uniform with type-specific fields)
- **Fields**: timestamp, eventType, userId, + type-specific

**Results**:
- TOON: 6,610 tokens ⭐
- ZSON: 10,745 tokens
- JSON: 15,669 tokens

### 6. 🧩 Deeply Nested Configuration
- **Size**: 1 complex config object
- **Structure**: 0% tabular (deeply nested)
- **Fields**: Nested application, server, database, cache configs

**Results**:
- ZSON: 223 tokens ⭐ (most efficient, tied with JSON-compact)
- YAML: 280 tokens
- TOON: 335 tokens
- JSON: 381 tokens

## Format Comparison Details

### JSON (Pretty-Printed)
- **Pros**: Human-readable, universal support, well-known
- **Cons**: Verbose, high token count due to indentation
- **Best for**: Human review, debugging, documentation

### JSON Compact (Minified)
- **Pros**: Minimal tokens for nested structures, standard
- **Cons**: Not human-readable, no tabular optimization
- **Best for**: API responses, deeply nested data

### YAML
- **Pros**: Human-readable, less verbose than JSON
- **Cons**: Still higher token count than compact formats
- **Best for**: Configuration files, human editing

### XML
- **Pros**: Rich metadata support, established ecosystem
- **Cons**: Extremely verbose, highest token count
- **Best for**: Legacy systems, SOAP APIs, document markup

### TOON (Token-Oriented Object Notation)
- **Pros**: Excellent for tabular data, table-style syntax
- **Cons**: New format, limited tooling, less efficient for deeply nested
- **Best for**: Highly tabular datasets, LLM context optimization

### ZSON (Minimalist YSON)
- **Current**: Uses JSON-compact (on par for nested, needs improvement for tabular)
- **Planned**: Zen Grid format for 20-35% tabular savings
- **Pros**: Automatic format selection, JSON compatibility, Rust performance
- **Best for**: Mixed workloads (both tabular and nested data)

## Recommendations

### When to Use Each Format

| Use Case | Recommended Format | Reasoning |
|----------|-------------------|-----------|
| 100% tabular data | TOON or ZSON Zen Grid* | Highest compression for tables |
| Mixed structure | ZSON* | Smart auto-selection |
| Deeply nested | JSON-compact or ZSON | Already optimal |
| Human editing | YAML or JSON | Readability priority |
| Legacy/XML systems | XML | Ecosystem requirement |
| LLM API cost optimization | TOON or ZSON Zen Grid* | Minimize tokens |

*Zen Grid implementation pending

### Development Priorities

1. **Implement Zen Grid Serialization**
   - Target: 20-35% reduction vs JSON-compact for tabular data
   - Goal: Match or exceed TOON for flat structures

2. **Smart Format Selection**
   - Automatically detect tabular vs nested structure
   - Use Zen Grid for ≥80% tabular, JSON-compact otherwise

3. **Hybrid Optimization**
   - Use Zen Grid for tabular sub-structures within nested data
   - Example: orders (nested) containing items (tabular)

## Running the Benchmarks

### Quick Start

```bash
# Run all benchmarks
python benchmarks/run_all_benchmarks.py

# Individual benchmarks
python benchmarks/token_efficiency.py      # Token comparison
python benchmarks/detailed_analysis.py     # In-depth analysis
python benchmarks/benchmark_final.py       # Parsing speed
```

### View Results

```bash
# Token efficiency results
cat benchmarks/results/token_efficiency.md

# Comprehensive summary
cat benchmarks/results/benchmark_summary.md

# This guide
cat benchmarks/results/BENCHMARK_GUIDE.md
```

### Requirements

```bash
pip install tiktoken PyYAML
```

## Methodology

### Token Counting

- **Tokenizer**: tiktoken with `o200k_base` encoding
- **Models**: GPT-4o, GPT-5 (OpenAI's latest tokenizer)
- **Measurement**: Total tokens per format, measured at string level

### Cost Calculation

Based on GPT-4o API pricing:
- Input tokens: $2.50 per 1M tokens
- Output tokens: $10.00 per 1M tokens

### Dataset Generation

All datasets are synthetically generated using realistic patterns:
- Employee records: Sequential IDs, realistic departments
- Analytics: Random but bounded metrics
- GitHub repos: Descending star counts, realistic metadata
- Orders: Nested items with varied quantities
- Events: Semi-uniform with type-specific fields
- Config: Deeply nested application settings

## Next Steps

### Implementation Roadmap

1. ✅ Comprehensive benchmark suite (DONE)
2. ✅ Dataset generators (DONE)
3. ✅ Multi-format comparison (DONE)
4. ⏳ Implement Zen Grid serialization
5. ⏳ Smart format auto-detection
6. ⏳ Hybrid tabular/nested optimization
7. ⏳ Performance benchmarks (parsing speed)

### Expected Improvements

Once Zen Grid is implemented:

**Flat-Only Track (100% tabular)**:
- Current: 123,376 tokens (JSON-compact)
- Target: 85,000-95,000 tokens (Zen Grid)
- Improvement: 23-31% reduction
- Goal: Competitive with or better than TOON (91,642 tokens)

**Mixed Track (40-60% tabular)**:
- Current: 57,126 tokens
- Target: 50,000-54,000 tokens
- Improvement: 5-13% reduction

## References

- [toon-format/toon](https://github.com/toon-format/toon) - Token-Oriented Object Notation
- [OpenAI Tokenizer](https://github.com/openai/tiktoken) - tiktoken library
- [ZSON Specs](../specs/001-short-name-ZSON/) - Format specification

---

**Last Updated**: December 25, 2025  
**Benchmark Version**: 1.0.0  
**ZSON Version**: 0.1.0 (Zen Grid pending)
