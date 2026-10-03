from __future__ import annotations
import base64
import json
import sqlite3
import random
from datetime import datetime, date
from pathlib import Path
from urllib.parse import quote
import pandas as pd
import streamlit as st
from engine import (
    WEIGHTS, clean_cnpj, validate_cnpj, score_from_evidence, risk_band, decision,
    public_confidence, calculate_box_value, discount_for_quantity,
    simulate_order, max_boxes_by_approved_limit, suggest_automatic_mix,
    build_dynamic_credit_analysis
)
from public_research import research_company, search_person

APP_DIR=Path(__file__).parent
DB=APP_DIR/"fratelli.db"
LOGO=APP_DIR/"assets"/"fratelli_logo.png"

# 6.0.6 — configuração comercial genérica.
# Altere SOMENTE estes valores para cadastrar seus produtos no seu ambiente.
PRODUCT_CONFIG = [
    {"name": "Produto A", "unit_price": 0.0, "units_per_box": 9},
    {"name": "Produto B", "unit_price": 0.0, "units_per_box": 9},
    {"name": "Produto C", "unit_price": 0.0, "units_per_box": 9},
]
COMMERCIAL_TIERS = [
    {"label": "Condição 1", "min_units": 1, "max_units": 18, "discount_pct": 0.0},
    {"label": "Condição 2", "min_units": 19, "max_units": 34, "discount_pct": 0.0},
    {"label": "Condição 3", "min_units": 35, "max_units": None, "discount_pct": 0.0},
]

st.set_page_config(page_title="Fratelli B2B Crédito 6.2.1", page_icon=str(LOGO) if LOGO.exists() else "💳", layout="wide")


def money(v):
    return f"R$ {float(v or 0):,.2f}".replace(",","X").replace(".",",").replace("X",".")


def db():
    c=sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS analyses(
        id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, cnpj TEXT, company TEXT,
        score REAL, confidence REAL, coverage REAL, requested REAL, approved REAL,
        decision TEXT, data_json TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS audit(
        id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, action TEXT, cnpj TEXT, details TEXT)""")
    c.commit(); return c


def audit(c, action, cnpj, details):
    c.execute("INSERT INTO audit(created_at,action,cnpj,details) VALUES(?,?,?,?)", (datetime.now().isoformat(timespec="seconds"),action,cnpj,json.dumps(details,ensure_ascii=False)))
    c.commit()


def logo_html():
    if not LOGO.exists(): return ""
    b=base64.b64encode(LOGO.read_bytes()).decode()
    return f'<img src="data:image/png;base64,{b}" style="width:180px;max-height:90px;object-fit:contain;display:block;margin:0 auto 18px;">'

st.markdown("""
<style>
.block-container{padding-top:1.4rem}
.decision{padding:22px;border-radius:14px;border:1px solid rgba(0,0,0,.08);margin-bottom:18px}
.decision h2{margin:0 0 8px 0}
.small{color:#737780;font-size:.9rem}
</style>
""", unsafe_allow_html=True)
st.sidebar.markdown(logo_html(), unsafe_allow_html=True)
st.sidebar.markdown("# Fratelli 6.2.1")
menu=st.sidebar.radio("Menu", ["Nova análise","Histórico","Auditoria","Metodologia"])

c=db()

if menu=="Nova análise":
    st.title("Nova análise — 6.2.1")
    st.caption("Motor B2B genérico de análise de crédito 6.2.1 — pesquisa pública, evidências, score dinâmico, limite, localização e simulação explicável.")
    cnpj=st.text_input("CNPJ", placeholder="00.000.000/0000-00")
    col1,col2=st.columns([1,1])
    with col1:
        if st.button("Analisar empresa", type="primary", use_container_width=True):
            ok,msg=validate_cnpj(cnpj)
            if not ok: st.error(msg)
            else:
                with st.spinner("Pesquisando fontes públicas disponíveis..."):
                    d=research_company(cnpj)
                st.session_state["dossier"]=d
                st.session_state["cnpj"]=clean_cnpj(cnpj)
                audit(c,"PESQUISA_PUBLICA",clean_cnpj(cnpj),{"sources":d.get("source_count",0),"successful":d.get("successful_sources",0),"conflicts":len(d.get("conflicts",[]))})
    with col2:
        st.info("A pesquisa pública não acessa bases privadas, não contorna autenticação e não transforma ausência de resultado em ausência de dívida/processo.")

    d=st.session_state.get("dossier")
    if d:
        fields=d.get("fields",{})
        st.subheader("Resumo da empresa")
        if fields:
            # Derivados: idade e situação atual, sempre explicados como derivados dos dados cadastrais.
            opening = fields.get("Data de abertura")
            age_label = None
            if opening:
                try:
                    dt = datetime.strptime(opening, "%d/%m/%Y").date()
                    today = date.today()
                    years = today.year - dt.year - ((today.month, today.day) < (dt.month, dt.day))
                    months = (today.year - dt.year) * 12 + today.month - dt.month - (1 if today.day < dt.day else 0)
                    age_label = f"{max(0, years)} anos e {max(0, months % 12)} meses"
                except Exception:
                    age_label = None
            display_fields = dict(fields)
            if age_label:
                display_fields["Idade da empresa"] = age_label
            status_value = fields.get("Situação cadastral")
            if status_value:
                display_fields["Empresa ativa? "] = "SIM — situação cadastral ativa" if "ATIV" in status_value.upper() else f"NÃO/REVISAR — {status_value}"
            rows = []
            for k,v in display_fields.items():
                srcs = "; ".join(s for s,_ in d.get("field_sources",{}).get(k,[]))
                if k == "Idade da empresa": srcs = "Derivada da Data de abertura"
                if k == "Empresa ativa? ": srcs = "Derivada da Situação cadastral"
                rows.append({"Campo":k,"Valor":v,"Fonte(s)":srcs})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum dado cadastral foi extraído automaticamente das fontes que responderam.")

        # Localização e visual da sede
        st.subheader("Localização da empresa")
        address_parts = [fields.get("Endereço"), fields.get("Bairro"), fields.get("Município/UF"), fields.get("CEP")]
        address = ", ".join([x for x in address_parts if x])
        if address:
            map_query = quote(address + ", Brasil")
            maps_url = f"https://www.google.com/maps/search/?api=1&query={map_query}"
            left, right = st.columns([1.35, 1])
            with left:
                st.markdown(f"**Endereço cadastral:** {address}")
                st.link_button("📍 Abrir localização no Google Maps", maps_url, use_container_width=True)
                st.caption("A localização é baseada no endereço cadastral encontrado nas fontes públicas. Confirme a fachada/local antes de usar como prova de operação física.")
            with right:
                imgs = d.get("image_candidates", [])
                shown = False
                for item in imgs:
                    u = item.get("url") if isinstance(item, dict) else item
                    if u:
                        try:
                            st.image(u, caption=f"Imagem pública — fonte: {item.get('source','fonte pública')}", use_container_width=True)
                            shown = True
                            break
                        except Exception:
                            pass
                if not shown:
                    st.info("Não foi encontrada automaticamente uma foto pública da fachada. O botão ao lado abre a localização no Google Maps para conferência visual.")
        else:
            st.info("Endereço suficiente para localizar a empresa não foi identificado nas fontes públicas.")
        if d.get("conflicts"):
            st.error(f"⚠️ {len(d['conflicts'])} divergência(s) entre fontes")
            for x in d["conflicts"]:
                st.markdown(f"**{x['field']}**")
                st.dataframe(pd.DataFrame(x["values"]), use_container_width=True, hide_index=True)
        ok_sources=d.get("successful_sources",0); total_sources=d.get("source_count",0)
        conf=public_confidence(total_sources,ok_sources,len(d.get("conflicts",[])),len(fields))
        d["confidence"]=conf
        st.metric("Confiança da pesquisa pública", f"{conf*100:.0f}%")

        st.subheader("Sócios / administradores")
        partners = d.get("partners", [])
        if partners:
            st.success(f"{len(partners)} sócio(s)/administrador(es) identificado(s) nas fontes públicas.")
            st.dataframe(
                pd.DataFrame([
                    {
                        "Nome": p.get("name"),
                        "Qualificação": p.get("role", "Não identificada"),
                        "Fonte(s)": "; ".join(d.get("partner_sources", {}).get(p.get("name"), [])),
                    }
                    for p in partners
                ]),
                use_container_width=True, hide_index=True
            )
        else:
            st.warning("Nenhum sócio/administrador foi extraído automaticamente das fontes que responderam. Isso não significa ausência de sócios; significa apenas que o QSA não foi localizado/extraído nesta pesquisa.")

        st.subheader("Pesquisa judicial — Jusbrasil")
        st.caption("A pesquisa automática usa o CNPJ e os nomes identificados no QSA. Processos são evidências; o sistema não conclui que uma ocorrência seja prejudicial sem analisar tipo, partes, assunto, situação, movimentações e decisões.")

        # Structured Jusbrasil API, when an authorized key is configured.
        api_rows = d.get("jusbrasil_api", [])
        if api_rows:
            configured = any(x.get("configured") for x in api_rows)
            if configured:
                st.success("Consulta automática estruturada do Jusbrasil habilitada.")
                for r in api_rows:
                    label = str(r.get("kind", "")).upper()
                    with st.expander(f"{label} — {len(r.get('processes', []))} processo(s)", expanded=True):
                        if r.get("ok"):
                            procs = r.get("processes", [])
                            if procs:
                                rows=[]
                                for proc in procs:
                                    rows.append({
                                        "Processo": proc.get("numero_processo", ""),
                                        "Tipo": proc.get("tipo_processo", ""),
                                        "Status": (proc.get("status") or {}).get("inferido", "") if isinstance(proc.get("status"), dict) else proc.get("status", ""),
                                        "Fórum": proc.get("forum", ""),
                                        "Parte/posição": "; ".join([str(x.get("nome", ""))+" — "+str(x.get("papel", "")) for x in (proc.get("partes") or [])[:5]]),
                                        "Última atualização": proc.get("data_ultima_atualizacao", ""),
                                        "Link": proc.get("link", ""),
                                    })
                                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                            else:
                                st.info("Nenhum processo foi retornado pela consulta para este tipo. Isso não equivale a prova de inexistência de processos em todas as bases.")
                        else:
                            st.warning(r.get("note", f"Consulta não concluída (HTTP {r.get('status')})."))
            else:
                st.warning("A integração automática do Jusbrasil ainda não está configurada. O sistema não vai abrir o site nem afirmar que não existem processos.")

        # Public discovery remains secondary and is shown as evidence/pista, not as a fake API result.
        judicial = d.get("partner_judicial", [])
        if judicial:
            st.markdown("**Pesquisa pública de descoberta**")
            for r in judicial:
                target = f"{r.get('target_type')}: {r.get('query')}"
                with st.expander(target, expanded=False):
                    if r.get("available_publicly"):
                        st.caption(r.get("snippet", "")[:2500])
                    else:
                        st.warning(r.get("note", "Fonte não disponível publicamente neste acesso."))

        st.divider()
        st.subheader("QSA — pesquisa automática")
        st.caption("Os nomes abaixo são os sócios/administradores que o sistema conseguiu extrair automaticamente das fontes públicas consultadas. A Receita Federal informa que a consulta cadastral de CNPJ inclui o QSA.")
        if partners:
            st.success(f"{len(partners)} sócio(s)/administrador(es) identificado(s) automaticamente.")
        else:
            st.warning("O QSA não foi extraído nas fontes que responderam. Isso não significa ausência de sócios.")

    st.subheader("Dados internos e solicitação")
    a,b,c1,c2=st.columns(4)
    with a: monthly=float(st.number_input("Faturamento mensal comprovado (R$)",min_value=0.0,step=1000.0))
    with b: exposure=float(st.number_input("Exposição atual em aberto (R$)",min_value=0.0,step=500.0))
    with c1: requested=float(st.number_input("Valor solicitado pelo cliente (R$)",min_value=0.0,step=500.0))
    with c2: current_limit=float(st.number_input("Limite atual informado (R$)",min_value=0.0,step=500.0))
    st.caption("O limite atual é informativo; não é somado à exposição. A exposição em aberto é o que reduz o limite disponível.")
    source=st.selectbox("Fonte do faturamento", ["Não informado","Documento financeiro","Fonte financeira autorizada","Declaração do cliente"])
    active_restriction=st.checkbox("Existe restrição crítica confirmada em fonte/documento?", value=False)
    years=st.number_input("Anos de atividade confirmados", min_value=0.0,step=1.0)
    status=st.selectbox("Situação cadastral confirmada", ["Não informado","ATIVA/REGULAR","SUSPENSA/INAPTA","BAIXADA/OUTRA"])
    docs=st.checkbox("Dados cadastrais/documentação conferidos", value=False)

    st.subheader("Composição do score")
    st.caption("O score 6.2.1 é calculado a partir das evidências efetivamente encontradas. Critérios sem evidência recebem no máximo 25% do peso e não são renormalizados.")

    analysis = build_dynamic_credit_analysis(
        d,
        monthly_revenue=monthly,
        exposure=exposure,
        requested=requested,
        revenue_source=source,
        critical_restriction=active_restriction,
        confirmed_years=years,
        confirmed_status=status,
        documents_checked=docs,
    )
    criteria = analysis["criteria"]
    score = analysis["score"]
    coverage = analysis["coverage"]
    confidence_pct = analysis["confidence"]
    risk = analysis["risk"]
    financial_available = analysis["financial_available"]
    dec = analysis["decision"]
    items = {x["name"]: round(x["points"] / x["max_points"] * 100, 1) if x["max_points"] else None for x in criteria}
    missing = analysis["missing"]

    st.dataframe(
        pd.DataFrame([
            {
                "Critério": x["name"],
                "Pontos": f'{x["points"]:.1f} / {x["max_points"]}',
                "Status": x["status"],
                "Evidência": x["evidence"],
                "Explicação": x["explanation"],
            } for x in criteria
        ]),
        use_container_width=True, hide_index=True
    )

    st.subheader("DECISÃO DE CRÉDITO")
    if dec["status"]=="APROVAR": cls="success"
    elif dec["status"]=="APROVAR COM LIMITE": cls="warning"
    elif dec["status"]=="REVISÃO MANUAL": cls="warning"
    else: cls="error"
    getattr(st,cls)(f"### {dec['status']}\n\n**Score:** {score}/100 · **Risco:** {risk} · **Cobertura:** {coverage}%\n\n**Limite pela política:** {money(dec['ceiling'])}\n\n**Limite financeiro disponível:** {money(financial_available)}\n\n**Solicitação:** {money(requested)}\n\n**Valor aprovado:** {money(dec['approved'])}\n\n**Motivo:** {dec['reason']}")
    if missing:
        st.warning("Dados sem evidência — contribuição limitada a 25%: " + ", ".join(missing))
    if requested>dec["approved"]:
        st.write(f"**Excedente não aprovado:** {money(requested-dec['approved'])}")

    st.subheader("Simulação financeira do pedido")
    sim=float(st.number_input("Valor a simular (R$)",min_value=0.0,value=0.0,step=500.0,key="sim"))
    # 6.1.3 — a simulação NÃO recalcula a decisão de crédito.
    # O valor do meio deve ser exatamente o valor aprovado na decisão acima.
    approved_in_decision = max(0.0, float(dec.get("approved", 0) or 0))
    simulated_excess = max(0.0, sim - approved_in_decision)
    s1,s2,s3=st.columns(3)
    s1.metric("Pedido simulado",money(sim)); s2.metric("Limite aprovado na decisão",money(approved_in_decision)); s3.metric("Excesso",money(simulated_excess))

    # 6.0.8 — a solicitação de aprovação manual só aparece quando o usuário
    # efetivamente simula um valor acima do valor aprovado na decisão de crédito.
    # Não exibimos alerta/botões de aprovação apenas porque a empresa está em
    # revisão manual ou porque o valor aprovado é zero.
    APPROVER_NAME = "Paulo Garcia"
    APPROVER_EMAIL = "teixeira1218@gmail.com"
    APPROVER_WA = "5585985552343"

    if sim > 0 and sim > float(dec.get("approved", 0) or 0):
        st.write(f"**Resultado:** SIMULAÇÃO ACIMA DO LIMITE — valor solicitado excede o crédito aprovado na decisão.")
        st.error("### CRÉDITO NÃO APROVADO AUTOMATICAMENTE\n\nO valor simulado é superior ao crédito aprovado na decisão. Este pedido precisa de aprovação manual antes de ser liberado.")
        reason = "Valor simulado superior ao crédito aprovado na decisão"
        excess_manual = max(0.0, sim - float(dec.get("approved", 0) or 0))
        company_name = fields.get("Razão social", "Empresa não identificada") if d else "Empresa não identificada"
        cnpj_value = st.session_state.get("cnpj", clean_cnpj(cnpj))
        email_subject = f"Solicitação de aprovação de crédito — {company_name} — {cnpj_value}"
        email_body = (
            f"Olá {APPROVER_NAME},\n\n"
            f"Solicito aprovação manual de crédito para a empresa {company_name} (CNPJ {cnpj_value}).\n\n"
            f"Score: {score:.1f}/100\n"
            f"Risco: {risk}\n"
            f"Cobertura: {coverage:.1f}%\n"
            f"Limite pela política: {money(dec['ceiling'])}\n"
            f"Valor aprovado na decisão: {money(dec.get('approved', 0))}\n"
            f"Valor solicitado: {money(sim)}\n"
            f"Excesso: {money(excess_manual)}\n"
            f"Resultado da análise: {dec['status']}\n"
            f"Motivo: {reason}\n\n"
            "Favor analisar e informar a decisão manual.\n"
        )
        import urllib.parse
        email_url = "mailto:" + APPROVER_EMAIL + "?" + urllib.parse.urlencode({"subject": email_subject, "body": email_body})
        wa_text = (
            f"Solicitação de aprovação de crédito\n"
            f"Empresa: {company_name}\n"
            f"CNPJ: {cnpj_value}\n"
            f"Score: {score:.1f}/100\n"
            f"Limite pela política: {money(dec['ceiling'])}\n"
            f"Aprovado na decisão: {money(dec.get('approved', 0))}\n"
            f"Solicitado: {money(sim)}\n"
            f"Excesso: {money(excess_manual)}\n"
            f"Motivo: {reason}\n\n"
            "Favor analisar e autorizar ou recusar o crédito."
        )
        wa_url = "https://wa.me/" + APPROVER_WA + "?" + urllib.parse.urlencode({"text": wa_text})
        b1, b2 = st.columns(2)
        with b1:
            st.link_button(f"✉️ Solicitar aprovação por e-mail — {APPROVER_NAME}", email_url, use_container_width=True)
        with b2:
            st.link_button(f"💬 Solicitar aprovação via WhatsApp — {APPROVER_NAME}", wa_url, use_container_width=True)
        st.caption("Os botões abrem uma mensagem pré-preenchida. O envio depende da confirmação do usuário no aplicativo de e-mail/WhatsApp.")
        if st.button("Registrar solicitação de aprovação manual", key="register_manual_approval", use_container_width=True):
            audit(c, "SOLICITACAO_APROVACAO_MANUAL", cnpj_value, {
                "approver": APPROVER_NAME, "email": APPROVER_EMAIL, "whatsapp": APPROVER_WA,
                "score": score, "coverage": coverage, "policy_ceiling": dec["ceiling"],
                "approved_automatically": dec.get("approved", 0), "requested": sim,
                "excess": excess_manual, "reason": reason
            })
            st.success("Solicitação de aprovação manual registrada na auditoria.")
    elif sim > 0:
        st.success("### CRÉDITO DENTRO DO LIMITE\n\nO valor simulado está dentro do crédito aprovado na decisão de crédito.")

    st.subheader("Simulador comercial")
    st.caption("A montagem do pedido é automática: o sistema usa o crédito efetivamente aprovado, trabalha com caixas inteiras e escolhe a composição que melhor utiliza o limite sem ultrapassá-lo.")

    with st.expander("⚙️ Configuração comercial (administrador)", expanded=False):
        st.markdown("**Produtos cadastrados**")
        pc1, pc2, pc3 = st.columns(3)
        edited_products = []
        for col, cfg, idx in zip((pc1, pc2, pc3), PRODUCT_CONFIG, range(3)):
            with col:
                name = st.text_input(f"Produto {chr(65+idx)}", value=cfg["name"], key=f"prod_name_612_{idx}")
                price = float(st.number_input("Preço unitário (R$)", min_value=0.0, value=float(cfg["unit_price"]), step=1.0, key=f"prod_price_612_{idx}"))
                units_box = int(st.number_input("Unidades por caixa", min_value=1, value=int(cfg["units_per_box"]), step=1, key=f"prod_box_612_{idx}"))
                edited_products.append({"name": name, "unit_price": price, "units_per_box": units_box})
        st.markdown("**Condições comerciais** — a faixa aplicável é escolhida automaticamente pela quantidade total de unidades.")
        st.dataframe(pd.DataFrame(COMMERCIAL_TIERS), use_container_width=True, hide_index=True)

    if "edited_products_612" not in st.session_state:
        st.session_state["edited_products_612"] = [dict(x) for x in PRODUCT_CONFIG]
    if edited_products:
        st.session_state["edited_products_612"] = edited_products
    edited_products = st.session_state["edited_products_612"]

    approved_limit = max(0.0, float(dec.get("approved", 0) or 0))

    q1, q2, q3 = st.columns(3)
    q1.metric("Crédito aprovado", money(approved_limit))
    q2.metric("Saldo disponível", money(approved_limit))
    q3.metric("Produtos cadastrados", str(sum(1 for x in edited_products if x["unit_price"] > 0)))

    if "mix_seed_612" not in st.session_state:
        st.session_state["mix_seed_612"] = random.randrange(1, 10**9)
    if st.button("🎲 Gerar nova sugestão", type="primary", use_container_width=True, key="generate_mix_612"):
        st.session_state["mix_seed_612"] = random.randrange(1, 10**9)

    mix = suggest_automatic_mix(approved_limit, edited_products, COMMERCIAL_TIERS, st.session_state["mix_seed_612"])
    if approved_limit <= 0:
        st.info("Ainda não existe crédito efetivamente liberado para montar uma sugestão automática. O teto da política não é tratado como autorização.")
    elif mix["status"] != "OK":
        st.warning("Não foi possível montar automaticamente uma composição dentro do crédito aprovado. Verifique os preços e as unidades por caixa na configuração administrativa.")
    else:
        st.markdown("### Sugestão automática de pedido")
        rows = [{"Produto": x["name"], "Caixas": x["boxes"], "Unidades": x["units"], "Valor bruto": money(x["gross"])} for x in mix["items"]]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        a,b,c2,d2 = st.columns(4)
        a.metric("Caixas", str(sum(x["boxes"] for x in mix["items"])))
        b.metric("Unidades", str(mix["units"]))
        c2.metric("Valor do pedido", money(mix["net"]))
        d2.metric("Saldo do crédito", money(mix["remaining"]))
        condition_text = mix["tier"] or "Sem faixa"
        st.success(f"Pedido dentro do crédito aprovado · {condition_text} · Desconto aplicado: {mix['discount_pct']:.1f}%")
        st.caption("A sugestão é calculada automaticamente. O botão gera outra composição entre alternativas próximas da melhor utilização do crédito.")

    with st.expander("Simulação manual (opcional)", expanded=False):
        st.caption("Use somente para conferência. A operação normal deve usar a sugestão automática acima.")
        product_options = [x["name"] for x in edited_products]
        if product_options:
            selected_product = st.selectbox("Produto", product_options, key="manual_product_612")
            selected_cfg = next(x for x in edited_products if x["name"] == selected_product)
            mc1, mc2 = st.columns(2)
            with mc1:
                requested_boxes = int(st.number_input("Quantidade de caixas", min_value=0, value=1, step=1, key="boxes_612"))
            with mc2:
                st.metric("Valor de 1 caixa", money(calculate_box_value(selected_cfg["unit_price"], selected_cfg["units_per_box"])))
            order = simulate_order(selected_cfg["unit_price"], requested_boxes, selected_cfg["units_per_box"], COMMERCIAL_TIERS)
            excess = round(max(0.0, order["net"] - approved_limit), 2)
            r1, r2, r3 = st.columns(3)
            r1.metric("Caixas", str(order["boxes"]))
            r2.metric("Unidades", str(order["units"]))
            r3.metric("Valor líquido", money(order["net"]))
            if requested_boxes == 0:
                st.info("Informe pelo menos 1 caixa para simular.")
            elif approved_limit > 0 and order["net"] <= approved_limit + 1e-9:
                st.success(f"Dentro do crédito aprovado. Saldo: {money(approved_limit - order['net'])}.")
            elif approved_limit <= 0:
                st.error(f"Pedido calculado: {money(order['net'])}. Não há crédito efetivamente liberado.")
            else:
                st.warning(f"Pedido calculado: {money(order['net'])}. Excesso: {money(excess)}.")

    st.subheader("Fontes consultadas")
    if d:
        rows=[]
        for x in d.get("sources",[]):
            rows.append({"Fonte":x.get("source"),"Tipo":x.get("kind"),"Status":"OK" if x.get("ok") else "Sem resposta","URL":x.get("url"),"Horário":x.get("started")})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        st.info("Quando uma fonte privada/paga ou protegida não está disponível publicamente, o sistema informa a indisponibilidade; ele não inventa o resultado.")
    else:
        st.info("Execute a análise da empresa para preencher as fontes.")

    if st.button("Salvar análise"):
        payload={"fields":d.get("fields",{}) if d else {},"conflicts":d.get("conflicts",[]) if d else [],"items":items,"missing":missing}
        c.execute("INSERT INTO analyses(created_at,cnpj,company,score,confidence,coverage,requested,approved,decision,data_json) VALUES(?,?,?,?,?,?,?,?,?,?)",(datetime.now().isoformat(timespec="seconds"),st.session_state.get("cnpj",clean_cnpj(cnpj)),fields.get("Razão social","") if d else "",score,confidence_pct/100 if d else 0,coverage,requested,dec["approved"],dec["status"],json.dumps(payload,ensure_ascii=False)))
        c.commit(); audit(c,"SALVAR_ANALISE",st.session_state.get("cnpj",clean_cnpj(cnpj)),payload); st.success("Análise salva.")

elif menu=="Histórico":
    st.title("Histórico")
    df=pd.read_sql_query("SELECT id,created_at,cnpj,company,score,confidence,coverage,requested,approved,decision FROM analyses ORDER BY id DESC",c)
    if df.empty: st.info("Nenhuma análise salva.")
    else: st.dataframe(df,use_container_width=True,hide_index=True)

elif menu=="Auditoria":
    st.title("Auditoria")
    df=pd.read_sql_query("SELECT * FROM audit ORDER BY id DESC",c)
    st.dataframe(df,use_container_width=True,hide_index=True) if not df.empty else st.info("Nenhum evento registrado.")

else:
    st.title("Metodologia")
    st.markdown("### Regras centrais")
    st.write("Sem informação suficiente = 25% da pontuação máxima do critério.")
    st.write("Score <25 = recusar; 25–<35 = teto R$1.500; 35–<45 = R$5.000; 45–<55 = R$10.000; 55–70 = R$20.000; >70 = analisar o pedido solicitado.")
    st.write("Cobertura, confiança e score são métricas diferentes. Divergências e bloqueios críticos são controles, não bônus/penalidades arbitrárias.")
    st.write("Ausência de resultado público nunca é tratada como ausência do fato.")
    st.write("Toda evidência externa deve conservar fonte e horário da consulta.")
