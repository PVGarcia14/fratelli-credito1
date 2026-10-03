from __future__ import annotations
import re, time
from typing import Any, Dict, List
from urllib.parse import quote
import requests
from bs4 import BeautifulSoup
from credit_engine import clean_cnpj

TIMEOUT=12
HEADERS={"User-Agent":"Mozilla/5.0 (compatible; B2BCreditResearch/6.3)"}

# Public sources only. Each adapter is isolated so one failure cannot poison the dossier.
SOURCE_URLS=[
    ("ReceitaWS", "https://www.receitaws.com.br/v1/cnpj/{cnpj}"),
    ("CNPJ.BIZ", "https://cnpj.biz/{cnpj}"),
    ("CNPJ.ai", "https://cnpj.ai/{cnpj}"),
    ("Casa dos Dados", "https://casadosdados.com.br/solucao/cnpj/{cnpj}"),
    ("Econodata", "https://www.econodata.com.br/consulta-empresa/{cnpj}"),
]

FIELD_ALIASES={
    "razao":"Razão social","nome":"Nome fantasia","nome_fantasia":"Nome fantasia",
    "abertura":"Data de abertura","data_abertura":"Data de abertura","situacao":"Situação cadastral",
    "natureza_juridica":"Natureza jurídica","capital_social":"Capital social","porte":"Porte",
    "cnae":"CNAE principal","logradouro":"Endereço","endereco":"Endereço","bairro":"Bairro",
    "municipio":"Município/UF","cep":"CEP"
}

def _json_fields(obj: Dict[str,Any])->Dict[str,Any]:
    out={}
    for k,v in obj.items():
        if k in FIELD_ALIASES and v not in (None,""): out[FIELD_ALIASES[k]]=v
    # ReceitaWS nested fields
    mapping={"nome":"Razão social","fantasia":"Nome fantasia","abertura":"Data de abertura",
             "situacao":"Situação cadastral","natureza_juridica":"Natureza jurídica",
             "capital_social":"Capital social","porte":"Porte","logradouro":"Endereço",
             "bairro":"Bairro","municipio":"Município","uf":"UF","cep":"CEP"}
    for k,dest in mapping.items():
        if obj.get(k) not in (None,""): out[dest]=obj[k]
    if obj.get("municipio") and obj.get("uf"): out["Município/UF"]=f"{obj['municipio']}/{obj['uf']}"
    if obj.get("atividade_principal") and isinstance(obj["atividade_principal"],list) and obj["atividade_principal"]:
        a=obj["atividade_principal"][0]; out["CNAE principal"]=f"{a.get('code','')} - {a.get('text','')}".strip(" -")
    return out

def _html_fields(html:str)->Dict[str,Any]:
    text=re.sub(r"\s+"," ",BeautifulSoup(html,"html.parser").get_text(" ",strip=True))
    def m(pats):
        for p in pats:
            x=re.search(p,text,re.I)
            if x:return x.group(1).strip(" |:")
    out={}
    for key,pats in {
      "Razão social":[r"Raz[aã]o Social\s*[:|]?\s*([^|]{3,120}?)(?=\s+Nome Fantasia|\s+CNPJ|\s+Data)"],
      "Nome fantasia":[r"Nome Fantasia\s*[:|]?\s*([^|]{2,100}?)(?=\s+Data|\s+CNPJ|\s+Porte)"],
      "Data de abertura":[r"Data (?:da )?Abertura\s*[:|]?\s*(\d{2}/\d{2}/\d{4})"],
      "Situação cadastral":[r"Situa[cç][aã]o Cadastral\s*[:|]?\s*([A-Za-zÀ-ÿ ]{3,30})(?=\s+Data|\s+Capital|\s+Natureza)"],
      "Capital social":[r"Capital Social\s*[:|]?\s*(R\$\s*[0-9\.\,]+)"],
      "Porte":[r"Porte\s*[:|]?\s*([^|]{2,50})(?=\s+Natureza|\s+Capital|\s+CNAE)"],
      "CNAE principal":[r"CNAE principal\s*[:|]?\s*([0-9\.\-/]+\s*[-–]\s*[^|]{4,140})"],
      "Endereço":[r"Logradouro\s*[:|]?\s*([^|]{5,140}?)(?=\s+Bairro|\s+CEP|\s+Munic)"],
      "Bairro":[r"Bairro\s*[:|]?\s*([^|]{2,80})(?=\s+CEP|\s+Munic)"],
      "CEP":[r"CEP\s*[:|]?\s*(\d{5}-\d{3})"],
    }.items():
        v=m(pats)
        if v: out[key]=v
    return out

def fetch(url:str)->Dict[str,Any]:
    try:
        r=requests.get(url,headers=HEADERS,timeout=TIMEOUT)
        if r.status_code>=400:return {"ok":False,"status":r.status_code,"error":f"HTTP {r.status_code}"}
        return {"ok":True,"status":r.status_code,"content_type":r.headers.get("content-type",""),"text":r.text}
    except requests.RequestException as e:
        return {"ok":False,"status":None,"error":str(e)}

def research_company(cnpj:str)->Dict[str,Any]:
    c=clean_cnpj(cnpj)
    records={}; source_status=[]; all_fields={}; field_sources={}
    for name,template in SOURCE_URLS:
        url=template.format(cnpj=c)
        res=fetch(url)
        row={"source":name,"url":url,"ok":res.get("ok",False),"status":res.get("status"),"error":res.get("error")}
        source_status.append(row)
        if not res.get("ok"): continue
        try:
            if "json" in res.get("content_type","") or name=="ReceitaWS":
                obj=res["text"] if isinstance(res["text"],dict) else __import__('json').loads(res["text"])
                fields=_json_fields(obj)
            else: fields=_html_fields(res["text"])
        except Exception as e:
            row["ok"]=False; row["error"]=f"Parser: {e}"; continue
        records[name]=fields
        for k,v in fields.items():
            all_fields.setdefault(k,[]).append((name,v))
    fields={}; conflicts=[]
    for k,vals in all_fields.items():
        normalized={re.sub(r"\W+","",str(v)).lower() for _,v in vals}
        if len(normalized)==1: fields[k]=vals[0][1]
        elif len(normalized)>1:
            conflicts.append({"field":k,"values":[{"Fonte":s,"Valor":v} for s,v in vals]})
            # Choose value with most source support; ties remain unresolved.
            counts={n:0 for n in normalized}
            for _,v in vals: counts[re.sub(r"\W+","",str(v)).lower()]+=1
            winner=max(counts,key=counts.get)
            if list(counts.values()).count(counts[winner])==1:
                fields[k]=next(v for _,v in vals if re.sub(r"\W+","",str(v)).lower()==winner)
    successful=sum(1 for x in source_status if x["ok"])
    critical=[]
    st=str(fields.get("Situação cadastral","")).upper()
    if "INAPTA" in st: critical.append("Empresa inapta")
    if "BAIXADA" in st: critical.append("Empresa baixada")
    return {"cnpj":c,"fields":fields,"source_records":records,"field_sources":field_sources,
            "conflicts":conflicts,"source_status":source_status,"source_count":len(source_status),
            "successful_sources":successful,"critical_flags":critical,
            "public_presence": bool(fields.get("Endereço") or fields.get("Telefone") or fields.get("Nome fantasia")),
            "partners":[],"commercial_evidence":False,"verified_revenue":False}
