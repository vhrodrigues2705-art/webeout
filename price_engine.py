
from datetime import datetime, timezone
from statistics import mean

import database


class PriceEngine:

    def __init__(self):
        database.initialize_database()

    def find_product(self, product_code):
        products = database.get_products()

        for product in products:
            if product["product_code"] == product_code:
                return product

        return None

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
        image_url=""
    ):

        if price <= 0:
            raise ValueError("Price must be greater than zero.")

        if market not in ("US", "DE"):
            raise ValueError("Unsupported market.")

        if market == "US" and currency != "USD":
            raise ValueError("USA products must use USD.")

        if market == "DE" and currency != "EUR":
            raise ValueError("German products must use EUR.")

        product = self.find_product(product_code)

        if product is None:
            product_id = database.add_product(
                product_code=product_code,
                name=name,
                category=category,
                market=market,
                currency=currency,
                store=store,
                product_url=product_url,
                image_url=image_url
            )
        else:
            product_id = product["id"]

        database.add_price(
            product_id=product_id,
            price=price,
            currency=currency,
            source=store or "Unknown"
        )

        return {
            "product_id": product_id,
            "product_code": product_code,
            "price": round(float(price), 2),
            "currency": currency,
            "market": market,
            "recorded_at": datetime.now(timezone.utc).isoformat()
        }

    def get_history(self, product_code):

        product = self.find_product(product_code)

        if product is None:
            return []

        return database.get_price_history(product["id"])

    def analyze_price(self, product_code):

        history = self.get_history(product_code)

        if not history:
            return {
                "status": "no_data",
                "message": "No price history available."
            }

        prices = [float(item["price"]) for item in history]

        current = prices[-1]
        previous = prices[-2] if len(prices) >= 2 else None

        result = {
            "status": "collecting_data",
            "product_code": product_code,
            "current_price": current,
            "currency": history[-1]["currency"],
            "records": len(prices),
            "message": "More price records are needed."
        }

        if len(prices) < 2:
            return result

        average_price = mean(prices)
        historical_low = min(prices)
        previous_low = min(prices[:-1])

        variation = ((current - previous) / previous) * 100

        result.update({
            "status": "analyzed",
            "average_price": round(average_price, 2),
            "historical_low": round(historical_low, 2),
            "previous_price": previous,
            "variation_percent": round(variation, 2),
            "price_decreased": current < previous,
            "new_historical_low": current < previous_low,
            "message": "Analysis based on recorded prices."
        })

        return result


if __name__ == "__main__":

    engine = PriceEngine()

    print("\n===== WEBEOUT PRICE ENGINE =====")
    print("Database connection initialized.")
    print("Price analysis system ready.")
