# farmnex_ai_forecaster

AI demand-forecast service for FarmNex: mandi price and arrivals forecasts for Pune-district
markets (Onion, Tomato, Potato), best place and day to sell, and which crop to grow.
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

## Train and serve (in progress)

```bash
python -m forecaster.train
uvicorn app.main:app --reload
```

## Tests

```bash
python -m pytest -q
```

Tests use a fake CEDA server; no key or network needed.

## Data attribution

Mandi data: Centre for Economic Data & Analysis (CEDA), Ashoka University, from Agmarknet.
Used under the [CEDA API terms](https://ceda.ashoka.edu.in/api-terms-conditions/)
(non-commercial). Screens showing this data must display the CEDA logo and credit.
