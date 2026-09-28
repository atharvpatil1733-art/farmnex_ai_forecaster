"""Tests for forecaster.ceda against a fake CEDA server (no network, no API key needed)."""
import copy
import json
from datetime import date, timedelta

import httpx
import pytest

from forecaster.ceda import (BudgetExhausted, CedaAuthError, CedaClient, CedaRateLimitError,
                             Downloader, date_chunks)
from forecaster.data import load_config, prepare

MARKETS = {1: "Pune", 2: "Pune(Pimpri)", 3: "Junnar(Otur)"}
THANE_MARKETS = {9: "Kalyan"}
DISTRICT_MARKETS = {521: MARKETS, 517: THANE_MARKETS}
CROPS = {"Onion": 23, "Tomato": 78, "Potato": 24}


def ok(data):
    return httpx.Response(200, json={"output": {"type": "success", "message": "", "data": data}})


class FakeCeda:
    """Mimics the live API: envelope, id-based rows, POST bodies with date windows."""

    def __init__(self, cap=None, quantities=True, hang_on_market_filter=False, timeout_over_days=None):
        self.cap, self.quantities, self.calls = cap, quantities, []
        # Live behaviour seen on 2026-09-27: a market_id filter (and /markets) -> 504 after 60 s.
        self.hang_on_market_filter, self.timeout_over_days = hang_on_market_filter, timeout_over_days

    def __call__(self, request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-key"
        path = request.url.path.removeprefix("/v1")
        body = json.loads(request.content) if request.content else {}
        self.calls.append((path, body))
        if path == "/agmarknet/geographies":
            return ok([{"census_state_id": 27, "census_state_name": "Maharashtra",
                        "census_district_id": 521, "census_district_name": "Pune"},
                       {"census_state_id": 27, "census_state_name": "Maharashtra",
                        "census_district_id": 517, "census_district_name": "Thane"},
                       {"census_state_id": 27, "census_state_name": "Maharashtra",
                        "census_district_id": 519, "census_district_name": "Mumbai"}])
        if path == "/agmarknet/commodities":
            return ok([{"commodity_id": v, "commodity_name": k} for k, v in CROPS.items()])
        if path == "/agmarknet/markets":
            if self.hang_on_market_filter:
                return httpx.Response(504, text="<html>504 Gateway Time-out</html>")
            return ok([{"market_id": k, "market_name": v}
                       for k, v in DISTRICT_MARKETS.get(body.get("district_id"), MARKETS).items()])
        if path in ("/agmarknet/prices", "/agmarknet/quantities"):
            if path.endswith("quantities") and not self.quantities:
                return httpx.Response(404, json={"detail": "Not Found"})
            if self.hang_on_market_filter and "market_id" in body:
                return httpx.Response(504, text="<html>504 Gateway Time-out</html>")
            a, b = date.fromisoformat(body["from_date"]), date.fromisoformat(body["to_date"])
            if self.timeout_over_days and (b - a).days + 1 > self.timeout_over_days:
                return httpx.Response(504, text="<html>504 Gateway Time-out</html>")
            rows, d = [], a
            while d <= b:
                pairs = [(did, mid) for did in body["district_id"] for mid in DISTRICT_MARKETS.get(did, {})
                         if not body.get("market_id") or mid in body["market_id"]]
                for did, mid in pairs:
                    base = {"date": f"{d.isoformat()}T00:00:00", "commodity_id": body["commodity_id"],
                            "census_state_id": 27, "census_district_id": did, "market_id": mid}
                    if path.endswith("prices"):
                        rows.append(dict(base, min_price=900, max_price=1100, modal_price=1000 + mid))
                    else:
                        rows.append(dict(base, quantity=100.0 * mid))
                d += timedelta(days=1)
            if self.cap and len(rows) > self.cap:
                rows = rows[-self.cap:]  # like the website: keep only the newest rows
            return ok(rows)
        return httpx.Response(404)


def make_cfg(start="2024-01-01", end="2024-01-10", years=1, budget=100, fetch_lists=True):
    cfg = copy.deepcopy(load_config())
    cfg["ceda"].update(districts=["Pune"], start_date=start, end_date=end, chunk_years=years,
                       max_requests_per_run=budget, min_chunk_days=2,
                       fetch_market_lists=fetch_lists, fetch_market_names=False)
    return cfg


def district_cfg(tmp_path, **kw):
    """Live-like config: no market lists; ids get names from an export CSV with market_id."""
    cfg = make_cfg(fetch_lists=False, **kw)
    exports = tmp_path / "exports"
    exports.mkdir()
    (exports / "old_export.csv").write_text(
        "t,cmdty,market_id,market_name,p_modal\n" +
        "".join(f"2024-01-01,Onion,{k},{v},1000\n" for k, v in MARKETS.items()))
    cfg["paths"]["exports_dir"] = str(exports)
    return cfg


def client(fake, budget=100):
    return CedaClient("test-key", "https://api.test/v1", max_requests=budget, min_interval=0,
                      transport=httpx.MockTransport(fake))


def test_date_chunks_cover_range_without_overlap():
    chunks = date_chunks(date(2012, 3, 1), date(2026, 9, 27), 5)
    assert chunks[0] == (date(2012, 3, 1), date(2016, 12, 31))
    assert chunks[-1][1] == date(2026, 9, 27)
    for (_, b), (a, _) in zip(chunks, chunks[1:]):
        assert a == b + timedelta(days=1)


def test_download_then_prepare_end_to_end(tmp_path):
    fake, cfg = FakeCeda(), make_cfg()
    summary = Downloader(cfg, client(fake), tmp_path, today=date(2026, 9, 27)).run()
    assert summary["state_id"] == 27 and summary["districts"] == {"Pune": 521}
    assert {c["indicator"] for c in summary["chunks"]} == {"price", "quantity"}
    assert (tmp_path / "manifest.json").exists()

    df, rep = prepare(cfg, ceda_dir=tmp_path)
    assert rep.source == "ceda"
    assert set(df["market"]) == {"Pune", "Pimpri", "Otur"}  # aliases applied to API names
    assert set(df["commodity"]) == set(CROPS)
    assert len(df) == 10 * 3 * 3
    pimpri = df[(df["market"] == "Pimpri") & (df["commodity"] == "Onion")].iloc[0]
    assert pimpri["modal_price"] == 1002 and pimpri["arrivals_tonnes"] == 200.0


def test_rerun_uses_cache(tmp_path):
    cfg = make_cfg()
    Downloader(cfg, client(FakeCeda()), tmp_path, today=date(2026, 9, 27)).run()
    fake2 = FakeCeda()
    Downloader(cfg, client(fake2), tmp_path, today=date(2026, 9, 27)).run()
    assert fake2.calls == []  # closed windows and reference lists all came from disk


def test_capped_response_is_split(tmp_path):
    fake, cfg = FakeCeda(cap=24), make_cfg(end="2024-01-20")  # 20 days x 3 markets = 60 rows
    cfg["ceda"]["suspicious_row_counts"] = [24]
    d = Downloader(cfg, client(fake), tmp_path, today=date(2026, 9, 27))
    d.run()
    assert any("splitting" in line for line in d.log)
    df, _ = prepare(cfg, ceda_dir=tmp_path)
    onion = df[(df["commodity"] == "Onion") & (df["market"] == "Pune")]
    assert onion["date"].min().date() == date(2024, 1, 1)  # oldest days recovered


def test_budget_stop_then_resume(tmp_path):
    cfg = make_cfg()
    with pytest.raises(BudgetExhausted):
        Downloader(cfg, client(FakeCeda(), budget=5), tmp_path, today=date(2026, 9, 27)).run()
    Downloader(cfg, client(FakeCeda()), tmp_path, today=date(2026, 9, 27)).run()
    df, _ = prepare(cfg, ceda_dir=tmp_path)
    assert len(df) == 90


def test_quantity_endpoint_failure_keeps_prices(tmp_path):
    cfg = make_cfg()
    summary = Downloader(cfg, client(FakeCeda(quantities=False)), tmp_path,
                         today=date(2026, 9, 27)).run()
    assert any("quantity" in s for s in summary["skipped"])
    df, _ = prepare(cfg, ceda_dir=tmp_path)
    assert df["modal_price"].notna().all() and df["arrivals_tonnes"].isna().all()


def test_auth_and_rate_limit_errors():
    c = client(lambda r: httpx.Response(401))
    with pytest.raises(CedaAuthError):
        c.request("GET", "/agmarknet/commodities")
    c = client(lambda r: httpx.Response(429, headers={"Retry-After": "120"}))
    with pytest.raises(CedaRateLimitError) as e:
        c.request("GET", "/agmarknet/commodities")
    assert e.value.retry_after_seconds == 120


def test_api_key_never_in_error_text():
    c = client(lambda r: httpx.Response(400, text="bad key test-key"))
    with pytest.raises(Exception) as e:
        c.request("GET", "/agmarknet/commodities")
    assert "test-key" not in str(e.value)


def test_district_level_fetch_never_sends_market_filter(tmp_path):
    """The live API hangs on market_id filters and /markets: fetch per district, map ids locally."""
    fake = FakeCeda(hang_on_market_filter=True)
    cfg = district_cfg(tmp_path)
    cache = tmp_path / "ceda"
    Downloader(cfg, client(fake), cache, today=date(2026, 9, 27)).run()
    data_calls = [b for p, b in fake.calls if p in ("/agmarknet/prices", "/agmarknet/quantities")]
    assert data_calls and all("market_id" not in b and b["district_id"] == [521] for b in data_calls)
    assert not any(p == "/agmarknet/markets" for p, _ in fake.calls)

    df, rep = prepare(cfg, ceda_dir=cache)
    assert rep.source == "ceda"
    assert set(df["market"]) == {"Pune", "Pimpri", "Otur"}  # names from the export's market_id column
    assert len(df) == 10 * 3 * 3


def test_gateway_timeout_splits_window(tmp_path):
    fake = FakeCeda(hang_on_market_filter=True, timeout_over_days=5)
    cfg = district_cfg(tmp_path, end="2024-01-20")
    d = Downloader(cfg, client(fake), tmp_path / "ceda", today=date(2026, 9, 27))
    d.run()
    assert any("splitting the window" in line for line in d.log)
    df, _ = prepare(cfg, ceda_dir=tmp_path / "ceda")
    onion = df[(df["commodity"] == "Onion") & (df["market"] == "Pune")]
    assert onion["date"].min().date() == date(2024, 1, 1)
    assert onion["date"].max().date() == date(2024, 1, 20)


def test_adding_a_district_fetches_only_the_new_one(tmp_path):
    """Old cache files (no district in the name) stay valid; a new district costs one request
    per window and indicator x crop, and never re-downloads Pune."""
    cfg = district_cfg(tmp_path, end="2024-12-31")
    cfg["ceda"]["refresh_open_chunk"] = False
    cache = tmp_path / "ceda"
    Downloader(cfg, client(FakeCeda()), cache, today=date(2026, 9, 27)).run()
    for f in (cache / "price").glob("*__d521.json"):  # simulate the older cache layout
        f.rename(f.with_name(f.name.replace("__d521", "")))

    cfg["ceda"]["districts"] = ["Pune", "Thane"]
    # /markets hangs live, so a new district's ids are named via "market_id N" aliases.
    cfg["markets"]["Kalyan"]["aliases"] = ["Kalyan", "market_id 9"]
    fake = FakeCeda()
    Downloader(cfg, client(fake), cache, today=date(2026, 9, 27)).run()
    data_calls = [b for p, b in fake.calls if p in ("/agmarknet/prices", "/agmarknet/quantities")]
    assert len(data_calls) == 2 * 3 and all(b["district_id"] == [517] for b in data_calls)

    df, _ = prepare(cfg, ceda_dir=cache)
    kalyan = df[df["market"] == "Kalyan"]
    assert len(kalyan) == 366 * 3 and (kalyan["district"] == "Thane").all()
    assert len(df[df["market"] == "Pune"]) == 366 * 3  # no duplicate Pune rows

    fake3 = FakeCeda()
    Downloader(cfg, client(fake3), cache, today=date(2026, 9, 27)).run()
    assert fake3.calls == []


def test_open_window_refresh_is_age_based(tmp_path):
    cfg = make_cfg(start="2026-09-20", end=None)
    cfg["ceda"]["refresh_open_chunk_hours"] = 24
    Downloader(cfg, client(FakeCeda()), tmp_path, today=date(2026, 9, 27)).run()
    fake = FakeCeda()
    Downloader(cfg, client(fake), tmp_path, today=date(2026, 9, 27)).run()
    assert fake.calls == []  # fetched minutes ago: not refetched

    for f in (tmp_path / "price").glob("*.json"):  # pretend it was fetched two days ago
        payload = json.loads(f.read_text())
        payload["fetched_at"] = "2026-09-25T00:00:00+00:00"
        f.write_text(json.dumps(payload))
    fake = FakeCeda()
    Downloader(cfg, client(fake), tmp_path, today=date(2026, 9, 27)).run()
    assert sum(p == "/agmarknet/prices" for p, _ in fake.calls) == 3
    assert len(list((tmp_path / "price").glob("*.json"))) == 3  # stale files replaced, not duplicated


def test_market_names_fetched_once_per_district_and_failure_is_not_fatal(tmp_path):
    cfg = district_cfg(tmp_path)
    cfg["ceda"].update(districts=["Pune", "Thane"], fetch_market_names=True)
    fake = FakeCeda()
    Downloader(cfg, client(fake), tmp_path / "ceda", today=date(2026, 9, 27)).run()
    names = [b for p, b in fake.calls if p == "/agmarknet/markets"]
    assert sorted(b["district_id"] for b in names) == [517, 521]
    assert all("market_id" not in b for p, b in fake.calls if p != "/agmarknet/markets")
    df, _ = prepare(cfg, ceda_dir=tmp_path / "ceda")
    assert "Kalyan" in set(df["market"])  # named by the API list, no alias needed

    (tmp_path / "b").mkdir()
    cfg2 = district_cfg(tmp_path / "b")
    cfg2["ceda"]["fetch_market_names"] = True
    d = Downloader(cfg2, client(FakeCeda(hang_on_market_filter=True)), tmp_path / "b" / "ceda",
                   today=date(2026, 9, 27))
    d.run()  # /markets 504 -> logged, prices still downloaded
    assert any("market names for Pune not fetched" in line for line in d.log)
