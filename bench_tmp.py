import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
BENCH_DIR = PROJECT_ROOT / "benchmarks"

import jton

files = [
    ('canada.json', BENCH_DIR / 'canada.json', 3),
    ('github.json', BENCH_DIR / 'github.json', 20),
    ('large.json',  BENCH_DIR / 'large.json',  2),
]

for name, path, iters in files:
    try:
        data = path.read_bytes()
        jton.loads(data)  # warmup
        start = time.perf_counter()
        for _ in range(iters):
            jton.loads(data)
        elapsed = time.perf_counter() - start
        mb_s = len(data) * iters / elapsed / 1e6
        print(f"{name}: {mb_s:.1f} MB/s ({len(data)/1e6:.2f} MB)")
    except Exception as e:
        print(f"{name}: ERROR - {e}")



