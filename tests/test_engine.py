import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from credit_engine import validate_cnpj, analyze, box_calc, score_limit

def dossier(active=True, sources=4, fields=None, conflicts=None, critical=None):
    return {'fields':fields or {'Situação cadastral':'ATIVA','Data de abertura':'02/10/2020','Endereço':'Rua X','CNAE principal':'123 - Teste','Porte':'ME','Capital social':'R$ 100.000'},'successful_sources':sources,'source_count':sources,'conflicts':conflicts or [],'critical_flags':critical or [],'partners':[{'name':'A'}],'public_presence':True,'source_records':{}}

def test_cnpj(): assert validate_cnpj('39.284.044/0001-26')[0]
def test_limit_bands():
    assert score_limit(20)[0]==0
    assert score_limit(30)[0]==1500
    assert score_limit(40)[0]==5000
    assert score_limit(50)[0]==10000
    assert score_limit(60)[0]==20000

def test_box():
    x=box_calc(5000,100,9); assert x['boxes']==5 and x['used']==4500

def test_dynamic_differs():
    a=analyze(dossier(),5000)
    b=analyze(dossier(sources=0,fields={}),5000)
    assert a['score'] != b['score']

def test_critical_recuses():
    a=analyze(dossier(critical=['Empresa inapta']),100)
    assert a['order']['decision']=='RECUSAR' and a['limit']==0

def test_over_limit():
    a=analyze(dossier(),50000)
    assert a['order']['excess']>=0
