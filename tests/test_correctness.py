#!/usr/bin/env python3
"""
Comprehensive test suite using orjson's real-world test data
Ensures correctness across diverse JSON structures
"""

import sys
import json
import os
sys.path.insert(0, 'src')

import myson_fast

def load_test_file(filename):
    """Load test file"""
    path = os.path.join('test_data', filename)
    with open(path, 'rb') as f:
        return f.read()

def test_parse_correctness(name, data):
    """Test that our parser produces same result as stdlib json"""
    print(f"\nTesting {name}...")
    
    # Parse with stdlib
    try:
        stdlib_result = json.loads(data)
    except Exception as e:
        print(f"  ❌ stdlib json failed: {e}")
        return False
    
    # Parse with our parser
    try:
        our_result = myson_fast.loads(data)
    except Exception as e:
        print(f"  ❌ myson_fast failed: {e}")
        return False
    
    # Compare results
    if our_result == stdlib_result:
        print(f"  ✅ PASS - Results match")
        return True
    else:
        print(f"  ❌ FAIL - Results differ")
        # Show sample difference
        if isinstance(stdlib_result, dict):
            stdlib_keys = set(stdlib_result.keys())
            our_keys = set(our_result.keys())
            if stdlib_keys != our_keys:
                print(f"     Key difference: stdlib={len(stdlib_keys)}, ours={len(our_keys)}")
        return False

def main():
    print("=" * 70)
    print("COMPREHENSIVE CORRECTNESS TESTS")
    print("Using orjson's real-world JSON test data")
    print("=" * 70)
    
    test_files = [
        ('canada.json', 'GeoJSON: Large polygon coordinates'),
        ('citm_catalog.json', 'Venue catalog: Mixed objects/arrays'),
        ('github.json', 'GitHub events: Nested structures'),
        ('twitter.json', 'Twitter timeline: Unicode, nested objects'),
    ]
    
    results = []
    total_size = 0
    
    for filename, description in test_files:
        try:
            data = load_test_file(filename)
            size_mb = len(data) / (1024 * 1024)
            total_size += size_mb
            
            print(f"\n{'=' * 70}")
            print(f"File: {filename} ({size_mb:.2f} MB)")
            print(f"Description: {description}")
            print(f"{'=' * 70}")
            
            success = test_parse_correctness(filename, data)
            results.append((filename, success))
            
        except FileNotFoundError:
            print(f"  ⚠️  File not found: {filename}")
            results.append((filename, False))
        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
            results.append((filename, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\nTests passed: {passed}/{total}")
    print(f"Total test data: {total_size:.2f} MB\n")
    
    for filename, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} - {filename}")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
