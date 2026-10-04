# B2B Credit Decision Engine 6.5.0

This release focuses on one critical rule: the available credit balance is the absolute ceiling for a commercial suggestion.

For each configured product, the engine:
1. reads the product name, unit price and units per box from `config.py`;
2. tests whole-box quantities;
3. determines the configured discount tier;
4. calculates gross value, discount and net value;
5. accepts only quantities whose net value is <= available credit;
6. returns the largest valid whole-box quantity.

The same calculation is used by the suggestion screen and order simulation.

The catalog and discount tiers are intentionally generic and configurable.
