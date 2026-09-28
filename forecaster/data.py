"""Mandi data preparation and loading.

`python -m forecaster.data` turns the raw data into data/raw/mandi.csv and writes
reports/data_quality.md. Raw data comes from ONE source (config `data_prep.source`):
  * "ceda": JSON cached by `python -m forecaster.ceda` (CEDA Agmarknet API, full history), or
  * "exports": manual Agmarknet / CEDA website exports in data/raw/ (csv/xls/xlsx, often
    truncated at ~1000 rows), or
  * "auto": the API cache if it has files, else the exports.

Output schema, one row per (date, market, commodity), prices in Rs/quintal:
    date, district, market, commodity, min_price, max_price, modal_price, arrivals_tonnes
modal_price may be NaN on arrivals-only market-days (config `keep_arrivals_only_rows`);
price models must train only on rows where modal_price is present.
Missing days stay missing; nothing is interpolated or forward-filled here.
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
MANDI_COLUMNS = ["date", "district", "market", "commodity",
                 "min_price", "max_price", "modal_price", "arrivals_tonnes"]
RAW_SUFFIXES = {".csv", ".xls", ".xlsx"}

# Raw header (normalised: lowercase, alphanumerics only) -> canonical column.
_COLUMN_PATTERNS = [
    (r"^(t|date|arrivaldate|pricedate|reporteddate)$", "date"),
    (r"^(cmdty|commodity|commodityname|crop)$", "commodity"),
    (r"^(marketname|market|apmc|mandi)$", "market"),
    (r"^(districtname|district)$", "district"),
    (r"^(variety|grade)$", "variety"),
    (r"^(pmin|minprice|minimumprice).*", "min_price"),
    (r"^(pmax|maxprice|maximumprice).*", "max_price"),
    (r"^(pmodal|modalprice).*", "modal_price"),
    (r"^(qty|quantity|arrival|arrivals).*", "arrivals"),
]


def load_config(path: Path | str | None = None) -> dict:
    with open(path or ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


def _key(name: str) -> str:
    """Lookup key for a market/crop name: lowercase, no 'APMC', no brackets/spaces/punctuation."""
    s = str(name).lower().replace("apmc", "")
    return re.sub(r"[^a-z0-9]", "", s)


def build_alias_map(section: dict) -> dict[str, str]:
    out = {}
    for canonical, spec in section.items():
        for alias in [canonical, *((spec or {}).get("aliases") or [])]:
            out[_key(alias)] = canonical
    return out


def _norm_header(col: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(col).lower())


def rename_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, str | None]:
    """Fuzzy-rename raw columns. Returns (df, arrivals unit from header or None)."""
    mapping, unit = {}, None
    for col in df.columns:
        n = _norm_header(col)
        for pattern, target in _COLUMN_PATTERNS:
            if re.match(pattern, n) and target not in mapping.values():
                mapping[col] = target
                if target == "arrivals":
                    unit = "quintals" if "quintal" in n else "tonnes" if "tonne" in n else None
                break
    return df.rename(columns=mapping)[list(mapping.values())], unit


def _peek_rows(path: Path, n: int = 30) -> list[list[str]]:
    if path.suffix.lower() == ".csv":
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
            return [row for _, row in zip(range(n), csv.reader(f))]
    raw = pd.read_excel(path, header=None, dtype=str, nrows=n)
    return [[c for c in row if isinstance(c, str)] for row in raw.itertuples(index=False)]


def read_raw_file(path: Path) -> pd.DataFrame:
    """Read an export, skipping title rows above the real header row."""
    header_row = 0
    for i, row in enumerate(_peek_rows(path)):
        cells = [_norm_header(c) for c in row if str(c).strip()]
        has_date = any(re.match(_COLUMN_PATTERNS[0][0], c) for c in cells)
        has_value = any(re.match(p, c) for c in cells
                        for p, t in _COLUMN_PATTERNS if t in ("modal_price", "arrivals"))
        if has_date and has_value:
            header_row = i
            break
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, skiprows=header_row, dtype=str, encoding="utf-8-sig")
    return pd.read_excel(path, skiprows=header_row, dtype=str)


@dataclass
class PrepReport:
    files: list[dict] = field(default_factory=list)
    dropped: Counter = field(default_factory=Counter)
    unknown_markets: Counter = field(default_factory=Counter)
    unknown_crops: Counter = field(default_factory=Counter)
    flagged_low_price: list[dict] = field(default_factory=list)
    flagged_high_price: list[dict] = field(default_factory=list)
    outliers: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    rows_in_price: int = 0
    rows_in_qty: int = 0
    source: str = "exports"
    orphan_arrivals: pd.DataFrame | None = None


def _normalize_names(df: pd.DataFrame, cfg: dict, rep: PrepReport) -> pd.DataFrame:
    mmap, cmap = build_alias_map(cfg["markets"]), build_alias_map(cfg["crops"])
    raw_m, raw_c = df["market"].astype(str).str.strip(), df["commodity"].astype(str).str.strip()
    df = df.assign(market=raw_m.map(lambda s: mmap.get(_key(s))),
                   commodity=raw_c.map(lambda s: cmap.get(_key(s))))
    for name, n in raw_m[df["market"].isna()].value_counts().items():
        rep.unknown_markets[name] += int(n)
    for name, n in raw_c[df["commodity"].isna()].value_counts().items():
        rep.unknown_crops[name] += int(n)
    bad = df["market"].isna() | df["commodity"].isna()
    rep.dropped["unknown market or crop name"] += int(bad.sum())
    df = df[~bad].copy()
    districts = {m: spec.get("district") for m, spec in cfg["markets"].items()}
    df["district"] = df["market"].map(districts)
    return df


def parse_dates(values: pd.Series) -> pd.Series:
    """ISO dates (YYYY-MM-DD) as-is; everything else (dd/mm/yyyy, '01 Jan 2024') day-first."""
    s = values.astype(str).str.strip()
    iso = s.str.match(r"^\d{4}-\d{2}-\d{2}")
    parsed = pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")
    parsed[iso] = pd.to_datetime(s[iso].str[:10], format="%Y-%m-%d", errors="coerce")
    parsed[~iso] = pd.to_datetime(s[~iso], dayfirst=True, errors="coerce", format="mixed")
    return parsed.dt.normalize()


def _parse_dates(df: pd.DataFrame, rep: PrepReport) -> pd.DataFrame:
    df = df.assign(date=parse_dates(df["date"]))
    bad = df["date"].isna()  # footer / total rows and junk
    rep.dropped["unparseable date (footer/total rows)"] += int(bad.sum())
    return df[~bad]


def load_raw(cfg: dict, raw_dir: Path, rep: PrepReport,
             ceda_dir: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pick ONE raw source per config `data_prep.source` and return (price rows, quantity rows)."""
    source = cfg["data_prep"].get("source", "auto")
    has_ceda = ceda_dir is not None and any(Path(ceda_dir).glob("price/*.json"))
    if source == "ceda" or (source == "auto" and has_ceda):
        if not has_ceda:
            raise FileNotFoundError(f"no CEDA price files in {ceda_dir}; run python -m forecaster.ceda")
        rep.source = "ceda"
        return load_ceda(cfg, Path(ceda_dir), rep)
    rep.source = "exports"
    return load_exports(cfg, raw_dir, rep)


_QTY_KEYS = ("quantity", "qty", "arrivals", "arrival_quantity", "arrival", "value")


def export_market_names(cfg: dict) -> dict[int, str]:
    """market_id -> market_name from website exports that carry both columns.

    The live /agmarknet/markets endpoint hangs, so this is how CEDA market ids get names.
    Ids not seen in any export stay as 'market_id N' and are reported as unknown names.
    """
    exports = Path(cfg["paths"].get("exports_dir", cfg["paths"]["raw_dir"]))
    exports = exports if exports.is_absolute() else ROOT / exports
    names: dict[int, str] = {}
    if not exports.is_dir():
        return names
    for f in sorted(exports.glob("*.csv")):
        try:
            head = pd.read_csv(f, nrows=0).columns
            if {"market_id", "market_name"} <= set(head):
                d = pd.read_csv(f, usecols=["market_id", "market_name"], dtype=str).dropna()
                for mid, name in zip(d["market_id"], d["market_name"]):
                    if mid.strip().isdigit():
                        names.setdefault(int(mid), name.strip())
        except (pd.errors.ParserError, UnicodeDecodeError, ValueError):
            continue
    return names


def load_ceda(cfg: dict, ceda_dir: Path, rep: PrepReport) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read the JSON cache written by forecaster.ceda into the same shape as the exports."""
    names = export_market_names(cfg)  # id -> raw name from the old exports (same Agmarknet ids)
    for f in sorted((ceda_dir / "ref").glob("markets_*.json")):
        for m in json.loads(f.read_text()):
            if m.get("market_id") is not None and m.get("market_name"):
                names[int(m["market_id"])] = str(m["market_name"])
    caps = set(cfg["ceda"].get("suspicious_row_counts", []))
    unit = cfg["data_prep"].get("default_arrivals_unit", "tonnes")
    frames: dict[str, list[pd.DataFrame]] = {"price": [], "quantity": []}
    for indicator in frames:
        for f in sorted((ceda_dir / indicator).glob("*.json")):
            payload = json.loads(f.read_text())
            recs = pd.DataFrame(payload.get("records") or [])
            info = {"file": f"ceda/{indicator}/{f.name}", "rows": len(recs), "kind": indicator,
                    "truncated": len(recs) in caps}
            if recs.empty:
                rep.files.append(info)
                continue
            if "market_id" not in recs:
                rep.notes.append(f"`{f.name}`: rows have no market_id (district/state aggregate?), skipped.")
                rep.files.append(info)
                continue
            no_mkt = recs["market_id"].isna()
            if no_mkt.any():
                rep.dropped["CEDA aggregate row without market_id"] += int(no_mkt.sum())
                recs = recs[~no_mkt]
            ids = recs["market_id"].astype(int)
            fallback = recs["market_name"] if "market_name" in recs else pd.Series(None, index=recs.index)
            df = pd.DataFrame({
                "date": recs["date"].astype(str).str[:10],
                "market": ids.map(names).fillna(fallback).fillna(ids.map(lambda i: f"market_id {i}")),
                "commodity": payload.get("crop"),
            })
            if indicator == "price":
                for c in ("min_price", "max_price", "modal_price"):
                    df[c] = pd.to_numeric(recs.get(c), errors="coerce")
                df["variety"] = recs["variety"].astype(str) if "variety" in recs else "NA"
            else:
                key = next((k for k in _QTY_KEYS if k in recs), None)
                if key is None:
                    rep.notes.append(f"`{f.name}`: no quantity column in {sorted(recs.columns)}; skipped. "
                                     "Add the field name to _QTY_KEYS in forecaster/data.py.")
                    rep.files.append(info)
                    continue
                q = pd.to_numeric(recs[key], errors="coerce")
                df["arrivals_tonnes"] = q / 10.0 if unit == "quintals" else q
                info["unit"] = unit
            d = pd.to_datetime(df["date"], errors="coerce")
            if d.notna().any():
                info["first"], info["last"] = d.min().date(), d.max().date()
            rep.files.append(info)
            frames[indicator].append(df)
    empty_p = pd.DataFrame(columns=["date", "market", "commodity", "variety",
                                    "min_price", "max_price", "modal_price"])
    empty_q = pd.DataFrame(columns=["date", "market", "commodity", "arrivals_tonnes"])
    return (pd.concat(frames["price"], ignore_index=True) if frames["price"] else empty_p,
            pd.concat(frames["quantity"], ignore_index=True) if frames["quantity"] else empty_q)


def load_exports(cfg: dict, raw_dir: Path, rep: PrepReport) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read all manual website exports and split them into price rows and quantity rows."""
    prices, qtys = [], []
    caps = set(cfg["data_prep"].get("suspicious_row_counts", []))
    default_unit = cfg["data_prep"].get("default_arrivals_unit", "tonnes")
    out_name = Path(cfg["paths"]["mandi_csv"]).name
    for path in sorted(raw_dir.iterdir()):
        if path.suffix.lower() not in RAW_SUFFIXES or path.name == out_name:
            continue
        raw = read_raw_file(path)
        df, unit = rename_columns(raw)
        info = {"file": path.name, "rows": len(raw), "kind": "?", "truncated": len(raw) in caps}
        if "modal_price" in df:
            info["kind"] = "price"
            for c in ("min_price", "max_price", "modal_price"):
                df[c] = pd.to_numeric(df.get(c), errors="coerce")
            if "variety" not in df:
                df["variety"] = "NA"
            prices.append(df)
        elif "arrivals" in df:
            info["kind"] = "quantity"
            unit = unit or default_unit
            info["unit"] = unit
            q = pd.to_numeric(df["arrivals"], errors="coerce")
            df["arrivals_tonnes"] = q / 10.0 if unit == "quintals" else q
            qtys.append(df.drop(columns="arrivals"))
        else:
            rep.notes.append(f"`{path.name}`: no price or quantity column recognised, skipped.")
        dates = parse_dates(df["date"]) if "date" in df else pd.Series(dtype="datetime64[ns]")
        if dates.notna().any():
            info["first"], info["last"] = dates.min().date(), dates.max().date()
            year = re.match(r"^(\d{4})", path.name)
            if year and not (dates.dt.year == int(year.group(1))).any():
                rep.notes.append(
                    f"`{path.name}`: file name says {year.group(1)} but every date is in "
                    f"{sorted(dates.dt.year.dropna().unique().astype(int).tolist())}.")
        rep.files.append(info)
    empty_p = pd.DataFrame(columns=["date", "market", "commodity", "variety",
                                    "min_price", "max_price", "modal_price"])
    empty_q = pd.DataFrame(columns=["date", "market", "commodity", "arrivals_tonnes"])
    return (pd.concat(prices, ignore_index=True) if prices else empty_p,
            pd.concat(qtys, ignore_index=True) if qtys else empty_q)


def clean_prices(p: pd.DataFrame, cfg: dict, rep: PrepReport) -> pd.DataFrame:
    rep.rows_in_price = len(p)
    p = _parse_dates(p, rep)
    p = _normalize_names(p, cfg, rep)
    p["variety"] = p["variety"].fillna("NA").astype(str).str.strip()
    cols = ["date", "market", "commodity", "variety", "min_price", "max_price", "modal_price"]
    n = len(p)
    p = p[cols].drop_duplicates()
    rep.dropped["exact duplicate price row (overlapping exports)"] += n - len(p)
    bad = p["modal_price"].isna() | (p["modal_price"] <= 0)
    rep.dropped["modal_price missing or <= 0"] += int(bad.sum())
    p = p[~bad].copy()
    swap = p["min_price"] > p["max_price"]
    if swap.any():
        rep.notes.append(f"Swapped min/max on {int(swap.sum())} rows where min > max.")
        p.loc[swap, ["min_price", "max_price"]] = p.loc[swap, ["max_price", "min_price"]].values
    outside = (p["modal_price"] < p["min_price"]) | (p["modal_price"] > p["max_price"])
    if outside.any():
        rep.notes.append(f"Clipped modal into [min, max] on {int(outside.sum())} rows.")
        p["modal_price"] = p["modal_price"].clip(p["min_price"], p["max_price"])

    # Collapse varieties/grades. Price exports carry no per-variety arrivals -> plain mean.
    n_before = len(p)
    p = (p.groupby(["date", "market", "commodity"], as_index=False)
          .agg(min_price=("min_price", "min"), max_price=("max_price", "max"),
               modal_price=("modal_price", "mean"), n_varieties=("variety", "nunique")))
    multi = int((p["n_varieties"] > 1).sum())
    rep.notes.append(f"Collapsed varieties: {n_before} variety rows -> {len(p)} market-days "
                     f"({multi} market-days had more than one variety; modal = plain mean "
                     f"because price exports have no per-variety arrivals).")
    p = p.drop(columns="n_varieties")

    # Flag (never convert) prices outside the crop's plausible Rs/quintal range.
    for crop, spec in cfg["crops"].items():
        m = p["commodity"] == crop
        lo, hi = spec.get("plausible_modal_min"), spec.get("plausible_modal_max")
        if lo is not None:
            rep.flagged_low_price += p[m & (p["modal_price"] < lo)].to_dict("records")
        if hi is not None:
            rep.flagged_high_price += p[m & (p["modal_price"] > hi)].to_dict("records")

    return drop_outliers(p, cfg, rep)


def drop_outliers(p: pd.DataFrame, cfg: dict, rep: PrepReport) -> pd.DataFrame:
    """Drop modal prices far from the centred 30-calendar-day rolling median of the pair."""
    dp = cfg["data_prep"]
    window, min_pts = f"{int(dp['outlier_window_days'])}D", int(dp["outlier_min_points"])
    keep = pd.Series(True, index=p.index)
    for _, g in p.sort_values("date").groupby(["market", "commodity"]):
        s = g.set_index("date")["modal_price"]
        med = s.rolling(window, center=True, min_periods=min_pts).median()
        ratio = (s / med).to_numpy()
        out = (ratio > dp["outlier_high_ratio"]) | (ratio < dp["outlier_low_ratio"])
        for idx, is_out, r, m in zip(g.index, out, ratio, med.to_numpy()):
            if is_out:
                keep[idx] = False
                rec = p.loc[idx].to_dict()
                rec.update(rolling_median=m, ratio=r)
                rep.outliers.append(rec)
    rep.dropped["outlier vs 30-day rolling median (>4x or <0.25x)"] += int((~keep).sum())
    return p[keep]


def clean_quantities(q: pd.DataFrame, cfg: dict, rep: PrepReport) -> pd.DataFrame:
    rep.rows_in_qty = len(q)
    if q.empty:
        return pd.DataFrame(columns=["date", "market", "commodity", "arrivals_tonnes"])
    q = _parse_dates(q, rep)
    q = _normalize_names(q, cfg, rep)
    q = q[["date", "market", "commodity", "arrivals_tonnes"]]
    n = len(q)
    q = q.drop_duplicates()
    rep.dropped["exact duplicate quantity row (overlapping exports)"] += n - len(q)
    bad = q["arrivals_tonnes"].isna() | (q["arrivals_tonnes"] < 0)
    rep.dropped["arrivals missing or negative"] += int(bad.sum())
    q = q[~bad]
    return q.groupby(["date", "market", "commodity"], as_index=False)["arrivals_tonnes"].sum()


def prepare(cfg: dict | None = None, raw_dir: Path | None = None,
            ceda_dir: Path | None = None) -> tuple[pd.DataFrame, PrepReport]:
    cfg = cfg or load_config()
    if ceda_dir is None and raw_dir is None and "ceda_cache_dir" in cfg["paths"]:
        ceda_dir = ROOT / cfg["paths"]["ceda_cache_dir"]
    raw_dir = Path(raw_dir or ROOT / cfg["paths"].get("exports_dir", cfg["paths"]["raw_dir"]))
    rep = PrepReport()
    p_raw, q_raw = load_raw(cfg, raw_dir, rep, ceda_dir)
    p = clean_prices(p_raw, cfg, rep)
    q = clean_quantities(q_raw, cfg, rep)

    no_arrivals = [c for c, s in cfg["crops"].items() if not (s or {}).get("has_arrivals", True)]
    forced = q["commodity"].isin(no_arrivals)
    if forced.any():
        rep.notes.append(f"Ignored {int(forced.sum())} quantity rows for crops configured "
                         f"with has_arrivals: false ({', '.join(no_arrivals)}).")
        q = q[~forced]

    keys = ["date", "market", "commodity"]
    orphan = q.merge(p[keys], how="left", indicator=True)
    orphan = orphan[orphan["_merge"] == "left_only"].drop(columns="_merge")
    rep.orphan_arrivals = orphan
    if cfg["data_prep"].get("keep_arrivals_only_rows", False):
        # Arrivals model needs these days; price model filters on modal_price.notna().
        df = p.merge(q, on=keys, how="outer")
    else:
        df = p.merge(q, on=keys, how="left")
        rep.dropped["arrivals-only market-day (no price row that day)"] += len(orphan)

    df.loc[df["commodity"].isin(no_arrivals), "arrivals_tonnes"] = np.nan
    districts = {m: spec.get("district") for m, spec in cfg["markets"].items()}
    df["district"] = df["market"].map(districts)
    df = df[MANDI_COLUMNS].sort_values(["commodity", "market", "date"]).reset_index(drop=True)
    return df, rep


def load_mandi(path: Path | str | None = None) -> pd.DataFrame:
    """Load the cleaned mandi.csv with proper dtypes (used by training and the service)."""
    cfg = load_config()
    path = Path(path or ROOT / cfg["paths"]["mandi_csv"])
    df = pd.read_csv(path, parse_dates=["date"])
    missing = set(MANDI_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {sorted(missing)}")
    for c in ("min_price", "max_price", "modal_price", "arrivals_tonnes"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df[MANDI_COLUMNS]


# ---------------------------------------------------------------- data quality report
def _md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_none_\n"
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in row) + " |")
    return "\n".join(lines) + "\n"


def coverage_table(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Per market x crop: span, reported days, coverage %, gaps (calendar days)."""
    dp = cfg["data_prep"]
    rows = []
    for market in cfg["markets"]:
        for crop in cfg["crops"]:
            pair = df[(df["market"] == market) & (df["commodity"] == crop)]
            g = pair[pair["modal_price"].notna()].sort_values("date")  # price days only
            if g.empty:
                rows.append({"market": market, "crop": crop, "first": "", "last": "",
                             "reported_days": 0, "span_days": 0, "coverage_pct": 0.0,
                             "arrivals_pct": "", "arrivals_only_days": len(pair),
                             "longest_gap_days": "", "gaps_gt_14d": "",
                             "status": "MISSING (synthetic fallback)"})
                continue
            span = (g["date"].max() - g["date"].min()).days + 1
            gaps = g["date"].diff().dt.days.dropna() - 1
            cov = 100 * len(g) / span
            has_arr = cfg["crops"][crop].get("has_arrivals", True)
            status = "ok" if cov >= dp["low_coverage_warn_pct"] else "LOW coverage, weak forecasts"
            if len(g) < 30:
                status = "VERY sparse (<30 days), weak forecasts"
            rows.append({
                "market": market, "crop": crop,
                "first": g["date"].min().date(), "last": g["date"].max().date(),
                "reported_days": len(g), "span_days": span, "coverage_pct": round(cov, 1),
                "arrivals_pct": round(100 * g["arrivals_tonnes"].notna().mean(), 1) if has_arr
                else "n/a (has_arrivals: false)",
                "arrivals_only_days": len(pair) - len(g),
                "longest_gap_days": int(gaps.max()) if len(gaps) else 0,
                "gaps_gt_14d": int((gaps > dp["long_gap_days"]).sum()),
                "status": status,
            })
    return pd.DataFrame(rows)


def write_report(df: pd.DataFrame, rep: PrepReport, cfg: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cov = coverage_table(df, cfg)
    files = pd.DataFrame(rep.files)
    out = ["# Data quality report: data/raw/mandi.csv", "",
           "Generated by `python -m forecaster.data` (agmarknet-data-prep). "
           "Prices are Rs/quintal, arrivals in tonnes.", ""]

    src = ("CEDA Agmarknet API cache (`python -m forecaster.ceda`)" if rep.source == "ceda"
           else "manual website exports in data/raw/ (fallback; run `python -m forecaster.ceda` "
                "for full history)")
    has_price = df["modal_price"].notna()
    out += ["## Summary", "",
            f"- Source: **{src}**",
            f"- Raw price rows read: **{rep.rows_in_price}**; raw quantity rows read: "
            f"**{rep.rows_in_qty}**",
            f"- Rows in mandi.csv (one per date x market x crop): **{len(df)}** "
            f"({int(has_price.sum())} with a price, {int((~has_price).sum())} arrivals-only)",
            f"- Date range: **{df['date'].min().date()} to {df['date'].max().date()}**",
            f"- Markets with real data: {df['market'].nunique()} "
            f"({', '.join(sorted(df['market'].unique()))})",
            f"- Crops with real data: {', '.join(sorted(df['commodity'].unique()))}",
            f"- Rows with arrivals: {int(df['arrivals_tonnes'].notna().sum())} "
            f"({100 * df['arrivals_tonnes'].notna().mean():.1f}%)", ""]
    for crop in cfg["crops"]:
        g = df[(df["commodity"] == crop) & df["modal_price"].notna()]
        if g.empty:
            continue
        months = g["date"].dt.to_period("M").astype(str).value_counts().sort_index()
        runs = _month_runs(list(months.index))
        out.append(f"- **{crop}**: {len(g)} priced market-days, months present: {runs}; "
                   f"arrivals on {int(df.loc[df['commodity'] == crop, 'arrivals_tonnes'].notna().sum())} rows")
    out.append("")

    trunc = files[files["truncated"]] if not files.empty else files
    out += ["## Important findings", ""]
    if not trunc.empty and rep.source == "exports":
        out.append(f"- **Truncated exports:** {len(trunc)} of {len(files)} files have exactly "
                   f"{sorted(trunc['rows'].unique().tolist())} data rows, a typical download cap. "
                   "Each keeps only the newest rows, so older dates are missing (see the per-file "
                   "date ranges below). Fix: `python -m forecaster.ceda` (API, full history).")
    elif not trunc.empty:
        out.append(f"- **Possibly capped API responses:** {len(trunc)} window(s) returned a round "
                   f"row count {sorted(trunc['rows'].unique().tolist())}. Lower `ceda.min_chunk_days` "
                   "or `ceda.chunk_years` and rerun `python -m forecaster.ceda`.")
    for note in rep.notes:
        out.append(f"- {note}")
    for crop in cfg["crops"]:
        seen = set(df.loc[(df["commodity"] == crop) & df["modal_price"].notna(), "date"].dt.month)
        if seen:
            never = [pd.Timestamp(2000, m, 1).strftime("%b") for m in range(1, 13) if m not in seen]
            if never:
                out.append(f"- **{crop}**: no real prices for calendar month(s) {', '.join(never)}; "
                           "seasonal (monthly) models will lean on synthetic data or fallbacks there.")
    for crop, spec in cfg["crops"].items():
        g = df[df["commodity"] == crop]
        if g.empty:
            continue
        n = int(g["arrivals_tonnes"].notna().sum())
        if not spec.get("has_arrivals", True):
            out.append(f"- **{crop}**: `has_arrivals: false` in config, arrivals_tonnes forced empty.")
        elif n == 0:
            out.append(f"- **{crop}**: no quantity data found, arrivals_tonnes is empty (NaN) on all "
                       "rows. Arrivals were not estimated or invented; the arrivals model and the "
                       "demand signal fall back to synthetic data for this crop.")
    out.append("- Missing days (Sundays, holidays, non-reporting) are left missing; "
               "nothing is interpolated or forward-filled.")
    out.append("")

    out += ["## Files read", "", _md_table(files), ""]

    dropped = pd.DataFrame([{"reason": k, "rows": v} for k, v in rep.dropped.items() if v])
    out += ["## Dropped rows by reason", "",
            "Counts are raw price/quantity rows (before variety collapse) except the outlier "
            "and arrivals-only rows, which are market-days.", "", _md_table(dropped), ""]

    out += ["## Coverage per market x crop", "",
            "`coverage_pct` = reported days / calendar days between the pair's first and last "
            "report. Gaps are in calendar days. Coverage below "
            f"{cfg['data_prep']['low_coverage_warn_pct']}% means forecasts for that pair will "
            "be weak.", "", _md_table(cov), ""]
    missing = cov[cov["reported_days"] == 0]
    out += ["### Configured pairs with no real data", "",
            ", ".join(f"{r.market} x {r.crop}" for r in missing.itertuples()) or "_none_",
            "", "These will use synthetic data (data_source = \"synthetic\").", ""]

    wd = (df.assign(dow=df["date"].dt.day_name().str[:3])
            .groupby(["market", "dow"]).size().unstack(fill_value=0))
    order = [d for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] if d in wd.columns]
    wd = wd[order].reset_index()
    out += ["## Reporting days by weekday (all crops)", "",
            "Useful later for `likely_closed` days.", "", _md_table(wd), ""]

    arr = (df.dropna(subset=["arrivals_tonnes"]).groupby(["market", "commodity"])["arrivals_tonnes"]
             .median().round(1).unstack().reset_index())
    out += ["## Arrivals unit check", "",
            "Quantity exports have a bare `qty` column; they are read as **tonnes** "
            "(`data_prep.default_arrivals_unit`). Median daily arrivals (tonnes) below: Pune main "
            "yard in the hundreds of tonnes and small sub-yards at a few tonnes is consistent "
            "with tonnes, not quintals.", "", _md_table(arr), ""]

    unknown = [{"kind": "market", "raw name": k, "rows": v} for k, v in rep.unknown_markets.items()]
    unknown += [{"kind": "crop", "raw name": k, "rows": v} for k, v in rep.unknown_crops.items()]
    out += ["## Unknown names", "",
            "Raw names not in config.yaml aliases (rows dropped, add an alias to keep them):", "",
            _md_table(pd.DataFrame(unknown)), ""]

    cols = ["date", "market", "commodity", "min_price", "max_price", "modal_price"]
    def recs(r, extra=()):
        d = pd.DataFrame(r)
        if d.empty:
            return d
        d = d[cols + list(extra)].copy()
        d["date"] = pd.to_datetime(d["date"]).dt.date
        for c in ["modal_price", *extra]:
            d[c] = d[c].astype(float).round(2)
        return d.sort_values(["commodity", "date"])
    out += ["## Dropped outliers", "",
            "modal_price > 4x or < 0.25x the centred 30-calendar-day rolling median of the pair.",
            "", _md_table(recs(rep.outliers, ["rolling_median", "ratio"])), ""]
    out += ["## Flagged prices (kept unless also an outlier)", "",
            "Outside the crop's plausible Rs/quintal range in config.yaml. Low values may be "
            "Rs/kg entries or genuine gluts; they are NOT converted.", "",
            "### Below plausible minimum", "", _md_table(recs(rep.flagged_low_price)), "",
            "### Above plausible maximum", "", _md_table(recs(rep.flagged_high_price)), ""]
    orphan = rep.orphan_arrivals
    if orphan is not None and not orphan.empty:
        o = (orphan.groupby(["commodity", "market"]).agg(
                rows=("date", "size"), first=("date", "min"), last=("date", "max")).reset_index())
        o["first"], o["last"] = o["first"].dt.date, o["last"].dt.date
        if cfg["data_prep"].get("keep_arrivals_only_rows", False):
            out += ["## Arrivals without a price row (kept, modal_price empty)", "",
                    "Kept for the arrivals model (`data_prep.keep_arrivals_only_rows: true`). "
                    "Price models must filter on `modal_price.notna()`.", "", _md_table(o), ""]
        else:
            out += ["## Arrivals without a price row (dropped)", "",
                    "`keep_arrivals_only_rows` is false, so these market-days are not kept.",
                    "", _md_table(o), ""]
    path.write_text("\n".join(out))


def _month_runs(months: list[str]) -> str:
    """['2024-03','2024-04','2024-06'] -> '2024-03..2024-04, 2024-06'."""
    if not months:
        return ""
    ps = [pd.Period(m, "M") for m in months]
    runs, start, prev = [], ps[0], ps[0]
    for p in ps[1:]:
        if p != prev + 1:
            runs.append((start, prev))
            start = p
        prev = p
    runs.append((start, prev))
    return ", ".join(str(a) if a == b else f"{a}..{b}" for a, b in runs)


def load_ref(cfg: dict | None = None) -> dict[str, pd.DataFrame]:
    """data/ref/ tables (approximate, see data/README.md): markets, crop_calendar, festivals."""
    cfg = cfg or load_config()
    ref = ROOT / cfg["paths"]["ref_dir"]
    markets = pd.read_csv(ref / "markets.csv")
    cal = pd.read_csv(ref / "crop_calendar.csv")
    cal["sowing_months"] = cal["sowing_months"].astype(str).map(
        lambda s: [int(m) for m in s.split(";") if m.strip()])
    fest = pd.read_csv(ref / "festivals.csv", parse_dates=["date"])
    return {"markets": markets, "crop_calendar": cal, "festivals": fest}


def main() -> None:
    cfg = load_config()
    df, rep = prepare(cfg)
    out = ROOT / cfg["paths"]["mandi_csv"]
    out.parent.mkdir(parents=True, exist_ok=True)
    df.assign(date=df["date"].dt.strftime("%Y-%m-%d")).to_csv(out, index=False)
    report = ROOT / cfg["paths"]["reports_dir"] / "data_quality.md"
    write_report(df, rep, cfg, report)
    print(f"wrote {out} ({len(df)} rows) and {report}")


if __name__ == "__main__":
    main()
