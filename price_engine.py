
# =====================================================
# WEBEOUT — PRICE ENGINE
# Product analysis + Independent offer analysis
# =====================================================

import math

from datetime import datetime, timezone
from statistics import mean

import database


class PriceEngine:

    def __init__(self):
        database.initialize_database()

    # =================================================
    # LOCALIZAR PRODUTO
    # =================================================

    def find_product(self, product_code):

        products = database.get_products()

        for product in products:
            if product["product_code"] == product_code:
                return product

        return None

    # =================================================
    # REGISTRAR PREÇO E CRIAR/ATUALIZAR OFERTA
    # =================================================

    def register_price(
        self,
        product_code,
        name,
        category,
        price,
        currency,
        market,
        store="",
        product_url="",
        image_url="",
        affiliate_url=None,
        external_id=None,
        catalog_source=None
    ):

        price = float(price)

        if not math.isfinite(price) or price <= 0:
            raise ValueError("Price must be greater than zero.")

        if not product_code or not name:
            raise ValueError("Product code and name are required.")

        if market not in ("US", "DE"):
            raise ValueError("Unsupported market.")

        expected_currency = {
            "US": "USD",
            "DE": "EUR"
        }[market]

        if currency != expected_currency:
            raise ValueError("Currency does not match market.")

        store = str(store or "Unknown").strip()

        # Cadastra ou atualiza o produto.
        product_id = database.add_product(
            product_code=product_code,
            name=name,
            category=category,
            market=market,
            currency=currency,
            store=store,
            product_url=product_url,
            image_url=image_url,
            affiliate_url=affiliate_url,
            external_id=external_id,
            catalog_source=catalog_source
        )

        # Cria ou recupera a oferta individual da loja.
        offer_id = database.add_offer(
            product_id=product_id,
            store=store,
            external_id=external_id,
            product_url=product_url,
            affiliate_url=affiliate_url,
            image_url=image_url,
            catalog_source=catalog_source
        )

        # Registra preço vinculado à oferta.
        price_id = database.add_offer_price(
            offer_id=offer_id,
            price=price,
            currency=currency,
            source=catalog_source or store
        )

        return {
            "product_id": product_id,
            "offer_id": offer_id,
            "price_id": price_id,
            "product_code": product_code,
            "store": store,
            "price": round(price, 2),
            "currency": currency,
            "market": market,
            "recorded_at": datetime.now(
                timezone.utc
            ).isoformat()
        }

    # =================================================
    # HISTÓRICO LEGADO DO PRODUTO
    # =================================================

    def get_history(self, product_code):

        product = self.find_product(product_code)

        if product is None:
            return []

        return database.get_price_history(product["id"])

    # =================================================
    # LISTAR OFERTAS DE UM PRODUTO
    # =================================================

    def get_product_offers(self, product_code):

        product = self.find_product(product_code)

        if product is None:
            return []

        return database.get_offers(
            product_id=product["id"]
        )

    # =================================================
    # HISTÓRICO DE UMA OFERTA
    # =================================================

    def get_offer_history(self, offer_id):

        return database.get_offer_history(offer_id)

    # =================================================
    # ANALISAR HISTÓRICO
    # =================================================

    def _analyze_history(self, history, product_code, offer_id=None):

        if not history:
            return {
                "status": "no_data",
                "product_code": product_code,
                "offer_id": offer_id,
                "records": 0,
                "message": "No price history available."
            }

        prices = [
            float(item["price"])
            for item in history
        ]

        current = prices[-1]
        previous = prices[-2] if len(prices) >= 2 else None

        result = {
            "status": "collecting_data",
            "product_code": product_code,
            "offer_id": offer_id,
            "current_price": round(current, 2),
            "currency": history[-1]["currency"],
            "records": len(prices),
            "message": "More price records are needed."
        }

        if len(prices) < 2:
            return result

        average_price = mean(prices)
        historical_low = min(prices)
        previous_low = min(prices[:-1])

        variation = (
            ((current - previous) / previous) * 100
            if previous else 0
        )

        result.update({
            "status": "analyzed",
            "average_price": round(average_price, 2),
            "historical_low": round(historical_low, 2),
            "previous_price": round(previous, 2),
            "variation_percent": round(variation, 2),
            "price_decreased": current < previous,
            "new_historical_low": current < previous_low,
            "message": "Analysis based on recorded prices."
        })

        return result

    # =================================================
    # ANALISAR UMA OFERTA ESPECÍFICA
    # =================================================

    def analyze_offer(self, offer_id):

        offers = database.get_offers()

        offer = next(
            (
                item for item in offers
                if item["id"] == offer_id
            ),
            None
        )

        if offer is None:
            return {
                "status": "not_found",
                "offer_id": offer_id,
                "message": "Offer not found."
            }

        history = database.get_offer_history(offer_id)

        result = self._analyze_history(
            history=history,
            product_code=offer["product_code"],
            offer_id=offer_id
        )

        result["store"] = offer["store"]

        return result

    # =================================================
    # COMPARAR OFERTAS DO MESMO PRODUTO
    # =================================================

    def compare_offers(self, product_code):

        product = self.find_product(product_code)

        if product is None:
            return {
                "status": "not_found",
                "product_code": product_code,
                "message": "Product not found."
            }

        offers = database.get_offers(
            product_id=product["id"]
        )

        comparisons = []

        for offer in offers:

            history = database.get_offer_history(
                offer["id"]
            )

            if not history:
                continue

            current_price = float(
                history[-1]["price"]
            )

            comparisons.append({
                "offer_id": offer["id"],
                "store": offer["store"],
                "price": round(current_price, 2),
                "currency": history[-1]["currency"],
                "product_url": offer["product_url"],
                "affiliate_url": offer["affiliate_url"],
                "records": len(history)
            })

        comparisons.sort(
            key=lambda item: item["price"]
        )

        return {
            "status": "compared",
            "product_code": product_code,
            "product_name": product["name"],
            "market": product["market"],
            "currency": product["currency"],
            "offers_found": len(comparisons),
            "best_offer": comparisons[0] if comparisons else None,
            "offers": comparisons
        }

    # =================================================
    # ANÁLISE LEGADA POR PRODUTO
    # Mantida para compatibilidade.
    # =================================================

    def analyze_price(self, product_code):

        history = self.get_history(product_code)

        return self._analyze_history(
            history=history,
            product_code=product_code
        )


# =====================================================
# EXECUÇÃO
# =====================================================

if __name__ == "__main__":

    engine = PriceEngine()

    print("\n===== WEBEOUT PRICE ENGINE =====")
    print("Database connection initialized.")
    print("Product analysis system ready.")
    print("Independent offer analysis ready.")
