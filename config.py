"""Configuração central do B2B Credit Decision Engine - FRATELLI"""

# =========================
# PRODUTOS
# =========================
PRODUCTS = [
    {
        "name": "Fratelli Montanhas",
        "code": "Produto A",
        "unit_price": 166.20,
        "units_per_box": 9
    },
    {
        "name": "Fratelli Desertos",
        "code": "Produto B",
        "unit_price": 162.20,
        "units_per_box": 9
    },
    {
        "name": "Fratelli Cânions",
        "code": "Produto C",
        "unit_price": 175.20,
        "units_per_box": 9
    },
]

# =========================
# PRAZOS DE PAGAMENTO
# =========================
PAYMENT_TERMS = [
    {"label": "À vista", "days": 0, "risk_factor": 0.00},
    {"label": "7 dias", "days": 7, "risk_factor": 0.02},
    {"label": "15 dias", "days": 15, "risk_factor": 0.05},
    {"label": "30 dias", "days": 30, "risk_factor": 0.10},
    {"label": "45 dias", "days": 45, "risk_factor": 0.15},
    {"label": "60 dias", "days": 60, "risk_factor": 0.20},
    {"label": "30/60 dias", "days": 60, "risk_factor": 0.25}
]

# =========================
# POLÍTICA DE LIMITE POR SCORE
# =========================
LIMIT_BANDS = [
    (0, 25, 0.0),
    (25, 35, 1500.0),
    (35, 45, 5000.0),
    (45, 55, 10000.0),
    (55, 65, 15000.0),
    (65, 70.0000001, 20000.0),
]

# Penalização por falta de dados
MISSING_FACTOR = 0.25


# =========================
# DESCONTOS COMERCIAIS FRATELLI
# =========================
# REGRA:
# 1 a 2 caixas → 20%
# >2 caixas até 34 unidades → 25%
# >=36 unidades → 30%
# =========================

COMMERCIAL_DISCOUNT_TIERS = [
    {
        "min_boxes": 1,
        "max_boxes": 2,
        "min_units": None,
        "max_units": None,
        "discount": 0.20
    },
    {
        "min_boxes": 3,
        "max_boxes": None,
        "min_units": None,
        "max_units": 34,
        "discount": 0.25
    },
    {
        "min_boxes": None,
        "max_boxes": None,
        "min_units": 36,
        "max_units": None,
        "discount": 0.30
    },
]
