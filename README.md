# Fratelli B2B Crédito 6.2.0

Motor genérico de análise de crédito empresarial por CNPJ.

## Principais mudanças
- Score dinâmico orientado por evidências.
- Critérios sem evidência limitados a 25% do peso.
- Ausência de informação não é tratada como informação positiva.
- Confiança da análise separada do score.
- Campos cadastrais e fontes exibidos.
- Alertas para situações cadastrais críticas.
- Limite calculado separadamente da decisão.
- Estrutura pronta para adicionar fontes públicas independentes.
- Sem dependência de uma única base no desenho do motor.

## Execução
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Próxima camada recomendada
Adicionar conectores independentes para fontes públicas oficiais e secundárias, com:
- data/hora da consulta;
- URL;
- evidência capturada;
- confiabilidade da fonte;
- convergência/divergência;
- deduplicação;
- histórico das análises.

A aplicação não deve afirmar que uma fonte foi consultada quando a consulta não ocorreu.
