import streamlit as st
from engine import analyze_company, clean_cnpj, score_to_limit

st.set_page_config(page_title="Fratelli B2B Crédito 6.2.0", layout="wide")

st.title("Fratelli B2B Crédito")
st.caption("Motor genérico de análise de crédito empresarial por CNPJ — versão 6.2.0")

cnpj = st.text_input("CNPJ", placeholder="00.000.000/0000-00")
requested = st.number_input("Valor solicitado (R$)", min_value=0.0, step=500.0)

if st.button("ANALISAR CNPJ", type="primary"):
    c = clean_cnpj(cnpj)
    if len(c) != 14:
        st.error("Informe um CNPJ válido com 14 dígitos.")
    else:
        with st.spinner("Consultando fontes públicas e consolidando evidências..."):
            result = analyze_company(c)

        st.divider()
        d = result["decision"]
        st.subheader("DECISÃO DE CRÉDITO")
        st.metric("Decisão", d["label"])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Score", f'{result["score"]:.1f}/100')
        c2.metric("Confiança", f'{result["confidence"]:.1f}%')
        c3.metric("Limite recomendado", f'R$ {d["limit"]:,.2f}'.replace(",", "X").replace(".", ",").replace("X", "."))
        c4.metric("Pedido", f'R$ {requested:,.2f}'.replace(",", "X").replace(".", ",").replace("X", "."))

        if requested:
            excess = max(0, requested - d["limit"])
            st.info(
                f"Pedido dentro do limite." if excess == 0 else
                f"Pedido acima do limite em R$ {excess:,.2f}."
            )

        st.subheader("Resumo cadastral")
        st.json(result["company"])

        st.subheader("Score por critério")
        for item in result["criteria"]:
            st.write(f"**{item['name']} — {item['points']:.1f}/{item['max_points']}**")
            st.progress(min(1.0, item["points"] / item["max_points"]))
            st.caption(item["explanation"])

        st.subheader("Fatores positivos")
        for x in result["positive"]:
            st.write("• " + x)

        st.subheader("Fatores de atenção")
        for x in result["attention"]:
            st.write("⚠ " + x)

        st.subheader("Alertas")
        if result["alerts"]:
            for x in result["alerts"]:
                st.warning(x)
        else:
            st.success("Nenhum alerta crítico identificado nas fontes consultadas.")

        st.subheader("Fontes consultadas")
        for s in result["sources"]:
            st.write(f"**{s['source']}** — {s['status']} — {s['detail']}")
            if s.get("url"):
                st.caption(s["url"])

        st.subheader("Confiabilidade da análise")
        st.write(result["confidence_explanation"])
