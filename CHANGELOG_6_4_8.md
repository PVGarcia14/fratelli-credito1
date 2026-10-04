# 6.4.8

- Corrigido o motor de sugestão comercial para usar o saldo realmente disponível da análise.
- Adicionado cálculo genérico de desconto por faixa de quantidade.
- O desconto é aplicado antes da validação do limite.
- A sugestão procura a maior quantidade inteira de caixas cujo valor líquido cabe no saldo.
- Interface passou a mostrar valor bruto, desconto, valor do desconto, valor líquido e saldo restante.
- Faixas e percentuais ficam configuráveis em `config.py`.
- Adicionados testes para desconto, saldo disponível e proteção contra estouro de limite.
- Mantidos catálogo genérico e valores placeholder; não foram embutidos produtos ou preços de bebidas alcoólicas.
