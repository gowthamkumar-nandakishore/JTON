import subprocess, sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

result = subprocess.run(
    ['maturin', 'develop', '--release'],
    cwd=str(PROJECT_ROOT),
    capture_output=True, text=True
)
print('STDOUT:', result.stdout[-5000:])
print('STDERR:', result.stderr[-5000:])
print('RC:', result.returncode)
