#!/usr/bin/env python3
"""
Phase 1 Pre-allocation Benchmark
Target: >= 300 MB/s (2.2x speedup from 136 MB/s baseline)

Tests array-heavy workloads to measure impact of:
- prescan_array_size() for element counting
- PyList_New() pre-allocation
- PyList_SET_ITEM() instead of PyList_Append()
- Py_INCREF() proper refcounting
"""

import sys
import time
import statistics
sys.path.insert(0, 'src')

import myson_core

def measure_throughput(data_bytes, num_runs=5):
    """Measure parsing throughput with multiple runs"""
    times = []
    
    for i in range(num_runs):
        start = time.perf_counter()
        result = myson_core.loads(data_bytes)
        end = time.perf_counter()
        
        elapsed = end - start
        mb_per_sec = (len(data_bytes) / (1024 * 1024)) / elapsed
        times.append(mb_per_sec)
        print(f"  Run {i+1}: {mb_per_sec:.2f} MB/s ({elapsed:.6f}s)")
    
    avg = statistics.mean(times)
    min_val = min(times)
    max_val = max(times)
    stddev = statistics.stdev(times) if len(times) > 1 else 0.0
    variance = (stddev / avg) * 100 if avg > 0 else 0.0
    
    print(f"\nResults: avg={avg:.2f} MB/s, min={min_val:.2f}, max={max_val:.2f}, stddev={stddev:.2f}, variance={variance:.2f}%")
    
    if variance > 5.0:
        print(f"WARNING: Variance {variance:.2f}% exceeds 5% threshold")
    
    return avg, min_val, max_val, stddev, variance

def generate_super_long_json():
    """Generate 10MB array-heavy JSON for benchmarking"""
    import json
    
    # Create a large nested structure focused on arrays
    data = {
        "numbers": list(range(100000)),
        "nested": [[i, i+1, i+2, i+3, i+4] for i in range(1000)],
        "mixed": [
            {
                "id": i,
                "values": [i, i*2, i*3],
                "tags": ["tag" + str(i % 10), "cat" + str(i % 5)]
            }
            for i in range(5000)
        ]
    }
    
    return json.dumps(data).encode('utf-8')

def main():
    print("Phase 1: Pre-allocation Optimization Benchmark")
    print("=" * 60)
    
    # Generate test data
    print("\nGenerating super_long.json (array-heavy, ~10MB)...")
    data = generate_super_long_json()
    size_mb = len(data) / (1024 * 1024)
    print(f"Generated {size_mb:.2f} MB of test data")
    
    # Warm-up
    print("\nWarm-up run...")
    myson_core.loads(data)
    
    # Benchmark
    print("\nBenchmarking (5 runs):")
    avg, min_val, max_val, stddev, variance = measure_throughput(data, num_runs=5)
    
    # Check target
    print("\n" + "=" * 60)
    TARGET = 300.0
    if avg >= TARGET:
        print(f"✓ PASS: {avg:.2f} MB/s >= {TARGET} MB/s target")
        speedup = avg / 136.0  # baseline
        print(f"  Speedup: {speedup:.2f}x from baseline")
        exit(0)
    else:
        shortfall = TARGET - avg
        print(f"✗ FAIL: {avg:.2f} MB/s < {TARGET} MB/s target (shortfall: {shortfall:.2f} MB/s)")
        speedup = avg / 136.0
        print(f"  Speedup: {speedup:.2f}x from baseline (target was 2.2x)")
        exit(1)

if __name__ == '__main__':
    main()
