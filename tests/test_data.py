"""Tests for forecaster.data: the cleaned mandi.csv and the prep pipeline on messy input."""
import copy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from forecaster.data import MANDI_COLUMNS, load_config, load_mandi, prepare

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def mandi():
    return load_mandi()


def test_mandi_csv_schema_and_keys(mandi):
    assert list(mandi.columns) == MANDI_COLUMNS
    assert pd.api.types.is_datetime64_any_dtype(mandi["date"])
    assert not mandi.duplicated(["date", "market", "commodity"]).any()
    priced = mandi[mandi["modal_price"].notna()]
    assert len(priced) > 0
    assert (priced["modal_price"] > 0).all()
    assert (priced["min_price"] <= priced["modal_price"]).all()
    assert (priced["modal_price"] <= priced["max_price"]).all()
    # Every row carries at least one observation: a price or arrivals.
    assert (mandi["modal_price"].notna() | mandi["arrivals_tonnes"].notna()).all()


def test_mandi_names_are_canonical(mandi):
    cfg = load_config()
    assert set(mandi["market"]) <= set(cfg["markets"])
    assert set(mandi["commodity"]) <= set(cfg["crops"])
    assert mandi["district"].notna().all()


def test_onion_potato_have_arrivals(mandi):
    for crop in ("Onion", "Potato"):
        assert mandi.loc[mandi["commodity"] == crop, "arrivals_tonnes"].notna().mean() > 0.5


def _write(path, text):
    path.write_text(text.strip() + "\n")


def test_prepare_handles_messy_export(tmp_path):
    cfg = load_config()
    # Title rows above the header, Agmarknet-style headers, dd/mm/yyyy dates, alias names,
    # two varieties on one day, min > max, a footer row, an unknown market and a duplicate.
    _write(tmp_path / "prices.csv", """
Agmarknet Price Report
Commodity wise,,,,,,
District Name,Market Name,Commodity,Variety,Min Price (Rs./Quintal),Max Price (Rs./Quintal),Modal Price (Rs./Quintal),Price Date
Pune,Pune(Pimpri) APMC,Onion Red,Red,1000,2000,1500,01/02/2025
Pune,Pune(Pimpri) APMC,Onion Red,Local,1200,2200,1700,01/02/2025
Pune,Pune(Pimpri) APMC,Onion Red,Local,1200,2200,1700,01/02/2025
Pune,Khed (Chakan),Tomato,Local,900,700,800,02/02/2025
Pune,Somewhere Else,Onion,Local,900,1000,950,02/02/2025
Total,,,,,,,
""")
    _write(tmp_path / "arrivals.csv", """
Price Date,Market Name,Commodity,Arrivals (Quintals)
01/02/2025,Pimpri,Onion,50
02/02/2025,Chakan,Tomato,30
""")
    df, rep = prepare(cfg, raw_dir=tmp_path)
    assert list(df.columns) == MANDI_COLUMNS
    assert len(df) == 2

    onion = df[df["commodity"] == "Onion"].iloc[0]
    assert onion["market"] == "Pimpri" and onion["district"] == "Pune"
    assert onion["date"] == pd.Timestamp("2025-02-01")  # day-first, not 2 Jan
    assert onion["modal_price"] == pytest.approx(1600)  # mean of the two varieties
    assert (onion["min_price"], onion["max_price"]) == (1000, 2200)
    assert onion["arrivals_tonnes"] == pytest.approx(5.0)  # 50 quintals -> 5 tonnes

    tomato = df[df["commodity"] == "Tomato"].iloc[0]
    assert tomato["market"] == "Khed(Chakan)"
    assert (tomato["min_price"], tomato["max_price"]) == (700, 900)  # swapped
    assert tomato["arrivals_tonnes"] == pytest.approx(3.0)  # real qty data is used when present

    assert rep.unknown_markets["Somewhere Else"] == 1
    assert rep.dropped["exact duplicate price row (overlapping exports)"] == 1
    assert rep.dropped["unparseable date (footer/total rows)"] >= 1


def test_has_arrivals_false_forces_nan(tmp_path):
    cfg = copy.deepcopy(load_config())
    cfg["crops"]["Tomato"]["has_arrivals"] = False
    _write(tmp_path / "p.csv", "t,cmdty,market_name,p_min,p_max,p_modal\n2025-06-01,Tomato,Pune,900,1100,1000")
    _write(tmp_path / "q.csv", "t,cmdty,market_name,qty\n2025-06-01,Tomato,Pune,40")
    df, _ = prepare(cfg, raw_dir=tmp_path)
    assert df["arrivals_tonnes"].isna().all()


def test_market_has_arrivals_false_drops_only_that_market(tmp_path):
    cfg = copy.deepcopy(load_config())
    cfg["markets"]["Kalyan"]["has_arrivals"] = False
    _write(tmp_path / "p.csv", "t,cmdty,market_name,p_min,p_max,p_modal\n"
           "2025-06-01,Onion,Kalyan,900,1100,1000\n2025-06-01,Onion,Pune,900,1100,1000")
    _write(tmp_path / "q.csv", "t,cmdty,market_name,qty\n2025-06-01,Onion,Kalyan,0.3\n"
           "2025-06-02,Onion,Kalyan,0.3\n2025-06-01,Onion,Pune,800")
    df, rep = prepare(cfg, raw_dir=tmp_path)
    kalyan = df[df["market"] == "Kalyan"]
    assert len(kalyan) == 1 and kalyan["arrivals_tonnes"].isna().all()  # no arrivals-only row either
    assert df.loc[df["market"] == "Pune", "arrivals_tonnes"].tolist() == [800]
    assert any("market Kalyan" in n for n in rep.notes)


def test_arrivals_only_days_are_kept(tmp_path):
    cfg = load_config()
    _write(tmp_path / "p.csv", "t,cmdty,market_name,p_min,p_max,p_modal\n2025-06-02,Onion,Pune,900,1100,1000")
    _write(tmp_path / "q.csv", "t,cmdty,market_name,qty\n2025-06-01,Onion,Pune,800\n2025-06-02,Onion,Pune,850")
    df, rep = prepare(cfg, raw_dir=tmp_path)
    assert len(df) == 2
    first = df.sort_values("date").iloc[0]
    assert np.isnan(first["modal_price"]) and first["arrivals_tonnes"] == 800
    assert len(rep.orphan_arrivals) == 1

    cfg = copy.deepcopy(cfg)
    cfg["data_prep"]["keep_arrivals_only_rows"] = False
    df, rep = prepare(cfg, raw_dir=tmp_path)
    assert len(df) == 1 and df["modal_price"].notna().all()


def test_prepare_drops_outlier(tmp_path):
    cfg = load_config()
    dates = pd.date_range("2025-06-01", periods=20, freq="D")
    rows = [f"{d:%Y-%m-%d},Onion,Pune,Pune,Local,900,1100,1000" for d in dates]
    rows[10] = f"{dates[10]:%Y-%m-%d},Onion,Pune,Pune,Local,9000,11000,10000"
    _write(tmp_path / "p.csv", "t,cmdty,market_name,district_name,variety,p_min,p_max,p_modal\n"
           + "\n".join(rows))
    df, rep = prepare(cfg, raw_dir=tmp_path)
    assert len(df) == 19
    assert df["modal_price"].max() == 1000
    assert len(rep.outliers) == 1


AGMARKNET_REPORT = """,,,,,,,Daily Price Arrival Report-07-11-2025 to 28-09-2026 for Maharashtra,,,,,,
State/UT,District,Market,Commodity Group,Commodity,Variety,Grade,Min Price,Max Price,Modal Price,Price Unit,Arrival Quantity,Arrival Unit,Arrival Date
Maharashtra,Mumbai,Mumbai-Onion & Potato Market ,Vegetables,Onion,Other,Local,"2,900.00","4,800.00","3,850.00",Rs./Quintal,"1,535.50",Metric Tonnes,28-09-2026
Maharashtra,Mumbai,Mumbai-Onion & Potato Market ,Vegetables,Onion,Other,Local,700.00,"1,900.00","1,300.00",Rs./Quintal,"1,049.50",Metric Tonnes,07-11-2025
Maharashtra,Pune,APMC Pune ,Vegetables,Onion,Local,Local,500.00,"1,500.00","1,150.00",Rs./Quintal,120.00,Quintal,07-11-2025
"""


def test_agmarknet_daily_price_arrival_report(tmp_path):
    """agmarknet.gov.in reports: title row, "2,900.00" numbers, price AND arrivals per row,
    per-row arrival unit, dd-mm-yyyy dates."""
    (tmp_path / "Mumbai Onion Daily Price Arrival Report.csv").write_text(AGMARKNET_REPORT)
    df, rep = prepare(load_config(), raw_dir=tmp_path)
    assert not rep.unknown_markets
    vashi = df[df["market"] == "Vashi"].set_index("date")
    assert vashi.loc["2026-09-28", "modal_price"] == 3850 and vashi.loc["2026-09-28", "min_price"] == 2900
    assert vashi.loc["2026-09-28", "arrivals_tonnes"] == pytest.approx(1535.5)
    assert vashi.loc["2025-11-07", "arrivals_tonnes"] == pytest.approx(1049.5)
    pune = df[df["market"] == "Pune"].iloc[0]  # "APMC Pune" -> Pune
    assert pune["modal_price"] == 1150 and pune["arrivals_tonnes"] == pytest.approx(12.0)  # 120 q


def test_ceda_then_exports_never_overlap(tmp_path):
    """source ceda+exports: CEDA for its dates, exports ONLY for dates after the last CEDA date."""
    import json
    ceda = tmp_path / "ceda"
    (ceda / "price").mkdir(parents=True)
    (ceda / "quantity").mkdir()
    recs = [{"date": f"2025-11-0{d}T00:00:00", "market_id": 1, "market_name": "Pune",
             "min_price": 900, "max_price": 1100, "modal_price": 1000} for d in range(1, 6)]
    (ceda / "price" / "Onion_x.json").write_text(json.dumps({"crop": "Onion", "records": recs}))
    qrecs = [{"date": r["date"], "market_id": 1, "market_name": "Pune", "quantity": 500.0} for r in recs]
    (ceda / "quantity" / "Onion_x.json").write_text(json.dumps({"crop": "Onion", "records": qrecs}))
    exports = tmp_path / "exports"
    exports.mkdir()
    rows = "".join(f'Maharashtra,Pune,APMC Pune ,Vegetables,Onion,Local,Local,"1,800.00","2,200.00",'
                   f'"2,000.00",Rs./Quintal,"1,200.00",Metric Tonnes,0{d}-11-2025\n' for d in range(3, 9))
    (exports / "Pune Onion report.csv").write_text("".join(AGMARKNET_REPORT.splitlines(keepends=True)[:2]) + rows)

    cfg = copy.deepcopy(load_config())
    cfg["data_prep"]["source"] = "ceda+exports"
    cfg["paths"]["exports_dir"] = str(exports)
    df, rep = prepare(cfg, raw_dir=exports, ceda_dir=ceda)
    assert rep.source == "ceda+exports" and str(rep.exports_after) == "2025-11-05"
    pune = df[df["market"] == "Pune"].set_index("date").sort_index()
    assert not pune.index.duplicated().any()
    assert list(pune.index.day) == [1, 2, 3, 4, 5, 6, 7, 8]
    assert (pune.loc[:"2025-11-05", "modal_price"] == 1000).all()      # CEDA wins on 3..5 Nov
    assert (pune.loc[:"2025-11-05", "arrivals_tonnes"] == 500).all()
    assert (pune.loc["2025-11-06":, "modal_price"] == 2000).all()      # exports only after cutoff
    assert (pune.loc["2025-11-06":, "arrivals_tonnes"] == 1200).all()
    assert rep.exports_rows_used == 6 and rep.exports_rows_skipped == 6  # 3 price + 3 qty each
