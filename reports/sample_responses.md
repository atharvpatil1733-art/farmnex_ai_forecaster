# Sample responses

Live calls against `uvicorn app.main:app` (one per endpoint), on CEDA API data (2012-01-01 .. 2025-10-30).
Long lists (meta pairs, sell options, demand pairs) are trimmed for readability; `...` marks cuts.

## GET /health

HTTP 200
```json
{
  "status": "ok",
  "model_version": "20260928T073941Z-asof20251030",
  "data_as_of": "2025-10-30"
}
```

## GET /meta

HTTP 200
```json
{
  "markets": [
    {
      "market": "Pune",
      "district": "Pune",
      "lat": 18.4918,
      "lon": 73.8676,
      "likely_closed_weekdays": [
        "Sat"
      ]
    },
    {
      "market": "Pimpri",
      "district": "Pune",
      "lat": 18.6279,
      "lon": 73.8009,
      "likely_closed_weekdays": []
    },
    {
      "market": "Manjri",
      "district": "Pune",
      "lat": 18.514,
      "lon": 73.976,
      "likely_closed_weekdays": []
    },
    "..."
  ],
  "crops": [
    "Onion",
    "Tomato",
    "Potato"
  ],
  "districts": [
    "Pune",
    "Thane"
  ],
  "data_as_of": "2025-10-30",
  "model_version": "20260928T073941Z-asof20251030",
  "pairs": [
    {
      "market": "Pune",
      "crop": "Onion",
      "price_source": "real",
      "arrivals_source": "real",
      "last_real_price_date": "2025-10-30"
    },
    {
      "market": "Pune",
      "crop": "Tomato",
      "price_source": "real",
      "arrivals_source": "real",
      "last_real_price_date": "2025-10-30"
    },
    {
      "market": "Pune",
      "crop": "Potato",
      "price_source": "real",
      "arrivals_source": "real",
      "last_real_price_date": "2025-10-30"
    },
    {
      "market": "Pimpri",
      "crop": "Onion",
      "price_source": "real",
      "arrivals_source": "real",
      "last_real_price_date": "2025-10-30"
    },
    "..."
  ],
  "demand_note": "Demand is a PROXY derived from mandi data (predicted modal price change vs predicted arrivals change), not measured consumer demand.",
  "attribution": "Data: Centre for Economic Data & Analysis (CEDA), Ashoka University, from Agmarknet"
}
```

## GET /forecast/price?market=Pune&crop=Onion&days=3

HTTP 200
```json
{
  "market": "Pune",
  "crop": "Onion",
  "district": "Pune",
  "forecast_origin": "2025-10-30",
  "as_of": "2025-10-30",
  "data_source": "real",
  "arrivals_data_source": "real",
  "last_price": 1100.0,
  "last_price_date": "2025-10-30",
  "days": [
    {
      "date": "2025-10-31",
      "horizon": 1,
      "p10": 981.1,
      "p50": 1114.2,
      "p90": 1286.6,
      "arrivals_p50_tonnes": 1258.2,
      "likely_closed": false
    },
    {
      "date": "2025-11-01",
      "horizon": 2,
      "p10": 952.6,
      "p50": 1108.2,
      "p90": 1287.8,
      "arrivals_p50_tonnes": 1342.8,
      "likely_closed": true
    },
    {
      "date": "2025-11-02",
      "horizon": 3,
      "p10": 956.1,
      "p50": 1117.9,
      "p90": 1311.0,
      "arrivals_p50_tonnes": 1343.1,
      "likely_closed": false
    }
  ],
  "reason": [
    "average price over the last 14 days (1,040 Rs/quintal) lowers the forecast by ~9%",
    "average price over the last 7 days (1,146 Rs/quintal) raises the forecast by ~3%",
    "latest price (1,100 Rs/quintal) lowers the forecast by ~2%"
  ],
  "model_version": "20260928T073941Z-asof20251030",
  "attribution": "Data: Centre for Economic Data & Analysis (CEDA), Ashoka University, from Agmarknet"
}
```

## GET /forecast/demand?district=Pune

HTTP 200
```json
{
  "district": "Pune",
  "date": "2025-10-31",
  "forecast_origin": "2025-10-30",
  "items": [
    {
      "crop": "Onion",
      "signal": "NORMAL",
      "price_change_pct": 2.1,
      "arrivals_change_pct": -13.6,
      "data_source": "real",
      "as_of": "2025-10-30",
      "pairs": [
        {
          "market": "Pune",
          "crop": "Onion",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2025-10-30"
        },
        {
          "market": "Pimpri",
          "crop": "Onion",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2025-10-30"
        },
        "..."
      ],
      "reason": [
        "price expected to change +2.1% and arrivals -13.6%: no clear shortage or glut (moves under 3% count as flat)",
        "typical change across 11 Pune markets: expected price on 2025-10-31 vs the last 7 days' average",
        "14 of 14 markets have real Onion prices"
      ]
    },
    {
      "crop": "Tomato",
      "signal": "NORMAL",
      "price_change_pct": -1.5,
      "arrivals_change_pct": -5.9,
      "data_source": "real",
      "as_of": "2025-10-30",
      "pairs": [
        {
          "market": "Pune",
          "crop": "Tomato",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2025-10-30"
        },
        {
          "market": "Pimpri",
          "crop": "Tomato",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2025-10-30"
        },
        "..."
      ],
      "reason": [
        "price expected to change -1.5% and arrivals -5.9%: no clear shortage or glut (moves under 3% count as flat)",
        "typical change across 13 Pune markets: expected price on 2025-10-31 vs the last 7 days' average",
        "9 of 14 markets have real Tomato prices; arrivals partly synthetic"
      ]
    },
    {
      "crop": "Potato",
      "signal": "NORMAL",
      "price_change_pct": -1.4,
      "arrivals_change_pct": -3.4,
      "data_source": "real",
      "as_of": "2025-10-30",
      "pairs": [
        {
          "market": "Pune",
          "crop": "Potato",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2025-10-30"
        },
        {
          "market": "Pimpri",
          "crop": "Potato",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2025-07-10"
        },
        "..."
      ],
      "reason": [
        "price expected to change -1.4% and arrivals -3.4%: no clear shortage or glut (moves under 3% count as flat)",
        "typical change across 12 Pune markets: expected price on 2025-10-31 vs the last 7 days' average",
        "10 of 14 markets have real Potato prices; arrivals partly synthetic"
      ]
    }
  ],
  "note": "Demand is a PROXY derived from mandi data (predicted modal price change vs predicted arrivals change), not measured consumer demand.",
  "attribution": "Data: Centre for Economic Data & Analysis (CEDA), Ashoka University, from Agmarknet"
}
```

## POST /forecast/sell-options

Request body:
```json
{"lat": 19.1, "lon": 73.97, "crop": "Onion", "qty_quintal": 50, "radius_km": 80}
```

HTTP 200
```json
{
  "crop": "Onion",
  "qty_quintal": 50.0,
  "radius_km": 80.0,
  "forecast_origin": "2025-10-30",
  "best": {
    "market": "Junnar",
    "district": "Pune",
    "distance_km": 15.6,
    "best_day": "2025-11-02",
    "asking_price": 1633.4,
    "floor_price": 995.4,
    "transport_cost_per_quintal": 15.6,
    "net_price_per_quintal": 1617.8,
    "net_total": 80890.0,
    "likely_closed_days": [
      "2025-10-31",
      "2025-11-01"
    ],
    "typical_daily_arrivals_quintal": 7570.5,
    "thin_market": false,
    "data_source": "real",
    "as_of": "2025-10-30",
    "reason": [
      "best open day 2025-11-02: expected price 1,633 Rs/quintal, minus transport for 16 km at 1 Rs/km per quintal = 16 Rs/quintal",
      "latest price (1,500 Rs/quintal) raises the forecast by ~10%",
      "season (Oct) raises the forecast by ~4%",
      "market (Junnar) raises the forecast by ~2%"
    ]
  },
  "options": [
    {
      "market": "Junnar",
      "district": "Pune",
      "distance_km": 15.6,
      "best_day": "2025-11-02",
      "asking_price": 1633.4,
      "floor_price": 995.4,
      "transport_cost_per_quintal": 15.6,
      "net_price_per_quintal": 1617.8,
      "net_total": 80890.0,
      "likely_closed_days": [
        "2025-10-31",
        "2025-11-01"
      ],
      "typical_daily_arrivals_quintal": 7570.5,
      "thin_market": false,
      "data_source": "real",
      "as_of": "2025-10-30",
      "reason": [
        "best open day 2025-11-02: expected price 1,633 Rs/quintal, minus transport for 16 km at 1 Rs/km per quintal = 16 Rs/quintal",
        "latest price (1,500 Rs/quintal) raises the forecast by ~10%",
        "season (Oct) raises the forecast by ~4%",
        "market (Junnar) raises the forecast by ~2%"
      ]
    },
    {
      "market": "Otur",
      "district": "Pune",
      "distance_km": 18.5,
      "best_day": "2025-11-02",
      "asking_price": 1621.8,
      "floor_price": 1146.4,
      "transport_cost_per_quintal": 18.5,
      "net_price_per_quintal": 1603.3,
      "net_total": 80165.0,
      "likely_closed_days": [
        "2025-10-31",
        "2025-11-01"
      ],
      "typical_daily_arrivals_quintal": 12876.0,
      "thin_market": false,
      "data_source": "real",
      "as_of": "2025-10-30",
      "reason": [
        "best open day 2025-11-02: expected price 1,622 Rs/quintal, minus transport for 18 km at 1 Rs/km per quintal = 18 Rs/quintal",
        "latest price (1,800 Rs/quintal) raises the forecast by ~15%",
        "average price over the last 28 days (1,375 Rs/quintal) lowers the forecast by ~2%",
        "season (Oct) raises the forecast by ~2%"
      ]
    },
    {
      "market": "Manchar",
      "district": "Pune",
      "distance_km": 11.0,
      "best_day": "2025-11-02",
      "asking_price": 1593.6,
      "floor_price": 1217.2,
      "transport_cost_per_quintal": 11.0,
      "net_price_per_quintal": 1582.6,
      "net_total": 79130.0,
      "likely_closed_days": [
        "2025-11-01"
      ],
      "typical_daily_arrivals_quintal": 8739.5,
      "thin_market": false,
      "data_source": "real",
      "as_of": "2025-10-28",
      "reason": [
        "best open day 2025-11-02: expected price 1,594 Rs/quintal, minus transport for 11 km at 1 Rs/km per quintal = 11 Rs/quintal",
        "price 2 days earlier (1,700 Rs/quintal) raises the forecast by ~5%",
        "season (Oct) raises the forecast by ~2%",
        "average price over the last 28 days (1,464 Rs/quintal) lowers the forecast by ~1%"
      ]
    },
    "..."
  ],
  "message": "12 market(s) within 80 km",
  "data_source": "real",
  "as_of": "2025-10-30",
  "reason": [
    "Junnar: highest net price among markets with the most trustworthy data (fresh real on a big enough market > thin or stale real > synthetic)",
    "best open day 2025-11-02: expected price 1,633 Rs/quintal, minus transport for 16 km at 1 Rs/km per quintal = 16 Rs/quintal",
    "latest price (1,500 Rs/quintal) raises the forecast by ~10%"
  ],
  "attribution": "Data: Centre for Economic Data & Analysis (CEDA), Ashoka University, from Agmarknet"
}
```

## GET /forecast/crops?district=Pune&sowing_month=6&k=5

HTTP 200
```json
{
  "district": "Pune",
  "sowing_month": 6,
  "forecast_origin": "2025-10-30",
  "items": [
    {
      "rank": 1,
      "crop": "Potato",
      "sowing_month": 6,
      "harvest_month": "2026-09",
      "expected_price": 1382.7,
      "method": "sarimax",
      "in_sowing_window": true,
      "data_source": "real",
      "as_of": "2025-10-30",
      "reason": [
        "SARIMAX on 130 months of prices expects 1,383 Rs/quintal in Sep (+2% vs the long-run average)",
        "Last 3 months averaged 1,442 Rs/quintal (+6% vs long-run)",
        "Sowing month fits the usual Potato calendar; harvest lands in Sep"
      ]
    },
    {
      "rank": 2,
      "crop": "Tomato",
      "sowing_month": 6,
      "harvest_month": "2026-10",
      "expected_price": 1277.6,
      "method": "sarimax",
      "in_sowing_window": true,
      "data_source": "real",
      "as_of": "2025-10-30",
      "reason": [
        "SARIMAX on 130 months of prices expects 1,278 Rs/quintal in Oct (-14% vs the long-run average)",
        "Last 3 months averaged 1,887 Rs/quintal (+27% vs long-run)",
        "Sowing month fits the usual Tomato calendar; harvest lands in Oct"
      ]
    },
    {
      "rank": 3,
      "crop": "Onion",
      "sowing_month": 6,
      "harvest_month": "2026-10",
      "expected_price": 1173.3,
      "method": "sarimax",
      "in_sowing_window": true,
      "data_source": "real",
      "as_of": "2025-10-30",
      "reason": [
        "SARIMAX on 129 months of prices expects 1,173 Rs/quintal in Oct (-25% vs the long-run average)",
        "Last 3 months averaged 1,195 Rs/quintal (-24% vs long-run)",
        "Sowing month fits the usual Onion calendar; harvest lands in Oct"
      ]
    }
  ],
  "note": "Ranked by expected modal price (Rs/quintal) at harvest; yields and input costs differ by crop and are not included.",
  "attribution": "Data: Centre for Economic Data & Analysis (CEDA), Ashoka University, from Agmarknet"
}
```
