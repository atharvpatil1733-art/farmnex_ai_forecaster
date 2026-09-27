# Sample responses

Live calls against `uvicorn app.main:app` (one per endpoint), recorded by the build session.
Long lists (meta pairs, sell options, demand pairs) are trimmed for readability; `...` marks cuts.

## GET /health

HTTP 200
```json
{
  "status": "ok",
  "model_version": "20260927T164925Z-asof20251030",
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
      "lat": 18.4905,
      "lon": 73.866,
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
  "model_version": "20260927T164925Z-asof20251030",
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
      "arrivals_source": "synthetic",
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
      "p10": 1038.1,
      "p50": 1061.7,
      "p90": 1184.9,
      "arrivals_p50_tonnes": 1141.0,
      "likely_closed": false
    },
    {
      "date": "2025-11-01",
      "horizon": 2,
      "p10": 1024.0,
      "p50": 1056.5,
      "p90": 1180.1,
      "arrivals_p50_tonnes": 1204.8,
      "likely_closed": true
    },
    {
      "date": "2025-11-02",
      "horizon": 3,
      "p10": 1003.6,
      "p50": 1056.5,
      "p90": 1186.5,
      "arrivals_p50_tonnes": 1238.1,
      "likely_closed": false
    }
  ],
  "reason": [
    "14-day average price (1,040 Rs/q) lowers the forecast by ~3%",
    "latest price (1,100 Rs/q) lowers the forecast by ~2%",
    "28-day average price (986 Rs/q) lowers the forecast by ~2%"
  ],
  "model_version": "20260927T164925Z-asof20251030",
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
      "price_change_pct": -1.9,
      "arrivals_change_pct": -2.8,
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
        "price -1.9% and arrivals -2.8%: no clear imbalance (threshold 3.0%)",
        "median over 12 Pune markets, p50 forecast for 2025-10-31 vs 7-day average",
        "13 of 14 markets have real Onion prices; arrivals partly synthetic"
      ]
    },
    {
      "crop": "Tomato",
      "signal": "LOW",
      "price_change_pct": -5.1,
      "arrivals_change_pct": -0.3,
      "data_source": "real",
      "as_of": "2025-10-30",
      "pairs": [
        {
          "market": "Pune",
          "crop": "Tomato",
          "price_source": "real",
          "arrivals_source": "synthetic",
          "last_real_price_date": "2025-10-30"
        },
        {
          "market": "Pimpri",
          "crop": "Tomato",
          "price_source": "real",
          "arrivals_source": "synthetic",
          "last_real_price_date": "2025-10-30"
        },
        "..."
      ],
      "reason": [
        "price expected -5.1% while arrivals -0.3%: supply outpacing demand",
        "median over 6 Pune markets, p50 forecast for 2025-10-31 vs 7-day average",
        "8 of 14 markets have real Tomato prices; arrivals partly synthetic"
      ]
    },
    {
      "crop": "Potato",
      "signal": "NORMAL",
      "price_change_pct": -2.3,
      "arrivals_change_pct": -5.9,
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
          "price_source": "synthetic",
          "arrivals_source": "synthetic",
          "last_real_price_date": null
        },
        "..."
      ],
      "reason": [
        "price -2.3% and arrivals -5.9%: no clear imbalance (threshold 3.0%)",
        "median over 14 Pune markets, p50 forecast for 2025-10-31 vs 7-day average",
        "8 of 14 markets have real Potato prices; arrivals partly synthetic"
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
{"lat": 18.52, "lon": 73.85, "crop": "Onion", "qty_quintal": 20, "radius_km": 80}
```

HTTP 200
```json
{
  "crop": "Onion",
  "qty_quintal": 20.0,
  "radius_km": 80.0,
  "forecast_origin": "2025-10-30",
  "best": {
    "market": "Manchar",
    "district": "Pune",
    "distance_km": 54.7,
    "best_day": "2025-10-31",
    "asking_price": 1445.0,
    "floor_price": 1171.4,
    "transport_cost_per_quintal": 54.7,
    "net_price_per_quintal": 1390.3,
    "net_total": 27806.0,
    "likely_closed_days": [
      "2025-11-01"
    ],
    "data_source": "real",
    "as_of": "2025-10-28",
    "reason": [
      "best open day 2025-10-31 (p50 1,445 Rs/q) minus transport 55 km x 1.0 Rs/km/q = 55 Rs/q",
      "7-day average price (no report) raises the forecast by ~12%",
      "14-day price volatility raises the forecast by ~4%",
      "14-day average price (no report) raises the forecast by ~3%"
    ]
  },
  "options": [
    {
      "market": "Manchar",
      "district": "Pune",
      "distance_km": 54.7,
      "best_day": "2025-10-31",
      "asking_price": 1445.0,
      "floor_price": 1171.4,
      "transport_cost_per_quintal": 54.7,
      "net_price_per_quintal": 1390.3,
      "net_total": 27806.0,
      "likely_closed_days": [
        "2025-11-01"
      ],
      "data_source": "real",
      "as_of": "2025-10-28",
      "reason": [
        "best open day 2025-10-31 (p50 1,445 Rs/q) minus transport 55 km x 1.0 Rs/km/q = 55 Rs/q",
        "7-day average price (no report) raises the forecast by ~12%",
        "14-day price volatility raises the forecast by ~4%",
        "14-day average price (no report) raises the forecast by ~3%"
      ]
    },
    {
      "market": "Junnar",
      "district": "Pune",
      "distance_km": 76.5,
      "best_day": "2025-11-02",
      "asking_price": 1438.3,
      "floor_price": 1140.6,
      "transport_cost_per_quintal": 76.5,
      "net_price_per_quintal": 1361.8,
      "net_total": 27236.0,
      "likely_closed_days": [
        "2025-10-31",
        "2025-11-01"
      ],
      "data_source": "real",
      "as_of": "2025-10-30",
      "reason": [
        "best open day 2025-11-02 (p50 1,438 Rs/q) minus transport 77 km x 1.0 Rs/km/q = 76 Rs/q",
        "latest price (1,500 Rs/q) raises the forecast by ~9%",
        "7-day average price (no report) raises the forecast by ~9%",
        "14-day price volatility raises the forecast by ~4%"
      ]
    },
    {
      "market": "Pimpri",
      "district": "Pune",
      "distance_km": 13.1,
      "best_day": "2025-10-31",
      "asking_price": 1295.2,
      "floor_price": 1103.4,
      "transport_cost_per_quintal": 13.1,
      "net_price_per_quintal": 1282.1,
      "net_total": 25642.0,
      "likely_closed_days": [],
      "data_source": "real",
      "as_of": "2025-10-30",
      "reason": [
        "best open day 2025-10-31 (p50 1,295 Rs/q) minus transport 13 km x 1.0 Rs/km/q = 13 Rs/q",
        "7-day average price (1,394 Rs/q) raises the forecast by ~12%",
        "price 1 days earlier (1,700 Rs/q) raises the forecast by ~3%",
        "season (Oct) lowers the forecast by ~2%"
      ]
    },
    "..."
  ],
  "message": "11 market(s) within 80 km",
  "data_source": "real",
  "as_of": "2025-10-28",
  "reason": [
    "Manchar: highest net price among markets with the most trustworthy data (fresh real > stale real > synthetic)",
    "best open day 2025-10-31 (p50 1,445 Rs/q) minus transport 55 km x 1.0 Rs/km/q = 55 Rs/q",
    "7-day average price (no report) raises the forecast by ~12%"
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
      "crop": "Onion",
      "sowing_month": 6,
      "harvest_month": "2026-10",
      "expected_price": 2275.2,
      "method": "same_month_average",
      "in_sowing_window": true,
      "data_source": "real",
      "as_of": "2025-10-30",
      "reason": [
        "Historical Oct average is 2,275 Rs/q (+14% vs the overall average); SARIMAX not used: too little history",
        "Last 3 months averaged 1,195 Rs/q (-40% vs long-run)",
        "Sowing month fits the usual Onion calendar; harvest lands in Oct"
      ]
    },
    {
      "rank": 2,
      "crop": "Potato",
      "sowing_month": 6,
      "harvest_month": "2026-09",
      "expected_price": 1914.0,
      "method": "same_month_average",
      "in_sowing_window": true,
      "data_source": "real",
      "as_of": "2025-10-30",
      "reason": [
        "Historical Sep average is 1,914 Rs/q (+5% vs the overall average); SARIMAX not used: too little history",
        "Last 3 months averaged 1,418 Rs/q (-22% vs long-run)",
        "Sowing month fits the usual Potato calendar; harvest lands in Sep"
      ]
    },
    {
      "rank": 3,
      "crop": "Tomato",
      "sowing_month": 6,
      "harvest_month": "2026-10",
      "expected_price": 1135.7,
      "method": "same_month_average",
      "in_sowing_window": true,
      "data_source": "real",
      "as_of": "2025-10-30",
      "reason": [
        "Historical Oct average is 1,136 Rs/q (-34% vs the overall average); SARIMAX not used: too little history",
        "Last 3 months averaged 1,802 Rs/q (+5% vs long-run)",
        "Sowing month fits the usual Tomato calendar; harvest lands in Oct"
      ]
    }
  ],
  "note": "Ranked by expected modal price (Rs/quintal) at harvest; yields and input costs differ by crop and are not included.",
  "attribution": "Data: Centre for Economic Data & Analysis (CEDA), Ashoka University, from Agmarknet"
}
```
