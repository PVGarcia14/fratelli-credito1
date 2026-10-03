# 6.4.0

- Motor de score simplificado para 4 pilares de 25 pontos.
- Histórico comercial passou a ser ajuste explícito, evitando penalização desproporcional de empresas sem histórico.
- Prazo de pagamento passou a aplicar fator de risco configurável no limite.
- Login obrigatório com criação do primeiro administrador no primeiro acesso.
- Senhas armazenadas com PBKDF2-HMAC-SHA256 + salt.
- Logo incluído na tela de login e na barra lateral.
- Sessão com logout.
- Auditoria registra usuário da análise.
- Baseado no 6.3.0.
