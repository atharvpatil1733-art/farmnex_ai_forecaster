"""No-leakage and calendar-day correctness tests for forecaster.features."""
import numpy as np
import pandas as pd
import pytest

from forecaster.data import load_config, load_ref
from forecaster.features import (daily_calendar, feature_columns, origin_features,
                                 split_and_stack, stack_horizon)

CFG = load_config()
FEST = load_ref(CFG)["festivals"]["date"]


def gappy_panel(n_days=80, seed=0):
    """Two pairs, ~5 reports a week, one 20-day gap, real prices and arrivals."""
    rng = np.random.default_rng(seed)
    rows = []
    for market in ("Pune", "Pimpri"):
        for i, d in enumerate(pd.date_range("2025-01-01", periods=n_days)):
            if d.dayofweek == 6 or rng.random() < 0.15 or 30 <= i < 50:
                continue
            rows.append({"date": d, "district": "Pune", "market": market, "commodity": "Onion",
                         "min_price": 900.0, "max_price": 2000.0, "modal_price": 1000.0 + 10 * i,
                         "arrivals_tonnes": 50.0 + i, "price_source": "real", "arrivals_source": "real"})
    return pd.DataFrame(rows)


def features_at(panel, end, target="price"):
    return origin_features(daily_calendar(panel, end), target)


@pytest.mark.parametrize("target", ["price", "arrivals"])
def test_changing_the_future_never_changes_past_features(target):
    panel = gappy_panel()
    end = panel["date"].max()
    t = pd.Timestamp("2025-02-25")
    base = features_at(panel, end, target)
    future = panel["date"] > t
    shocked = panel.copy()
    shocked.loc[future, ["modal_price", "arrivals_tonnes"]] *= 7.0
    moved = features_at(shocked, end, target)
    cols = [c for c in feature_columns(target) if c in base and c not in ("market", "commodity")]
    past_b = base[base["date"] <= t].set_index(["market", "date"])[cols]
    past_m = moved[moved["date"] <= t].set_index(["market", "date"])[cols]
    pd.testing.assert_frame_equal(past_b, past_m)


def test_split_by_target_date_and_train_rows_only_see_data_up_to_cutoff():
    panel = gappy_panel()
    end = panel["date"].max()
    cutoff = end - pd.Timedelta(days=15)
    of = features_at(panel, end)
    train, test = split_and_stack(of, [1, 2, 3], cutoff, FEST, CFG)
    assert train["target_date"].max() <= cutoff < test["target_date"].min()
    assert set(zip(train["market"], train["target_date"])).isdisjoint(zip(test["market"], test["target_date"]))
    # Rebuild with the data truncated at the cutoff: train rows must be identical.
    of_cut = features_at(panel[panel["date"] <= cutoff], end)
    train_cut, _ = split_and_stack(of_cut, [1, 2, 3], cutoff, FEST, CFG)
    cols = [c for c in feature_columns("price") if c not in ("market", "commodity")] + ["y_true", "baseline"]
    key = ["market", "date", "horizon"]
    pd.testing.assert_frame_equal(train.sort_values(key).reset_index(drop=True)[cols],
                                  train_cut.sort_values(key).reset_index(drop=True)[cols])


def test_lags_are_calendar_days_not_rows():
    panel = gappy_panel()
    of = features_at(panel, panel["date"].max())
    s = panel[panel["market"] == "Pune"].set_index("date")["modal_price"]
    f = of[of["market"] == "Pune"].set_index("date")
    for t in f.index[20:]:
        for k in (1, 2, 3, 7, 14):
            want = s.get(t - pd.Timedelta(days=k - 1), np.nan)
            got = np.expm1(f.loc[t, f"y_lag_{k}"])
            assert (np.isnan(want) and np.isnan(got)) or got == pytest.approx(want)


def test_rolling_needs_three_points_and_gap_is_not_filled():
    panel = gappy_panel()
    of = features_at(panel, panel["date"].max())
    f = of[of["market"] == "Pune"].set_index("date")
    in_gap = f.loc["2025-02-16":"2025-02-19"]  # >= 16 days into the 20-day gap
    assert in_gap["y_roll_mean_7"].isna().all() and in_gap["y_roll_mean_14"].isna().all()
    assert (in_gap["days_since_last_report"] >= 16).all()
    assert (in_gap["reports_last_7d"] == 0).all()


def test_target_and_baseline_alignment():
    panel = gappy_panel()
    of = features_at(panel, panel["date"].max())
    s = panel[panel["market"] == "Pune"].set_index("date")["modal_price"]
    for h in (1, 2, 3):
        st = stack_horizon(of, h, FEST, CFG)
        st = st[(st["market"] == "Pune") & st["y_true"].notna()].set_index("date")
        for t, r in st.iloc[::7].iterrows():
            assert r["y_true"] == s[t + pd.Timedelta(days=h)]
            wk = t + pd.Timedelta(days=h - 7)
            if wk in s.index:
                assert r["baseline"] == s[wk]
            assert r["dow"] == (t + pd.Timedelta(days=h)).dayofweek  # calendar of the TARGET day


def test_price_model_ignores_synthetic_arrivals():
    panel = gappy_panel()
    panel["arrivals_source"] = "synthetic"
    of = features_at(panel, panel["date"].max())
    assert of[["arr_lag_1", "arr_lag_7", "arr_roll_mean_7"]].isna().all().all()


def test_evaluation_panel_ignores_post_cutoff_real_data():
    """Synthetic calibration for evaluation must not see test-period real prices."""
    from forecaster.data import load_mandi
    from forecaster.train import eval_panel
    real = load_mandi()
    as_of = real["date"].max()
    cutoff = as_of - pd.Timedelta(days=int(CFG["modelling"]["test_days"]))
    shocked = real.copy()
    shocked.loc[shocked["date"] > cutoff, "modal_price"] *= 5
    a, b = eval_panel(CFG, real, cutoff, as_of), eval_panel(CFG, shocked, cutoff, as_of)
    syn_a = a[a["price_source"] == "synthetic"].reset_index(drop=True)
    syn_b = b[b["price_source"] == "synthetic"].reset_index(drop=True)
    pd.testing.assert_frame_equal(syn_a, syn_b)
