#!/usr/bin/env python3
import subprocess
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# Step 1: Build the project
print("=" * 80)
print("STEP 1: Building the Rust/PyO3 project")
print("=" * 80)
result = subprocess.run(
    ['maturin', 'develop', '--release'],
    cwd=str(PROJECT_ROOT),
    capture_output=True, text=True
)

stdout = result.stdout
stderr = result.stderr

# Print last 8000 chars of output
if stdout:
    print('STDOUT:')
    print(stdout[-8000:])
    
if stderr:
    print('STDERR:')
    print(stderr[-8000:])
    
print('Return Code:', result.returncode)

if result.returncode == 0:
    print("\n" + "=" * 80)
    print("STEP 2: Running smoke tests")
    print("=" * 80)
    
    try:
        import zson
        
        print("Test 1: Simple dict")
        result = zson.dumps({'name': 'Alice', 'age': 30})
        print(result)
        
        print("\nTest 2: List of dicts with zen_grid=True (default)")
        result = zson.dumps([{'id': 1, 'x': 10}, {'id': 2, 'x': 20}])
        print(result)
        
        print("\nTest 3: List of dicts with zen_grid=False")
        result = zson.dumps([{'id': 1, 'x': 10}, {'id': 2, 'x': 20}], zen_grid=False)
        print(result)
        
        print("\nAll tests passed!")
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
else:
    print("\nBuild failed! Compile errors need to be fixed.")

