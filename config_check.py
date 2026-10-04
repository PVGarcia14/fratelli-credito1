"""Valida a configuração antes do deploy."""
import ast
from pathlib import Path

p = Path(__file__).with_name("config.py")
ast.parse(p.read_text(encoding="utf-8"))
import config

assert isinstance(config.PRODUCTS, list)
assert isinstance(config.LIMIT_BANDS, list)
assert isinstance(config.PAYMENT_TERMS, list)
assert isinstance(config.COMMERCIAL_DISCOUNT_TIERS, list)
for product in config.PRODUCTS:
    assert product.get("name")
    assert float(product.get("unit_price", 0)) >= 0
    assert int(product.get("units_per_box", 0)) > 0
print("CONFIG OK")
