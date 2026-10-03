# Fratelli B2B Crédito 6.4.1

Correção de autenticação da versão 6.4.0.

## Se já existe um usuário e a senha não funciona
1. Abra o sistema.
2. Na tela de login, abra **Esqueci a senha / recuperação local**.
3. Selecione o usuário.
4. Defina uma nova senha com pelo menos 8 caracteres.
5. Entre novamente.

Alternativamente, no terminal dentro da pasta do sistema:
`python reset_admin.py`

## Importante
A autenticação usa a mesma base local `credit.db`. Não apague essa base se quiser preservar histórico e usuários.
