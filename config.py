from __future__ import annotations

# Generic B2B configuration. Product names/prices/terms are intentionally placeholders.
# Keep commercial catalog values in this file or replace with your own internal catalog.
PRODUCTS = [
    {"name": "Produto A", "unit_price": 100.00, "units_per_box": 9},
    {"name": "Produto B", "unit_price": 120.00, "units_per_box": 9},
    {"name": "Produto C", "unit_price": 150.00, "units_per_box": 9},
]

PAYMENT_TERMS = [
    {"label": "À vista", "days": 0, "risk_factor": 0.00},
    {"label": "7 dias", "days": 7, "risk_factor": 0.02},
    {"label": "15 dias", "days": 15, "risk_factor": 0.05},
    {"label": "30 dias", "days": 30, "risk_factor": 0.10},
    {"label": "45 dias", "days": 45, "risk_factor": 0.15},
    {"label": "60 dias", "days": 60, "risk_factor": 0.20},
]

# Policy supplied by the project specification.
LIMIT_BANDS = [
    (0, 25, 0.0),
    (25, 35, 1500.0),
    (35, 45, 5000.0),
    (45, 55, 10000.0),
    (55, 70.0000001, 20000.0),
]

MISSING_FACTOR = 0.25
