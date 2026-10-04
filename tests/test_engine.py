from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from credit_engine import validate_cnpj, score_limit, box_calc, analyze, order_value_for_boxes, suggest_products


def dossier(age_date, status="ATIVA", fields_extra=None):
    fields={"CNPJ":"12345678000195","Razão social":"Empresa Teste","Endereço":"Rua A","CNAE principal":"1234","Natureza jurídica":"LTDA","Data de abertura":age_date,"Situação cadastral":status}
    if fields_extra: fields.update(fields_extra)
    return {"fields":fields,"conflicts":[],"successful_sources":3,"source_count":5,"critical_flags":[],"partners":["A"],"public_presence":True,"verified_revenue":False}


def test_cnpj_validation():
    ok,c=validate_cnpj('12.345.678/0001-95'); assert ok and c=='12345678000195'


def test_limit_bands():
    assert score_limit(20)[0]==0
    assert score_limit(30)[0]==1500
    assert score_limit(40)[0]==5000
    assert score_limit(50)[0]==10000
    assert score_limit(60)[0]==20000


def test_box_calc():
    r=box_calc(1500,100,9); assert r['boxes']==1 and r['units']==9


def test_dynamic_difference():
    old=analyze(dossier('2015-01-01'))
    new=analyze(dossier('2026-06-01'))
    assert old['score'] > new['score']
    old_age=next(x for x in old['criteria'] if x['name']=='Tempo de atividade')
    new_age=next(x for x in new['criteria'] if x['name']=='Tempo de atividade')
    assert old_age['points']==10.0
    assert new_age['points']==1.0


def test_age_mid_band():
    r=analyze(dossier('2024-01-01'))
    age=next(x for x in r['criteria'] if x['name']=='Tempo de atividade')
    assert age['points']==6.0


def test_critical_refusal():
    d=dossier('2015-01-01',status='BAIXADA')
    r=analyze(d,requested=1000)
    assert r['limit']==0 and r['order']['decision']=='RECUSAR'


def test_over_limit():
    d=dossier('2015-01-01')
    r=analyze(d,requested=50000)
    assert r['order']['decision'] in ('APROVAR COM LIMITE','ANÁLISE EXCEPCIONAL','RECUSAR')


def test_discount_is_applied_before_limit_check():
    tiers=[
        {"min_boxes":1,"max_boxes":2,"min_units":None,"max_units":None,"discount":0.10},
        {"min_boxes":3,"max_boxes":None,"min_units":None,"max_units":34,"discount":0.20},
        {"min_boxes":None,"max_boxes":None,"min_units":36,"max_units":None,"discount":0.30},
    ]
    r=order_value_for_boxes(2,100,9,tiers)
    assert r['gross']==1800 and r['discount_rate']==0.10 and r['net']==1620
    r2=order_value_for_boxes(3,100,9,tiers)
    assert r2['discount_rate']==0.20 and r2['net']==2160
    r3=order_value_for_boxes(4,100,9,tiers)
    assert r3['discount_rate']==0.30 and r3['net']==2520

def test_suggestion_uses_available_balance_and_net_value():
    tiers=[
        {"min_boxes":1,"max_boxes":2,"min_units":None,"max_units":None,"discount":0.10},
        {"min_boxes":3,"max_boxes":None,"min_units":None,"max_units":34,"discount":0.20},
        {"min_boxes":None,"max_boxes":None,"min_units":36,"max_units":None,"discount":0.30},
    ]
    products=[{'name':'Produto X','unit_price':100,'units_per_box':9}]
    out=suggest_products(1700,80,90,products,tiers)
    assert out[0]['boxes']==2
    assert out[0]['net']==1620
    assert out[0]['remaining']==80

def test_suggestion_never_exceeds_available_balance():
    tiers=[
        {"min_boxes":1,"max_boxes":2,"min_units":None,"max_units":None,"discount":0.10},
        {"min_boxes":3,"max_boxes":None,"min_units":None,"max_units":34,"discount":0.20},
        {"min_boxes":None,"max_boxes":None,"min_units":36,"max_units":None,"discount":0.30},
    ]
    products=[{'name':'Produto X','unit_price':100,'units_per_box':9}]
    out=suggest_products(1000,80,90,products,tiers)
    assert out[0]['net'] <= 1000

def test_discount_boundary_by_whole_boxes():
    tiers=[
        {"min_boxes":1,"max_boxes":2,"min_units":None,"max_units":None,"discount":0.10},
        {"min_boxes":3,"max_boxes":None,"min_units":None,"max_units":34,"discount":0.20},
        {"min_boxes":None,"max_boxes":None,"min_units":36,"max_units":None,"discount":0.30},
    ]
    assert order_value_for_boxes(2,100,9,tiers)['discount_rate']==0.10
    assert order_value_for_boxes(3,100,9,tiers)['discount_rate']==0.20
    assert order_value_for_boxes(4,100,9,tiers)['discount_rate']==0.30

def test_max_boxes_accounts_for_discount():
    tiers=[
        {"min_boxes":1,"max_boxes":2,"min_units":None,"max_units":None,"discount":0.10},
        {"min_boxes":3,"max_boxes":None,"min_units":None,"max_units":34,"discount":0.20},
        {"min_boxes":None,"max_boxes":None,"min_units":36,"max_units":None,"discount":0.30},
    ]
    from credit_engine import max_boxes_within_limit
    r=max_boxes_within_limit(2500,100,9,tiers)
    assert r['boxes']==3 and r['net']==2160
