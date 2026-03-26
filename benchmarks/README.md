# 🎯 UOON Benchmarking Suite - SIMPLIFIED!

**ONE SCRIPT TO RULE THEM ALL**

---

## 🚀 Quick Start

```bash
# Run EVERYTHING (recommended)
python benchmarks/run_all_benchmarks.py

# Quick mode (tokens only)
python benchmarks/run_all_benchmarks.py --quick

# Speed only
python benchmarks/run_all_benchmarks.py --speed
```

---

## 📂 What You Need to Know

### Master Scripts (Only 2!)

| Script | What It Does | When to Use |
|--------|--------------|-------------|
| **run_all_benchmarks.py** | ⭐ **EVERYTHING** - tokens + speed + cost | Always! |
| datasets.py | Generates test data | Auto-imported |
| formatters.py | Format encoders | Auto-imported |

### Results Location

```
benchmarks/results/
├── token_efficiency.md    ⭐ Main results
├── cost_analysis.md       💰 API costs
└── benchmark_summary.md   📊 Summary
```

---

## 🏆 Latest Results

**Winner**: **TRON** (122,097 tokens, 32.4% better than UOON)

See `results/QUICK_REFERENCE.md` for full breakdown.

---

## 📋 What Gets Benchmarked

### 8 Formats
JSON, JSON-compact, orjson, YAML, XML, TOON, **TRON**, UOON

### 6 Datasets
👥 Employees | 📈 Analytics | ⭐ GitHub | 🛒 Orders | 🧾 Events | 🧩 Config

---

## 🗑️ Deprecated Files

We consolidated 8+ scripts into ONE!

~~token_efficiency_benchmark.py~~  
~~benchmark_tokens.py~~  
~~benchmark_final.py~~  
~~benchmark_throughput.py~~  
~~detailed_analysis.py~~  
~~token_savings_analysis.py~~  

**Use `run_all_benchmarks.py` for everything!**

---

**That's it! Just run the master script.** 🎯
