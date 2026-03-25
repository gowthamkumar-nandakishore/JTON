#!/usr/bin/env python3
"""
Comprehensive dataset generators for benchmarking.
Inspired by toon-format's benchmark datasets.
"""

from typing import Any, Dict, List
import random
from datetime import datetime, timedelta


# === Dataset Configuration ===

DATASET_ICONS = {
    'employees': '👥',
    'analytics': '📈',
    'orders': '🛒',
    'github': '⭐',
    'events': '🧾',
    'config': '🧩',
}


# === Data Generators ===

def generate_employees(count: int = 2000) -> Dict[str, List]:
    """
    Uniform employee records (100% tabular structure)
    Matches toon-format's employee dataset pattern.
    """
    departments = ["Engineering", "Sales", "Marketing", "HR", "Finance", "Operations"]
    
    return {
        "employees": [
            {
                "id": i,
                "name": f"Employee{i:04d}",
                "email": f"emp{i}@company.com",
                "department": departments[i % len(departments)],
                "salary": 50000 + (i * 500) % 100000,
                "active": i % 3 != 0,
                "hireDate": f"20{15 + (i % 10)}-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
                "manager": f"MGR{(i // 10):04d}" if i % 10 != 0 else None,
            }
            for i in range(1, count + 1)
        ]
    }


def generate_analytics_data(days: int = 365) -> Dict[str, List]:
    """
    Time-series analytics data (100% tabular structure)
    Matches toon-format's analytics dataset pattern.
    """
    start_date = datetime(2025, 1, 1)
    
    return {
        "metrics": [
            {
                "date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"),
                "views": random.randint(5000, 10000),
                "clicks": random.randint(200, 500),
                "conversions": random.randint(20, 50),
                "revenue": round(random.uniform(3000, 10000), 2),
                "bounceRate": round(random.uniform(0.3, 0.6), 2),
            }
            for i in range(days)
        ]
    }


def generate_orders(count: int = 500) -> Dict[str, List]:
    """
    E-commerce orders with nested structures (mixed structure)
    Matches toon-format's order dataset pattern.
    """
    products = [
        ("Widget Pro", 29.99),
        ("Gadget Ultra", 49.99),
        ("Tool Master", 19.99),
        ("Device Premium", 79.99),
        ("Kit Deluxe", 99.99),
    ]
    
    return {
        "orders": [
            {
                "orderId": f"ORD{i:06d}",
                "customerId": f"CUST{(i * 3) % 1000:04d}",
                "orderDate": f"2025-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
                "status": ["pending", "shipped", "delivered", "cancelled"][i % 4],
                "items": [
                    {
                        "productName": products[j % len(products)][0],
                        "quantity": (i + j) % 5 + 1,
                        "price": products[j % len(products)][1],
                    }
                    for j in range((i % 3) + 1)
                ],
                "shipping": {
                    "address": f"{i * 10} Main St",
                    "city": ["New York", "Los Angeles", "Chicago", "Houston"][i % 4],
                    "zipCode": f"{10000 + i:05d}",
                },
                "total": round(sum(
                    products[j % len(products)][1] * ((i + j) % 5 + 1)
                    for j in range((i % 3) + 1)
                ), 2),
            }
            for i in range(1, count + 1)
        ]
    }


def generate_github_repos(count: int = 100) -> Dict[str, List]:
    """
    GitHub repository data (semi-structured)
    Matches toon-format's github dataset pattern.
    """
    return {
        "repositories": [
            {
                "id": 28457823 + i * 1000,
                "name": f"repo-{i}",
                "repo": f"org{i % 20}/repo-{i}",
                "description": f"Repository {i} with various features and capabilities...",
                "createdAt": f"20{14 + i % 11}-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}T{i % 24:02d}:00:00Z",
                "updatedAt": f"2025-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}T{i % 24:02d}:00:00Z",
                "pushedAt": f"2025-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}T{(i + 1) % 24:02d}:00:00Z",
                "stars": 100000 - i * 500,
                "watchers": 8000 - i * 50,
                "forks": 40000 - i * 200,
                "defaultBranch": "main" if i % 2 == 0 else "master",
                "language": ["JavaScript", "Python", "TypeScript", "Java", "Go"][i % 5],
                "license": ["MIT", "Apache-2.0", "GPL-3.0", "BSD-3-Clause"][i % 4] if i % 3 != 0 else None,
            }
            for i in range(count)
        ]
    }


def generate_event_logs(count: int = 300) -> Dict[str, List]:
    """
    Semi-uniform event logs (mixed structure)
    Matches toon-format's event log pattern.
    """
    event_types = ["login", "logout", "purchase", "view", "error"]
    
    events = []
    for i in range(count):
        event = {
            "timestamp": f"2025-01-{(i % 30) + 1:02d}T{i % 24:02d}:{i % 60:02d}:00Z",
            "eventType": event_types[i % len(event_types)],
            "userId": f"USER{i % 100:04d}",
        }
        
        # Add type-specific fields (semi-uniform structure)
        if event["eventType"] == "purchase":
            event["amount"] = round(random.uniform(10, 1000), 2)
            event["itemId"] = f"ITEM{i % 50:03d}"
        elif event["eventType"] == "error":
            event["errorCode"] = f"ERR{i % 10:03d}"
            event["errorMessage"] = f"Error occurred in module {i % 5}"
        elif event["eventType"] == "view":
            event["pageUrl"] = f"/page{i % 20}"
            event["duration"] = random.randint(5, 300)
        
        events.append(event)
    
    return {"events": events}


def generate_nested_config() -> Dict[str, Any]:
    """
    Deeply nested configuration (0% tabular)
    Matches toon-format's config pattern.
    """
    return {
        "application": {
            "name": "MyApp",
            "version": "1.0.0",
            "server": {
                "host": "localhost",
                "port": 8080,
                "ssl": {
                    "enabled": True,
                    "certificate": "/etc/ssl/cert.pem",
                    "key": "/etc/ssl/key.pem",
                    "protocols": ["TLSv1.2", "TLSv1.3"],
                },
                "cors": {
                    "enabled": True,
                    "origins": ["https://example.com", "https://app.example.com"],
                    "methods": ["GET", "POST", "PUT", "DELETE"],
                    "maxAge": 3600,
                },
            },
            "database": {
                "primary": {
                    "host": "db.example.com",
                    "port": 5432,
                    "name": "myapp_prod",
                    "pool": {
                        "min": 2,
                        "max": 10,
                        "timeout": 30000,
                    },
                },
                "replica": {
                    "host": "db-replica.example.com",
                    "port": 5432,
                    "name": "myapp_prod",
                    "readOnly": True,
                },
            },
            "cache": {
                "redis": {
                    "host": "redis.example.com",
                    "port": 6379,
                    "db": 0,
                    "ttl": 3600,
                },
            },
            "features": {
                "authentication": True,
                "analytics": True,
                "notifications": {
                    "email": True,
                    "push": False,
                    "sms": True,
                },
            },
        }
    }


# === Dataset Catalog ===

DATASETS = {
    "employees": {
        "description": "Uniform employee records",
        "icon": "👥",
        "generator": lambda: generate_employees(2000),
        "tabular_percent": 100,
        "track": "flat",
    },
    "analytics": {
        "description": "Time-series analytics data",
        "icon": "📈",
        "generator": lambda: generate_analytics_data(365),
        "tabular_percent": 100,
        "track": "flat",
    },
    "github": {
        "description": "Top 100 GitHub repositories",
        "icon": "⭐",
        "generator": lambda: generate_github_repos(100),
        "tabular_percent": 100,
        "track": "flat",
    },
    "orders": {
        "description": "E-commerce orders with nested structures",
        "icon": "🛒",
        "generator": lambda: generate_orders(500),
        "tabular_percent": 60,
        "track": "mixed",
    },
    "events": {
        "description": "Semi-uniform event logs",
        "icon": "🧾",
        "generator": lambda: generate_event_logs(300),
        "tabular_percent": 40,
        "track": "mixed",
    },
    "config": {
        "description": "Deeply nested configuration",
        "icon": "🧩",
        "generator": generate_nested_config,
        "tabular_percent": 0,
        "track": "mixed",
    },
}


def get_dataset(name: str) -> Dict[str, Any]:
    """Get a dataset by name"""
    if name not in DATASETS:
        raise ValueError(f"Unknown dataset: {name}. Available: {list(DATASETS.keys())}")
    
    return DATASETS[name]["generator"]()


if __name__ == "__main__":
    import json
    
    print("📊 ZSON Benchmark Datasets\n")
    print("Available datasets:")
    for name, info in DATASETS.items():
        print(f"  {info['icon']} {name:12s} - {info['description']}")
        print(f"     Tabular: {info['tabular_percent']}% | Track: {info['track']}")
    
    # Generate and save sample datasets
    print("\n🔨 Generating sample datasets...")
    for name in DATASETS:
        data = get_dataset(name)
        size = len(json.dumps(data))
        print(f"  ✓ {name}: {size:,} bytes")
