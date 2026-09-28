# Sample responses

Live calls against `uvicorn app.main:app` (one per endpoint, plus Thane/Vashi/Kalyan and a hidden synthetic pair), on CEDA API data (2012-01-01 .. 2025-10-30) plus agmarknet.gov.in exports (2025-11-07 .. 2026-09-28), districts Pune, Thane and Mumbai.
Long lists (meta markets/pairs, sell options, demand pairs) are trimmed for readability; `...` marks cuts.

## GET /health

HTTP 200
```json
{
  "status": "ok",
  "model_version": "20260928T113858Z-asof20260928",
  "data_as_of": "2026-09-28"
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
  "data_as_of": "2026-09-28",
  "model_version": "20260928T113858Z-asof20260928",
  "pairs": [
    {
      "market": "Pune",
      "crop": "Onion",
      "price_source": "real",
      "arrivals_source": "real",
      "last_real_price_date": "2026-09-24"
    },
    {
      "market": "Pune",
      "crop": "Tomato",
      "price_source": "real",
      "arrivals_source": "real",
      "last_real_price_date": "2026-09-24"
    },
    {
      "market": "Pune",
      "crop": "Potato",
      "price_source": "real",
      "arrivals_source": "real",
      "last_real_price_date": "2026-09-24"
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
  "forecast_origin": "2026-09-28",
  "as_of": "2026-09-24",
  "data_source": "real",
  "arrivals_data_source": "real",
  "last_price": 2850.0,
  "last_price_date": "2026-09-24",
  "days": [
    {
      "date": "2026-09-29",
      "horizon": 1,
      "p10": 2546.8,
      "p50": 2963.0,
      "p90": 3333.7,
      "arrivals_p50_tonnes": 881.7,
      "likely_closed": false
    },
    {
      "date": "2026-09-30",
      "horizon": 2,
      "p10": 2539.5,
      "p50": 2945.2,
      "p90": 3389.1,
      "arrivals_p50_tonnes": 878.4,
      "likely_closed": false
    },
    {
      "date": "2026-10-01",
      "horizon": 3,
      "p10": 2464.4,
      "p50": 2962.0,
      "p90": 3515.0,
      "arrivals_p50_tonnes": 899.9,
      "likely_closed": false
    }
  ],
  "reason": [
    "average price over the last 14 days (2,916 Rs/quintal) raises the forecast by ~66%",
    "average price over the last 7 days (2,867 Rs/quintal) raises the forecast by ~18%",
    "average price over the last 28 days (2,937 Rs/quintal) raises the forecast by ~6%"
  ],
  "model_version": "20260928T113858Z-asof20260928",
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
  "forecast_origin": "2026-09-28",
  "as_of": "2026-09-28",
  "data_source": "real",
  "arrivals_data_source": "real",
  "last_price": 3850.0,
  "last_price_date": "2026-09-28",
  "days": [
    {
      "date": "2026-09-29",
      "horizon": 1,
      "p10": 3379.0,
      "p50": 3835.5,
      "p90": 3975.1,
      "arrivals_p50_tonnes": 988.1,
      "likely_closed": false
    },
    {
      "date": "2026-09-30",
      "horizon": 2,
      "p10": 3370.4,
      "p50": 3782.1,
      "p90": 4019.2,
      "arrivals_p50_tonnes": 1010.3,
      "likely_closed": false
    },
    {
      "date": "2026-10-01",
      "horizon": 3,
      "p10": 3294.2,
      "p50": 3746.7,
      "p90": 4012.5,
      "arrivals_p50_tonnes": 971.7,
      "likely_closed": false
    }
  ],
  "reason": [
    "average price over the last 14 days (3,853 Rs/quintal) raises the forecast by ~73%",
    "average price over the last 7 days (3,769 Rs/quintal) raises the forecast by ~25%",
    "latest price (3,850 Rs/quintal) raises the forecast by ~25%"
  ],
  "model_version": "20260928T113858Z-asof20260928",
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
  "forecast_origin": "2026-09-28",
  "as_of": "2026-09-23",
  "data_source": "real",
  "arrivals_data_source": "synthetic",
  "last_price": 500.0,
  "last_price_date": "2026-09-23",
  "days": [
    {
      "date": "2026-09-29",
      "horizon": 1,
      "p10": 359.4,
      "p50": 529.2,
      "p90": 848.0,
      "arrivals_p50_tonnes": 59.0,
      "likely_closed": false
    },
    {
      "date": "2026-09-30",
      "horizon": 2,
      "p10": 350.8,
      "p50": 523.9,
      "p90": 859.9,
      "arrivals_p50_tonnes": 59.1,
      "likely_closed": false
    },
    {
      "date": "2026-10-01",
      "horizon": 3,
      "p10": 346.8,
      "p50": 513.7,
      "p90": 882.7,
      "arrivals_p50_tonnes": 60.2,
      "likely_closed": false
    }
  ],
  "reason": [
    "average price over the last 14 days (404 Rs/quintal) lowers the forecast by ~47%",
    "average price over the last 28 days (417 Rs/quintal) lowers the forecast by ~14%",
    "season (Sep) raises the forecast by ~2%",
    "few recent reports from this market, so this forecast is less certain"
  ],
  "model_version": "20260928T113858Z-asof20260928",
  "attribution": "Data: Centre for Economic Data & Analysis (CEDA), Ashoka University, from Agmarknet"
}
```

## GET /forecast/demand?district=Pune

HTTP 200
```json
{
  "district": "Pune",
  "date": "2026-09-29",
  "forecast_origin": "2026-09-28",
  "items": [
    {
      "crop": "Onion",
      "signal": "NORMAL",
      "price_change_pct": 0.3,
      "arrivals_change_pct": -6.0,
      "data_source": "real",
      "as_of": "2026-09-28",
      "pairs": [
        {
          "market": "Pune",
          "crop": "Onion",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2026-09-24"
        },
        {
          "market": "Pimpri",
          "crop": "Onion",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2026-09-28"
        },
        {
          "market": "Manjri",
          "crop": "Onion",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2026-09-27"
        },
        "..."
      ],
      "reason": [
        "price expected to change +0.3% and arrivals -6.0%: no clear shortage or glut (moves under 3% count as flat)",
        "typical change across 12 Pune markets: expected price on 2026-09-29 vs the last 7 days' average",
        "14 of 14 markets have real Onion prices"
      ]
    },
    {
      "crop": "Tomato",
      "signal": "HIGH",
      "price_change_pct": 3.2,
      "arrivals_change_pct": -3.4,
      "data_source": "real",
      "as_of": "2026-09-28",
      "pairs": [
        {
          "market": "Pune",
          "crop": "Tomato",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2026-09-24"
        },
        {
          "market": "Pimpri",
          "crop": "Tomato",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2026-09-28"
        },
        {
          "market": "Manjri",
          "crop": "Tomato",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2026-09-27"
        },
        "..."
      ],
      "reason": [
        "price expected to change +3.2% while arrivals change -3.4%: buyers want more than is arriving",
        "typical change across 7 Pune markets: expected price on 2026-09-29 vs the last 7 days' average",
        "9 of 9 markets have real Tomato prices"
      ]
    },
    {
      "crop": "Potato",
      "signal": "NORMAL",
      "price_change_pct": 2.1,
      "arrivals_change_pct": 2.8,
      "data_source": "real",
      "as_of": "2026-09-28",
      "pairs": [
        {
          "market": "Pune",
          "crop": "Potato",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2026-09-24"
        },
        {
          "market": "Pimpri",
          "crop": "Potato",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2026-04-13"
        },
        {
          "market": "Manjri",
          "crop": "Potato",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2026-09-27"
        },
        "..."
      ],
      "reason": [
        "price expected to change +2.1% and arrivals +2.8%: no clear shortage or glut (moves under 3% count as flat)",
        "typical change across 7 Pune markets: expected price on 2026-09-29 vs the last 7 days' average",
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
  "date": "2026-09-29",
  "forecast_origin": "2026-09-28",
  "items": [
    {
      "crop": "Onion",
      "signal": "NORMAL",
      "price_change_pct": -0.1,
      "arrivals_change_pct": -5.4,
      "data_source": "real",
      "as_of": "2026-09-28",
      "pairs": [
        {
          "market": "Vashi",
          "crop": "Onion",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2026-09-28"
        },
        {
          "market": "Kalyan",
          "crop": "Onion",
          "price_source": "real",
          "arrivals_source": "synthetic",
          "last_real_price_date": "2026-09-28"
        }
      ],
      "reason": [
        "price expected to change -0.1% and arrivals -5.4%: no clear shortage or glut (moves under 3% count as flat)",
        "typical change across 2 Thane markets: expected price on 2026-09-29 vs the last 7 days' average",
        "2 of 2 markets have real Onion prices; arrivals partly synthetic"
      ]
    },
    {
      "crop": "Tomato",
      "signal": "HIGH",
      "price_change_pct": 14.8,
      "arrivals_change_pct": -4.2,
      "data_source": "real",
      "as_of": "2026-09-28",
      "pairs": [
        {
          "market": "Vashi",
          "crop": "Tomato",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2026-09-28"
        },
        {
          "market": "Kalyan",
          "crop": "Tomato",
          "price_source": "real",
          "arrivals_source": "synthetic",
          "last_real_price_date": "2026-09-23"
        }
      ],
      "reason": [
        "price expected to change +14.8% while arrivals change -4.2%: buyers want more than is arriving",
        "typical change across 2 Thane markets: expected price on 2026-09-29 vs the last 7 days' average",
        "2 of 2 markets have real Tomato prices; arrivals partly synthetic"
      ]
    },
    {
      "crop": "Potato",
      "signal": "HIGH",
      "price_change_pct": 8.7,
      "arrivals_change_pct": -5.0,
      "data_source": "real",
      "as_of": "2026-09-28",
      "pairs": [
        {
          "market": "Vashi",
          "crop": "Potato",
          "price_source": "real",
          "arrivals_source": "real",
          "last_real_price_date": "2026-09-28"
        },
        {
          "market": "Kalyan",
          "crop": "Potato",
          "price_source": "real",
          "arrivals_source": "synthetic",
          "last_real_price_date": "2026-09-15"
        }
      ],
      "reason": [
        "price expected to change +8.7% while arrivals change -5.0%: buyers want more than is arriving",
        "typical change across 2 Thane markets: expected price on 2026-09-29 vs the last 7 days' average",
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
  "forecast_origin": "2026-09-28",
  "best": {
    "market": "Manchar",
    "district": "Pune",
    "distance_km": 11.0,
    "best_day": "2026-10-01",
    "asking_price": 4473.9,
    "floor_price": 2994.9,
    "transport_cost_per_quintal": 11.0,
    "net_price_per_quintal": 4462.9,
    "net_total": 223145.0,
    "likely_closed_days": [],
    "typical_daily_arrivals_quintal": 13059.0,
    "thin_market": false,
    "data_source": "real",
    "as_of": "2026-09-27",
    "reason": [
      "best open day 2026-10-01: expected price 4,474 Rs/quintal, minus transport for 11 km at 1 Rs/km per quintal = 11 Rs/quintal",
      "average price over the last 14 days (4,598 Rs/quintal) raises the forecast by ~97%",
      "yesterday's price (4,260 Rs/quintal) raises the forecast by ~16%",
      "average price over the last 28 days (4,758 Rs/quintal) raises the forecast by ~13%"
    ]
  },
  "options": [
    {
      "market": "Manchar",
      "district": "Pune",
      "distance_km": 11.0,
      "best_day": "2026-10-01",
      "asking_price": 4473.9,
      "floor_price": 2994.9,
      "transport_cost_per_quintal": 11.0,
      "net_price_per_quintal": 4462.9,
      "net_total": 223145.0,
      "likely_closed_days": [],
      "typical_daily_arrivals_quintal": 13059.0,
      "thin_market": false,
      "data_source": "real",
      "as_of": "2026-09-27",
      "reason": [
        "best open day 2026-10-01: expected price 4,474 Rs/quintal, minus transport for 11 km at 1 Rs/km per quintal = 11 Rs/quintal",
        "average price over the last 14 days (4,598 Rs/quintal) raises the forecast by ~97%",
        "yesterday's price (4,260 Rs/quintal) raises the forecast by ~16%",
        "average price over the last 28 days (4,758 Rs/quintal) raises the forecast by ~13%"
      ]
    },
    {
      "market": "Alephata",
      "district": "Pune",
      "distance_km": 16.8,
      "best_day": "2026-09-29",
      "asking_price": 4313.0,
      "floor_price": 3437.7,
      "transport_cost_per_quintal": 16.8,
      "net_price_per_quintal": 4296.2,
      "net_total": 214810.0,
      "likely_closed_days": [
        "2026-09-30",
        "2026-10-01"
      ],
      "typical_daily_arrivals_quintal": 6633.0,
      "thin_market": false,
      "data_source": "real",
      "as_of": "2026-09-27",
      "reason": [
        "best open day 2026-09-29: expected price 4,313 Rs/quintal, minus transport for 17 km at 1 Rs/km per quintal = 17 Rs/quintal",
        "average price over the last 14 days (4,280 Rs/quintal) raises the forecast by ~90%",
        "average price over the last 7 days (4,200 Rs/quintal) raises the forecast by ~31%",
        "yesterday's price (4,200 Rs/quintal) raises the forecast by ~13%"
      ]
    },
    {
      "market": "Junnar",
      "district": "Pune",
      "distance_km": 15.6,
      "best_day": "2026-10-01",
      "asking_price": 4166.5,
      "floor_price": 2718.4,
      "transport_cost_per_quintal": 15.6,
      "net_price_per_quintal": 4150.9,
      "net_total": 207545.0,
      "likely_closed_days": [
        "2026-09-29",
        "2026-09-30"
      ],
      "typical_daily_arrivals_quintal": 6770.0,
      "thin_market": false,
      "data_source": "real",
      "as_of": "2026-09-27",
      "reason": [
        "best open day 2026-10-01: expected price 4,166 Rs/quintal, minus transport for 16 km at 1 Rs/km per quintal = 16 Rs/quintal",
        "average price over the last 14 days (4,171 Rs/quintal) raises the forecast by ~92%",
        "yesterday's price (3,800 Rs/quintal) raises the forecast by ~13%",
        "average price over the last 28 days (4,330 Rs/quintal) raises the forecast by ~13%"
      ]
    },
    "..."
  ],
  "message": "12 market(s) within 80 km",
  "data_source": "real",
  "as_of": "2026-09-27",
  "reason": [
    "Manchar: highest net price among markets with the most trustworthy data (fresh real on a big enough market > thin or stale real > synthetic)",
    "best open day 2026-10-01: expected price 4,474 Rs/quintal, minus transport for 11 km at 1 Rs/km per quintal = 11 Rs/quintal",
    "average price over the last 14 days (4,598 Rs/quintal) raises the forecast by ~97%"
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
  "forecast_origin": "2026-09-28",
  "best": {
    "market": "Vashi",
    "district": "Thane",
    "distance_km": 43.3,
    "best_day": "2026-09-29",
    "asking_price": 2161.4,
    "floor_price": 1753.8,
    "transport_cost_per_quintal": 43.3,
    "net_price_per_quintal": 2118.1,
    "net_total": 42362.0,
    "likely_closed_days": [],
    "typical_daily_arrivals_quintal": 2787.0,
    "thin_market": false,
    "data_source": "real",
    "as_of": "2026-09-28",
    "reason": [
      "best open day 2026-09-29: expected price 2,161 Rs/quintal, minus transport for 43 km at 1 Rs/km per quintal = 43 Rs/quintal",
      "average price over the last 14 days (1,930 Rs/quintal) raises the forecast by ~34%",
      "latest price (2,250 Rs/quintal) raises the forecast by ~14%",
      "average price over the last 7 days (2,103 Rs/quintal) raises the forecast by ~4%"
    ]
  },
  "options": [
    {
      "market": "Vashi",
      "district": "Thane",
      "distance_km": 43.3,
      "best_day": "2026-09-29",
      "asking_price": 2161.4,
      "floor_price": 1753.8,
      "transport_cost_per_quintal": 43.3,
      "net_price_per_quintal": 2118.1,
      "net_total": 42362.0,
      "likely_closed_days": [],
      "typical_daily_arrivals_quintal": 2787.0,
      "thin_market": false,
      "data_source": "real",
      "as_of": "2026-09-28",
      "reason": [
        "best open day 2026-09-29: expected price 2,161 Rs/quintal, minus transport for 43 km at 1 Rs/km per quintal = 43 Rs/quintal",
        "average price over the last 14 days (1,930 Rs/quintal) raises the forecast by ~34%",
        "latest price (2,250 Rs/quintal) raises the forecast by ~14%",
        "average price over the last 7 days (2,103 Rs/quintal) raises the forecast by ~4%"
      ]
    },
    {
      "market": "Kalyan",
      "district": "Thane",
      "distance_km": 28.8,
      "best_day": "2026-09-29",
      "asking_price": 529.2,
      "floor_price": 359.4,
      "transport_cost_per_quintal": 28.8,
      "net_price_per_quintal": 500.4,
      "net_total": 10008.0,
      "likely_closed_days": [],
      "typical_daily_arrivals_quintal": null,
      "thin_market": false,
      "data_source": "real",
      "as_of": "2026-09-23",
      "reason": [
        "best open day 2026-09-29: expected price 529 Rs/quintal, minus transport for 29 km at 1 Rs/km per quintal = 29 Rs/quintal",
        "no reliable arrivals data for Kalyan, so we cannot check whether 20 quintals would move its price",
        "average price over the last 14 days (404 Rs/quintal) lowers the forecast by ~47%",
        "average price over the last 28 days (417 Rs/quintal) lowers the forecast by ~14%"
      ]
    }
  ],
  "message": "2 market(s) within 60 km",
  "data_source": "real",
  "as_of": "2026-09-28",
  "reason": [
    "Vashi: highest net price among markets with the most trustworthy data (fresh real on a big enough market > thin or stale real > synthetic)",
    "best open day 2026-09-29: expected price 2,161 Rs/quintal, minus transport for 43 km at 1 Rs/km per quintal = 43 Rs/quintal",
    "average price over the last 14 days (1,930 Rs/quintal) raises the forecast by ~34%"
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
  "forecast_origin": "2026-09-28",
  "items": [
    {
      "rank": 1,
      "crop": "Onion",
      "sowing_month": 6,
      "harvest_month": "2027-10",
      "expected_price": 2024.0,
      "method": "sarimax",
      "in_sowing_window": true,
      "data_source": "real",
      "as_of": "2026-09-28",
      "reason": [
        "SARIMAX on 140 months of prices expects 2,024 Rs/quintal in Oct (+29% vs the long-run average)",
        "Last 3 months averaged 2,564 Rs/quintal (+64% vs long-run)",
        "Sowing month fits the usual Onion calendar; harvest lands in Oct"
      ]
    },
    {
      "rank": 2,
      "crop": "Tomato",
      "sowing_month": 6,
      "harvest_month": "2027-10",
      "expected_price": 1308.6,
      "method": "sarimax",
      "in_sowing_window": true,
      "data_source": "real",
      "as_of": "2026-09-28",
      "reason": [
        "SARIMAX on 141 months of prices expects 1,309 Rs/quintal in Oct (-14% vs the long-run average)",
        "Last 3 months averaged 1,505 Rs/quintal (-1% vs long-run)",
        "Sowing month fits the usual Tomato calendar; harvest lands in Oct"
      ]
    },
    {
      "rank": 3,
      "crop": "Potato",
      "sowing_month": 6,
      "harvest_month": "2027-09",
      "expected_price": 1278.8,
      "method": "sarimax",
      "in_sowing_window": true,
      "data_source": "real",
      "as_of": "2026-09-28",
      "reason": [
        "SARIMAX on 141 months of prices expects 1,279 Rs/quintal in Sep (-5% vs the long-run average)",
        "Last 3 months averaged 1,144 Rs/quintal (-15% vs long-run)",
        "Sowing month fits the usual Potato calendar; harvest lands in Sep"
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
  "forecast_origin": "2026-09-28",
  "items": [
    {
      "rank": 1,
      "crop": "Onion",
      "sowing_month": 10,
      "harvest_month": "2027-02",
      "expected_price": 2571.6,
      "method": "sarimax",
      "in_sowing_window": true,
      "data_source": "real",
      "as_of": "2026-09-28",
      "reason": [
        "SARIMAX on 140 months of prices expects 2,572 Rs/quintal in Feb (+44% vs the long-run average)",
        "Last 3 months averaged 2,949 Rs/quintal (+65% vs long-run)",
        "Sowing month fits the usual Onion calendar; harvest lands in Feb"
      ]
    },
    {
      "rank": 2,
      "crop": "Tomato",
      "sowing_month": 10,
      "harvest_month": "2027-02",
      "expected_price": 1671.8,
      "method": "sarimax",
      "in_sowing_window": true,
      "data_source": "real",
      "as_of": "2026-09-28",
      "reason": [
        "SARIMAX on 139 months of prices expects 1,672 Rs/quintal in Feb (-17% vs the long-run average)",
        "Last 3 months averaged 1,301 Rs/quintal (-35% vs long-run)",
        "Sowing month fits the usual Tomato calendar; harvest lands in Feb"
      ]
    },
    {
      "rank": 3,
      "crop": "Potato",
      "sowing_month": 10,
      "harvest_month": "2027-01",
      "expected_price": 1095.7,
      "method": "sarimax",
      "in_sowing_window": true,
      "data_source": "real",
      "as_of": "2026-09-28",
      "reason": [
        "SARIMAX on 141 months of prices expects 1,096 Rs/quintal in Jan (-20% vs the long-run average)",
        "Last 3 months averaged 1,010 Rs/quintal (-26% vs long-run)",
        "Sowing month fits the usual Potato calendar; harvest lands in Jan"
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
