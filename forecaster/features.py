"""Feature building for the direct multi-horizon LightGBM models.

Conventions (all by CALENDAR day, never by row position):
  * Each market x crop is reindexed to a full daily calendar; missing days stay NaN.
  * A row is an ORIGIN day t: everything in it is known at the end of day t.
      lag_k            = value on day t-k+1  (lag_1 = value on t itself, lag_7 = t-6, ...)
      roll_{mean,std}_w = over days t-w+1..t, needs >= 3 reported values
      days_since_last_report, reports_last_7d  (as of t)
  * Direct multi-horizon: for h in horizons the target is the value on day t+h, and calendar
    features (day-of-week, month, festival within 3 days, monsoon) describe that TARGET day.
    Predictions are never fed back as lags.
  * split_and_stack() assigns every (origin, h) row to train/test by its TARGET date BEFORE the
    horizons are stacked, so no target date can appear on both sides of the split.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LAGS = (1, 2, 3, 7, 14)
WINDOWS = (7, 14, 28)
MIN_ROLL_POINTS = 3
TARGET_COL = {"price": "modal_price", "arrivals": "arrivals_tonnes"}


def daily_calendar(panel: pd.DataFrame, end: pd.Timestamp) -> pd.DataFrame:
    """Reindex every market x crop to one row per calendar day from its first date to `end`."""
    out = []
    for (market, crop), g in panel.groupby(["market", "commodity"], sort=False):
        g = g.drop_duplicates("date").set_index("date").sort_index()
        idx = pd.date_range(g.index.min(), end, freq="D")
        d = g.reindex(idx)
        d.index.name = "date"
        for c in ("market", "commodity", "district", "price_source", "arrivals_source"):
            if c in g:
                d[c] = g[c].iloc[0]
        out.append(d.reset_index())
    return pd.concat(out, ignore_index=True)


def _series_features(y: pd.Series, prefix: str) -> dict[str, pd.Series]:
    f = {}
    for k in LAGS:
        f[f"{prefix}_lag_{k}"] = y.shift(k - 1)
    for w in WINDOWS:
        r = y.rolling(w, min_periods=MIN_ROLL_POINTS)
        f[f"{prefix}_roll_mean_{w}"] = r.mean()
        f[f"{prefix}_roll_std_{w}"] = r.std()
    return f


def origin_features(daily: pd.DataFrame, target: str) -> pd.DataFrame:
    """Features known at the end of each origin day, per pair (no target, no calendar yet)."""
    tcol = TARGET_COL[target]
    parts = []
    for _, g in daily.groupby(["market", "commodity"], sort=False):
        g = g.sort_values("date").reset_index(drop=True)
        y = np.log1p(g[tcol])
        feats = _series_features(y, "y")
        reported = g[tcol].notna()
        last = g["date"].where(reported).ffill()
        feats["days_since_last_report"] = (g["date"] - last).dt.days
        feats["reports_last_7d"] = reported.astype(float).rolling(7, min_periods=1).sum()
        if target == "price":
            # arrivals features come from REAL arrivals only (NaN where arrivals are synthetic)
            real_arr = g["arrivals_tonnes"].where(g.get("arrivals_source", "real") == "real")
            a = np.log1p(real_arr)
            feats["arr_lag_1"] = a
            feats["arr_lag_7"] = a.shift(6)
            feats["arr_roll_mean_7"] = a.rolling(7, min_periods=MIN_ROLL_POINTS).mean()
        else:
            p = np.log1p(g["modal_price"])
            feats["price_lag_1"] = p
            feats["price_roll_mean_7"] = p.rolling(7, min_periods=MIN_ROLL_POINTS).mean()
        # seasonal-naive baseline ingredients (same weekday last week of the TARGET day)
        feats["_raw"] = g[tcol]
        f = pd.DataFrame(feats)
        f.insert(0, "date", g["date"])
        f.insert(1, "market", g["market"])
        f.insert(2, "commodity", g["commodity"])
        f["is_synthetic"] = (g["price_source" if target == "price" else "arrivals_source"]
                             .eq("synthetic").astype(int).to_numpy())
        parts.append(f)
    return pd.concat(parts, ignore_index=True)


def add_calendar(df: pd.DataFrame, when: pd.Series, festivals: pd.Series, cfg: dict) -> pd.DataFrame:
    fest = np.sort(pd.to_datetime(festivals).values.astype("datetime64[D]"))
    w = when.values.astype("datetime64[D]")
    pos = np.clip(np.searchsorted(fest, w), 1, len(fest) - 1)
    dist = np.minimum(np.abs((w - fest[pos - 1]).astype(int)), np.abs((fest[pos] - w).astype(int)))
    df["dow"] = when.dt.dayofweek.to_numpy()
    df["month"] = when.dt.month.to_numpy()
    df["festival_3d"] = (dist <= 3).astype(int)
    df["monsoon"] = when.dt.month.isin(cfg["synthetic"]["monsoon_months"]).astype(int).to_numpy()
    return df


def stack_horizon(of: pd.DataFrame, h: int, festivals: pd.Series, cfg: dict) -> pd.DataFrame:
    """Rows for horizon h: features at origin t, target on t+h, calendar of t+h, baseline."""
    df = of.copy()
    df["horizon"] = h
    df["target_date"] = df["date"] + pd.Timedelta(days=h)
    g = df.groupby(["market", "commodity"], sort=False)["_raw"]
    df["y_true"] = g.shift(-h)                      # value on t+h (NaN if not reported)
    # seasonal naive: same weekday one week before the target day = t+h-7 (always <= t);
    # if that day was not reported, fall back to the last reported value up to t.
    same_wd = g.shift(7 - h)
    last_known = g.ffill()
    df["baseline"] = same_wd.fillna(last_known)
    df = add_calendar(df, df["target_date"], festivals, cfg)
    return df


def split_and_stack(of: pd.DataFrame, horizons, cutoff: pd.Timestamp, festivals: pd.Series,
                    cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train rows: target_date <= cutoff. Test rows: target_date > cutoff. Both need a reported target."""
    train, test = [], []
    for h in horizons:
        s = stack_horizon(of, h, festivals, cfg)
        s = s[s["y_true"].notna()]
        train.append(s[s["target_date"] <= cutoff])
        test.append(s[s["target_date"] > cutoff])
    return pd.concat(train, ignore_index=True), pd.concat(test, ignore_index=True)


def feature_columns(target: str) -> list[str]:
    cols = ["market", "commodity", "horizon", "dow", "month", "festival_3d", "monsoon",
            "days_since_last_report", "reports_last_7d", "is_synthetic"]
    for k in LAGS:
        cols.append(f"y_lag_{k}")
    for w in WINDOWS:
        cols += [f"y_roll_mean_{w}", f"y_roll_std_{w}"]
    cols += (["arr_lag_1", "arr_lag_7", "arr_roll_mean_7"] if target == "price"
             else ["price_lag_1", "price_roll_mean_7"])
    return cols


def to_model_frame(df: pd.DataFrame, target: str, markets, crops) -> pd.DataFrame:
    X = df[feature_columns(target)].copy()
    X["market"] = pd.Categorical(X["market"], categories=list(markets))
    X["commodity"] = pd.Categorical(X["commodity"], categories=list(crops))
    return X
