"""Train everything: `python -m forecaster.train`.

1. Build the real/synthetic panel (forecaster.synthetic.build_panel) from data/raw/mandi.csv.
2. For each target (price, arrivals): origin features, time split by TARGET date (last
   modelling.test_days days of real data are test), stack horizons, fit one global LightGBM per
   quantile, compare with the seasonal-naive baseline on REAL test pairs, then refit on all
   rows for serving.
3. Monthly SARIMAX per district x crop for "best crop to grow" (fallback: same-month average).
4. Write artifacts/ (models, meta.json, crop_monthly.csv, model_version.txt) and reports/metrics.md.
"""
from __future__ import annotations

import json
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from forecaster.data import ROOT, load_config, load_mandi, load_ref
from forecaster.features import (daily_calendar, feature_columns, origin_features,
                                 split_and_stack, to_model_frame)
from forecaster.synthetic import as_of_date, build_panel

TARGETS = ("price", "arrivals")


def qname(q: float) -> str:
    return f"p{int(round(q * 100))}"


def fit_quantiles(X: pd.DataFrame, y: pd.Series, cfg: dict) -> dict[float, lgb.LGBMRegressor]:
    models = {}
    for q in cfg["modelling"]["quantiles"]:
        m = lgb.LGBMRegressor(objective="quantile", alpha=q, verbose=-1, random_state=0,
                              **cfg["lightgbm"])
        m.fit(X, y, categorical_feature=["market", "commodity"])
        models[q] = m
    return models


def predict_quantiles(models: dict, X: pd.DataFrame) -> pd.DataFrame:
    """Predictions on the original scale, sorted so p10 <= p50 <= p90 (no quantile crossing)."""
    qs = sorted(models)
    raw = np.column_stack([np.expm1(models[q].predict(X)) for q in qs])
    raw = np.sort(np.clip(raw, 0, None), axis=1)
    return pd.DataFrame(raw, columns=[qname(q) for q in qs], index=X.index)


def likely_closed_table(real: pd.DataFrame, panel: pd.DataFrame, cfg: dict) -> dict[str, list[int]]:
    """Per market: weekdays (0=Mon) on which it rarely reports. Real data if any, else synthetic."""
    thr = float(cfg["likely_closed_share"])
    out = {}
    for market in cfg["markets"]:
        src = real[(real["market"] == market) & real["modal_price"].notna()]
        if src.empty:
            src = panel[(panel["market"] == market) & panel["modal_price"].notna()]
        days = src.drop_duplicates("date")["date"]
        counts = days.dt.dayofweek.value_counts().reindex(range(7), fill_value=0)
        typical = counts.max() if counts.max() > 0 else 1
        out[market] = [int(d) for d in range(7) if counts[d] < thr * typical]
    return out


def evaluate(test: pd.DataFrame, preds: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    t = test.assign(**{c: preds[c].to_numpy() for c in preds})
    t = t[t["is_synthetic"] == 0]
    rows = []
    for keys, g in list(t.groupby(["commodity", "horizon"])) + [((c, "all"), g) for c, g in t.groupby("commodity")]:
        crop, h = keys
        y, m, b = g["y_true"], g["p50"], g["baseline"]
        ok = b.notna()
        rows.append({
            "crop": crop, "horizon": h, "n": len(g),
            "mae_model": (y - m).abs().mean(), "mae_baseline": (y[ok] - b[ok]).abs().mean(),
            "mape_model": ((y - m).abs() / y).mean() * 100,
            "mape_baseline": ((y[ok] - b[ok]).abs() / y[ok]).mean() * 100,
            "coverage_p10_p90": ((y >= g["p10"]) & (y <= g["p90"])).mean() * 100,
        })
    res = pd.DataFrame(rows)
    res["beats_baseline"] = res["mae_model"] < res["mae_baseline"]
    return res, t


# ------------------------------------------------------------------ SARIMAX, best crop to grow
def monthly_series(panel: pd.DataFrame, district: str, crop: str) -> tuple[pd.Series, str]:
    """District monthly mean modal price, from REAL-price pairs if the district has any."""
    p = panel[(panel["district"] == district) & (panel["commodity"] == crop) & panel["modal_price"].notna()]
    real = p[p["price_source"] == "real"]
    use, source = (real, "real") if not real.empty else (p, "synthetic")
    if use.empty:
        return pd.Series(dtype=float), source
    by_pair = use.groupby(["market", pd.Grouper(key="date", freq="MS")])["modal_price"].mean()
    s = by_pair.groupby(level=1).mean()
    s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="MS"))
    return s, source


def sarimax_forecast(s: pd.Series, cfg: dict, as_of: pd.Timestamp) -> tuple[pd.Series | None, str]:
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    sc = cfg["sarimax"]
    if s.notna().sum() < sc["min_months"]:
        return None, f"only {int(s.notna().sum())} months of data (< {sc['min_months']})"
    steps = sc["months_ahead"] + max(0, (as_of.to_period("M") - s.index.max().to_period("M")).n)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = SARIMAX(np.log(s), order=tuple(sc["order"]), seasonal_order=tuple(sc["seasonal_order"]),
                          trend="c", enforce_stationarity=False, enforce_invertibility=False
                          ).fit(disp=False, maxiter=200)
            fc = np.exp(res.get_forecast(steps).predicted_mean)
    except Exception as exc:  # noqa: BLE001 - any SARIMAX failure means "use the fallback"
        return None, f"SARIMAX failed ({type(exc).__name__})"
    lo, hi = sc["plausible_ratio"]
    mean = s.mean()
    if not np.isfinite(fc).all() or (fc < lo * mean).any() or (fc > hi * mean).any():
        return None, "SARIMAX forecast implausible"
    return fc, "ok"


def crop_monthly_table(panel: pd.DataFrame, cfg: dict, as_of: pd.Timestamp) -> tuple[pd.DataFrame, list[str]]:
    districts = sorted({m.get("district") for m in cfg["markets"].values()})
    months = pd.date_range(as_of.to_period("M").to_timestamp(), periods=cfg["sarimax"]["months_ahead"] + 1, freq="MS")
    rows, notes = [], []
    for district in districts:
        for crop in cfg["crops"]:
            s, source = monthly_series(panel, district, crop)
            if s.dropna().empty:
                continue
            fc, why = sarimax_forecast(s, cfg, as_of)
            same_month = s.groupby(s.index.month).mean()
            notes.append(f"{district} x {crop}: {why}" if fc is None else f"{district} x {crop}: SARIMAX ok")
            for m in months:
                if fc is not None and m in fc.index:
                    price, method = float(fc[m]), "sarimax"
                elif m.month in same_month.dropna().index:
                    price, method = float(same_month[m.month]), "same_month_average"
                else:
                    price, method = float(s.mean()), "overall_average"
                rows.append({"district": district, "crop": crop, "month": m.strftime("%Y-%m"),
                             "price": round(price, 1), "method": method, "data_source": source,
                             "history_months": int(s.notna().sum()),
                             "history_mean": round(float(s.mean()), 1),
                             "same_month_mean": (round(float(same_month[m.month]), 1)
                                                 if m.month in same_month.dropna().index else None),
                             "last_3m_mean": round(float(s.dropna().iloc[-3:].mean()), 1)})
    return pd.DataFrame(rows), notes


# ------------------------------------------------------------------ main
def train(cfg: dict | None = None, out_dir: Path | None = None, report: Path | None = None) -> dict:
    t0 = time.time()
    cfg = cfg or load_config()
    out_dir = Path(out_dir or ROOT / cfg["paths"]["artifacts_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    real = load_mandi()
    as_of = as_of_date(real)
    panel, sources = build_panel(cfg, real)
    panel = panel[panel["date"] >= pd.Timestamp(cfg["modelling"]["train_start"])]
    daily = daily_calendar(panel, as_of)
    fest = load_ref(cfg)["festivals"]["date"]
    horizons = cfg["modelling"]["horizons"]
    cutoff = as_of - pd.Timedelta(days=int(cfg["modelling"]["test_days"]))
    markets, crops = list(cfg["markets"]), list(cfg["crops"])

    metrics, meta_targets = {}, {}
    for target in TARGETS:
        of = origin_features(daily, target)
        tr, te = split_and_stack(of, horizons, cutoff, fest, cfg)
        cols = feature_columns(target)
        Xtr, Xte = (to_model_frame(d, target, markets, crops) for d in (tr, te))
        models = fit_quantiles(Xtr, np.log1p(tr["y_true"]), cfg)
        res, _ = evaluate(te, predict_quantiles(models, Xte))
        metrics[target] = res
        # refit on train + test for serving
        full = pd.concat([tr, te], ignore_index=True)
        final = fit_quantiles(to_model_frame(full, target, markets, crops), np.log1p(full["y_true"]), cfg)
        for q, m in final.items():
            m.booster_.save_model(str(out_dir / f"{target}_{qname(q)}.txt"))
        meta_targets[target] = {"features": cols, "train_rows": len(tr), "test_rows": len(te),
                                "final_rows": len(full)}

    monthly, sarimax_notes = crop_monthly_table(panel, cfg, as_of)
    monthly.to_csv(out_dir / "crop_monthly.csv", index=False)
    version = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-asof{as_of:%Y%m%d}"
    meta = {"model_version": version, "as_of": str(as_of.date()), "cutoff": str(cutoff.date()),
            "horizons": horizons, "quantiles": cfg["modelling"]["quantiles"], "markets": markets,
            "crops": crops, "targets": meta_targets,
            "likely_closed": likely_closed_table(real, panel, cfg),
            "sources": sources.to_dict("records"), "sarimax_notes": sarimax_notes,
            "train_seconds": round(time.time() - t0, 1)}
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    (out_dir / "model_version.txt").write_text(version + "\n")
    write_metrics(metrics, meta, sources, report or ROOT / cfg["paths"]["reports_dir"] / "metrics.md")
    return {"metrics": metrics, "meta": meta}


def _fmt(df: pd.DataFrame) -> str:
    d = df.copy()
    for c in d.columns:
        if d[c].dtype.kind == "f":
            d[c] = d[c].map(lambda v: "" if pd.isna(v) else f"{v:,.1f}")
    lines = ["| " + " | ".join(d.columns) + " |", "|" + "---|" * len(d.columns)]
    lines += ["| " + " | ".join(str(v) for v in r) + " |" for r in d.itertuples(index=False)]
    return "\n".join(lines)


def write_metrics(metrics: dict, meta: dict, sources: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = ["# Model metrics", "",
           f"Model version `{meta['model_version']}`. Data as_of **{meta['as_of']}**; test = target dates "
           f"after **{meta['cutoff']}** (last {len(pd.date_range(meta['cutoff'], meta['as_of'])) - 1} days), "
           "time split by target date, never random. Metrics use REAL pairs only (synthetic pairs are "
           "trained on but never scored). Baseline = seasonal naive (same weekday last week; if that day "
           "was not reported, the last reported value). MAE in Rs/quintal (price) or tonnes (arrivals). "
           f"Training took {meta['train_seconds']} s.", ""]
    for target, res in metrics.items():
        out += [f"## {target.title()}", "", _fmt(res), ""]
        allr = res[res["horizon"] == "all"]
        bad = allr.loc[~allr["beats_baseline"], "crop"].tolist()
        out.append(f"**Crops that do NOT beat the baseline ({target}):** {', '.join(bad) if bad else 'none'}")
        out.append("")
    n_real = (sources["price_source"] == "real").sum()
    out += ["## Data behind the models", "",
            f"- {n_real} of {len(sources)} market x crop pairs have real prices; the rest use synthetic prices.",
            f"- {(sources['arrivals_source'] == 'real').sum()} pairs have real arrivals; "
            "Tomato has no real arrivals anywhere, so tomato arrivals forecasts are synthetic-only "
            "and are not scored.",
            f"- Rows: " + ", ".join(f"{t}: train {v['train_rows']}, test {v['test_rows']}"
                                    for t, v in meta["targets"].items()),
            "", "## Best-crop monthly model (SARIMAX)", ""]
    out += [f"- {n}" for n in meta["sarimax_notes"]]
    path.write_text("\n".join(out) + "\n")


def main() -> None:
    t = time.time()
    r = train()
    print(f"trained in {time.time() - t:.1f} s -> artifacts/, reports/metrics.md")
    for target, res in r["metrics"].items():
        print(target)
        print(res[res["horizon"] == "all"].round(1).to_string(index=False))


if __name__ == "__main__":
    main()
