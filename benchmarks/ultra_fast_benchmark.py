#!/usr/bin/env python3
"""
Ultra-Fast Parser Benchmark
Tests the new pointer-based parser against baseline
"""

import sys
import time
import statistics
sys.path.insert(0, 'src')

import myson_fast

def measure_throughput(data_bytes, num_runs=5):
    """Measure parsing throughput"""
    times = []
    
    for i in range(num_runs):
        start = time.perf_counter()
        result = myson_fast.loads(data_bytes)
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
    
    return avg, min_val, max_val, stddev, variance

def generate_test_data():
    """Generate comprehensive test data"""
    import json
    
    # Mix of all data types
    data = {
        "numbers": list(range(100000)),
        "nested_arrays": [[i, i+1, i+2, i+3, i+4] for i in range(1000)],
        "objects": [
            {
                "id": i,
                "name": f"item_{i}",
                "values": [i, i*2, i*3],
                "nested": {"x": i, "y": i*2},
                "tags": [f"tag{i%10}", f"cat{i%5}"]
            }
            for i in range(5000)
        ],
        "strings": [f"string_number_{i}_with_some_length" for i in range(10000)],
        "booleans": [True, False] * 5000,
        "nulls": [None] * 1000,
    }
    
    return json.dumps(data).encode('utf-8')

def main():
    print("=" * 70)
    print("ULTRA-FAST PARSER BENCHMARK")
    print("Pointer arithmetic + lookup tables + optimized string scanning")
    print("=" * 70)
    
    # Generate test data
    print("\nGenerating test data (~10MB JSON)...")
    data = generate_test_data()
    size_mb = len(data) / (1024 * 1024)
    print(f"Generated {size_mb:.2f} MB of test data")
    
    # Warm-up
    print("\nWarm-up...")
    myson_fast.loads(data)
    
    # Benchmark
    print("\nBenchmarking (5 runs):")
    avg, min_val, max_val, stddev, variance = measure_throughput(data, num_runs=5)
    
    # Results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Average throughput: {avg:.2f} MB/s")
    print(f"Min: {min_val:.2f} MB/s")
    print(f"Max: {max_val:.2f} MB/s")
    print(f"Std Dev: {stddev:.2f} MB/s ({variance:.1f}%)")
    
    # Compare to baseline
    baseline = 143.0  # From growth_based_results.txt
    speedup = avg / baseline
    print(f"\nSpeedup vs baseline: {speedup:.2f}x ({baseline:.0f} → {avg:.0f} MB/s)")
    
    # Target analysis
    target_1gb = 1000.0
    if avg >= target_1gb:
        print(f"\n🎉 TARGET ACHIEVED: {avg:.2f} MB/s >= 1 GB/s!")
    else:
        remaining = target_1gb / avg
        print(f"\nRemaining to 1 GB/s: {remaining:.2f}x speedup needed")
        print(f"Estimated with SIMD + more optimizations: {avg * 1.5:.0f}-{avg * 2.0:.0f} MB/s")

if __name__ == '__main__':
    main()
