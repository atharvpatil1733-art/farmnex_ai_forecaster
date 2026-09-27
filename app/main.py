"""FastAPI app: `uvicorn app.main:app`. Loads artifacts once at startup; CORS on for Flutter web."""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from forecaster.data import load_config
from forecaster.schemas import (CropsResponse, DemandResponse, Health, Meta, PriceForecast,
                                SellRequest, SellResponse)
from forecaster.service import ForecastService, NotFound

CFG = load_config()
MAX_H = max(CFG["modelling"]["horizons"])
DEMAND_NOTE = " ".join(CFG["api"]["demand_note"].split())


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.svc = ForecastService(CFG)
    yield


app = FastAPI(
    title="FarmNex AI Demand Forecast",
    version="0.1.0",
    description=(
        "What to grow, where and when to sell, and at what price, for Pune-district mandis. "
        "Prices are Rs/quintal, arrivals tonnes. Forecasts start from the last date with data "
        f"(`forecast_origin`), not today. {DEMAND_NOTE} "
        f"{CFG['ceda']['attribution']}. Non-commercial use; show the CEDA logo and this credit."
    ),
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=CFG["api"]["cors_origins"],
                   allow_methods=["GET", "POST"], allow_headers=["*"])


@app.exception_handler(NotFound)
async def not_found(_: Request, exc: NotFound):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


def svc(request: Request) -> ForecastService:
    return request.app.state.svc


@app.get("/health", response_model=Health)
def health(request: Request):
    return svc(request).health()


@app.get("/meta", response_model=Meta)
def meta(request: Request):
    return svc(request).meta_info()


@app.get("/forecast/price", response_model=PriceForecast)
def forecast_price(request: Request, market: str, crop: str, days: int = Query(MAX_H, ge=1, le=MAX_H)):
    return svc(request).price(market, crop, days)


@app.get("/forecast/demand", response_model=DemandResponse,
         description=f"HIGH/NORMAL/LOW per crop for a district. {DEMAND_NOTE}")
def forecast_demand(request: Request, district: str, date: date | None = None):
    return svc(request).demand(district, date)


@app.post("/forecast/sell-options", response_model=SellResponse)
def sell_options(request: Request, body: SellRequest):
    return svc(request).sell_options(body.lat, body.lon, body.crop, body.qty_quintal, body.radius_km)


@app.get("/forecast/crops", response_model=CropsResponse)
def forecast_crops(request: Request, district: str, sowing_month: int = Query(ge=1, le=12),
                   k: int = Query(5, ge=1, le=20)):
    return svc(request).best_crops(district, sowing_month, k)
