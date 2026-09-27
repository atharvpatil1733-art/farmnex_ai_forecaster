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


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok" and r.json()["data_as_of"]


def test_meta(client):
    j = client.get("/meta").json()
    assert {m["market"] for m in j["markets"]} == set(CFG["markets"])
    assert j["crops"] == list(CFG["crops"]) and "Pune" in j["districts"]
    assert j["attribution"] == ATTR and j["data_as_of"]
    assert "PROXY" in j["demand_note"]
    assert len(j["pairs"]) == len(CFG["markets"]) * len(CFG["crops"])


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
def test_markets_without_real_data_do_not_crash(client, market):
    for crop in CFG["crops"]:
        r = client.get("/forecast/price", params={"market": market, "crop": crop})
        assert r.status_code == 200, r.text
        j = r.json()
        if j["data_source"] == "synthetic":
            assert any("SYNTHETIC" in x for x in j["reason"])


def test_thane_district_all_synthetic(client):
    assert client.get("/forecast/demand", params={"district": "Thane"}).status_code == 200
    j = client.get("/forecast/crops", params={"district": "Thane", "sowing_month": 10}).json()
    assert all(i["data_source"] == "synthetic" for i in j["items"])
    body = {"lat": 19.08, "lon": 73.01, "crop": "Tomato", "qty_quintal": 5, "radius_km": 30}
    j = client.post("/forecast/sell-options", json=body).json()
    assert j["best"]["market"] == "Vashi" and j["best"]["data_source"] == "synthetic"


def test_bad_inputs(client):
    assert client.get("/forecast/price", params={"market": "Nowhere", "crop": "Onion"}).status_code == 404
    assert client.get("/forecast/price", params={"market": "Pune", "crop": "Onion", "days": 9}).status_code == 422
    assert client.get("/forecast/demand", params={"district": "Pune", "date": "2020-01-01"}).status_code == 404
    body = {"lat": 28.6, "lon": 77.2, "crop": "Onion", "qty_quintal": 5, "radius_km": 50}  # Delhi
    j = client.post("/forecast/sell-options", json=body).json()
    assert j["best"] is None and "increase radius_km" in j["message"]
