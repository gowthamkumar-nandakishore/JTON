#!/usr/bin/env python3
"""
Comprehensive benchmark suite using orjson's test data
Measures performance across diverse real-world JSON files
"""

import sys
import time
import statistics
import os
sys.path.insert(0, 'src')

import myson_fast

def load_test_file(filename):
    """Load test file"""
    path = os.path.join('test_data', filename)
    with open(path, 'rb') as f:
        return f.read()

def benchmark_file(name, data, num_runs=10):
    """Benchmark parsing a specific file"""
    size_mb = len(data) / (1024 * 1024)
    
    # Warmup
    for _ in range(3):
        myson_fast.loads(data)
    
    # Benchmark
    times = []
    for _ in range(num_runs):
        start = time.perf_counter()
        result = myson_fast.loads(data)
        end = time.perf_counter()
        times.append(end - start)
    
    # Calculate statistics
    avg_time = statistics.mean(times)
    min_time = min(times)
    max_time = max(times)
    throughput = size_mb / avg_time
    
    return {
        'name': name,
        'size_mb': size_mb,
        'avg_time': avg_time,
        'min_time': min_time,
        'max_time': max_time,
        'throughput': throughput,
        'times': times
    }

def print_results(results):
    """Print formatted benchmark results"""
    print("\n" + "=" * 90)
    print(f"{'File':<25} {'Size':<10} {'Avg Time':<12} {'Throughput':<15} {'Min/Max':<20}")
    print("=" * 90)
    
    for r in results:
        print(f"{r['name']:<25} {r['size_mb']:>6.2f} MB  {r['avg_time']:>8.4f}s   "
              f"{r['throughput']:>10.2f} MB/s   {r['min_time']:.4f}s / {r['max_time']:.4f}s")
    
    print("=" * 90)
    
    # Overall statistics
    total_size = sum(r['size_mb'] for r in results)
    total_time = sum(r['avg_time'] for r in results)
    overall_throughput = total_size / total_time
    avg_throughput = statistics.mean(r['throughput'] for r in results)
    
    print(f"\nTotal data processed: {total_size:.2f} MB")
    print(f"Total time: {total_time:.4f}s")
    print(f"Overall throughput: {overall_throughput:.2f} MB/s")
    print(f"Average throughput: {avg_throughput:.2f} MB/s")
    
    return overall_throughput

def compare_with_baseline(throughput):
    """Compare with baseline and targets"""
    baseline = 143.0
    target_1gb = 1000.0
    
    print("\n" + "=" * 90)
    print("PERFORMANCE ANALYSIS")
    print("=" * 90)
    
    speedup = throughput / baseline
    print(f"\nBaseline (143 MB/s) → Current ({throughput:.0f} MB/s)")
    print(f"Speedup: {speedup:.2f}x")
    
    if throughput >= target_1gb:
        print(f"🎉 TARGET ACHIEVED: {throughput:.0f} MB/s >= 1 GB/s!")
    else:
        remaining = target_1gb / throughput
        print(f"\nRemaining to 1 GB/s: {remaining:.2f}x speedup needed")
        
        # Estimate with further optimizations
        with_simd = throughput * 1.5
        with_custom_parsing = throughput * 2.0
        print(f"\nEstimated with SIMD: {with_simd:.0f} MB/s")
        print(f"Estimated with custom number parsing: {with_custom_parsing:.0f} MB/s")

def main():
    print("=" * 90)
    print("COMPREHENSIVE BENCHMARK SUITE")
    print("Using orjson's real-world JSON test data")
    print("=" * 90)
    
    test_files = [
        ('canada.json', 'Large GeoJSON with coordinates'),
        ('citm_catalog.json', 'Venue catalog data'),
        ('github.json', 'GitHub API events'),
        ('twitter.json', 'Twitter timeline'),
    ]
    
    results = []
    
    for filename, description in test_files:
        try:
            print(f"\n{'=' * 90}")
            print(f"Benchmarking: {filename}")
            print(f"Description: {description}")
            print(f"{'=' * 90}")
            
            data = load_test_file(filename)
            result = benchmark_file(filename, data)
            results.append(result)
            
            print(f"  Size: {result['size_mb']:.2f} MB")
            print(f"  Average time: {result['avg_time']:.4f}s")
            print(f"  Throughput: {result['throughput']:.2f} MB/s")
            
        except FileNotFoundError:
            print(f"  ⚠️  File not found: {filename}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    if results:
        overall_throughput = print_results(results)
        compare_with_baseline(overall_throughput)
    else:
        print("\n❌ No benchmarks completed")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
