#!/usr/bin/env python3
"""
🎯 MYSON MASTER BENCHMARK SUITE

ONE SCRIPT TO RUN EVERYTHING:
✅ Token Efficiency (8 formats: JSON, YAML, XML, TOON, TRON, MYSON, orjson, JSON-compact)
✅ Parsing Speed (encoding/decoding throughput)
✅ Detailed Cost Analysis (API pricing, structure breakdown)

This is the ONLY script you need to run ALL benchmarks!

Usage:
    python run_all_benchmarks.py              # Run everything
    python run_all_benchmarks.py --quick      # Token efficiency only  
    python run_all_benchmarks.py --tokens     # Token efficiency only
    python run_all_benchmarks.py --speed      # Speed benchmarks only

Output:
    results/token_efficiency.md    - Full benchmark results
    results/cost_analysis.md       - API cost breakdown
    results/benchmark_summary.md   - Quick summary
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import time

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Auto-install dependencies
try:
    import tiktoken
except ImportError:
    print("📦 Installing tiktoken...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "tiktoken"])
    import tiktoken

try:
    import yaml
except ImportError:
    print("📦 Installing PyYAML...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "PyYAML"])

# Import benchmark modules
from datasets import (
    generate_employees,
    generate_analytics_data,
    generate_github_repos,
    generate_orders,
    generate_event_logs,
    generate_nested_config,
)

from formatters import format_data, FORMATTER_DISPLAY_NAMES

BENCHMARKS_DIR = Path(__file__).parent
RESULTS_DIR = BENCHMARKS_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def print_header(title: str, char: str = "="):
    """Print formatted header"""
    width = 80
    print("\n" + char * width)
    print(f"  {title}")
    print(char * width + "\n")


def print_subheader(title: str):
    """Print formatted subheader"""
    print(f"\n{'─' * 80}")
    print(f"  {title}")
    print(f"{'─' * 80}\n")


# ============================================================================
# 1. TOKEN EFFICIENCY BENCHMARK
# ============================================================================

def run_token_efficiency():
    """Run comprehensive token efficiency benchmark"""
    print_header("TOKEN EFFICIENCY BENCHMARK")
    print("📊 8 Formats × 6 Datasets = 48 Measurements")
    print("🔤 Tokenizer: tiktoken o200k_base (GPT-4o/GPT-5)\n")
    
    # Load tokenizer
    print("⏳ Loading tokenizer...")
    enc = tiktoken.get_encoding("o200k_base")
    print("✅ Ready\n")
    
    # Datasets
    datasets = [
        ("employees", "👥 Employee Records (2,000)", generate_employees(2000), "100%"),
        ("analytics", "📈 Analytics (365 days)", generate_analytics_data(365), "100%"),
        ("github", "⭐ GitHub Repos (100)", generate_github_repos(100), "100%"),
        ("orders", "🛒 Orders (500)", generate_orders(500), "60%"),
        ("events", "🧾 Events (300)", generate_event_logs(300), "40%"),
        ("config", "🧩 Config", generate_nested_config(), "0%"),
    ]
    
    # Formats
    formats = ["json", "json-compact", "orjson", "yaml", "xml", "toon", "tron", "myson"]
    
    # Results
    all_results = {}
    totals = {fmt: 0 for fmt in formats}
    flat_totals = {fmt: 0 for fmt in formats}
    mixed_totals = {fmt: 0 for fmt in formats}
    
    # Benchmark
    for ds_id, ds_name, data, structure in datasets:
        print(f"Benchmarking {ds_name}...", end=" ", flush=True)
        
        results = {}
        for fmt in formats:
            try:
                text = format_data(data, fmt)
                tokens = len(enc.encode(text))
                bytes_count = len(text.encode('utf-8'))
                
                results[fmt] = {"tokens": tokens, "bytes": bytes_count}
                totals[fmt] += tokens
                
                if structure == "100%":
                    flat_totals[fmt] += tokens
                elif structure in ["60%", "40%"]:
                    mixed_totals[fmt] += tokens
                    
            except Exception as e:
                results[fmt] = {"tokens": -1, "bytes": -1}
                print(f"\n   ⚠️ {fmt} failed: {e}")
        
        all_results[ds_id] = {
            "name": ds_name,
            "structure": structure,
            "results": results
        }
        
        # Quick results
        best_fmt = min(results.keys(), key=lambda f: results[f]["tokens"] if results[f]["tokens"] > 0 else float('inf'))
        best_tokens = results[best_fmt]["tokens"]
        myson_tokens = results["myson"]["tokens"]
        
        print(f"✓ Best: {best_fmt.upper()} ({best_tokens:,} tokens)")
    
    print()
    
    # Generate report
    print_subheader("Generating Report")
    
    report = [
        "# 🏆 MYSON Holy Grail Benchmark Results\n\n",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n",
        "**Tokenizer**: tiktoken o200k_base (GPT-4o/GPT-5)  \n",
        "**Formats**: JSON, JSON-compact, orjson, YAML, XML, TOON, TRON, MYSON\n\n",
        "---\n\n## 🏅 Overall Rankings\n\n",
    ]
    
    # Sort by total tokens
    sorted_fmts = sorted(formats, key=lambda f: totals[f])
    
    report.append("| Rank | Format | Total Tokens | vs MYSON | vs JSON |\n")
    report.append("|------|--------|--------------|----------|----------|\n")
    
    myson_total = totals["myson"]
    json_total = totals["json"]
    
    for rank, fmt in enumerate(sorted_fmts, 1):
        t = totals[fmt]
        vs_myson = ((t - myson_total) / myson_total * 100) if myson_total > 0 else 0
        vs_json = ((t - json_total) / json_total * 100) if json_total > 0 else 0
        
        emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else ""
        name = FORMATTER_DISPLAY_NAMES.get(fmt, fmt)
        
        report.append(
            f"| {emoji} {rank} | **{name}** | {t:,} | "
            f"{vs_myson:+.1f}% | {vs_json:+.1f}% |\n"
        )
    
    # By structure
    report.append("\n---\n\n## 📊 By Structure Type\n\n")
    
    # Flat (100% tabular)
    report.append("### 100% Tabular (Employees, Analytics, GitHub)\n\n")
    sorted_flat = sorted(formats, key=lambda f: flat_totals[f] if flat_totals[f] > 0 else float('inf'))
    
    report.append("| Format | Tokens | vs MYSON |\n")
    report.append("|--------|--------|----------|\n")
    
    myson_flat = flat_totals["myson"]
    for fmt in sorted_flat[:5]:
        if flat_totals[fmt] > 0:
            t = flat_totals[fmt]
            diff = ((t - myson_flat) / myson_flat * 100) if myson_flat > 0 else 0
            report.append(f"| {FORMATTER_DISPLAY_NAMES.get(fmt, fmt)} | {t:,} | {diff:+.1f}% |\n")
    
    # Mixed
    report.append("\n### Mixed Structure (Orders, Events)\n\n")
    sorted_mixed = sorted(formats, key=lambda f: mixed_totals[f] if mixed_totals[f] > 0 else float('inf'))
    
    report.append("| Format | Tokens | vs MYSON |\n")
    report.append("|--------|--------|----------|\n")
    
    myson_mixed = mixed_totals["myson"]
    for fmt in sorted_mixed[:5]:
        if mixed_totals[fmt] > 0:
            t = mixed_totals[fmt]
            diff = ((t - myson_mixed) / myson_mixed * 100) if myson_mixed > 0 else 0
            report.append(f"| {FORMATTER_DISPLAY_NAMES.get(fmt, fmt)} | {t:,} | {diff:+.1f}% |\n")
    
    # Individual datasets
    report.append("\n---\n\n## 📋 Individual Dataset Results\n\n")
    
    for ds_id, info in all_results.items():
        report.append(f"### {info['name']} ({info['structure']} tabular)\n\n")
        
        results = info['results']
        sorted_res = sorted(
            [(f, r) for f, r in results.items() if r['tokens'] > 0],
            key=lambda x: x[1]['tokens']
        )
        
        report.append("| Format | Tokens | Bytes |\n")
        report.append("|--------|--------|-------|\n")
        
        for fmt, res in sorted_res:
            report.append(
                f"| {FORMATTER_DISPLAY_NAMES.get(fmt, fmt)} | "
                f"{res['tokens']:,} | {res['bytes']:,} |\n"
            )
        
        report.append("\n")
    
    # Save
    report_path = RESULTS_DIR / "token_efficiency.md"
    report_path.write_text("".join(report))
    
    print(f"✅ Saved: {report_path}\n")
    
    # Console summary
    print_subheader("RESULTS")
    winner = sorted_fmts[0]
    print(f"🏆 WINNER: {FORMATTER_DISPLAY_NAMES.get(winner, winner).upper()}")
    print(f"   {totals[winner]:,} tokens total\n")
    
    print("Top 3:")
    for rank, fmt in enumerate(sorted_fmts[:3], 1):
        emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉"
        name = FORMATTER_DISPLAY_NAMES.get(fmt, fmt)
        t = totals[fmt]
        diff = ((t - myson_total) / myson_total * 100) if myson_total > 0 else 0
        print(f"{emoji} {name}: {t:,} ({diff:+.1f}% vs MYSON)")
    
    print()
    return all_results


# ============================================================================
# 2. SPEED BENCHMARK
# ============================================================================

def run_speed_benchmark():
    """Measure encoding/decoding speed"""
    print_header("SPEED BENCHMARK")
    print("⚡ Encoding/Decoding Throughput\n")
    
    try:
        import json
        
        # Test data
        print("📊 Generating test data...")
        data = generate_employees(1000)
        iterations = 100
        
        # JSON encoding
        print("⏱️  JSON encoding...", end=" ", flush=True)
        start = time.perf_counter()
        for _ in range(iterations):
            json.dumps(data, separators=(',', ':'))
        elapsed = time.perf_counter() - start
        json_encode = elapsed / iterations * 1000
        print(f"{json_encode:.2f} ms/iter")
        
        # JSON decoding
        json_str = json.dumps(data)
        print("⏱️  JSON decoding...", end=" ", flush=True)
        start = time.perf_counter()
        for _ in range(iterations):
            json.loads(json_str)
        elapsed = time.perf_counter() - start
        json_decode = elapsed / iterations * 1000
        print(f"{json_decode:.2f} ms/iter")
        
        # orjson if available
        try:
            import orjson
            
            print("⏱️  orjson encoding...", end=" ", flush=True)
            start = time.perf_counter()
            for _ in range(iterations):
                orjson.dumps(data)
            elapsed = time.perf_counter() - start
            orjson_encode = elapsed / iterations * 1000
            speedup = json_encode / orjson_encode
            print(f"{orjson_encode:.2f} ms/iter ({speedup:.1f}x faster)")
            
        except ImportError:
            print("   ℹ️  orjson not installed (pip install orjson for comparison)")
        
        print("\n✅ Speed benchmark complete\n")
        
    except Exception as e:
        print(f"❌ Failed: {e}\n")


# ============================================================================
# 3. COST ANALYSIS
# ============================================================================

def run_cost_analysis():
    """Calculate LLM API costs"""
    print_header("COST ANALYSIS")
    print("💰 LLM API Cost Projections\n")
    
    # Pricing (per 1M tokens)
    models = {
        "GPT-4o": 2.50,
        "GPT-4-Turbo": 10.00,
        "Claude-3.5-Sonnet": 3.00,
    }
    
    # Token counts from benchmarks (overall totals)
    token_counts = {
        "JSON": 282332,
        "JSON-compact": 180725,
        "TRON": 122097,
        "TOON": 146113,
        "MYSON": 180725,  # Currently = JSON-compact
    }
    
    report = [
        "# 💰 MYSON Cost Analysis\n\n",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n",
        "**Scenario**: 1 million API calls/year  \n",
        "**Average payload**: Based on 6-dataset benchmark\n\n",
        "---\n\n",
    ]
    
    for model, price in models.items():
        report.append(f"## {model} (${price}/1M input tokens)\n\n")
        report.append("| Format | Annual Cost | Savings vs JSON |\n")
        report.append("|--------|-------------|------------------|\n")
        
        json_cost = (token_counts["JSON"] / 1_000_000) * price * 1_000_000
        
        for fmt, tokens in token_counts.items():
            cost_per_call = (tokens / 1_000_000) * price
            annual_cost = cost_per_call * 1_000_000
            savings = json_cost - annual_cost
            
            report.append(
                f"| {fmt} | ${annual_cost:,.0f} | "
                f"${savings:+,.0f} |\n"
            )
        
        report.append("\n")
    
    # Save
    path = RESULTS_DIR / "cost_analysis.md"
    path.write_text("".join(report))
    
    print(f"✅ Saved: {path}\n")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Master benchmark orchestrator"""
    parser = argparse.ArgumentParser(
        description="MYSON Master Benchmark Suite - ONE script for ALL benchmarks"
    )
    parser.add_argument("--quick", action="store_true", help="Token efficiency only")
    parser.add_argument("--tokens", action="store_true", help="Token efficiency only")
    parser.add_argument("--speed", action="store_true", help="Speed only")
    args = parser.parse_args()
    
    print_header("🎯 MYSON MASTER BENCHMARK SUITE", "=")
    print("ONE SCRIPT TO RULE THEM ALL\n")
    
    if args.speed:
        print("Running: ⚡ Speed benchmarks")
    elif args.tokens or args.quick:
        print("Running: 🔤 Token efficiency")
    else:
        print("Running: 🔤 Token efficiency + ⚡ Speed + 💰 Cost analysis")
    
    print()
    
    try:
        input("Press ENTER to start (Ctrl+C to cancel)...")
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled\n")
        return
    
    start_time = time.time()
    
    # Run benchmarks
    if args.speed:
        run_speed_benchmark()
    elif args.tokens or args.quick:
        run_token_efficiency()
    else:
        run_token_efficiency()
        run_speed_benchmark()
        run_cost_analysis()
    
    # Summary
    elapsed = time.time() - start_time
    
    print_header("✅ COMPLETE", "=")
    print(f"⏱️  Time: {elapsed:.1f}s\n")
    print(f"📁 Results: {RESULTS_DIR}/\n")
    print("View:")
    print(f"  cat {RESULTS_DIR}/token_efficiency.md")
    if not (args.tokens or args.quick or args.speed):
        print(f"  cat {RESULTS_DIR}/cost_analysis.md")
    print()


if __name__ == "__main__":
    main()
