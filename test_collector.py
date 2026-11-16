from collector import ProductCollector

collector = ProductCollector()

product = {
    "product_code": "webeout-collector-check-001",
    "name": "Webeout Collector Test",
    "category": "Electronics",
    "price": 12.99,
    "currency": "USD",
    "market": "US",
    "store": "Walmart",
    "external_id": "WALMART-COLLECTOR-CHECK-001",
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