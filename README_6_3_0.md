# B2B Credit Decision Engine 6.3.0

Motor genérico de análise de crédito B2B derivado da arquitetura 6.2.2.

## O que mudou
- Separação real entre pesquisa, motor de score, política de limite e simulação.
- Pesquisa multifonte isolada por adaptadores; uma falha não derruba a análise.
- Divergência entre fontes fica explícita.
- Ausência de informação não vira evidência positiva.
- Score dinâmico: campos, fontes, conflitos, sinais críticos e histórico alteram o resultado.
- Confiança separada do score.
- Exposição interna descontada do limite disponível.
- Pedido analisado em etapa separada.
- Histórico SQLite.
- Testes automatizados.

## Execução
```bash
pip install -r requirements.txt
streamlit run app.py
```

O software é deliberadamente genérico. Cadastros de produtos e condições comerciais ficam separados em `config.py`.
