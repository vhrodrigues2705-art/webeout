
import os
import secrets
from typing import Literal

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import database
from price_engine import PriceEngine


# Banco de dados e motor de preços
database.initialize_database()
engine = PriceEngine()


app = FastAPI(
    title="Webeout API",
    description="Global Deal Tracker",
    version="1.1.0"
)


# Origens autorizadas a acessar a API
default_origins = [
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:5501",
    "http://127.0.0.1:5501"
]

configured_origins = os.getenv("CORS_ORIGINS", "")

allowed_origins = default_origins + [
    origin.strip()
    for origin in configured_origins.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"]
)


class PriceRegistration(BaseModel):
    product_code: str
    name: str
    category: str
    price: float = Field(gt=0)
    currency: Literal["USD", "EUR"]
    market: Literal["US", "DE"]
    store: str = ""
    product_url: str = ""
    image_url: str = ""


@app.get("/")
def home():
    return {
        "project": "Webeout",
        "status": "online",
        "message": "Webeout API is running."
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/products")
def list_products(
    market: Literal["US", "DE"] | None = None
):
    return database.get_products(market)


@app.get("/products/{product_code}/history")
def product_history(product_code: str):
    product = engine.find_product(product_code)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found."
        )

    return engine.get_history(product_code)


@app.get("/products/{product_code}/analysis")
def product_analysis(product_code: str):
    product = engine.find_product(product_code)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found."
        )

    return engine.analyze_price(product_code)


@app.post("/prices")
def register_price(
    data: PriceRegistration,
    x_api_key: str | None = Header(default=None)
):
    api_key = os.getenv("INGEST_API_KEY")

    # Não permite cadastro público sem uma chave configurada
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Price registration is not configured."
        )

    if not x_api_key or not secrets.compare_digest(
        x_api_key,
        api_key
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key."
        )

    try:
        result = engine.register_price(
            product_code=data.product_code,
            name=data.name,
            category=data.category,
            price=data.price,
            currency=data.currency,
            market=data.market,
            store=data.store,
            product_url=data.product_url,
            image_url=data.image_url
        )

        return {
            "success": True,
            "message": "Price registered successfully.",
            "data": result
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )
