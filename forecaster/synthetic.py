"""Synthetic mandi data and the per-pair, per-target real/synthetic fallback.

    python -m forecaster.synthetic     # writes data/synthetic/synthetic.csv (inspection only)

`generate()` makes `synthetic.years` of daily data for EVERY configured market x crop, ending at
the real data's as_of date, with: a yearly price cycle peaking in the crop's `peak_month`, a
monsoon uplift, festival demand bumps, a weekday effect, AR(1) noise, one closed weekday per
market plus random non-reporting days, and arrivals inversely related to price.

`build_panel()` is the fallback rule used by training and serving. For each market x crop:
  * price  : real rows if the pair has >= min_real_days real prices, else synthetic prices
  * arrivals: real arrivals if the pair has >= min_real_days real arrivals, else synthetic
Real data always wins where it exists; `price_source` / `arrivals_source` say which was used.
"""
from __future__ import annotations

import zlib
from pathlib import Path

import numpy as np
import pandas as pd

from forecaster.data import MANDI_COLUMNS, ROOT, load_config, load_mandi, load_ref

PANEL_COLUMNS = MANDI_COLUMNS + ["price_source", "arrivals_source"]


def _pair_seed(seed: int, market: str, crop: str) -> int:
    return (seed * 1_000_003 + zlib.crc32(f"{market}|{crop}".encode())) % (2**32)


def as_of_date(real: pd.DataFrame | None) -> pd.Timestamp:
    """Last date with real data; today if there is none."""
    if real is not None and real["date"].notna().any():
        return pd.Timestamp(real["date"].max()).normalize()
    return pd.Timestamp.today().normalize()


def crop_params(cfg: dict, crop: str, real: pd.DataFrame | None) -> dict:
    scfg = cfg["synthetic"]
    p = dict(scfg.get("default_crop", {}), **scfg.get("crops", {}).get(crop, {}))
    if real is not None:
        prices = real.loc[real["commodity"] == crop, "modal_price"].dropna()
        if len(prices) >= scfg["min_real_days"]:
            p["base_price"] = float(prices.median())
    return p


def _recent_anchor(real: pd.DataFrame | None, crop: str, days: pd.DatetimeIndex, modal: np.ndarray,
                   n_days: int) -> float:
    """Scale factor so the synthetic series' recent median matches the real crop's recent median.

    Without this, a synthetic pair follows the average seasonal cycle and can sit far above or
    below the current real market level (e.g. after a price crash), which would make synthetic
    markets look like the best place to sell.
    """
    if real is None or n_days <= 0:
        return 1.0
    start = days[-1] - pd.Timedelta(days=n_days - 1)
    r = real[(real["commodity"] == crop) & (real["date"] >= start)]["modal_price"].dropna()
    if len(r) < 10:
        return 1.0
    syn = np.median(modal[np.asarray(days >= start)])
    return float(r.median() / syn) if syn > 0 else 1.0


def generate(cfg: dict | None = None, real: pd.DataFrame | None = None,
             end: pd.Timestamp | None = None) -> pd.DataFrame:
    cfg = cfg or load_config()
    scfg = cfg["synthetic"]
    end = end or as_of_date(real)
    start = end - pd.DateOffset(years=int(scfg["years"])) + pd.Timedelta(days=1)
    days = pd.date_range(start, end, freq="D")
    fest = load_ref(cfg)["festivals"]["date"].values.astype("datetime64[D]")
    d64 = days.values.astype("datetime64[D]")
    near = np.abs(d64[:, None] - fest[None, :]).astype(int).min(axis=1) <= scfg["festival_window_days"]
    monsoon = np.isin(days.month, scfg["monsoon_months"])
    doy = np.asarray(days.dayofyear)

    out = []
    for crop in cfg["crops"]:
        cp = crop_params(cfg, crop, real)
        peak_doy = (cp["peak_month"] - 0.5) * 30.4
        season = cp["seasonal_amp"] * np.cos(2 * np.pi * (doy - peak_doy) / 365.25)
        for market, mspec in cfg["markets"].items():
            rng = np.random.default_rng(_pair_seed(int(scfg["seed"]), market, crop))
            level = 1 + rng.normal(0, 0.06)            # market price offset
            size = float(np.exp(rng.normal(0, 0.8)))    # market size (arrivals scale)
            if real is not None:
                a = real.loc[(real["market"] == market) & (real["commodity"] == crop), "arrivals_tonnes"].dropna()
                if len(a) >= scfg["min_real_days"]:
                    size = float(a.median()) / cp["base_arrivals"]
            eps = np.zeros(len(days))
            shocks = rng.normal(0, scfg["noise_sd"], len(days))
            for i in range(1, len(days)):
                eps[i] = scfg["noise_ar"] * eps[i - 1] + shocks[i]
            dow = np.asarray(days.dayofweek)
            weekday = np.where(dow == 0, 0.02, 0.0)      # Monday: post-Sunday demand
            log_p = (np.log(cp["base_price"] * level) + season + eps + weekday
                     + scfg["monsoon_uplift"] * monsoon + scfg["festival_uplift"] * near)
            modal = np.exp(log_p)
            modal *= _recent_anchor(real, crop, days, modal, int(scfg.get("anchor_recent_days", 0)))
            spread = rng.uniform(0.15, 0.35)
            arrivals = (cp["base_arrivals"] * size
                        * (modal / (cp["base_price"] * level)) ** (-scfg["price_arrivals_elasticity"])
                        * np.exp(rng.normal(0, 0.15, len(days))) * np.where(dow == 0, 1.3, 1.0))
            closed = int(rng.integers(0, 7))
            open_ = (dow != closed) & (rng.random(len(days)) >= scfg["closed_weekday_share"])
            out.append(pd.DataFrame({
                "date": days[open_], "district": mspec.get("district"), "market": market,
                "commodity": crop,
                "min_price": np.round(modal * (1 - spread))[open_],
                "max_price": np.round(modal * (1 + spread))[open_],
                "modal_price": np.round(modal)[open_],
                "arrivals_tonnes": np.round(arrivals, 1)[open_],
            }))
    return pd.concat(out, ignore_index=True)[MANDI_COLUMNS]


def pair_sources(real: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Per market x crop: 'real' or 'synthetic' for price and for arrivals."""
    n = int(cfg["synthetic"]["min_real_days"])
    counts = (real.groupby(["market", "commodity"])
                  .agg(price_days=("modal_price", "count"), arrivals_days=("arrivals_tonnes", "count")))
    rows = []
    for market in cfg["markets"]:
        for crop in cfg["crops"]:
            pc, ac = (counts.loc[(market, crop)] if (market, crop) in counts.index else (0, 0))
            rows.append({"market": market, "commodity": crop,
                         "real_price_days": int(pc), "real_arrivals_days": int(ac),
                         "price_source": "real" if pc >= n else "synthetic",
                         "arrivals_source": "real" if ac >= n else "synthetic"})
    return pd.DataFrame(rows)


def build_panel(cfg: dict | None = None, real: pd.DataFrame | None = None,
                synth: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Combine real and synthetic data per pair and per target. Returns (panel, sources)."""
    cfg = cfg or load_config()
    real = load_mandi() if real is None else real
    synth = generate(cfg, real) if synth is None else synth
    src = pair_sources(real, cfg)
    parts = []
    for r in src.itertuples(index=False):
        key = ["date"]
        R = real[(real["market"] == r.market) & (real["commodity"] == r.commodity)]
        S = synth[(synth["market"] == r.market) & (synth["commodity"] == r.commodity)]
        P = R if r.price_source == "real" else S
        P = P[["date", "district", "min_price", "max_price", "modal_price"]].dropna(subset=["modal_price"])
        A = R if r.arrivals_source == "real" else S
        A = A[["date", "arrivals_tonnes"]].dropna(subset=["arrivals_tonnes"])
        m = P.merge(A, on=key, how="outer")
        m["district"] = cfg["markets"][r.market].get("district")
        m["market"], m["commodity"] = r.market, r.commodity
        m["price_source"], m["arrivals_source"] = r.price_source, r.arrivals_source
        parts.append(m)
    panel = pd.concat(parts, ignore_index=True)[PANEL_COLUMNS]
    panel = panel.sort_values(["commodity", "market", "date"]).reset_index(drop=True)
    return panel, src


def main() -> None:
    cfg = load_config()
    real = load_mandi()
    synth = generate(cfg, real)
    out = ROOT / cfg["paths"]["synthetic_dir"] / "synthetic.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    synth.assign(date=synth["date"].dt.strftime("%Y-%m-%d")).to_csv(out, index=False)
    src = pair_sources(real, cfg)
    print(f"wrote {out} ({len(synth)} rows, as_of {as_of_date(real).date()})")
    print(src.groupby(["price_source", "arrivals_source"]).size().to_string())


if __name__ == "__main__":
    main()
