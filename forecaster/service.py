"""ForecastService: loads artifacts and data ONCE, answers every endpoint. Never calls CEDA.

Forecasts are anchored at the data's as_of date (CEDA lags weeks to months), not "today":
day +1..+3 are calendar days after as_of.
"""
from __future__ import annotations

import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from forecaster import explain, recommend
from forecaster.data import ROOT, load_config, load_mandi, load_ref
from forecaster.features import add_calendar, daily_calendar, origin_features, to_model_frame
from forecaster.synthetic import as_of_date, build_panel

WEEKDAYS = explain.WEEKDAYS


class NotFound(ValueError):
    """Unknown market/crop/district or a date outside the forecast window."""


class ForecastService:
    def __init__(self, cfg: dict | None = None, artifacts: Path | None = None):
        self.cfg = cfg or load_config()
        art = Path(artifacts or ROOT / self.cfg["paths"]["artifacts_dir"])
        self.meta = json.loads((art / "meta.json").read_text())
        self.version = self.meta["model_version"]
        self.boosters = {(t, q): lgb.Booster(model_file=str(art / f"{t}_{q}.txt"))
                         for t in ("price", "arrivals") for q in ("p10", "p50", "p90")}
        self.monthly = pd.read_csv(art / "crop_monthly.csv")
        self.ref = load_ref(self.cfg)
        self.real = load_mandi()
        self.as_of = as_of_date(self.real)
        panel, self.sources = build_panel(self.cfg, self.real)
        self.panel = panel[panel["date"] >= pd.Timestamp(self.cfg["modelling"]["train_start"])]
        daily = daily_calendar(self.panel, self.as_of)
        self.origin = {}
        for t in ("price", "arrivals"):
            of = origin_features(daily, t)
            self.origin[t] = of[of["date"] == self.as_of].set_index(["market", "commodity"])
        self.markets, self.crops = list(self.cfg["markets"]), list(self.cfg["crops"])
        self.likely_closed = {m: set(v) for m, v in self.meta["likely_closed"].items()}
        self.attribution = self.cfg["ceda"]["attribution"]
        self.max_h = max(self.cfg["modelling"]["horizons"])
        last = self.real.dropna(subset=["modal_price"]).groupby(["market", "commodity"])["date"].max()
        self.last_real = last.to_dict()

    # ------------------------------------------------------------------ helpers
    def check(self, market: str | None = None, crop: str | None = None, district: str | None = None):
        if market is not None and market not in self.markets:
            raise NotFound(f"unknown market {market!r}; valid: {self.markets}")
        if crop is not None and crop not in self.crops:
            raise NotFound(f"unknown crop {crop!r}; valid: {self.crops}")
        if district is not None and district not in self.districts():
            raise NotFound(f"unknown district {district!r}; valid: {self.districts()}")

    def districts(self) -> list[str]:
        return sorted({s.get("district") for s in self.cfg["markets"].values()})

    def source(self, market: str, crop: str) -> dict:
        r = self.sources[(self.sources["market"] == market) & (self.sources["commodity"] == crop)].iloc[0]
        last = self.last_real.get((market, crop))
        return {"market": market, "crop": crop, "price_source": r["price_source"],
                "arrivals_source": r["arrivals_source"],
                "last_real_price_date": last.date() if last is not None and r["price_source"] == "real" else None}

    def pair_as_of(self, market: str, crop: str):
        s = self.source(market, crop)
        return s["last_real_price_date"] or self.as_of.date()

    def _rows(self, target: str, pairs: list[tuple[str, str]], horizons: list[int]) -> pd.DataFrame:
        base = self.origin[target].loc[pairs].reset_index()
        rows = []
        for h in horizons:
            r = base.copy()
            r["horizon"] = h
            r["target_date"] = self.as_of + pd.Timedelta(days=h)
            rows.append(r)
        df = pd.concat(rows, ignore_index=True)
        return add_calendar(df, df["target_date"], self.ref["festivals"]["date"], self.cfg)

    def _predict(self, target: str, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        X = to_model_frame(df, target, self.markets, self.crops)
        preds = np.column_stack([np.expm1(self.boosters[(target, q)].predict(X)) for q in ("p10", "p50", "p90")])
        preds = np.sort(np.clip(preds, 0, None), axis=1)
        return pd.DataFrame(preds, columns=["p10", "p50", "p90"], index=df.index), X

    def forecast_pairs(self, pairs: list[tuple[str, str]], days: int, explain_rows: bool = True) -> dict:
        """{(market, crop): {"days": [...], "reason": [...]}} for +1..+days."""
        hs = list(range(1, days + 1))
        pr_df = self._rows("price", pairs, hs)
        ar_df = self._rows("arrivals", pairs, hs)
        pp, Xp = self._predict("price", pr_df)
        ap, _ = self._predict("arrivals", ar_df)
        reasons = (explain.shap_reasons(self.boosters[("price", "p50")], Xp, "price")
                   if explain_rows else [[] for _ in range(len(Xp))])
        out: dict = {}
        for i, r in pr_df.iterrows():
            key = (r["market"], r["commodity"])
            d = out.setdefault(key, {"days": [], "reason": []})
            td = r["target_date"]
            d["days"].append({"date": td.date(), "horizon": int(r["horizon"]),
                              "p10": round(float(pp.at[i, "p10"]), 1), "p50": round(float(pp.at[i, "p50"]), 1),
                              "p90": round(float(pp.at[i, "p90"]), 1),
                              "arrivals_p50_tonnes": round(float(ap.at[i, "p50"]), 1),
                              "likely_closed": td.dayofweek in self.likely_closed.get(r["market"], set())})
            if int(r["horizon"]) == 1:
                d["reason"] = reasons[i]
        return out

    def _typical_arrivals_quintal(self, market: str, crop: str) -> float | None:
        """Median REAL daily arrivals (quintals) over the last depth_lookback_days; None if unknown."""
        days = int(self.cfg["recommend"]["depth_lookback_days"])
        r = self.real[(self.real["market"] == market) & (self.real["commodity"] == crop)
                      & (self.real["date"] > self.as_of - pd.Timedelta(days=days))]["arrivals_tonnes"].dropna()
        return float(r.median() * 10) if len(r) >= 5 else None

    def _staleness_note(self, market: str, crop: str) -> list[str]:
        s = self.source(market, crop)
        if s["price_source"] == "synthetic":
            return [f"No real prices for {crop} at {market}: forecast is from SYNTHETIC data"]
        last = s["last_real_price_date"]
        gap = (self.as_of.date() - last).days if last else 0
        if gap > self.cfg["recommend"]["stale_days_warning"]:
            return [f"Last real {crop} price at {market} was {gap} days before the forecast origin"]
        return []

    # ------------------------------------------------------------------ endpoints
    def health(self) -> dict:
        return {"status": "ok", "model_version": self.version, "data_as_of": self.as_of.date()}

    def meta_info(self) -> dict:
        m = self.ref["markets"].set_index("market")
        return {
            "markets": [{"market": k, "district": v.get("district"), "lat": float(m.at[k, "lat"]),
                         "lon": float(m.at[k, "lon"]),
                         "likely_closed_weekdays": [WEEKDAYS[d] for d in sorted(self.likely_closed.get(k, []))]}
                        for k, v in self.cfg["markets"].items()],
            "crops": self.crops, "districts": self.districts(), "data_as_of": self.as_of.date(),
            "model_version": self.version,
            "pairs": [self.source(mk, c) for mk in self.markets for c in self.crops],
            "demand_note": " ".join(self.cfg["api"]["demand_note"].split()),
            "attribution": self.attribution,
        }

    def price(self, market: str, crop: str, days: int = 3) -> dict:
        self.check(market=market, crop=crop)
        if not 1 <= days <= self.max_h:
            raise NotFound(f"days must be between 1 and {self.max_h}")
        f = self.forecast_pairs([(market, crop)], days)[(market, crop)]
        src = self.source(market, crop)
        hist = self.panel[(self.panel["market"] == market) & (self.panel["commodity"] == crop)].dropna(subset=["modal_price"])
        last = hist.iloc[-1] if not hist.empty else None
        return {"market": market, "crop": crop, "district": self.cfg["markets"][market].get("district"),
                "forecast_origin": self.as_of.date(), "as_of": self.pair_as_of(market, crop),
                "data_source": src["price_source"], "arrivals_data_source": src["arrivals_source"],
                "last_price": float(last["modal_price"]) if last is not None else None,
                "last_price_date": last["date"].date() if last is not None else None,
                "days": f["days"], "reason": self._staleness_note(market, crop) + f["reason"],
                "model_version": self.version, "attribution": self.attribution}

    def demand(self, district: str, when=None) -> dict:
        self.check(district=district)
        target = pd.Timestamp(when) if when is not None else self.as_of + pd.Timedelta(days=1)
        h = (target - self.as_of).days
        if not 1 <= h <= self.max_h:
            raise NotFound(f"date must be within the forecast window "
                           f"{(self.as_of + pd.Timedelta(days=1)).date()}..{(self.as_of + pd.Timedelta(days=self.max_h)).date()} "
                           f"(data as_of {self.as_of.date()})")
        thr = float(self.cfg["recommend"]["demand_threshold_pct"])
        mkts = [m for m, s in self.cfg["markets"].items() if s.get("district") == district]
        items = []
        for crop in self.crops:
            pairs = [(m, crop) for m in mkts]
            fc = self.forecast_pairs(pairs, h, explain_rows=False)
            pch, ach, srcs = [], [], []
            for m in mkts:
                day = fc[(m, crop)]["days"][h - 1]
                po = self.origin["price"].loc[(m, crop)]
                ao = self.origin["arrivals"].loc[(m, crop)]
                p_ref = np.expm1(po["y_roll_mean_7"]) if pd.notna(po["y_roll_mean_7"]) else np.expm1(po["y_roll_mean_28"])
                a_ref = np.expm1(ao["y_roll_mean_7"]) if pd.notna(ao["y_roll_mean_7"]) else np.expm1(ao["y_roll_mean_28"])
                if pd.notna(p_ref) and p_ref > 0:
                    pch.append((day["p50"] / p_ref - 1) * 100)
                if pd.notna(a_ref) and a_ref > 0:
                    ach.append((day["arrivals_p50_tonnes"] / a_ref - 1) * 100)
                srcs.append(self.source(m, crop))
            p, a = (float(np.median(pch)) if pch else 0.0), (float(np.median(ach)) if ach else 0.0)
            signal, why = recommend.demand_signal(p, a, thr)
            real = [s for s in srcs if s["price_source"] == "real"]
            items.append({
                "crop": crop, "signal": signal, "price_change_pct": round(p, 1), "arrivals_change_pct": round(a, 1),
                "data_source": "real" if real else "synthetic",
                "as_of": max((s["last_real_price_date"] for s in real), default=self.as_of.date()),
                "pairs": srcs,
                "reason": [why,
                           f"typical change across {len(pch)} {district} markets: expected price on {target.date()} "
                           f"vs the last 7 days' average",
                           f"{len(real)} of {len(srcs)} markets have real {crop} prices"
                           + ("" if all(s["arrivals_source"] == "real" for s in srcs) else "; arrivals partly synthetic")],
            })
        return {"district": district, "date": target.date(), "forecast_origin": self.as_of.date(), "items": items,
                "note": " ".join(self.cfg["api"]["demand_note"].split()), "attribution": self.attribution}

    def sell_options(self, lat: float, lon: float, crop: str, qty_quintal: float, radius_km: float | None) -> dict:
        self.check(crop=crop)
        radius = float(radius_km or self.cfg["recommend"]["default_radius_km"])
        rate = float(self.cfg["recommend"]["rate_per_km_quintal"])
        coords = self.ref["markets"].set_index("market")
        near = []
        for m in self.markets:
            d = recommend.haversine_km(lat, lon, float(coords.at[m, "lat"]), float(coords.at[m, "lon"]))
            if d <= radius:
                near.append((m, d))
        share = float(self.cfg["recommend"]["thin_market_share"])
        options = []
        if near:
            fc = self.forecast_pairs([(m, crop) for m, _ in near], self.max_h)
            for m, dist in near:
                f = fc[(m, crop)]
                best = recommend.best_sell_day(f["days"])
                if best is None:
                    continue
                cost = round(dist * rate, 1)
                net = round(best["p50"] - cost, 1)
                src = self.source(m, crop)
                depth_q = self._typical_arrivals_quintal(m, crop)
                thin = depth_q is not None and qty_quintal > share * depth_q
                thin_note = ([f"{m} normally receives about {depth_q:,.0f} quintals of {crop} a day; "
                              f"{qty_quintal:g} quintals may push the price down (ranked lower)"] if thin else [])
                options.append({
                    "market": m, "district": self.cfg["markets"][m].get("district"), "distance_km": round(dist, 1),
                    "best_day": best["date"], "asking_price": best["p50"], "floor_price": best["p10"],
                    "transport_cost_per_quintal": cost, "net_price_per_quintal": net,
                    "net_total": round(net * qty_quintal, 0),
                    "likely_closed_days": [d["date"] for d in f["days"] if d["likely_closed"]],
                    "typical_daily_arrivals_quintal": None if depth_q is None else round(depth_q, 1),
                    "thin_market": thin,
                    "data_source": src["price_source"], "as_of": self.pair_as_of(m, crop),
                    "reason": ([f"best open day {best['date']}: expected price {best['p50']:,.0f} Rs/quintal, "
                                f"minus transport for {dist:,.0f} km at {rate:g} Rs/km per quintal "
                                f"= {cost:,.0f} Rs/quintal"]
                               + thin_note + self._staleness_note(m, crop) + f["reason"])[:4],
                })
        # Trust tier first: fresh real data on a market deep enough for this load, then thin or
        # stale real data, then synthetic; then net price.
        stale = self.cfg["recommend"]["stale_days_warning"]
        def tier(o):
            if o["data_source"] == "synthetic":
                return 2
            return 1 if o["thin_market"] or (self.as_of.date() - o["as_of"]).days > stale else 0
        options.sort(key=lambda o: (tier(o), -o["net_price_per_quintal"]))
        msg = (f"{len(options)} market(s) within {radius:g} km" if options
               else f"no configured market within {radius:g} km; increase radius_km")
        best = options[0] if options else None
        why = []
        if best:
            why = [f"{best['market']}: highest net price among markets with the most trustworthy data "
                   f"(fresh real on a big enough market > thin or stale real > synthetic)"] + best["reason"][:2]
        return {"crop": crop, "qty_quintal": qty_quintal, "radius_km": radius, "forecast_origin": self.as_of.date(),
                "best": best, "options": options, "message": msg,
                "data_source": best["data_source"] if best else None, "as_of": best["as_of"] if best else None,
                "reason": why,
                "attribution": self.attribution}

    def best_crops(self, district: str, sowing_month: int, k: int = 5) -> dict:
        self.check(district=district)
        if not 1 <= sowing_month <= 12:
            raise NotFound("sowing_month must be 1..12")
        cal = self.ref["crop_calendar"].set_index("crop")
        sowing = recommend.next_sowing_date(self.as_of, sowing_month)
        opts = []
        for crop in self.crops:
            if crop not in cal.index:
                continue
            hm = recommend.harvest_month(sowing, cal.at[crop, "duration_days"])
            t = self.monthly[(self.monthly["district"] == district) & (self.monthly["crop"] == crop)]
            if t.empty:
                continue
            row = t[t["month"] == hm]
            if row.empty:  # beyond the SARIMAX horizon: same calendar month's latest estimate
                same = t[t["month"].str[5:7] == hm[5:7]]
                row = same.tail(1) if not same.empty else t.tail(1)
            rec = row.iloc[0].to_dict()
            in_win = sowing_month in cal.at[crop, "sowing_months"]
            real_pairs = [m for m, s in self.cfg["markets"].items() if s.get("district") == district
                          and self.source(m, crop)["price_source"] == "real"]
            opts.append({
                "crop": crop, "sowing_month": sowing_month, "harvest_month": hm,
                "expected_price": round(float(rec["price"]), 1), "method": rec["method"],
                "in_sowing_window": bool(in_win), "data_source": rec["data_source"],
                "as_of": (max(self.pair_as_of(m, crop) for m in real_pairs) if real_pairs else self.as_of.date()),
                "reason": explain.sarimax_reasons(rec, hm, in_win, crop),
            })
        return {"district": district, "sowing_month": sowing_month, "forecast_origin": self.as_of.date(),
                "items": recommend.rank_crops(opts, k),
                "note": ("Ranked by expected modal price (Rs/quintal) at harvest; yields and input costs "
                         "differ by crop and are not included."),
                "attribution": self.attribution}
