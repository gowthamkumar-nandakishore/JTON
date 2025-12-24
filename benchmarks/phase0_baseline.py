#!/usr/bin/env python3
"""Phase 0 Baseline Benchmark - Measure current performance before optimizations

This script measures the current parser throughput on super_long.json to establish
a baseline for measuring optimization improvements.

Target baseline: ~136 MB/s (current performance)
"""
import time
import myson
import os
import sys

def measure_throughput(filename, runs=5):
    """Measure parser throughput over multiple runs"""
    if not os.path.exists(filename):
        print(f"ERROR: File {filename} not found.")
        return None
    
    with open(filename, 'rb') as f:
        data = f.read()
    
    file_size_mb = len(data) / 1024 / 1024
    print(f"=== Phase 0: Baseline Performance ===")
    print(f"File: {filename} ({file_size_mb:.2f} MB)")
    print(f"Runs: {runs}")
    print()
    
    # Warmup
    print("Warming up (2 iterations)...")
    for _ in range(2):
        myson.loads(data)
    
    # Measure
    print(f"Measuring throughput ({runs} runs)...")
    throughputs = []
    for i in range(runs):
        start = time.perf_counter()
        result = myson.loads(data)
        end = time.perf_counter()
        
        elapsed = end - start
        throughput = file_size_mb / elapsed
        throughputs.append(throughput)
        print(f"Run {i+1}: {elapsed:.2f}s ({throughput:.2f} MB/s)")
    
    # Statistics
    avg_throughput = sum(throughputs) / len(throughputs)
    min_throughput = min(throughputs)
    max_throughput = max(throughputs)
    
    # Standard deviation
    variance = sum((t - avg_throughput) ** 2 for t in throughputs) / len(throughputs)
    std_dev = variance ** 0.5
    std_dev_pct = (std_dev / avg_throughput) * 100
    
    print()
    print("=== Results ===")
    print(f"Average: {avg_throughput:.2f} MB/s")
    print(f"Min:     {min_throughput:.2f} MB/s")
    print(f"Max:     {max_throughput:.2f} MB/s")
    print(f"Std Dev: {std_dev:.2f} MB/s ({std_dev_pct:.1f}%)")
    print()
    
    if std_dev_pct > 5:
        print("WARNING: Standard deviation > 5% - results may be unstable")
    else:
        print("✓ Standard deviation < 5% - stable results")
    
    return {
        'file': filename,
        'file_size_mb': file_size_mb,
        'runs': runs,
        'avg_throughput': avg_throughput,
        'min_throughput': min_throughput,
        'max_throughput': max_throughput,
        'std_dev': std_dev,
        'std_dev_pct': std_dev_pct,
        'throughputs': throughputs
    }

if __name__ == "__main__":
    # Benchmark super_long.json
    filename = "benchmarks/super_long.json"
    if not os.path.exists(filename):
        print(f"ERROR: {filename} not found. Cannot establish baseline.")
        sys.exit(1)
    
    results = measure_throughput(filename, runs=5)
    
    if results:
        print()
        print("=== Baseline Established ===")
        print(f"Current performance: {results['avg_throughput']:.2f} MB/s")
        print(f"Target Phase 1: >= 300 MB/s (2.2x improvement)")
        print(f"Target Phase 2: >= 500 MB/s (3.7x improvement)")
        print(f"Target Phase 3: >= 700 MB/s (5.1x improvement)")
