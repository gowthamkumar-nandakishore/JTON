# Quickstart: MYSON Performance & Compatibility

**Feature**: `002-myson-perf-compat`

## Installation

```bash
pip install myson
```

*Note: Requires a C compiler for installation from source.*

## Drop-in Replacement

Replace `json` with `myson` to instantly boost performance.

```python
import myson as json  # Drop-in replacement!

data = '{"key": "value", "list": [1, 2, 3]}'
obj = json.loads(data)
print(obj)
# Output: {'key': 'value', 'list': [1, 2, 3]}

print(json.dumps(obj))
# Output: {"key":"value","list":[1,2,3]}
```

## Using MysonModel

Define schemas for validation and performance.

```python
from myson import MysonModel

class User(MysonModel):
    id: int
    name: str
    active: bool

# Parse JSON directly into a User object
json_data = '{"id": 123, "name": "Alice", "active": true}'
user = User.from_json(json_data)

print(user.name)  # Alice
print(type(user)) # <class 'User'>

# Serialize back to JSON
print(user.to_json())
# Output: {"id":123,"name":"Alice","active":true}
```

## Benchmarking

Run the included benchmarks to verify performance on your machine.

```bash
python -m myson.benchmarks.throughput
```
