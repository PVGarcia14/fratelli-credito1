# 6.4.1

- Corrigida a autenticação para normalizar usuário (maiúsculas/minúsculas e espaços externos).
- Adicionada recuperação local de senha para instalações em computador controlado pelo cliente.
- Adicionado `reset_admin.py` para redefinição de senha via terminal quando necessário.
- Tratamento mais robusto de dados de senha/salt inválidos.
- Mantida a política de não armazenar senhas em texto puro.
