# REVIEW: farmnex_ai_forecaster end-to-end build

Built unattended from CLAUDE.md. Everything runs: `python -m forecaster.train` (about 20 s on
4 CPUs) → `uvicorn app.main:app`. All 6 endpoints return 200 (`reports/sample_responses.md`),
and `python -m pytest -q` passes 43 tests. **The data is still the old website exports
(Feb 2024 – Oct 2025, Pune district only), not CEDA API history.** Read the CEDA section
first.

## 1. CEDA outcome (Step 0)

I made 2 of the allowed 3 requests, with no retries:

| # | Request | Result |
|---|---|---|
| 1 | `POST /agmarknet/prices` `{commodity_id: 23, state_id: 27, 2025-09-01..07}` (as specified) | **200 in 50 s**, but the rows are **state-level averages**: no `market_id` and no district, so they are useless for per-market forecasts. |
| 2 | Same, plus `district_id: [521]` (Pune), with no `market_id` | **200 in 9.5 s**, one row per market with `market_id` (172 = Pune, 2494 = Pimpri, ...). |

Earlier in this session, requests with a `market_id` filter and requests to `/agmarknet/markets`
hung until a 504 from the gateway (60 s). So **the market filter is what hangs, not the API**.
I changed `forecaster/ceda.py` to match (commit `16055ea`):
- It fetches per district, never sends `market_id`, and skips `/markets` unless
  `ceda.fetch_market_lists: true`.
- CEDA market ids get their names from the `market_id`/`market_name` columns in the old
  exports. It's the same Agmarknet id space: id 172 is "Pune" in both. An id not seen in any
  export shows up as `market_id N`, is listed as an unknown name in the data quality report,
  and is dropped. Example: 1171 appeared in diagnostic 2 and is not in the exports.
- A 5xx or timeout on a data window now halves the window instead of retrying it.
- 2 mocked tests were added: district-level fetch without market filters, and window
  splitting on a 504.

**I did NOT run `python -m forecaster.ceda`.** Its dry run plans about 20 requests, which is
over the "max 3 requests total" cap you set for Step 0. `mandi.csv` and
`reports/data_quality.md` are therefore unchanged from `main`, and everything below uses
the old exports. To get the full history, run this once (it fits the 36-request per-run budget):

```bash
python -m forecaster.ceda && python -m forecaster.data && python -m forecaster.train
```

Unverified until then:
- whether windows of several years at district level stay under the 60 s gateway limit. The
  code splits them if they don't, which costs more of the request budget.
- whether `/agmarknet/quantities` works and what its arrivals field is called. If the report
  says "no quantity column", add the field name to `_QTY_KEYS` in `data.py`.

## 2. Metrics (leak-free, real pairs only, test = 2025-09-01..2025-10-30)

Seasonal-naive baseline = same weekday last week; if that day wasn't reported, the last
reported value. MAE is in Rs/quintal for price and tonnes for arrivals.

| Target | Crop | n | MAE model | MAE baseline | MAPE model | MAPE baseline | p10–p90 coverage |
|---|---|---|---|---|---|---|---|
| price | Onion | 1107 | 132.3 | 138.7 | 12.6% | 12.6% | 63.7% |
| price | Potato | 864 | 132.1 | 155.9 | 9.4% | 10.6% | 68.4% |
| price | Tomato | 531 | 285.7 | 310.7 | 23.8% | 24.7% | 64.8% |
| arrivals | Onion | 1116 | 100.6 | 111.3 | 43.2% | 54.9% | 64.4% |
| arrivals | Potato | 870 | 39.5 | 54.8 | 77.2% | 89.9% | 60.9% |

- **Every crop beats the baseline on MAE.** On MAPE, these rows do not: **Onion h2, Onion h3
  (a tie) and Tomato h3**. Onion's gain is small (about 5% lower MAE).
- Per-horizon rows are in `reports/metrics.md`.
- **The p10–p90 intervals are too narrow:** they cover 61–68% of actual values instead of
  80%. Treat the floor price (p10) as optimistic.
- Tomato arrivals are not scored: there is no real tomato quantity data.
- One leak was caught in self-review. At first, the synthetic data was calibrated on real data
  from the test period, which made onion look better than it is (MAE 119 instead of the honest
  132). Evaluation now builds its synthetic data from real data up to the cutoff only, and a
  test covers this.

## 3. Real vs synthetic per market x crop

Each cell is price source / arrivals source, with the number of real price days in brackets.
A pair counts as "real" for a target only with at least 30 real days
(`synthetic.min_real_days`). 29 of 48 pairs have real prices and 22 have real arrivals.

| Market | Onion | Tomato | Potato |
|---|---|---|---|
| Pune | real / real (229 d) | real / synth (130 d) | real / real (321 d) |
| Pimpri | real / real (272 d) | real / synth (151 d) | synth / synth (2 d) |
| Manjri | real / real (262 d) | real / synth (143 d) | real / real (365 d) |
| Moshi | real / real (239 d) | real / synth (134 d) | real / real (340 d) |
| Khadki | real / real (221 d) | real / synth (137 d) | real / real (329 d) |
| Khed(Chakan) | real / real (202 d) | real / synth (121 d) | real / real (288 d) |
| Manchar | real / real (78 d) | real / synth (62 d) | real / real (97 d) |
| Junnar | real / real (43 d) | synth / synth (0 d) | synth / real (24 d) |
| Otur | real / real (73 d) | synth / synth (9 d) | real / real (101 d) |
| Narayangaon | real / real (170 d) | real / synth (118 d) | real / real (139 d) |
| Alephata | real / real (90 d) | synth / synth (0 d) | synth / synth (0 d) |
| Baramati | real / real (55 d) | synth / synth (0 d) | synth / synth (0 d) |
| Shirur | synth / synth (21 d) | synth / synth (0 d) | synth / synth (0 d) |
| Indapur | real / real (41 d) | synth / synth (0 d) | synth / synth (0 d) |
| Vashi | synth / synth (0 d) | synth / synth (0 d) | synth / synth (0 d) |
| Kalyan | synth / synth (0 d) | synth / synth (0 d) | synth / synth (0 d) |

- Tomato arrivals are synthetic everywhere, as CLAUDE.md allows ("synthetic arrivals only").
  The real `mandi.csv` still has no tomato arrivals.
- Baramati's onion prices are real but a year old: the last report is 2024-10-28. Answers for
  it carry a staleness warning, and it ranks below fresh real markets.

## 4. Assumptions and approximate values

**Data and time**
1. **Forecast origin = as_of = 2025-10-30**, the last real date, not today (2026-09-27).
   Every response has `forecast_origin`. `as_of` is the pair's last real price date, or the
   data as_of for synthetic pairs.
2. **The data covers Feb 2024 – Oct 2025 only**, so `modelling.train_start: 2015` has no
   effect. It wasn't possible to check whether older data helps.
3. **Arrivals are in tonnes** (the bare `qty` field), unchanged from the data prep PR.

**Reference data (`data/ref/`, all marked approximate in `data/README.md`)**
4. **Market coordinates** were picked from public maps to about 1 km.
5. **Crop calendar**, as sowing months and days from sowing to harvest:

   | Crop | Sowing months | Duration |
   |---|---|---|
   | Onion | Jun, Jul, Sep–Jan | 120 days |
   | Tomato | Jan, Feb, Jun, Jul, Oct, Nov | 110 days |
   | Potato | Jun, Jul, Oct, Nov | 100 days |

   These are typical Maharashtra windows, not agronomic advice.
6. **Festival dates 2012–2027** (7 festivals) were written from memory. Lunar dates may be off
   by a day, and Makar Sankranti is fixed at 14 Jan.

**Synthetic data**
7. It covers 3 years ending at as_of.
8. Each crop's price level is its real median. Each crop peaks in a set month: Onion Oct,
   Tomato Aug, Potato Sep. Seasonal swing: ±35% onion, ±45% tomato, ±15% potato.
9. Effects: monsoon +10%, festival ±3 days +6%, Monday +2%, AR(1) noise, and arrivals that
   fall as price rises (∝ price^-1.5).
10. Each market has one closed weekday plus 12% random missing days.
11. **Anchoring:** each synthetic crop is rescaled so its last-60-day median matches the real
    one. Without this, synthetic Shirur onion showed ₹2,536/q against a real ~₹1,100 and won
    "best place to sell".

**Models**
12. LightGBM with defaults, no tuning: 300 trees, learning rate 0.05, 31 leaves. It is trained
    on log1p(target) because quantiles survive monotone transforms. Predictions are sorted so
    p10 ≤ p50 ≤ p90.
13. The global models train on real and synthetic rows together, with an `is_synthetic`
    feature, but only real pairs are scored.
14. Served models are refit on all rows, train and test. The metrics come from the
    train-only models.
15. **Feature and baseline conventions:**
    - `lag_1` is the value on the origin day t (known at the end of t), and `lag_k` is day
      t-k+1.
    - Rolling windows include t.
    - The price model gets arrivals features only from real arrivals.
    - The baseline falls back to the last reported value when "same weekday last week" is
      missing, so it can score every row.

**Recommendations**
16. **`likely_closed`:** the market reports on that weekday less than 25% as often as on its
    busiest weekday (`likely_closed_share`). This comes from real reports, or synthetic ones
    for synthetic-only markets. The best-day choice skips likely-closed days.
17. **Demand signal:** HIGH if the p50 price change vs the 7-day average is above +3% and
    greater than the arrivals change. LOW if it is below -3% and less than the arrivals
    change. NORMAL otherwise. It is the median across the district's markets. The response
    labels it a PROXY.
18. **Sell options:**
    - transport costs 1.0 Rs per km per quintal, one way, straight-line distance (approximate
      small-truck cost); the default radius is 100 km.
    - markets are ranked by data trust first (fresh real, then stale real over 30 days old,
      then synthetic), then by net price.
19. **Best crop to grow:**
    - sowing date = the 15th of the next occurrence of the sowing month at or after as_of;
      harvest = sowing date + duration.
    - in-season crops rank before out-of-season ones, then by expected Rs/quintal. Yield and
      input costs are ignored.
20. **SARIMAX** is (1,0,0)x(1,0,0,12) on log monthly district means from real-price pairs, and
    needs at least 12 months. If it fails or its forecast falls outside 0.33–3x the history
    mean, the fallback is the same-month average, then the overall average when that month has
    never been observed. **For Pune it falls back for every crop**: onion has 11 months, tomato
    7, and the potato forecast was implausible. Thane (synthetic) uses SARIMAX.

**Implementation choices**
21. SHAP values come from LightGBM's built-in TreeSHAP (`pred_contrib=True`, exact tree SHAP),
    not the `shap` package. Reasons are the top 3 contributions of the p50 price model for
    day +1, shown as % effects.
22. CORS allows `*` (Flutter web). Tighten it to the app's origin before production.
23. Artifacts (5 MB) are committed so the API runs from a fresh clone.
    `data/synthetic/` is git-ignored because it is rebuilt deterministically.

## 5. Known limitations

- **Real history is thin:** 2 part-seasons, no Nov–Feb data, and only 60 test days, all in
  Sep–Oct 2025. The metrics say nothing about winter or other years. Running the CEDA download
  (section 1) is the single biggest improvement available.
- **The intervals are too narrow** (about 65% coverage instead of 80%).
- **Crop recommendations for Pune are just same-month historical averages**, and months with
  no data (Nov–Feb for onion) fall back to the overall average. They are not trustworthy yet.
- **Vashi, Kalyan (Thane) and 17 other pairs are fully synthetic.** Their answers say
  `data_source: "synthetic"`, but the numbers are illustrative only.
- **Demand is a proxy**, and tomato's arrivals side is synthetic.
- **The prices are stale:** forecasts are for 31 Oct – 2 Nov 2025, because the data ends
  2025-10-30.
- **No auth, rate limiting or caching** on the API; it's a prototype.
- **Commercial use of CEDA data needs CEDA's permission.** The app must show the CEDA logo and
  credit, which is returned in every response's `attribution`.

## 6. Checklist for you to verify (10)

1. [ ] Run `python -m forecaster.ceda` once. Confirm it completes within the budget and that
       `reports/data_quality.md` says the source is the CEDA API cache. Then check that
       `/agmarknet/quantities` produced arrivals.
2. [ ] After step 1, look for `market_id N` names in the data quality report and add aliases
       to `config.yaml` for any you want to keep.
3. [ ] Re-run `python -m forecaster.train`. Check that it stays under 5 minutes with the longer
       history, and compare `reports/metrics.md` with the table above.
4. [ ] Spot-check 3–4 coordinates in `data/ref/markets.csv`, especially the sub-yards Manjri,
       Moshi and Khadki.
5. [ ] Confirm the crop calendar (sowing months and durations) with an agronomist or the
       FarmNex team.
6. [ ] Confirm `recommend.rate_per_km_quintal: 1.0` is a realistic transport cost for your
       farmers.
7. [ ] Check that `/forecast/sell-options` from a real farm location ranks markets sensibly,
       and that Baramati and synthetic markets rank last.
8. [ ] Read 2–3 `reason` texts in `reports/sample_responses.md` and decide whether farmers will
       understand them. They are plain English; translation is not done.
9. [ ] Decide whether synthetic-only pairs (Vashi, Kalyan, ...) should be hidden in the app
       rather than shown with a "synthetic" badge.
10. [ ] Confirm the Flutter app shows the CEDA logo and the `attribution` text on every price
        screen, and restrict `api.cors_origins`.
