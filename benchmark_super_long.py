import time
import json
import sys
sys.path.insert(0, 'src')
import myson

# Load file
file_path = "benchmarks/super_long.json"
print(f"Loading {file_path}...")

with open(file_path, 'rb') as f:
    data = f.read()

size_mb = len(data) / (1024 * 1024)
print(f"File size: {size_mb:.2f} MB\n")

# Benchmark standard json
print("=== Standard JSON ===")
for i in range(3):
    start = time.perf_counter()
    result_json = json.loads(data)
    elapsed = time.perf_counter() - start
    throughput = size_mb / elapsed
    print(f"Run {i+1}: {elapsed:.3f}s ({throughput:.2f} MB/s)")

# Benchmark myson
print("\n=== MYSON ===")
for i in range(3):
    start = time.perf_counter()
    result_myson = myson.loads(data)
    elapsed = time.perf_counter() - start
    throughput = size_mb / elapsed
    print(f"Run {i+1}: {elapsed:.3f}s ({throughput:.2f} MB/s)")

# Quick validation
print("\n=== Validation ===")
print(f"Results match: {result_json == result_myson}")
