import subprocess
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
print('STDOUT:', result.stdout[-8000:] if result.stdout else "")
print('STDERR:', result.stderr[-8000:] if result.stderr else "")
print('RC:', result.returncode)

if result.returncode == 0:
    print("\n" + "=" * 80)
    print("STEP 2: Running smoke tests")
    print("=" * 80)
    
    test_code = """
import lexatron

print("Test 1: Simple dict")
result = lexatron.dumps({'name': 'Alice', 'age': 30})
print(result)

print("\\nTest 2: List of dicts with zen_grid=True (default)")
result = lexatron.dumps([{'id': 1, 'x': 10}, {'id': 2, 'x': 20}])
print(result)

print("\\nTest 3: List of dicts with zen_grid=False")
result = lexatron.dumps([{'id': 1, 'x': 10}, {'id': 2, 'x': 20}], zen_grid=False)
print(result)
"""
    
    result = subprocess.run(['python', '-c', test_code], capture_output=True, text=True)
    print('STDOUT:', result.stdout)
    if result.stderr:
        print('STDERR:', result.stderr)
    print('RC:', result.returncode)
else:
    print("\nBuild failed! Please fix the compile errors above.")

