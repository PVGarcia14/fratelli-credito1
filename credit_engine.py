from __future__ import annotations

import math
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from config import LIMIT_BANDS, MISSING_FACTOR, COMMERCIAL_DISCOUNT_TIERS


# ============================================================
# PESOS DO MOTOR DE CRÉDITO
# ============================================================

WEIGHTS = {
    "Legitimidade e cadastro": 20,
    "Tempo de atividade": 10,
    "Estrutura e capacidade": 25,
    "Histórico público e risco": 20,
    "Qualidade das evidências": 25,
}


# ============================================================
# UTILITÁRIOS
# ============================================================

def clean_cnpj(value: str) -> str:
    """Remove qualquer caractere que não seja número."""
    return re.sub(r"\D", "", value or "")


def validate_cnpj(value: str) -> Tuple[bool, str]:
    """Valida quantidade de dígitos e dígitos verificadores do CNPJ."""

    cnpj = clean_cnpj(value)

    if len(cnpj) != 14:
        return False, "CNPJ inválido: informe 14 dígitos."

    if cnpj == cnpj[0] * 14:
        return False, "CNPJ inválido."

    numbers = list(map(int, cnpj))

    weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    for position, weights in (
        (12, weights_1),
        (13, weights_2),
    ):
        total = sum(
            numbers[i] * weights[i]
            for i in range(len(weights))
        )

        digit = (total * 10) % 11

        if digit == 10:
            digit = 0

        if numbers[position] != digit:
            return (
                False,
                "CNPJ inválido: dígitos verificadores não conferem.",
            )

    return True, cnpj


def parse_date(value: Any) -> Optional[date]:

    if not value:
        return None

    text = str(value).strip()

    formats = (
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    )

    for fmt in formats:
        try:
            return datetime.strptime(
                text[:26],
                fmt,
            ).date()
        except ValueError:
            continue

    return None


def age_years(
    opening: Any,
    today: Optional[date] = None,
) -> Optional[float]:

    opening_date = parse_date(opening)

    if not opening_date:
        return None

    reference = today or date.today()

    days = (reference - opening_date).days

    if days < 0:
        return None

    return round(days / 365.2425, 2)


def money(value: float) -> float:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0.0

    return round(max(0.0, number), 2)


# ============================================================
# FAIXA DE RISCO
# ============================================================

def risk_band(score: float) -> str:

    score = float(score)

    if score < 25:
        return "ALTO RISCO"

    if score < 45:
        return "RISCO ELEVADO"

    if score < 55:
        return "RISCO MODERADO"

    if score <= 70:
        return "RISCO CONTROLADO"

    return "RISCO INDIVIDUALIZADO"


# ============================================================
# LIMITE DE CRÉDITO
# ============================================================

def score_limit(
    score: float,
    requested: float = 0.0,
    confidence: float = 0.0,
    critical: bool = False,
) -> Tuple[float, str]:

    score = max(
        0.0,
        min(100.0, float(score)),
    )

    confidence = max(
        0.0,
        min(1.0, float(confidence)),
    )

    # Fator crítico sempre bloqueia.
    if critical:
        return 0.0, "RECUSAR"

    # Score abaixo de 25.
    if score < 25:
        return 0.0, "RECUSAR"

    # Faixas configuradas.
    for lower, upper, limit in LIMIT_BANDS:

        if lower <= score < upper:

            return money(limit), "APROVAR COM LIMITE"

    # Scores acima da última faixa:
    # cálculo individualizado, limitado pela confiança.
    base_limit = 20000.0 + (
        max(0.0, score - 70.0) * 2500.0
    )

    base_limit = min(
        100000.0,
        base_limit,
    )

    evidence_limit = base_limit * max(
        0.25,
        confidence,
    )

    limit = min(
        base_limit,
        evidence_limit,
    )

    if requested > 0 and requested <= limit:
        decision = "APROVAR"
    else:
        decision = "APROVAR COM LIMITE"

    return money(limit), decision


# ============================================================
# CRITÉRIO
# ============================================================

def criterion(
    name: str,
    max_points: float,
    points: Optional[float],
    evidence: str,
    details: Optional[List[str]] = None,
) -> Dict[str, Any]:

    max_points = max(
        0.0,
        float(max_points),
    )

    if points is None:

        points_value = (
            max_points * MISSING_FACTOR
        )

        status = "INFORMAÇÃO PARCIAL"

    else:

        points_value = max(
            0.0,
            min(
                max_points,
                float(points),
            ),
        )

        status = "COM EVIDÊNCIA"

    return {
        "name": name,
        "max": max_points,
        "points": round(points_value, 2),
        "status": status,
        "evidence": evidence,
        "details": details or [],
    }


# ============================================================
# ANÁLISE DE CRÉDITO
# ============================================================

def analyze(
    dossier: Dict[str, Any],
    requested: float = 0.0,
    internal_payment_status: str = "Sem histórico",
    overdue: float = 0.0,
    exposure: float = 0.0,
    payment_risk: float = 0.0,
) -> Dict[str, Any]:

    dossier = dossier or {}

    fields = dossier.get(
        "fields",
        {},
    ) or {}

    conflicts = dossier.get(
        "conflicts",
        [],
    ) or []

    successful = int(
        dossier.get(
            "successful_sources",
            0,
        ) or 0
    )

    total = int(
        dossier.get(
            "source_count",
            0,
        ) or 0
    )

    critical_flags = list(
        dossier.get(
            "critical_flags",
            [],
        ) or []
    )

    partners = dossier.get(
        "partners",
        [],
    ) or []

    status = str(
        fields.get(
            "Situação cadastral",
            "",
        )
    ).upper()

    # --------------------------------------------------------
    # SITUAÇÃO CRÍTICA
    # --------------------------------------------------------

    critical_statuses = (
        "INAPTA",
        "BAIXADA",
        "SUSPENSA",
    )

    if (
        any(item in status for item in critical_statuses)
        and not critical_flags
    ):
        critical_flags.append(
            f"Situação cadastral crítica: {status}."
        )

    # --------------------------------------------------------
    # IDADE
    # --------------------------------------------------------

    age = age_years(
        fields.get("Data de abertura")
    )

    criteria: List[Dict[str, Any]] = []

    # ========================================================
    # 1. LEGITIMIDADE E CADASTRO
    # ========================================================

    registration_points = None
    registration_details = []

    if status or fields:

        if "ATIVA" in status:
            registration_points = 12.0

        elif any(
            item in status
            for item in critical_statuses
        ):
            registration_points = 3.0

        else:
            registration_points = 7.0

        identity_fields = (
            "Razão social",
            "CNPJ",
            "Endereço",
            "CNAE principal",
            "Natureza jurídica",
        )

        found_identity = sum(
            bool(fields.get(field))
            for field in identity_fields
        )

        registration_points += min(
            4.0,
            found_identity * 0.8,
        )

        registration_points = min(
            20.0,
            registration_points,
        )

        registration_details.append(
            f"Situação: {status or 'não identificada'}."
        )

        registration_details.append(
            f"Campos cadastrais encontrados: "
            f"{found_identity}/{len(identity_fields)}."
        )

    criteria.append(
        criterion(
            "Legitimidade e cadastro",
            20,
            registration_points,
            "Existência, situação e consistência dos dados cadastrais.",
            registration_details,
        )
    )

    # ========================================================
    # 2. TEMPO DE ATIVIDADE
    # ========================================================

    age_points = None
    age_details = []

    if age is not None:

        if age < 1:
            factor = 0.10
            range_name = "menos de 1 ano"

        elif age <= 3:
            factor = 0.60
            range_name = "entre 1 e 3 anos"

        else:
            factor = 1.00
            range_name = "acima de 3 anos"

        age_points = 10.0 * factor

        age_details = [
            f"Idade estimada: {age:.1f} anos.",
            f"Faixa: {range_name}.",
            (
                "Pontuação aplicada: "
                f"{factor * 100:.0f}% do critério."
            ),
        ]

    criteria.append(
        criterion(
            "Tempo de atividade",
            10,
            age_points,
            "Tempo desde a abertura do CNPJ.",
            age_details,
        )
    )

    # ========================================================
    # 3. ESTRUTURA E CAPACIDADE
    # ========================================================

    structure_points = None
    structure_details = []

    if successful or fields:

        structure_points = 8.0

        structure_fields = (
            "Capital social",
            "Porte",
            "CNAE principal",
            "Natureza jurídica",
        )

        found_structure = sum(
            bool(fields.get(field))
            for field in structure_fields
        )

        structure_points += min(
            7.0,
            found_structure * 1.75,
        )

        structure_points += min(
            5.0,
            len(partners) * 1.5,
        )

        if dossier.get(
            "public_presence",
            False,
        ):
            structure_points += 2.0

        if fields.get("Capital social"):
            structure_points += 3.0

        structure_points = min(
            25.0,
            structure_points,
        )

        structure_details.append(
            f"Sócios identificados: {len(partners)}."
        )

        if dossier.get(
            "verified_revenue",
            False,
        ):
            structure_details.append(
                "Informação financeira pública identificada."
            )
        else:
            structure_details.append(
                "Faturamento não identificado em "
                "fonte pública confiável."
            )

    criteria.append(
        criterion(
            "Estrutura e capacidade",
            25,
            structure_points,
            "Porte, capital, atividade, estrutura e presença pública observáveis.",
            structure_details,
        )
    )

    # ========================================================
    # 4. HISTÓRICO PÚBLICO E RISCO
    # ========================================================

    history_points = None
    history_details = []

    if successful or fields:

        history_points = 16.0

        history_points -= min(
            10.0,
            len(critical_flags) * 5.0,
        )

        history_points -= min(
            5.0,
            len(conflicts) * 1.0,
        )

        if dossier.get(
            "public_presence",
            False,
        ):
            history_points += 2.0

        history_points = max(
            0.0,
            min(
                20.0,
                history_points,
            ),
        )

        if critical_flags:
            history_details.extend(
                critical_flags
            )
        else:
            history_details.append(
                "Nenhum evento crítico identificado "
                "nas fontes que responderam."
            )

    criteria.append(
        criterion(
            "Histórico público e risco",
            20,
            history_points,
            "Sinais públicos de risco, situação e divergências entre fontes.",
            history_details,
        )
    )

    # ========================================================
    # 5. QUALIDADE DAS EVIDÊNCIAS
    # ========================================================

    evidence_points = None

    if total or successful:

        ratio = (
            successful / max(1, total)
        )

        evidence_points = min(
            25.0,
            (
                10.0 * ratio
                + min(
                    10.0,
                    len(fields) * 1.5,
                )
                + max(
                    0.0,
                    5.0 - len(conflicts) * 1.5,
                )
            ),
        )

        evidence_points = max(
            0.0,
            min(
                25.0,
                evidence_points,
            ),
        )

    criteria.append(
        criterion(
            "Qualidade das evidências",
            25,
            evidence_points,
            (
                f"Fontes que responderam: "
                f"{successful}/{total}; "
                f"divergências: {len(conflicts)}."
            ),
        )
    )

    # ========================================================
    # SCORE
    # ========================================================

    score = round(
        sum(
            item["points"]
            for item in criteria
        ),
        2,
    )

    # ========================================================
    # HISTÓRICO COMERCIAL INTERNO
    # ========================================================

    commercial_modifier = 0.0

    if internal_payment_status == "Em dia":
        commercial_modifier = 5.0

    elif internal_payment_status == "Atrasos":
        commercial_modifier = -3.0

    elif internal_payment_status == "Inadimplente":
        commercial_modifier = -8.0

    if overdue > 0:

        commercial_modifier -= min(
            5.0,
            overdue / 10000.0,
        )

    score = round(
        max(
            0.0,
            min(
                100.0,
                score + commercial_modifier,
            ),
        ),
        2,
    )

    # ========================================================
    # COBERTURA
    # ========================================================

    coverage = round(
        sum(
            1
            for item in criteria
            if item["status"] == "COM EVIDÊNCIA"
        )
        / len(criteria)
        * 100,
        1,
    )

    # ========================================================
    # CONFIANÇA
    # ========================================================

    if total:

        confidence = (
            (
                successful
                / max(1, total)
            ) * 65
            + min(
                30,
                len(fields) * 2.5,
            )
            + max(
                0,
                5 - len(conflicts),
            )
        )

        confidence = round(
            max(
                0.0,
                min(
                    100.0,
                    confidence,
                ),
            ),
            1,
        )

    else:
        confidence = 0.0

    # ========================================================
    # LIMITE
    # ========================================================

    limit, policy_decision = score_limit(
        score,
        requested,
        confidence / 100.0,
        bool(critical_flags),
    )

    # ========================================================
    # PRAZO DE PAGAMENTO
    # ========================================================

    payment_risk = max(
        0.0,
        min(
            1.0,
            float(payment_risk or 0),
        ),
    )

    if payment_risk > 0 and limit > 0:

        limit = money(
            limit * (
                1 - payment_risk
            )
        )

    # ========================================================
    # SALDO DISPONÍVEL
    # ========================================================

    available = max(
        0.0,
        money(
            limit - exposure
        ),
    )

    # ========================================================
    # DECISÃO DO PEDIDO
    # ========================================================

    order = simulate_order_decision(
        requested,
        available,
        score,
        confidence,
        bool(critical_flags),
    )

    # ========================================================
    # EXPLICAÇÕES
    # ========================================================

    positives = []
    attentions = []

    for item in criteria:

        if item["points"] >= (
            item["max"] * 0.70
        ):
            positives.append(
                f"{item['name']}: "
                f"{item['evidence']}"
            )

        if (
            item["status"]
            == "INFORMAÇÃO PARCIAL"
            or item["points"]
            < item["max"] * 0.40
        ):
            attentions.append(
                f"{item['name']}: "
                "informação limitada ou sinal de atenção."
            )

    if commercial_modifier > 0:

        positives.append(
            f"Histórico interno: "
            f"+{commercial_modifier:.1f} pontos."
        )

    elif commercial_modifier < 0:

        attentions.append(
            f"Histórico interno: "
            f"{commercial_modifier:.1f} pontos."
        )

    for conflict in conflicts:

        attentions.append(
            "Divergência: "
            + str(
                conflict.get(
                    "field",
                    conflict,
                )
            )
        )

    for flag in critical_flags:

        attentions.append(
            f"Alerta crítico: {flag}"
        )

    return {
        "score": score,
        "confidence": confidence,
        "coverage": coverage,
        "criteria": criteria,
        "commercial_modifier": commercial_modifier,
        "limit": money(limit),
        "exposure": money(exposure),
        "available": money(available),
        "policy_decision": policy_decision,
        "order": order,
        "positives": positives,
        "attentions": attentions,
        "risk_band": risk_band(score),
        "critical": bool(critical_flags),
    }


# ============================================================
# DECISÃO DO PEDIDO
# ============================================================

def simulate_order_decision(
    requested: float,
    available: float,
    score: float,
    confidence: float,
    critical: bool,
) -> Dict[str, Any]:

    requested = money(requested)
    available = money(available)

    if requested <= 0:

        return {
            "decision": "SEM PEDIDO",
            "requested": 0,
            "excess": 0,
            "pct_excess": 0,
            "reason": (
                "Informe o valor do pedido "
                "para testar a operação."
            ),
        }

    excess = max(
        0.0,
        requested - available,
    )

    if available > 0:

        pct_excess = round(
            excess / available * 100,
            2,
        )

    else:

        pct_excess = 100.0

    if critical or score < 25:

        decision = "RECUSAR"

        reason = (
            "Há fator crítico ou score "
            "abaixo do piso de crédito."
        )

    elif requested <= available:

        decision = "APROVAR"

        reason = (
            "Pedido dentro do limite "
            "disponível para a operação."
        )

    elif (
        score > 70
        and confidence >= 70
        and excess / requested <= 0.20
    ):

        decision = "ANÁLISE EXCEPCIONAL"

        reason = (
            "Pedido acima do limite, mas os "
            "indicadores permitem análise "
            "complementar de exceção."
        )

    else:

        decision = "APROVAR COM LIMITE"

        reason = (
            "Pedido excede o limite; "
            "reduza o pedido ou encaminhe "
            "para análise excepcional."
        )

    return {
        "decision": decision,
        "requested": requested,
        "excess": money(excess),
        "pct_excess": pct_excess,
        "reason": reason,
    }


# ============================================================
# POLÍTICA COMERCIAL
# ============================================================

def commercial_discount(
    boxes: int,
    units: int,
    tiers: Optional[
        List[Dict[str, Any]]
    ] = None,
) -> float:

    boxes = max(
        0,
        int(boxes),
    )

    units = max(
        0,
        int(units),
    )

    # IMPORTANTE:
    # Não usar "tiers or COMMERCIAL_DISCOUNT_TIERS".
    # Se uma lista vazia for enviada, ela deve continuar vazia.
    policy = (
        COMMERCIAL_DISCOUNT_TIERS
        if tiers is None
        else tiers
    )

    for tier in policy:

        min_boxes = tier.get(
            "min_boxes"
        )

        max_boxes = tier.get(
            "max_boxes"
        )

        min_units = tier.get(
            "min_units"
        )

        max_units = tier.get(
            "max_units"
        )

        if (
            min_boxes is not None
            and boxes < int(min_boxes)
        ):
            continue

        if (
            max_boxes is not None
            and boxes > int(max_boxes)
        ):
            continue

        if (
            min_units is not None
            and units < int(min_units)
        ):
            continue

        if (
            max_units is not None
            and units > int(max_units)
        ):
            continue

        return max(
            0.0,
            min(
                1.0,
                float(
                    tier.get(
                        "discount",
                        0.0,
                    )
                ),
            ),
        )

    return 0.0


# ============================================================
# VALOR DO PEDIDO
# ============================================================

def order_value_for_boxes(
    boxes: int,
    unit_price: float,
    units_per_box: int = 9,
    tiers: Optional[
        List[Dict[str, Any]]
    ] = None,
) -> Dict[str, Any]:

    boxes = max(
        0,
        int(boxes),
    )

    units_per_box = max(
        1,
        int(units_per_box),
    )

    unit_price = money(
        unit_price
    )

    units = (
        boxes
        * units_per_box
    )

    gross = money(
        units
        * unit_price
    )

    discount_rate = commercial_discount(
        boxes,
        units,
        tiers,
    )

    discount_value = money(
        gross
        * discount_rate
    )

    net = money(
        gross
        - discount_value
    )

    return {
        "boxes": boxes,
        "units": units,
        "gross": gross,
        "discount_rate": discount_rate,
        "discount_value": discount_value,
        "net": net,
    }


# ============================================================
# MÁXIMO DE CAIXAS DENTRO DO LIMITE
# ============================================================

def max_boxes_within_limit(
    available_limit: float,
    unit_price: float,
    units_per_box: int = 9,
    tiers: Optional[
        List[Dict[str, Any]]
    ] = None,
) -> Dict[str, Any]:

    available = money(
        available_limit
    )

    unit_price = money(
        unit_price
    )

    units_per_box = max(
        1,
        int(units_per_box),
    )

    if (
        available <= 0
        or unit_price <= 0
    ):

        return order_value_for_boxes(
            0,
            unit_price,
            units_per_box,
            tiers,
        )

    gross_box = (
        unit_price
        * units_per_box
    )

    high = max(
        1,
        math.floor(
            available
            / gross_box
        ) + 2,
    )

    while True:

        test = order_value_for_boxes(
            high,
            unit_price,
            units_per_box,
            tiers,
        )

        if test["net"] <= (
            available + 1e-9
        ):
            high *= 2
        else:
            break

    low = 0

    while low < high:

        middle = (
            low + high + 1
        ) // 2

        test = order_value_for_boxes(
            middle,
            unit_price,
            units_per_box,
            tiers,
        )

        if test["net"] <= (
            available + 1e-9
        ):
            low = middle
        else:
            high = middle - 1

    return order_value_for_boxes(
        low,
        unit_price,
        units_per_box,
        tiers,
    )


# ============================================================
# SUGESTÃO DE PRODUTOS
# ============================================================

def suggest_products(
    available_limit: float,
    score: float,
    confidence: float,
    products: List[Dict[str, Any]],
    tiers: Optional[
        List[Dict[str, Any]]
    ] = None,
) -> List[Dict[str, Any]]:

    available = money(
        available_limit
    )

    if (
        available <= 0
        or not products
    ):
        return []

    suggestions = []

    for product in products:

        name = str(
            product.get(
                "name",
                "Produto",
            )
        )

        unit_price = money(
            product.get(
                "unit_price",
                0,
            )
        )

        units_per_box = max(
            1,
            int(
                product.get(
                    "units_per_box",
                    1,
                )
            ),
        )

        if unit_price <= 0:
            continue

        calculation = max_boxes_within_limit(
            available,
            unit_price,
            units_per_box,
            tiers,
        )

        if calculation["boxes"] <= 0:
            continue

        suggestions.append(
            {
                "name": name,
                "boxes": calculation["boxes"],
                "units": calculation["units"],
                "unit_price": unit_price,
                "gross": calculation["gross"],
                "discount_rate": calculation[
                    "discount_rate"
                ],
                "discount_value": calculation[
                    "discount_value"
                ],
                "net": calculation["net"],
                "box_value": money(
                    calculation["net"]
                    / calculation["boxes"]
                ),
                "used": calculation["net"],
                "remaining": money(
                    available
                    - calculation["net"]
                ),
            }
        )

    return suggestions


# ============================================================
# CÁLCULO SIMPLES DE CAIXAS
# ============================================================

def box_calc(
    limit: float,
    unit_price: float,
    units_per_box: int = 9,
) -> Dict[str, Any]:

    unit_price = money(
        unit_price
    )

    units_per_box = max(
        1,
        int(units_per_box),
    )

    box_value = money(
        unit_price
        * units_per_box
    )

    if box_value <= 0:

        boxes = 0

    else:

        boxes = math.floor(
            max(
                0.0,
                limit,
            )
            / box_value
        )

    used = money(
        boxes
        * box_value
    )

    remaining = money(
        max(
            0.0,
            limit - used,
        )
    )

    return {
        "boxes": boxes,
        "units": boxes * units_per_box,
        "box_value": box_value,
        "used": used,
        "remaining": remaining,
    }
