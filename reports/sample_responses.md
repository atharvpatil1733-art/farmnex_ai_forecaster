# Sample responses

Live calls against `uvicorn app.main:app` (one per endpoint, plus Thane/Vashi/Kalyan and a hidden synthetic pair), on CEDA API data (2012-01-01 .. 2025-10-30), districts Pune, Thane and Mumbai.
Long lists (meta markets/pairs, sell options, demand pairs) are trimmed for readability; `...` marks cuts.

## GET /health

HTTP 200
```json
{
  "status": "ok",
  "model_version": "20260928T081539Z-asof20251030",
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
      ],
      "crops": [
        "Onion",
        "Tomato",
        "Potato"
      ]
    },
    {
      "market": "Pimpri",
      "district": "Pune",
      "lat": 18.6279,
      "lon": 73.8009,
      "likely_closed_weekdays": [],
      "crops": [
        "Onion",
        "Tomato",
        "Potato"
      ]
    },
    {
      "market": "Manjri",
      "district": "Pune",
      "lat": 18.514,
      "lon": 73.976,
      "likely_closed_weekdays": [],
      "crops": [
        "Onion",
        "Tomato",
        "Potato"
      ]
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
  "model_version": "20260928T081539Z-asof20251030",
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
    "..."
  ],
  "demand_note": "Demand is a PROXY derived from mandi data (predicted modal price change vs predicted arrivals change), not measured consumer demand.",
  "synthetic_shown": false,
  "attribution": "Data: Centre for Economic Data & Analysis (CEDA), Ashoka University, from Agmarknet",
  "attribution_details": {
    "text": "Data: Centre for Economic Data & Analysis (CEDA), Ashoka University, from Agmarknet",
    "terms_url": "https://ceda.ashoka.edu.in/api-terms-conditions/",
    "logo_placement": "bottom right",
    "rules": [
      "Show the official CEDA logo (https://ceda.ashoka.edu.in/api-terms-conditions/) at the bottom right of every screen or chart that shows these prices",
      "Show the text credit next to the prices",
      "Do not imply that CEDA endorses FarmNex",
      "Non-commercial use only; commercial use needs CEDA's written permission"
    ]
  }
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
      "p10": 992.5,
      "p50": 1105.5,
      "p90": 1242.9,
      "arrivals_p50_tonnes": 1241.6,
      "likely_closed": false
    },
    {
      "date": "2025-11-01",
      "horizon": 2,
      "p10": 944.5,
      "p50": 1092.0,
      "p90": 1243.7,
      "arrivals_p50_tonnes": 1306.3,
      "likely_closed": true
    },
    {
      "date": "2025-11-02",
      "horizon": 3,
      "p10": 943.4,
      "p50": 1097.0,
      "p90": 1257.5,
      "arrivals_p50_tonnes": 1309.0,
      "likely_closed": false
    }
  ],
  "reason": [
    "average price over the last 14 days (1,040 Rs/quintal) lowers the forecast by ~11%",
    "latest price (1,100 Rs/quintal) lowers the forecast by ~4%",
    "average price over the last 28 days (986 Rs/quintal) lowers the forecast by ~1%"
  ],
  "model_version": "20260928T081539Z-asof20251030",
  "attribution": "Data: Centre for Economic Data & Analysis (CEDA), Ashoka University, from Agmarknet"
}
```

## GET /forecast/price?market=Vashi&crop=Onion&days=3

HTTP 200
```json
{
  "market": "Vashi",
  "crop": "Onion",
  "district": "Thane",
  "forecast_origin": "2025-10-30",
  "as_of": "2025-10-30",
  "data_source": "real",
  "arrivals_data_source": "real",
  "last_price": 1400.0,
  "last_price_date": "2025-10-30",
  "days": [
    {
      "date": "2025-10-31",
      "horizon": 1,
      "p10": 1297.4,
      "p50": 1426.9,
      "p90": 1627.9,
      "arrivals_p50_tonnes": 1034.2,
      "likely_closed": false
    },
    {
      "date": "2025-11-01",
      "horizon": 2,
      "p10": 1253.9,
      "p50": 1416.7,
      "p90": 1651.3,
      "arrivals_p50_tonnes": 1136.0,
      "likely_closed": false
    },
    {
      "date": "2025-11-02",
      "horizon": 3,
      "p10": 1245.5,
      "p50": 1417.8,
      "p90": 1666.4,
      "arrivals_p50_tonnes": 1136.5,
      "likely_closed": true
    }
  ],
  "reason": [
    "average price over the last 14 days (1,404 Rs/quintal) raises the forecast by ~12%",
    "average price over the last 7 days (1,422 Rs/quintal) lowers the forecast by ~4%",
    "average price over the last 28 days (1,267 Rs/quintal) lowers the forecast by ~1%"
  ],
  "model_version": "20260928T081539Z-asof20251030",
  "attribution": "Data: Centre for Economic Data & Analysis (CEDA), Ashoka University, from Agmarknet"
}
```

## GET /forecast/price?market=Kalyan&crop=Tomato&days=3

HTTP 200
```json
{
  "market": "Kalyan",
  "crop": "Tomato",
  "district": "Thane",
  "forecast_origin": "2025-10-30",
  "as_of": "2025-10-30",
  "data_source": "real",
  "arrivals_data_source": "synthetic",
  "last_price": 1750.0,
  "last_price_date": "2025-10-30",
  "days": [
    {
      "date": "2025-10-31",
      "horizon": 1,
      "p10": 1007.8,
      "p50": 1790.7,
      "p90": 2388.9,
      "arrivals_p50_tonnes": 52.6,
      "likely_closed": false
    },
    {
      "date": "2025-11-01",
      "horizon": 2,
      "p10": 980.6,
      "p50": 1806.4,
      "p90": 2506.2,
      "arrivals_p50_tonnes": 53.3,
      "likely_closed": false
    },
    {
      "date": "2025-11-02",
      "horizon": 3,
      "p10": 982.5,
      "p50": 1803.0,
      "p90": 2550.1,
      "arrivals_p50_tonnes": 53.2,
      "likely_closed": false
    }
  ],
  "reason": [
    "latest price (1,750 Rs/quintal) raises the forecast by ~23%",
    "yesterday's price (1,750 Rs/quintal) raises the forecast by ~8%",
    "average price over the last 14 days (1,058 Rs/quintal) lowers the forecast by ~6%"
  ],
  "model_version": "20260928T081539Z-asof20251030",
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
      "price_change_pct": 1.3,
      "arrivals_change_pct": -13.0,
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
        {
          "market": "Manjri",
          "crop": "Onion",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2025-10-30"
        },
        "..."
      ],
      "reason": [
        "price expected to change +1.3% and arrivals -13.0%: no clear shortage or glut (moves under 3% count as flat)",
        "typical change across 11 Pune markets: expected price on 2025-10-31 vs the last 7 days' average",
        "14 of 14 markets have real Onion prices"
      ]
    },
    {
      "crop": "Tomato",
      "signal": "NORMAL",
      "price_change_pct": 1.4,
      "arrivals_change_pct": -6.2,
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
        {
          "market": "Manjri",
          "crop": "Tomato",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2025-10-30"
        },
        "..."
      ],
      "reason": [
        "price expected to change +1.4% and arrivals -6.2%: no clear shortage or glut (moves under 3% count as flat)",
        "typical change across 8 Pune markets: expected price on 2025-10-31 vs the last 7 days' average",
        "9 of 9 markets have real Tomato prices"
      ]
    },
    {
      "crop": "Potato",
      "signal": "NORMAL",
      "price_change_pct": 0.5,
      "arrivals_change_pct": -5.5,
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
        {
          "market": "Manjri",
          "crop": "Potato",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2025-10-30"
        },
        "..."
      ],
      "reason": [
        "price expected to change +0.5% and arrivals -5.5%: no clear shortage or glut (moves under 3% count as flat)",
        "typical change across 8 Pune markets: expected price on 2025-10-31 vs the last 7 days' average",
        "10 of 10 markets have real Potato prices"
      ]
    }
  ],
  "note": "Demand is a PROXY derived from mandi data (predicted modal price change vs predicted arrivals change), not measured consumer demand.",
  "attribution": "Data: Centre for Economic Data & Analysis (CEDA), Ashoka University, from Agmarknet"
}
```

## GET /forecast/demand?district=Thane

HTTP 200
```json
{
  "district": "Thane",
  "date": "2025-10-31",
  "forecast_origin": "2025-10-30",
  "items": [
    {
      "crop": "Onion",
      "signal": "HIGH",
      "price_change_pct": 4.9,
      "arrivals_change_pct": -5.0,
      "data_source": "real",
      "as_of": "2025-10-30",
      "pairs": [
        {
          "market": "Vashi",
          "crop": "Onion",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2025-10-30"
        },
        {
          "market": "Kalyan",
          "crop": "Onion",
          "price_source": "real",
          "arrivals_source": "synthetic",
          "last_real_price_date": "2025-10-30"
        }
      ],
      "reason": [
        "price expected to change +4.9% while arrivals change -5.0%: buyers want more than is arriving",
        "typical change across 2 Thane markets: expected price on 2025-10-31 vs the last 7 days' average",
        "2 of 2 markets have real Onion prices; arrivals partly synthetic"
      ]
    },
    {
      "crop": "Tomato",
      "signal": "HIGH",
      "price_change_pct": 15.1,
      "arrivals_change_pct": -3.8,
      "data_source": "real",
      "as_of": "2025-10-30",
      "pairs": [
        {
          "market": "Vashi",
          "crop": "Tomato",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2025-10-30"
        },
        {
          "market": "Kalyan",
          "crop": "Tomato",
          "price_source": "real",
          "arrivals_source": "synthetic",
          "last_real_price_date": "2025-10-30"
        }
      ],
      "reason": [
        "price expected to change +15.1% while arrivals change -3.8%: buyers want more than is arriving",
        "typical change across 2 Thane markets: expected price on 2025-10-31 vs the last 7 days' average",
        "2 of 2 markets have real Tomato prices; arrivals partly synthetic"
      ]
    },
    {
      "crop": "Potato",
      "signal": "NORMAL",
      "price_change_pct": -1.2,
      "arrivals_change_pct": 1.9,
      "data_source": "real",
      "as_of": "2025-10-30",
      "pairs": [
        {
          "market": "Vashi",
          "crop": "Potato",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2025-10-30"
        },
        {
          "market": "Kalyan",
          "crop": "Potato",
          "price_source": "real",
          "arrivals_source": "synthetic",
          "last_real_price_date": "2025-08-07"
        }
      ],
      "reason": [
        "price expected to change -1.2% and arrivals +1.9%: no clear shortage or glut (moves under 3% count as flat)",
        "typical change across 1 Thane markets: expected price on 2025-10-31 vs the last 7 days' average",
        "2 of 2 markets have real Potato prices; arrivals partly synthetic"
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
    "asking_price": 1689.2,
    "floor_price": 1001.2,
    "transport_cost_per_quintal": 15.6,
    "net_price_per_quintal": 1673.6,
    "net_total": 83680.0,
    "likely_closed_days": [
      "2025-10-31",
      "2025-11-01"
    ],
    "typical_daily_arrivals_quintal": 7570.5,
    "thin_market": false,
    "data_source": "real",
    "as_of": "2025-10-30",
    "reason": [
      "best open day 2025-11-02: expected price 1,689 Rs/quintal, minus transport for 16 km at 1 Rs/km per quintal = 16 Rs/quintal",
      "latest price (1,500 Rs/quintal) raises the forecast by ~16%",
      "season (Oct) raises the forecast by ~3%",
      "market (Junnar) raises the forecast by ~1%"
    ]
  },
  "options": [
    {
      "market": "Junnar",
      "district": "Pune",
      "distance_km": 15.6,
      "best_day": "2025-11-02",
      "asking_price": 1689.2,
      "floor_price": 1001.2,
      "transport_cost_per_quintal": 15.6,
      "net_price_per_quintal": 1673.6,
      "net_total": 83680.0,
      "likely_closed_days": [
        "2025-10-31",
        "2025-11-01"
      ],
      "typical_daily_arrivals_quintal": 7570.5,
      "thin_market": false,
      "data_source": "real",
      "as_of": "2025-10-30",
      "reason": [
        "best open day 2025-11-02: expected price 1,689 Rs/quintal, minus transport for 16 km at 1 Rs/km per quintal = 16 Rs/quintal",
        "latest price (1,500 Rs/quintal) raises the forecast by ~16%",
        "season (Oct) raises the forecast by ~3%",
        "market (Junnar) raises the forecast by ~1%"
      ]
    },
    {
      "market": "Otur",
      "district": "Pune",
      "distance_km": 18.5,
      "best_day": "2025-11-02",
      "asking_price": 1629.7,
      "floor_price": 1208.4,
      "transport_cost_per_quintal": 18.5,
      "net_price_per_quintal": 1611.2,
      "net_total": 80560.0,
      "likely_closed_days": [
        "2025-10-31",
        "2025-11-01"
      ],
      "typical_daily_arrivals_quintal": 12876.0,
      "thin_market": false,
      "data_source": "real",
      "as_of": "2025-10-30",
      "reason": [
        "best open day 2025-11-02: expected price 1,630 Rs/quintal, minus transport for 18 km at 1 Rs/km per quintal = 18 Rs/quintal",
        "latest price (1,800 Rs/quintal) raises the forecast by ~21%",
        "season (Oct) raises the forecast by ~2%",
        "average price over the last 28 days (1,375 Rs/quintal) raises the forecast by ~1%"
      ]
    },
    {
      "market": "Manchar",
      "district": "Pune",
      "distance_km": 11.0,
      "best_day": "2025-10-31",
      "asking_price": 1535.3,
      "floor_price": 1235.1,
      "transport_cost_per_quintal": 11.0,
      "net_price_per_quintal": 1524.3,
      "net_total": 76215.0,
      "likely_closed_days": [
        "2025-11-01"
      ],
      "typical_daily_arrivals_quintal": 8739.5,
      "thin_market": false,
      "data_source": "real",
      "as_of": "2025-10-28",
      "reason": [
        "best open day 2025-10-31: expected price 1,535 Rs/quintal, minus transport for 11 km at 1 Rs/km per quintal = 11 Rs/quintal",
        "price 2 days earlier (1,700 Rs/quintal) raises the forecast by ~6%",
        "season (Oct) raises the forecast by ~3%",
        "average price over the last 28 days (1,464 Rs/quintal) raises the forecast by ~2%"
      ]
    },
    "..."
  ],
  "message": "12 market(s) within 80 km",
  "data_source": "real",
  "as_of": "2025-10-30",
  "reason": [
    "Junnar: highest net price among markets with the most trustworthy data (fresh real on a big enough market > thin or stale real > synthetic)",
    "best open day 2025-11-02: expected price 1,689 Rs/quintal, minus transport for 16 km at 1 Rs/km per quintal = 16 Rs/quintal",
    "latest price (1,500 Rs/quintal) raises the forecast by ~16%"
  ],
  "attribution": "Data: Centre for Economic Data & Analysis (CEDA), Ashoka University, from Agmarknet"
}
```

## POST /forecast/sell-options

Request body:
```json
{"lat": 19.2, "lon": 73.4, "crop": "Tomato", "qty_quintal": 20, "radius_km": 60}
```

HTTP 200
```json
{
  "crop": "Tomato",
  "qty_quintal": 20.0,
  "radius_km": 60.0,
  "forecast_origin": "2025-10-30",
  "best": {
    "market": "Kalyan",
    "district": "Thane",
    "distance_km": 28.8,
    "best_day": "2025-11-01",
    "asking_price": 1806.4,
    "floor_price": 980.6,
    "transport_cost_per_quintal": 28.8,
    "net_price_per_quintal": 1777.6,
    "net_total": 35552.0,
    "likely_closed_days": [],
    "typical_daily_arrivals_quintal": null,
    "thin_market": false,
    "data_source": "real",
    "as_of": "2025-10-30",
    "reason": [
      "best open day 2025-11-01: expected price 1,806 Rs/quintal, minus transport for 29 km at 1 Rs/km per quintal = 29 Rs/quintal",
      "no reliable arrivals data for Kalyan, so we cannot check whether 20 quintals would move its price",
      "latest price (1,750 Rs/quintal) raises the forecast by ~23%",
      "yesterday's price (1,750 Rs/quintal) raises the forecast by ~8%"
    ]
  },
  "options": [
    {
      "market": "Kalyan",
      "district": "Thane",
      "distance_km": 28.8,
      "best_day": "2025-11-01",
      "asking_price": 1806.4,
      "floor_price": 980.6,
      "transport_cost_per_quintal": 28.8,
      "net_price_per_quintal": 1777.6,
      "net_total": 35552.0,
      "likely_closed_days": [],
      "typical_daily_arrivals_quintal": null,
      "thin_market": false,
      "data_source": "real",
      "as_of": "2025-10-30",
      "reason": [
        "best open day 2025-11-01: expected price 1,806 Rs/quintal, minus transport for 29 km at 1 Rs/km per quintal = 29 Rs/quintal",
        "no reliable arrivals data for Kalyan, so we cannot check whether 20 quintals would move its price",
        "latest price (1,750 Rs/quintal) raises the forecast by ~23%",
        "yesterday's price (1,750 Rs/quintal) raises the forecast by ~8%"
      ]
    },
    {
      "market": "Vashi",
      "district": "Thane",
      "distance_km": 43.3,
      "best_day": "2025-10-31",
      "asking_price": 1185.1,
      "floor_price": 1016.2,
      "transport_cost_per_quintal": 43.3,
      "net_price_per_quintal": 1141.8,
      "net_total": 22836.0,
      "likely_closed_days": [
        "2025-11-02"
      ],
      "typical_daily_arrivals_quintal": 1991.5,
      "thin_market": false,
      "data_source": "real",
      "as_of": "2025-10-30",
      "reason": [
        "best open day 2025-10-31: expected price 1,185 Rs/quintal, minus transport for 43 km at 1 Rs/km per quintal = 43 Rs/quintal",
        "latest price (1,150 Rs/quintal) lowers the forecast by ~9%",
        "average price over the last 14 days (1,344 Rs/quintal) raises the forecast by ~7%",
        "average price over the last 7 days (1,268 Rs/quintal) lowers the forecast by ~7%"
      ]
    }
  ],
  "message": "2 market(s) within 60 km",
  "data_source": "real",
  "as_of": "2025-10-30",
  "reason": [
    "Kalyan: highest net price among markets with the most trustworthy data (fresh real on a big enough market > thin or stale real > synthetic)",
    "best open day 2025-11-01: expected price 1,806 Rs/quintal, minus transport for 29 km at 1 Rs/km per quintal = 29 Rs/quintal",
    "no reliable arrivals data for Kalyan, so we cannot check whether 20 quintals would move its price"
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

## GET /forecast/crops?district=Thane&sowing_month=10&k=5

HTTP 200
```json
{
  "district": "Thane",
  "sowing_month": 10,
  "forecast_origin": "2025-10-30",
  "items": [
    {
      "rank": 1,
      "crop": "Tomato",
      "sowing_month": 10,
      "harvest_month": "2026-02",
      "expected_price": 1663.6,
      "method": "sarimax",
      "in_sowing_window": true,
      "data_source": "real",
      "as_of": "2025-10-30",
      "reason": [
        "SARIMAX on 128 months of prices expects 1,664 Rs/quintal in Feb (-17% vs the long-run average)",
        "Last 3 months averaged 1,837 Rs/quintal (-8% vs long-run)",
        "Sowing month fits the usual Tomato calendar; harvest lands in Feb"
      ]
    },
    {
      "rank": 2,
      "crop": "Potato",
      "sowing_month": 10,
      "harvest_month": "2026-01",
      "expected_price": 1375.1,
      "method": "sarimax",
      "in_sowing_window": true,
      "data_source": "real",
      "as_of": "2025-10-30",
      "reason": [
        "SARIMAX on 130 months of prices expects 1,375 Rs/quintal in Jan (-2% vs the long-run average)",
        "Last 3 months averaged 1,334 Rs/quintal (-4% vs long-run)",
        "Sowing month fits the usual Potato calendar; harvest lands in Jan"
      ]
    },
    {
      "rank": 3,
      "crop": "Onion",
      "sowing_month": 10,
      "harvest_month": "2026-02",
      "expected_price": 1311.3,
      "method": "sarimax",
      "in_sowing_window": true,
      "data_source": "real",
      "as_of": "2025-10-30",
      "reason": [
        "SARIMAX on 129 months of prices expects 1,311 Rs/quintal in Feb (-27% vs the long-run average)",
        "Last 3 months averaged 1,302 Rs/quintal (-27% vs long-run)",
        "Sowing month fits the usual Onion calendar; harvest lands in Feb"
      ]
    }
  ],
  "note": "Ranked by expected modal price (Rs/quintal) at harvest; yields and input costs differ by crop and are not included.",
  "attribution": "Data: Centre for Economic Data & Analysis (CEDA), Ashoka University, from Agmarknet"
}
```

## GET /forecast/price?market=Baramati&crop=Tomato

HTTP 404
```json
{
  "detail": "no real Tomato prices for Baramati; synthetic data is hidden (set api.show_synthetic: true in config.yaml to show it)"
}
```
