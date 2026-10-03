# Fratelli B2B Crédito — 6.1.2

- Simulador comercial simplificado para operação diária.
- Sugestão automática de composição baseada no crédito efetivamente aprovado.
- Otimização por caixas inteiras, sem ultrapassar o limite.
- Faixa comercial escolhida automaticamente pela quantidade total de unidades.
- Configuração de produtos e condições movida para área administrativa recolhida.
- Simulação manual mantida apenas como contingência.

# Fratelli B2B Crédito — 6.1.0

- QSA automático reforçado para múltiplos formatos públicos.
- Pesquisa judicial Jusbrasil separada em descoberta pública e integração estruturada autorizada.
- Suporte opcional à API oficial do Jusbrasil via `JUSBRASIL_API_KEY` em Streamlit Secrets ou variável de ambiente.
- Consulta automática civil, criminal e trabalhista por CNPJ quando a API autorizada estiver configurada.
- Exibição estruturada de número, tipo, status, fórum, partes e última atualização.
- Removidos botões que simplesmente redirecionavam o usuário para o Jusbrasil na seção principal.
- Ausência de API/resultado não é interpretada como ausência de processos.


## 6.1.1
- Corrigida a simulação financeira para reutilizar exatamente o valor aprovado na decisão de crédito.
- Removido o recálculo independente da decisão ao alterar o valor simulado.
- Campo passou a mostrar "Limite aprovado na decisão" e excesso calculado contra esse mesmo valor.
- Solicitação de aprovação manual continua aparecendo somente quando a simulação excede o limite aprovado.

## 6.1.3 — correção da simulação financeira
- O campo central da simulação agora mostra exatamente o `Valor aprovado` da decisão de crédito.
- O excesso é calculado como `valor simulado - valor aprovado na decisão`.
- A simulação não recalcula uma nova decisão de crédito.
- A aprovação manual continua aparecendo somente quando o valor simulado excede o valor aprovado.


## 6.2.1
- Integração da interface/pesquisa pública da 6.1.3 com score dinâmico da 6.2.0.
- Score variável por evidências, convergência, divergências e dados cadastrais reais.
- Mantida a regra de 25% para critérios sem evidência.
- Mantidos histórico, auditoria, localização, QSA e simulação B2B genérica.
