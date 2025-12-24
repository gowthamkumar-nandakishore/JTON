# cython: language_level=3, boundscheck=False, wraparound=False, cdivision=True, initializedcheck=False, infer_types=True
from libc.stdlib cimport malloc, free, strtod, strtoll, strtol
from libc.string cimport memcpy, strncmp, memchr, strlen
from libc.errno cimport errno, ERANGE
from cpython.ref cimport PyObject, Py_INCREF, Py_DECREF
from cpython.exc cimport PyErr_SetString
from cpython.unicode cimport PyUnicode_DecodeUTF8
from cpython.list cimport PyList_New, PyList_Append
from cpython.dict cimport PyDict_New, PyDict_SetItem

cdef extern from "Python.h":
    const char* PyUnicode_AsUTF8AndSize(object o, Py_ssize_t *size) except NULL
    object PyLong_FromString(const char *str, char **pend, int base)
    object PyFloat_FromDouble(double v)
    void PyUnicode_InternInPlace(PyObject **string)
    void PyList_SET_ITEM(object list, Py_ssize_t index, object item)
    Py_ssize_t PyList_GET_SIZE(object list)
    int PyList_SetSlice(object list, Py_ssize_t low, Py_ssize_t high, object itemlist)

# Character classification lookup table (256 bytes for O(1) lookup)
# Inspired by simdjson and msgspec approaches
cdef enum:
    CHAR_WHITESPACE = 0x01
    CHAR_DIGIT = 0x02
    CHAR_DIGIT_OR_SIGN = 0x04  # 0-9, +, -
    CHAR_NUMBER_CHAR = 0x08    # 0-9, +, -, ., e, E
    CHAR_STRUCTURAL = 0x10     # [ ] { } , :
    CHAR_QUOTE = 0x20          # "
    CHAR_ALPHA = 0x40          # a-z, A-Z

# Global lookup table initialized at module load
cdef unsigned char CHAR_TABLE[256]

cdef void init_char_table() nogil:
    """Initialize character classification lookup table"""
    cdef int i
    for i in range(256):
        CHAR_TABLE[i] = 0
    
    # Whitespace
    CHAR_TABLE[<int>b' '] = CHAR_WHITESPACE
    CHAR_TABLE[<int>b'\t'] = CHAR_WHITESPACE
    CHAR_TABLE[<int>b'\n'] = CHAR_WHITESPACE
    CHAR_TABLE[<int>b'\r'] = CHAR_WHITESPACE
    
    # Digits
    for i in range(ord('0'), ord('9') + 1):
        CHAR_TABLE[i] = CHAR_DIGIT | CHAR_DIGIT_OR_SIGN | CHAR_NUMBER_CHAR
    
    # Number characters
    CHAR_TABLE[<int>b'+'] = CHAR_DIGIT_OR_SIGN | CHAR_NUMBER_CHAR
    CHAR_TABLE[<int>b'-'] = CHAR_DIGIT_OR_SIGN | CHAR_NUMBER_CHAR
    CHAR_TABLE[<int>b'.'] = CHAR_NUMBER_CHAR
    CHAR_TABLE[<int>b'e'] = CHAR_NUMBER_CHAR | CHAR_ALPHA
    CHAR_TABLE[<int>b'E'] = CHAR_NUMBER_CHAR | CHAR_ALPHA
    
    # Structural characters
    CHAR_TABLE[<int>b'['] = CHAR_STRUCTURAL
    CHAR_TABLE[<int>b']'] = CHAR_STRUCTURAL
    CHAR_TABLE[<int>b'{'] = CHAR_STRUCTURAL
    CHAR_TABLE[<int>b'}'] = CHAR_STRUCTURAL
    CHAR_TABLE[<int>b','] = CHAR_STRUCTURAL
    CHAR_TABLE[<int>b':'] = CHAR_STRUCTURAL
    
    # Quote
    CHAR_TABLE[<int>b'"'] = CHAR_QUOTE
    
    # Alpha characters
    for i in range(ord('a'), ord('z') + 1):
        CHAR_TABLE[i] |= CHAR_ALPHA
    for i in range(ord('A'), ord('Z') + 1):
        CHAR_TABLE[i] |= CHAR_ALPHA

# Initialize table at module import
init_char_table()

cdef inline int encode_utf8(int code, char* buf) nogil:
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

import sys

# Optimized inline helpers for raw pointer parsing
cdef inline bint is_whitespace(unsigned char c) nogil:
    """Fast whitespace check using lookup table"""
    return (CHAR_TABLE[c] & CHAR_WHITESPACE) != 0

cdef inline bint is_digit(unsigned char c) nogil:
    """Fast digit check using lookup table"""
    return (CHAR_TABLE[c] & CHAR_DIGIT) != 0

cdef inline bint is_number_char(unsigned char c) nogil:
    """Fast number character check using lookup table"""
    return (CHAR_TABLE[c] & CHAR_NUMBER_CHAR) != 0

cdef class Parser:
    cdef const char* buf
    cdef const unsigned char* end_ptr  # T001: Pointer to end of buffer
    cdef Py_ssize_t length
    cdef Py_ssize_t pos
    cdef int recursion_depth
    cdef int max_recursion_depth

    def __cinit__(self, const unsigned char[:] buf):
        # T007: Cast to const unsigned char* for pointer arithmetic compatibility
        self.buf = <const char*>&buf[0]
        self.length = buf.shape[0]
        # T006: Initialize end_ptr to point to end of buffer
        self.end_ptr = <const unsigned char*>&buf[0] + self.length
        self.pos = 0
        self.recursion_depth = 0
        self.max_recursion_depth = 1024

    cdef void skip_whitespace(self):
        cdef const char* b = self.buf
        cdef Py_ssize_t p = self.pos
        cdef Py_ssize_t l = self.length
        cdef char c
        
        while p < l:
            c = b[p]
            if c == b' ':
                p += 1
                continue
            elif c == b'\n' or c == b'\t' or c == b'\r':
                p += 1
                continue
            elif c == b'/':
                # Handle comments
                if p + 1 < l:
                    if b[p+1] == b'/':
                        p += 2
                        while p < l and b[p] != b'\n':
                            p += 1
                    elif b[p+1] == b'*':
                        p += 2
                        while p + 1 < l:
                            if b[p] == b'*' and b[p+1] == b'/':
                                p += 2
                                break
                            p += 1
                    else:
                        break # Just a slash
                else:
                    break
            else:
                break
        self.pos = p

    cdef object parse(self):
        self.skip_whitespace()
        if self.pos == self.length:
             raise ValueError("Empty document")
        val = self.parse_value()
        self.skip_whitespace()
        if self.pos != self.length:
             raise ValueError("Extra data")
        return val

    cdef object parse_value(self):
        if self.recursion_depth >= self.max_recursion_depth:
            raise RecursionError("Maximum recursion depth exceeded")
        
        self.recursion_depth += 1
        cdef char c
        cdef object val
        
        self.skip_whitespace()
        if self.pos >= self.length:
            raise ValueError("Unexpected EOF")
            
        c = self.buf[self.pos]
        
        if c == b'{': val = self.parse_object()
        elif c == b'[': 
            if self.pos + 1 < self.length and self.buf[self.pos+1] == b':':
                val = self.parse_zen_grid()
            else:
                val = self.parse_array()
        elif c == b'"': val = self.parse_string()
        elif c == b't': val = self.parse_true()
        elif c == b'f': val = self.parse_false()
        elif c == b'n': val = self.parse_null()
        elif c == b'I': val = self.parse_infinity()
        elif c == b'N': val = self.parse_nan()
        elif (c >= b'0' and c <= b'9') or c == b'-': val = self.parse_number()
        elif c == b'+': val = self.parse_number()  # +Infinity
        else:
            raise ValueError(f"Unexpected char '{chr(c)}' at position {self.pos}")
        
        self.recursion_depth -= 1
        return val

    cdef object parse_object(self):
        self.pos += 1 # skip {
        cdef dict obj = PyDict_New()
        cdef object key
        cdef object val
        cdef char c
        cdef PyObject* pkey
        
        self.skip_whitespace()
        if self.pos >= self.length: raise ValueError("Unexpected EOF in object")
        if self.buf[self.pos] == b'}':
            self.pos += 1
            return obj

        while True:
            # Parse Key
            self.skip_whitespace()
            if self.pos >= self.length: raise ValueError("Unexpected EOF in object")
            c = self.buf[self.pos]
            
            if c == b'"':
                key = self.parse_string()
            elif (c >= b'a' and c <= b'z') or (c >= b'A' and c <= b'Z'):
                key = self.parse_unquoted_key()
            else:
                raise ValueError(f"Expected string or unquoted key, got '{chr(c)}'")
            
            # Optimized interning
            Py_INCREF(key)
            pkey = <PyObject*>key
            key = None
            PyUnicode_InternInPlace(&pkey)
            key = <object>pkey

            self.skip_whitespace()
            if self.pos >= self.length or self.buf[self.pos] != b':':
                raise ValueError("Expected colon")
            self.pos += 1 # skip :

            # Inline parse_value dispatch for leaf nodes
            self.skip_whitespace()
            if self.pos >= self.length: raise ValueError("Unexpected EOF in object")
            c = self.buf[self.pos]
            
            if c == b'"': val = self.parse_string()
            elif c == b't': val = self.parse_true()
            elif c == b'f': val = self.parse_false()
            elif c == b'n': val = self.parse_null()
            elif (c >= b'0' and c <= b'9') or c == b'-': val = self.parse_number()
            else:
                val = self.parse_value()

            PyDict_SetItem(obj, key, val)

            self.skip_whitespace()
            if self.pos >= self.length: raise ValueError("Unexpected EOF in object")
            c = self.buf[self.pos]
            
            if c == b',':
                self.pos += 1
                # Check for trailing comma
                self.skip_whitespace()
                if self.pos < self.length and self.buf[self.pos] == b'}':
                    self.pos += 1
                    return obj
            elif c == b'}':
                self.pos += 1
                return obj
            else:
                raise ValueError("Expected comma or }")

    cdef Py_ssize_t prescan_array_size(self, Py_ssize_t start_pos) except -1:
        """
        Prescan array to count elements - optimized for speed.
        Simply counts commas at depth 0, ignoring strings.
        """
        cdef const unsigned char* p = <const unsigned char*>&self.buf[start_pos]
        cdef const unsigned char* end = self.end_ptr
        cdef Py_ssize_t count = 1  # Start at 1 (first element)
        cdef int depth = 0
        cdef unsigned char c
        
        # Bounds check
        if p >= end or p[0] != b'[':
            raise ValueError("Expected [")
        p += 1
        
        # Skip initial whitespace and check for empty array
        while p < end and (p[0] == b' ' or p[0] == b'\t' or p[0] == b'\n' or p[0] == b'\r'):
            p += 1
        if p >= end:
            raise ValueError("Unexpected EOF")
        if p[0] == b']':
            return 0
        
        # Fast scan: just track depth and count commas
        # This is much faster than trying to parse everything
        while p < end:
            c = p[0]
            p += 1
            
            if c == b'"':
                # Skip string content quickly - don't care about details
                while p < end and p[0] != b'"':
                    if p[0] == b'\\':
                        p += 1  # Skip escape char
                    p += 1
                if p < end:
                    p += 1  # Skip closing "
            elif c == b'[' or c == b'{':
                depth += 1
            elif c == b']':
                if depth == 0:
                    return count  # Found end of our array
                depth -= 1
            elif c == b'}':
                depth -= 1
            elif c == b',' and depth == 0:
                count += 1
        
        raise ValueError("Unexpected EOF in array")

        
        raise ValueError("Unexpected EOF in array prescan")

    cdef object parse_array(self):
        self.pos += 1 # skip [
        cdef list arr = []
        cdef char c
        cdef object val
        
        self.skip_whitespace()
        if self.pos >= self.length: raise ValueError("Unexpected EOF in array")
        if self.buf[self.pos] == b']':
            self.pos += 1
            return arr

        while True:
            # Inline parse_value dispatch for leaf nodes
            self.skip_whitespace()
            if self.pos >= self.length: raise ValueError("Unexpected EOF in array")
            c = self.buf[self.pos]
            
            if c == b'"': val = self.parse_string()
            elif c == b't': val = self.parse_true()
            elif c == b'f': val = self.parse_false()
            elif c == b'n': val = self.parse_null()
            elif (c >= b'0' and c <= b'9') or c == b'-': val = self.parse_number()
            else:
                val = self.parse_value()

            arr.append(val)  # Python list append is optimized in Cython

            self.skip_whitespace()
            if self.pos >= self.length: raise ValueError("Unexpected EOF in array")
            c = self.buf[self.pos]
            
            if c == b',':
                self.pos += 1
                # Check for trailing comma
                self.skip_whitespace()
                if self.pos < self.length and self.buf[self.pos] == b']':
                    self.pos += 1
                    return arr
            elif c == b']':
                self.pos += 1
                return arr
            else:
                raise ValueError("Expected comma or ]")





    cdef object parse_string(self):
        self.pos += 1 # skip "
        cdef const char* start = self.buf + self.pos
        cdef const char* end
        cdef Py_ssize_t remaining = self.length - self.pos
        cdef bint has_escape = False
        
        # Fast path: find next "
        # We loop to handle escaped quotes
        cdef const char* search_start = start
        cdef Py_ssize_t search_len = remaining
        
        while True:
            end = <const char*>memchr(search_start, b'"', search_len)
            if end == NULL:
                raise ValueError("Unterminated string")
            
            # Check if escaped
            if end > start and (end-1)[0] == b'\\':
                # It might be escaped. But wait, what if it is \\" (escaped backslash, then quote)?
                # We need to count backslashes.
                # This is the slow part of the fast path.
                # For now, let's just assume if we see \, we fall back to slow decode or handle it.
                # Actually, memchr is fast. Let's just check the char before.
                
                # Count backslashes
                bs_count = 0
                ptr = end - 1
                while ptr >= start and ptr[0] == b'\\':
                    bs_count += 1
                    ptr -= 1
                
                if bs_count % 2 == 1:
                    # It is escaped. Continue searching.
                    has_escape = True
                    search_start = end + 1
                    search_len = (self.buf + self.length) - search_start
                    continue
            
            # Found the end
            break
            
        # Check for other escapes if we haven't confirmed any yet
        # We can use memchr to look for \ in the range [start, end)
        if not has_escape:
            if memchr(start, b'\\', end - start) != NULL:
                has_escape = True
        
        cdef Py_ssize_t len = end - start
        self.pos += len + 1 # +1 for closing quote
        
        if not has_escape:
            return PyUnicode_DecodeUTF8(start, len, "strict")
        else:
            return self._decode_string_slow(start, len)

    cdef object _decode_string_slow(self, const char* s, Py_ssize_t length):
        # Allocate buffer for worst case (UTF-8 expansion of escapes is usually smaller or same, except \u which expands to 1-4 bytes)
        # \uXXXX is 6 bytes in source, becomes 1-3 bytes in UTF-8.
        # \uXXXX\uXXXX (surrogate) is 12 bytes, becomes 4 bytes.
        # So length is safe upper bound.
        cdef char* buffer = <char*>malloc(length + 1)
        if buffer == NULL:
            raise MemoryError()
            
        cdef Py_ssize_t i = 0
        cdef Py_ssize_t out_idx = 0
        cdef char c
        cdef char hexbuf[5]
        cdef char low_hex[5]
        cdef long code
        cdef long low
        
        try:
            while i < length:
                c = s[i]
                if c == b'\\':
                    i += 1
                    if i >= length: raise ValueError("Unterminated escape")
                    
                    c = s[i]
                    if c == b'"': buffer[out_idx] = b'"'; out_idx += 1
                    elif c == b'\\': buffer[out_idx] = b'\\'; out_idx += 1
                    elif c == b'/': buffer[out_idx] = b'/'; out_idx += 1
                    elif c == b'b': buffer[out_idx] = b'\b'; out_idx += 1
                    elif c == b'f': buffer[out_idx] = b'\f'; out_idx += 1
                    elif c == b'n': buffer[out_idx] = b'\n'; out_idx += 1
                    elif c == b'r': buffer[out_idx] = b'\r'; out_idx += 1
                    elif c == b't': buffer[out_idx] = b'\t'; out_idx += 1
                    elif c == b'u':
                        if i + 4 >= length: raise ValueError("Incomplete unicode escape")
                        memcpy(hexbuf, s + i + 1, 4)
                        hexbuf[4] = 0
                        code = strtol(hexbuf, NULL, 16)
                        
                        if 0xD800 <= code <= 0xDBFF:
                            if i + 10 < length and s[i+5] == b'\\' and s[i+6] == b'u':
                                memcpy(low_hex, s + i + 7, 4)
                                low_hex[4] = 0
                                low = strtol(low_hex, NULL, 16)
                                if 0xDC00 <= low <= 0xDFFF:
                                    code = 0x10000 + ((code - 0xD800) << 10) + (low - 0xDC00)
                                    i += 6
                        
                        out_idx += encode_utf8(code, buffer + out_idx)
                        i += 4
                    else:
                        raise ValueError(f"Invalid escape \\{chr(c)}")
                else:
                    buffer[out_idx] = c
                    out_idx += 1
                i += 1
                
            return PyUnicode_DecodeUTF8(buffer, out_idx, "strict")
        finally:
            free(buffer)

    cdef object parse_number(self):
        cdef const char* start = self.buf + self.pos
        cdef bint is_float = False
        cdef bint is_negative
        cdef char c
        
        # Handle +/- Infinity
        if self.pos < self.length and (self.buf[self.pos] == b'-' or self.buf[self.pos] == b'+'):
            is_negative = self.buf[self.pos] == b'-'
            if self.length - self.pos >= 9 and strncmp(self.buf + self.pos + 1, "Infinity", 8) == 0:
                self.pos += 9
                return float('-inf') if is_negative else float('inf')
        
        # Scan to end of number
        while self.pos < self.length:
            c = self.buf[self.pos]
            if (c >= b'0' and c <= b'9') or c == b'+' or c == b'-':
                self.pos += 1
            elif c == b'.' or c == b'e' or c == b'E':
                is_float = True
                self.pos += 1
            else:
                break
        
        cdef Py_ssize_t len = (self.buf + self.pos) - start
        cdef char temp[64]
        cdef long long val
        
        # Optimization: avoid copy if not at EOF
        if self.pos < self.length:
            if is_float:
                return strtod(start, NULL)
            else:
                errno = 0
                val = strtoll(start, NULL, 10)
                if errno == 0:
                    return val
                # Fallback on overflow
        
        if len < 64:
            memcpy(temp, start, len)
            temp[len] = 0
            if is_float:
                return strtod(temp, NULL)
            else:
                return PyLong_FromString(temp, NULL, 10)
        
        s = PyUnicode_DecodeUTF8(start, len, "strict")
        if is_float:
            return float(s)
        return int(s)

    cdef object parse_true(self):
        if self.length - self.pos >= 4 and strncmp(self.buf + self.pos, "true", 4) == 0:
            self.pos += 4
            return True
        raise ValueError("Expected true")

    cdef object parse_false(self):
        if self.length - self.pos >= 5 and strncmp(self.buf + self.pos, "false", 5) == 0:
            self.pos += 5
            return False
        raise ValueError("Expected false")

    cdef object parse_null(self):
        if self.length - self.pos >= 4 and strncmp(self.buf + self.pos, "null", 4) == 0:
            self.pos += 4
            return None
        raise ValueError("Expected null")

    cdef object parse_infinity(self):
        # Check for "Infinity"
        if self.length - self.pos >= 8 and strncmp(self.buf + self.pos, "Infinity", 8) == 0:
            self.pos += 8
            return float('inf')
        raise ValueError("Expected Infinity")

    cdef object parse_nan(self):
        # Check for "NaN"
        if self.length - self.pos >= 3 and strncmp(self.buf + self.pos, "NaN", 3) == 0:
            self.pos += 3
            return float('nan')
        raise ValueError("Expected NaN")

    cdef object parse_unquoted_key(self):
        cdef const char* start = self.buf + self.pos
        cdef char c
        while self.pos < self.length:
            c = self.buf[self.pos]
            if (c >= b'a' and c <= b'z') or (c >= b'A' and c <= b'Z') or (c >= b'0' and c <= b'9'):
                self.pos += 1
            else:
                break
        cdef Py_ssize_t len = (self.buf + self.pos) - start
        return PyUnicode_DecodeUTF8(start, len, "strict")

    cdef object parse_zen_grid(self):
        self.pos += 2 # skip [:
        cdef list headers = PyList_New(0)
        cdef list result = PyList_New(0)
        cdef object key
        cdef char c
        
        self.skip_whitespace()
        if self.pos >= self.length: raise ValueError("Unexpected EOF in Zen Grid")
        if self.buf[self.pos] == b']':
            self.pos += 1
            return result

        # Headers
        while True:
            self.skip_whitespace()
            c = self.buf[self.pos]
            if c == b'"':
                key = self.parse_string()
            elif (c >= b'a' and c <= b'z') or (c >= b'A' and c <= b'Z'):
                key = self.parse_unquoted_key()
            else:
                raise ValueError("Expected header")
            
            PyList_Append(headers, key)
            
            self.skip_whitespace()
            c = self.buf[self.pos]
            if c == b',':
                self.pos += 1
            elif c == b';':
                self.pos += 1
                break
            elif c == b']':
                self.pos += 1
                return result
            else:
                raise ValueError("Expected , ; or ]")

        cdef int arity = len(headers)
        cdef dict row
        cdef int col_idx
        
        while True:
            self.skip_whitespace()
            if self.buf[self.pos] == b']':
                self.pos += 1
                break
                
            row = PyDict_New()
            col_idx = 0
            
            while True:
                if col_idx < arity:
                    val = self.parse_value()
                    PyDict_SetItem(row, headers[col_idx], val)
                else:
                    self.parse_value() # Drop
                
                col_idx += 1
                
                self.skip_whitespace()
                c = self.buf[self.pos]
                if c == b',':
                    self.pos += 1
                elif c == b';':
                    self.pos += 1
                    break
                elif c == b']':
                    break
                else:
                    raise ValueError("Expected , ; or ]")
            
            # Fill missing
            while col_idx < arity:
                PyDict_SetItem(row, headers[col_idx], None)
                col_idx += 1
            
            PyList_Append(result, row)
            
            if self.buf[self.pos] == b']':
                self.pos += 1
                break

        return result

def loads(s, **kwargs):
    if isinstance(s, str):
        s = s.encode('utf-8')
    cdef Parser parser = Parser(s)
    return parser.parse()

def dumps(obj, *, skipkeys=False, ensure_ascii=True, check_circular=True, allow_nan=True, cls=None, indent=None, separators=None, default=None, sort_keys=False, zen=False, **kw):
    if zen and isinstance(obj, list) and len(obj) > 0 and isinstance(obj[0], dict):
        try:
            return _dump_zen(obj)
        except Exception:
            pass
            
    import json
    return json.dumps(
        obj,
        skipkeys=skipkeys,
        ensure_ascii=ensure_ascii,
        check_circular=check_circular,
        allow_nan=allow_nan,
        cls=cls,
        indent=indent,
        separators=separators,
        default=default,
        sort_keys=sort_keys,
        **kw
    )

cdef str _dump_zen(list obj):
    if not obj:
        return "[]"
    
    cdef dict first_row = obj[0]
    cdef list headers = list(first_row.keys())
    
    cdef list parts = ["[:"]
    
    # Headers
    parts.append(",".join(headers))
    parts.append(";")
    
    # Rows
    import json
    for row in obj:
        if not isinstance(row, dict):
             raise ValueError("Zen Grid requires list of dicts")
        
        row_vals = []
        for h in headers:
            val = row.get(h)
            if val is None:
                row_vals.append("null")
            else:
                row_vals.append(json.dumps(val))
        
        parts.append(",".join(row_vals))
        parts.append(";")
    
    parts.append("]")
    return "".join(parts)

cdef class MysonModel:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def from_json(cls, data):
        cdef object obj
        if isinstance(data, (str, bytes, bytearray)):
            obj = loads(data)
        else:
            raise TypeError("Expected str, bytes or bytearray")
        
        if not isinstance(obj, dict):
            raise ValueError("Expected JSON object")
            
        annotations = getattr(cls, '__annotations__', {})
        valid_kwargs = {}
        
        for k, v in obj.items():
            if k in annotations:
                valid_kwargs[k] = v
            
        return cls(**valid_kwargs)

    def to_json(self):
        return dumps(self.__dict__)

