# 6.4.5

## Correções
- Corrigido o problema de comparação de senha no Primeiro acesso usando `st.form`, evitando estados parciais entre reruns do Streamlit.
- Senhas continuam sendo comparadas exatamente como digitadas; não são aparadas, convertidas para minúsculas ou alteradas.
- Mensagem de diagnóstico de comprimento só aparece quando há divergência, sem exibir a senha.

## Banco de usuários
- Tabela `users` passa a registrar `created_by`, `role`, `active`, `last_login` e `password_changed_at`.
- Migração automática de bancos criados em versões anteriores.
- Primeiro administrador fica registrado como `PRIMEIRO_ACESSO`.
- Usuários criados por administrador registram quem os criou.
- Novo painel administrativo `Usuários` com listagem de acessos, perfil, criador, datas e ativação/desativação.
- Senhas nunca são exibidas nem armazenadas em texto puro.

## Recuperação
- “Esqueci minha senha” passa a exigir autenticação de um administrador existente.
- O reset de senha fica registrado pela identidade do administrador responsável.
- `reset_admin.py` permanece como recuperação de emergência local para o administrador.
