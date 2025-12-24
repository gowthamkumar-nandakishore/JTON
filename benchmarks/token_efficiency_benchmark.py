#!/usr/bin/env python3
"""
Token Efficiency Benchmark (inspired by toon-format/toon)

Measures token count reduction for MYSON vs JSON formats.
Uses tiktoken with o200k_base encoding (GPT-4o/GPT-5 tokenizer).

Usage:
    python benchmarks/token_efficiency_benchmark.py
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import tiktoken
except ImportError:
    print("Installing tiktoken...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "tiktoken"])
    import tiktoken


# === Dataset Generators (matching toon-format patterns) ===

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
    """Time-series analytics data (100% tabular)"""
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


def generate_orders(count: int) -> Dict[str, List]:
    """E-commerce orders with nested structures (33% tabular)"""
    import random
    random.seed(42)
    return {
        "orders": [
            {
                "orderId": f"ORD-{i:06d}",
                "customerId": f"CUST-{random.randint(1, 1000)}",
                "status": ["pending", "shipped", "delivered"][i % 3],
                "total": round(random.uniform(20, 500), 2),
                "items": [
                    {
                        "productId": f"PROD-{random.randint(1, 100)}",
                        "quantity": random.randint(1, 5),
                        "price": round(random.uniform(10, 100), 2)
                    }
                    for _ in range(random.randint(1, 4))
                ],
                "shipping": {
                    "address": f"{random.randint(1, 9999)} Main St",
                    "city": ["New York", "Los Angeles", "Chicago"][i % 3],
                    "zipCode": f"{random.randint(10000, 99999)}"
                }
            }
            for i in range(count)
        ]
    }


def generate_github_repos(count: int) -> Dict[str, List]:
    """GitHub repository metadata (100% tabular)"""
    import random
    random.seed(42)
    return {
        "repositories": [
            {
                "id": 28457823 + i,
                "name": f"project-{i}",
                "repo": f"org{i % 10}/project-{i}",
                "description": f"An awesome open source project that does amazing things #{i}",
                "createdAt": f"20{15 + (i % 10)}-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}T12:00:00Z",
                "updatedAt": "2025-10-28T11:58:08Z",
                "pushedAt": "2025-10-28T10:17:16Z",
                "stars": random.randint(100, 500000),
                "watchers": random.randint(10, 10000),
                "forks": random.randint(5, 50000),
                "defaultBranch": ["main", "master"][i % 2]
            }
            for i in range(count)
        ]
    }


# === Token Counting ===

_encoder = None

def count_tokens(text: str) -> int:
    """Count tokens using tiktoken o200k_base (GPT-4o/GPT-5 tokenizer)"""
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding("o200k_base")
    return len(_encoder.encode(text))


# === Formatters ===

def to_json_pretty(data: Any) -> str:
    """JSON with 2-space indentation (toon baseline)"""
    return json.dumps(data, indent=2)


def to_json_compact(data: Any) -> str:
    """Minified JSON"""
    return json.dumps(data, separators=(',', ':'))


# === Progress Bar (toon-style) ===

def create_progress_bar(value: float, max_val: float, width: int = 20) -> str:
    """Create ASCII progress bar like toon-format"""
    filled = '█'
    empty = '░'
    if max_val == 0:
        return empty * width
    percentage = min(100, (value / max_val) * 100)
    filled_count = int((percentage / 100) * width)
    return filled * filled_count + empty * (width - filled_count)


# === Dataset Definitions ===

DATASETS = [
    {
        "name": "tabular",
        "description": "Uniform employee records",
        "icon": "👥",
        "generator": lambda: generate_employees(2000),
        "tabular": 100
    },
    {
        "name": "analytics",
        "description": "Time-series analytics data",
        "icon": "📈",
        "generator": lambda: generate_analytics_data(365),
        "tabular": 100
    },
    {
        "name": "nested",
        "description": "E-commerce orders with nested structures",
        "icon": "🛒",
        "generator": lambda: generate_orders(500),
        "tabular": 33
    },
    {
        "name": "github",
        "description": "Top 100 GitHub repositories",
        "icon": "⭐",
        "generator": lambda: generate_github_repos(100),
        "tabular": 100
    }
]


# === Main Benchmark ===

def run_benchmark():
    """Run token efficiency benchmark (toon-style output)"""
    
    print("Token Efficiency Benchmark")
    print()
    print("Measuring token counts with tiktoken o200k_base encoding (GPT-4o/GPT-5)...")
    print()
    
    results = []
    
    for dataset_spec in DATASETS:
        print(f"Generating {dataset_spec['description']}...", end=" ")
        data = dataset_spec["generator"]()
        print("✓")
        
        # Format in different representations
        json_pretty = to_json_pretty(data)
        json_compact = to_json_compact(data)
        
        # Count tokens
        tokens_json = count_tokens(json_pretty)
        tokens_compact = count_tokens(json_compact)
        
        # For now, JSON compact is our baseline (MYSON format TBD)
        tokens_myson = tokens_compact  # TODO: Replace with actual MYSON Zen Grid format
        
        results.append({
            "dataset": dataset_spec,
            "tokens": {
                "json": tokens_json,
                "json_compact": tokens_compact,
                "myson": tokens_myson
            }
        })
    
    print()
    print("=" * 80)
    print("Results")
    print("=" * 80)
    print()
    
    # Flat-Only Track (all our datasets are compatible)
    print("#### Flat-Only Track")
    print()
    print("Datasets with flat or semi-flat structures.")
    print()
    print("```")
    
    total_json = 0
    total_compact = 0
    total_myson = 0
    
    for result in results:
        dataset = result["dataset"]
        tokens = result["tokens"]
        
        # Calculate savings vs JSON pretty
        savings_json = tokens["json"] - tokens["myson"]
        savings_pct_json = (savings_json / tokens["json"] * 100) if tokens["json"] > 0 else 0
        
        # Calculate savings vs JSON compact
        savings_compact = tokens["json_compact"] - tokens["myson"]
        savings_pct_compact = (savings_compact / tokens["json_compact"] * 100) if tokens["json_compact"] > 0 else 0
        
        # Progress bar showing MYSON efficiency vs JSON pretty
        percentage = 100 - savings_pct_json
        bar = create_progress_bar(percentage, 100, 20)
        
        print(f"{dataset['icon']} {dataset['description']}  ┊  Tabular: {dataset['tabular']}%")
        print(f"   │")
        print(f"   JSON compact        {bar}   {tokens['myson']:>7,} tokens")
        
        # Show comparison vs JSON pretty
        sign_json = "−" if savings_pct_json >= 0 else "+"
        print(f"   ├─ vs JSON          ({sign_json}{abs(savings_pct_json):.1f}%)                {tokens['json']:>7,} tokens")
        
        # Note: For now MYSON == JSON compact, so this will show 0%
        sign_compact = "−" if savings_pct_compact >= 0 else "+"
        if savings_pct_compact != 0:
            print(f"   └─ vs JSON compact  ({sign_compact}{abs(savings_pct_compact):.1f}%)                {tokens['json_compact']:>7,} tokens")
        
        print()
        
        total_json += tokens["json"]
        total_compact += tokens["json_compact"]
        total_myson += tokens["myson"]
    
    # Total line
    total_savings_json = total_json - total_myson
    total_savings_pct_json = (total_savings_json / total_json * 100) if total_json > 0 else 0
    
    total_savings_compact = total_compact - total_myson
    total_savings_pct_compact = (total_savings_compact / total_compact * 100) if total_compact > 0 else 0
    
    print("─" * 36 + " Total " + "─" * 36)
    total_bar = create_progress_bar(100 - total_savings_pct_json, 100, 20)
    print(f"   JSON compact        {total_bar}   {total_myson:>7,} tokens")
    print(f"   ├─ vs JSON          (−{total_savings_pct_json:.1f}%)               {total_json:>7,} tokens")
    if total_savings_pct_compact != 0:
        print(f"   └─ vs JSON compact  (−{total_savings_pct_compact:.1f}%)               {total_compact:>7,} tokens")
    print("```")
    print()
    
    # Summary
    print("## Summary")
    print()
    print(f"**Current Status**: Using JSON compact as baseline (MYSON Zen Grid format TBD)")
    print()
    print(f"- Total tokens (JSON pretty): {total_json:,}")
    print(f"- Total tokens (JSON compact): {total_compact:,}")
    print(f"- Token reduction vs JSON pretty: **{total_savings_pct_json:.1f}%**")
    print()
    print("**Next Steps**:")
    print("1. Implement MYSON Zen Grid serializer")
    print("2. Integrate with myson_fast.pyx")
    print("3. Re-run benchmarks with actual MYSON format")
    print("4. Compare against TOON, MessagePack, other compact formats")
    print()


if __name__ == "__main__":
    run_benchmark()
