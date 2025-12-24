import time
import json
import sys
sys.path.insert(0, 'src')
import myson

# Test with super_long.json
file_path = "benchmarks/super_long.json"
print(f"Loading {file_path}...")

with open(file_path, 'rb') as f:
    data = f.read()

size_mb = len(data) / (1024 * 1024)
print(f"File size: {size_mb:.2f} MB\n")

print("Current performance: ~145 MB/s")
print("Target: 1000 MB/s (7x improvement)\n")

print("Bottleneck analysis:")
print("1. List.append() - Python API overhead")
print("2. String decode - creating temporary objects")
print("3. Dict assignment - hash lookups")
print("4. Whitespace skipping - character by character\n")

print("Optimization strategy:")
print("✓ Use PyList_SET_ITEM instead of append")
print("✓ Pre-allocate lists with PyList_New(size)")
print("✓ Direct pointer arithmetic for whitespace")
print("✓ Lookup tables for character classification")
print("✓ String interning for dict keys")
print("✓ Batch processing where possible")
