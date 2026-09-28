# farmnex_ai_forecaster

AI demand-forecast service for FarmNex: mandi price and arrivals forecasts for Pune-district
mandis plus Vashi (Navi Mumbai) and Kalyan (Onion, Tomato, Potato), best place and day to sell, and which crop to grow.
Standalone FastAPI service called by the FarmNex backend and Flutter app. Prototype.

## Setup

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your free CEDA API key
```

## Data pipeline

```bash
python -m forecaster.ceda --dry-run   # show the request plan (no network)
python -m forecaster.ceda             # download history from the CEDA Agmarknet API
python -m forecaster.data             # clean -> data/raw/mandi.csv, reports/data_quality.md
```

The API allows 40 requests per hour. The downloader caches every response and stops before
the limit; if it says "Stopped early", rerun it in an hour and it continues where it left off.
All settings (markets, crops, date range, chunk size) are in `config.yaml`.

## Train and serve

```bash
python -m forecaster.train          # ~20 s on 4 CPUs -> artifacts/, reports/metrics.md
uvicorn app.main:app                # loads artifacts once; docs at http://localhost:8000/docs
```

`python -m forecaster.synthetic` writes the synthetic fallback data to `data/synthetic/` for
inspection; training and serving rebuild it in memory (deterministic, < 1 s).

| Endpoint | What it answers |
|---|---|
| `GET /health` | status, model version, data as_of |
| `GET /meta` | markets (lat/lon, likely-closed weekdays), crops, districts, real/synthetic per pair, attribution |
| `GET /forecast/price?market=&crop=&days=3` | p10/p50/p90 modal price (+ arrivals) for day +1..+3 after as_of |
| `GET /forecast/demand?district=&date=` | HIGH/NORMAL/LOW per crop (a PROXY from mandi data) |
| `POST /forecast/sell-options` `{lat, lon, crop, qty_quintal, radius_km}` | best market and day, asking (p50) and floor (p10) price, net of transport |
| `GET /forecast/crops?district=&sowing_month=&k=5` | crops ranked by expected price at harvest |

Every answer carries `reason`, `data_source` ("real"/"synthetic") and `as_of` (last real data
date). Market x crop pairs with no real prices are hidden by default (404, left out of lists);
set `api.show_synthetic: true` in `config.yaml` to show them for demos.

**Flutter app setup:**
- **CORS:** local development on `localhost` (any port) works out of the box. For production, add the web app's origin to `api.cors_origins` in `config.yaml`, or set
  `FARMNEX_CORS_ORIGINS="https://app.example.com"`.
- **CEDA attribution:** show `/meta.attribution_details` on every screen or chart with these prices. Put the official CEDA logo at the bottom right (download it from the `terms_url` page and bundle it as an asset), show the text credit, and don't imply that CEDA endorses FarmNex. Forecasts start from the data's last date (`forecast_origin`), not today, because CEDA
data lags. See `REVIEW.md` for assumptions and limitations, `reports/` for metrics, data
quality and sample responses.

## Connecting it to FarmNex (Flutter + FastAPI backend + Supabase)

Step-by-step beginner guide: [`integration/INTEGRATION.md`](integration/INTEGRATION.md). It
includes a ready backend router, a Supabase table and Flutter code. Hosting needs no Docker:
Render.com, build `pip install -r requirements.txt`, start
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

Set `FARMNEX_FORECASTER_API_KEY` on the forecaster so only your backend can call it: every
endpoint except `/health` then needs the `X-API-Key` header. With it unset, the API is open,
which is fine for local development.

## Tests

```bash
python -m pytest -q
```

Tests use a fake CEDA server; no key or network needed.

## Data attribution

Mandi data: Centre for Economic Data & Analysis (CEDA), Ashoka University, from Agmarknet.
Used under the [CEDA API terms](https://ceda.ashoka.edu.in/api-terms-conditions/)
(non-commercial). Screens showing this data must display the CEDA logo and credit.
