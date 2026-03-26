#!/usr/bin/env python3
"""Simple test runner for LEXATRON - executes all test steps"""

import subprocess
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

print("=" * 80)
print("STEP 1: Running pytest tests (quick mode)")
print("=" * 80)
try:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_json_compatibility.py", "-v"],
        cwd=str(PROJECT_ROOT),
        timeout=120
    )
    print(f"\nStep 1 return code: {result.returncode}")
except Exception as e:
    print(f"Step 1 failed: {e}")

print("\n" + "=" * 80)
print("STEP 2: Attempting build with maturin (if needed)")
print("=" * 80)
try:
    result = subprocess.run(
        ["maturin", "develop", "--release"],
        cwd=str(PROJECT_ROOT),
        timeout=300
    )
    print(f"\nStep 2 return code: {result.returncode}")
except Exception as e:
    print(f"Step 2 failed: {e}")

print("\n" + "=" * 80)
print("STEP 3: Running manual smoke test")
print("=" * 80)

script = '''
try:
    import lexatron, json
    
    # Test 1: basic JSON output
    r = lexatron.dumps({"name": "Alice", "age": 30})
    print("Test 1:", r)
    assert json.loads(r) == {"name": "Alice", "age": 30}
    
    # Test 2: zen grid table
    data = [{"id": 1, "name": "Alice", "score": 95}, {"id": 2, "name": "Bob", "score": 87}]
    r = lexatron.dumps(data, zen_grid=True)
    print("Test 2 (zen grid):", r)
    rt = lexatron.loads(r)
    assert rt == data, f"Round-trip failed: {rt} != {data}"
    print("Round-trip: OK")
    
    # Test 3: token savings
    data_large = [{"employee_id": i, "first_name": f"Name{i}", "dept": "Eng"} for i in range(100)]
    zen = lexatron.dumps(data_large, zen_grid=True)
    compact = json.dumps(data_large, separators=(",",":"))
    print(f"Test 3: zen={len(zen)} chars, json={len(compact)} chars, savings={100*(len(compact)-len(zen))/len(compact):.1f}%")
except ImportError as e:
    print(f"Module not found: {e}")
    print("Make sure to run maturin develop --release first")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
'''

try:
    result = subprocess.run([sys.executable, "-c", script], timeout=60)
    print(f"\nStep 3 return code: {result.returncode}")
except Exception as e:
    print(f"Step 3 failed: {e}")

print("\n" + "=" * 80)
print("STEP 4: Running token efficiency benchmark")
print("=" * 80)

try:
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "benchmarks" / "token_efficiency.py")],
        cwd=str(PROJECT_ROOT),
        timeout=120
    )
    print(f"\nStep 4 return code: {result.returncode}")
except FileNotFoundError:
    print("Benchmark file not found")
except Exception as e:
    print(f"Step 4 failed: {e}")

print("\nAll steps completed!")

