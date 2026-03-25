#!/usr/bin/env python3
"""
TRON Format Support for ZSON Benchmarks

TRON (Token Reduced Object Notation) is a class-based format that extends JSON.
It reduces token count by defining schemas (classes) and using positional arguments.

Example:
    JSON: {"name": "Alice", "age": 30}
    TRON: class User: name,age; User("Alice",30)

This module adds TRON encoding/decoding for comprehensive benchmarking.
"""

from typing import Any, Dict, List, Tuple, Set
from collections import Counter
import json


# === TRON Encoding ===

def analyze_object_structures(data: Any, structures: Dict[str, List] = None) -> Dict[str, List]:
    """
    Analyze data to find repeated object structures.
    Returns a dict mapping structure signatures to lists of object instances.
    """
    if structures is None:
        structures = {}
    
    if isinstance(data, dict):
        # Create signature from sorted keys
        if data:
            keys = tuple(sorted(data.keys()))
            sig = ",".join(keys)
            
            if sig not in structures:
                structures[sig] = []
            structures[sig].append(data)
        
        # Recurse into values
        for value in data.values():
            analyze_object_structures(value, structures)
    
    elif isinstance(data, list):
        # Recurse into list items
        for item in data:
            analyze_object_structures(item, structures)
    
    return structures


def should_create_class(num_properties: int, num_occurrences: int) -> bool:
    """
    Determine if a class should be created for an object structure.
    
    Strategy: Create class if:
    - Object has > 1 property AND occurs > 1 time
    
    Alternative strategy (mathematically proven to never use more tokens than JSON):
    - n > (2x + 3) / (2x - 2) where x=properties, n=occurrences
    """
    # Simple strategy (more aggressive)
    return num_properties > 1 and num_occurrences > 1
    
    # Conservative strategy (guaranteed improvement)
    # if num_properties <= 1:
    #     return False
    # threshold = (2 * num_properties + 3) / (2 * num_properties - 2)
    # return num_occurrences > threshold


def generate_class_name(index: int) -> str:
    """
    Generate class name using A-Z, then A1-Z1, A2-Z2, etc.
    
    Examples:
        0 -> A
        25 -> Z
        26 -> A1
        51 -> Z1
        52 -> A2
    """
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    
    if index < 26:
        return alphabet[index]
    else:
        suffix = (index // 26)
        letter_idx = index % 26
        return f"{alphabet[letter_idx]}{suffix}"


def encode_tron_value(value: Any, class_map: Dict[str, str]) -> str:
    """Encode a single value to TRON format"""
    if value is None:
        return "null"
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, (int, float)):
        return json.dumps(value)
    elif isinstance(value, str):
        return json.dumps(value)
    elif isinstance(value, list):
        items = [encode_tron_value(item, class_map) for item in value]
        return "[" + ",".join(items) + "]"
    elif isinstance(value, dict):
        if not value:
            return "{}"
        
        # Check if this object structure has a class
        keys = tuple(sorted(value.keys()))
        sig = ",".join(keys)
        
        if sig in class_map:
            # Use class instantiation
            class_name = class_map[sig]
            # Values in the order defined by the class
            ordered_keys = sig.split(",")
            args = [encode_tron_value(value[k], class_map) for k in ordered_keys]
            return f"{class_name}({','.join(args)})"
        else:
            # Use JSON syntax
            pairs = [f'"{k}":{encode_tron_value(v, class_map)}' for k, v in value.items()]
            return "{" + ",".join(pairs) + "}"
    else:
        return json.dumps(value)


def format_tron(data: Any, compress: bool = True) -> str:
    """
    Encode data to TRON format.
    
    Args:
        data: Python object to encode
        compress: If True, use compact format. If False, add readability spacing.
    
    Returns:
        TRON-formatted string
    """
    # Analyze object structures
    structures = analyze_object_structures(data)
    
    # Determine which structures should get classes
    class_definitions = []
    class_map = {}  # sig -> class_name
    class_index = 0
    
    # Sort by occurrence count (descending) for better token efficiency
    sorted_structures = sorted(
        structures.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )
    
    for sig, instances in sorted_structures:
        keys = sig.split(",")
        num_properties = len(keys)
        num_occurrences = len(instances)
        
        if should_create_class(num_properties, num_occurrences):
            class_name = generate_class_name(class_index)
            class_map[sig] = class_name
            class_index += 1
            
            # Create class definition
            if compress:
                class_def = f"class {class_name}:{sig}"
            else:
                class_def = f"class {class_name}: {sig}"
            
            class_definitions.append(class_def)
    
    # Encode the data
    data_str = encode_tron_value(data, class_map)
    
    # Combine header and data
    if class_definitions:
        if compress:
            header = ";".join(class_definitions)
            return f"{header};{data_str}"
        else:
            header = "\n".join(class_definitions)
            return f"{header}\n\n{data_str}"
    else:
        return data_str


# === TRON Decoding (Basic) ===

def decode_tron(tron_str: str) -> Any:
    """
    Decode TRON format to Python object.
    
    Note: This is a simplified decoder that handles basic TRON.
    For production use, a full parser would be needed.
    
    For now, we'll just validate that it's parseable and return
    the equivalent JSON representation.
    """
    # For benchmarking purposes, we mainly need encoding
    # Decoding can use a proper TRON parser if available
    # For now, just raise NotImplementedError
    raise NotImplementedError(
        "TRON decoding not yet implemented. "
        "Use a proper TRON parser library for decoding."
    )


# === Integration with ZSON Benchmarks ===

def format_tron_compact(data: Any) -> str:
    """Format as TRON (compact/compressed)"""
    return format_tron(data, compress=True)


def format_tron_readable(data: Any) -> str:
    """Format as TRON (readable with spacing)"""
    return format_tron(data, compress=False)


# === Testing and Examples ===

if __name__ == "__main__":
    # Test TRON encoding
    
    print("=" * 80)
    print("TRON Encoding Examples")
    print("=" * 80)
    print()
    
    # Example 1: Simple object (from TRON spec)
    example1 = {
        "index": "ord-123",
        "items": [
            {"index": 1, "name": "Widget", "price": 19.99, "quantity": 2},
            {"index": 2, "name": "Gadget", "price": 29.99, "quantity": 1},
            {"index": 3, "name": "Gizmo", "price": 39.99, "quantity": 1},
        ],
        "total": 109.96
    }
    
    print("Example 1: Order with items")
    print("-" * 40)
    print("JSON:")
    print(json.dumps(example1, indent=2)[:200] + "...")
    print()
    print("TRON (compact):")
    tron1 = format_tron_compact(example1)
    print(tron1)
    print()
    print("TRON (readable):")
    tron1_readable = format_tron_readable(example1)
    print(tron1_readable)
    print()
    
    # Example 2: Employee records
    example2 = {
        "employees": [
            {"id": 1, "name": "Alice", "age": 30},
            {"id": 2, "name": "Bob", "age": 25},
            {"id": 3, "name": "Charlie", "age": 35},
        ]
    }
    
    print("\nExample 2: Employee records")
    print("-" * 40)
    print("JSON:")
    print(json.dumps(example2, indent=2))
    print()
    print("TRON:")
    tron2 = format_tron_compact(example2)
    print(tron2)
    print()
    
    # Token count comparison
    try:
        import tiktoken
        tokenizer = tiktoken.get_encoding("o200k_base")
        
        print("\nToken Comparison:")
        print("-" * 40)
        
        json_str = json.dumps(example1)
        json_tokens = len(tokenizer.encode(json_str))
        tron_tokens = len(tokenizer.encode(tron1))
        savings = json_tokens - tron_tokens
        savings_pct = (savings / json_tokens * 100)
        
        print(f"JSON:  {json_tokens} tokens")
        print(f"TRON:  {tron_tokens} tokens")
        print(f"Savings: {savings} tokens ({savings_pct:.1f}%)")
        
    except ImportError:
        print("\n(Install tiktoken to see token counts)")
    
    print()
    print("=" * 80)
