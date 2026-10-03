from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from credit_engine import validate_cnpj, score_limit, box_calc, analyze


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
