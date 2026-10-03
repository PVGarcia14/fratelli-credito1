# Configuração neutra de produto/condições.
# Não contém catálogo ou regras de comercialização de bebidas alcoólicas.

PAYMENT_TERMS = [
    "À vista",
    "50% + 30 dias",
    "30/60 dias",
]

def suggest_term(score, confidence, critical_alert=False):
    if critical_alert or confidence < 55 or score < 45:
        return "À vista"
    if score < 70:
        return "50% + 30 dias"
    return "30/60 dias"
