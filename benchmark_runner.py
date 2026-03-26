#!/usr/bin/env python
"""LEXATRON Benchmark Runner"""

import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
BENCH_DIR = PROJECT_ROOT / "benchmarks"

print("=" * 60)
print("1. Python and lexatron version check")
print("=" * 60)

try:
    import lexatron
    print(f"Python version: {sys.version}")
    print(f"lexatron version: {lexatron.__version__}")
except ImportError as e:
    print(f"Error importing lexatron: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("2. Benchmark: canada.json (number-heavy)")
print("=" * 60)

try:
    data = (BENCH_DIR / "canada.json").read_bytes()
    print(f"File size: {len(data) / 1e6:.2f} MB")
    
    # Warmup
    for _ in range(2):
        lexatron.loads(data)
    
    # Benchmark
    t = time.perf_counter()
    for _ in range(3):
        lexatron.loads(data)
    elapsed = time.perf_counter() - t
    
    throughput = len(data) * 3 / elapsed / 1e6
    print(f'canada.json: {throughput:.1f} MB/s ({len(data)/1e6:.2f} MB)')
    print(f'Time elapsed: {elapsed:.3f} seconds')
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("3. Benchmark: github.json (string-heavy)")
print("=" * 60)

try:
    data = (BENCH_DIR / "github.json").read_bytes()
    print(f"File size: {len(data) / 1e6:.2f} MB")
    
    # Warmup
    for _ in range(5):
        lexatron.loads(data)
    
    # Benchmark
    t = time.perf_counter()
    for _ in range(50):
        lexatron.loads(data)
    elapsed = time.perf_counter() - t
    
    throughput = len(data) * 50 / elapsed / 1e6
    print(f'github.json: {throughput:.1f} MB/s ({len(data)/1e6:.2f} MB)')
    print(f'Time elapsed: {elapsed:.3f} seconds')
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("4. Check lexatron functions (dumps support)")
print("=" * 60)

try:
    import lexatron
    print("Available lexatron attributes:")
    lexatron_attrs = [attr for attr in dir(lexatron) if not attr.startswith('_')]
    print(lexatron_attrs)
    print(f"\nHas 'dumps' function: {hasattr(lexatron, 'dumps')}")
    print(f"Has 'loads' function: {hasattr(lexatron, 'loads')}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("5. List benchmark files")
print("=" * 60)

try:
    if BENCH_DIR.exists():
        files = sorted(f.name for f in BENCH_DIR.glob("*.json"))
        print("Benchmark JSON files:")
        for f in files:
            size = (BENCH_DIR / f).stat().st_size
            print(f'  {f}: {size/1e6:.2f} MB')
    else:
        print("benchmarks directory not found")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("Benchmark completed")
print("=" * 60)


print("=" * 60)
print("1. Python and lexatron version check")
print("=" * 60)

try:
    import lexatron
    print(f"Python version: {sys.version}")
    print(f"lexatron version: {lexatron.__version__}")
except ImportError as e:
    print(f"Error importing lexatron: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("2. Benchmark: canada.json (number-heavy)")
print("=" * 60)

try:
    data = open('benchmarks/canada.json', 'rb').read()
    print(f"File size: {len(data) / 1e6:.2f} MB")
    
    # Warmup
    for _ in range(2):
        lexatron.loads(data)
    
    # Benchmark
    t = time.perf_counter()
    for _ in range(3):
        lexatron.loads(data)
    elapsed = time.perf_counter() - t
    
    throughput = len(data) * 3 / elapsed / 1e6
    print(f'canada.json: {throughput:.1f} MB/s ({len(data)/1e6:.2f} MB)')
    print(f'Time elapsed: {elapsed:.3f} seconds')
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("3. Benchmark: github.json (string-heavy)")
print("=" * 60)

try:
    data = open('benchmarks/github.json', 'rb').read()
    print(f"File size: {len(data) / 1e6:.2f} MB")
    
    # Warmup
    for _ in range(5):
        lexatron.loads(data)
    
    # Benchmark
    t = time.perf_counter()
    for _ in range(50):
        lexatron.loads(data)
    elapsed = time.perf_counter() - t
    
    throughput = len(data) * 50 / elapsed / 1e6
    print(f'github.json: {throughput:.1f} MB/s ({len(data)/1e6:.2f} MB)')
    print(f'Time elapsed: {elapsed:.3f} seconds')
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("4. Check lexatron functions (dumps support)")
print("=" * 60)

try:
    import lexatron
    print("Available lexatron attributes:")
    lexatron_attrs = [attr for attr in dir(lexatron) if not attr.startswith('_')]
    print(lexatron_attrs)
    print(f"\nHas 'dumps' function: {hasattr(lexatron, 'dumps')}")
    print(f"Has 'loads' function: {hasattr(lexatron, 'loads')}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("5. List benchmark files")
print("=" * 60)

try:
    if os.path.exists('benchmarks'):
        files = [f for f in os.listdir('benchmarks') if f.endswith('.json')]
        files.sort()
        print("Benchmark JSON files:")
        for f in files:
            size = os.path.getsize(f'benchmarks/{f}')
            print(f'  {f}: {size/1e6:.2f} MB')
    else:
        print("benchmarks directory not found")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("Benchmark completed")
print("=" * 60)
