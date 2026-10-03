# Fratelli B2B Crédito 6.4.0

Software genérico de decisão de crédito B2B, com pesquisa pública, score, confiança, limite, simulação e histórico.

## Primeiro acesso
Execute:
`streamlit run app.py`

Na primeira abertura, crie o usuário administrador. Depois disso, a aplicação exige login.

## Segurança
- Senhas não ficam em texto puro; são derivadas com PBKDF2-HMAC-SHA256 e salt.
- A base SQLite local contém usuários, análises e auditoria.
- Para uso em produção multiusuário, recomenda-se colocar a aplicação atrás de HTTPS e um mecanismo de gestão de identidade corporativa.

## Score 6.4
O score usa quatro pilares de 25 pontos. Histórico comercial é um modificador pequeno e explícito; prazo de pagamento aplica um fator de risco configurável.

## Logo
`logo.png` é usado na tela de login e na barra lateral.
