#!/usr/bin/env python3
"""
🧪 JTON MASTER TEST RUNNER

ONE SCRIPT TO RUN ALL TESTS:
✅ JSON Compatibility Tests (primitives, arrays, objects, edge cases)
✅ Reference Vector Tests (644 JSON test files from JSONTestSuite)
✅ Unit Tests (when implemented)
✅ Integration Tests (when implemented)

Usage:
    python tests/run_all_tests.py                # Run ALL tests
    python tests/run_all_tests.py --quick        # Fast tests only (skip reference vectors)
    python tests/run_all_tests.py --compat       # JSON compatibility only
    python tests/run_all_tests.py --vectors      # Reference vectors only
    python tests/run_all_tests.py --verbose      # Show all test names

This is the ONLY script you need to run ALL tests!
"""

import sys
import subprocess
from pathlib import Path
import argparse

TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent


def print_header(title: str, char: str = "="):
    """Print formatted header"""
    width = 80
    print("\n" + char * width)
    print(f"  {title}")
    print(char * width + "\n")


def print_subheader(title: str):
    """Print formatted subheader"""
    print(f"\n{'─' * 80}")
    print(f"  {title}")
    print(f"{'─' * 80}\n")


def count_tests(test_file: str) -> int:
    """Count number of test functions in a file"""
    try:
        content = (TESTS_DIR / test_file).read_text()
        return content.count("def test_")
    except:
        return 0


def run_pytest(args: list[str], description: str) -> bool:
    """Run pytest with given arguments"""
    print(f"🧪 {description}")
    print(f"   Running: pytest {' '.join(args)}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest"] + args,
            cwd=PROJECT_ROOT,
            check=False,
        )
        
        if result.returncode == 0:
            print("\n✅ PASSED\n")
            return True
        else:
            print(f"\n❌ FAILED (exit code {result.returncode})\n")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        return False


def main():
    """Master test orchestrator"""
    parser = argparse.ArgumentParser(
        description="JTON Master Test Runner - ONE script for ALL tests"
    )
    parser.add_argument("--quick", action="store_true", help="Fast tests only (skip 644 reference vectors)")
    parser.add_argument("--compat", action="store_true", help="JSON compatibility tests only")
    parser.add_argument("--vectors", action="store_true", help="Reference vectors only (644 files)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()
    
    print_header("🧪 JTON MASTER TEST SUITE", "=")
    print("ONE SCRIPT TO TEST THEM ALL\n")
    
    # Count available tests
    compat_count = count_tests("test_json_compatibility.py")
    vectors_count = 644  # Known from file search
    
    if args.compat:
        print(f"Running: JSON Compatibility Tests ({compat_count} tests)")
    elif args.vectors:
        print(f"Running: Reference Vector Tests ({vectors_count} test files)")
    elif args.quick:
        print(f"Running: Quick Tests (JSON Compatibility only, {compat_count} tests)")
    else:
        print(f"Running: ALL Tests ({compat_count + vectors_count}+ tests)")
        print(f"  • JSON Compatibility: {compat_count} tests")
        print(f"  • Reference Vectors: {vectors_count} test files")
    
    print()
    
    # Check if pytest is installed
    try:
        subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            capture_output=True,
            check=True
        )
    except:
        print("📦 Installing pytest...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-q", "pytest"
        ])
    
    # Build pytest arguments
    pytest_args = []
    
    if args.verbose:
        pytest_args.append("-v")
    else:
        pytest_args.append("-q")  # Quiet mode
    
    # Select tests to run
    results = {}
    
    if args.compat:
        # JSON compatibility only
        print_header("JSON COMPATIBILITY TESTS")
        results["compat"] = run_pytest(
            pytest_args + ["tests/test_json_compatibility.py"],
            f"Testing JSON spec compliance ({compat_count} tests)"
        )
        
    elif args.vectors:
        # Reference vectors only
        print_header("REFERENCE VECTOR TESTS")
        results["vectors"] = run_pytest(
            pytest_args + ["tests/test_reference_vectors.py"],
            f"Testing against {vectors_count} reference JSON files"
        )
        
    elif args.quick:
        # Quick mode: compatibility only
        print_header("QUICK TEST MODE")
        results["compat"] = run_pytest(
            pytest_args + ["tests/test_json_compatibility.py"],
            f"JSON Compatibility ({compat_count} tests)"
        )
        
    else:
        # Run ALL tests
        print_header("1. JSON COMPATIBILITY TESTS")
        results["compat"] = run_pytest(
            pytest_args + ["tests/test_json_compatibility.py"],
            f"JSON spec compliance ({compat_count} tests)"
        )
        
        print_header("2. REFERENCE VECTOR TESTS")
        results["vectors"] = run_pytest(
            pytest_args + ["tests/test_reference_vectors.py"],
            f"JSONTestSuite corpus ({vectors_count} files)"
        )
        
        # Future: Unit and Integration tests
        # print_header("3. UNIT TESTS")
        # results["unit"] = run_pytest(
        #     pytest_args + ["tests/unit/"],
        #     "Unit tests for individual components"
        # )
        
        # print_header("4. INTEGRATION TESTS")
        # results["integration"] = run_pytest(
        #     pytest_args + ["tests/integration/"],
        #     "Integration tests for full workflows"
        # )
    
    # Final summary
    print_header("TEST SUITE COMPLETE", "=")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    failed = total - passed
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED!\n")
        print(f"✅ {passed}/{total} test suites passed")
    else:
        print(f"⚠️  {failed}/{total} test suite(s) failed\n")
        print("Failed suites:")
        for suite, success in results.items():
            if not success:
                print(f"  ❌ {suite}")
    
    print()
    print("Test files:")
    print(f"  • tests/test_json_compatibility.py ({compat_count} tests)")
    print(f"  • tests/test_reference_vectors.py ({vectors_count} files)")
    print(f"  • tests/reference_vectors/ (644 JSON files)")
    print()
    
    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()


