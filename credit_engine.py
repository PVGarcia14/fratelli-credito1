from __future__ import annotations
import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple
from config import LIMIT_BANDS, MISSING_FACTOR

WEIGHTS = {
    "Cadastro e existência": 15,
    "Estrutura empresarial": 15,
    "Histórico público": 20,
    "Capacidade empresarial": 20,
    "Confiabilidade das informações": 10,
    "Histórico comercial identificado": 20,
}


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
        status = "SEM INFORMAÇÃO"
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
            exposure: float = 0.0) -> Dict[str, Any]:
    fields = dossier.get("fields", {})
    conflicts = dossier.get("conflicts", [])
    successful = dossier.get("successful_sources", 0)
    total = dossier.get("source_count", 0)
    critical_flags = dossier.get("critical_flags", [])
    partners = dossier.get("partners", [])

    # 1. Registration / existence
    status = str(fields.get("Situação cadastral", "")).upper()
    age = age_years(fields.get("Data de abertura"))
    reg = None
    details=[]
    if status:
        if "ATIVA" in status: reg = 8
        elif any(x in status for x in ("INAPTA", "BAIXADA", "SUSPENSA")): reg = 1
        else: reg = 4
        if age is not None: reg += min(4, max(0, age / 2))
        for k in ("Endereço", "CNAE principal", "Natureza jurídica"):
            if fields.get(k): reg += 1
        reg = min(15, reg)
        details.append(f"Situação: {status}.")
        if age is not None: details.append(f"Idade estimada: {age:.1f} anos.")
    criteria=[]
    criteria.append(criterion("Cadastro e existência",15,reg,"Situação, idade e campos cadastrais encontrados.",details))

    # 2. Structure: evidence coverage, not arbitrary fixed score.
    structural = ["Capital social","Porte","CNAE principal","Natureza jurídica"]
    found = sum(bool(fields.get(k)) for k in structural) + min(2, len(partners))
    struct = min(15, found / 6 * 12)
    if conflicts: struct -= min(3, len(conflicts)*0.75)
    criteria.append(criterion("Estrutura empresarial",15,struct if found else None,
                              f"{found} sinais estruturais identificados.",
                              ["Sócios identificados: %d" % len(partners), "Divergências: %d" % len(conflicts)]))

    # 3. Public history: critical events reduce score; absence remains uncertainty.
    hist = None
    if successful:
        hist = 14.0
        hist -= min(8.0, len(critical_flags)*3.0)
        hist -= min(4.0, len(conflicts)*0.8)
        if dossier.get("public_presence"): hist += 2
        hist = max(0, min(20, hist))
    criteria.append(criterion("Histórico público",20,hist,
                              "Eventos públicos e sinais de risco encontrados nas fontes consultadas.",
                              critical_flags or ["Nenhum evento crítico foi identificado nas fontes que responderam; isso não prova ausência em todas as bases."]))

    # 4. Capacity: use only observed fields; no invented revenue.
    cap = None
    cap_details=[]
    if successful:
        cap = 5.0
        if fields.get("Porte"): cap += 3
        if fields.get("Capital social"): cap += 3
        if fields.get("CNAE principal"): cap += 2
        if dossier.get("public_presence"): cap += 3
        if dossier.get("contracts_count", 0): cap += min(2, dossier["contracts_count"]*0.5)
        if overdue > 0: cap -= min(6, overdue / 10000)
        cap = max(0, min(20, cap))
        cap_details.append("Faturamento não identificado em fonte pública confiável." if not dossier.get("verified_revenue") else "Faturamento público verificado disponível.")
    criteria.append(criterion("Capacidade empresarial",20,cap,"Porte, atividade, estrutura e presença pública observáveis.",cap_details))

    # 5. Reliability: independent successful sources vs conflicts.
    rel=None
    if total or successful:
        ratio = successful / max(1,total)
        rel = min(10, 5*ratio + min(5, len(fields)/10))
        rel -= min(4, len(conflicts)*0.8)
        rel = max(0,min(10,rel))
    criteria.append(criterion("Confiabilidade das informações",10,rel,
                              f"Fontes que responderam: {successful}/{total}; divergências: {len(conflicts)}."))

    # 6. Commercial history: internal data is more useful than public assumptions.
    commercial=None
    if internal_payment_status == "Em dia": commercial=18
    elif internal_payment_status == "Atrasos": commercial=8
    elif internal_payment_status == "Inadimplente": commercial=0
    elif dossier.get("commercial_evidence"): commercial=10
    criteria.append(criterion("Histórico comercial identificado",20,commercial,
                              "Histórico interno e/ou evidências comerciais identificadas.",
                              [f"Status interno: {internal_payment_status}", f"Exposição: R$ {exposure:,.2f}".replace(',','X').replace('.',',').replace('X','.'), f"Atrasado: R$ {overdue:,.2f}".replace(',','X').replace('.',',').replace('X','.')]))

    score=round(sum(x["points"] for x in criteria),2)
    coverage=round(sum(1 for x in criteria if x["status"]=="COM EVIDÊNCIA")/len(criteria)*100,1)
    confidence=round(max(0,min(100, (successful/max(1,total))*55 + min(35, len(fields)*2) + max(0,10-len(conflicts)*2))),1) if total else 0
    limit, policy_decision=score_limit(score, requested, confidence/100, bool(critical_flags))
    # Internal exposure reduces available room; never create a negative limit.
    available=max(0, money(limit-exposure))
    order=simulate_order_decision(requested, available, score, confidence, bool(critical_flags))
    positives=[]; attentions=[]
    for x in criteria:
        if x["points"] >= x["max"]*0.7: positives.append(f"{x['name']}: {x['evidence']}")
        if x["status"]=="SEM INFORMAÇÃO" or x["points"] < x["max"]*0.4: attentions.append(f"{x['name']}: informação limitada ou sinal de atenção.")
    attentions += [f"Divergência: {c.get('field')}" for c in conflicts]
    if critical_flags: attentions += [f"Alerta crítico: {x}" for x in critical_flags]
    return {"score":score,"confidence":confidence,"coverage":coverage,"criteria":criteria,
            "limit":money(limit),"exposure":money(exposure),"available":money(available),
            "policy_decision":policy_decision,"order":order,"positives":positives,
            "attentions":attentions,"risk_band":risk_band(score),"critical":bool(critical_flags)}


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


def box_calc(limit: float, unit_price: float, units_per_box: int=9) -> Dict[str,Any]:
    bv=money(unit_price)*max(1,int(units_per_box))
    boxes=0 if bv<=0 else math.floor((max(0,limit)+1e-9)/bv)
    return {"boxes":boxes,"units":boxes*units_per_box,"box_value":money(bv),"used":money(boxes*bv),"remaining":money(limit-boxes*bv)}
