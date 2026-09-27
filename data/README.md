# Data

## data/raw/
- `*_price_data.csv`, `*_quantity_data.csv`: real Agmarknet / data.gov.in (CEDA) exports for
  Pune district markets (Onion, Potato price + quantity; Tomato price only, no quantity).
  Nine of the files hit a 1000-row export cap and are truncated (see reports/data_quality.md).
- `mandi.csv`: cleaned output, **generated**; do not edit by hand. Rebuild with
  `python -m forecaster.data` (also rewrites `reports/data_quality.md`).
  Schema: date, district, market, commodity, min_price, max_price, modal_price (Rs/quintal),
  arrivals_tonnes (NaN for Tomato: no quantity data exists, none is invented).

Market and crop name aliases live in `config.yaml`; add new spellings there, not in code.

## data/ref/, data/synthetic/
Not created yet (next step). Reference files will be approximate values and marked as such here.
