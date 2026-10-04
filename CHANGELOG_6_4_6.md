# B2B Credit Decision Engine 6.4.6

## Correção
- Corrigido StreamlitDuplicateElementId causado pela execução dupla de `login_gate()` após a autenticação.
- A tela `Login` do menu interno não chama mais a rotina de autenticação novamente.
- Adicionadas keys exclusivas aos botões de logout.
- Mantidos banco de usuários, histórico, auditoria e demais funcionalidades.
