# Model metrics

Model version `20260927T164602Z-asof20251030`. Data as_of **2025-10-30**; test = target dates after **2025-08-31** (last 60 days), time split by target date, never random. Metrics use REAL pairs only (synthetic pairs are trained on but never scored). Baseline = seasonal naive (same weekday last week; if that day was not reported, the last reported value). MAE in Rs/quintal (price) or tonnes (arrivals). Training took 19.5 s.

## Price

| crop | horizon | n | mae_model | mae_baseline | mape_model | mape_baseline | coverage_p10_p90 | beats_baseline |
|---|---|---|---|---|---|---|---|---|
| Onion | 1 | 369 | 115.6 | 137.7 | 10.7 | 12.5 | 73.2 | True |
| Onion | 2 | 369 | 120.1 | 138.4 | 11.1 | 12.6 | 76.2 | True |
| Onion | 3 | 369 | 121.6 | 139.9 | 11.2 | 12.8 | 75.6 | True |
| Potato | 1 | 288 | 123.7 | 154.2 | 8.7 | 10.4 | 74.3 | True |
| Potato | 2 | 288 | 131.3 | 155.8 | 9.2 | 10.6 | 70.8 | True |
| Potato | 3 | 288 | 130.9 | 157.8 | 9.1 | 10.8 | 75.7 | True |
| Tomato | 1 | 177 | 279.7 | 300.8 | 23.1 | 24.3 | 60.5 | True |
| Tomato | 2 | 177 | 323.4 | 314.8 | 26.2 | 24.9 | 61.0 | False |
| Tomato | 3 | 177 | 345.5 | 316.5 | 28.1 | 25.0 | 59.3 | False |
| Onion | all | 1107 | 119.1 | 138.7 | 11.0 | 12.6 | 75.0 | True |
| Potato | all | 864 | 128.6 | 155.9 | 9.0 | 10.6 | 73.6 | True |
| Tomato | all | 531 | 316.2 | 310.7 | 25.8 | 24.7 | 60.3 | False |

**Crops that do NOT beat the baseline (price):** Tomato

## Arrivals

| crop | horizon | n | mae_model | mae_baseline | mape_model | mape_baseline | coverage_p10_p90 | beats_baseline |
|---|---|---|---|---|---|---|---|---|
| Onion | 1 | 372 | 99.4 | 109.6 | 43.2 | 54.2 | 63.2 | True |
| Onion | 2 | 372 | 100.7 | 110.7 | 45.1 | 53.6 | 61.3 | True |
| Onion | 3 | 372 | 102.6 | 113.6 | 45.6 | 56.9 | 61.3 | True |
| Potato | 1 | 290 | 39.4 | 54.3 | 71.1 | 89.3 | 59.3 | True |
| Potato | 2 | 290 | 39.9 | 53.9 | 78.5 | 87.0 | 59.0 | True |
| Potato | 3 | 290 | 41.6 | 56.3 | 77.1 | 93.5 | 57.6 | True |
| Onion | all | 1116 | 100.9 | 111.3 | 44.6 | 54.9 | 61.9 | True |
| Potato | all | 870 | 40.3 | 54.8 | 75.6 | 89.9 | 58.6 | True |

**Crops that do NOT beat the baseline (arrivals):** none

## Data behind the models

- 29 of 48 market x crop pairs have real prices; the rest use synthetic prices.
- 22 pairs have real arrivals; Tomato has no real arrivals anywhere, so tomato arrivals forecasts are synthetic-only and are not scored.
- Rows: price: train 56611, test 5073, arrivals: train 70691, test 5529

## Best-crop monthly model (SARIMAX)

- Pune x Onion: only 11 months of data (< 12)
- Pune x Tomato: only 7 months of data (< 12)
- Pune x Potato: SARIMAX forecast implausible
- Thane x Onion: SARIMAX ok
- Thane x Tomato: SARIMAX ok
- Thane x Potato: SARIMAX ok
