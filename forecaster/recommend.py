"""Business rules on top of the forecasts: demand signal, best place/day to sell, best crop to grow."""
from __future__ import annotations

import math

import pandas as pd

EARTH_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_KM * math.asin(math.sqrt(a))


def demand_signal(price_change_pct: float, arrivals_change_pct: float, threshold: float) -> tuple[str, str]:
    """HIGH: price expected up while arrivals are not rising as fast (buyers absorb less supply at
    higher prices). LOW: price expected down while arrivals are not falling. Else NORMAL."""
    p, a = price_change_pct, arrivals_change_pct
    if p > threshold and a < p:
        return "HIGH", f"price expected to change {p:+.1f}% while arrivals change {a:+.1f}%: buyers want more than is arriving"
    if p < -threshold and a > p:
        return "LOW", f"price expected to change {p:+.1f}% while arrivals change {a:+.1f}%: more is arriving than buyers want"
    return "NORMAL", (f"price expected to change {p:+.1f}% and arrivals {a:+.1f}%: "
                      f"no clear shortage or glut (moves under {threshold:g}% count as flat)")


def best_sell_day(days: list[dict]) -> dict | None:
    """Highest p50 among days not marked likely_closed (None if every day is likely closed)."""
    open_days = [d for d in days if not d["likely_closed"]]
    return max(open_days, key=lambda d: d["p50"]) if open_days else None


def next_sowing_date(as_of: pd.Timestamp, sowing_month: int) -> pd.Timestamp:
    """Mid-month of the next occurrence of sowing_month at or after the as_of month."""
    year = as_of.year if sowing_month >= as_of.month else as_of.year + 1
    return pd.Timestamp(year=year, month=sowing_month, day=15)


def harvest_month(sowing: pd.Timestamp, duration_days: int) -> str:
    return (sowing + pd.Timedelta(days=int(duration_days))).strftime("%Y-%m")


def rank_crops(options: list[dict], k: int) -> list[dict]:
    """In-season crops first, then by expected harvest price (Rs/quintal), highest first."""
    ranked = sorted(options, key=lambda o: (not o["in_sowing_window"], -o["expected_price"]))[:k]
    for i, o in enumerate(ranked, 1):
        o["rank"] = i
    return ranked
