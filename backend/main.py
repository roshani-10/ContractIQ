
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jsonschema import Draft7Validator, ValidationError
import httpx
import time

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


def record_result(
    endpoint,
    method,
    status,
    message,
    http_status=None,
    response_time_ms=None
):
    try:
        save_validation(
            endpoint,
            method,
            status,
            message,
            http_status,
            response_time_ms
        )
    except Exception as error:
        print(f"Could not save validation history: {error}")


def get_actual_type(value):
    if isinstance(value, bool):
        return "boolean"
    elif isinstance(value, str):
        return "string"
    elif isinstance(value, int):
        return "integer"
    elif isinstance(value, float):
        return "number"
    elif isinstance(value, list):
        return "array"
    elif isinstance(value, dict):
        return "object"
    elif value is None:
        return "null"

    return type(value).__name__


def build_error_details(error):
    field_path = ".".join(str(part) for part in error.path)

    # Handle missing required fields
    if (
        error.validator == "required"
        and isinstance(error.instance, dict)
    ):
        missing_fields = [
            field
            for field in error.validator_value
            if field not in error.instance
        ]

        return [
            {
                "field": (
                    f"{field_path}.{field}"
                    if field_path
                    else field
                ),
                "expected": "Required field",
                "received": "Missing",
                "actual_value": None,
                "message": f"Required field '{field}' is missing",
            }
            for field in missing_fields
        ]

    # Handle incorrect data types and other schema violations
    return [
        {
            "field": field_path or "$",
            "expected": error.validator_value,
            "received": get_actual_type(error.instance),
            "actual_value": error.instance,
            "message": error.message,
        }
    ]


# FEATURE 1: Automatically infer JSON Schema from sample data
def infer_schema(data):

    if isinstance(data, dict):
        return {
            "type": "object",
            "properties": {
                key: infer_schema(value)
                for key, value in data.items()
            },
            "required": list(data.keys()),
        }

    if isinstance(data, list):
        return {
            "type": "array",
            "items": infer_schema(data[0]) if data else {},
        }

    # Boolean must be checked before integer
    if isinstance(data, bool):
        return {"type": "boolean"}

    if isinstance(data, int):
        return {"type": "integer"}

    if isinstance(data, float):
        return {"type": "number"}

    if data is None:
        return {"type": "null"}

    if isinstance(data, str):
        return {"type": "string"}

    return {}


# FEATURE 2: Explain contract errors in plain English
def explain_validation_error(error):

    field = ".".join(str(part) for part in error.path) or "response"
    validator = error.validator

    if validator == "type":
        expected = error.validator_value
        received = get_actual_type(error.instance)

        return (
            f"'{field}' has the wrong data type. "
            f"Expected {expected}, but received {received}. "
            "Check how the API sends this field."
        )

    if validator == "required":
        if isinstance(error.instance, dict):
            missing_fields = [
                name
                for name in error.validator_value
                if name not in error.instance
            ]

            if missing_fields:
                missing = ", ".join(missing_fields)
                return (
                    f"Required field '{missing}' is missing. "
                    "The API may have removed or renamed this field. "
                    "Restore the required field in the API response."
                )

    return f"'{field}': {error.message}"


# Diagnose HTTP client and server errors
def explain_http_status(status_code):

    if 400 <= status_code < 500:
        return (
            f"Client-side problem (HTTP {status_code}). "
            "Check the request URL, parameters, authentication, "
            "and request data."
        )

    if 500 <= status_code < 600:
        return (
            f"Server-side failure (HTTP {status_code}). "
            "The target API encountered an error. "
            "Check the server logs and backend implementation."
        )

    return f"The API returned HTTP status {status_code}."


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
    return {
        "message": "Product received",
        "product": product,
    }


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


# FEATURE 1: Generate a contract from a live API response
@app.post("/generate-schema")
async def generate_schema(url: str):

    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid HTTP or HTTPS endpoint URL."
        )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)

        if not response.is_success:
            raise HTTPException(
                status_code=response.status_code,
                detail=(
                    "Could not fetch sample response. "
                    f"Target API returned HTTP {response.status_code}."
                )
            )

        try:
            data = response.json()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="The endpoint did not return valid JSON."
            )

        schema = infer_schema(data)

        return {
            "message": "JSON Schema generated successfully",
            "source_url": url,
            "schema": schema,
        }

    except HTTPException:
        raise

    except httpx.RequestError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Could not connect to the endpoint: {str(error)}"
        )


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
            request.endpoint,
            method,
            "FAIL",
            result["message"]
        )

        return result

    response = None
    response_time_ms = None
    http_status = None

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            start_time = time.perf_counter()

            response = await client.request(
                method,
                request.endpoint
            )

            end_time = time.perf_counter()

        response_time_ms = round(
            (end_time - start_time) * 1000, 2
        )

        http_status = response.status_code

        # Diagnose unsuccessful HTTP responses
        if not response.is_success:

            diagnosis = explain_http_status(http_status)

            result = {
                "status": "FAIL",
                "message": "API returned an unsuccessful HTTP status",
                "error": f"HTTP {http_status}",
                "diagnosis": diagnosis,
                "http_status": http_status,
                "response_time_ms": response_time_ms,
            }

            record_result(
                request.endpoint,
                method,
                "FAIL",
                diagnosis,
                http_status,
                response_time_ms,
            )

            return result

        data = response.json()

        # Demonstration scenario: incorrect data type
        if request.scenario == "wrong_type":

            target = (
                data[0]
                if isinstance(data, list) and data
                else data
            )

            if isinstance(target, dict) and "price" in target:
                target["price"] = "Wrong"

        # Demonstration scenario: missing required field
        elif request.scenario == "missing_field":

            target = (
                data[0]
                if isinstance(data, list) and data
                else data
            )

            if isinstance(target, dict):
                target.pop("name", None)

        # Demonstration scenario: simulated HTTP failure
        elif request.scenario == "bad_status":

            diagnosis = (
                "Server-side failure (simulated HTTP 500). "
                "Check the target API server and its backend implementation."
            )

            result = {
                "status": "FAIL",
                "message": "Simulated HTTP status failure",
                "error": "Demo scenario: simulated HTTP 500",
                "diagnosis": diagnosis,
                "http_status": 500,
                "actual_http_status": http_status,
                "response_time_ms": response_time_ms,
            }

            record_result(
                request.endpoint,
                method,
                "FAIL",
                diagnosis,
                500,
                response_time_ms,
            )

            return result

        # Validate the API response and collect all violations
        validator = Draft7Validator(request.contract)
        validation_errors = list(validator.iter_errors(data))

        if validation_errors:

            error_details = []
            explanations = []

            for validation_error in validation_errors:
                error_details.extend(
                    build_error_details(validation_error)
                )

                explanations.append(
                    explain_validation_error(validation_error)
                )

            diagnosis = explanations[0]

            result = {
                "status": "FAIL",
                "message": "API response does not match the contract",
                "error": validation_errors[0].message,
                "errors": error_details,
                "explanations": explanations,
                "diagnosis": diagnosis,
                "http_status": http_status,
                "response_time_ms": response_time_ms,
            }

            record_result(
                request.endpoint,
                method,
                "FAIL",
                diagnosis,
                http_status,
                response_time_ms,
            )

            return result

        # Successful validation
        result = {
            "status": "PASS",
            "message": "API response matches the contract",
            "http_status": http_status,
            "response_time_ms": response_time_ms,
        }

        record_result(
            request.endpoint,
            method,
            "PASS",
            result["message"],
            http_status,
            response_time_ms,
        )

        return result

    except ValidationError as error:

        result = {
            "status": "FAIL",
            "message": "Invalid JSON Schema contract",
            "error": error.message,
            "http_status": http_status,
            "response_time_ms": response_time_ms,
        }

        record_result(
            request.endpoint,
            method,
            "FAIL",
            result["message"],
            http_status,
            response_time_ms,
        )

        return result

    except httpx.RequestError as error:

        result = {
            "status": "FAIL",
            "message": "Could not reach the target API",
            "error": str(error),
            "response_time_ms": response_time_ms,
        }

        record_result(
            request.endpoint,
            method,
            "FAIL",
            result["message"],
            http_status,
            response_time_ms,
        )

        return result

    except ValueError as error:

        result = {
            "status": "FAIL",
            "message": "API did not return valid JSON",
            "error": str(error),
            "http_status": http_status,
            "response_time_ms": response_time_ms,
        }

        record_result(
            request.endpoint,
            method,
            "FAIL",
            result["message"],
            http_status,
            response_time_ms,
        )

        return result

    except Exception as error:

        result = {
            "status": "FAIL",
            "message": "Validation could not be completed",
            "error": str(error),
            "http_status": http_status,
            "response_time_ms": response_time_ms,
        }

        record_result(
            request.endpoint,
            method,
            "FAIL",
            result["message"],
            http_status,
            response_time_ms,
        )

        return result


@app.get("/history")
def validation_history():
    return get_history()


@app.delete("/history")
def delete_validation_history():
    clear_history()
    return {"message": "Validation history cleared"}
