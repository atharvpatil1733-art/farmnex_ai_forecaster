"""data/ref/ files exist, parse, and cover every configured market and crop."""
from forecaster.data import load_config, load_ref


def test_ref_files_cover_config():
    cfg, ref = load_config(), load_ref()
    m = ref["markets"]
    assert set(cfg["markets"]) <= set(m["market"])
    assert m["lat"].between(15, 22).all() and m["lon"].between(72, 77).all()  # Maharashtra
    for market, spec in cfg["markets"].items():
        assert m.loc[m["market"] == market, "district"].iloc[0] == spec["district"]
    cal = ref["crop_calendar"].set_index("crop")
    assert set(cfg["crops"]) <= set(cal.index)
    assert all(1 <= mo <= 12 for months in cal["sowing_months"] for mo in months)
    assert (cal["duration_days"] > 30).all()
    f = ref["festivals"]
    assert f["date"].dt.year.min() <= 2015 and f["date"].dt.year.max() >= 2026
    assert f["date"].notna().all()
