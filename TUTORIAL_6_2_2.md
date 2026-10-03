# Fratelli B2B Crédito 6.2.2 — Tutorial rápido

## 1. Instalação local
1. Extraia o ZIP.
2. Abra o terminal na pasta do projeto.
3. Instale as dependências:
   `pip install -r requirements.txt`
4. Execute:
   `streamlit run app.py`
5. Abra o endereço local exibido pelo Streamlit.

## 2. Nova análise
1. Digite os 14 dígitos do CNPJ.
2. Clique em **Validar/Pesquisar CNPJ**.
3. Aguarde a pesquisa pública.
4. Confira a tabela de fontes: cada fonte deve aparecer como **OK** ou **Sem resposta**.
5. Confira os campos cadastrais e as divergências antes de usar o score.
6. Informe, quando existir documentação:
   - faturamento mensal comprovado;
   - exposição atual em aberto;
   - valor solicitado;
   - fonte do faturamento;
   - histórico de pagamentos;
   - valor vencido;
   - documentação conferida.
7. Leia o quadro **Qualidade dos dados** antes da decisão.

## 3. Como interpretar o score
- Cada critério tem peso próprio.
- Informação ausente recebe no máximo 25% daquele critério.
- Informação positiva só gera pontos quando existe evidência.
- Divergências ficam visíveis e reduzem a confiabilidade.
- Cobertura, confiança e score são métricas diferentes.
- Se nenhuma fonte retornar, o sistema deve mostrar **SEM RESPOSTA** e não fingir que a empresa foi pesquisada.

## 4. Como saber se a pesquisa funcionou
Para uma empresa real, você deve ver pelo menos alguns campos como razão social, situação, abertura, endereço, CNAE etc. Se todos os campos estiverem vazios e as fontes estiverem como “Sem resposta”, NÃO use o resultado para liberar crédito: corrija primeiro a conectividade/fontes.

## 5. Histórico e auditoria
- **Histórico:** mostra análises salvas.
- **Auditoria:** registra ações importantes.
- Use **Salvar análise** somente depois de conferir as evidências.

## 6. GitHub + Streamlit Community Cloud
1. Crie/abra seu repositório no GitHub.
2. Envie os arquivos do projeto, mantendo `app.py` na raiz.
3. Confirme que `requirements.txt` está na raiz.
4. No Streamlit Community Cloud, conecte o GitHub e escolha o repositório.
5. Selecione `app.py` como arquivo principal e publique.
6. Quando você fizer um novo commit no GitHub, o Streamlit poderá atualizar o aplicativo implantado.

## 7. Problema conhecido que esta versão corrige
Nas versões anteriores, quando a pesquisa pública não alimentava o motor de score, vários CNPJs acabavam recebendo praticamente a mesma pontuação porque os critérios ficavam sem evidência e eram tratados de forma uniforme.

A 6.2.2 adiciona:
- mais fontes públicas diretas;
- pesquisa de descoberta para encontrar páginas públicas;
- aproveitamento controlado de campos encontrados na descoberta;
- diagnóstico de fontes que responderam/não responderam;
- confiabilidade que realmente depende da pesquisa;
- histórico comercial opcional;
- faturamento/exposição/pedido influenciando capacidade quando documentados;
- alerta explícito quando a pesquisa não retornou evidências.

## 8. Regra de ouro
**Nunca interprete “sem informação” como “empresa sem problema”.**
Se a pesquisa estiver incompleta, primeiro corrija a coleta e só depois use o score para uma decisão comercial.
