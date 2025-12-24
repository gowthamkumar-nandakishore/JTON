#!/usr/bin/env python3
"""
Comprehensive benchmark suite inspired by orjson's benchmarking approach
Measures deserialization performance, correctness, and memory efficiency
"""

import sys
import time
import statistics
import os
import json
sys.path.insert(0, 'src')

import myson_fast

def format_time_us(seconds):
    """Format time in microseconds"""
    return f"{seconds * 1_000_000:.0f}"

def format_ops_per_sec(seconds):
    """Format operations per second"""
    ops = 1 / seconds
    if ops >= 1000:
        return f"{int(ops):,}"
    else:
        return f"{int(ops)}"

def load_test_file(filename):
    """Load test file"""
    path = os.path.join('test_data', filename)
    with open(path, 'rb') as f:
        return f.read()

def benchmark_deserialization(name, data, num_runs=100):
    """
    Benchmark deserialization performance
    Similar to orjson's latency benchmarks
    """
    # Warmup
    for _ in range(10):
        myson_fast.loads(data)
    
    # Benchmark myson_fast
    myson_times = []
    for _ in range(num_runs):
        start = time.perf_counter()
        result = myson_fast.loads(data)
        end = time.perf_counter()
        myson_times.append(end - start)
    
    # Benchmark stdlib json
    json_times = []
    data_str = data.decode('utf-8')
    for _ in range(num_runs):
        start = time.perf_counter()
        result = json.loads(data_str)
        end = time.perf_counter()
        json_times.append(end - start)
    
    myson_avg = statistics.mean(myson_times)
    json_avg = statistics.mean(json_times)
    speedup = json_avg / myson_avg
    
    return {
        'name': name,
        'size_kb': len(data) / 1024,
        'myson_time_us': myson_avg * 1_000_000,
        'myson_ops': 1 / myson_avg,
        'json_time_us': json_avg * 1_000_000,
        'json_ops': 1 / json_avg,
        'speedup': speedup
    }

def print_latency_table(results):
    """Print latency comparison table like orjson's README"""
    print("\n" + "=" * 100)
    print("DESERIALIZATION LATENCY BENCHMARKS")
    print("=" * 100)
    print()
    
    for r in results:
        print(f"\n{r['name']} deserialization")
        print("-" * 100)
        print(f"{'Library':<15} {'Time (μs)':<15} {'Ops/Sec':<15} {'vs myson_fast':<15}")
        print("-" * 100)
        print(f"{'myson_fast':<15} {r['myson_time_us']:<15.1f} {r['myson_ops']:<15,.0f} {'1':<15}")
        print(f"{'json':<15} {r['json_time_us']:<15.1f} {r['json_ops']:<15,.0f} {r['speedup']:<15.1f}")
        print()

def benchmark_throughput(name, data):
    """Measure raw throughput in MB/s"""
    size_mb = len(data) / (1024 * 1024)
    
    # Warmup
    for _ in range(3):
        myson_fast.loads(data)
    
    # Benchmark
    times = []
    for _ in range(10):
        start = time.perf_counter()
        result = myson_fast.loads(data)
        end = time.perf_counter()
        times.append(end - start)
    
    avg_time = statistics.mean(times)
    throughput = size_mb / avg_time
    
    return {
        'name': name,
        'size_mb': size_mb,
        'throughput': throughput
    }

def print_throughput_table(results):
    """Print throughput table"""
    print("\n" + "=" * 100)
    print("THROUGHPUT BENCHMARKS")
    print("=" * 100)
    print(f"\n{'File':<25} {'Size':<12} {'Throughput':<15}")
    print("-" * 100)
    
    for r in results:
        print(f"{r['name']:<25} {r['size_mb']:>6.2f} MB    {r['throughput']:>10.2f} MB/s")
    
    total_size = sum(r['size_mb'] for r in results)
    total_time = sum(r['size_mb'] / r['throughput'] for r in results)
    overall_throughput = total_size / total_time
    
    print("-" * 100)
    print(f"{'Overall':<25} {total_size:>6.2f} MB    {overall_throughput:>10.2f} MB/s")
    print()

def benchmark_correctness():
    """
    Test correctness on various edge cases
    Similar to orjson's correctness graph
    """
    print("\n" + "=" * 100)
    print("CORRECTNESS VALIDATION")
    print("=" * 100)
    
    test_cases = [
        # Valid JSON
        (b'{"a": 1}', True, "Simple object"),
        (b'[1, 2, 3]', True, "Simple array"),
        (b'{"nested": {"deep": [1, 2]}}', True, "Nested structures"),
        (b'"Hello, World!"', True, "Simple string"),
        (b'123.456', True, "Float number"),
        (b'-123', True, "Negative integer"),
        (b'true', True, "Boolean true"),
        (b'false', True, "Boolean false"),
        (b'null', True, "Null value"),
        
        # Invalid JSON (should reject)
        (b'{"a": 1,}', False, "Trailing comma in object"),
        (b'[1, 2,]', False, "Trailing comma in array"),
        (b'013', False, "Leading zero"),
        (b'{a: 1}', False, "Unquoted key"),
        (b"{'a': 1}", False, "Single quotes"),
        (b'[NaN]', False, "NaN value"),
        (b'[Infinity]', False, "Infinity value"),
    ]
    
    passed = 0
    failed = 0
    
    print(f"\n{'Test Case':<40} {'Expected':<12} {'Result':<12} {'Status':<10}")
    print("-" * 100)
    
    for data, should_pass, description in test_cases:
        try:
            result = myson_fast.loads(data)
            actual_pass = True
        except:
            actual_pass = False
        
        expected = "Valid" if should_pass else "Invalid"
        actual = "Parsed" if actual_pass else "Rejected"
        
        if should_pass == actual_pass:
            status = "✓ PASS"
            passed += 1
        else:
            status = "✗ FAIL"
            failed += 1
        
        print(f"{description:<40} {expected:<12} {actual:<12} {status:<10}")
    
    print("-" * 100)
    print(f"\nTotal: {passed + failed} tests, {passed} passed, {failed} failed")
    print(f"Correctness: {100 * passed / (passed + failed):.1f}%")
    print()
    
    return passed, failed

def benchmark_memory_efficiency():
    """
    Measure memory efficiency (similar to orjson's RSS column)
    Note: This is a simplified version - full RSS measurement requires platform-specific APIs
    """
    print("\n" + "=" * 100)
    print("MEMORY EFFICIENCY (Approximate)")
    print("=" * 100)
    print("\nNote: Full RSS measurement would require platform-specific memory profiling")
    print("This shows relative object sizes instead:")
    print()
    
    test_files = [
        'canada.json',
        'citm_catalog.json',
        'github.json',
        'twitter.json',
    ]
    
    print(f"{'File':<25} {'Input Size':<15} {'Ratio':<15}")
    print("-" * 100)
    
    for filename in test_files:
        try:
            data = load_test_file(filename)
            result = myson_fast.loads(data)
            
            input_size = len(data)
            # Rough estimate of output size (this is simplified)
            output_size = sys.getsizeof(result)
            ratio = output_size / input_size
            
            print(f"{filename:<25} {input_size / 1024:>10.2f} KB    {ratio:>10.2f}x")
        except:
            pass
    
    print()

def compare_with_json_stdlib():
    """
    Head-to-head comparison with json module
    """
    print("\n" + "=" * 100)
    print("COMPARISON WITH STANDARD LIBRARY json MODULE")
    print("=" * 100)
    
    test_files = [
        'canada.json',
        'citm_catalog.json', 
        'github.json',
        'twitter.json',
    ]
    
    print(f"\n{'File':<25} {'myson_fast':<15} {'json':<15} {'Speedup':<15}")
    print("-" * 100)
    
    speedups = []
    
    for filename in test_files:
        try:
            data = load_test_file(filename)
            
            # Benchmark myson_fast
            myson_times = []
            for _ in range(20):
                start = time.perf_counter()
                myson_fast.loads(data)
                end = time.perf_counter()
                myson_times.append(end - start)
            myson_avg = statistics.mean(myson_times)
            
            # Benchmark json
            data_str = data.decode('utf-8')
            json_times = []
            for _ in range(20):
                start = time.perf_counter()
                json.loads(data_str)
                end = time.perf_counter()
                json_times.append(end - start)
            json_avg = statistics.mean(json_times)
            
            speedup = json_avg / myson_avg
            speedups.append(speedup)
            
            print(f"{filename:<25} {myson_avg * 1000:>10.2f} ms    {json_avg * 1000:>10.2f} ms    {speedup:>10.2f}x")
            
        except Exception as e:
            print(f"{filename:<25} Error: {e}")
    
    if speedups:
        avg_speedup = statistics.mean(speedups)
        print("-" * 100)
        print(f"{'Average':<25} {'':>15} {'':>15} {avg_speedup:>10.2f}x")
        print()

def progress_to_1gb():
    """Show progress toward 1 GB/s goal"""
    print("\n" + "=" * 100)
    print("PROGRESS TO 1 GB/s TARGET")
    print("=" * 100)
    
    test_files = [
        'canada.json',
        'citm_catalog.json',
        'github.json',
        'twitter.json',
    ]
    
    throughputs = []
    
    for filename in test_files:
        try:
            data = load_test_file(filename)
            result = benchmark_throughput(filename, data)
            throughputs.append(result['throughput'])
        except:
            pass
    
    if throughputs:
        overall = statistics.mean(throughputs)
        target = 1000.0
        percentage = (overall / target) * 100
        remaining = target / overall
        
        print(f"\nCurrent average throughput: {overall:.2f} MB/s")
        print(f"Target: {target:.2f} MB/s (1 GB/s)")
        print(f"Progress: {percentage:.1f}%")
        print(f"Remaining speedup needed: {remaining:.2f}x")
        
        # Visual progress bar
        bar_length = 50
        filled = int(bar_length * min(overall / target, 1.0))
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"\n[{bar}] {percentage:.1f}%")
        
        if overall >= target:
            print("\n🎉 TARGET ACHIEVED!")
        else:
            print(f"\nEstimated optimizations needed:")
            print(f"  • Fast number parsing: ~2x improvement")
            print(f"  • SIMD scanning: ~1.5x improvement")
            print(f"  • String interning: ~1.3x improvement")
            print(f"  Combined potential: ~{overall * 2 * 1.5 * 1.3:.0f} MB/s")
        
        print()

def main():
    """Run comprehensive benchmark suite"""
    print("=" * 100)
    print("MYSON_FAST COMPREHENSIVE BENCHMARK SUITE")
    print("Inspired by orjson's benchmarking methodology")
    print("=" * 100)
    
    test_files = [
        'twitter.json',
        'github.json',
        'citm_catalog.json',
        'canada.json',
    ]
    
    # 1. Latency benchmarks (like orjson's per-file tables)
    print("\n" + "=" * 100)
    print("PART 1: LATENCY BENCHMARKS")
    print("=" * 100)
    
    latency_results = []
    for filename in test_files:
        try:
            data = load_test_file(filename)
            result = benchmark_deserialization(filename, data, num_runs=100)
            latency_results.append(result)
        except Exception as e:
            print(f"Error benchmarking {filename}: {e}")
    
    if latency_results:
        print_latency_table(latency_results)
    
    # 2. Throughput benchmarks
    print("\n" + "=" * 100)
    print("PART 2: THROUGHPUT BENCHMARKS")
    print("=" * 100)
    
    throughput_results = []
    for filename in test_files:
        try:
            data = load_test_file(filename)
            result = benchmark_throughput(filename, data)
            throughput_results.append(result)
        except Exception as e:
            print(f"Error benchmarking {filename}: {e}")
    
    if throughput_results:
        print_throughput_table(throughput_results)
    
    # 3. Correctness validation (like orjson's correctness graph)
    benchmark_correctness()
    
    # 4. Comparison with stdlib
    compare_with_json_stdlib()
    
    # 5. Memory efficiency
    benchmark_memory_efficiency()
    
    # 6. Progress to goal
    progress_to_1gb()
    
    print("=" * 100)
    print("BENCHMARK SUITE COMPLETE")
    print("=" * 100)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
