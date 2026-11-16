
# =====================================================
# WEBEOUT — API
# Global Deal Tracker
# =====================================================

import os
import secrets
from typing import Literal

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import database
from price_engine import PriceEngine
from collector import ProductCollector

# =====================================================
# INICIALIZAÇÃO
# =====================================================

database.initialize_database()

engine = PriceEngine()
collector = ProductCollector()

app = FastAPI(
    title="Webeout API",
    description="Global Deal Tracker",
    version="1.3.0"
)

# =====================================================
# CORS
# =====================================================

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

# =====================================================
# MODELO DE REGISTRO DE PREÇOS
# =====================================================

class PriceRegistration(BaseModel):

    product_code: str
    name: str
    category: str = "Other"

    price: float = Field(gt=0)

    currency: Literal["USD", "EUR"]
    market: Literal["US", "DE"]

    store: str = ""

    product_url: str = ""
    affiliate_url: str = ""
    image_url: str = ""

    external_id: str = ""
    catalog_source: str = "API"

# =====================================================
# MODELO DE IMPORTAÇÃO EM LOTE
# =====================================================

class ProductBatch(BaseModel):

    products: list[PriceRegistration] = Field(
        min_length=1,
        max_length=100
    )

# =====================================================
# AUTENTICAÇÃO
# =====================================================

def verify_api_key(x_api_key):

    api_key = os.getenv("INGEST_API_KEY")

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

# =====================================================
# FILTRO DE OFERTAS PÚBLICAS
# =====================================================

def filter_public_offers(offers):

    return [
        offer for offer in offers
        if str(offer.get("catalog_source", "")).strip().upper() != "TEST"
        and str(offer.get("store", "")).strip().lower() not in ("", "unknown store")
        and str(offer.get("name", "")).strip().lower() != "string"
        and str(offer.get("product_code", "")).strip().lower() != "string"
        and offer.get("is_active") in (1, True)
    ]

# =====================================================
# ROTAS PRINCIPAIS
# =====================================================

@app.get("/")
def home():

    return {
        "project": "Webeout",
        "status": "online",
        "version": "1.3.0",
        "message": "Webeout API is running."
    }

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "database": "connected"
    }

# =====================================================
# PRODUTOS
# =====================================================

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

# =====================================================
# OFERTAS
# =====================================================

@app.get("/offers")
def list_offers(
    market: Literal["US", "DE"] | None = None
):

    offers = database.get_offers(market=market)

    return filter_public_offers(offers)

@app.get("/products/{product_code}/offers")
def product_offers(product_code: str):

    product = engine.find_product(product_code)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found."
        )

    offers = database.get_offers(
        product_id=product["id"]
    )

    return filter_public_offers(offers)

# =====================================================
# HISTÓRICO INDIVIDUAL DA OFERTA
# =====================================================

@app.get("/offers/{offer_id}/history")
def offer_history(offer_id: int):

    return engine.get_offer_history(offer_id)

# =====================================================
# ANÁLISE INDIVIDUAL DA OFERTA
# =====================================================

@app.get("/offers/{offer_id}/analysis")
def offer_analysis(offer_id: int):

    return engine.analyze_offer(offer_id)

# =====================================================
# COMPARAÇÃO ENTRE LOJAS
# =====================================================

@app.get("/products/{product_code}/comparison")
def compare_product_offers(product_code: str):

    product = engine.find_product(product_code)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found."
        )

    return engine.compare_offers(product_code)

# =====================================================
# REGISTRO INDIVIDUAL PROTEGIDO
# =====================================================

@app.post("/prices")
def register_price(
    data: PriceRegistration,
    x_api_key: str | None = Header(default=None)
):

    verify_api_key(x_api_key)

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
            image_url=data.image_url,
            affiliate_url=data.affiliate_url,
            external_id=data.external_id,
            catalog_source=data.catalog_source
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

# =====================================================
# IMPORTAÇÃO AUTOMÁTICA EM LOTE
# =====================================================

@app.post("/collector/import")
def import_product_batch(
    batch: ProductBatch,
    x_api_key: str | None = Header(default=None)
):

    verify_api_key(x_api_key)

    try:

        products = [
            product.model_dump()
            for product in batch.products
        ]

        result = collector.import_products(products)

        return {
            "success": result["failed"] == 0,
            "message": "Product batch processed.",
            "total": result["total"],
            "successful": result["successful"],
            "failed": result["failed"],
            "results": result["results"]
        }

    except (ValueError, TypeError, KeyError) as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )