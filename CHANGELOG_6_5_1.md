# 6.5.1

- Corrigido o empacotamento: arquivos da aplicação ficam na raiz do ZIP.
- Corrigido o carregamento das funções comerciais: o app não depende mais de uma importação múltipla frágil.
- Adicionada compatibilidade com instalações que ainda tenham um `credit_engine.py` antigo, evitando `ImportError` para funções comerciais.
- Mantido o cálculo por saldo disponível, caixas inteiras, valor bruto, desconto, valor líquido e saldo restante.
- Adicionado smoke check para validar os imports essenciais antes do deploy.
