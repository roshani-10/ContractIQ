import json
import httpx
from jsonschema import validate
from jsonschema.exceptions import ValidationError


def load_contract():
    with open("contracts/product_api.json", "r") as file:
        return json.load(file)


def get_products():
    response = httpx.get("http://127.0.0.1:8000/products")
    return response


def get_product(product_id):
    response = httpx.get(
        f"http://127.0.0.1:8000/products/{product_id}"
    )
    return response


def validate_products():
    contract = load_contract()
    response = get_products()

    products_schema = {
        "type": "array",
        "items": contract["components"]["schemas"]["Product"]
    }

    try:
        validate(
            instance=response.json(),
            schema=products_schema
        )

        return {
            "status": "PASS",
            "message": "API response matches the contract"
        }

    except ValidationError as error:
        return {
            "status": "FAIL",
            "message": "API response does not match the contract",
            "error": error.message
        }


def validate_product(product_id):
    contract = load_contract()
    response = get_product(product_id)

    product_schema = contract["components"]["schemas"]["Product"]

    try:
        validate(
            instance=response.json(),
            schema=product_schema
        )

        return {
            "status": "PASS",
            "message": f"Product {product_id} matches the contract"
        }

    except ValidationError as error:
        return {
            "status": "FAIL",
            "message": f"Product {product_id} does not match the contract",
            "error": error.message
        }