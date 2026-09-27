# farmnex_ai_forecaster: AI Demand Forecast (one-day prototype)

## Goal
Standalone FastAPI service that tells a farmer near Mumbai/Pune WHAT to grow, WHERE and WHEN
to sell, and at WHAT price. The main FarmNex backend and Flutter app call it over HTTP.
This is a PROTOTYPE: working end-to-end today beats accuracy. Use sensible defaults,
no hyperparameter tuning, full training must finish in < 5 minutes on 4 CPUs.

## Scope (all in config.yaml, never hardcode)
- Markets: the Pune-district mandis listed under `markets:` in config.yaml (Pune, Pimpri,
  Khed(Chakan), Manchar, Junnar, Otur, ...). Vashi and Kalyan are planned, no real data yet
  (add their district to `ceda.districts` to fetch them).
- Crops: Onion, Tomato, Potato (add more only via config).

## Features
1. Price forecast: modal price per (market, crop) for day +1..+3 with p10/p50/p90.
2. Demand signal: HIGH/NORMAL/LOW from predicted price change vs arrivals change.
   Demand is a PROXY from mandi data; say so in API docs.
3. Best place to sell: for (lat, lon, crop, qty_quintal), rank markets within radius by
   p50 price minus transport cost (haversine km x rate_per_km_quintal in config).
   Return best market, best day (next 3), asking price (p50), floor price (p10).
4. Best crop to grow: for (district, sowing_month), estimate price at harvest month
   (sowing + crop duration from crop_calendar.csv) using SARIMAX on monthly averages;
   fall back to same-month historical average if SARIMAX fails. Rank top k.
Every answer includes `reason`: top 3 drivers in plain text (SHAP for LightGBM,
simple rules for SARIMAX), `data_source`: "real" or "synthetic", and `as_of`: the last
date with real data behind the answer.

## Data
Pipeline: `python -m forecaster.ceda` (download) -> `python -m forecaster.data` (clean) ->
`python -m forecaster.train`.
- SOURCE = CEDA Agmarknet API (Ashoka University), via forecaster/ceda.py. Do NOT scrape the
  CEDA website and do NOT rely on manual downloads: website exports are capped at ~1000 rows
  and silently drop the oldest dates (this is what happened to the first data/raw/*.csv files).
  - Needs `CEDA_API_KEY` (free) in env or `.env`; never commit it. See .env.example.
  - Rate limit 40 requests/hour: the downloader has a per-run budget, caches every response
    under data/raw/ceda/ (git-ignored) and resumes on rerun. Never loop on 429s.
  - API responses are id-based; the downloader resolves names -> ids from the API itself,
    never hardcode ids. Its module docstring is the source of truth for endpoints/shapes.
  - CEDA data lags weeks to months. Forecasts are anchored at the last real date (`as_of`),
    not "today". A live daily feed (data.gov.in) is a later step, not today.
  - The old website exports in data/raw/*.csv are a fallback only (`data_prep.source`).
    Never mix both sources.
- data/raw/mandi.csv (generated, committed). Schema:
  date, district, market, commodity, min_price, max_price, modal_price, arrivals_tonnes
  data.py normalizes market/crop names via config aliases (skill: agmarknet-data-prep).
  Arrivals-only days are KEPT with modal_price = NaN: price models filter on
  `modal_price.notna()`, the arrivals model uses them. Tomato arrivals come from real
  quantity data if the API has it; never estimate or invent arrivals.
- synthetic.py generates 3 years of daily data per market x crop with realistic seasonality
  (monsoon spikes, festival demand, weekday effects, arrivals inversely related to price)
  into data/synthetic/. Fallback is PER market x crop (and per target: a pair with real
  prices but no arrivals uses synthetic arrivals only). Real data wins wherever it exists.
  Every response reports data_source per pair.
- Real data has gaps: markets report ~4-5 days/week, some weeks less. This is expected.
  Arrivals are in tonnes (the bare `qty` field is tonnes; see reports/data_quality.md).
- data/ref/: markets.csv (market, district, lat, lon), crop_calendar.csv
  (crop, sowing_months, duration_days), festivals.csv (date, name). Create these yourself
  with approximate values and mark them "approximate" in data/README.md.
- ATTRIBUTION (CEDA terms, non-commercial use): `/meta` returns `ceda.attribution` from
  config; the Flutter app must show the CEDA logo (bottom right) and that credit wherever it
  shows these prices, and must not imply CEDA endorses FarmNex. Commercial use needs CEDA's
  permission first.

## Modelling (settings under `modelling:` in config.yaml)
- Train from `modelling.train_start` (2015 by default); older fetched history is only used
  for long-run seasonal averages. Check in reports whether older data helps before changing it.
- Baseline: seasonal naive (same weekday last week). Report it next to the model.
- Main: LightGBM, one global model per target (price, arrivals) x quantile (p10/p50/p90),
  market & crop categorical. DIRECT multi-horizon: stack training rows for h in
  `modelling.horizons` with `horizon` as a feature, target = value at t+h. Never feed a
  prediction back in as a lag (no recursive forecasting).
  Features: lags 1,2,3,7,14; rolling mean/std 7,14,28 (shift(1) before rolling);
  day-of-week and month of the TARGET day, festival within 3 days, monsoon flag.
  Arrivals features for the price model come from real arrivals only (NaN if none).
- GAPS: before features, reindex each market x crop to a full daily calendar. Lags and
  rolling windows are by CALENDAR DAYS, never by row position. Leave missing days as NaN
  (LightGBM handles NaN); add days_since_last_report and reports_last_7d features.
  Train only on rows where the target was actually reported. Rolling stats need >= 3 points.
- Forecast days +1..+3 are calendar days after `as_of`; mark a day `likely_closed` if that
  market historically rarely reports on that weekday, and skip it when choosing the best day.
- If a market x crop has a gap > 14 days, don't interpolate across it.
- Validation: time split, last `modelling.test_days` (60) days as test. Never random split.
  Split BEFORE building stacked horizon rows so no target date leaks across the split.
- Write reports/metrics.md: MAE, MAPE per crop and horizon vs baseline, quantile coverage
  (share of actuals inside p10..p90). Flag crops that don't beat the baseline.

## Layout
```
config.yaml  requirements.txt  README.md  .env.example
forecaster/  ceda.py data.py schemas.py synthetic.py features.py train.py explain.py recommend.py service.py
app/main.py  # FastAPI, loads artifacts once at startup, CORS enabled for Flutter web
artifacts/   # models + model_version.txt (< 50 MB)
data/raw/    # mandi.csv (committed), ceda/ API cache (git-ignored), old exports (fallback)
data/ref/ data/synthetic/ reports/ tests/
```

## API
GET  /health
GET  /meta                  -> markets, crops, districts (for Flutter dropdowns), data_as_of,
                               attribution
GET  /forecast/price?market=&crop=&days=3
GET  /forecast/demand?district=&date=
POST /forecast/sell-options {lat, lon, crop, qty_quintal, radius_km}
GET  /forecast/crops?district=&sowing_month=&k=5
All responses are Pydantic models defined in forecaster/schemas.py.

## Rules
- Python 3.11, dependencies in requirements.txt (pandas, numpy, lightgbm, statsmodels, shap,
  fastapi, uvicorn, pydantic, httpx, python-dotenv, pyyaml, pytest).
- `python -m forecaster.train` trains everything; `uvicorn app.main:app` serves it.
  Training and serving read data/raw/mandi.csv only; they never call the CEDA API.
- Tests never touch the network: mock CEDA with httpx.MockTransport (see tests/test_ceda.py).
  Also: no-leakage test for features, one test per endpoint using TestClient.
- No secrets in code or logs (ceda.py scrubs the key from errors). No database needed today
  (Supabase integration comes later).
- Show a short plan first, then build. Commit often. Open a PR with metrics summary.
