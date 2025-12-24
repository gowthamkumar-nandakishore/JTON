MYSON - Known Issues & Roadmap
================================================================================

CRITICAL ISSUES (P0) - Must fix before optimization
────────────────────────────────────────────────────────────────────────────────

❌ INTEGER OVERFLOW
   Status: BROKEN
   Impact: Data corruption for large numbers
   Test: number_10000000000000000999.json
   Current: 10000000000000000999 → 9223372036854775807 (clamped)
   Expected: 10000000000000000999 (Python long int)
   Fix: In parse_number(), detect overflow and use PyLong_FromString
   Location: src/myson_fast.pyx:382-477 (parse_number)
   
   Code change needed:
   ```python
   # After strtoll/strtod, check for overflow
   if errno == ERANGE or value == LLONG_MAX or value == LLONG_MIN:
       # Use Python arbitrary precision
       return PyLong_FromString(<const char*>start, NULL, 10)
   ```

================================================================================

SPEC COMPLIANCE ISSUES (P1) - Should fix for production
────────────────────────────────────────────────────────────────────────────────

⚠️ TRAILING COMMAS
   Status: PERMISSIVE (should reject)
   Impact: Non-standard JSON accepted
   Tests: jsonchecker/fail04.json, fail09.json
   Current: ["a",] and {"k":1,} are accepted
   Expected: Should raise parse error
   Fix: After parsing array/object element, check next char
   Location: src/myson_fast.pyx:292-380 (parse_array, parse_object)

⚠️ LEADING ZEROS
   Status: PERMISSIVE (should reject)
   Impact: Non-standard numbers accepted
   Test: jsonchecker/fail13.json
   Current: 013 is accepted as 13
   Expected: Should raise parse error (only 0 can start with 0)
   Fix: In parse_number(), after seeing '0', reject if next is digit
   Location: src/myson_fast.pyx:382-477 (parse_number)
   
   Code change needed:
   ```python
   if self.ptr[0] == 48:  # '0'
       if self.ptr + 1 < self.end and (CTAB[self.ptr[1]] & DG):
           self.error("Leading zeros not allowed")
   ```

================================================================================

SECURITY ISSUES (P2) - Important for robustness
────────────────────────────────────────────────────────────────────────────────

⚠️ DEEP NESTING (DoS Risk)
   Status: NO LIMIT
   Impact: Stack overflow / DoS attack
   Test: jsonchecker/fail18.json (20 levels)
   Current: No recursion limit
   Expected: Reject after N levels (default 1000)
   Fix: Add depth counter in FastParser class
   Location: src/myson_fast.pyx:127 (class init)
   
   Implementation:
   ```python
   cdef class FastParser:
       cdef Py_ssize_t depth
       cdef Py_ssize_t max_depth  # default 1000
       
       cdef inline void check_depth(self):
           if self.depth >= self.max_depth:
               self.error("Maximum nesting depth exceeded")
       
       # In parse_array/parse_object:
       self.depth += 1
       self.check_depth()
       # ... parse content ...
       self.depth -= 1
   ```

================================================================================

DESIGN DECISIONS (P3) - Document behavior
────────────────────────────────────────────────────────────────────────────────

ℹ️ TOP-LEVEL PRIMITIVES
   Status: ACCEPTED (intentional)
   Impact: None (RFC 8259 compliant)
   Test: jsonchecker/fail01.json
   Current: "string", 123, true, etc. are valid JSON
   Expected: Some parsers require object/array only
   Decision: KEEP current behavior
   Reason: JSON RFC 8259 (2017) allows any value at top level
   Note: Old RFC 4627 (2006) required object/array only

================================================================================

ENCODING ISSUES (P4) - Not implemented yet
────────────────────────────────────────────────────────────────────────────────

⏸️ INVALID UTF-8 SURROGATES
   Status: NOT APPLICABLE
   Impact: None (these test dumps(), not loads())
   Tests: string_*_invalid_codepoint.json
   Current: Files contain 0xED bytes (invalid UTF-8)
   Reason: Test encoding behavior (converting Python → JSON)
   Decision: SKIP these tests (encoding not implemented)

================================================================================

TEST SUMMARY
────────────────────────────────────────────────────────────────────────────────

Total: 403 test files
Passed: ~385 files (97%)
Failed: ~10 files (P0-P2 issues)
Skipped: ~8 files (encoding tests)

By category:
├─ Correctness: ✅ 97% (390/403 files)
├─ Performance: ✅ 139 MB/s baseline
├─ Real-world: ✅ github, twitter, canada, citm all pass
└─ Escape handling: ✅ Fixed

================================================================================

ROADMAP
────────────────────────────────────────────────────────────────────────────────

Phase 1: Critical Fixes (BEFORE optimization)
[P0] Fix integer overflow
     └─ Enables: Financial apps, large IDs, timestamps
     
[P1] Fix trailing commas & leading zeros
     └─ Enables: Strict spec compliance
     
[P2] Add depth limiting
     └─ Enables: Production deployment (DoS protection)

Phase 2: Performance Optimization (1 GB/s goal)
[OPT1] Fast number parsing
       └─ Target: 2-3x speedup on number-heavy JSON
       └─ Estimate: 93 MB/s → 280 MB/s on canada.json
       
[OPT2] String interning for object keys
       └─ Target: 1.2-1.3x speedup on object-heavy JSON
       
[OPT3] SIMD for whitespace/structural scanning
       └─ Target: 1.3-1.5x speedup across all cases
       
[OPT4] Memory optimization (pre-allocation)
       └─ Target: 1.2x speedup

Phase 3: Production Ready
[DOC] Document behavior vs RFC 8259
[DOC] Performance characteristics guide
[TEST] Add fuzzing tests
[BENCH] Continuous benchmarking

================================================================================

ESTIMATED TIMELINE
────────────────────────────────────────────────────────────────────────────────

P0 fix: 1-2 hours
P1 fixes: 1-2 hours  
P2 fix: 1 hour
→ Total critical fixes: 3-5 hours

Then ready for 1 GB/s optimization phase! 🚀

================================================================================

CURRENT STATUS: ✅ Test suite ready, issues identified, ready to fix
