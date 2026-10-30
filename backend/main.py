
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jsonschema import validate, ValidationError
import httpx

from backend.validator import validate_products, validate_product
from backend.database import (
    init_db,
    save_validation,
    get_history,
    clear_history,
)

app = FastAPI(title="ContractIQ")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


class Product(BaseModel):
    name: str
    price: float


class ValidationRequest(BaseModel):
    endpoint: str
    method: str = "GET"
    contract: dict
    scenario: str = "valid"


def record_result(endpoint, method, status, message):
    try:
        save_validation(endpoint, method, status, message)
    except Exception as error:
        print(f"Could not save validation history: {error}")


@app.get("/")
def home():
    return {"message": "ContractIQ is running!"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/products")
def get_products():
    return [
        {"id": 1, "name": "Laptop", "price": 20000},
        {"id": 2, "name": "Keyboard", "price": 2500},
        {"id": 3, "name": "Mouse", "price": 1200},
    ]


@app.post("/products")
def create_product(product: Product):
    return {"message": "Product received", "product": product}


@app.get("/products/{product_id}")
def get_product(product_id: int):
    products = get_products()
    for product in products:
        if product["id"] == product_id:
            return product
    return {"message": "Product not found"}


@app.put("/products/{product_id}")
def update_product(product_id: int, product: Product):
    if product_id in [1, 2, 3]:
        return {
            "id": product_id,
            "name": product.name,
            "price": product.price,
        }
    return {"message": "Product not found"}


@app.delete("/products/{product_id}")
def delete_product(product_id: int):
    if product_id in [1, 2, 3]:
        return {
            "message": "Product deleted",
            "product_id": product_id,
        }
    return {"message": "Product not found"}


@app.get("/validate/products")
def validate_all_products():
    return validate_products()


@app.get("/validate/products/{product_id}")
def validate_single_product(product_id: int):
    return validate_product(product_id)


@app.get("/validate")
def validate_api():
    return {
        "project": "ContractIQ",
        "message": "API Contract Validation",
        "endpoints": {
            "all_products": "/validate/products",
            "single_product": "/validate/products/{product_id}",
        },
    }


@app.post("/validate/run")
async def run_validation(request: ValidationRequest):
    method = request.method.upper()

    if method not in ["GET", "POST", "PUT", "DELETE"]:
        result = {
            "status": "FAIL",
            "message": "Unsupported HTTP method",
            "error": method,
        }
        record_result(
            request.endpoint, method, "FAIL", result["message"]
        )
        return result

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.request(method, request.endpoint)

        if not response.is_success:
            result = {
                "status": "FAIL",
                "message": "API returned an unsuccessful HTTP status",
                "error": f"HTTP {response.status_code}",
            }
            record_result(
                request.endpoint, method, "FAIL", result["message"]
            )
            return result

        data = response.json()

        if request.scenario == "wrong_type":
            target = data[0] if isinstance(data, list) and data else data
            if isinstance(target, dict) and "price" in target:
                target["price"] = "Wrong"

        elif request.scenario == "missing_field":
            target = data[0] if isinstance(data, list) and data else data
            if isinstance(target, dict):
                target.pop("name", None)

        elif request.scenario == "bad_status":
            result = {
                "status": "FAIL",
                "message": "Simulated HTTP status failure",
                "error": "Demo scenario: simulated HTTP 500",
            }
            record_result(
                request.endpoint, method, "FAIL", result["message"]
            )
            return result

        validate(instance=data, schema=request.contract)

        result = {
            "status": "PASS",
            "message": "API response matches the contract",
            "http_status": response.status_code,
        }
        record_result(
            request.endpoint, method, "PASS", result["message"]
        )
        return result

    except ValidationError as error:
        result = {
            "status": "FAIL",
            "message": "API response does not match the contract",
            "error": error.message,
        }
        record_result(
            request.endpoint, method, "FAIL", result["message"]
        )
        return result

    except httpx.RequestError as error:
        result = {
            "status": "FAIL",
            "message": "Could not reach the target API",
            "error": str(error),
        }
        record_result(
            request.endpoint, method, "FAIL", result["message"]
        )
        return result

    except ValueError as error:
        result = {
            "status": "FAIL",
            "message": "API did not return valid JSON",
            "error": str(error),
        }
        record_result(
            request.endpoint, method, "FAIL", result["message"]
        )
        return result

    except Exception as error:
        result = {
            "status": "FAIL",
            "message": "Validation could not be completed",
            "error": str(error),
        }
        record_result(
            request.endpoint, method, "FAIL", result["message"]
        )
        return result


@app.get("/history")
def validation_history():
    return get_history()


@app.delete("/history")
def delete_validation_history():
    clear_history()
    return {"message": "Validation history cleared"}
