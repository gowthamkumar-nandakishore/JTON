#!/usr/bin/env python3
"""
Comprehensive Token Efficiency Benchmark
Inspired by toon-format/toon benchmarks

Compares token counts across formats:
- JSON (2-space indent)
- JSON compact (minified)
- YAML
- XML
- TOON
- ZSON (Zen Grid)

Uses tiktoken with o200k_base encoding (GPT-4o/GPT-5 tokenizer).
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
from dataclasses import dataclass

# Add local modules to path
sys.path.insert(0, str(Path(__file__).parent))

from datasets import DATASETS, get_dataset
from formatters import format_data, FORMATTER_DISPLAY_NAMES

try:
    import tiktoken
    TOKENIZER = tiktoken.get_encoding("o200k_base")
except ImportError:
    print("📦 Installing tiktoken...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "tiktoken"])
    import tiktoken
    TOKENIZER = tiktoken.get_encoding("o200k_base")

try:
    import yaml
except ImportError:
    print("📦 Installing PyYAML...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "PyYAML"])


# === Configuration ===

# Formats to benchmark (in display order)
FORMATS = ["json", "json-compact", "orjson", "yaml", "xml", "toon", "tron", "ZSON"]

# Format order for comparisons (against ZSON as baseline)
COMPARISON_ORDER = ["json", "json-compact", "orjson", "yaml", "xml", "toon", "tron"]

# Bar chart settings
BAR_WIDTH = 20
TOKEN_PADDING = 7


# === Data Structures ===

@dataclass
class FormatMetrics:
    """Metrics for a single format"""
    name: str
    tokens: int
    savings: int  # Negative = ZSON uses fewer tokens
    savings_percent: float


@dataclass
class BenchmarkResult:
    """Results for a single dataset"""
    dataset_name: str
    description: str
    icon: str
    tabular_percent: int
    formats: List[FormatMetrics]
    data_sample: Any  # For detailed examples


# === Token Counting ===

def count_tokens(text: str) -> int:
    """Count tokens using tiktoken o200k_base encoding"""
    if not text:
        return 0
    return len(TOKENIZER.encode(text))


# === Benchmarking ===

def benchmark_dataset(dataset_name: str) -> BenchmarkResult:
    """Benchmark a single dataset across all formats"""
    dataset_info = DATASETS[dataset_name]
    data = get_dataset(dataset_name)
    
    # Calculate tokens for each format
    format_metrics = []
    ZSON_tokens = None
    
    for format_name in FORMATS:
        formatted = format_data(data, format_name)
        tokens = count_tokens(formatted)
        
        if format_name == "ZSON":
            ZSON_tokens = tokens
        
        format_metrics.append({
            "name": format_name,
            "tokens": tokens,
            "formatted": formatted,
        })
    
    # Calculate savings relative to ZSON
    results = []
    for metrics in format_metrics:
        savings = metrics["tokens"] - ZSON_tokens
        savings_percent = (savings / metrics["tokens"] * 100) if metrics["tokens"] > 0 else 0
        
        results.append(FormatMetrics(
            name=metrics["name"],
            tokens=metrics["tokens"],
            savings=savings,
            savings_percent=savings_percent,
        ))
    
    return BenchmarkResult(
        dataset_name=dataset_name,
        description=dataset_info["description"],
        icon=dataset_info["icon"],
        tabular_percent=dataset_info["tabular_percent"],
        formats=results,
        data_sample=data,
    )


def benchmark_all() -> List[BenchmarkResult]:
    """Run benchmarks on all datasets"""
    results = []
    
    print("🔬 Running Token Efficiency Benchmark")
    print(f"📊 Tokenizer: tiktoken o200k_base (GPT-4o/GPT-5)\n")
    
    for dataset_name in DATASETS:
        print(f"  Benchmarking {dataset_name}...", end=" ", flush=True)
        result = benchmark_dataset(dataset_name)
        results.append(result)
        print("✓")
    
    print()
    return results


# === Visual Formatting ===

def create_bar_chart(tokens: int, max_tokens: int, width: int = BAR_WIDTH) -> str:
    """Create ASCII bar chart"""
    if max_tokens == 0:
        return "░" * width
    
    filled = int((tokens / max_tokens) * width)
    empty = width - filled
    
    return "█" * filled + "░" * empty


def format_comparison_line(format_metrics: FormatMetrics, is_last: bool = False) -> str:
    """Format a comparison line showing savings vs ZSON"""
    label = FORMATTER_DISPLAY_NAMES.get(format_metrics.name, format_metrics.name.upper())
    
    # Sign for savings (negative means ZSON saves tokens)
    sign = "−" if format_metrics.savings_percent >= 0 else "+"
    percent = abs(format_metrics.savings_percent)
    signed_percent = f"{sign}{percent:.1f}%"
    
    connector = "└─" if is_last else "├─"
    token_str = f"{format_metrics.tokens:,}".rjust(TOKEN_PADDING)
    
    return f"   {connector} vs {label.ljust(13)} ({signed_percent.ljust(7)})   {token_str} tokens"


def format_dataset_result(result: BenchmarkResult) -> str:
    """Format a single dataset result"""
    lines = []
    
    # Header
    header = f"{result.icon} {result.description}  ┊  Tabular: {result.tabular_percent}%"
    lines.append(header)
    lines.append("   │")
    
    # Get ZSON and other format metrics
    ZSON = next(f for f in result.formats if f.name == "ZSON")
    others = [f for f in result.formats if f.name in COMPARISON_ORDER]
    
    # Find max tokens for bar chart
    max_tokens = max(f.tokens for f in result.formats)
    
    # ZSON baseline (first format might be CSV if available)
    csv_format = next((f for f in result.formats if f.name == "csv" and f.tokens > 0), None)
    
    if csv_format and result.tabular_percent == 100:
        # Show CSV first for flat datasets
        bar = create_bar_chart(csv_format.tokens, max_tokens)
        csv_str = f"{csv_format.tokens:,}".rjust(TOKEN_PADDING)
        lines.append(f"   CSV                 {bar}    {csv_str} tokens")
        
        # Show ZSON with comparison to CSV
        bar = create_bar_chart(ZSON.tokens, max_tokens)
        ZSON_str = f"{ZSON.tokens:,}".rjust(TOKEN_PADDING)
        csv_diff = ZSON.tokens - csv_format.tokens
        csv_diff_pct = (csv_diff / csv_format.tokens * 100) if csv_format.tokens > 0 else 0
        sign = "+" if csv_diff >= 0 else "−"
        lines.append(f"   ZSON               {bar}    {ZSON_str} tokens   ({sign}{abs(csv_diff_pct):.1f}% vs CSV)")
    else:
        # Show ZSON as baseline
        bar = create_bar_chart(ZSON.tokens, max_tokens)
        ZSON_str = f"{ZSON.tokens:,}".rjust(TOKEN_PADDING)
        lines.append(f"   ZSON               {bar}    {ZSON_str} tokens")
    
    # Show comparisons to other formats
    for i, fmt in enumerate(others):
        is_last = (i == len(others) - 1)
        lines.append(format_comparison_line(fmt, is_last))
    
    return "\n".join(lines)


def calculate_track_totals(results: List[BenchmarkResult], track: str) -> Dict[str, int]:
    """Calculate total tokens for a track"""
    track_results = [r for r in results if DATASETS[r.dataset_name]["track"] == track]
    
    totals = {}
    for format_name in FORMATS:
        total = sum(
            next(f.tokens for f in r.formats if f.name == format_name)
            for r in track_results
        )
        totals[format_name] = total
    
    return totals


def format_track_totals(totals: Dict[str, int], track_name: str) -> str:
    """Format track total summary"""
    lines = []
    lines.append(f"{'─' * 34} Total {'─' * 34}")
    
    ZSON_total = totals["ZSON"]
    max_tokens = max(totals.values())
    
    # Check if CSV is applicable
    csv_total = totals.get("csv", 0)
    
    if csv_total > 0:
        # Show CSV total first
        bar = create_bar_chart(csv_total, max_tokens)
        csv_str = f"{csv_total:,}".rjust(TOKEN_PADDING)
        lines.append(f"   CSV                 {bar}    {csv_str} tokens")
        
        # Show ZSON with CSV comparison
        bar = create_bar_chart(ZSON_total, max_tokens)
        ZSON_str = f"{ZSON_total:,}".rjust(TOKEN_PADDING)
        csv_diff = ZSON_total - csv_total
        csv_diff_pct = (csv_diff / csv_total * 100) if csv_total > 0 else 0
        sign = "+" if csv_diff >= 0 else "−"
        lines.append(f"   ZSON               {bar}    {ZSON_str} tokens   ({sign}{abs(csv_diff_pct):.1f}% vs CSV)")
    else:
        # Show ZSON baseline
        bar = create_bar_chart(ZSON_total, max_tokens)
        ZSON_str = f"{ZSON_total:,}".rjust(TOKEN_PADDING)
        lines.append(f"   ZSON               {bar}    {ZSON_str} tokens")
    
    # Show comparisons
    for i, format_name in enumerate(COMPARISON_ORDER):
        tokens = totals[format_name]
        savings = tokens - ZSON_total
        savings_pct = (savings / tokens * 100) if tokens > 0 else 0
        
        label = FORMATTER_DISPLAY_NAMES[format_name]
        sign = "−" if savings_pct >= 0 else "+"
        signed_percent = f"{sign}{abs(savings_pct):.1f}%"
        token_str = f"{tokens:,}".rjust(TOKEN_PADDING)
        
        is_last = (i == len(COMPARISON_ORDER) - 1)
        connector = "└─" if is_last else "├─"
        
        lines.append(f"   {connector} vs {label.ljust(13)} ({signed_percent.ljust(7)})   {token_str} tokens")
    
    return "\n".join(lines)


# === Report Generation ===

def generate_report(results: List[BenchmarkResult]) -> str:
    """Generate comprehensive markdown report"""
    sections = []
    
    # Separate by track
    flat_results = [r for r in results if DATASETS[r.dataset_name]["track"] == "flat"]
    mixed_results = [r for r in results if DATASETS[r.dataset_name]["track"] == "mixed"]
    
    # Mixed-Structure Track
    if mixed_results:
        sections.append("#### Mixed-Structure Track\n")
        sections.append("Datasets combining tabular and nested structures.\n")
        sections.append("```")
        
        for result in mixed_results:
            sections.append(format_dataset_result(result))
            sections.append("")
        
        # Track totals
        totals = calculate_track_totals(results, "mixed")
        sections.append(format_track_totals(totals, "Mixed-Structure"))
        sections.append("```\n")
    
    # Flat-Only Track
    if flat_results:
        sections.append("#### Flat-Only Track\n")
        sections.append("Datasets with flat tabular structures where CSV is applicable.\n")
        sections.append("```")
        
        for result in flat_results:
            sections.append(format_dataset_result(result))
            sections.append("")
        
        # Track totals
        totals = calculate_track_totals(results, "flat")
        sections.append(format_track_totals(totals, "Flat-Only"))
        sections.append("```\n")
    
    return "\n".join(sections)


def save_results(results: List[BenchmarkResult], output_path: Path):
    """Save results to markdown file"""
    report = generate_report(results)
    
    # Create full document
    doc = f"""# Token Efficiency Results

**Tokenizer:** tiktoken `o200k_base` (GPT-4o/GPT-5)  
**Date:** {Path(__file__).parent.parent}

Token counts measured across different serialization formats.
ZSON serves as the baseline for comparisons.

{report}

---
*Generated by benchmarks/token_efficiency.py*
"""
    
    output_path.write_text(doc)
    print(f"📄 Report saved to: {output_path}")


# === Main ===

def main():
    """Run comprehensive token efficiency benchmark"""
    # Run benchmarks
    results = benchmark_all()
    
    # Print to console
    print("=" * 80)
    print("TOKEN EFFICIENCY RESULTS")
    print("=" * 80)
    print()
    print(generate_report(results))
    
    # Save to file
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    
    output_path = results_dir / "token_efficiency.md"
    save_results(results, output_path)
    
    print("\n✅ Token efficiency benchmark complete!")


if __name__ == "__main__":
    main()
