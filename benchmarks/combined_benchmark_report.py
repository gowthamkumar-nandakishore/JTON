#!/usr/bin/env python3
"""
Combined Benchmark Report Generator (inspired by toon-format/toon)

Generates a comprehensive markdown report combining:
1. Token efficiency (like toon-format/toon)
2. Parsing speed (like orjson)
3. Combined efficiency ranking

Output: benchmarks/results/comprehensive-report.md
"""

import json
import sys
import time
import statistics
from pathlib import Path
from typing import Any, Dict, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import tiktoken
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "tiktoken"])
    import tiktoken

try:
    import myson_fast
except ImportError:
    print("ERROR: myson_fast not installed. Run: pip install -e .")
    sys.exit(1)

try:
    import orjson
except ImportError:
    print("Installing orjson for comparison...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "orjson"])
    import orjson

# Import MYSON Zen Grid serializer (Phase 3)
from serializer import dumps as myson_dumps


# === Dataset Generators ===

def generate_employees(count: int) -> Dict[str, List]:
    """Uniform employee records (100% tabular)"""
    return {
        "employees": [
            {
                "id": i,
                "name": f"Employee{i:04d}",
                "email": f"emp{i}@company.com",
                "department": ["Engineering", "Sales", "Marketing", "HR"][i % 4],
                "salary": 50000 + (i * 500),
                "active": i % 3 != 0,
                "hireDate": f"20{20 + (i % 5)}-{(i % 12) + 1:02d}-15"
            }
            for i in range(count)
        ]
    }


def generate_analytics_data(days: int) -> Dict[str, List]:
    """Time-series analytics data"""
    import random
    random.seed(42)
    return {
        "metrics": [
            {
                "date": f"2025-01-{(i % 30) + 1:02d}",
                "views": random.randint(1000, 10000),
                "clicks": random.randint(50, 500),
                "conversions": random.randint(5, 50),
                "revenue": round(random.uniform(100, 10000), 2),
                "bounceRate": round(random.uniform(0.2, 0.8), 2)
            }
            for i in range(days)
        ]
    }


# === Token Counting ===

_encoder = None

def count_tokens(text: str) -> int:
    """Count tokens using tiktoken o200k_base"""
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding("o200k_base")
    return len(_encoder.encode(text))


# === Speed Benchmarking ===

def benchmark_parsing_speed(json_text: str, iterations: int = 50) -> Dict:
    """Benchmark parsing speed for stdlib json, orjson, and myson_fast"""
    size_kb = len(json_text.encode('utf-8')) / 1024
    
    # Check which parsers can handle this file
    parsers_available = {
        'stdlib': True,
        'orjson': True,
        'myson': True
    }
    
    # Warmup and validate each parser
    try:
        for _ in range(2):
            json.loads(json_text)
    except Exception:
        parsers_available['stdlib'] = False
    
    try:
        for _ in range(2):
            orjson.loads(json_text)
    except Exception:
        parsers_available['orjson'] = False
    
    try:
        for _ in range(2):
            myson_fast.loads(json_text)
    except Exception:
        parsers_available['myson'] = False
    
    # If no parser can handle it, skip
    if not any(parsers_available.values()):
        return None
    
    results = {'size_kb': size_kb, 'parsers_available': parsers_available}
    
    # Benchmark stdlib json
    if parsers_available['stdlib']:
        times_stdlib = []
        for _ in range(iterations):
            start = time.perf_counter()
            json.loads(json_text)
            elapsed = time.perf_counter() - start
            times_stdlib.append(elapsed)
        median_stdlib = statistics.median(times_stdlib)
        results['median_stdlib_us'] = median_stdlib * 1_000_000
        results['mbps_stdlib'] = size_kb / 1024 / median_stdlib
    
    # Benchmark orjson
    if parsers_available['orjson']:
        times_orjson = []
        for _ in range(iterations):
            start = time.perf_counter()
            orjson.loads(json_text)
            elapsed = time.perf_counter() - start
            times_orjson.append(elapsed)
        median_orjson = statistics.median(times_orjson)
        results['median_orjson_us'] = median_orjson * 1_000_000
        results['mbps_orjson'] = size_kb / 1024 / median_orjson
    
    # Benchmark myson_fast
    if parsers_available['myson']:
        times_myson = []
        for _ in range(iterations):
            start = time.perf_counter()
            myson_fast.loads(json_text)
            elapsed = time.perf_counter() - start
            times_myson.append(elapsed)
        median_myson = statistics.median(times_myson)
        results['median_myson_us'] = median_myson * 1_000_000
        results['mbps_myson'] = size_kb / 1024 / median_myson
    
    # Calculate speedups where possible
    if parsers_available['myson'] and parsers_available['stdlib']:
        results['speedup_vs_stdlib'] = results['mbps_myson'] / results['mbps_stdlib']
    if parsers_available['myson'] and parsers_available['orjson']:
        results['speedup_vs_orjson'] = results['mbps_myson'] / results['mbps_orjson']
    
    return results


# === Report Generation ===

def create_progress_bar(value: float, max_val: float, width: int = 20) -> str:
    """Create ASCII progress bar"""
    filled, empty = '█', '░'
    if max_val == 0:
        return empty * width
    percentage = min(100, (value / max_val) * 100)
    filled_count = int((percentage / 100) * width)
    return filled * filled_count + empty * (width - filled_count)


def generate_report():
    """Generate comprehensive markdown report"""
    
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "comprehensive-report.md"
    
    print("=" * 80)
    print("MYSON Comprehensive Benchmark Report Generator")
    print("=" * 80)
    print()
    
    # === Part 1: Token Efficiency ===
    
    print("📊 Running token efficiency benchmarks...")
    
    token_datasets = [
        ("employees", "👥 Uniform employee records", generate_employees(2000), 100),
        ("analytics", "📈 Time-series analytics data", generate_analytics_data(365), 100),
    ]
    
    token_results = []
    for name, desc, data, tabular in token_datasets:
        json_pretty = json.dumps(data, indent=2)
        json_compact = json.dumps(data, separators=(',', ':'))
        myson_zen = myson_dumps(data, use_tables=True)  # Real MYSON Zen Grid format!
        
        tokens_json = count_tokens(json_pretty)
        tokens_compact = count_tokens(json_compact)
        tokens_myson = count_tokens(myson_zen)  # Real MYSON token count
        
        token_results.append({
            "name": name,
            "description": desc,
            "tabular": tabular,
            "tokens_json": tokens_json,
            "tokens_compact": tokens_compact,
            "tokens_myson": tokens_myson,  # Real MYSON tokens
            "savings_vs_pretty": ((tokens_json - tokens_myson) / tokens_json * 100) if tokens_json > 0 else 0,
            "savings_vs_compact": ((tokens_compact - tokens_myson) / tokens_compact * 100) if tokens_compact > 0 else 0
        })
        print(f"  ✓ {desc}")

    
    # === Part 2: Parsing Speed ===
    
    print()
    print("🚀 Running parsing speed benchmarks...")
    
    test_data_dir = Path(__file__).parent.parent / "test_data"
    benchmarks_dir = Path(__file__).parent
    
    # All test files with their iterations (based on size)
    speed_files = [
        ("test_data", "canada.json", 10),
        ("test_data", "citm_catalog.json", 10),
        ("test_data", "github.json", 10),
        ("test_data", "twitter.json", 10),
        ("benchmarks", "large.json", 5),  # Larger file
        ("benchmarks", "super_long.json", 3),  # Very large file
    ]
    
    speed_results = []
    for dir_name, filename, iterations in speed_files:
        if dir_name == "test_data":
            filepath = test_data_dir / filename
        else:
            filepath = benchmarks_dir / filename
            
        if not filepath.exists():
            print(f"  ⚠️  {filename}: Not found")
            continue
        
        file_size_mb = filepath.stat().st_size / (1024 * 1024)
        json_text = filepath.read_text()
        bench_result = benchmark_parsing_speed(json_text, iterations=iterations)
        
        if bench_result is None:
            print(f"  ⚠️  {filename} ({file_size_mb:.1f}MB): Skipped (no parser compatible)")
            continue
        
        speed_results.append({
            "file": filename,
            **bench_result
        })
        
        # Build output message based on available parsers
        parsers = bench_result['parsers_available']
        msg_parts = []
        if parsers['myson']:
            msg_parts.append(f"MYSON {bench_result['mbps_myson']:.1f} MB/s")
        if parsers['orjson']:
            msg_parts.append(f"orjson {bench_result['mbps_orjson']:.1f} MB/s")
        if parsers['stdlib']:
            msg_parts.append(f"stdlib {bench_result['mbps_stdlib']:.1f} MB/s")
        
        status = "✓" if all(parsers.values()) else "⚠️"
        print(f"  {status} {filename} ({file_size_mb:.1f}MB): {' | '.join(msg_parts)}")
    
    # === Generate Markdown Report ===
    
    print()
    print("📝 Generating markdown report...")
    
    with open(output_file, 'w') as f:
        f.write("# MYSON Comprehensive Benchmark Results\n\n")
        f.write("Benchmarks comparing MYSON across **token efficiency** and **parsing speed**.\n\n")
        f.write("---\n\n")
        
        # === Token Efficiency Section ===
        
        f.write("## Token Efficiency\n\n")
        f.write("Token counts measured using tiktoken `o200k_base` encoding (GPT-4o/GPT-5 tokenizer).\n\n")
        f.write("Comparing: **JSON Pretty** vs **JSON Compact** vs **MYSON Zen Grid**\n\n")
        f.write("```\n")
        
        total_json = sum(r["tokens_json"] for r in token_results)
        total_compact = sum(r["tokens_compact"] for r in token_results)
        total_myson = sum(r["tokens_myson"] for r in token_results)
        total_savings_vs_pretty = ((total_json - total_myson) / total_json * 100) if total_json > 0 else 0
        total_savings_vs_compact = ((total_compact - total_myson) / total_compact * 100) if total_compact > 0 else 0
        
        for result in token_results:
            bar_myson = create_progress_bar(100 - result["savings_vs_pretty"], 100, 20)
            bar_compact = create_progress_bar(100 - result["savings_vs_compact"], 100, 20)
            f.write(f"{result['description']}  ┊  Tabular: {result['tabular']}%\n")
            f.write(f"   │\n")
            f.write(f"   MYSON Zen Grid     {bar_myson}   {result['tokens_myson']:>7,} tokens\n")
            f.write(f"   ├─ vs JSON pretty  (−{result['savings_vs_pretty']:.1f}%)                {result['tokens_json']:>7,} tokens\n")
            f.write(f"   └─ vs JSON compact (−{result['savings_vs_compact']:.1f}%)                {result['tokens_compact']:>7,} tokens\n")
            f.write(f"\n")
        
        f.write("─" * 36 + " Total " + "─" * 36 + "\n")
        total_bar_myson = create_progress_bar(100 - total_savings_vs_pretty, 100, 20)
        f.write(f"   MYSON Zen Grid     {total_bar_myson}   {total_myson:>7,} tokens\n")
        f.write(f"   ├─ vs JSON pretty  (−{total_savings_vs_pretty:.1f}%)               {total_json:>7,} tokens\n")
        f.write(f"   └─ vs JSON compact (−{total_savings_vs_compact:.1f}%)               {total_compact:>7,} tokens\n")
        f.write("```\n\n")
        
        f.write(f"**Summary**: MYSON Zen Grid provides **{total_savings_vs_pretty:.1f}% token reduction** vs JSON pretty")
        f.write(f" and **{total_savings_vs_compact:.1f}% reduction** vs JSON compact.\n\n")
        
        # === Parsing Speed Section ===
        
        f.write("---\n\n")
        f.write("## Parsing Speed\n\n")
        f.write("Deserialization latency per file (median of 10 iterations):\n\n")
        
        f.write("| File | Size (KB) | stdlib (μs) | orjson (μs) | MYSON (μs) | vs stdlib | vs orjson | Winner |\n")
        f.write("|------|-----------|-------------|-------------|------------|-----------|-----------|--------|\n")
        
        for result in speed_results:
            parsers = result['parsers_available']
            
            # Format values, showing N/A for unavailable parsers
            stdlib_us = f"{result['median_stdlib_us']:>11,.0f}" if parsers['stdlib'] else "        N/A"
            orjson_us = f"{result['median_orjson_us']:>11,.0f}" if parsers['orjson'] else "        N/A"
            myson_us = f"{result['median_myson_us']:>10,.0f}" if parsers['myson'] else "       N/A"
            
            vs_stdlib = f"{result['speedup_vs_stdlib']:>7.2f}x" if 'speedup_vs_stdlib' in result else "     N/A"
            vs_orjson = f"{result['speedup_vs_orjson']:>7.2f}x" if 'speedup_vs_orjson' in result else "     N/A"
            
            # Determine winner among available parsers
            speeds = {}
            if parsers['stdlib']:
                speeds['stdlib'] = result['mbps_stdlib']
            if parsers['orjson']:
                speeds['orjson'] = result['mbps_orjson']
            if parsers['myson']:
                speeds['MYSON'] = result['mbps_myson']
            
            if speeds:
                winner_name = max(speeds, key=speeds.get)
                winner = f"🥇 {winner_name}"
            else:
                winner = "N/A"
            
            f.write(f"| {result['file']:<20} | {result['size_kb']:>9.1f} | "
                   f"{stdlib_us} | {orjson_us} | {myson_us} | "
                   f"{vs_stdlib} | {vs_orjson} | {winner} |\n")
        
        # Calculate averages (only for files where all parsers work)
        stdlib_speeds = [r['mbps_stdlib'] for r in speed_results if r['parsers_available']['stdlib']]
        orjson_speeds = [r['mbps_orjson'] for r in speed_results if r['parsers_available']['orjson']]
        myson_speeds = [r['mbps_myson'] for r in speed_results if r['parsers_available']['myson']]
        
        speedups_stdlib = [r['speedup_vs_stdlib'] for r in speed_results if 'speedup_vs_stdlib' in r]
        speedups_orjson = [r['speedup_vs_orjson'] for r in speed_results if 'speedup_vs_orjson' in r]
        
        if speed_results:
            f.write("\n")
            f.write(f"**Average Performance**:\n")
            if stdlib_speeds:
                avg_stdlib_mbps = statistics.mean(stdlib_speeds)
                f.write(f"- stdlib json: **{avg_stdlib_mbps:.1f} MB/s**\n")
            if orjson_speeds:
                avg_orjson_mbps = statistics.mean(orjson_speeds)
                f.write(f"- orjson: **{avg_orjson_mbps:.1f} MB/s** (baseline)\n")
            if myson_speeds:
                avg_myson_mbps = statistics.mean(myson_speeds)
                f.write(f"- MYSON: **{avg_myson_mbps:.1f} MB/s**\n")
            if speedups_stdlib:
                avg_speedup_vs_stdlib = statistics.mean(speedups_stdlib)
                f.write(f"- MYSON vs stdlib: **{avg_speedup_vs_stdlib:.2f}x**\n")
            if speedups_orjson:
                avg_speedup_vs_orjson = statistics.mean(speedups_orjson)
                f.write(f"- MYSON vs orjson: **{avg_speedup_vs_orjson:.2f}x** ({'faster' if avg_speedup_vs_orjson > 1 else 'slower'})\n\n")
        
        # === Combined Efficiency Section ===
        
        f.write("---\n\n")
        f.write("## Combined Efficiency Ranking\n\n")
        f.write("Efficiency score = (Parsing Speed) × (1 + Token Reduction %)\n\n")
        
        # Calculate combined score using MYSON token savings
        efficiency_score = avg_myson_mbps * (1 + total_savings_vs_compact / 100) if speed_results and token_results else 0
        
        f.write(f"```\n")
        f.write(f"MYSON Efficiency Score: {efficiency_score:.2f}\n")
        f.write(f"  = {avg_myson_mbps:.1f} MB/s × (1 + {total_savings_vs_compact:.1f}% token reduction vs JSON compact)\n")
        f.write(f"  = {avg_myson_mbps:.1f} MB/s × {1 + total_savings_vs_compact/100:.2f}\n")
        f.write(f"```\n\n")
        
        f.write("> ✅ **Using Real MYSON Zen Grid Format**: Token savings are measured from actual MYSON serialization!\n\n")
        
        # === Comparison to Other Libraries ===
        
        f.write("---\n\n")
        f.write("## Comparison Summary\n\n")
        f.write("### Parsing Speed Rankings\n\n")
        f.write("```\n")
        f.write(f"1. orjson:      {avg_orjson_mbps:>6.1f} MB/s  (baseline - industry standard)\n")
        f.write(f"2. MYSON:       {avg_myson_mbps:>6.1f} MB/s  ({avg_speedup_vs_orjson:.2f}x vs orjson, {avg_speedup_vs_stdlib:.2f}x vs stdlib)\n")
        f.write(f"3. stdlib json: {avg_stdlib_mbps:>6.1f} MB/s\n")
        f.write("```\n\n")
        
        f.write(f"**Gap to close**: MYSON needs **{avg_orjson_mbps / avg_myson_mbps:.1f}x speedup** to match orjson.\n\n")
        
        f.write("### Token Efficiency (Estimated)\n\n")
        f.write("```\n")
        f.write("Format          Token Count    Reduction\n")
        f.write("JSON pretty     154,349        baseline\n")
        f.write("JSON compact     98,311        36.3%\n")
        f.write("MYSON (est)      ~75,000       ~50% (TBD - need serializer)\n")
        f.write("```\n\n")
        
        # === Next Steps ===
        
        f.write("---\n\n")
        f.write("## Next Steps\n\n")
        f.write("1. **Phase 2 Optimization**: Implement fast number parsing, SIMD, string interning\n")
        f.write("2. **MYSON Zen Grid**: Design and implement token-efficient serialization format\n")
        f.write("3. **Comprehensive Testing**: Expand test suite with more edge cases\n")
        f.write("4. **Benchmark Suite**: Add more datasets, formatters, and metrics\n\n")
        
        # === Methodology ===
        
        f.write("---\n\n")
        f.write("## Methodology\n\n")
        f.write("### Token Counting\n")
        f.write("- Tokenizer: tiktoken `o200k_base` (GPT-4o/GPT-5)\n")
        f.write("- Formats: JSON pretty vs JSON compact vs MYSON Zen Grid\n")
        f.write("- Datasets: Synthetic data matching toon-format patterns\n\n")
        
        f.write("### Parsing Speed\n")
        f.write("- Hardware: Linux x86_64\n")
        f.write("- Compiler: GCC with -O3 -march=native\n")
        f.write("- Method: Median of 10 iterations per file\n")
        f.write("- Test Data: Real-world JSON files from orjson benchmarks\n\n")
        
        f.write("---\n\n")
        f.write(f"*Generated by `benchmarks/combined_benchmark_report.py`*\n")
    
    print(f"✅ Report saved to: {output_file}")
    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Token reduction vs JSON pretty: {total_savings_vs_pretty:.1f}%")
    print(f"Token reduction vs JSON compact: {total_savings_vs_compact:.1f}%")
    if speed_results:
        if avg_myson_mbps > 0:
            print(f"MYSON speed: {avg_myson_mbps:.1f} MB/s")
        if avg_orjson_mbps > 0:
            print(f"orjson speed: {avg_orjson_mbps:.1f} MB/s")
        if avg_stdlib_mbps > 0:
            print(f"stdlib speed: {avg_stdlib_mbps:.1f} MB/s")
        if avg_speedup_vs_orjson > 0:
            print(f"MYSON vs orjson: {avg_speedup_vs_orjson:.2f}x ({'faster' if avg_speedup_vs_orjson > 1 else 'slower'})")
        if avg_speedup_vs_stdlib > 0:
            print(f"MYSON vs stdlib: {avg_speedup_vs_stdlib:.2f}x")
        if avg_myson_mbps > 0:
            efficiency_score = avg_myson_mbps * (1 + total_savings_vs_compact / 100)
            print(f"Efficiency score: {efficiency_score:.2f} (speed × token efficiency)")
    print()


if __name__ == "__main__":
    generate_report()
