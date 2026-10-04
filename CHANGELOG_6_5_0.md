# 6.5.0

- Reworked commercial calculation around the actual available credit balance.
- Product names, prices and units/box are read directly from the configured catalog.
- Added a single `max_boxes_within_limit` calculation used by both suggestions and simulation.
- Net value after configured discount is the value compared with available credit.
- Binary search prevents underestimating whole-box quantity when discounts apply.
- Fixed simulation safe-box calculation to use the same discounted net-value logic.
- Added boundary tests for 1–2 boxes, 3 boxes up to 34 units, and 36+ units.
- Added test proving the maximum quantity calculation accounts for discount.
- Preserved login, users, audit, history, logo and database architecture.
- Generic catalog/discount configuration only; no restricted-product catalog values are embedded.
