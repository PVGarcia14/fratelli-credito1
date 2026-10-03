from __future__ import annotations
import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple
from config import LIMIT_BANDS, MISSING_FACTOR

# Four decision pillars. Commercial history is a modifier, not a fifth penalty bucket.
WEIGHTS = {
    "Legitimidade e cadastro": 20,
    "Tempo de atividade": 10,
    "Estrutura e capacidade": 25,
    "Histórico público e risco": 20,
    "Qualidade das evidências": 25,
}
# Missing information earns only the configured partial factor; it is never treated as a positive fact.
MISSING_FACTOR = 0.25


def clean_cnpj(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def validate_cnpj(value: str) -> Tuple[bool, str]:
    c = clean_cnpj(value)
    if len(c) != 14 or c == c[0] * 14:
        return False, "CNPJ inválido: informe 14 dígitos."
    nums = list(map(int, c))
    for pos, weights in ((12, [5,4,3,2,9,8,7,6,5,4,3,2]), (13, [6,5,4,3,2,9,8,7,6,5,4,3,2])):
        s = sum(nums[i] * weights[i] for i in range(len(weights)))
        digit = (s * 10) % 11
        if digit == 10: digit = 0
        if nums[pos] != digit:
            return False, "CNPJ inválido: dígitos verificadores não conferem."
    return True, c


def parse_date(value: Any) -> Optional[date]:
    if not value: return None
    s = str(value).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try: return datetime.strptime(s[:19], fmt).date()
        except ValueError: pass
    return None


def age_years(opening: Any, today: Optional[date] = None) -> Optional[float]:
    d = parse_date(opening)
    if not d: return None
    t = today or date.today()
    return round((t - d).days / 365.2425, 2)


def money(v: float) -> float: return round(max(0.0, float(v or 0)), 2)


def score_limit(score: float, requested: float = 0.0, confidence: float = 0.0,
                critical: bool = False) -> Tuple[float, str]:
    s = max(0.0, min(100.0, score))
    if critical or s < 25: return 0.0, "RECUSAR"
    for lo, hi, limit in LIMIT_BANDS[1:]:
        if lo <= s < hi: return limit, "APROVAR COM LIMITE"
    # >70 is deliberately individualized, with a conservative formula tied to evidence quality.
    base = max(20000.0, min(100000.0, 20000.0 + (s - 70.0) * 2500.0))
    evidence_cap = base * max(0.25, min(1.0, confidence))
    if requested > 0:
        limit = min(base, max(20000.0, requested))
        limit = min(limit, max(20000.0, evidence_cap))
    else:
        limit = min(base, evidence_cap)
    return money(limit), "APROVAR" if requested <= limit or requested <= 0 else "APROVAR COM LIMITE"


def criterion(name: str, max_points: float, points: Optional[float], evidence: str,
              details: Optional[List[str]] = None) -> Dict[str, Any]:
    if points is None:
        p = max_points * MISSING_FACTOR
        status = "INFORMAÇÃO PARCIAL"
    else:
        p = max(0.0, min(max_points, points))
        status = "COM EVIDÊNCIA"
    return {"name": name, "max": max_points, "points": round(p,2), "status": status,
            "evidence": evidence, "details": details or []}

def field_values(dossier: Dict[str, Any], key: str) -> List[Tuple[str, Any]]:
    return [(src, vals.get(key)) for src, vals in dossier.get("source_records", {}).items()
            if vals.get(key) not in (None, "", [], {})]

def analyze(dossier: Dict[str, Any], requested: float = 0.0,
            internal_payment_status: str = "Sem histórico", overdue: float = 0.0,
            exposure: float = 0.0, payment_risk: float = 0.0) -> Dict[str, Any]:
    fields = dossier.get("fields", {})
    conflicts = dossier.get("conflicts", [])
    successful = dossier.get("successful_sources", 0)
    total = dossier.get("source_count", 0)
    critical_flags = list(dossier.get("critical_flags", []))
    partners = dossier.get("partners", [])
    status = str(fields.get("Situação cadastral", "")).upper()
    if any(x in status for x in ("INAPTA", "BAIXADA", "SUSPENSA")) and not critical_flags:
        critical_flags.append(f"Situação cadastral crítica: {status}.")
    age = age_years(fields.get("Data de abertura"))
    criteria=[]

    # 1) Legitimidade/cadastro: status and identity fields.
    reg=None; details=[]
    if status or fields:
        reg = 12.0 if "ATIVA" in status else 3.0 if any(x in status for x in ("INAPTA","BAIXADA","SUSPENSA")) else 7.0
        reg += min(4.0, sum(bool(fields.get(k)) for k in ("Razão social","CNPJ","Endereço","CNAE principal","Natureza jurídica")) * 0.8)
        reg=min(20.0,reg)
        details=[f"Situação: {status or 'não identificada'}."]
    criteria.append(criterion("Legitimidade e cadastro",20,reg,"Existência, situação e consistência dos dados cadastrais.",details))

    # 2) Time in business is an independent criterion.
    # User policy: <1 year = 10%; 1–3 years = 60%; >3 years = 100%.
    age_points=None; age_details=[]
    if age is not None:
        if age < 1.0:
            factor=0.10; faixa="menos de 1 ano"
        elif age <= 3.0:
            factor=0.60; faixa="entre 1 e 3 anos"
        else:
            factor=1.00; faixa="acima de 3 anos"
        age_points=10.0*factor
        age_details=[f"Idade estimada: {age:.1f} anos.", f"Faixa: {faixa}.", f"Pontuação aplicada: {factor*100:.0f}% do critério."]
    criteria.append(criterion("Tempo de atividade",10,age_points,"Tempo desde a data de abertura do CNPJ.",age_details))

    # 3) Structure/capacity: observable fields, without inventing revenue.
    struct=None; sdet=[]
    if successful or fields:
        struct=8.0
        struct += min(7.0, sum(bool(fields.get(k)) for k in ("Capital social","Porte","CNAE principal","Natureza jurídica"))*1.75)
        struct += min(5.0, len(partners)*1.5)
        struct += 2.0 if dossier.get("public_presence") else 0.0
        struct += 3.0 if fields.get("Capital social") else 0.0
        struct=max(0,min(25,struct))
        sdet=[f"Sócios identificados: {len(partners)}.", "Faturamento não identificado em fonte pública confiável." if not dossier.get("verified_revenue") else "Faturamento público verificado disponível."]
    criteria.append(criterion("Estrutura e capacidade",25,struct,"Porte, capital, atividade, estrutura e presença pública observáveis.",sdet))

    # 4) Public history/risk. Lack of negative evidence is not treated as a positive claim.
    hist=None; hdet=[]
    if successful or fields:
        hist=16.0
        hist -= min(10.0,len(critical_flags)*5.0)
        hist -= min(5.0,len(conflicts)*1.0)
        if dossier.get("public_presence"): hist += 2.0
        hist=max(0,min(20,hist))
        hdet=critical_flags or ["Nenhum evento crítico identificado nas fontes que responderam; isso não prova ausência em todas as bases."]
    criteria.append(criterion("Histórico público e risco",20,hist,"Sinais públicos de risco, status e divergências entre fontes.",hdet))

    # 5) Evidence quality. This is where source coverage belongs, so missing sources do not get counted twice.
    rel=None
    if total or successful:
        ratio=successful/max(1,total)
        rel=min(25.0, 10.0*ratio + min(10.0,len(fields)*1.5) + max(0.0,5.0-len(conflicts)*1.5))
        rel=max(0,min(25,rel))
    criteria.append(criterion("Qualidade das evidências",25,rel,f"Fontes que responderam: {successful}/{total}; divergências: {len(conflicts)}."))

    score=round(sum(x["points"] for x in criteria),2)
    # Internal payment behavior is a small, explicit modifier rather than a whole criterion.
    commercial_modifier=0.0
    if internal_payment_status == "Em dia": commercial_modifier=5.0
    elif internal_payment_status == "Atrasos": commercial_modifier=-3.0
    elif internal_payment_status == "Inadimplente": commercial_modifier=-8.0
    if overdue > 0: commercial_modifier -= min(5.0, overdue/10000.0)
    score=round(max(0,min(100,score+commercial_modifier)),2)

    coverage=round(sum(1 for x in criteria if x["status"]=="COM EVIDÊNCIA")/len(criteria)*100,1)
    confidence=round(max(0,min(100,(successful/max(1,total))*65 + min(30,len(fields)*2.5) + max(0,5-len(conflicts)))),1) if total else 0
    limit,policy_decision=score_limit(score,requested,confidence/100,bool(critical_flags))
    # Longer terms carry a small policy haircut; the user can configure this in config.py.
    if payment_risk>0 and limit>0:
        limit=money(limit*(1-payment_risk))
    available=max(0,money(limit-exposure))
    order=simulate_order_decision(requested,available,score,confidence,bool(critical_flags))
    positives=[]; attentions=[]
    for x in criteria:
        if x["points"] >= x["max"]*0.7: positives.append(f"{x['name']}: {x['evidence']}")
        if x["status"]=="INFORMAÇÃO PARCIAL" or x["points"] < x["max"]*0.4: attentions.append(f"{x['name']}: informação limitada ou sinal de atenção.")
    if commercial_modifier>0: positives.append(f"Histórico interno: +{commercial_modifier:.1f} pontos.")
    elif commercial_modifier<0: attentions.append(f"Histórico interno: {commercial_modifier:.1f} pontos.")
    attentions += [f"Divergência: {c.get('field')}" for c in conflicts]
    if critical_flags: attentions += [f"Alerta crítico: {x}" for x in critical_flags]
    return {"score":score,"confidence":confidence,"coverage":coverage,"criteria":criteria,
            "commercial_modifier":commercial_modifier,"limit":money(limit),"exposure":money(exposure),"available":money(available),
            "policy_decision":policy_decision,"order":order,"positives":positives,"attentions":attentions,
            "risk_band":risk_band(score),"critical":bool(critical_flags)}

def simulate_order_decision(requested: float, available: float, score: float, confidence: float, critical: bool) -> Dict[str,Any]:
    req=money(requested); avail=money(available)
    if req<=0: return {"decision":"SEM PEDIDO","requested":0,"excess":0,"pct_excess":0,"reason":"Informe o valor do pedido para testar a operação."}
    excess=max(0,req-avail)
    pct=round(excess/avail*100,2) if avail>0 else 100.0
    if critical or score<25:
        dec="RECUSAR"; reason="Há fator crítico ou score abaixo do piso de crédito."
    elif req<=avail:
        dec="APROVAR"; reason="Pedido dentro do limite disponível para a operação."
    elif score>70 and confidence>=70 and excess/req<=0.20:
        dec="ANÁLISE EXCEPCIONAL"; reason="Pedido acima do limite, mas os indicadores permitem análise complementar de exceção."
    else:
        dec="APROVAR COM LIMITE"; reason="Pedido excede o limite; reduzir o pedido ou submeter exceção."
    return {"decision":dec,"requested":req,"excess":money(excess),"pct_excess":pct,"reason":reason}


def risk_band(score: float) -> str:
    if score < 25: return "ALTO RISCO"
    if score < 45: return "RISCO ELEVADO"
    if score < 55: return "RISCO MODERADO"
    if score <= 70: return "RISCO CONTROLADO"
    return "RISCO INDIVIDUALIZADO"



def suggest_products(available_limit: float, score: float, confidence: float, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return a conservative, configurable product/box suggestion for a generic B2B catalog.
    Suggestions never exceed the available credit limit.
    """
    if available_limit <= 0 or not products:
        return []
    eligible = []
    # Higher-quality evidence unlocks a broader configurable catalog; this is a policy rule, not a product valuation.
    if score < 35 or confidence < 50:
        max_items = 1
    elif score < 55 or confidence < 65:
        max_items = min(2, len(products))
    else:
        max_items = min(3, len(products))
    for p in products[:max_items]:
        price = money(p.get("unit_price", 0))
        upb = max(1, int(p.get("units_per_box", 1)))
        box_value = money(price * upb)
        if box_value <= 0:
            continue
        boxes = math.floor(available_limit / box_value)
        if boxes > 0:
            eligible.append({
                "name": p.get("name", "Produto"),
                "boxes": boxes,
                "units": boxes * upb,
                "box_value": box_value,
                "used": money(boxes * box_value),
                "remaining": money(available_limit - boxes * box_value),
            })
    return eligible

def box_calc(limit: float, unit_price: float, units_per_box: int=9) -> Dict[str,Any]:
    bv=money(unit_price)*max(1,int(units_per_box))
    boxes=0 if bv<=0 else math.floor((max(0,limit)+1e-9)/bv)
    return {"boxes":boxes,"units":boxes*units_per_box,"box_value":money(bv),"used":money(boxes*bv),"remaining":money(limit-boxes*bv)}
