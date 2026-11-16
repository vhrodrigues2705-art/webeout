
# =====================================================
# WEBEOUT — PRODUCT COLLECTOR
# Importador e validador de produtos
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

        required_fields = [
            "product_code",
            "name",
            "price",
            "currency",
            "market"
        ]

        for field in required_fields:
            if field not in product or product[field] is None:
                raise ValueError(
                    f"Missing required field: {field}"
                )

        price = float(product["price"])

        if not math.isfinite(price) or price <= 0:
            raise ValueError("Invalid product price.")

        market = product["market"]
        currency = product["currency"]

        if market not in ("US", "DE"):
            raise ValueError("Unsupported market.")

        expected_currency = {
            "US": "USD",
            "DE": "EUR"
        }[market]

        if currency != expected_currency:
            raise ValueError("Currency does not match market.")

        return True

    # =================================================
    # IMPORTAR UM PRODUTO
    # =================================================

    def import_product(self, product):

        self.validate_product(product)

        product_id = database.add_product(
            product_code=product["product_code"],
            name=product["name"],
            category=product.get("category", "Other"),
            market=product["market"],
            currency=product["currency"],
            store=product.get("store"),
            product_url=product.get("product_url"),
            image_url=product.get("image_url"),
            affiliate_url=product.get("affiliate_url"),
            external_id=product.get("external_id"),
            catalog_source=product.get("catalog_source")
        )

        # Verifica o último preço registrado.
        history = database.get_price_history(product_id)

        new_price = round(float(product["price"]), 2)

        if not history or round(float(history[-1]["price"]), 2) != new_price:

            database.add_price(
                product_id=product_id,
                price=new_price,
                currency=product["currency"],
                source=product.get("catalog_source", "IMPORT")
            )

            price_updated = True

        else:
            price_updated = False

        return {
            "success": True,
            "product_id": product_id,
            "product_code": product["product_code"],
            "price_updated": price_updated,
            "message": "Product imported successfully."
        }

    # =================================================
    # IMPORTAR VÁRIOS PRODUTOS
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
                    "product_code": product.get("product_code"),
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

    print("Webeout Product Collector ready.")
    print("Waiting for an authorized product data source.")
