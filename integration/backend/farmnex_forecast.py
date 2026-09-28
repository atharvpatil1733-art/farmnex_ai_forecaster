"""FarmNex backend <-> forecaster connector. Copy this ONE file into your FastAPI backend.

    # in your backend's main.py
    from farmnex_forecast import router as forecast_router
    app.include_router(forecast_router)

Your Flutter app then calls YOUR backend (e.g. https://api.farmnex.app/forecast/price?...),
and this file forwards the call to the forecaster service with the secret key, checks that the
user is logged in to Supabase, and saves a copy of each answer in the Supabase table
`forecast_logs` (see integration/supabase/001_forecast_logs.sql).

Settings (environment variables of your backend, e.g. in its .env file):
    FORECASTER_URL            where the forecaster runs, e.g. https://farmnex-forecaster.onrender.com
    FORECASTER_API_KEY        same value as FARMNEX_FORECASTER_API_KEY on the forecaster
    SUPABASE_URL              https://<project>.supabase.co   (unset = no login check, no logging)
    SUPABASE_ANON_KEY         Supabase "anon public" or "publishable" key (checks the user's login)
    SUPABASE_SERVICE_ROLE_KEY Supabase "service_role" or "secret" key (saves logs; keep it secret!)

Needs only `httpx` (FastAPI already depends on it in most setups: `pip install httpx`).
"""
from __future__ import annotations

import logging
import os
import time
from datetime import date

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

log = logging.getLogger("farmnex_forecast")

FORECASTER_URL = os.environ.get("FORECASTER_URL", "http://localhost:8000").rstrip("/")
FORECASTER_API_KEY = os.environ.get("FORECASTER_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

router = APIRouter(prefix="/forecast", tags=["forecast"])

# Free hosting plans sleep when idle and take ~1 minute to wake up, hence the long read timeout.
# A fresh client per call works with any server setup.
TIMEOUT = httpx.Timeout(90.0, connect=10.0)
_meta_cache: dict = {"at": 0.0, "data": None}
META_CACHE_SECONDS = 600


# ----------------------------------------------------------------------------- login check
async def current_user_id(authorization: str | None = Header(default=None)) -> str | None:
    """Return the Supabase user id from the 'Authorization: Bearer <token>' header.

    If your backend already has its own login dependency, use that instead and delete this.
    With SUPABASE_URL unset (local testing) nobody needs to log in and this returns None.
    """
    if not SUPABASE_URL:
        return None
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "log in first (missing Supabase token)")
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as http:
            r = await http.get(f"{SUPABASE_URL}/auth/v1/user",
                               headers={"Authorization": authorization, "apikey": SUPABASE_ANON_KEY})
    except httpx.HTTPError:
        raise HTTPException(503, "login check is temporarily unavailable, try again soon")
    if r.status_code != 200:
        raise HTTPException(401, "your login has expired, please log in again")
    return r.json()["id"]


# ----------------------------------------------------------------------------- helpers
async def _call(method: str, path: str, params: dict | None = None, body: dict | None = None) -> dict:
    """Forward one call to the forecaster and return its JSON, passing its errors through."""
    params = {k: v for k, v in (params or {}).items() if v is not None}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as http:
            r = await http.request(method, f"{FORECASTER_URL}{path}", params=params, json=body,
                                   headers={"X-API-Key": FORECASTER_API_KEY})
    except httpx.HTTPError as exc:
        log.error("forecaster unreachable: %s", exc)
        raise HTTPException(503, "price forecasts are temporarily unavailable, try again soon")
    if r.status_code == 401:
        log.error("forecaster refused our key: check FORECASTER_API_KEY")
        raise HTTPException(503, "price forecasts are temporarily unavailable")
    if r.status_code >= 400:
        detail = r.json().get("detail", r.text) if r.headers.get("content-type", "").startswith(
            "application/json") else r.text
        raise HTTPException(r.status_code, detail)
    return r.json()


def _service_headers() -> dict:
    """Newer Supabase secret keys ("sb_secret_...") go in the apikey header only; the older
    JWT-style service_role key goes in both apikey and Authorization."""
    key = SUPABASE_SERVICE_ROLE_KEY
    return {"apikey": key} if key.startswith("sb_") else {"apikey": key, "Authorization": f"Bearer {key}"}


async def _save_log(user_id: str | None, kind: str, request: dict, response: dict) -> None:
    """Save the answer to Supabase table forecast_logs. Never breaks the user's request."""
    if not (SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY):
        return
    row = {"user_id": user_id, "kind": kind, "request": request, "response": response,
           "data_as_of": response.get("as_of") or response.get("forecast_origin")}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as http:
            r = await http.post(f"{SUPABASE_URL}/rest/v1/forecast_logs", json=row,
                                headers=_service_headers() | {"Prefer": "return=minimal"})
        if r.status_code >= 300:
            log.warning("could not save forecast log: %s %s", r.status_code, r.text[:200])
    except httpx.HTTPError as exc:
        log.warning("could not save forecast log: %s", exc)


# ----------------------------------------------------------------------------- routes
@router.get("/meta")
async def meta():
    """Dropdown lists for the app (markets, crops, districts), data date and the CEDA credit.
    Public (no login) and cached for 10 minutes."""
    if _meta_cache["data"] is None or time.time() - _meta_cache["at"] > META_CACHE_SECONDS:
        _meta_cache.update(data=await _call("GET", "/meta"), at=time.time())
    return _meta_cache["data"]


@router.get("/price")
async def price(market: str, crop: str, days: int = Query(3, ge=1, le=3),
                user_id: str | None = Depends(current_user_id)):
    """Price forecast (low / expected / high, Rs per quintal) for the next 1-3 days."""
    req = {"market": market, "crop": crop, "days": days}
    res = await _call("GET", "/forecast/price", req)
    await _save_log(user_id, "price", req, res)
    return res


@router.get("/demand")
async def demand(district: str, on: date | None = Query(None, alias="date"),
                 user_id: str | None = Depends(current_user_id)):
    """HIGH / NORMAL / LOW demand signal per crop for a district."""
    req = {"district": district, "date": on.isoformat() if on else None}
    res = await _call("GET", "/forecast/demand", req)
    await _save_log(user_id, "demand", req, res)
    return res


class SellRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    crop: str
    qty_quintal: float = Field(gt=0)
    radius_km: float | None = Field(default=None, gt=0)


@router.post("/sell-options")
async def sell_options(body: SellRequest, user_id: str | None = Depends(current_user_id)):
    """Best market and day to sell, after transport cost."""
    req = body.model_dump()
    res = await _call("POST", "/forecast/sell-options", body=req)
    await _save_log(user_id, "sell_options", req, res)
    return res


@router.get("/crops")
async def crops(district: str, sowing_month: int = Query(ge=1, le=12), k: int = Query(5, ge=1, le=20),
                user_id: str | None = Depends(current_user_id)):
    """Which crop to sow this month, ranked by expected price at harvest."""
    req = {"district": district, "sowing_month": sowing_month, "k": k}
    res = await _call("GET", "/forecast/crops", req)
    await _save_log(user_id, "crops", req, res)
    return res


@router.get("/health")
async def health():
    """Is the forecaster up, and how fresh is its data?"""
    return await _call("GET", "/health")
