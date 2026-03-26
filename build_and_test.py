#!/usr/bin/env python
import subprocess
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# Build
print("=" * 80)
print("RUNNING MATURIN BUILD")
print("=" * 80)
result = subprocess.run(
    ['maturin', 'develop', '--release'],
    cwd=str(PROJECT_ROOT),
    capture_output=True, text=True
)
print('STDOUT:')
print(result.stdout[-8000:])
print('\nSTDERR:')
print(result.stderr[-8000:])
print('\nRC:', result.returncode)

if result.returncode != 0:
    print("\n❌ BUILD FAILED")
    sys.exit(1)

print("\n✅ BUILD SUCCEEDED\n")

# Smoke test
print("=" * 80)
print("RUNNING SMOKE TEST")
print("=" * 80)
smoke_result = subprocess.run(
    ['python', '-c', '''
import uoon
print(uoon.dumps({"name": "Alice", "age": 30}))
print(uoon.dumps([{"id": 1, "x": 10}, {"id": 2, "x": 20}]))
print(uoon.dumps([{"id": 1, "x": 10}, {"id": 2, "x": 20}], zen_grid=False))
'''],
    cwd=str(PROJECT_ROOT),
    capture_output=True, text=True
)
print('SMOKE STDOUT:')
print(smoke_result.stdout)
print('\nSMOKE STDERR:')
print(smoke_result.stderr)
print('\nSMOKE RC:', smoke_result.returncode)

if smoke_result.returncode == 0:
    print("\n✅ SMOKE TEST PASSED")
else:
    print("\n❌ SMOKE TEST FAILED")
    sys.exit(1)

