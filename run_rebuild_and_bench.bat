@echo off
cd /d "%~dp0"
echo ===== Running maturin develop --release =====
maturin develop --release
echo.
echo ===== Maturin command completed =====
echo.
echo ===== Running Python benchmark =====
python bench_tmp.py
