# REVIEW: farmnex_ai_forecaster end-to-end build

Everything runs end to end:
- `python -m forecaster.ceda` downloads the data with 18 API requests.
- `python -m forecaster.data` cleans it.
- `python -m forecaster.train` takes 42 s on 4 CPUs.
- `uvicorn app.main:app` serves all 6 endpoints, and each one returned 200 on a live run (`reports/sample_responses.md`).
- `python -m pytest -q` passes 44 tests.

**The data is now full CEDA API history: 2012-01-01 to 2025-10-30, Pune district, 54,580 rows.**

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
- **4 market ids have no name** (checklist item 2). None of them appears in any old export, and the `/markets` lookup hangs, so they are listed as unknown and dropped:

  | CEDA id | Rows | Dates | Note |
  |---|---|---|---|
  | 3110 | 4,621 | 2012 to 2020-05-14 | Probably the old id of Manjri or Moshi: both new ids start 1–4 days after it ends. I did not guess which. |
  | 1454, 1456, 2385 | 26 in total | scattered | Too small to matter. |

  If you know which market 3110 is, add `"market_id 3110"` to that market's `aliases` in `config.yaml`, then rerun `python -m forecaster.data && python -m forecaster.train`.

## 2. Metrics

These are leak-free and scored on real pairs only. The test period is 2025-09-01 to 2025-10-30. The baseline is the seasonal naive (same weekday last week). MAE is in ₹/quintal for price and tonnes for arrivals.

| Target | Crop | n | MAE model | MAE baseline | MAPE model | MAPE baseline | p10–p90 coverage |
|---|---|---|---|---|---|---|---|
| price | Onion | 1107 | 112.2 | 138.7 | 10.3% | 12.6% | 81.8% |
| price | Potato | 870 | 126.8 | 156.2 | 8.7% | 10.6% | 78.9% |
| price | Tomato | 1032 | 242.2 | 317.6 | 18.1% | 23.6% | 80.8% |
| arrivals | Onion | 1116 | 86.7 | 111.3 | 39.0% | 54.9% | 78.1% |
| arrivals | Potato | 870 | 38.1 | 54.8 | 64.1% | 89.9% | 74.7% |
| arrivals | Tomato | 1032 | 17.0 | 24.9 | 34.0% | 37.3% | 79.1% |

- **Every crop beats the baseline on MAE and MAPE, at every horizon.** No crop is flagged. Per-horizon rows are in `reports/metrics.md`.
- **The p10–p90 intervals now cover about 80% of actual values**, which is what they should. On the old export data they covered only about 65%.
- **Change from the export-only build:**

  | Crop | Price MAE before | Price MAE now |
  |---|---|---|
  | Onion | 132 | 112 |
  | Potato | 132 | 127 |
  | Tomato | 286 | 242 |

- **The SARIMAX crop model now runs for every Pune crop.** Before, it fell back to historical averages.

## 3. Real vs synthetic per market x crop

Each cell is price source / arrivals source, with the number of real price days in brackets. A pair needs at least 30 real days to count as "real". 33 of 48 pairs have real prices and 33 have real arrivals.

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
| Vashi | synth / synth (0 d) | synth / synth (0 d) | synth / synth (0 d) |
| Kalyan | synth / synth (0 d) | synth / synth (0 d) | synth / synth (0 d) |

Vashi and Kalyan need `Thane` or `Mumbai` added to `ceda.districts`, which would cost about 6 more requests.

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
7. **Synthetic data covers only the 15 pairs with no real data:**
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

- **Stale data:** forecasts are for 31 Oct – 2 Nov 2025 because CEDA ends at 2025-10-30. A live feed (data.gov.in) is the next step.
- **Unknown market id 3110** (about 4,600 rows, 2012–2020) is dropped until someone names it.
- **15 pairs have no real prices**, including all of Vashi and Kalyan (Thane). By default they are hidden from every answer; with `api.show_synthetic: true` they appear, labelled `synthetic`, and their numbers are illustrative only.
- **Crop ranking ignores yield per acre and input costs.** It compares ₹/quintal only.
- **Reasons are in English only.** Marathi is not done.
- **No auth, rate limiting or caching** on the API. CORS allows localhost on any port plus the origins you configure.
- **CEDA data is for non-commercial use.** The app must show the CEDA logo and `attribution`.

## 6. Checklist status

| # | Item | Status |
|---|---|---|
| 1 | Run the CEDA download | **Done.** 18 requests, CEDA source, tomato arrivals are real. |
| 2 | Name `market_id N` rows | **Checked.** 4 ids can't be named from any source I can reach (see §1). Id 3110 needs you. |
| 3 | Retrain, stay under 5 min, compare metrics | **Done.** 42 s; every crop improved (see §2). |
| 4 | Spot-check coordinates | **Done.** 5 checked; Pune and Vashi corrected (see §4.4). |
| 5 | Confirm crop calendar | **Cross-checked against sources**, onion duration fixed. **Agronomist sign-off still needed.** |
| 6 | Confirm transport rate | **Checked** against public rates: plausible but low if round trips are charged. **Your call.** |
| 7 | Check sell-options from real farms | **Done** for 4 farm locations. Found and fixed thin-market recommendations; stale and synthetic markets rank last. |
| 8 | Check reason texts | **Done.** Removed jargon ("p50", "Rs/q", "threshold"), fixed grammar, stopped presenting missing data as a cause. |
| 9 | Hide or show synthetic-only pairs in the app | **Done: hidden by default.** Pairs with no real prices return 404 and are left out of `/meta`, demand, sell-options and crops. Set `api.show_synthetic: true` for demos. |
| 10 | CEDA logo in the app, tighten `api.cors_origins` | **API side done.** `/meta.attribution_details` gives the text, terms URL, logo placement and rules. CORS now allows only localhost plus `api.cors_origins` / `FARMNEX_CORS_ORIGINS`. **Still to do in the Flutter repo:** add the official logo asset (download it from the terms page) at the bottom right of price screens, and set the production origin. |
