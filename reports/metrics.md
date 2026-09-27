# Model metrics

Model version `20260927T164231Z-asof20251030`. Data as_of **2025-10-30**; test = target dates after **2025-08-31** (last 60 days), time split by target date, never random. Metrics use REAL pairs only (synthetic pairs are trained on but never scored). Baseline = seasonal naive (same weekday last week; if that day was not reported, the last reported value). MAE in Rs/quintal (price) or tonnes (arrivals). Training took 20.0 s.

## Price

| crop | horizon | n | mae_model | mae_baseline | mape_model | mape_baseline | coverage_p10_p90 | beats_baseline |
|---|---|---|---|---|---|---|---|---|
| Onion | 1 | 369 | 126.7 | 137.7 | 12.1 | 12.5 | 65.9 | True |
| Onion | 2 | 369 | 131.9 | 138.4 | 12.6 | 12.6 | 66.7 | True |
| Onion | 3 | 369 | 132.7 | 139.9 | 12.6 | 12.8 | 65.9 | True |
| Potato | 1 | 288 | 121.9 | 154.2 | 8.7 | 10.4 | 69.4 | True |
| Potato | 2 | 288 | 132.3 | 155.8 | 9.4 | 10.6 | 69.4 | True |
| Potato | 3 | 288 | 131.3 | 157.8 | 9.3 | 10.8 | 71.5 | True |
| Tomato | 1 | 177 | 264.1 | 300.8 | 22.5 | 24.3 | 67.2 | True |
| Tomato | 2 | 177 | 299.1 | 314.8 | 25.0 | 24.9 | 62.7 | True |
| Tomato | 3 | 177 | 316.5 | 316.5 | 26.6 | 25.0 | 62.1 | False |
| Onion | all | 1107 | 130.4 | 138.7 | 12.4 | 12.6 | 66.1 | True |
| Potato | all | 864 | 128.5 | 155.9 | 9.1 | 10.6 | 70.1 | True |
| Tomato | all | 531 | 293.2 | 310.7 | 24.7 | 24.7 | 64.0 | True |

**Crops that do NOT beat the baseline (price):** none

## Arrivals

| crop | horizon | n | mae_model | mae_baseline | mape_model | mape_baseline | coverage_p10_p90 | beats_baseline |
|---|---|---|---|---|---|---|---|---|
| Onion | 1 | 372 | 98.8 | 109.6 | 41.0 | 54.2 | 65.1 | True |
| Onion | 2 | 372 | 100.3 | 110.7 | 43.1 | 53.6 | 64.0 | True |
| Onion | 3 | 372 | 100.6 | 113.6 | 43.1 | 56.9 | 62.6 | True |
| Potato | 1 | 290 | 38.2 | 54.3 | 75.4 | 89.3 | 63.8 | True |
| Potato | 2 | 290 | 39.4 | 53.9 | 80.3 | 87.0 | 61.4 | True |
| Potato | 3 | 290 | 39.4 | 56.3 | 81.5 | 93.5 | 63.1 | True |
| Onion | all | 1116 | 99.9 | 111.3 | 42.4 | 54.9 | 63.9 | True |
| Potato | all | 870 | 39.0 | 54.8 | 79.1 | 89.9 | 62.8 | True |

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
