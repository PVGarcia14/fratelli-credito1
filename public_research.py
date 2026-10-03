from __future__ import annotations
from datetime import datetime
from urllib.parse import quote, urlparse, urljoin
from typing import Dict, Any, List
import re
import os
import requests
from bs4 import BeautifulSoup
try:
    from engine import clean_cnpj, parse_public_page, normalize_text
except ImportError:
    from .engine import clean_cnpj, parse_public_page, normalize_text

UA = "Mozilla/5.0 (compatible; Fratelli-B2B-Credit/6.0; +public-web-research)"

DIRECT_SOURCES = [
    ("CNPJ.BIZ", "https://cnpj.biz/{cnpj}"),
    ("CNPJ.ai", "https://cnpj.ai/{cnpj}"),
]
SEARCH_TARGETS = [
    ("Google — CNPJ", "https://www.google.com/search?q={q}"),
    ("DuckDuckGo — CNPJ", "https://html.duckduckgo.com/html/?q={q}"),
    ("Google — processos", "https://www.google.com/search?q={q}+processos"),
    ("Google — notícias", "https://www.google.com/search?q={q}+notícias"),
]
JUSBRASIL_SEARCH = "https://www.jusbrasil.com.br/consulta-processual/?q={q}"

MANUAL_PUBLIC_SOURCES = [
    ("Receita Federal / Redesim", "https://www.gov.br/empresas-e-negocios/pt-br/redesim"),
    ("SINTEGRA", "http://www.sintegra.gov.br/"),
    ("Portal da Transparência", "https://portaldatransparencia.gov.br/"),
    ("Diário Oficial da União", "https://www.in.gov.br/"),
    ("CNJ", "https://www.cnj.jus.br/"),
    ("Junta Comercial — pesquisa manual", "https://www.gov.br/empresas-e-negocios/pt-br/redesim"),
]


def fetch(url: str) -> Dict[str, Any]:
    started = datetime.now().isoformat(timespec="seconds")
    try:
        r = requests.get(url, timeout=12, headers={"User-Agent": UA}, allow_redirects=True)
        if r.status_code >= 400:
            return {"ok":False,"status":r.status_code,"url":url,"text":"","started":started}
        soup = BeautifulSoup(r.text, "html.parser")
        image_urls = []
        og = soup.find("meta", attrs={"property": "og:image"})
        if og and og.get("content"):
            image_urls.append(urljoin(r.url, og.get("content")))
        for img in soup.find_all("img", src=True):
            u = urljoin(r.url, img.get("src"))
            if u.startswith(("http://", "https://")) and u not in image_urls:
                image_urls.append(u)
            if len(image_urls) >= 8:
                break
        links = []
        for a in soup.find_all("a", href=True):
            u = urljoin(r.url, a.get("href"))
            if u.startswith(("http://", "https://")) and u not in links:
                links.append(u)
            if len(links) >= 80:
                break
        for tag in soup(["script","style","noscript","svg"]):
            tag.decompose()
        text = " ".join(soup.stripped_strings)
        return {"ok":True,"status":r.status_code,"url":r.url,"text":text[:300000],"started":started,
                "images": image_urls, "links": links}
    except Exception as e:
        return {"ok":False,"status":None,"url":url,"text":"","error":str(e),"started":started}



def extract_partners(text: str) -> List[Dict[str, str]]:
    """Extract QSA names/roles from public company pages when exposed.

    Handles common CNPJ.ai/CNPJ.biz/Receita QSA layouts, including
    "Nome/Nome Empresarial" + "Qualificação" pairs and inline role labels.
    """
    clean = normalize_text(text)
    out: List[Dict[str, str]] = []

    def add(name: str, role: str = "Não identificada", source_hint: str = ""):
        name = normalize_text(name).strip(" |:-")
        role = normalize_text(role).strip(" |:-") or "Não identificada"
        if len(name) < 5:
            return
        bad = ("quadro de sócios", "nome empresarial", "capital social", "consulta", "receita federal")
        if any(x in name.lower() for x in bad):
            return
        if not any(x["name"].upper() == name.upper() for x in out):
            out.append({"name": name, "role": role})

    # Receita-style blocks: Nome/Nome Empresarial ... Qualificação ...
    for m in re.finditer(
        r"Nome/Nome Empresarial\s*[:|]?\s*([A-ZÀ-Ú][A-ZÀ-Úa-zà-ú.'-]+(?:\s+[A-ZÀ-Úa-zà-ú.'-]+){1,12})\s+Qualifica[cç][aã]o\s*[:|]?\s*([^|]+?)(?=\s+Nome/Nome Empresarial|\s+Capital Social|\s+Para informa[cç]|$)",
        clean, re.I
    ):
        add(m.group(1), m.group(2))

    # Common inline forms: NAME - Sócio-Administrador
    for m in re.finditer(
        r"\b([A-ZÀ-Ú][A-ZÀ-Úa-zà-ú.'-]+(?:\s+[A-ZÀ-Úa-zà-ú.'-]+){1,12})\s+-\s+(Sócio-Administrador|Sócio|Administrador|Diretor|Presidente|Gerente)\b",
        clean, re.I
    ):
        add(m.group(1), m.group(2))

    # Label forms: Sócio-Administrador: NAME / Administrador: NAME
    for m in re.finditer(
        r"(Sócio-Administrador|Sócio|Administrador|Diretor|Presidente|Gerente)\s*[:|-]\s*([A-ZÀ-Ú][A-ZÀ-Úa-zà-ú.'-]+(?:\s+[A-ZÀ-Úa-zà-ú.'-]+){1,12})",
        clean, re.I
    ):
        add(m.group(2), m.group(1))

    return out


def jusbrasil_api_key() -> str:
    """Read the optional Jusbrasil API key without hard-coding credentials."""
    try:
        import streamlit as st
        return str(st.secrets.get("JUSBRASIL_API_KEY", "") or "").strip()
    except Exception:
        return os.getenv("JUSBRASIL_API_KEY", "").strip()


def search_jusbrasil_api(document: str, kind: str) -> Dict[str, Any]:
    """Query Jusbrasil Consulta PRO when an API key is configured.

    The official API supports CPF/CNPJ searches. No attempt is made to bypass
    authentication or scrape restricted pages.
    """
    key = jusbrasil_api_key()
    if not key:
        return {
            "source": "Jusbrasil API",
            "query": document,
            "kind": kind,
            "configured": False,
            "available_publicly": False,
            "note": "Integração Jusbrasil API não configurada. Sem API autorizada, o sistema não deve inferir ausência de processos."
        }
    endpoint = f"https://api.jusbrasil.com.br/background-check/lawsuits/{kind}"
    try:
        r = requests.post(
            endpoint,
            headers={"Content-Type": "application/json", "apikey": key},
            json={"documentNumber": clean_cnpj(document), "pagination": {"cursor": "", "size": 100}},
            timeout=20,
        )
        data = r.json() if r.content else {}
        return {
            "source": "Jusbrasil API",
            "query": document,
            "kind": kind,
            "configured": True,
            "available_publicly": True,
            "ok": r.ok,
            "status": r.status_code,
            "data": data,
            "processes": data.get("processos", []) if isinstance(data, dict) else [],
            "pagination": data.get("pagination", {}) if isinstance(data, dict) else {},
        }
    except Exception as e:
        return {
            "source": "Jusbrasil API", "query": document, "kind": kind,
            "configured": True, "available_publicly": False,
            "note": f"Falha na consulta autorizada da API: {e}"
        }

def search_jusbrasil(query: str) -> Dict[str, Any]:
    """Search the publicly accessible Jusbrasil search page as discovery evidence only."""
    q = normalize_text(query)
    url = JUSBRASIL_SEARCH.format(q=quote(q))
    row = fetch(url)
    result = {
        "source": "Jusbrasil — pesquisa pública",
        "query": q,
        "url": row.get("url") or url,
        "ok": bool(row.get("ok")),
        "status": row.get("status"),
        "snippet": " ".join(row.get("text", "").split())[:8000],
        "available_publicly": bool(row.get("ok")),
        "mode": "public_discovery",
    }
    if not row.get("ok"):
        result["note"] = "Fonte não disponível publicamente neste acesso; o sistema não deve inferir ausência de processos."
    return result


def judicial_api_for_cnpj(cnpj: str) -> List[Dict[str, Any]]:
    """Run authorized Jusbrasil API checks for civil/criminal/labor cases."""
    out = []
    for kind in ("civil", "criminal", "trabalhista"):
        out.append(search_jusbrasil_api(cnpj, kind))
    return out

def research_company(cnpj: str) -> Dict[str, Any]:
    c = clean_cnpj(cnpj)
    result = {"queried_at":datetime.now().isoformat(timespec="seconds"),"cnpj":c,"sources":[],"fields":{},"field_sources":{},"conflicts":[],"search_leads":[],"partners":[],"partner_sources":{},"partner_judicial":[],"manual_sources":MANUAL_PUBLIC_SOURCES,"image_candidates":[],"website_candidates":[]}
    if len(c) != 14:
        result["error"] = "CNPJ inválido."
        return result
    all_fields: Dict[str, List[tuple]] = {}
    for name, template in DIRECT_SOURCES:
        row = fetch(template.format(cnpj=c))
        row.update({"source":name,"kind":"direct"})
        if row.get("ok"):
            for img in row.get("images", []):
                if img not in result["image_candidates"]:
                    result["image_candidates"].append({"url": img, "source": name})
            fields = parse_public_page(row.get("text",""))
            row["fields"] = fields
            partners = extract_partners(row.get("text", ""))
            row["partners"] = partners
            for partner in partners:
                if not any(p["name"].upper() == partner["name"].upper() for p in result["partners"]):
                    result["partners"].append(partner)
                result["partner_sources"].setdefault(partner["name"], []).append(name)
            for k,v in fields.items():
                all_fields.setdefault(k,[]).append((name,v))
        result["sources"].append(row)
    # Search pages are treated as discovery evidence, not as authoritative records.
    queries = [c, f'"{c}" empresa']
    for q in queries:
        for name, template in SEARCH_TARGETS[:2]:
            row = fetch(template.format(q=quote(q)))
            row.update({"source":name,"kind":"search"})
            if row.get("ok"):
                snippet = " ".join(row.get("text","").split())[:5000]
                result["search_leads"].append({"source":name,"query":q,"url":row.get("url"),"snippet":snippet})
                for u in row.get("links", []):
                    host = urlparse(u).netloc.lower()
                    if host and not any(x in host for x in ("google.", "duckduckgo.", "bing.", "yahoo.", "jusbrasil.", "cnpj.biz", "cnpj.ai")):
                        if u not in result["website_candidates"]:
                            result["website_candidates"].append(u)
                for img in row.get("images", []):
                    if img not in [x["url"] for x in result["image_candidates"]]:
                        result["image_candidates"].append({"url": img, "source": name})
            result["sources"].append(row)
    for field, vals in all_fields.items():
        result["field_sources"][field] = vals
        unique = {v.strip().upper() for _,v in vals}
        if len(unique) > 1:
            result["conflicts"].append({"field":field,"values":[{"source":s,"value":v} for s,v in vals]})
        # Majority is only a display convenience; conflicts remain visible.
        counts = {}
        for s,v in vals: counts[v] = counts.get(v,0)+1
        result["fields"][field] = max(vals, key=lambda x: counts[x[1]])[1]
    # Jusbrasil: public process research for the company and identified partners.
    jb_queries = []
    if c:
        jb_queries.append(("CNPJ", c))
    for partner in result.get("partners", []):
        jb_queries.append(("Sócio/administrador", partner["name"]))
    for kind, query in jb_queries:
        jb = search_jusbrasil(query)
        jb["target_type"] = kind
        result["partner_judicial"].append(jb)
    # Authorized API: automatic structured process retrieval for the company CNPJ.
    result["jusbrasil_api"] = judicial_api_for_cnpj(c)
    # Names are always collected automatically when public QSA evidence exposes them.
    # If a future authorized name-search API is configured, this list is the input set.
    result["automatic_qsa"] = list(result.get("partners", []))
    result["successful_sources"] = sum(1 for x in result["sources"] if x.get("ok"))
    result["source_count"] = len(result["sources"])
    result["confidence"] = None
    return result


def search_person(name: str) -> List[Dict[str, Any]]:
    if not name or len(name.strip()) < 5:
        return []
    out=[]
    for label, template in [
        ("Jusbrasil — processos", JUSBRASIL_SEARCH),
        ("Google — nome + processos", "https://www.google.com/search?q={q}+processos"),
        ("DuckDuckGo — nome", "https://html.duckduckgo.com/html/?q={q}"),
        ("Google — nome + empresa", "https://www.google.com/search?q={q}+empresa"),
    ]:
        row=fetch(template.format(q=quote('"'+name.strip()+'"')))
        out.append({"source":label,"url":row.get("url"),"ok":row.get("ok"),"status":row.get("status"),"snippet":" ".join(row.get("text","").split())[:4000]})
    return out
