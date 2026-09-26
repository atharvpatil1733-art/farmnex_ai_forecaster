---
name: agmarknet-data-prep
description: Clean, normalize and validate Agmarknet / data.gov.in mandi price and arrivals exports into the project's standard mandi.csv schema. Use this whenever raw mandi data is added or refreshed, when data.py fails to load real data, when adding a new market or crop, or when forecasts look wrong and the input data might be the cause, even if the user doesn't say "clean the data".
---

# Agmarknet data prep

Turn messy mandi exports into `data/raw/mandi.csv` that training can trust.

## Target schema (exact column names)
date (YYYY-MM-DD), district, market, commodity, min_price, max_price, modal_price, arrivals_tonnes
Prices are Rs/quintal. One row per (date, market, commodity).

## Steps
1. **Load everything** in data/raw/ (csv, xls, xlsx). Exports often have title rows above
   the header and footer/total rows at the bottom: detect the real header row, drop footers.
2. **Rename columns** by fuzzy match (e.g. "Arrival Date", "Price Date" -> date;
   "Modal Price (Rs./Quintal)" -> modal_price; "Arrivals (Tonnes)" -> arrivals_tonnes).
3. **Parse dates** in all formats seen (dd/mm/yyyy, dd-mm-yyyy, "01 Jan 2024"). Use dayfirst=True.
4. **Normalize names** with the alias map in config.yaml (`market_aliases`, `crop_aliases`).
   Strip "APMC", brackets, extra spaces; title-case. Unknown names: list them in the report,
   never guess silently. Add new aliases to config.yaml, not to code.
5. **Collapse varieties**: if a market has several varieties/grades of a crop on one day,
   combine into one row: modal = arrivals-weighted mean (plain mean if arrivals missing),
   min = min, max = max, arrivals = sum.
6. **Fix or drop bad rows**:
   - drop exact duplicates and rows with modal_price <= 0 or missing
   - if min > max, swap them; clip modal into [min, max]
   - outlier: modal > 4x or < 0.25x the 30-day rolling median for that market x crop -> drop
   - prices that look like Rs/kg (far below the crop's usual range) -> flag in report, don't convert blindly
7. **Missing days** (holidays, Sundays, no arrivals): leave them missing in mandi.csv.
   Feature code decides how to fill; never forward-fill more than 3 days.
8. **Write outputs**: data/raw/mandi.csv plus reports/data_quality.md with rows before/after,
   date range and coverage % per market x crop, dropped-row counts by reason, unknown names.

## Checks before finishing
- Every configured market x crop has data, or is listed as missing in the report.
- Coverage below 50% for a market x crop: warn that its forecasts will be weak.
- Run the existing tests; the data loader test must pass on the new file.
