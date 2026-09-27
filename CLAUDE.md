# farmnex_ai_forecaster: AI Demand Forecast (one-day prototype)

## Goal
Standalone FastAPI service that tells a farmer near Mumbai/Pune WHAT to grow, WHERE and WHEN
to sell, and at WHAT price. The main FarmNex backend and Flutter app call it over HTTP.
This is a PROTOTYPE: working end-to-end today beats accuracy. Use sensible defaults,
no hyperparameter tuning, full training must finish in < 5 minutes on 4 CPUs.

## Scope (all in config.yaml, never hardcode)
- Markets: Pune, Pimpri, Khed(Chakan), Manchar, Vashi (Navi Mumbai), Kalyan
- Crops: Onion, Tomato, Potato (add more only via config)

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
simple rules for SARIMAX), and `data_source`: "real" or "synthetic".

## Data
- data/raw/mandi.csv (real, may be missing at first). Schema:
  date, district, market, commodity, min_price, max_price, modal_price, arrivals_tonnes
  data.py must normalize messy market/crop names and column names from Agmarknet exports.
- synthetic.py generates 3 years of daily data per market x crop with realistic seasonality
  (monsoon spikes, festival demand, weekday effects, arrivals inversely related to price)
  into data/synthetic/. Fallback is PER market x crop: use real data where it exists,
  synthetic only for pairs with no real data. Every response reports data_source per pair.
- Real data (CEDA/Agmarknet) has gaps: markets report ~4-5 days/week, some weeks less.
  This is expected. Check arrival units (tonnes vs quintals) and convert to tonnes.
- data/ref/: markets.csv (market, district, lat, lon), crop_calendar.csv
  (crop, sowing_months, duration_days), festivals.csv (date, name). Create these yourself
  with approximate values and mark them "approximate" in data/README.md.

## Modelling
- Baseline: seasonal naive (same weekday last week). Report it next to the model.
- Main: one global LightGBM per target (price, arrivals), market & crop categorical,
  quantile objective for p10/p50/p90. Features: lags 1,2,3,7,14; rolling mean/std 7,14,28
  (shift(1) before rolling); day-of-week, month, festival within 3 days, monsoon flag.
- GAPS: before features, reindex each market x crop to a full daily calendar. Lags and
  rolling windows are by CALENDAR DAYS, never by row position. Leave missing days as NaN
  (LightGBM handles NaN); add days_since_last_report and reports_last_7d features.
  Train only on rows where the target was actually reported. Rolling stats need >= 3 points.
- Forecast days +1..+3 are calendar days; mark a day `likely_closed` if that market
  historically rarely reports on that weekday, and skip it when choosing the best day.
- If a market x crop has a gap > 14 days, don't interpolate across it.
- Validation: time split, last 60 days as test. Never random split.
- Write reports/metrics.md: MAE, MAPE per crop vs baseline. Flag crops that don't beat it.

## Layout
```
config.yaml  requirements.txt  README.md
forecaster/  schemas.py data.py synthetic.py features.py train.py explain.py recommend.py service.py
app/main.py  # FastAPI, loads artifacts once at startup, CORS enabled for Flutter web
artifacts/   # models + model_version.txt (< 50 MB)
data/ reports/ tests/
```

## API
GET  /health
GET  /meta                  -> markets, crops, districts (for Flutter dropdowns)
GET  /forecast/price?market=&crop=&days=3
GET  /forecast/demand?district=&date=
POST /forecast/sell-options {lat, lon, crop, qty_quintal, radius_km}
GET  /forecast/crops?district=&sowing_month=&k=5
All responses are Pydantic models defined in forecaster/schemas.py.

## Rules
- Python 3.11: pandas, numpy, lightgbm, statsmodels, shap, fastapi, uvicorn, pydantic, pytest.
- `python -m forecaster.train` trains everything; `uvicorn app.main:app` serves it.
- Tests: no-leakage test for features, one test per endpoint using TestClient.
- No secrets in code. No database needed today (Supabase integration comes later).
- Show a short plan first, then build. Commit often. Open a PR with metrics summary.
