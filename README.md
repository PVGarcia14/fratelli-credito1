# Fratelli B2B Crédito 6.2.1

Motor genérico de análise de crédito empresarial por CNPJ, incorporando a interface e pesquisa pública da 6.1.3 com o motor de score dinâmico da 6.2.0.

## O que foi incorporado da 6.1.3
- Pesquisa pública em fontes diretas e páginas de descoberta.
- Convergência/divergência entre fontes, com fonte e horário.
- Extração de dados cadastrais e QSA quando publicamente disponível.
- Pesquisa pública de descoberta de processos e integração opcional autorizada do Jusbrasil por API.
- Localização cadastral e abertura no Google Maps.
- Histórico, auditoria e salvamento local das análises.
- Simulação financeira separada da decisão.
- Simulador B2B genérico com produtos configuráveis, caixas/unidades e composição automática sem ultrapassar o crédito efetivamente aprovado.
- Logo da versão 6.1.3 preservada.

## O que foi incorporado/alterado na 6.2.1
- Score passa a variar com as evidências reais encontradas no dossiê.
- Não existem mais notas fixas do tipo “mesma pontuação para todo CNPJ”.
- Critérios sem evidência continuam limitados a 25% do peso.
- Confiança da informação é separada do score.
- Divergências entre fontes afetam a confiabilidade e permanecem visíveis.
- Histórico comercial não é presumido positivo quando não existe informação interna.
- Limite financeiro considera faturamento comprovado e exposição em aberto informados pelo analista.
- A decisão usa o limite aprovado na decisão, não apenas o teto de política.
- Nenhuma fonte é considerada consultada quando a consulta não ocorreu.

## Regras centrais
- Score <25: recusar / sem venda a prazo.
- 25–<35: teto de política R$ 1.500.
- 35–<45: teto R$ 5.000.
- 45–<55: teto R$ 10.000.
- 55–70: teto R$ 20.000.
- >70: analisar o pedido solicitado, sujeito à evidência e ao limite financeiro disponível.
- Critério sem evidência: no máximo 25% do peso.
- Ausência de resultado público não significa ausência do fato.

## Execução
```bash
pip install -r requirements.txt
streamlit run app.py
```

Esta é uma aplicação B2B genérica. Produtos e condições comerciais permanecem configuráveis no ambiente do usuário.
