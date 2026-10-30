
from jsonschema import validate, ValidationError
import pytest


PRODUCT_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["id", "name", "price"],
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string"},
            "price": {"type": "number"}
        }
    }
}


def test_valid_product_response():
    data = [
        {"id": 1, "name": "Laptop", "price": 20000}
    ]

    validate(instance=data, schema=PRODUCT_SCHEMA)


def test_wrong_data_type():
    data = [
        {"id": 1, "name": "Laptop", "price": "Wrong"}
    ]

    with pytest.raises(ValidationError):
        validate(instance=data, schema=PRODUCT_SCHEMA)


def test_missing_required_field():
    data = [
        {"id": 1, "price": 20000}
    ]

    with pytest.raises(ValidationError):
        validate(instance=data, schema=PRODUCT_SCHEMA)


def test_invalid_product_id_type():
    data = [
        {"id": "one", "name": "Laptop", "price": 20000}
    ]

    with pytest.raises(ValidationError):
        validate(instance=data, schema=PRODUCT_SCHEMA)


def test_empty_product_array():
    data = []

    validate(instance=data, schema=PRODUCT_SCHEMA)
