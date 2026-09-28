"""Plain-text reasons: SHAP for LightGBM (TreeSHAP via LightGBM's pred_contrib) and rules for SARIMAX."""
from __future__ import annotations

import numpy as np
import pandas as pd

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _describe(name: str, value, row: pd.Series, target: str) -> str:
    unit = "Rs/quintal" if target == "price" else "tonnes"
    what = "price" if target == "price" else "arrivals"
    v = None if value is None or (isinstance(value, float) and np.isnan(value)) else value
    if name.startswith("y_lag_"):
        k = int(name.rsplit("_", 1)[1])
        when = {1: f"latest {what}", 2: f"yesterday's {what}"}.get(k, f"{what} {k - 1} days earlier")
        return f"{when} ({np.expm1(v):,.0f} {unit})" if v is not None else f"no {what} reported for that day"
    if name.startswith("y_roll_mean_"):
        w = name.rsplit("_", 1)[1]
        return (f"average {what} over the last {w} days ({np.expm1(v):,.0f} {unit})" if v is not None
                else f"too few {what} reports in the last {w} days")
    if name.startswith("y_roll_std_"):
        w = name.rsplit("_", 1)[1]
        return (f"how much the {what} moved in the last {w} days" if v is not None
                else f"too few {what} reports in the last {w} days")
    if name.startswith("arr_"):
        return f"recent arrivals at the market ({np.expm1(v):,.0f} tonnes)" if v is not None else "no recent arrivals data"
    if name.startswith("price_"):
        return f"recent price ({np.expm1(v):,.0f} Rs/quintal)" if v is not None else "no recent price reported"
    if name == "dow":
        return f"day of week ({WEEKDAYS[int(v)]})"
    if name == "month":
        return f"season ({MONTHS[int(v) - 1]})"
    if name == "festival_3d":
        return "festival within 3 days" if v else "no festival nearby"
    if name == "monsoon":
        return "monsoon season" if v else "outside monsoon"
    if name == "days_since_last_report":
        return f"{int(v)} days since last report" if v is not None else "no report yet"
    if name == "reports_last_7d":
        return f"{int(v)} reports in the last 7 days"
    if name == "horizon":
        return f"{int(v)} day(s) ahead"
    if name == "market":
        return f"market ({row['market']})"
    if name == "commodity":
        return f"crop ({row['commodity']})"
    if name == "is_synthetic":
        return "synthetic data for this pair" if v else "real data for this pair"
    return name


def shap_reasons(booster, X: pd.DataFrame, target: str = "price", top: int = 3) -> list[list[str]]:
    """Top `top` drivers per row. Contributions are on the log scale, shown as % effects."""
    contrib = booster.predict(X, pred_contrib=True)
    names = list(X.columns)
    out = []
    for i in range(len(X)):
        c = contrib[i, :-1]  # last column is the expected value (bias)
        row = X.iloc[i]
        order = np.argsort(-np.abs(c))
        # A missing value is not a cause a farmer can act on: explain with observed drivers only,
        # and say once that recent reports are sparse if missing values mattered a lot.
        missing_top = any(pd.isna(row.iloc[j]) for j in order[:top])
        texts = []
        for j in order:
            if len(texts) == top:
                break
            val = row.iloc[j]
            if pd.isna(val):
                continue
            val = float(val) if not isinstance(val, str) else val
            pct = (np.exp(c[j]) - 1) * 100
            texts.append(f"{_describe(names[j], val, row, target)} "
                         f"{'raises' if c[j] > 0 else 'lowers'} the forecast by ~{abs(pct):.0f}%")
        if missing_top:
            texts.append("few recent reports from this market, so this forecast is less certain")
        out.append(texts)
    return out


def sarimax_reasons(rec: dict, harvest_month: str, in_window: bool, crop: str) -> list[str]:
    """Rule-based reasons for the monthly (SARIMAX or fallback) harvest-price estimate."""
    reasons = []
    price, mean = rec["price"], rec["history_mean"]
    diff = (price / mean - 1) * 100 if mean else 0.0
    m = MONTHS[int(harvest_month[5:7]) - 1]
    if rec["method"] == "sarimax":
        reasons.append(f"SARIMAX on {rec['history_months']} months of prices expects {price:,.0f} Rs/quintal in "
                       f"{m} ({diff:+.0f}% vs the long-run average)")
    elif rec["method"] == "same_month_average":
        reasons.append(f"Historical {m} average is {price:,.0f} Rs/quintal ({diff:+.0f}% vs the overall "
                       f"average); SARIMAX not used: too little history")
    else:
        reasons.append(f"No {m} prices on record; using the overall average {price:,.0f} Rs/quintal")
    trend = (rec["last_3m_mean"] / mean - 1) * 100 if mean else 0.0
    reasons.append(f"Last 3 months averaged {rec['last_3m_mean']:,.0f} Rs/quintal ({trend:+.0f}% vs long-run)")
    if in_window:
        reasons.append(f"Sowing month fits the usual {crop} calendar; harvest lands in {m}")
    else:
        reasons.append(f"Sowing month is OUTSIDE the usual {crop} calendar (ranked after in-season crops)")
    return reasons
