"""MYSON Zen Grid serializer - converts Python objects to token-efficient MYSON format."""

from __future__ import annotations

import json
from typing import Any


def _is_homogeneous_array(arr: list[Any], threshold: float = 0.7) -> tuple[bool, list[str]]:
    """
    Check if an array of dicts is homogeneous enough to serialize as a table.
    
    Returns:
        (is_homogeneous, common_keys)
    """
    if not arr or not isinstance(arr[0], dict):
        return False, []
    
    # Collect all keys from all objects
    all_keys: set[str] = set()
    for item in arr:
        if not isinstance(item, dict):
            return False, []
        all_keys.update(item.keys())
    
    if not all_keys:
        return False, []
    
    # Count how many objects have each key
    key_counts: dict[str, int] = {key: 0 for key in all_keys}
    for item in arr:
        for key in item.keys():
            key_counts[key] += 1
    
    # Find keys present in >= threshold of objects
    n = len(arr)
    common_keys = [key for key, count in key_counts.items() if count >= n * threshold]
    
    if len(common_keys) >= 2:  # Need at least 2 common keys to benefit
        # Sort for consistent ordering
        return True, sorted(common_keys)
    
    return False, []


def _serialize_value(value: Any) -> str:
    """Serialize a single value to MYSON format."""
    if value is None:
        return "null"
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        # Use JSON string escaping
        return json.dumps(value)
    elif isinstance(value, (list, dict)):
        # Nested structures - use recursive serialization
        return serialize(value)
    else:
        # Fallback to JSON
        return json.dumps(value)


def _serialize_table(arr: list[dict], keys: list[str]) -> str:
    """Serialize homogeneous array as Zen Grid table."""
    lines = []
    
    # Table opener
    lines.append("[:") 
    
    # Header row
    header = ", ".join(keys)
    lines.append(header)
    
    # Data rows (separated by semicolons)
    for obj in arr:
        row_values = []
        for key in keys:
            value = obj.get(key)
            row_values.append(_serialize_value(value))
        lines.append("; " + ", ".join(row_values))
    
    lines.append("]")
    return "\n".join(lines)


def serialize(data: Any, use_tables: bool = True) -> str:
    """
    Serialize Python data to MYSON Zen Grid format.
    
    Args:
        data: Python object to serialize
        use_tables: If True, convert homogeneous arrays to table format
    
    Returns:
        MYSON-formatted string
    """
    if isinstance(data, dict):
        # Serialize as JSON object
        pairs = []
        for key, value in data.items():
            key_str = json.dumps(key) if not key.isalnum() else key
            value_str = serialize(value, use_tables)
            pairs.append(f"{key_str}: {value_str}")
        return "{" + ", ".join(pairs) + "}"
    
    elif isinstance(data, list):
        if use_tables and len(data) >= 2:
            # Check if we can use table format (need at least 2 items for tables to be beneficial)
            is_homog, keys = _is_homogeneous_array(data)
            if is_homog:
                return _serialize_table(data, keys)
        
        # Fall back to JSON array
        items = [serialize(item, use_tables) for item in data]
        return "[" + ", ".join(items) + "]"
    
    else:
        return _serialize_value(data)


def dumps(obj: Any, use_tables: bool = True) -> str:
    """
    Serialize Python object to MYSON string (json.dumps compatible API).
    
    Args:
        obj: Python object to serialize
        use_tables: If True (default), use Zen Grid tables for homogeneous arrays
    
    Returns:
        MYSON-formatted string
    """
    return serialize(obj, use_tables)


def dump(obj: Any, fp, use_tables: bool = True) -> None:
    """
    Serialize Python object to MYSON and write to file (json.dump compatible API).
    
    Args:
        obj: Python object to serialize
        fp: File-like object with write() method
        use_tables: If True (default), use Zen Grid tables for homogeneous arrays
    """
    fp.write(dumps(obj, use_tables))
