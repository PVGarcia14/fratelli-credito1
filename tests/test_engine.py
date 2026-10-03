from engine import (
    validate_cnpj, score_from_evidence, policy_ceiling, decision, risk_band,
    calculate_box_value, simulate_order, max_boxes_by_approved_limit
)

def test_cnpj_valid():
    ok,msg=validate_cnpj('39.284.044/0001-26')
    assert ok

def test_cnpj_invalid():
    ok,msg=validate_cnpj('39.284.044/0001-27')
    assert not ok

def test_missing_is_25_percent_without_renormalization():
    vals={k:100 for k in __import__('engine').WEIGHTS}
    vals['Histórico comercial identificado']=None
    score,cov,missing=score_from_evidence(vals)
    assert 84.9 <= score <= 85.1
    assert cov == 80.0
    assert 'Histórico comercial identificado' in missing

def test_policy_bands():
    assert policy_ceiling(24.9,100)[0]==0
    assert policy_ceiling(25,100)[0]==1500
    assert policy_ceiling(34.99,100)[0]==1500
    assert policy_ceiling(35,100)[0]==5000
    assert policy_ceiling(45,100)[0]==10000
    assert policy_ceiling(55,100)[0]==20000
    assert policy_ceiling(70,100)[0]==20000
    assert policy_ceiling(70.1,100)[0]==100

def test_decision_full_and_partial():
    assert decision(60,5000,10000,80)['status']=='APROVAR'
    assert decision(60,25000,10000,80)['status']=='APROVAR COM LIMITE'
    assert decision(20,1000,10000,80)['status']=='RECUSAR'
    assert decision(60,1000,10000,40)['status']=='REVISÃO MANUAL'

def test_risk():
    assert risk_band(24.9)=='MUITO ELEVADO'
    assert risk_band(70)=='CONTROLADO'
    assert risk_band(70.1)=='BAIXO'


def test_box_value_and_quantity():
    assert calculate_box_value(100, 9) == 900
    q = __import__('engine').quantity_within_limit(2000, 900, 9)
    assert q["boxes"] == 2
    assert q["units"] == 18
    assert q["gross"] == 1800


def test_discount_and_order():
    tiers = [
        {"min_units": 1, "max_units": 18, "discount_pct": 10},
        {"min_units": 19, "max_units": 34, "discount_pct": 20},
        {"min_units": 35, "max_units": None, "discount_pct": 30},
    ]
    sim = simulate_order(100, 2, 9, tiers)
    assert sim["units"] == 18
    assert sim["discount_pct"] == 10
    assert sim["net"] == 1620


def test_max_boxes_respects_net_limit():
    tiers = [{"min_units": 35, "max_units": None, "discount_pct": 30}]
    result = max_boxes_by_approved_limit(3500, 500, 9, tiers)
    assert result["net"] <= 3500
