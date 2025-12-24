import pytest
from myson import MysonModel

class User(MysonModel):
    id: int
    name: str
    active: bool

def test_model_hydration():
    json_data = '{"id": 1, "name": "Alice", "active": true}'
    user = User.from_json(json_data)
    assert user.id == 1
    assert user.name == "Alice"
    assert user.active is True

def test_extra_fields_ignored():
    json_data = '{"id": 1, "name": "Alice", "active": true, "extra": "value"}'
    user = User.from_json(json_data)
    assert not hasattr(user, "extra")

def test_serialization():
    user = User(id=2, name="Bob", active=False)
    json_str = user.to_json()
    assert '"id": 2' in json_str
    assert '"name": "Bob"' in json_str
    assert '"active": false' in json_str
