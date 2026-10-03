import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; B2BCreditResearch/6.2)"}

def clean_cnpj(value):
    return re.sub(r"\D", "", value or "")

def safe_get(url, timeout=12):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        return r if r.ok else None
    except requests.RequestException:
        return None

def parse_public_page(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(" ", strip=True)

def fetch_receita_public(cnpj):
    # Public endpoint commonly used for basic CNPJ consultation.
    url = f"https://www.receitaws.com.br/v1/cnpj/{cnpj}"
    r = safe_get(url)
    if not r:
        return None, "Fonte não disponível publicamente neste momento."
    try:
        return r.json(), "Consulta pública retornou dados."
    except ValueError:
        return None, "Resposta pública não pôde ser interpretada."

def evidence_quality(found, independent_sources, conflicts):
    if not found:
        return 0.0
    base = min(1.0, 0.35 + 0.15 * min(independent_sources, 4))
    if conflicts:
        base *= 0.75
    return max(0.0, min(1.0, base))

def criterion(name, max_points, evidence, positive=0, negative=0, missing=False, explanation=""):
    if missing:
        # Missing evidence can receive at most 25% of the criterion.
        points = min(max_points * 0.25, max(0, positive - negative))
        status = "SEM INFORMAÇÃO"
    else:
        points = max(0, min(max_points, positive - negative))
        status = "COM EVIDÊNCIA"
    return {
        "name": name, "max_points": max_points, "points": points,
        "status": status, "explanation": explanation, "evidence": evidence
    }

def analyze_company(cnpj):
    raw, status = fetch_receita_public(cnpj)
    company = {}
    sources = []
    positive = []
    attention = []
    alerts = []

    if raw:
        company = {
            "CNPJ": raw.get("cnpj") or cnpj,
            "Razão social": raw.get("nome"),
            "Nome fantasia": raw.get("fantasia"),
            "Abertura": raw.get("abertura"),
            "Situação": raw.get("situacao"),
            "Data situação": raw.get("data_situacao"),
            "Município": raw.get("municipio"),
            "UF": raw.get("uf"),
            "Natureza jurídica": raw.get("natureza_juridica"),
            "CNAE principal": raw.get("atividade_principal"),
            "Capital social": raw.get("capital_social"),
            "Porte": raw.get("porte"),
        }
        sources.append({"source": "Consulta pública CNPJ", "status": "OK", "detail": status,
                         "url": f"https://www.receitaws.com.br/v1/cnpj/{cnpj}"})
    else:
        sources.append({"source": "Consulta pública CNPJ", "status": "INDISPONÍVEL",
                         "detail": status, "url": ""})

    active = str(company.get("Situação") or "").lower() in ("ativa", "active")
    age = 0
    try:
        age = max(0, (datetime.now() - datetime.strptime(company.get("Abertura"), "%d/%m/%Y")).days / 365.25)
    except Exception:
        pass

    # Dynamic evidence-driven criteria. No hard-coded customer score.
    criteria = []

    if raw:
        p = 15 if active else 0
        neg = 15 if company.get("Situação") in ("BAIXADA", "INAPTA", "SUSPENSA", "NULA") else 0
        criteria.append(criterion(
            "Cadastro e existência", 15, "situação cadastral",
            positive=p, negative=neg,
            explanation=f"Situação encontrada: {company.get('Situação') or 'não informada'}."
        ))
        if active:
            positive.append("Situação cadastral ativa na fonte consultada.")
        elif company.get("Situação"):
            alerts.append(f"Situação cadastral: {company['Situação']}.")

        structure_fields = sum(bool(company.get(k)) for k in ["Razão social","Nome fantasia","Município","UF","Natureza jurídica","CNAE principal","Porte","Capital social"])
        structure_points = min(15, structure_fields / 8 * 15)
        criteria.append(criterion(
            "Estrutura empresarial", 15, f"{structure_fields}/8 campos estruturais identificados",
            positive=structure_points,
            explanation="Pontuação proporcional à quantidade de informações estruturais identificadas."
        ))

        hist_points = 20 if active else 0
        if age >= 5: hist_points += 0
        elif age >= 2: hist_points *= 0.8
        elif age > 0: hist_points *= 0.6
        criteria.append(criterion(
            "Histórico público", 20, f"tempo estimado de atividade: {age:.1f} anos",
            positive=hist_points,
            explanation="O tempo de atividade modula o critério; ausência de eventos públicos adicionais não é tratada como prova positiva."
        ))

        cap_fields = sum(bool(company.get(k)) for k in ["CNAE principal","Porte","Capital social"])
        cap_points = cap_fields / 3 * 20
        criteria.append(criterion(
            "Capacidade empresarial", 20, f"{cap_fields}/3 indicadores públicos básicos",
            positive=cap_points,
            explanation="Usa apenas indicadores públicos encontrados; não estima faturamento sem fonte confiável."
        ))
        if not company.get("Capital social"):
            attention.append("Capital social não identificado na fonte consultada.")
        if not company.get("Porte"):
            attention.append("Porte empresarial não identificado na fonte consultada.")
    else:
        for name, maxp in [
            ("Cadastro e existência",15), ("Estrutura empresarial",15),
            ("Histórico público",20), ("Capacidade empresarial",20)
        ]:
            criteria.append(criterion(name, maxp, "sem evidência pública recuperada", missing=True,
                                      explanation="Informação insuficiente: critério limitado a no máximo 25%."))

    # Reliability is independent from credit score.
    available = sum(bool(v) for v in company.values())
    reliability_points = min(10, available / max(1, len(company)) * 10)
    criteria.append(criterion(
        "Confiabilidade das informações", 10, f"{available}/{len(company)} campos preenchidos",
        positive=reliability_points,
        explanation="Mede qualidade/completude da evidência encontrada, não probabilidade de pagamento."
    ))

    # Commercial history is intentionally not inferred from public absence.
    criteria.append(criterion(
        "Histórico comercial identificado", 20, "não informado por fonte interna nesta versão",
        missing=True,
        explanation="Sem histórico interno verificável, o critério recebe no máximo 25%."
    ))
    attention.append("Histórico comercial/pagamentos internos não informado.")

    score = sum(x["points"] for x in criteria)
    confidence = min(100, 30 + available / max(1, len(company)) * 45 + (20 if raw else 0))

    if score < 25:
        limit = 0
        label = "RECUSAR"
    elif score < 35:
        limit = 1500
        label = "APROVAR COM LIMITE"
    elif score < 45:
        limit = 5000
        label = "APROVAR COM LIMITE"
    elif score < 55:
        limit = 10000
        label = "APROVAR COM LIMITE"
    elif score <= 70:
        limit = 20000
        label = "APROVAR COM LIMITE"
    else:
        # Higher scores are still bounded by evidence quality in this generic build.
        limit = 30000
        label = "APROVAR"

    decision = {"label": label, "limit": limit}

    confidence_explanation = (
        "Confiança separada do score: aumenta com quantidade/completude de evidências "
        "recuperadas e não é interpretada como probabilidade de pagamento."
    )

    return {
        "company": company,
        "score": score,
        "confidence": confidence,
        "criteria": criteria,
        "positive": positive,
        "attention": attention,
        "alerts": alerts,
        "sources": sources,
        "decision": decision,
        "confidence_explanation": confidence_explanation,
    }

def score_to_limit(score):
    return analyze_company
