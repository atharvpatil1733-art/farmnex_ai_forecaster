# Data

## data/raw/
- `ceda/` (git-ignored): raw responses from the CEDA Agmarknet API, written by
  `python -m forecaster.ceda`. One JSON per indicator x crop x date window, plus `ref/`
  (id lookups, market lists) and `manifest.json` (what the last run fetched or skipped).
  This is the **primary** source: full daily history for the Pune-district mandis in config.
- `*_price_data.csv`, `*_quantity_data.csv`: the first manual CEDA website exports (Onion,
  Potato price + quantity; Tomato price only). Nine of them hit the ~1000-row export cap and
  keep only Mar/Jun-Oct 2024 and Apr/May-Oct 2025. Used only as a fallback when the API cache
  is empty (`data_prep.source: auto`).
- `mandi.csv`: cleaned output, **generated**; do not edit by hand. Rebuild with
  `python -m forecaster.data` (also rewrites `reports/data_quality.md`, which says which
  source was used). Schema: date, district, market, commodity, min_price, max_price,
  modal_price (Rs/quintal), arrivals_tonnes. Rows with arrivals but no price that day keep
  modal_price empty; price models must filter on it.

Market and crop name aliases live in `config.yaml`; add new spellings there, not in code.

**Attribution:** data from Centre for Economic Data & Analysis (CEDA), Ashoka University,
based on Agmarknet. Free for non-commercial use; show the CEDA logo and credit in any chart or
app that uses it (https://ceda.ashoka.edu.in/api-terms-conditions/).

## data/ref/, data/synthetic/
Not created yet (next step). Reference files will be approximate values and marked as such here.
