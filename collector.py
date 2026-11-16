
# =====================================================
# WEBEOUT — PRODUCT COLLECTOR
# Importador, validador e organizador de ofertas
# =====================================================

import math
from urllib.parse import urlparse

import database

class ProductCollector:

    def __init__(self):
        database.initialize_database()

    # =================================================
    # VALIDAR TEXTO
    # =================================================

    def validate_text(self, value, field):

        if not isinstance(value, str):
            raise ValueError(f"Invalid {field}.")

        value = value.strip()

        invalid_values = {
            "",
            "string",
            "null",
            "none",
            "undefined",
            "unknown",
            "n/a"
        }

        if value.lower() in invalid_values:
            raise ValueError(f"Invalid {field}.")

        return value

    # =================================================
    # VALIDAR URL
    # =================================================

    def validate_url(self, value, field):

        if not value:
            return ""

        if not isinstance(value, str):
            raise ValueError(f"Invalid {field}.")

        value = value.strip()

        parsed = urlparse(value)

        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Invalid {field}.")

        if not parsed.netloc:
            raise ValueError(f"Invalid {field}.")

        return value

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

        product_code = self.validate_text(
            product["product_code"],
            "product code"
        )

        name = self.validate_text(
            product["name"],
            "product name"
        )

        store = self.validate_text(
            product.get("store"),
            "store"
        )

        if store.lower() in (
            "unknown store",
            "test",
            "example store"
        ):
            raise ValueError("Store is not valid.")

        if len(product_code) < 3:
            raise ValueError("Product code is too short.")

        if len(name) < 3:
            raise ValueError("Product name is too short.")

        if product_code.lower() == name.lower():
            raise ValueError("Product code and name cannot be identical.")

        try:
            price = float(product["price"])
        except (TypeError, ValueError):
            raise ValueError("Invalid product price.")

        if not math.isfinite(price) or price <= 0:
            raise ValueError("Invalid product price.")

        market = str(product["market"]).strip().upper()
        currency = str(product["currency"]).strip().upper()

        if market not in ("US", "DE"):
            raise ValueError("Unsupported market.")

        expected_currency = {
            "US": "USD",
            "DE": "EUR"
        }[market]

        if currency != expected_currency:
            raise ValueError("Currency does not match market.")

        external_id = str(
            product.get("external_id") or ""
        ).strip()

        product_url = self.validate_url(
            product.get("product_url") or "",
            "product URL"
        )

        if not external_id and not product_url:
            raise ValueError(
                "Product requires an external ID or product URL."
            )

        if external_id.lower() in (
            "string",
            "null",
            "undefined",
            "none"
        ):
            raise ValueError("Invalid external ID.")

        self.validate_url(
            product.get("affiliate_url") or "",
            "affiliate URL"
        )

        self.validate_url(
            product.get("image_url") or "",
            "image URL"
        )

        return True

    # =================================================
    # IMPORTAR UMA OFERTA
    # =================================================

    def import_product(self, product):

        self.validate_product(product)

        product_code = product["product_code"].strip()
        name = product["name"].strip()

        market = str(product["market"]).strip().upper()
        currency = str(product["currency"]).strip().upper()

        price = round(float(product["price"]), 2)

        store = product["store"].strip()

        catalog_source = str(
            product.get("catalog_source") or "IMPORT"
        ).strip().upper()

        if catalog_source.lower() in (
            "string",
            "null",
            "undefined",
            "none"
        ):
            raise ValueError("Invalid catalog source.")

        external_id = str(
            product.get("external_id") or ""
        ).strip()

        product_url = product.get("product_url") or ""
        affiliate_url = product.get("affiliate_url") or ""
        image_url = product.get("image_url") or ""

        # ---------------------------------------------
        # 1. CADASTRAR OU ATUALIZAR O PRODUTO
        # ---------------------------------------------

        product_id = database.add_product(
            product_code=product_code,
            name=name,
            category=product.get("category", "Other"),
            market=market,
            currency=currency,
            store=store,
            product_url=product_url,
            image_url=image_url,
            affiliate_url=affiliate_url,
            external_id=external_id,
            catalog_source=catalog_source
        )

        # ---------------------------------------------
        # 2. CADASTRAR OU ATUALIZAR A OFERTA DA LOJA
        # ---------------------------------------------

        offer_id = database.add_offer(
            product_id=product_id,
            store=store,
            external_id=external_id,
            product_url=product_url,
            affiliate_url=affiliate_url,
            image_url=image_url,
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
            "product_code": product_code,
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
    print("Product validation enabled.")
    print("Waiting for an authorized data source.")