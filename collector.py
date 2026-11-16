
# =====================================================
# WEBEOUT — PRODUCT COLLECTOR
# Importador, validador e organizador de ofertas
# =====================================================

import math
import database


class ProductCollector:

    def __init__(self):
        database.initialize_database()

    # =================================================
    # VALIDAR PRODUTO
    # =================================================

    def validate_product(self, product):

        if not isinstance(product, dict):
            raise ValueError("Product must be a dictionary.")

        required_fields = [
            "product_code",
            "name",
            "price",
            "currency",
            "market"
        ]

        for field in required_fields:
            value = product.get(field)

            if value is None or value == "":
                raise ValueError(
                    f"Missing required field: {field}"
                )

        try:
            price = float(product["price"])
        except (TypeError, ValueError):
            raise ValueError("Invalid product price.")

        if not math.isfinite(price) or price <= 0:
            raise ValueError("Invalid product price.")

        market = str(product["market"]).upper()
        currency = str(product["currency"]).upper()

        if market not in ("US", "DE"):
            raise ValueError("Unsupported market.")

        expected_currency = {
            "US": "USD",
            "DE": "EUR"
        }[market]

        if currency != expected_currency:
            raise ValueError("Currency does not match market.")

        if not str(product["product_code"]).strip():
            raise ValueError("Product code cannot be empty.")

        if not str(product["name"]).strip():
            raise ValueError("Product name cannot be empty.")

        return True

    # =================================================
    # IMPORTAR UMA OFERTA
    # =================================================

    def import_product(self, product):

        self.validate_product(product)

        market = str(product["market"]).upper()
        currency = str(product["currency"]).upper()
        price = round(float(product["price"]), 2)

        store = str(
            product.get("store") or "Unknown Store"
        ).strip()

        catalog_source = (
            product.get("catalog_source") or "IMPORT"
        )

        # ---------------------------------------------
        # 1. CADASTRAR OU ATUALIZAR O PRODUTO
        # ---------------------------------------------

        product_id = database.add_product(
            product_code=product["product_code"],
            name=product["name"],
            category=product.get("category", "Other"),
            market=market,
            currency=currency,
            store=store,
            product_url=product.get("product_url"),
            image_url=product.get("image_url"),
            affiliate_url=product.get("affiliate_url"),
            external_id=product.get("external_id"),
            catalog_source=catalog_source
        )

        # ---------------------------------------------
        # 2. CADASTRAR OU ATUALIZAR A OFERTA DA LOJA
        # ---------------------------------------------

        offer_id = database.add_offer(
            product_id=product_id,
            store=store,
            external_id=product.get("external_id"),
            product_url=product.get("product_url"),
            affiliate_url=product.get("affiliate_url"),
            image_url=product.get("image_url"),
            catalog_source=catalog_source
        )

        # ---------------------------------------------
        # 3. CONSULTAR HISTÓRICO DA OFERTA
        # ---------------------------------------------

        history = database.get_offer_history(offer_id)

        # ---------------------------------------------
        # 4. EVITAR REGISTROS DUPLICADOS DE PREÇO
        # ---------------------------------------------

        if (
            not history
            or round(float(history[-1]["price"]), 2) != price
        ):

            price_id = database.add_offer_price(
                offer_id=offer_id,
                price=price,
                currency=currency,
                source=catalog_source
            )

            price_updated = True

        else:
            price_id = None
            price_updated = False

        # ---------------------------------------------
        # 5. RETORNAR RESULTADO
        # ---------------------------------------------

        return {
            "success": True,
            "product_id": product_id,
            "offer_id": offer_id,
            "price_id": price_id,
            "product_code": product["product_code"],
            "store": store,
            "market": market,
            "currency": currency,
            "price": price,
            "price_updated": price_updated,
            "message": "Offer imported successfully."
        }

    # =================================================
    # IMPORTAR VÁRIAS OFERTAS
    # =================================================

    def import_products(self, products):

        results = []

        for product in products:

            try:
                result = self.import_product(product)
                results.append(result)

            except (ValueError, TypeError, KeyError) as error:

                results.append({
                    "success": False,
                    "product_code": (
                        product.get("product_code")
                        if isinstance(product, dict)
                        else None
                    ),
                    "error": str(error)
                })

        return {
            "total": len(products),
            "successful": sum(
                1 for item in results if item["success"]
            ),
            "failed": sum(
                1 for item in results if not item["success"]
            ),
            "results": results
        }


# =====================================================
# EXECUÇÃO
# =====================================================

if __name__ == "__main__":

    collector = ProductCollector()

    print("====================================")
    print("WEBEOUT PRODUCT COLLECTOR")
    print("====================================")
    print("Database connected.")
    print("Independent offer collection ready.")
    print("Waiting for an authorized data source.")
