
import uuid

from collector import ProductCollector

collector = ProductCollector()

# Identificadores exclusivos para cada execução
test_id = uuid.uuid4().hex[:12]

product = {
    "product_code": f"webeout-test-{test_id}",
    "name": "Webeout Collector Test",
    "category": "Electronics",
    "price": 12.99,
    "currency": "USD",
    "market": "US",
    "store": "Walmart",
    "external_id": f"WALMART-TEST-{test_id}",
    "product_url": "https://example.com/test",
    "catalog_source": "TEST"
}

print("\n===== FIRST IMPORT =====")
first = collector.import_product(product)
print(first)

print("\n===== SECOND IMPORT =====")
second = collector.import_product(product)
print(second)

assert first["success"] is True
assert first["price_updated"] is True

assert second["success"] is True
assert second["price_updated"] is False

print("\nSUCCESS: Collector test passed!")
print("First import registered the price.")
print("Second import avoided duplicate price history.")