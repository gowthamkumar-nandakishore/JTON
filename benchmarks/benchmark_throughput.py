import time
import json
import myson
import os
import sys

def benchmark(filename):
    if not os.path.exists(filename):
        print(f"File {filename} not found.")
        return

    with open(filename, 'rb') as f:
        data = f.read()
    
    print(f"Benchmarking {filename} ({len(data)/1024/1024:.2f} MB)")
    
    # Warmup
    print("Warming up...")
    for _ in range(2):
        myson.loads(data)
        json.loads(data)
        
    # Measure myson
    print("Running MYSON...")
    start = time.time()
    for _ in range(10):
        myson.loads(data)
    end = time.time()
    myson_time = end - start
    myson_throughput = len(data)*10/myson_time/1024/1024
    print(f"MYSON: {myson_throughput:.2f} MB/s")
    
    # Measure json
    print("Running JSON...")
    start = time.time()
    for _ in range(10):
        json.loads(data)
    end = time.time()
    json_time = end - start
    json_throughput = len(data)*10/json_time/1024/1024
    print(f"JSON: {json_throughput:.2f} MB/s")
    
    print(f"Speedup: {myson_throughput/json_throughput:.2f}x")

if __name__ == "__main__":
    # Create dummy file if not exists
    if not os.path.exists("benchmarks/large.json"):
        print("Generating large.json...")
        data = [{"id": i, "name": f"Item {i}", "values": [j for j in range(10)]} for i in range(100000)]
        with open("benchmarks/large.json", "w") as f:
            json.dump(data, f)
            
    benchmark("benchmarks/large.json")
