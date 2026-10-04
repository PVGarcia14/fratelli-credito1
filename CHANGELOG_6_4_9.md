# 6.4.9

- Fixed deployment ImportError when an older `config.py` does not yet expose `COMMERCIAL_DISCOUNT_TIERS`.
- Added compatibility fallback in `app.py` and `credit_engine.py`.
- Moved `order_value_for_boxes` to the main engine import in `app.py`, preventing a later simulation NameError.
- Added `smoke_test.py` for startup/import validation.
- Existing user database, authentication, audit, analysis history and catalog configuration remain intact.
