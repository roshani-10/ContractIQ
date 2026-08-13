from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Product(BaseModel):
    name: str
    price: float


@app.get("/")
def home():
    return {"message": "ContractIQ is running!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/products")
def get_products():
            return [
        {
            "id":1,
            "name": "Laptop",
            "price": 20000
        },
        {
            "id": 2,
            "name": "Keyboard",
            "price": 2500
        },
        {
            "id": 3,
            "name": "Mouse",
            "price": 1200
        }
 ]



@app.post("/products")
def create_product(product: Product):
    return {
        "message": "Product received",
        "product": product
    }