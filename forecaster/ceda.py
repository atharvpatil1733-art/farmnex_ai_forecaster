"""Download real mandi prices and arrivals from the CEDA (Ashoka University) Agmarknet API.

    python -m forecaster.ceda            # fetch what is missing, then: python -m forecaster.data
    python -m forecaster.ceda --dry-run  # print the request plan, no network

Why the API and not website exports: website downloads are capped (~1000 rows) and silently keep
only the newest dates. The API returns full history, in any date window.

API facts (checked against live behaviour by other projects; the published OpenAPI schema is
wrong about response shapes, so trust this module, not the docs):
  * Base URL https://api.ceda.ashoka.edu.in/v1, auth header `Authorization: Bearer <key>`.
  * Every response is wrapped: {"output": {"type": "success", "message": ..., "data": [...]}}.
  * GET  /agmarknet/commodities  -> [{commodity_id, commodity_name}]
  * GET  /agmarknet/geographies  -> [{census_state_id, census_state_name,
                                      census_district_id, census_district_name}]
  * POST /agmarknet/markets      {commodity_id, state_id, district_id, indicator}
                                  -> [{market_id, market_name, ...}]
  * POST /agmarknet/prices       {commodity_id, state_id, district_id: [..], market_id: [..],
                                  from_date, to_date} -> daily rows
                                  [{date, commodity_id, census_state_id, census_district_id,
                                    market_id, min_price, max_price, modal_price}]
  * POST /agmarknet/quantities   same body -> daily arrivals. NOT verified yet: if it fails,
                                  quantities are skipped and reported, prices still download.
  * Rate limit: 40 requests per rolling hour (RateLimit-Policy: 40;w=3600). 429 carries
    Retry-After. Multi-year windows are accepted, so we fetch in big chunks.

Every response is cached as JSON under config `paths.ceda_cache_dir`; reruns skip cached
chunks, so a run stopped by the hourly budget just resumes next time.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

from forecaster.data import ROOT, load_config

INDICATORS = {"price": "/agmarknet/prices", "quantity": "/agmarknet/quantities"}


class CedaError(RuntimeError):
    """Non-auth API failure."""


class CedaAuthError(CedaError):
    """Missing or rejected CEDA_API_KEY."""


class CedaRateLimitError(CedaError):
    def __init__(self, message: str, retry_after_seconds: int | None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class BudgetExhausted(CedaError):
    """This run used its request budget; rerun later and cached chunks are skipped."""


def load_api_key() -> str:
    """CEDA_API_KEY from the environment, else from a .env file at the repo root."""
    key = os.environ.get("CEDA_API_KEY")
    if not key:
        try:
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env")
            key = os.environ.get("CEDA_API_KEY")
        except ImportError:
            pass
    if not key:
        raise CedaAuthError("CEDA_API_KEY is not set. Copy .env.example to .env and add your free "
                            "key from https://api.ceda.ashoka.edu.in")
    return key


class CedaClient:
    """Thin client: auth, envelope unwrap, polite pacing, a hard per-run request budget."""

    def __init__(self, api_key: str, base_url: str, max_requests: int = 36,
                 min_interval: float = 1.0, transport: httpx.BaseTransport | None = None,
                 max_retries: int = 3):
        self._key = api_key
        self._http = httpx.Client(base_url=base_url, timeout=120.0, transport=transport,
                                  headers={"Authorization": f"Bearer {api_key}"})
        self.max_requests, self.min_interval, self.max_retries = max_requests, min_interval, max_retries
        self.requests_made = 0
        self._last = 0.0

    def _scrub(self, text: str) -> str:
        return text.replace(self._key, "***") if self._key else text

    def request(self, method: str, path: str, body: dict | None = None) -> list[dict]:
        for attempt in range(1, self.max_retries + 1):
            if self.requests_made >= self.max_requests:
                raise BudgetExhausted(f"used this run's budget of {self.max_requests} requests")
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self.requests_made += 1
            try:
                resp = self._http.request(method, path, json=body)
            except httpx.HTTPError as exc:
                self._last = time.monotonic()
                if attempt == self.max_retries:
                    raise CedaError(self._scrub(f"{path}: network error {type(exc).__name__}")) from None
                time.sleep(2.0 * attempt)
                continue
            self._last = time.monotonic()
            if resp.status_code in (401, 403):
                raise CedaAuthError(f"{path}: HTTP {resp.status_code}, check CEDA_API_KEY")
            if resp.status_code == 429:
                ra = resp.headers.get("Retry-After", "")
                raise CedaRateLimitError(
                    f"{path}: rate limited (Retry-After={ra or '?'}s, "
                    f"policy={resp.headers.get('RateLimit-Policy')})",
                    int(ra) if ra.isdigit() else None)
            if resp.status_code >= 500 and attempt < self.max_retries:
                time.sleep(2.0 * attempt)
                continue
            if resp.status_code >= 400:
                raise CedaError(self._scrub(f"{path}: HTTP {resp.status_code}: {resp.text[:300]}"))
            output = resp.json().get("output", {})
            if output.get("type") != "success":
                raise CedaError(self._scrub(f"{path}: {output.get('message', 'unknown error')}"))
            return output.get("data") or []
        raise CedaError(f"{path}: failed after {self.max_retries} attempts")


# ------------------------------------------------------------------------------ planning
def date_chunks(start: date, end: date, years: int) -> list[tuple[date, date]]:
    """Calendar-year aligned windows of `years` years covering start..end (inclusive)."""
    out, y = [], start.year
    while y <= end.year:
        a = max(start, date(y, 1, 1))
        b = min(end, date(y + years - 1, 12, 31))
        out.append((a, b))
        y += years
    return out


def split_chunk(a: date, b: date) -> list[tuple[date, date]]:
    mid = a + (b - a) // 2
    return [(a, mid), (mid + timedelta(days=1), b)]


def _unique(items: list[dict], key: str, name: str, value: str, kind: str) -> int:
    hits = {r[value] for r in items if str(r.get(key, "")).strip().lower() == name.strip().lower()}
    if len(hits) != 1:
        raise CedaError(f"could not resolve {kind} {name!r} uniquely (found {sorted(hits)}); "
                        "fix the name in config.yaml")
    return hits.pop()


@dataclass
class Plan:
    state_id: int
    district_ids: dict[str, int]
    commodity_ids: dict[str, int]
    chunks: list[tuple[date, date]]


class Downloader:
    def __init__(self, cfg: dict, client: CedaClient | None, cache_dir: Path, today: date | None = None):
        self.cfg, self.c, self.cache = cfg, client, Path(cache_dir)
        self.ccfg = cfg["ceda"]
        self.today = today or date.today()
        self.log: list[str] = []

    # --- cache helpers
    def _read(self, path: Path):
        return json.loads(path.read_text()) if path.exists() else None

    def _write(self, path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload))
        tmp.replace(path)

    def _cached_call(self, path: Path, method: str, endpoint: str, body: dict | None = None):
        hit = self._read(path)
        if hit is not None:
            return hit
        data = self.c.request(method, endpoint, body)
        self._write(path, data)
        return data

    # --- steps
    def plan(self) -> Plan:
        ref = self.cache / "ref"
        geos = self._cached_call(ref / "geographies.json", "GET", "/agmarknet/geographies")
        comms = self._cached_call(ref / "commodities.json", "GET", "/agmarknet/commodities")
        state_id = _unique(geos, "census_state_name", self.ccfg["state"], "census_state_id", "state")
        in_state = [g for g in geos if g["census_state_id"] == state_id]
        districts = {d: _unique(in_state, "census_district_name", d, "census_district_id", "district")
                     for d in self.ccfg["districts"]}
        crops = {c: _unique(comms, "commodity_name", spec.get("ceda_name", c), "commodity_id", "commodity")
                 for c, spec in self.cfg["crops"].items()}
        start = date.fromisoformat(str(self.ccfg["start_date"]))
        end = date.fromisoformat(str(self.ccfg["end_date"])) if self.ccfg.get("end_date") else self.today
        return Plan(state_id, districts, crops, date_chunks(start, end, int(self.ccfg["chunk_years"])))

    def markets(self, plan: Plan, crop: str, indicator: str) -> list[dict]:
        out = []
        for dname, did in plan.district_ids.items():
            path = self.cache / "ref" / f"markets_{crop}_{dname}_{indicator}.json"
            body = {"commodity_id": plan.commodity_ids[crop], "state_id": plan.state_id,
                    "district_id": did, "indicator": indicator}
            try:
                rows = self._cached_call(path, "POST", "/agmarknet/markets", body)
            except CedaError as exc:
                if indicator == "price" or isinstance(exc, (CedaAuthError, BudgetExhausted, CedaRateLimitError)):
                    raise
                self.log.append(f"markets list for {crop}/{dname}/quantity failed ({exc}); "
                                "using the price market list")
                rows = self.markets(plan, crop, "price")
            out += [dict(r, district_name=dname, census_district_id=did) for r in rows]
        return out

    def chunk_path(self, indicator: str, crop: str, a: date, b: date) -> Path:
        return self.cache / indicator / f"{crop}_{a.isoformat()}_{b.isoformat()}.json"

    def fetch_chunk(self, plan: Plan, indicator: str, crop: str, market_ids: list[int],
                    a: date, b: date) -> int:
        """Fetch one window (splitting it if it looks truncated). Returns rows written."""
        path = self.chunk_path(indicator, crop, a, b)
        is_open = b >= self.today - timedelta(days=1)
        if path.exists() and not (is_open and self.ccfg.get("refresh_open_chunk", True)):
            return len(self._read(path)["records"])
        body = {"commodity_id": plan.commodity_ids[crop], "state_id": plan.state_id,
                "district_id": list(plan.district_ids.values()), "market_id": market_ids,
                "from_date": a.isoformat(), "to_date": b.isoformat()}
        rows = self.c.request("POST", INDICATORS[indicator], body)
        caps = set(self.ccfg.get("suspicious_row_counts", []))
        if len(rows) in caps and (b - a).days + 1 > 2 * int(self.ccfg["min_chunk_days"]):
            self.log.append(f"{indicator}/{crop} {a}..{b}: {len(rows)} rows looks capped, splitting")
            return sum(self.fetch_chunk(plan, indicator, crop, market_ids, x, y) for x, y in split_chunk(a, b))
        if len(rows) in caps:
            self.log.append(f"WARNING {indicator}/{crop} {a}..{b}: {len(rows)} rows may be truncated")
        self._write(path, {"indicator": indicator, "crop": crop, "from_date": a.isoformat(),
                           "to_date": b.isoformat(), "request": body,
                           "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                           "records": rows})
        return len(rows)

    def run(self) -> dict:
        plan = self.plan()
        summary = {"state_id": plan.state_id, "districts": plan.district_ids,
                   "commodities": plan.commodity_ids, "chunks": [], "skipped": []}
        fatal = (CedaAuthError, BudgetExhausted, CedaRateLimitError)
        # Prices for every crop first, so a budget stop never leaves prices half-done for
        # the sake of arrivals.
        for indicator in ("price", "quantity"):
            for crop in self.cfg["crops"]:
                try:
                    mkts = self.markets(plan, crop, indicator)
                    ids = sorted({int(m["market_id"]) for m in mkts})
                    if not ids:
                        summary["skipped"].append(f"{indicator}/{crop}: no markets in configured districts")
                        continue
                    for a, b in plan.chunks:
                        n = self.fetch_chunk(plan, indicator, crop, ids, a, b)
                        summary["chunks"].append({"indicator": indicator, "crop": crop,
                                                  "from": a.isoformat(), "to": b.isoformat(), "rows": n})
                except fatal:
                    raise
                except CedaError as exc:
                    if indicator == "price":
                        raise
                    # Quantities endpoint is unverified: report it, keep the prices.
                    summary["skipped"].append(f"quantity/{crop} failed ({exc}); prices unaffected")
        summary["log"] = self.log
        self._write(self.cache / "manifest.json", summary)
        return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="print the planned windows and exit")
    args = ap.parse_args(argv)
    cfg = load_config()
    ccfg = cfg["ceda"]
    cache = ROOT / cfg["paths"]["ceda_cache_dir"]
    if args.dry_run:
        start = date.fromisoformat(str(ccfg["start_date"]))
        end = date.fromisoformat(str(ccfg["end_date"])) if ccfg.get("end_date") else date.today()
        chunks = date_chunks(start, end, int(ccfg["chunk_years"]))
        n = 2 + 2 * len(cfg["crops"]) * len(ccfg["districts"]) + 2 * len(cfg["crops"]) * len(chunks)
        print(f"{len(chunks)} windows: {[(a.isoformat(), b.isoformat()) for a, b in chunks]}")
        print(f"~{n} requests on a cold cache (budget per run: {ccfg['max_requests_per_run']}, "
              "cached files are skipped)")
        return 0
    try:
        client = CedaClient(load_api_key(), ccfg["base_url"], int(ccfg["max_requests_per_run"]),
                            float(ccfg.get("min_seconds_between_requests", 1.0)))
        summary = Downloader(cfg, client, cache).run()
    except BudgetExhausted as exc:
        print(f"Stopped early: {exc}. Everything fetched so far is cached; rerun in about an hour "
              "to continue.")
        return 2
    except CedaRateLimitError as exc:
        print(f"Stopped: {exc}. Cached chunks are kept; rerun after the wait.")
        return 2
    except CedaError as exc:
        print(f"STOP: {exc}")
        return 1
    total = sum(c["rows"] for c in summary["chunks"])
    print(f"CEDA download complete: {len(summary['chunks'])} windows, {total} rows, "
          f"{client.requests_made} requests this run.")
    for line in summary["log"] + summary["skipped"]:
        print(f"  - {line}")
    print("Next: python -m forecaster.data")
    return 0


if __name__ == "__main__":
    sys.exit(main())
