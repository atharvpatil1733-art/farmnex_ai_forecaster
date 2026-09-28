# REVIEW: farmnex_ai_forecaster end-to-end build

Everything runs end to end:
- `python -m forecaster.ceda` downloads the data: 18 API requests for Pune, then 18 more for Thane and Mumbai.
- `python -m forecaster.data` cleans it.
- `python -m forecaster.train` takes 48 s on 4 CPUs.
- `uvicorn app.main:app` serves all 6 endpoints, and each one returned 200 on a live run (`reports/sample_responses.md`).
- `python -m pytest -q` passes 56 tests.

**The data is full CEDA API history: 2012-01-01 to 2025-10-30, districts Pune, Thane and Mumbai, 72,439 rows. Vashi and Kalyan now have real prices.**

## 1. CEDA outcome

- **Diagnosis:** in the first build, two test calls showed what the API accepts.
  - A statewide call returns only state averages, with no `market_id`.
  - A call by district without `market_id` returns one row per market in about 10 s.
  - Calls that filter by `market_id`, and calls to `/agmarknet/markets`, hang until a 504.
- **Fix in `forecaster/ceda.py`:**
  - it fetches per district and never sends `market_id`;
  - it maps market ids to names using the `market_id` column in the old exports;
  - it halves a date window that times out instead of retrying it.
  - Mocked tests cover this.
- **Full download:** one run, **18 requests** out of a 36-per-run budget, 109,361 raw rows. No window was capped and no request failed. `reports/data_quality.md` says `Source: CEDA Agmarknet API cache`.
- **Quantities:** `/agmarknet/quantities` works and returns a `quantity` field, which the cleaner already recognised.
  - It is in tonnes: Pune onion on 2024-10-30 is 892.2, the same value as in the old export.
  - **Tomato now has real arrivals.**
- **CEDA lags about 11 months:** the newest data is 2025-10-30, so forecasts start from that date.
- **Every market id now has a name.** On 2026-09-28 the `/agmarknet/markets` lookup answered (it hung the day before). The downloader now asks it once per district and caches the answer. A failure is only logged, and it is never used to filter data.
  - Id 3110 is **Pune(Hadapsar)**: 4,621 rows, 2012 to 2020-05-14.
  - Ids 1454, 1456 and 2385 are Dound, Nira and Mulshi (26 rows in total).
  - None of these is modelled: Hadapsar stopped reporting in 2020, and the other three are too small. They are listed in `config.yaml`.

### Thane and Mumbai (added 2026-09-28)

- **Config:** `ceda.districts: [Pune, Thane, Mumbai]`. CEDA district ids are 517 (Thane) and 519 (Mumbai); "Mumbai Suburban" (518) was not asked for.
- **Cache fix in `forecaster/ceda.py`:** cached files did not record which districts they covered, so adding a district would have silently re-used the Pune-only files.
  - Each file now records the districts it covers.
  - Only districts that are missing get fetched, all in one request per window.
  - The open window is refreshed only when its copy is older than `refresh_open_chunk_hours` (24).
  - Mocked tests cover this.
- **Download:** one run, **18 requests**, 37,387 raw rows, no failures. Three more single requests named the markets.
- **Vashi** is the Mumbai APMC at Vashi, Navi Mumbai. CEDA files it under district Mumbai with two ids:
  - 3108 "Vashi New Mumbai" is the onion-potato market.
  - 162 "Mumbai" is the vegetable market, and has most of the tomato.
  - Both were already aliases of Vashi. They overlap on only 17 onion days.
  - Arrivals look right: a median of about 1,030 t a day of onion and 1,120 t of potato.
- **Kalyan** (CEDA 177, district Thane) has real prices from 2012 to 2025.
  - **Its quantity reports are placeholders:** 0.1–1.3 t a day, often the same number for all three crops.
  - So `markets.Kalyan.has_arrivals: false` keeps them out, and its `arrivals_tonnes` stays empty. Nothing was estimated in mandi.csv.
  - As CLAUDE.md specifies, the arrivals model uses synthetic arrivals for Kalyan (reported as `arrivals_source: synthetic`).
  - Sell-options says "no reliable arrivals data for Kalyan" rather than guessing how big the market is.
- **Other Thane markets are not modelled:** Bhivandi, Vasai, Ulhasnagar, Murbad, Palghar and Shahapur. They have old or sparse data, mostly ending 2016–17. Add them to `markets:` if you want them.
- **In the API,** `/meta` districts are now Pune and Thane. Vashi is kept in district Thane, where it is on the map.

## 2. Metrics

These are leak-free and scored on real pairs only. The test period is 2025-09-01 to 2025-10-30. The baseline is the seasonal naive (same weekday last week). MAE is in ₹/quintal for price and tonnes for arrivals.

| Target | Crop | n | MAE model | MAE baseline | MAPE model | MAPE baseline | p10–p90 coverage |
|---|---|---|---|---|---|---|---|
| price | Onion | 1326 | 108.0 | 131.8 | 9.8% | 11.9% | 81.5% |
| price | Potato | 996 | 121.0 | 148.8 | 8.3% | 10.2% | 78.2% |
| price | Tomato | 1254 | 267.9 | 360.1 | 22.7% | 30.4% | 77.6% |
| arrivals | Onion | 1239 | 96.8 | 130.0 | 37.1% | 52.4% | 75.6% |
| arrivals | Potato | 996 | 58.4 | 85.7 | 61.9% | 82.2% | 74.4% |
| arrivals | Tomato | 1155 | 17.9 | 27.8 | 33.0% | 36.2% | 79.1% |

- **Every crop beats the baseline on MAE and MAPE, at every horizon.** No crop is flagged. Per-horizon rows are in `reports/metrics.md`.
- **The p10–p90 intervals cover about 75–82% of actual values**, close to the 80% they should. On the old export data they covered only about 65%.
- **The test set now also includes Vashi and Kalyan**, so these numbers are not directly comparable with the Pune-only run:

  | Crop | Price MAE (Pune only) | Price MAE (with Vashi, Kalyan) | Price MAPE (Pune only) | Price MAPE (with Vashi, Kalyan) |
  |---|---|---|---|---|
  | Onion | 112.2 | 108.0 | 10.3% | 9.8% |
  | Potato | 126.8 | 121.0 | 8.7% | 8.3% |
  | Tomato | 242.2 | 267.9 | 18.1% | 22.7% |

  Tomato error went up. Kalyan tomato is jumpy: in the sample response the latest price is ₹1,750 against a 14-day average of ₹1,058.
- **Change from the export-only build:**

  | Crop | Price MAE before | Price MAE now |
  |---|---|---|
  | Onion | 132 | 112 |
  | Potato | 132 | 127 |
  | Tomato | 286 | 242 |

- **The SARIMAX crop model runs for every crop in Pune and Thane.**

## 3. Real vs synthetic per market x crop

Each cell is price source / arrivals source, with the number of real price days in brackets. A pair needs at least 30 real days to count as "real". 39 of 48 pairs have real prices and 36 have real arrivals.

| Market | Onion | Tomato | Potato |
|---|---|---|---|
| Pune | real / real (3723 d) | real / real (3713 d) | real / real (3757 d) |
| Pimpri | real / real (3109 d) | real / real (3607 d) | real / real (425 d) |
| Manjri | real / real (1525 d) | real / real (1626 d) | real / real (1400 d) |
| Moshi | real / real (1528 d) | real / real (1576 d) | real / real (1578 d) |
| Khadki | real / real (2825 d) | real / real (2970 d) | real / real (2381 d) |
| Khed(Chakan) | real / real (1534 d) | real / real (2714 d) | real / real (1612 d) |
| Manchar | real / real (1334 d) | real / real (551 d) | real / real (816 d) |
| Junnar | real / real (1024 d) | synth / synth (1 d) | real / real (513 d) |
| Otur | real / real (678 d) | real / real (53 d) | real / real (594 d) |
| Narayangaon | real / real (723 d) | real / real (2813 d) | real / real (565 d) |
| Alephata | real / real (1294 d) | synth / synth (0 d) | synth / synth (12 d) |
| Baramati | real / real (462 d) | synth / synth (0 d) | synth / synth (0 d) |
| Shirur | real / real (53 d) | synth / synth (0 d) | synth / synth (0 d) |
| Indapur | real / real (620 d) | synth / synth (0 d) | synth / synth (0 d) |
| Vashi | real / real (3685 d) | real / real (2353 d) | real / real (3781 d) |
| Kalyan | real / synth (2409 d) | real / synth (2326 d) | real / synth (1717 d) |

Kalyan's arrivals show as synthetic because its CEDA quantity reports are placeholders (see §1).

## 4. Assumptions and approximate values

1. **Forecasts start at 2025-10-30**, the last real date, not today. Every response has `forecast_origin`.
2. **Train window:** models train from `modelling.train_start: 2015-01-01`. 2012–2014 is downloaded but only used by the monthly SARIMAX model.
3. **Arrivals are in tonnes.** This was checked against the export (892.2 on both sides).
4. **Market coordinates are approximate.** Spot-checked against public maps:
   - Pune: 0.2 km off, then corrected to the sourced point.
   - Moshi: under 0.1 km off.
   - Khadki: about 0.8 km off.
   - Manjri: about 1.6 km from the village centre (the yard is on the highway).
   - Vashi APMC: 0.4 km off, then corrected.
   - Kalyan APMC: the yard is at Bail Bazar, Bhoiwada, Kalyan West (421301). The configured point (19.2440, 73.1300) is in Kalyan West, about 1 km from the town centre. This was checked against the address only, not pinpointed on a map.
5. **Crop calendar**, as sowing months and days from sowing to harvest:

   | Crop | Sowing months | Duration |
   |---|---|---|
   | Onion | Jun, Jul, Sep–Jan | **135 days** (was 120) |
   | Tomato | Jan, Feb, Jun, Jul, Oct, Nov | 110 days |
   | Potato | Jun, Jul, Oct, Nov | 100 days |

   These were cross-checked against published sources:
   - Onion is sown Jul–Aug (kharif), Sep–Oct (late kharif) and Nov–Jan (rabi). Bulbs mature 100–120 days after transplanting, and the nursery adds 45–60 days, so 120 days was too short.
   - Potato is sown mid-June to mid-July and Oct–Nov.

   It still needs agronomist sign-off.
6. **Festival dates (2012–2027) are approximate**; lunar festivals can be a day off.
7. **Synthetic data covers only the pairs with no real data:** 9 pairs for prices, 12 for arrivals.
   - 3 years, rescaled so its recent level matches the real crop level;
   - each synthetic pair is labelled `synthetic` in every response.
8. **LightGBM uses defaults with no tuning.** The global models train on real and synthetic rows (with an `is_synthetic` flag) and are scored on real rows only. Served models are refit on all rows.
9. **Explanations use LightGBM's built-in TreeSHAP.** Each answer shows the top 3 drivers that have real values. Missing data is not presented as a cause; if missing values mattered, the answer instead adds "few recent reports from this market, so this forecast is less certain".
10. **Demand signal:**
    - HIGH or LOW when the expected price change is over ±3% and goes the opposite way to the arrivals change;
    - otherwise NORMAL;
    - labelled a PROXY in the response.
11. **Transport cost is ₹1.0 per km per quintal, one way.**
    - Public 2025 rates for 1–2 t mini trucks are about ₹10–25 per km, which is roughly ₹0.5–2.5 per km per quintal, so ₹1 is plausible.
    - But many trips are priced per trip or charge the return leg, which would be about ₹2.
12. **Selling options are ranked by trust tier first, then net price.** The tiers, best first:
    1. fresh real data on a market big enough for the load;
    2. real data that is **thin** (the load is over 50% of the market's median real daily arrivals in the last 90 days) or **stale** (last report more than 30 days before the forecast date);
    3. synthetic data.

    The thin-market check is new. Without it, Manchar tomato (₹2,400/q, but only 1–8 quintals arriving a day) was recommended for a 20-quintal sale.
13. **Best crop to grow:**
    - harvest month = sowing month (15th) + duration;
    - in-season crops rank first, then by expected ₹/quintal;
    - yield and input costs are ignored.
14. **Artifacts (about 5 MB) are committed.** `data/raw/ceda/` and `data/synthetic/` are git-ignored because they are rebuilt deterministically.

## 5. Known limitations

- **Stale data:** forecasts are for 31 Oct – 2 Nov 2025 because CEDA ends at 2025-10-30.
  - On 2026-09-28 every district, crop and indicator was requested up to that day, and the newest row was still 2025-10-30. So retraining gains nothing until CEDA publishes newer data; rerun `python -m forecaster.ceda && python -m forecaster.data && python -m forecaster.train` when it does. The open window refreshes itself once its copy is a day old.
  - data.gov.in, the live feed CLAUDE.md names as the next step, could not be reached from this build environment: the network policy blocks `api.data.gov.in`.
- **Pune(Hadapsar)** (id 3110, about 4,600 rows, 2012–2020) is named but not modelled, because it stopped reporting.
- **9 pairs have no real prices:** tomato and potato at the small outer Pune markets. By default they are hidden from every answer. With `api.show_synthetic: true` they appear, labelled `synthetic`, and their numbers are illustrative only.
- **Kalyan has no reliable arrivals,** so its demand signal leans on synthetic arrivals, and its market size can't be checked for a sale.
- **Crop ranking ignores yield per acre and input costs.** It compares ₹/quintal only.
- **Reasons are in English only.** Marathi is not done.
- **No auth, rate limiting or caching** on the API. CORS allows localhost on any port plus the origins you configure.
- **CEDA data is for non-commercial use.** The app must show the CEDA logo and `attribution`.

## 6. Checklist status

| # | Item | Status |
|---|---|---|
| 1 | Run the CEDA download | **Done.** 18 requests, CEDA source, tomato arrivals are real. |
| 2 | Name `market_id N` rows | **Done.** The CEDA `/markets` lookup works again; 3110 is Pune(Hadapsar) (stopped 2020). Nothing is unnamed. |
| 3 | Retrain, stay under 5 min, compare metrics | **Done.** 42 s; every crop improved (see §2). |
| 4 | Spot-check coordinates | **Done.** 5 checked; Pune and Vashi corrected (see §4.4). |
| 5 | Confirm crop calendar | **Cross-checked against sources**, onion duration fixed. **Agronomist sign-off still needed.** |
| 6 | Confirm transport rate | **Checked** against public rates: plausible but low if round trips are charged. **Your call.** |
| 7 | Check sell-options from real farms | **Done** for 4 farm locations. Found and fixed thin-market recommendations; stale and synthetic markets rank last. |
| 8 | Check reason texts | **Done.** Removed jargon ("p50", "Rs/q", "threshold"), fixed grammar, stopped presenting missing data as a cause. |
| 9 | Hide or show synthetic-only pairs in the app | **Done: hidden by default.** Pairs with no real prices return 404 and are left out of `/meta`, demand, sell-options and crops. Set `api.show_synthetic: true` for demos. |
| 10 | CEDA logo in the app, tighten `api.cors_origins` | **API side done.** `/meta.attribution_details` gives the text, terms URL, logo placement and rules. CORS now allows only localhost plus `api.cors_origins` / `FARMNEX_CORS_ORIGINS`. **Still to do in the Flutter repo:** add the official logo asset (download it from the terms page) at the bottom right of price screens, and set the production origin. |
