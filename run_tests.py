import subprocess, sys, time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

print("=" * 80)
print("STEP 1: Running pytest tests")
print("=" * 80)

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "-q"],
    cwd=str(PROJECT_ROOT),
    capture_output=True, text=True, timeout=120
)
print("STDOUT:", result.stdout[-4000:])
print("STDERR:", result.stderr[-2000:])
print("Return code:", result.returncode)

if result.returncode != 0:
    print("\n" + "=" * 80)
    print("STEP 2: Tests failed - attempting build with maturin")
    print("=" * 80)
    
    result = subprocess.run(
        ["maturin", "develop", "--release"],
        cwd=str(PROJECT_ROOT),
        capture_output=True, text=True, timeout=300
    )
    print(result.stdout[-2000:])
    print("STDERR:", result.stderr[-3000:])
    print("Build return code:", result.returncode)
    
    if result.returncode == 0:
        print("\n" + "=" * 80)
        print("STEP 1b: Re-running pytest tests after build")
        print("=" * 80)
        
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "-q"],
            cwd=str(PROJECT_ROOT),
            capture_output=True, text=True, timeout=120
        )
        print("STDOUT:", result.stdout[-4000:])
        print("STDERR:", result.stderr[-2000:])
        print("Return code:", result.returncode)

print("\n" + "=" * 80)
print("STEP 3: Running manual dumps() smoke test")
print("=" * 80)

script = '''
import uoon, json

# Test 1: basic JSON output
r = uoon.dumps({"name": "Alice", "age": 30})
print("Test 1:", r)
assert json.loads(r) == {"name": "Alice", "age": 30}

# Test 2: zen grid table
data = [{"id": 1, "name": "Alice", "score": 95}, {"id": 2, "name": "Bob", "score": 87}]
r = uoon.dumps(data, zen_grid=True)
print("Test 2 (zen grid):", r)
rt = uoon.loads(r)
assert rt == data, f"Round-trip failed: {rt} != {data}"
print("Round-trip: OK")

# Test 3: token savings
data_large = [{"employee_id": i, "first_name": f"Name{i}", "dept": "Eng"} for i in range(100)]
zen = uoon.dumps(data_large, zen_grid=True)
compact = json.dumps(data_large, separators=(",",":"))
print(f"Test 3: zen={len(zen)} chars, json={len(compact)} chars, savings={100*(len(compact)-len(zen))/len(compact):.1f}%")
'''

result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=60)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)
print("Return code:", result.returncode)

print("\n" + "=" * 80)
print("STEP 4: Running token efficiency benchmark")
print("=" * 80)

result = subprocess.run(
    [sys.executable, str(PROJECT_ROOT / "benchmarks" / "token_efficiency.py")],
    cwd=str(PROJECT_ROOT),
    capture_output=True, text=True, timeout=120
)
print(result.stdout[-5000:])
if result.stderr:
    print("STDERR:", result.stderr[-2000:])
print("Return code:", result.returncode)

