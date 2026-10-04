from __future__ import annotations
from pathlib import Path
import streamlit as st
import pandas as pd
import credit_engine as _ce
clean_cnpj = _ce.clean_cnpj
validate_cnpj = _ce.validate_cnpj
analyze = _ce.analyze

# Keep the app compatible with older deployments while the full 6.5.1 package is being rolled out.
try:
    box_calc = _ce.box_calc
except AttributeError:
    def box_calc(limit, unit_price, units_per_box=9):
        import math
        bv=max(0.0,float(unit_price))*max(1,int(units_per_box))
        boxes=0 if bv<=0 else math.floor(max(0.0,float(limit))/bv + 1e-9)
        return {'boxes':boxes,'units':boxes*max(1,int(units_per_box)),'box_value':round(bv,2),'used':round(boxes*bv,2),'remaining':round(max(0.0,float(limit))-boxes*bv,2)}

try:
    order_value_for_boxes = _ce.order_value_for_boxes
except AttributeError:
    def order_value_for_boxes(boxes, unit_price, units_per_box=9, tiers=None):
        b=max(0,int(boxes)); u=max(1,int(units_per_box)); gross=round(b*u*float(unit_price),2)
        rate=0.0
        for t in (tiers or []):
            if t.get('min_boxes') is not None and b < int(t['min_boxes']): continue
            if t.get('max_boxes') is not None and b > int(t['max_boxes']): continue
            units=b*u
            if t.get('min_units') is not None and units < int(t['min_units']): continue
            if t.get('max_units') is not None and units > int(t['max_units']): continue
            rate=max(0.0,min(1.0,float(t.get('discount',0)))); break
        disc=round(gross*rate,2); return {'boxes':b,'units':b*u,'gross':gross,'discount_rate':rate,'discount_value':disc,'net':round(gross-disc,2)}

try:
    max_boxes_within_limit = _ce.max_boxes_within_limit
except AttributeError:
    def max_boxes_within_limit(available_limit, unit_price, units_per_box=9, tiers=None):
        available=max(0.0,float(available_limit)); best=order_value_for_boxes(0,unit_price,units_per_box,tiers)
        for b in range(1,100000):
            cur=order_value_for_boxes(b,unit_price,units_per_box,tiers)
            if cur['net'] <= available + 1e-9: best=cur
            else: break
        return best

try:
    suggest_products = _ce.suggest_products
except AttributeError:
    def suggest_products(available_limit, score, confidence, products, tiers=None):
        out=[]
        for prod in products or []:
            best=max_boxes_within_limit(available_limit,prod.get('unit_price',0),prod.get('units_per_box',1),tiers)
            if best['boxes']>0:
                out.append({'name':prod.get('name','Produto'),'boxes':best['boxes'],'units':best['units'],'unit_price':float(prod.get('unit_price',0)),'gross':best['gross'],'discount_rate':best['discount_rate'],'discount_value':best['discount_value'],'net':best['net'],'box_value':round(best['net']/best['boxes'],2),'used':best['net'],'remaining':round(float(available_limit)-best['net'],2)})
        return out
from research import research_company
from config import PRODUCTS, PAYMENT_TERMS
try:
    from config import COMMERCIAL_DISCOUNT_TIERS
except ImportError:
    # Compatibility with older deployments: the commercial policy is optional.
    COMMERCIAL_DISCOUNT_TIERS = []
from storage import Store
from auth import init_users, has_users, create_user, verify_user, list_users, list_user_records, reset_password, register_login, is_admin, deactivate_user

APP=Path(__file__).parent
store=Store(APP/'credit.db')
init_users(APP/'credit.db')

st.set_page_config(page_title='B2B Crédito 6.5.2',page_icon='logo.png',layout='wide')

st.markdown('''<style>
.block-container{padding-top:1rem}.decision{padding:18px;border-radius:12px;border:1px solid #ddd;margin:10px 0}.muted{color:#6b7280}.danger{border-left:5px solid #b91c1c}.warn{border-left:5px solid #d97706}.ok{border-left:5px solid #15803d}
.login-card{max-width:460px;margin:6vh auto;padding:30px;border:1px solid #e5e7eb;border-radius:16px;box-shadow:0 8px 30px rgba(0,0,0,.08)}
</style>''',unsafe_allow_html=True)


def money(v): return f"R$ {float(v or 0):,.2f}".replace(',','X').replace('.',',').replace('X','.')

def login_gate():
    """Tela de autenticação. Formulários evitam reruns parciais e problemas de sincronização dos campos de senha."""
    db = APP / 'credit.db'
    if st.session_state.get('authenticated'):
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.image(str(APP/'logo.png'), width=170)
        st.title('Acesso ao Fratelli B2B Crédito')
        st.success(f"Você está conectado como **{st.session_state.get('username','')}**.")
        if st.button('SAIR DA CONTA', type='primary', use_container_width=True, key='login_gate_logout_button'):
            st.session_state.clear(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        return True

    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.image(str(APP/'logo.png'), width=170)
    st.title('Fratelli B2B Crédito')
    st.caption('Acesso restrito')
    action = st.radio('Acesso', ['Entrar', 'Esqueci minha senha', 'Primeiro acesso'], horizontal=True,
                      label_visibility='collapsed', key='login_action')

    if action == 'Entrar':
        with st.form('login_form', clear_on_submit=False):
            u = st.text_input('Usuário', placeholder='Ex.: administrador')
            p = st.text_input('Senha', type='password')
            submit = st.form_submit_button('ENTRAR', type='primary', use_container_width=True)
        if submit:
            if verify_user(db, u, p):
                normalized = ' '.join(u.strip().lower().split())
                register_login(db, normalized)
                st.session_state.authenticated = True
                st.session_state.username = normalized
                st.session_state.role = 'admin' if is_admin(db, normalized) else 'user'
                st.rerun()
            else:
                st.error('Usuário ou senha inválidos.')

    elif action == 'Esqueci minha senha':
        st.info('Por segurança, a redefinição é autorizada por um administrador existente. Se o administrador perdeu a senha, use reset_admin.py no computador do sistema.')
        users = list_users(db)
        if not users:
            st.warning('Ainda não existe nenhum usuário. Use “Primeiro acesso”.')
        else:
            with st.form('recovery_form', clear_on_submit=True):
                admin_u = st.text_input('Usuário administrador')
                admin_p = st.text_input('Senha do administrador', type='password')
                target = st.selectbox('Usuário a redefinir', users)
                rp = st.text_input('Nova senha', type='password')
                rp2 = st.text_input('Confirmar nova senha', type='password')
                submit = st.form_submit_button('REDEFINIR SENHA', use_container_width=True)
            if submit:
                if not verify_user(db, admin_u, admin_p) or not is_admin(db, admin_u):
                    st.error('Administrador não autenticado ou credenciais inválidas.')
                elif rp != rp2:
                    st.error('As senhas não conferem.')
                else:
                    ok, msg = reset_password(db, target, rp, admin_u)
                    (st.success if ok else st.error)(msg)

    else:
        if has_users(db):
            st.warning('O primeiro acesso já foi realizado neste computador. Novos usuários devem ser criados por um administrador.')
        else:
            st.caption('Crie o primeiro usuário administrador. Depois disso, todo acesso ao sistema exigirá login.')
            with st.form('first_access_form', clear_on_submit=True):
                u = st.text_input('Novo usuário', placeholder='Ex.: PVGFratelli')
                p = st.text_input('Senha', type='password')
                p2 = st.text_input('Confirmar senha', type='password')
                submit = st.form_submit_button('CRIAR PRIMEIRO ACESSO', type='primary', use_container_width=True)
            if submit:
                # The two values come from the same submitted form, preventing the
                # previous widget-state/rerun issue that could show equal values but compare differently.
                if p != p2:
                    st.error(f'As senhas não conferem. Comprimento informado: {len(p)} e {len(p2)}.')
                else:
                    ok, msg = create_user(db, u, p, 'PRIMEIRO_ACESSO', 'admin')
                    if ok:
                        st.success(msg + ' Agora selecione “Entrar”.')
                    else:
                        st.error(msg)
    st.markdown('</div>', unsafe_allow_html=True)
    return False

if not login_gate(): st.stop()

with st.sidebar:
    st.image(str(APP/'logo.png'),width=130)
    st.caption(f"Usuário: **{st.session_state.get('username','')}**")
    if st.button('Sair',use_container_width=True, key='sidebar_logout_button'):
        st.session_state.clear(); st.rerun()
    menu_items=['Login','Nova análise','Simulação do pedido','Histórico','Carteira']
    if st.session_state.get('role')=='admin': menu_items += ['Usuários']
    menu_items += ['Metodologia']
    menu=st.radio('Menu',menu_items)

def render_decision(result):
    o=result['order']; dec=o['decision']
    icon={'APROVAR':'🟢','APROVAR COM LIMITE':'🟡','ANÁLISE EXCEPCIONAL':'🟠','RECUSAR':'🔴','SEM PEDIDO':'⚪'}.get(dec,'⚪')
    cls='ok' if dec=='APROVAR' else 'warn' if 'LIMITE' in dec or 'EXCEPCIONAL' in dec else 'danger' if dec=='RECUSAR' else ''
    st.markdown(f'<div class="decision {cls}"><h2>{icon} {dec}</h2><b>Score:</b> {result["score"]:.1f}/100 &nbsp; <b>Confiança:</b> {result["confidence"]:.1f}% &nbsp; <b>Limite:</b> {money(result["limit"])}</div>',unsafe_allow_html=True)
    a,b,c,d=st.columns(4); a.metric('Score',f'{result["score"]:.1f}/100'); b.metric('Confiança',f'{result["confidence"]:.1f}%'); c.metric('Limite',money(result['limit'])); d.metric('Disponível',money(result['available']))
    st.markdown(f'**Por que:** {o["reason"]}')

if menu=='Login':
    st.title('Acesso ao sistema')
    st.success(f"Você está conectado como **{st.session_state.get('username','')}**.")
    st.caption('A autenticação já foi concluída. Use o botão Sair no menu lateral para encerrar a sessão.')

elif menu=='Nova análise':
    st.title('Nova análise de crédito')
    st.caption('Motor de 5 critérios: inclui tempo de atividade como fator independente. O histórico interno continua como ajuste comercial, não como penalização estrutural para empresas sem histórico.')
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
        st.subheader('Sugestão comercial dentro do limite')
        suggestions=suggest_products(r['available'], r['score'], r['confidence'], PRODUCTS, COMMERCIAL_DISCOUNT_TIERS)
        if suggestions:
            st.dataframe(pd.DataFrame(suggestions)[['name','boxes','units','gross','discount_rate','discount_value','net','remaining']].rename(columns={
                'name':'Produto','boxes':'Caixas sugeridas','units':'Unidades','gross':'Valor bruto',
                'discount_rate':'Desconto','discount_value':'Valor do desconto','net':'Valor líquido',
                'remaining':'Saldo após sugestão'
            }), use_container_width=True, hide_index=True)
            st.caption('Cada linha usa o nome, preço e unidades/caixa do catálogo configurado. O saldo disponível é o teto absoluto: o desconto é aplicado antes da validação e a maior quantidade de caixas cujo valor líquido cabe no saldo é calculada automaticamente.')
        else:
            st.info('Nenhum produto do catálogo cabe no limite disponível. Reduza a quantidade ou revise a política de crédito.')
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
    sim=order_value_for_boxes(boxes,p['unit_price'],p['units_per_box'],COMMERCIAL_DISCOUNT_TIERS); requested=sim['net']
    result=analyze(r['dossier'],requested,r.get('internal_payment_status','Sem histórico'),r.get('overdue',0),r['exposure'],term.get('risk_factor',0))
    a,b,c,d=st.columns(4); a.metric('Valor bruto',money(sim['gross'])); b.metric('Desconto',f"{sim['discount_rate']*100:.0f}%"); c.metric('Valor líquido',money(requested)); d.metric('Limite disponível',money(result['available']))
    render_decision(result); st.write(f"**{boxes} caixas × {p['units_per_box']} unidades = {sim['units']} unidades**")
    safe_calc=max_boxes_within_limit(result['available'],p['unit_price'],p['units_per_box'],COMMERCIAL_DISCOUNT_TIERS)
    safe_boxes=safe_calc['boxes']
    if result['order']['decision']!='APROVAR':
        st.info(f"Contraproposta operacional: até {safe_boxes} caixas dentro do limite disponível, ou encaminhar para análise excepcional conforme a política interna.")
    else:
        st.success(f"Pedido dentro do limite: até {safe_boxes} caixas deste produto permanecem cobertas pelo limite disponível.")

elif menu=='Histórico':
    st.title('Histórico de análises'); rows=store.history(); st.dataframe(pd.DataFrame(rows,columns=['Data','CNPJ','Empresa','Score','Confiança','Limite','Pedido','Decisão']),use_container_width=True,hide_index=True)

elif menu=='Carteira':
    st.title('Carteira de crédito'); count,total,used,refused=store.portfolio(); a,b,c,d=st.columns(4); a.metric('Análises',count); b.metric('Limite acumulado',money(total)); c.metric('Pedidos analisados',money(used)); d.metric('Recusas',refused)
    st.caption('Painel das análises registradas no aplicativo.')

elif menu=='Usuários':
    st.title('Usuários e acessos')
    st.caption('Banco local de usuários: login, perfil, data de criação, criador e último acesso. Senhas nunca são exibidas nem armazenadas em texto puro.')
    records=list_user_records(APP/'credit.db')
    if records:
        df=pd.DataFrame(records)
        st.dataframe(df.rename(columns={'username':'Usuário','role':'Perfil','active':'Ativo','created_at':'Criado em','created_by':'Criado por','last_login':'Último login','password_changed_at':'Senha alterada em'}),use_container_width=True,hide_index=True)
    st.subheader('Criar usuário')
    with st.form('admin_create_user', clear_on_submit=True):
        nu=st.text_input('Novo usuário')
        np=st.text_input('Senha inicial', type='password')
        np2=st.text_input('Confirmar senha', type='password')
        role=st.selectbox('Perfil',['user','admin'])
        submit=st.form_submit_button('CRIAR USUÁRIO',type='primary')
    if submit:
        if np!=np2: st.error('As senhas não conferem.')
        else:
            ok,msg=create_user(APP/'credit.db',nu,np,st.session_state.get('username',''),role)
            (st.success if ok else st.error)(msg)
    st.subheader('Desativar usuário')
    active_users=[x['username'] for x in records if x['active'] and x['username']!=st.session_state.get('username','')]
    if active_users:
        target=st.selectbox('Usuário',active_users)
        if st.button('DESATIVAR USUÁRIO'):
            ok,msg=deactivate_user(APP/'credit.db',target)
            (st.success if ok else st.error)(msg)
    else:
        st.info('Não há outro usuário ativo para desativar.')

else:
    st.title('Metodologia')
    st.markdown('''### Motor de decisão 6.4.3\n\n**5 critérios**\n1. Legitimidade e cadastro — 20 pontos\n2. Tempo de atividade — 10 pontos\n3. Estrutura e capacidade — 25 pontos\n4. Histórico público e risco — 20 pontos\n5. Qualidade das evidências — 25 pontos\n\n**Tempo de atividade:** menos de 1 ano = 10% do critério; entre 1 e 3 anos = 60%; acima de 3 anos = 100%.\n\nO histórico interno deixa de ser um critério de 20 pontos que derruba automaticamente empresas novas. Ele funciona como ajuste comercial pequeno: em dia, atrasos ou inadimplência.\n\nA ausência de informação reduz a pontuação, mas não destrói o score; a **confiança** mostra separadamente o quanto da análise foi sustentado por fontes.''')
