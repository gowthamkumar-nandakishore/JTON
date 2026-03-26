#!/usr/bin/env python3
"""
Format converters for benchmarking.
Converts data to: JSON, JSON-compact, YAML, XML, TOON, UOON
"""

import json
from typing import Any, Dict
import sys
from pathlib import Path

# Add src to path for UOON import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def format_json(data: Any, compact: bool = False) -> str:
    """Format as JSON (pretty or compact)"""
    if compact:
        return json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    else:
        return json.dumps(data, indent=2, ensure_ascii=False)


def format_yaml(data: Any) -> str:
    """Format as YAML"""
    try:
        import yaml
    except ImportError:
        print("⚠️  PyYAML not installed. Install with: pip install PyYAML")
        return ""
    
    return yaml.dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )


def format_xml(data: Any, root_name: str = "root") -> str:
    """Format as XML"""
    def dict_to_xml(d: Dict, indent: int = 0) -> str:
        """Convert dictionary to XML"""
        xml_lines = []
        spaces = "  " * indent
        
        for key, value in d.items():
            if isinstance(value, dict):
                xml_lines.append(f"{spaces}<{key}>")
                xml_lines.append(dict_to_xml(value, indent + 1))
                xml_lines.append(f"{spaces}</{key}>")
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        xml_lines.append(f"{spaces}<{key}>")
                        xml_lines.append(dict_to_xml(item, indent + 1))
                        xml_lines.append(f"{spaces}</{key}>")
                    else:
                        xml_lines.append(f"{spaces}<{key}>{escape_xml(item)}</{key}>")
            else:
                xml_lines.append(f"{spaces}<{key}>{escape_xml(value)}</{key}>")
        
        return "\n".join(xml_lines)
    
    def escape_xml(value: Any) -> str:
        """Escape XML special characters"""
        s = str(value)
        s = s.replace("&", "&amp;")
        s = s.replace("<", "&lt;")
        s = s.replace(">", "&gt;")
        s = s.replace('"', "&quot;")
        s = s.replace("'", "&apos;")
        return s
    
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += f"<{root_name}>\n"
    xml += dict_to_xml(data, indent=1)
    xml += f"\n</{root_name}>"
    
    return xml


def format_toon(data: Any) -> str:
    """
    Format as TOON (Token-Oriented Object Notation)
    This is a simplified implementation matching toon-format's style.
    """
    def toon_encode(obj: Any, indent: int = 0) -> str:
        """Encode object to TOON format"""
        spaces = "  " * indent
        
        if isinstance(obj, dict):
            if not obj:
                return "{}"
            
            # Check if this looks like a list of uniform objects (tabular)
            if len(obj) == 1:
                key, value = next(iter(obj.items()))
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    # Tabular format
                    items = value
                    if all(isinstance(item, dict) for item in items):
                        keys = list(items[0].keys())
                        
                        # Header row
                        lines = [f"{spaces}{key}"]
                        header = " | ".join(keys)
                        lines.append(f"{spaces}  {header}")
                        
                        # Data rows
                        for item in items:
                            row = " | ".join(str(item.get(k, "")) for k in keys)
                            lines.append(f"{spaces}  {row}")
                        
                        return "\n".join(lines)
            
            # Regular dict
            lines = ["{"]
            for i, (key, value) in enumerate(obj.items()):
                encoded = toon_encode(value, indent + 1)
                comma = "," if i < len(obj) - 1 else ""
                lines.append(f"{spaces}  {key}: {encoded}{comma}")
            lines.append(f"{spaces}}}")
            return "\n".join(lines)
        
        elif isinstance(obj, list):
            if not obj:
                return "[]"
            
            # Check if all items are dicts with same keys (tabular)
            if all(isinstance(item, dict) for item in obj):
                if obj and all(set(item.keys()) == set(obj[0].keys()) for item in obj):
                    # Tabular list
                    keys = list(obj[0].keys())
                    
                    lines = []
                    # Header
                    header = " | ".join(keys)
                    lines.append(f"{spaces}{header}")
                    
                    # Rows
                    for item in obj:
                        row = " | ".join(str(item.get(k, "")) for k in keys)
                        lines.append(f"{spaces}{row}")
                    
                    return "\n".join(lines)
            
            # Regular list
            lines = ["["]
            for i, item in enumerate(obj):
                encoded = toon_encode(item, indent + 1)
                comma = "," if i < len(obj) - 1 else ""
                lines.append(f"{spaces}  {encoded}{comma}")
            lines.append(f"{spaces}]")
            return "\n".join(lines)
        
        elif isinstance(obj, str):
            # Escape special characters
            escaped = obj.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        
        elif isinstance(obj, bool):
            return "true" if obj else "false"
        
        elif obj is None:
            return "null"
        
        else:
            return str(obj)
    
    return toon_encode(data)


def format_UOON(data: Any) -> str:
    """Format as UOON (Zen Grid format) — uses real Zen Grid serialization."""
    try:
        import uoon
        return uoon.dumps(data, zen_grid=True)
    except ImportError:
        print("❌ UOON not installed. Run: maturin develop --release")
        return ""
    except Exception as e:
        # Fallback to JSON compact if serialization fails
        return json.dumps(data, separators=(',', ':'), ensure_ascii=False)


def format_tron(data: Any) -> str:
    """Format as TRON (Token Reduced Object Notation)"""
    try:
        from format_tron import format_tron_compact
        return format_tron_compact(data)
    except ImportError:
        print("⚠️  TRON formatter not available")
        return ""


def format_orjson(data: Any) -> str:
    """Format as JSON using orjson (fastest JSON library)"""
    try:
        import orjson
        return orjson.dumps(data).decode('utf-8')
    except ImportError:
        # Fallback to stdlib json
        return json.dumps(data, separators=(',', ':'), ensure_ascii=False)


def format_csv(data: Any) -> str:
    """
    Format as CSV (only for flat tabular data)
    Returns empty string if data is not suitable for CSV.
    """
    import csv
    from io import StringIO
    
    # Extract tabular data
    if isinstance(data, dict) and len(data) == 1:
        key, value = next(iter(data.items()))
        if isinstance(value, list) and value and isinstance(value[0], dict):
            rows = value
        else:
            return ""
    elif isinstance(data, list) and data and isinstance(data[0], dict):
        rows = data
    else:
        return ""
    
    # Check if all rows have the same structure
    if not all(isinstance(row, dict) for row in rows):
        return ""
    
    output = StringIO()
    if rows:
        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    return output.getvalue()


# === Formatter Registry ===

FORMATTERS = {
    "json": lambda data: format_json(data, compact=False),
    "json-compact": lambda data: format_json(data, compact=True),
    "orjson": format_orjson,
    "yaml": format_yaml,
    "xml": format_xml,
    "toon": format_toon,
    "tron": format_tron,
    "UOON": format_UOON,
    "csv": format_csv,
}

FORMATTER_DISPLAY_NAMES = {
    "json": "JSON",
    "json-compact": "JSON compact",
    "orjson": "orjson",
    "yaml": "YAML",
    "xml": "XML",
    "toon": "TOON",
    "tron": "TRON",
    "UOON": "UOON",
    "csv": "CSV",
}


def format_data(data: Any, format_name: str) -> str:
    """Format data using the specified formatter"""
    if format_name not in FORMATTERS:
        raise ValueError(
            f"Unknown format: {format_name}. "
            f"Available: {list(FORMATTERS.keys())}"
        )
    
    return FORMATTERS[format_name](data)


if __name__ == "__main__":
    # Test formatters
    test_data = {
        "users": [
            {"id": 1, "name": "Alice", "active": True},
            {"id": 2, "name": "Bob", "active": False},
        ]
    }
    
    print("📝 Format Converter Test\n")
    
    for format_name in ["json", "json-compact", "orjson", "yaml", "xml", "toon", "tron", "csv"]:
        print(f"\n{'='*60}")
        print(f"{FORMATTER_DISPLAY_NAMES[format_name]}:")
        print(f"{'='*60}")
        result = format_data(test_data, format_name)
        if result:
            print(result[:500])  # First 500 chars
            print(f"\n({len(result)} total bytes)")
        else:
            print("(not applicable for this data structure)")
