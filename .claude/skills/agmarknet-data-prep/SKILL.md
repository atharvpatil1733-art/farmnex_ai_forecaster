---
name: agmarknet-data-prep
description: Download (CEDA Agmarknet API), clean, normalize and validate mandi price and arrivals data into the project's standard mandi.csv schema. Use this whenever raw mandi data is added or refreshed, when the date range or markets/crops change, when forecaster.ceda or data.py fails, when adding a new market or crop, or when forecasts look wrong and the input data might be the cause, even if the user doesn't say "clean the data".
---

# Agmarknet data prep

Turn CEDA Agmarknet data into `data/raw/mandi.csv` that training can trust.

```
python -m forecaster.ceda --dry-run   # request plan, no network
python -m forecaster.ceda             # download into data/raw/ceda/ (cached, resumable)
python -m forecaster.data             # clean -> data/raw/mandi.csv + reports/data_quality.md
python -m pytest -q
```

## Target schema (exact column names)
date (YYYY-MM-DD), district, market, commodity, min_price, max_price, modal_price, arrivals_tonnes
Prices are Rs/quintal, arrivals tonnes. One row per (date, market, commodity).
A row has a price, arrivals, or both. modal_price is NaN only on arrivals-only days.

## 1. Get the data (CEDA API, never the website)
- Website exports are capped (~1000 rows) and keep only the newest dates. Never ask the user
  to re-download by hand; use `forecaster.ceda`.
- Needs `CEDA_API_KEY` in env or `.env`. If it is missing, stop and tell the user where to get
  a free key (https://api.ceda.ashoka.edu.in). Never print, log or commit the key.
- Budget: 40 requests per rolling hour. The downloader stops at `ceda.max_requests_per_run`
  (exit code 2) with everything cached; the fix is to rerun later, not to raise the budget or
  retry in a loop. Use `--dry-run` to see the cost before a big change.
- Scope comes from config.yaml: `ceda.state`, `ceda.districts`, `ceda.start_date`, crops'
  `ceda_name`. Names are resolved to ids through the API; if one fails to resolve, fix the
  name in config, never hardcode an id.
- Round row counts (`ceda.suspicious_row_counts`) mean a capped response: the downloader
  splits the window automatically. If the report still lists capped windows, lower
  `ceda.chunk_years` / `ceda.min_chunk_days`.
- The quantities endpoint is not verified against the live API yet. If it fails, prices still
  download and the manifest (`data/raw/ceda/manifest.json`) says why. If quantity rows arrive
  but the report says "no quantity column", add the real field name to `_QTY_KEYS` in data.py.
- Changing chunk settings leaves old cache files next to new ones; overlaps are removed as exact
  duplicates, but for a clean slate delete `data/raw/ceda/price` and `data/raw/ceda/quantity`.

## 2. Clean (forecaster.data does all of this; keep it that way)
1. **Source**: `data_prep.source` = auto (API cache if present, else the old exports in
   data/raw/). Never combine both: same underlying data, it double-counts.
2. **Rename columns** by fuzzy match (exports) or read API fields directly
   (min_price, max_price, modal_price, market_id -> market_name via the cached markets lists).
3. **Parse dates**: ISO as-is; other formats day-first (dd/mm/yyyy).
4. **Normalize names** with the alias map in config.yaml (`markets.*.aliases`,
   `crops.*.aliases`). Unknown names are listed in the report and dropped, never guessed.
   Add new spellings to config.yaml, not to code.
5. **Collapse varieties**: several varieties of a crop at a market on one day become one row:
   modal = mean, min = min, max = max, arrivals = sum.
6. **Fix or drop bad rows**:
   - drop exact duplicates and rows with modal_price <= 0 or missing
   - if min > max, swap them; clip modal into [min, max]
   - outlier: modal > 4x or < 0.25x the 30-day centred rolling median for that market x crop -> drop
   - prices outside the crop's plausible range -> flag in report (may be Rs/kg), never convert
7. **Arrivals**: tonnes (bare `qty` is tonnes; convert quintals / 10). Keep arrivals-only
   days (`keep_arrivals_only_rows: true`). `has_arrivals: false` on a crop forces NaN; only
   set it if the quantity data for that crop is known to be wrong.
8. **Missing days** (holidays, Sundays, no arrivals): leave them missing in mandi.csv.
   Feature code decides how to fill; never forward-fill more than 3 days.
9. **Write outputs**: data/raw/mandi.csv plus reports/data_quality.md.

## Checks before finishing
- Report says `Source: CEDA Agmarknet API cache` (unless deliberately on exports).
- No capped windows listed; date range starts near `ceda.start_date` for the main markets.
- Every configured market x crop has data, or is listed as missing (synthetic fallback).
- Coverage below 50% for a market x crop: warn that its forecasts will be weak.
- Months with no real prices for a crop are listed; with API data there should be few or none.
- Tell the user which crops have no arrivals data, if any.
- `python -m pytest -q` passes (tests mock the API; they never need the key or network).
- Any chart or app screen built on this data credits CEDA (`ceda.attribution` in config).
