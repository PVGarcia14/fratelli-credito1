"""Configuração central do B2B Credit Decision Engine.

Edite os valores abaixo para um catálogo B2B permitido. Evite alterar a estrutura
Python; para nomes, preços e unidades, altere apenas os valores entre aspas/números.
"""

PRODUCTS = [
    {"Fratelli Montanhas": "Produto A", "unit_price": 166.20, "units_per_box": 9},
    {"Fratelli Desertos": "Produto B", "unit_price": 162.20, "units_per_box": 9},
    {"Fratelli Cânions": "Produto C", "unit_price": 175.20, "units_per_box": 9},
]

PAYMENT_TERMS = [
    {"label": "À vista", "days": 0, "risk_factor": 0.00},
    {"label": "7 dias", "days": 7, "risk_factor": 0.02},
    {"label": "15 dias", "days": 15, "risk_factor": 0.05},
    {"label": "30 dias", "days": 30, "risk_factor": 0.10},
    {"label": "45 dias", "days": 45, "risk_factor": 0.15},
    {"label": "60 dias", "days": 60, "risk_factor": 0.20},
    {"label": "30/60 dias", "days": 60, "risk_factor": 0.25}
]

LIMIT_BANDS = [
    (0, 25, 0.0),
    (25, 35, 1500.0),
    (35, 45, 5000.0),
    (45, 55, 10000.0),
    (55, 65, 15000.0),
    (65, 70.0000001, 20000.0),
]

MISSING_FACTOR = 0.25

# Política comercial genérica e configurável.
# Valores de exemplo: ajuste conforme o catálogo permitido.
COMMERCIAL_DISCOUNT_TIERS = [
    {
        "min_boxes": 1,
        "max_boxes": 2,
        "min_units": None,
        "max_units": None,
        "discount": DESCONTO_FAIXA_1
    },
    {
        "min_boxes": 3,
        "max_boxes": None,
        "min_units": None,
        "max_units": 34,
        "discount": DESCONTO_FAIXA_2
    },
    {
        "min_boxes": None,
        "max_boxes": None,
        "min_units": 36,
        "max_units": None,
        "discount": DESCONTO_FAIXA_3
    },
]
