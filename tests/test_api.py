"""One TestClient test per endpoint, plus markets with no real data and bad input."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from forecaster.data import load_config

CFG = load_config()
ATTR = CFG["ceda"]["attribution"]


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def synth_pair(client):
    """A (market, crop, lat, lon, district) with synthetic prices only, read from the data
    (which pairs have real data changes as districts are added)."""
    src = client.app.state.svc.sources
    rows = src[src["price_source"] == "synthetic"]
    if rows.empty:
        pytest.skip("every market x crop has real prices")
    m, c = rows.iloc[0][["market", "commodity"]]
    ref = client.app.state.svc.ref["markets"].set_index("market").loc[m]
    return m, c, float(ref["lat"]), float(ref["lon"]), ref["district"]


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok" and r.json()["data_as_of"]


def test_meta(client, synth_pair):
    j = client.get("/meta").json()
    assert j["synthetic_shown"] is False
    assert {m["market"] for m in j["markets"]} <= set(CFG["markets"])
    assert (synth_pair[0], synth_pair[1]) not in {(p["market"], p["crop"]) for p in j["pairs"]}
    assert all(p["price_source"] == "real" for p in j["pairs"])
    assert set(j["crops"]) <= set(CFG["crops"]) and "Pune" in j["districts"]
    assert j["attribution"] == ATTR and j["data_as_of"]
    d = j["attribution_details"]
    assert d["logo_placement"] == "bottom right" and d["terms_url"].startswith("https://")
    assert any("endorse" in r for r in d["rules"])
    assert "PROXY" in j["demand_note"]


def test_forecast_price(client):
    j = client.get("/forecast/price", params={"market": "Pune", "crop": "Onion", "days": 3}).json()
    assert [d["horizon"] for d in j["days"]] == [1, 2, 3]
    for d in j["days"]:
        assert 0 < d["p10"] <= d["p50"] <= d["p90"]
    assert j["data_source"] == "real" and j["as_of"] and len(j["reason"]) >= 3
    assert j["attribution"] == ATTR


def test_forecast_demand(client):
    meta = client.get("/meta").json()
    j = client.get("/forecast/demand", params={"district": "Pune"}).json()
    assert {i["crop"] for i in j["items"]} == set(CFG["crops"])
    assert all(i["signal"] in ("HIGH", "NORMAL", "LOW") and i["reason"] and i["as_of"] for i in j["items"])
    assert "PROXY" in j["note"] and j["attribution"] == ATTR
    assert j["date"] > meta["data_as_of"]


def test_sell_options(client):
    body = {"lat": 18.52, "lon": 73.85, "crop": "Onion", "qty_quintal": 20, "radius_km": 60}
    j = client.post("/forecast/sell-options", json=body).json()
    best = j["best"]
    assert best is not None and best["distance_km"] <= 60
    assert best["floor_price"] <= best["asking_price"]
    assert best["data_source"] == "real" and best["reason"] and best["as_of"]
    assert best["best_day"] not in best["likely_closed_days"]
    assert best["net_price_per_quintal"] == pytest.approx(best["asking_price"] - best["transport_cost_per_quintal"], abs=0.2)
    assert j["attribution"] == ATTR


def test_forecast_crops(client):
    j = client.get("/forecast/crops", params={"district": "Pune", "sowing_month": 6, "k": 5}).json()
    items = j["items"]
    assert [i["rank"] for i in items] == list(range(1, len(items) + 1))
    assert all(i["reason"] and i["data_source"] in ("real", "synthetic") and i["as_of"] for i in items)
    assert j["attribution"] == ATTR


@pytest.mark.parametrize("market", ["Vashi", "Kalyan", "Shirur", "Baramati"])
def test_markets_without_real_data_are_hidden_not_crashing(client, market):
    for crop in CFG["crops"]:
        r = client.get("/forecast/price", params={"market": market, "crop": crop})
        assert r.status_code in (200, 404), r.text
        if r.status_code == 404:
            assert "synthetic data is hidden" in r.json()["detail"]
        else:
            assert r.json()["data_source"] == "real"


def test_hidden_synthetic_never_reaches_answers(client, synth_pair):
    market, crop, lat, lon, district = synth_pair
    r = client.get("/forecast/price", params={"market": market, "crop": crop})
    assert r.status_code == 404 and "synthetic data is hidden" in r.json()["detail"]
    body = {"lat": lat, "lon": lon, "crop": crop, "qty_quintal": 5, "radius_km": 1}
    j = client.post("/forecast/sell-options", json=body).json()
    assert j["best"] is None  # the only market in range has synthetic data only
    j = client.post("/forecast/sell-options", json={**body, "radius_km": 80}).json()
    assert all(o["data_source"] == "real" for o in j["options"])
    for d in client.get("/meta").json()["districts"]:
        for i in client.get("/forecast/demand", params={"district": d}).json()["items"]:
            assert all(p["price_source"] == "real" for p in i["pairs"])
        for i in client.get("/forecast/crops", params={"district": d, "sowing_month": 7}).json()["items"]:
            assert i["data_source"] == "real"


@pytest.fixture(scope="module")
def shown():
    """Service with api.show_synthetic: true (demo mode)."""
    import copy
    from forecaster.service import ForecastService
    cfg = copy.deepcopy(CFG)
    cfg["api"]["show_synthetic"] = True
    return ForecastService(cfg)


@pytest.mark.parametrize("market", ["Vashi", "Kalyan", "Shirur", "Baramati"])
def test_synthetic_mode_markets_do_not_crash(shown, market):
    for crop in CFG["crops"]:
        j = shown.price(market, crop)
        if j["data_source"] == "synthetic":
            assert any("SYNTHETIC" in x for x in j["reason"])


def test_synthetic_mode_shows_synthetic_pairs(shown, synth_pair):
    market, crop, lat, lon, district = synth_pair
    assert shown.price(market, crop)["data_source"] == "synthetic"
    j = shown.sell_options(lat, lon, crop, 5, 1)
    assert j["best"]["market"] == market and j["best"]["data_source"] == "synthetic"
    pairs = [p for i in shown.demand(district)["items"] for p in i["pairs"]]
    assert any(p["market"] == market and p["price_source"] == "synthetic" for p in pairs)
    assert len(shown.meta_info()["pairs"]) == len(CFG["markets"]) * len(CFG["crops"])


def test_sell_options_says_when_market_size_is_unknown(client):
    """Markets with `has_arrivals: false` (placeholder quantity reports) can't be checked for depth."""
    no_arr = [m for m, spec in CFG["markets"].items() if spec.get("has_arrivals") is False]
    if not no_arr:
        pytest.skip("no market configured with has_arrivals: false")
    ref = client.app.state.svc.ref["markets"].set_index("market").loc[no_arr[0]]
    for crop in CFG["crops"]:
        body = {"lat": float(ref["lat"]), "lon": float(ref["lon"]), "crop": crop, "qty_quintal": 20, "radius_km": 1}
        j = client.post("/forecast/sell-options", json=body).json()
        if j["best"] and j["best"]["data_source"] == "real":
            assert j["best"]["typical_daily_arrivals_quintal"] is None
            assert any("no reliable arrivals data" in r for r in j["best"]["reason"])
            return
    pytest.skip("no real pair for that market")


def test_cors_allows_local_dev_and_blocks_unknown_origins(client):
    ok = client.options("/meta", headers={"Origin": "http://localhost:5173",
                                          "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.options("/meta", headers={"Origin": "https://evil.example.com",
                                           "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in bad.headers


def test_cors_env_origins(monkeypatch):
    from app.main import cors_origins
    monkeypatch.setenv("FARMNEX_CORS_ORIGINS", "https://app.farmnex.in, https://staging.farmnex.in")
    assert cors_origins(CFG) == ["https://app.farmnex.in", "https://staging.farmnex.in"]


def test_bad_inputs(client):
    assert client.get("/forecast/price", params={"market": "Nowhere", "crop": "Onion"}).status_code == 404
    assert client.get("/forecast/price", params={"market": "Pune", "crop": "Onion", "days": 9}).status_code == 422
    assert client.get("/forecast/demand", params={"district": "Pune", "date": "2020-01-01"}).status_code == 404
    body = {"lat": 28.6, "lon": 77.2, "crop": "Onion", "qty_quintal": 5, "radius_km": 50}  # Delhi
    j = client.post("/forecast/sell-options", json=body).json()
    assert j["best"] is None and "increase radius_km" in j["message"]


def test_sell_options_demotes_thin_markets(client):
    """A load far bigger than a market's normal daily arrivals must not win on price alone."""
    body = {"lat": 18.83, "lon": 74.37, "crop": "Tomato", "qty_quintal": 50, "radius_km": 80}
    j = client.post("/forecast/sell-options", json=body).json()
    opts = j["options"]
    thin = [o for o in opts if o["thin_market"]]
    for o in thin:
        assert o["typical_daily_arrivals_quintal"] is not None and o["typical_daily_arrivals_quintal"] * 0.5 < 50
        assert any("normally receives" in r for r in o["reason"])
    if j["best"] and any(not o["thin_market"] and o["data_source"] == "real" for o in opts):
        assert not j["best"]["thin_market"]


def test_api_key_protects_everything_but_health(client, monkeypatch):
    monkeypatch.setenv("FARMNEX_FORECASTER_API_KEY", "s3cret")
    assert client.get("/health").status_code == 200
    assert client.get("/meta").status_code == 401
    assert client.get("/meta", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get("/meta", headers={"X-API-Key": "s3cret"}).status_code == 200
    r = client.post("/forecast/sell-options", json={"lat": 18.5, "lon": 73.9, "crop": "Onion", "qty_quintal": 5})
    assert r.status_code == 401
    monkeypatch.delenv("FARMNEX_FORECASTER_API_KEY")
    assert client.get("/meta").status_code == 200  # no key configured: open (local dev)
