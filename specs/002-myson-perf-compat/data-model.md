# Data Model: MysonModel

**Feature**: `002-myson-perf-compat`

## Overview

`MysonModel` is a base class for defining data schemas. It is designed to be a high-performance, zero-copy (where possible) alternative to `pydantic.BaseModel` and `msgspec.Struct`.

## Class Definition

```python
class MysonModel:
    """
    Base class for MYSON data models.
    Subclasses define fields using Python type hints.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize the model with keyword arguments matching the field names.
        """
        ...

    @classmethod
    def from_json(cls, data: str | bytes) -> "MysonModel":
        """
        Parse JSON data directly into an instance of this model.
        """
        ...

    def to_json(self) -> str:
        """
        Serialize the model instance to a JSON string.
        """
        ...
        
    def to_dict(self) -> dict:
        """
        Convert the model instance to a Python dictionary.
        """
        ...
```

## Type Support

`MysonModel` supports the following types:

- `int` (arbitrary precision)
- `float`
- `bool`
- `str`
- `bytes` (base64 encoded in JSON)
- `datetime` (ISO 8601)
- `date` (ISO 8601)
- `uuid.UUID` (hex string)
- `list[T]`
- `dict[K, V]`
- `Optional[T]`
- Nested `MysonModel` subclasses

## Zero-Copy Semantics

- **Bytes**: When parsing from `bytes` input, `bytes` fields in the model MAY point directly to the input buffer if the input object is kept alive.
- **Strings**: Standard Python strings are allocated, but decoding is optimized.

## Validation

Validation happens at parse time.
- **Extra Fields**: Fields present in the JSON but not in the schema are silently ignored.
- **Type Mismatch**: If the input JSON does not match the schema (e.g., wrong type, missing required field), a `ValidationError` (or `MysonError`) is raised.

