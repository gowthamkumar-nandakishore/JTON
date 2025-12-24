#!/usr/bin/env python3
"""
Final Comprehensive Benchmark: stdlib json vs orjson vs MYSON NITRO
Tests across all major JSON datasets: citm_catalog, canada, github, twitter
"""
import json
import time
import statistics
import os
import sys

try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False
    print("⚠️  orjson not installed. Install with: pip install orjson")
    print("Continuing with stdlib json and MYSON only...\n")

try:
    import myson
    HAS_MYSON = True
except ImportError:
    HAS_MYSON = False
    print("❌ MYSON not installed. Run: maturin develop --release")
    sys.exit(1)

# Test files from orjson's benchmark suite + additional large files
TEST_FILES = {
    'github': 'test_data/github.json',
    'twitter': 'test_data/twitter.json',
    'citm_catalog': 'test_data/citm_catalog.json',
    'canada': 'test_data/canada.json',
    'large': 'benchmarks/large.json',
    'super_long': 'benchmarks/super_long.json',
}

def load_test_file(filepath):
    """Load test file as bytes"""
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'rb') as f:
        return f.read()

def benchmark_parser(name, data_bytes, parse_fn, iterations=50, warmup=10, timeout_seconds=10):
    """Benchmark a single parser on data with timeout protection"""
    size_mb = len(data_bytes) / (1024 * 1024)
    
    # Adjust iterations and timeout for file size
    if size_mb > 50:
        iterations = 3
        warmup = 1
        timeout_seconds = 30  # 30 seconds max for very large files
    elif size_mb > 10:
        iterations = 5
        warmup = 2
        timeout_seconds = 20
    elif size_mb > 5:
        iterations = 10
        warmup = 3
        timeout_seconds = 15
    
    # Test single parse first with timeout (max 5 seconds for initial test)
    max_single_parse_time = min(5.0, timeout_seconds * 0.5)
    try:
        start_test = time.perf_counter()
        parse_fn(data_bytes)
        elapsed_test = time.perf_counter() - start_test
        
        # If single parse is too slow, skip benchmarking
        if elapsed_test > max_single_parse_time:
            return None
    except Exception:
        return None  # Parser failed
    
    # Warmup
    try:
        for _ in range(warmup):
            parse_fn(data_bytes)
    except Exception:
        return None
    
    # Benchmark with individual timeout protection
    times = []
    for i in range(iterations):
        try:
            start = time.perf_counter()
            parse_fn(data_bytes)
            end = time.perf_counter()
            elapsed = end - start
            
            # Abort if any iteration is too slow (max 3 seconds per iteration)
            max_iteration_time = min(3.0, timeout_seconds * 0.3)
            if elapsed > max_iteration_time:
                if len(times) == 0:
                    return None  # Too slow, can't benchmark
                break  # Use what we have
            
            times.append(elapsed)
        except Exception:
            if len(times) == 0:
                return None
            break
    
    avg_time = statistics.mean(times)
    min_time = min(times)
    max_time = max(times)
    median_time = statistics.median(times)
    
    return {
        'name': name,
        'size_mb': size_mb,
        'avg_time_ms': avg_time * 1000,
        'min_time_ms': min_time * 1000,
        'max_time_ms': max_time * 1000,
        'median_time_ms': median_time * 1000,
        'avg_throughput': size_mb / avg_time,
        'peak_throughput': size_mb / min_time,
    }

def format_throughput(mbps):
    """Format throughput with color coding"""
    if mbps >= 400:
        return f"\033[92m{mbps:7.1f}\033[0m"  # Green
    elif mbps >= 200:
        return f"\033[93m{mbps:7.1f}\033[0m"  # Yellow
    else:
        return f"{mbps:7.1f}"

def print_separator(char='=', length=100):
    print(char * length)

def print_results_table(results_by_file):
    """Print comprehensive results table"""
    print_separator()
    print("COMPREHENSIVE BENCHMARK RESULTS - STDLIB vs ORJSON vs MYSON NITRO")
    print_separator()
    
    for file_name, results in results_by_file.items():
        if not results:
            continue
            
        print(f"\n📊 {file_name.upper()}")
        size_mb = results[0]['size_mb']
        print(f"   Size: {size_mb:.2f} MB")
        print()
        
        # Table header
        print("   Parser          Avg (ms)   Min (ms)   Max (ms)   Median (ms)   Avg (MB/s)   Peak (MB/s)")
        print("   " + "-" * 90)
        
        # Results for each parser
        for r in results:
            avg_mbps = format_throughput(r['avg_throughput'])
            peak_mbps = format_throughput(r['peak_throughput'])
            print(f"   {r['name']:<15} {r['avg_time_ms']:8.2f}   {r['min_time_ms']:8.2f}   "
                  f"{r['max_time_ms']:8.2f}   {r['median_time_ms']:10.2f}   {avg_mbps}   {peak_mbps}")
        
        # Calculate speedup ratios
        if len(results) > 1:
            print()
            stdlib_avg = next((r['avg_throughput'] for r in results if r['name'] == 'stdlib json'), None)
            orjson_avg = next((r['avg_throughput'] for r in results if r['name'] == 'orjson'), None)
            myson_avg = next((r['avg_throughput'] for r in results if r['name'] == 'MYSON NITRO'), None)
            
            if stdlib_avg and myson_avg:
                speedup = myson_avg / stdlib_avg
                print(f"   📈 MYSON vs stdlib: {speedup:.2f}x faster")
            
            if orjson_avg and myson_avg:
                ratio = (myson_avg / orjson_avg) * 100
                if ratio >= 100:
                    print(f"   🎉 MYSON vs orjson: {ratio:.1f}% (MYSON WINS!)")
                elif ratio >= 80:
                    print(f"   ✅ MYSON vs orjson: {ratio:.1f}% (Competitive!)")
                elif ratio >= 50:
                    print(f"   👍 MYSON vs orjson: {ratio:.1f}% (Good!)")
                else:
                    print(f"   📊 MYSON vs orjson: {ratio:.1f}%")

def print_summary(all_results):
    """Print overall summary across all files"""
    print("\n")
    print_separator()
    print("OVERALL SUMMARY - Average Across All Files")
    print_separator()
    print()
    
    # Collect averages by parser
    parser_averages = {}
    parser_peaks = {}
    
    for file_results in all_results.values():
        for r in file_results:
            if r['name'] not in parser_averages:
                parser_averages[r['name']] = []
                parser_peaks[r['name']] = []
            parser_averages[r['name']].append(r['avg_throughput'])
            parser_peaks[r['name']].append(r['peak_throughput'])
    
    print("   Parser          Avg Throughput   Peak Throughput   Files Tested")
    print("   " + "-" * 70)
    
    for parser_name in sorted(parser_averages.keys()):
        avg_tp = statistics.mean(parser_averages[parser_name])
        peak_tp = max(parser_peaks[parser_name])
        count = len(parser_averages[parser_name])
        
        avg_fmt = format_throughput(avg_tp)
        peak_fmt = format_throughput(peak_tp)
        
        print(f"   {parser_name:<15} {avg_fmt} MB/s   {peak_fmt} MB/s   {count} files")
    
    # Final verdict
    if 'MYSON NITRO' in parser_averages and 'orjson' in parser_averages:
        myson_overall = statistics.mean(parser_averages['MYSON NITRO'])
        orjson_overall = statistics.mean(parser_averages['orjson'])
        ratio = (myson_overall / orjson_overall) * 100
        
        print()
        print_separator('-')
        if ratio >= 100:
            print(f"   🏆 FINAL VERDICT: MYSON NITRO BEATS ORJSON! ({ratio:.1f}%)")
        elif ratio >= 85:
            print(f"   🥈 FINAL VERDICT: MYSON is highly competitive ({ratio:.1f}% of orjson)")
        elif ratio >= 70:
            print(f"   📊 FINAL VERDICT: MYSON has strong performance ({ratio:.1f}% of orjson)")
        else:
            print(f"   📈 FINAL VERDICT: MYSON at {ratio:.1f}% of orjson (room for optimization)")
        print_separator('-')
    
    print()
    print("NITRO Optimizations Active:")
    print("  ✓ Quote position indexing (SIMD AVX2)")
    print("  ✓ Zero-copy string extraction")
    print("  ✓ Direct FFI dict operations (PyDict_SetItem)")
    print("  ✓ Direct FFI list operations (PyList_SET_ITEM)")
    print("  ✓ String key caching (2048 entries)")
    print_separator()

def main():
    print("\n🚀 Starting Comprehensive JSON Parser Benchmark\n")
    
    # Load all test files
    test_data = {}
    for name, filepath in TEST_FILES.items():
        data = load_test_file(filepath)
        if data:
            test_data[name] = data
            print(f"✓ Loaded {name}: {len(data)/1024:.1f} KB")
        else:
            print(f"✗ Could not load {filepath}")
    
    if not test_data:
        print("\n❌ No test files found!")
        return
    
    print(f"\n📁 Testing {len(test_data)} files")
    print()
    
    all_results = {}
    
    for file_name, data_bytes in test_data.items():
        print(f"⚙️  Benchmarking {file_name}...")
        results = []
        
        # Benchmark stdlib json
        try:
            stdlib_result = benchmark_parser('stdlib json', data_bytes, json.loads)
            if stdlib_result:
                results.append(stdlib_result)
                print(f"   ✓ stdlib json: {stdlib_result['avg_throughput']:.1f} MB/s")
            else:
                print(f"   ✗ stdlib json: TIMEOUT or FAILED")
        except Exception as e:
            print(f"   ✗ stdlib json: EXCEPTION ({type(e).__name__})")
        
        # Benchmark orjson
        if HAS_ORJSON:
            try:
                orjson_result = benchmark_parser('orjson', data_bytes, orjson.loads)
                if orjson_result:
                    results.append(orjson_result)
                    print(f"   ✓ orjson:      {orjson_result['avg_throughput']:.1f} MB/s")
                else:
                    print(f"   ✗ orjson:      TIMEOUT or FAILED")
            except Exception as e:
                print(f"   ✗ orjson:      EXCEPTION ({type(e).__name__})")
        
        # Benchmark MYSON
        if HAS_MYSON:
            try:
                myson_result = benchmark_parser('MYSON NITRO', data_bytes, myson.loads)
                if myson_result:
                    results.append(myson_result)
                    print(f"   ✓ MYSON NITRO: {myson_result['avg_throughput']:.1f} MB/s")
                else:
                    print(f"   ✗ MYSON NITRO: TIMEOUT or FAILED")
            except Exception as e:
                print(f"   ✗ MYSON NITRO: EXCEPTION ({type(e).__name__})")
        
        all_results[file_name] = results
        print()
    
    # Print detailed results
    print_results_table(all_results)
    
    # Print summary
    print_summary(all_results)

if __name__ == '__main__':
    main()
