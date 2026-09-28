"""Pydantic response/request models for every API endpoint."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

DataSource = Literal["real", "synthetic"]


class Health(BaseModel):
    status: Literal["ok"]
    model_version: str
    data_as_of: date


class PairSource(BaseModel):
    market: str
    crop: str
    price_source: DataSource
    arrivals_source: DataSource
    last_real_price_date: date | None = None


class MarketInfo(BaseModel):
    market: str
    district: str
    lat: float
    lon: float
    likely_closed_weekdays: list[str]
    crops: list[str] = Field(description="crops this API answers for at this market")


class Attribution(BaseModel):
    text: str
    terms_url: str
    logo_placement: str
    rules: list[str]


class Meta(BaseModel):
    markets: list[MarketInfo]
    crops: list[str]
    districts: list[str]
    data_as_of: date
    model_version: str
    pairs: list[PairSource]
    demand_note: str
    synthetic_shown: bool = Field(description="false: pairs without real prices are hidden everywhere")
    attribution: str
    attribution_details: Attribution


class PriceDay(BaseModel):
    date: date
    horizon: int
    p10: float = Field(description="Rs/quintal")
    p50: float = Field(description="Rs/quintal")
    p90: float = Field(description="Rs/quintal")
    arrivals_p50_tonnes: float
    likely_closed: bool


class PriceForecast(BaseModel):
    market: str
    crop: str
    district: str
    forecast_origin: date = Field(description="Day the forecast is made from (data as_of); days are +1..+n after it")
    as_of: date = Field(description="Last date with real price data behind this answer")
    data_source: DataSource
    arrivals_data_source: DataSource
    last_price: float | None
    last_price_date: date | None
    days: list[PriceDay]
    reason: list[str]
    model_version: str
    attribution: str


class DemandItem(BaseModel):
    crop: str
    signal: Literal["HIGH", "NORMAL", "LOW"]
    price_change_pct: float
    arrivals_change_pct: float
    data_source: DataSource
    as_of: date
    pairs: list[PairSource]
    reason: list[str]


class DemandResponse(BaseModel):
    district: str
    date: date
    forecast_origin: date
    items: list[DemandItem]
    note: str
    attribution: str


class SellRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    crop: str
    qty_quintal: float = Field(gt=0)
    radius_km: float | None = Field(default=None, gt=0)


class SellOption(BaseModel):
    market: str
    district: str
    distance_km: float
    best_day: date
    asking_price: float = Field(description="p50, Rs/quintal")
    floor_price: float = Field(description="p10, Rs/quintal")
    transport_cost_per_quintal: float
    net_price_per_quintal: float = Field(description="asking price minus transport")
    net_total: float = Field(description="net price x qty_quintal, Rs")
    likely_closed_days: list[date]
    typical_daily_arrivals_quintal: float | None = Field(
        default=None, description="median real daily arrivals at this market (last 90 days); None if unknown")
    thin_market: bool = Field(default=False, description="load is large vs what this market normally receives")
    data_source: DataSource
    as_of: date
    reason: list[str]


class SellResponse(BaseModel):
    crop: str
    qty_quintal: float
    radius_km: float
    forecast_origin: date
    best: SellOption | None
    options: list[SellOption]
    message: str
    data_source: DataSource | None = Field(description="data source of the best option")
    as_of: date | None = Field(description="last real data date behind the best option")
    reason: list[str] = Field(description="why the best option was chosen")
    attribution: str


class CropRecommendation(BaseModel):
    rank: int
    crop: str
    sowing_month: int
    harvest_month: str = Field(description="YYYY-MM")
    expected_price: float = Field(description="Rs/quintal at harvest month")
    method: Literal["sarimax", "same_month_average", "overall_average"]
    in_sowing_window: bool
    data_source: DataSource
    as_of: date
    reason: list[str]


class CropsResponse(BaseModel):
    district: str
    sowing_month: int
    forecast_origin: date
    items: list[CropRecommendation]
    note: str
    attribution: str
