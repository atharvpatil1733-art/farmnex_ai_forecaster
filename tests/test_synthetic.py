"""Synthetic data realism checks and the per-pair / per-target real-vs-synthetic fallback."""
import numpy as np
import pandas as pd
import pytest

from forecaster.data import MANDI_COLUMNS, load_config, load_mandi
from forecaster.synthetic import build_panel, generate, pair_sources


@pytest.fixture(scope="module")
def cfg():
    return load_config()


@pytest.fixture(scope="module")
def real():
    return load_mandi()


@pytest.fixture(scope="module")
def synth(cfg, real):
    return generate(cfg, real)


def test_generate_covers_every_pair(cfg, synth, real):
    assert list(synth.columns) == MANDI_COLUMNS
    pairs = set(zip(synth["market"], synth["commodity"]))
    assert pairs == {(m, c) for m in cfg["markets"] for c in cfg["crops"]}
    assert synth["date"].max() == real["date"].max()  # ends at as_of
    span = (synth["date"].max() - synth["date"].min()).days
    assert span >= 365 * cfg["synthetic"]["years"] - 2
    assert (synth["modal_price"] > 0).all()
    assert ((synth["min_price"] <= synth["modal_price"]) & (synth["modal_price"] <= synth["max_price"])).all()


def test_generate_is_realistic(cfg, synth):
    for crop, spec in cfg["synthetic"]["crops"].items():
        s = synth[synth["commodity"] == crop]
        monthly = s.groupby(s["date"].dt.month)["modal_price"].median()
        assert abs(int(monthly.idxmax()) - spec["peak_month"]) <= 1 or {int(monthly.idxmax()), spec["peak_month"]} == {12, 1}
        # arrivals move against price within a pair
        one = s[s["market"] == "Pune"]
        assert np.corrcoef(np.log(one["modal_price"]), np.log(one["arrivals_tonnes"]))[0, 1] < 0
    # markets are not open every day (gaps like real mandis)
    per_pair = synth.groupby(["market", "commodity"]).size()
    assert (per_pair < 365 * cfg["synthetic"]["years"] * 0.95).all()


def test_generate_is_deterministic(cfg, real):
    a, b = generate(cfg, real), generate(cfg, real)
    pd.testing.assert_frame_equal(a, b)


def test_fallback_is_per_pair_and_per_target(cfg, real, synth):
    # Remove tomato arrivals from a copy so the test does not depend on what the source provides.
    real = real.copy()
    real.loc[real["commodity"] == "Tomato", "arrivals_tonnes"] = np.nan
    real = real[real["market"] != "Vashi"]  # and pretend Vashi has no real data
    panel, src = build_panel(cfg, real, synth)
    s = src.set_index(["market", "commodity"])
    # Pune Onion has real price and real arrivals
    assert tuple(s.loc[("Pune", "Onion"), ["price_source", "arrivals_source"]]) == ("real", "real")
    # real prices but no real arrivals -> synthetic arrivals only
    assert tuple(s.loc[("Pune", "Tomato"), ["price_source", "arrivals_source"]]) == ("real", "synthetic")
    # Vashi has no real data at all
    assert tuple(s.loc[("Vashi", "Onion"), ["price_source", "arrivals_source"]]) == ("synthetic", "synthetic")

    # real rows are passed through untouched where the pair is real
    r = real[(real["market"] == "Pune") & (real["commodity"] == "Onion")].dropna(subset=["modal_price"])
    p = panel[(panel["market"] == "Pune") & (panel["commodity"] == "Onion")].dropna(subset=["modal_price"])
    pd.testing.assert_series_equal(r.set_index("date")["modal_price"].sort_index(),
                                   p.set_index("date")["modal_price"].sort_index())
    # tomato price rows are real prices; synthetic arrivals are marked as such
    tp = panel[(panel["market"] == "Pune") & (panel["commodity"] == "Tomato")]
    real_t = real[(real["market"] == "Pune") & (real["commodity"] == "Tomato")]
    assert set(tp.dropna(subset=["modal_price"])["date"]) == set(real_t.dropna(subset=["modal_price"])["date"])
    assert (tp["arrivals_source"] == "synthetic").all()


def test_thin_pair_counts_as_synthetic(cfg):
    real = pd.DataFrame({"date": pd.date_range("2025-01-01", periods=5), "district": "Pune",
                         "market": "Pune", "commodity": "Onion", "min_price": 900.0,
                         "max_price": 1100.0, "modal_price": 1000.0, "arrivals_tonnes": np.nan})
    src = pair_sources(real, cfg).set_index(["market", "commodity"])
    assert src.loc[("Pune", "Onion"), "price_source"] == "synthetic"  # < min_real_days
