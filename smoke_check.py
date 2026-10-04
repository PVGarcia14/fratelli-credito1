import importlib
import sys

m = importlib.import_module('credit_engine')
required = ['clean_cnpj','validate_cnpj','analyze','box_calc','suggest_products','order_value_for_boxes','max_boxes_within_limit']
missing = [name for name in required if not hasattr(m,name)]
if missing:
    raise SystemExit('Funções ausentes em credit_engine.py: ' + ', '.join(missing))
import config
for name in ['PRODUCTS','PAYMENT_TERMS','LIMIT_BANDS']:
    if not hasattr(config,name):
        raise SystemExit('Configuração ausente: ' + name)
print('SMOKE OK:', ', '.join(required))
