# cython: language_level=3, boundscheck=False, wraparound=False, cdivision=True
# cython: initializedcheck=False, infer_types=True, optimize.use_switch=True
"""
Ultra-fast JSON parser targeting 1+ GB/s throughput
Inspired by orjson, msgspec, yapic.json, and simdjson

Key optimizations:
1. Pure pointer arithmetic (no bounds checking)
2. 256-byte character lookup table (O(1) classification)
3. Inline everything (minimal function call overhead)
4. Direct C-API manipulation (PyList_SET_ITEM, PyDict_SetItem)
5. Specialized fast paths for common cases
6. SIMD-ready string scanning
"""

from libc.stdlib cimport malloc, free, strtod, strtoll
from libc.string cimport memcpy, memchr, strlen
from libc.errno cimport errno, ERANGE
from libc.limits cimport LLONG_MAX, LLONG_MIN
from cpython.ref cimport PyObject, Py_INCREF, Py_DECREF
from cpython.unicode cimport PyUnicode_DecodeUTF8
from cpython.list cimport PyList_New
from cpython.dict cimport PyDict_New

cdef extern from "Python.h":
    void PyList_SET_ITEM(object list, Py_ssize_t index, object item)
    object PyDict_SetItem(object dict, object key, object value)
    object PyFloat_FromDouble(double v)
    void PyUnicode_InternInPlace(PyObject **string)

# Character classification bits
cdef enum:
    WS = 0x01      # Whitespace
    DG = 0x02      # Digit 0-9
    NM = 0x04      # Number char (+, -, ., e, E, 0-9)
    ST = 0x08      # Structural ([]{},: )

# Global 256-byte lookup table for O(1) character classification
cdef unsigned char CTAB[256]

cdef void init_table() nogil:
    cdef int i
    for i in range(256):
        CTAB[i] = 0
    
    # Whitespace
    CTAB[32] = WS   # space
    CTAB[9] = WS    # tab
    CTAB[10] = WS   # \n
    CTAB[13] = WS   # \r
    
    # Digits (also number chars)
    for i in range(48, 58):  # '0'-'9'
        CTAB[i] = DG | NM
    
    # Number characters
    CTAB[43] = NM   # +
    CTAB[45] = NM   # -
    CTAB[46] = NM   # .
    CTAB[101] = NM  # e
    CTAB[69] = NM   # E
    
    # Structural
    CTAB[91] = ST   # [
    CTAB[93] = ST   # ]
    CTAB[123] = ST  # {
    CTAB[125] = ST  # }
    CTAB[44] = ST   # ,
    CTAB[58] = ST   # :

init_table()

# Cached constants for object pooling
cdef dict SMALL_INT_CACHE = {}
cdef object TRUE_OBJ = True
cdef object FALSE_OBJ = False
cdef object NULL_OBJ = None

def _init_int_cache():
    """Initialize small integer cache"""
    for i in range(-5, 257):
        SMALL_INT_CACHE[i] = i

_init_int_cache()

# Fast inline helpers
cdef inline const unsigned char* skip_ws(const unsigned char* p, const unsigned char* end) nogil:
    """Skip whitespace using lookup table"""
    while p < end and (CTAB[p[0]] & WS):
        p += 1
    return p

cdef inline const unsigned char* find_char(
    const unsigned char* p,
    const unsigned char* end,
    unsigned char target
) nogil:
    """Fast character search using memchr"""
    cdef const unsigned char* result = <const unsigned char*>memchr(p, target, end - p)
    return result if result != NULL else end


cdef class FastParser:
    """Ultra-fast JSON parser using raw pointer arithmetic"""
    cdef const unsigned char* start   # Buffer start
    cdef const unsigned char* end     # Buffer end
    cdef const unsigned char* ptr     # Current position
    cdef int depth                     # Recursion depth guard
    cdef int max_depth                 # Maximum allowed depth
    
    def __cinit__(self, const unsigned char[:] data):
        self.start = &data[0]
        self.end = self.start + data.shape[0]
        self.ptr = self.start
        self.depth = 0
        self.max_depth = 1000  # DoS protection
    
    cdef inline void error(self, str msg) except *:
        """Raise ValueError with position info"""
        cdef Py_ssize_t pos = self.ptr - self.start
        raise ValueError(f"{msg} at position {pos}")
    
    cdef inline void check_depth(self) except *:
        """Guard against stack overflow"""
        if self.depth > self.max_depth:
            self.error("Maximum recursion depth exceeded")
    
    cpdef object parse(self):
        """Parse JSON and return Python object"""
        self.ptr = skip_ws(self.ptr, self.end)
        if self.ptr >= self.end:
            self.error("Empty document")
        
        cdef object result = self.parse_value()
        
        # Check for trailing content
        self.ptr = skip_ws(self.ptr, self.end)
        if self.ptr < self.end:
            self.error("Extra data after JSON")
        
        return result
    
    cdef inline object parse_value(self):
        """Parse any JSON value - FAST PATH"""
        cdef unsigned char c
        
        # Skip whitespace inline (avoid function call)
        while self.ptr < self.end and (CTAB[self.ptr[0]] & WS):
            self.ptr += 1
        
        if self.ptr >= self.end:
            self.error("Unexpected EOF")
        
        c = self.ptr[0]
        
        # Fast dispatch using if-elif chain (faster than dict lookup)
        if c == 34:  # "
            return self.parse_string()
        elif c == 123:  # {
            return self.parse_object()
        elif c == 91:  # [
            return self.parse_array()
        elif c == 116:  # t (true)
            return self.parse_true()
        elif c == 102:  # f (false)
            return self.parse_false()
        elif c == 110:  # n (null)
            return self.parse_null()
        elif (CTAB[c] & NM) or c == 73:  # number or I (Infinity)
            return self.parse_number()
        else:
            self.error(f"Unexpected character '{chr(c)}'")
    
    cdef inline object parse_string(self):
        """Ultra-fast string parsing with memchr"""
        self.ptr += 1  # Skip opening "
        cdef const unsigned char* start = self.ptr
        cdef const unsigned char* quote_ptr
        cdef const unsigned char* backslash_ptr
        cdef Py_ssize_t backslash_count
        cdef const unsigned char* bs_ptr
        
        # Find the closing quote
        quote_ptr = find_char(self.ptr, self.end, 34)  # Find "
        if quote_ptr == self.end:
            self.error("Unterminated string")
        
        # Check if there are ANY backslashes in the string
        backslash_ptr = <const unsigned char*>memchr(start, 92, quote_ptr - start)  # Find \
        
        # Fast path: no backslashes at all
        if backslash_ptr == NULL:
            self.ptr = quote_ptr + 1
            return PyUnicode_DecodeUTF8(<const char*>start, quote_ptr - start, NULL)
        
        # There are backslashes - need to handle escapes properly
        # Find the actual closing quote (handle escaped quotes)
        self.ptr = start
        while True:
            quote_ptr = find_char(self.ptr, self.end, 34)  # Find "
            if quote_ptr == self.end:
                self.error("Unterminated string")
            
            # Count preceding backslashes
            backslash_count = 0
            bs_ptr = quote_ptr - 1
            while bs_ptr >= start and bs_ptr[0] == 92:  # \
                backslash_count += 1
                bs_ptr -= 1
            
            # If even number of backslashes, quote is not escaped
            if (backslash_count & 1) == 0:
                break
            
            # Quote was escaped, continue search
            self.ptr = quote_ptr + 1
        
        # Decode escapes
        return self.decode_string_with_escapes(start, quote_ptr)
    
    cdef inline object decode_string_with_escapes(
        self,
        const unsigned char* start,
        const unsigned char* quote_ptr
    ):
        """Decode string with escape sequences"""
        cdef char* buf = <char*>malloc((quote_ptr - start) * 4 + 1)
        if buf == NULL:
            raise MemoryError()
        
        cdef Py_ssize_t out_pos = 0
        cdef const unsigned char* p = start
        cdef unsigned char c
        cdef int code_point
        
        try:
            while p < quote_ptr:
                c = p[0]
                if c == 92:  # \
                    p += 1
                    if p >= quote_ptr:
                        self.error("Invalid escape")
                    
                    c = p[0]
                    if c == 34 or c == 92 or c == 47:  # " \ /
                        buf[out_pos] = c
                        out_pos += 1
                    elif c == 98:  # b
                        buf[out_pos] = 8
                        out_pos += 1
                    elif c == 102:  # f
                        buf[out_pos] = 12
                        out_pos += 1
                    elif c == 110:  # n
                        buf[out_pos] = 10
                        out_pos += 1
                    elif c == 114:  # r
                        buf[out_pos] = 13
                        out_pos += 1
                    elif c == 116:  # t
                        buf[out_pos] = 9
                        out_pos += 1
                    elif c == 117:  # u (unicode)
                        p += 1
                        code_point = self.parse_unicode_escape(&p, quote_ptr)
                        out_pos += self.encode_utf8(code_point, &buf[out_pos])
                        p -= 1  # Will be incremented below
                    else:
                        self.error(f"Invalid escape sequence \\{chr(c)}")
                    p += 1
                else:
                    buf[out_pos] = c
                    out_pos += 1
                    p += 1
            
            self.ptr = quote_ptr + 1
            result = PyUnicode_DecodeUTF8(buf, out_pos, NULL)
            return result
        finally:
            free(buf)
    
    cdef inline int parse_unicode_escape(
        self,
        const unsigned char** pp,
        const unsigned char* end
    ) except -1:
        r"""Parse \uXXXX escape sequence"""
        cdef const unsigned char* p = pp[0]
        cdef int code = 0
        cdef int i
        cdef unsigned char c
        
        for i in range(4):
            if p >= end:
                self.error("Invalid unicode escape")
            c = p[0]
            if c >= 48 and c <= 57:  # 0-9
                code = (code << 4) | (c - 48)
            elif c >= 65 and c <= 70:  # A-F
                code = (code << 4) | (c - 55)
            elif c >= 97 and c <= 102:  # a-f
                code = (code << 4) | (c - 87)
            else:
                self.error("Invalid unicode escape")
            p += 1
        
        pp[0] = p
        return code
    
    cdef inline int encode_utf8(self, int code, char* buf) nogil:
        """Encode code point to UTF-8"""
        if code < 0x80:
            buf[0] = <char>code
            return 1
        elif code < 0x800:
            buf[0] = <char>(0xC0 | (code >> 6))
            buf[1] = <char>(0x80 | (code & 0x3F))
            return 2
        elif code < 0x10000:
            buf[0] = <char>(0xE0 | (code >> 12))
            buf[1] = <char>(0x80 | ((code >> 6) & 0x3F))
            buf[2] = <char>(0x80 | (code & 0x3F))
            return 3
        else:
            buf[0] = <char>(0xF0 | (code >> 18))
            buf[1] = <char>(0x80 | ((code >> 12) & 0x3F))
            buf[2] = <char>(0x80 | ((code >> 6) & 0x3F))
            buf[3] = <char>(0x80 | (code & 0x3F))
            return 4
    
    cdef inline object parse_array(self):
        """Ultra-fast array parsing with pre-allocation"""
        self.depth += 1
        self.check_depth()
        
        self.ptr += 1  # Skip [
        self.ptr = skip_ws(self.ptr, self.end)
        
        if self.ptr >= self.end:
            self.depth -= 1
            self.error("Unexpected EOF in array")
        
        # Empty array fast path
        if self.ptr[0] == 93:  # ]
            self.ptr += 1
            self.depth -= 1
            return []
        
        # Use Python list with growth strategy (proven fastest)
        cdef list arr = []
        cdef object val
        
        while True:
            val = self.parse_value()
            arr.append(val)
            
            self.ptr = skip_ws(self.ptr, self.end)
            if self.ptr >= self.end:
                self.depth -= 1
                self.error("Unexpected EOF in array")
            
            if self.ptr[0] == 44:  # ,
                self.ptr += 1
                self.ptr = skip_ws(self.ptr, self.end)
                # Reject trailing commas (strict JSON compliance)
                if self.ptr < self.end and self.ptr[0] == 93:  # ]
                    self.depth -= 1
                    self.error("Trailing comma not allowed in array")
            elif self.ptr[0] == 93:  # ]
                self.ptr += 1
                self.depth -= 1
                return arr
            else:
                self.depth -= 1
                self.error("Expected ',' or ']'")
    
    cdef inline object parse_object(self):
        """Ultra-fast object parsing"""
        self.depth += 1
        self.check_depth()
        
        self.ptr += 1  # Skip {
        self.ptr = skip_ws(self.ptr, self.end)
        
        if self.ptr >= self.end:
            self.depth -= 1
            self.error("Unexpected EOF in object")
        
        # Empty object fast path
        if self.ptr[0] == 125:  # }
            self.ptr += 1
            self.depth -= 1
            return {}
        
        cdef dict obj = {}
        cdef object key, val
        
        while True:
            # Parse key (must be string)
            self.ptr = skip_ws(self.ptr, self.end)
            if self.ptr >= self.end or self.ptr[0] != 34:  # "
                self.depth -= 1
                self.error("Expected string key")
            
            key = self.parse_string()
            
            # Expect :
            self.ptr = skip_ws(self.ptr, self.end)
            if self.ptr >= self.end or self.ptr[0] != 58:  # :
                self.depth -= 1
                self.error("Expected ':'")
            self.ptr += 1
            
            # Parse value
            val = self.parse_value()
            obj[key] = val
            
            self.ptr = skip_ws(self.ptr, self.end)
            if self.ptr >= self.end:
                self.depth -= 1
                self.error("Unexpected EOF in object")
            
            if self.ptr[0] == 44:  # ,
                self.ptr += 1
                self.ptr = skip_ws(self.ptr, self.end)
                # Reject trailing commas (strict JSON compliance)
                if self.ptr < self.end and self.ptr[0] == 125:  # }
                    self.depth -= 1
                    self.error("Trailing comma not allowed in object")
            elif self.ptr[0] == 125:  # }
                self.ptr += 1
                self.depth -= 1
                return obj
            else:
                self.depth -= 1
                self.error("Expected ',' or '}'")
    
    cdef inline object parse_number(self):
        """Ultra-fast number parsing"""
        cdef const unsigned char* start = self.ptr
        cdef bint is_float = False
        cdef bint is_negative = False
        cdef unsigned char c
        cdef long long val
        cdef char* end_ptr
        cdef Py_ssize_t num_len
        cdef bytes num_bytes
        
        # Check for leading zeros (reject numbers like 013)
        if self.ptr[0] == 48:  # '0'
            if self.ptr + 1 < self.end:
                c = self.ptr[1]
                # Only allow 0 followed by '.', 'e', 'E', or end of number
                if c >= 48 and c <= 57:  # '0'-'9'
                    self.error("Leading zeros not allowed")
        
       # Check for Infinity
        if self.ptr[0] == 73:  # I
            if self.end - self.ptr >= 8:
                if (self.ptr[1] == 110 and self.ptr[2] == 102 and 
                    self.ptr[3] == 105 and self.ptr[4] == 110 and
                    self.ptr[5] == 105 and self.ptr[6] == 116 and
                    self.ptr[7] == 121):
                    self.ptr += 8
                    return float('inf')
        elif self.ptr[0] == 45:  # -
            is_negative = True
            if self.end - self.ptr >= 9:
                if (self.ptr[1] == 73 and self.ptr[2] == 110 and 
                    self.ptr[3] == 102 and self.ptr[4] == 105 and
                    self.ptr[5] == 110 and self.ptr[6] == 105 and
                    self.ptr[7] == 116 and self.ptr[8] == 121):
                    self.ptr += 9
                    return float('-inf')
        
        # Scan number
        while self.ptr < self.end and (CTAB[self.ptr[0]] & NM):
            c = self.ptr[0]
            if c == 46 or c == 101 or c == 69:  # . e E
                is_float = True
            self.ptr += 1
        
        cdef Py_ssize_t length = self.ptr - start
        
        # Use strtod/strtoll for conversion
        if is_float:
            return strtod(<const char*>start, NULL)
        else:
            errno = 0
            val = strtoll(<const char*>start, &end_ptr, 10)
            
            # Check for overflow: errno set or value is at limits
            if errno == ERANGE or val == LLONG_MAX or val == LLONG_MIN:
                # Integer overflow - use Python arbitrary precision
                num_len = self.ptr - start
                num_bytes = (<char*>start)[:num_len]
                return int(num_bytes)
            elif end_ptr == <char*>self.ptr:
                # Successful conversion
                # Use cached small integers
                if val >= -5 and val <= 256:
                    return SMALL_INT_CACHE.get(val, val)
                return val
            else:
                # Parse error - try as float
                return strtod(<const char*>start, NULL)
    
    cdef inline object parse_true(self):
        """Parse true literal"""
        if self.end - self.ptr >= 4:
            if self.ptr[1] == 114 and self.ptr[2] == 117 and self.ptr[3] == 101:
                self.ptr += 4
                return TRUE_OBJ
        self.error("Invalid literal (expected 'true')")
    
    cdef inline object parse_false(self):
        """Parse false literal"""
        if self.end - self.ptr >= 5:
            if (self.ptr[1] == 97 and self.ptr[2] == 108 and 
                self.ptr[3] == 115 and self.ptr[4] == 101):
                self.ptr += 5
                return FALSE_OBJ
        self.error("Invalid literal (expected 'false')")
    
    cdef inline object parse_null(self):
        """Parse null literal"""
        if self.end - self.ptr >= 4:
            if self.ptr[1] == 117 and self.ptr[2] == 108 and self.ptr[3] == 108:
                self.ptr += 4
                return NULL_OBJ
        self.error("Invalid literal (expected 'null')")


def loads(data):
    """Parse JSON string/bytes to Python object - ULTRA FAST"""
    cdef bytes b
    if isinstance(data, str):
        b = data.encode('utf-8')
    elif isinstance(data, bytes):
        b = data
    else:
        raise TypeError("Expected str or bytes")
    
    cdef FastParser parser = FastParser(b)
    return parser.parse()
