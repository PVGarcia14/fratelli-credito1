from __future__ import annotations
from pathlib import Path
import streamlit as st
import pandas as pd
from credit_engine import clean_cnpj, validate_cnpj, analyze, box_calc
from research import research_company
from config import PRODUCTS, PAYMENT_TERMS
from storage import Store
from auth import init_users, has_users, create_user, verify_user

APP=Path(__file__).parent
store=Store(APP/'credit.db')
init_users(APP/'credit.db')

st.set_page_config(page_title='Fratelli B2B Crédito 6.4',page_icon='logo.png',layout='wide')

st.markdown('''<style>
.block-container{padding-top:1rem}.decision{padding:18px;border-radius:12px;border:1px solid #ddd;margin:10px 0}.muted{color:#6b7280}.danger{border-left:5px solid #b91c1c}.warn{border-left:5px solid #d97706}.ok{border-left:5px solid #15803d}
.login-card{max-width:460px;margin:6vh auto;padding:30px;border:1px solid #e5e7eb;border-radius:16px;box-shadow:0 8px 30px rgba(0,0,0,.08)}
</style>''',unsafe_allow_html=True)


def money(v): return f"R$ {float(v or 0):,.2f}".replace(',','X').replace('.',',').replace('X','.')

def login_gate():
    if st.session_state.get('authenticated'): return True
    st.markdown('<div class="login-card">',unsafe_allow_html=True)
    if not has_users(APP/'credit.db'):
        st.image(str(APP/'logo.png'),width=170)
        st.title('Primeiro acesso')
        st.caption('Crie o usuário administrador. Depois disso, todo acesso ao sistema exigirá login.')
        u=st.text_input('Usuário',key='setup_u')
        p=st.text_input('Senha',type='password',key='setup_p')
        p2=st.text_input('Confirmar senha',type='password',key='setup_p2')
        if st.button('CRIAR ACESSO',type='primary',use_container_width=True):
            if p!=p2: st.error('As senhas não conferem.')
            else:
                ok,msg=create_user(APP/'credit.db',u,p)
                if ok: st.success('Acesso criado. Faça login abaixo.'); st.rerun()
                else: st.error(msg)
    else:
        st.image(str(APP/'logo.png'),width=170)
        st.title('Fratelli B2B Crédito')
        st.caption('Acesso restrito')
        u=st.text_input('Usuário',key='login_u')
        p=st.text_input('Senha',type='password',key='login_p')
        if st.button('ENTRAR',type='primary',use_container_width=True):
            if verify_user(APP/'credit.db',u,p):
                st.session_state.authenticated=True; st.session_state.username=u; st.rerun()
            else: st.error('Usuário ou senha inválidos.')
    st.markdown('</div>',unsafe_allow_html=True)
    return False

if not login_gate(): st.stop()

with st.sidebar:
    st.image(str(APP/'logo.png'),width=130)
    st.caption(f"Usuário: **{st.session_state.get('username','')}**")
    if st.button('Sair',use_container_width=True):
        st.session_state.clear(); st.rerun()
    menu=st.radio('Menu',['Nova análise','Simulação do pedido','Histórico','Carteira','Metodologia'])

def render_decision(result):
    o=result['order']; dec=o['decision']
    icon={'APROVAR':'🟢','APROVAR COM LIMITE':'🟡','ANÁLISE EXCEPCIONAL':'🟠','RECUSAR':'🔴','SEM PEDIDO':'⚪'}.get(dec,'⚪')
    cls='ok' if dec=='APROVAR' else 'warn' if 'LIMITE' in dec or 'EXCEPCIONAL' in dec else 'danger' if dec=='RECUSAR' else ''
    st.markdown(f'<div class="decision {cls}"><h2>{icon} {dec}</h2><b>Score:</b> {result["score"]:.1f}/100 &nbsp; <b>Confiança:</b> {result["confidence"]:.1f}% &nbsp; <b>Limite:</b> {money(result["limit"])}</div>',unsafe_allow_html=True)
    a,b,c,d=st.columns(4); a.metric('Score',f'{result["score"]:.1f}/100'); b.metric('Confiança',f'{result["confidence"]:.1f}%'); c.metric('Limite',money(result['limit'])); d.metric('Disponível',money(result['available']))
    st.markdown(f'**Por que:** {o["reason"]}')

if menu=='Nova análise':
    st.title('Nova análise de crédito')
    st.caption('Motor enxuto: 4 pilares de decisão. O histórico interno entra como ajuste comercial, não como critério que derruba sozinho um cliente sem histórico.')
    cnpj=st.text_input('CNPJ',placeholder='00.000.000/0000-00')
    requested=st.number_input('Valor do pedido (opcional)',min_value=0.0,step=100.0,format='%.2f')
    payment=st.selectbox('Condição de pagamento',[x['label'] for x in PAYMENT_TERMS])
    term=next(x for x in PAYMENT_TERMS if x['label']==payment)
    hist=st.selectbox('Histórico interno',['Sem histórico','Em dia','Atrasos','Inadimplente'])
    overdue=st.number_input('Valor em atraso interno',min_value=0.0,step=100.0,format='%.2f')
    exposure=st.number_input('Exposição atual',min_value=0.0,step=100.0,format='%.2f')
    if st.button('ANALISAR EMPRESA',type='primary',use_container_width=True):
        ok,msg=validate_cnpj(cnpj)
        if not ok: st.error(msg)
        else:
            with st.spinner('Consultando fontes públicas disponíveis...'):
                dossier=research_company(cnpj)
            result=analyze(dossier,requested,hist,overdue,exposure,term.get('risk_factor',0))
            result['dossier']=dossier; result['cnpj']=clean_cnpj(cnpj); result['requested']=requested; result['payment']=payment
            result['company']=dossier.get('fields',{}).get('Razão social') or dossier.get('fields',{}).get('Nome fantasia') or 'Empresa não identificada'
            st.session_state['result']=result
            store.save_analysis({**result,'decision':result['order']['decision']})
            store.audit('NOVA_ANALISE',result['cnpj'],{'user':st.session_state.get('username'),'sources':dossier['successful_sources'],'conflicts':len(dossier['conflicts'])})
    r=st.session_state.get('result')
    if r:
        render_decision(r); d=r['dossier']; f=d['fields']
        st.subheader(r['company']); st.write(f"CNPJ: **{r['cnpj']}**")
        cols=st.columns(4); cols[0].metric('Fontes responderam',f"{d['successful_sources']}/{d['source_count']}"); cols[1].metric('Campos encontrados',len(f)); cols[2].metric('Divergências',len(d['conflicts'])); cols[3].metric('Cobertura do score',f"{r['coverage']:.0f}%")
        st.subheader('Raio-X')
        tabs=st.tabs(['Identidade','Pilares','Risco','Fontes','Explicação'])
        with tabs[0]: st.dataframe(pd.DataFrame([{'Campo':k,'Valor':v} for k,v in f.items()]),use_container_width=True,hide_index=True)
        with tabs[1]: st.dataframe(pd.DataFrame(r['criteria']),use_container_width=True,hide_index=True)
        with tabs[2]:
            if d['critical_flags']:
                for x in d['critical_flags']: st.error(x)
            if d['conflicts']:
                for x in d['conflicts']:
                    st.warning(f"Divergência em {x['field']}"); st.dataframe(pd.DataFrame(x['values']),use_container_width=True,hide_index=True)
            else: st.info('Não foram identificadas divergências entre as fontes que responderam. Isso não significa ausência de eventos em bases não consultadas.')
        with tabs[3]: st.dataframe(pd.DataFrame(d['source_status']),use_container_width=True,hide_index=True)
        with tabs[4]:
            st.markdown('**Fatores positivos**'); [st.write('• '+x) for x in r['positives']]
            st.markdown('**Fatores de atenção**'); [st.write('• '+x) for x in r['attentions']]
            st.caption('Confiança mede qualidade/cobertura da evidência; não é probabilidade de pagamento.')

elif menu=='Simulação do pedido':
    st.title('Simulação financeira do pedido')
    r=st.session_state.get('result')
    if not r: st.warning('Faça uma análise primeiro.'); st.stop()
    product=st.selectbox('Produto',[p['name'] for p in PRODUCTS]); p=next(x for x in PRODUCTS if x['name']==product)
    boxes=st.number_input('Quantidade de caixas',min_value=0,step=1); term_label=st.selectbox('Prazo',[x['label'] for x in PAYMENT_TERMS]); term=next(x for x in PAYMENT_TERMS if x['label']==term_label)
    sim=box_calc(boxes*p['unit_price']*p['units_per_box'],p['unit_price'],p['units_per_box']); requested=sim['used']
    result=analyze(r['dossier'],requested,r.get('internal_payment_status','Sem histórico'),r.get('overdue',0),r['exposure'],term.get('risk_factor',0))
    a,b,c=st.columns(3); a.metric('Valor do pedido',money(requested)); b.metric('Limite disponível',money(result['available'])); c.metric('Excesso',money(result['order']['excess']))
    render_decision(result); st.write(f"**{boxes} caixas × {p['units_per_box']} unidades = {sim['units']} unidades**")
    if result['order']['decision']!='APROVAR':
        safe_boxes=box_calc(result['available'],p['unit_price'],p['units_per_box'])['boxes']
        st.info(f"Contraproposta operacional: até {safe_boxes} caixas dentro do limite disponível, ou encaminhar para análise excepcional conforme a política interna.")

elif menu=='Histórico':
    st.title('Histórico de análises'); rows=store.history(); st.dataframe(pd.DataFrame(rows,columns=['Data','CNPJ','Empresa','Score','Confiança','Limite','Pedido','Decisão']),use_container_width=True,hide_index=True)

elif menu=='Carteira':
    st.title('Carteira de crédito'); count,total,used,refused=store.portfolio(); a,b,c,d=st.columns(4); a.metric('Análises',count); b.metric('Limite acumulado',money(total)); c.metric('Pedidos analisados',money(used)); d.metric('Recusas',refused)
    st.caption('Painel das análises registradas no aplicativo.')

else:
    st.title('Metodologia')
    st.markdown('''### Motor de decisão 6.4\n\n**4 pilares**\n1. Legitimidade e cadastro — 25 pontos\n2. Estrutura e capacidade — 25 pontos\n3. Histórico público e risco — 25 pontos\n4. Qualidade das evidências — 25 pontos\n\nO histórico interno deixa de ser um critério de 20 pontos que derruba automaticamente empresas novas. Ele funciona como ajuste comercial pequeno: em dia, atrasos ou inadimplência.\n\nA ausência de informação reduz a pontuação, mas não destrói o score; a **confiança** mostra separadamente o quanto da análise foi sustentado por fontes.''')
