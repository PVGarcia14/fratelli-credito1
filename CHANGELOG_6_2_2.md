# Fratelli B2B Crédito 6.2.2

## Correção principal
O motor não deve produzir a mesma avaliação apenas porque vários CNPJs estão sem histórico interno. A pesquisa pública agora participa efetivamente da diferenciação.

## Melhorias
- 4 fontes cadastrais diretas configuradas: CNPJ.BIZ, CNPJ.ai, Casa dos Dados e Econodata.
- Pesquisa de descoberta em Google/DuckDuckGo e buscas direcionadas por fonte.
- Campos encontrados em páginas de descoberta podem corroborar dados, sem substituir a evidência direta.
- Diagnóstico explícito de fontes com resposta e sem resposta.
- Confiabilidade não é mais marcada como “com evidência” quando nenhuma fonte respondeu.
- Cobertura não fica artificialmente alta quando a coleta falha.
- Cadastro diferencia situação e idade da empresa.
- Estrutura diferencia quantidade de campos e convergência.
- Capacidade considera faturamento documentado, relação pedido/faturamento e exposição/faturamento.
- Histórico comercial interno passou a ser um campo explícito e opcional.
- Valor vencido informado gera alerta e impacto específico.
- Score, cobertura, confiança e qualidade dos dados ficam separados.
- Mantida a regra: ausência de informação recebe no máximo 25% do peso do critério.
- Incluído tutorial de uso e implantação.

## Testes
9 testes automatizados passaram.
Também foi executado teste comparativo com empresas sintéticas para verificar diferenciação do score.
