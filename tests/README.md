# 🧪 UOON Test Suite

**ONE SCRIPT TO RUN ALL TESTS**

---

## 🚀 Quick Start

```bash
# Run ALL tests (recommended)
python tests/run_all_tests.py

# Quick mode (compatibility only, ~1 second)
python tests/run_all_tests.py --quick

# Specific test suites
python tests/run_all_tests.py --compat    # JSON compatibility only
python tests/run_all_tests.py --vectors   # 644 reference files only
```

---

## 📂 What Gets Tested

### Test Suites

| Suite | Tests | What It Checks |
|-------|-------|----------------|
| **JSON Compatibility** | ~50 tests | Primitives, arrays, objects, edge cases |
| **Reference Vectors** | 644 files | JSONTestSuite corpus (parsing/roundtrip) |
| Unit Tests | 0 | Individual components (future) |
| Integration Tests | 0 | Full workflows (future) |

### Test Files

```
tests/
├── run_all_tests.py              ⭐ MASTER - Run this!
├── test_json_compatibility.py    JSON spec compliance
├── test_reference_vectors.py     644 reference files
├── conftest.py                   Pytest configuration
└── reference_vectors/
    └── json/                     644 JSON test files
        ├── parsing/              JSONTestSuite parsing tests
        ├── roundtrip/            Roundtrip tests
        ├── encoding/             Encoding tests
        └── number/               Number handling tests
```

---

## 🎯 Test Coverage

### JSON Compatibility Tests (~50 tests)

- ✅ Primitives: null, booleans, numbers, strings
- ✅ Arrays: empty, nested, mixed types
- ✅ Objects: empty, nested, unicode keys
- ✅ Edge cases: special numbers (Infinity, NaN), escapes
- ✅ Roundtrip: `json.dumps(uoon.loads(x)) == x`

### Reference Vector Tests (644 files)

- ✅ **Parsing tests** (~300 files): Valid/invalid JSON detection
- ✅ **Roundtrip tests** (~250 files): Parse → Serialize → Parse
- ✅ **Encoding tests** (~50 files): Unicode, BOM, escapes
- ✅ **Number tests** (~44 files): Edge case number handling

**Source**: JSONTestSuite corpus + yyjson test vectors

---

## 🏃 Running Tests

### All Tests
```bash
python tests/run_all_tests.py
```

**Output**:
- JSON Compatibility: ~50 tests in ~1 second
- Reference Vectors: 644 files in ~5 seconds
- **Total**: ~700 tests in ~6 seconds

### Quick Mode (Fast!)
```bash
python tests/run_all_tests.py --quick
```

**Output**: ~50 tests in ~1 second

### Verbose Mode
```bash
python tests/run_all_tests.py --verbose
```

Shows every test name and result.

---

## 📊 What's NOT Here

The following are **NOT tests** (they're in `benchmarks/`):

- ❌ Token efficiency benchmarks → `benchmarks/run_all_benchmarks.py`
- ❌ Parsing speed benchmarks → `benchmarks/run_all_benchmarks.py --speed`
- ❌ Format comparisons → `benchmarks/run_all_benchmarks.py`

**Tests verify correctness. Benchmarks measure performance.**

---

## 🧹 Cleanup Done

We already have a clean structure:
- ✅ ONE master test runner (`run_all_tests.py`)
- ✅ 644 reference vectors organized by type
- ✅ No duplicate test files
- ✅ Clear separation: tests/ vs benchmarks/

**Nothing to delete!** The test suite was already well-organized.

---

## 📚 Adding New Tests

### Add to JSON Compatibility
Edit `test_json_compatibility.py`:
```python
def test_my_new_feature(self):
    assert uoon.loads('{"new": "feature"}') == {"new": "feature"}
```

### Add Reference Vectors
Drop JSON files into:
- `reference_vectors/json/parsing/` for parsing tests
- `reference_vectors/json/roundtrip/` for roundtrip tests

They'll auto-run next time!

---

## 🎯 Summary

**ONE command to run ALL tests:**
```bash
python tests/run_all_tests.py
```

**That's it!** No confusion, no duplicate files, just one simple command. 🚀

---

*Last Updated: December 25, 2025*  
*Test Count: ~700 tests (50 compatibility + 644 reference vectors)*
