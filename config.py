from __future__ import annotations

# Generic B2B catalog. Configure the actual catalog for your permitted business use.
# The engine never invents product names or prices: the values shown in the UI come from here.
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

LIMIT_BANDS = [
    (0, 25, 0.0),
    (25, 35, 1500.0),
    (35, 45, 5000.0),
    (45, 55, 10000.0),
    (55, 70.0000001, 20000.0),
]

MISSING_FACTOR = 0.25

# Generic configurable commercial policy. Percentages are intentionally neutral examples.
# The administrator can change these for the permitted catalog in use.
COMMERCIAL_DISCOUNT_TIERS = [
    {"min_boxes": 1, "max_boxes": 2, "min_units": None, "max_units": None, "discount": 0.10},
    {"min_boxes": 3, "max_boxes": None, "min_units": None, "max_units": 34, "discount": 0.15},
    {"min_boxes": None, "max_boxes": None, "min_units": 36, "max_units": None, "discount": 0.20},
]
