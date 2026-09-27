# Model metrics

Model version `20260927T164925Z-asof20251030`. Data as_of **2025-10-30**; test = target dates after **2025-08-31** (last 60 days), time split by target date, never random. Metrics use REAL pairs only (synthetic pairs are trained on but never scored). Baseline = seasonal naive (same weekday last week; if that day was not reported, the last reported value). MAE in Rs/quintal (price) or tonnes (arrivals). Training took 20.4 s.

## Price

| crop | horizon | n | mae_model | mae_baseline | mape_model | mape_baseline | coverage_p10_p90 | beats_baseline | beats_baseline_mape |
|---|---|---|---|---|---|---|---|---|---|
| Onion | 1 | 369 | 127.5 | 137.7 | 12.2 | 12.5 | 62.9 | True | True |
| Onion | 2 | 369 | 134.2 | 138.4 | 12.8 | 12.6 | 64.2 | True | False |
| Onion | 3 | 369 | 135.1 | 139.9 | 12.8 | 12.8 | 64.0 | True | False |
| Potato | 1 | 288 | 124.7 | 154.2 | 8.9 | 10.4 | 70.5 | True | True |
| Potato | 2 | 288 | 136.9 | 155.8 | 9.8 | 10.6 | 66.3 | True | True |
| Potato | 3 | 288 | 134.6 | 157.8 | 9.6 | 10.8 | 68.4 | True | True |
| Tomato | 1 | 177 | 256.4 | 300.8 | 21.8 | 24.3 | 66.1 | True | True |
| Tomato | 2 | 177 | 289.3 | 314.8 | 23.9 | 24.9 | 65.0 | True | True |
| Tomato | 3 | 177 | 311.2 | 316.5 | 25.7 | 25.0 | 63.3 | True | False |
| Onion | all | 1107 | 132.3 | 138.7 | 12.6 | 12.6 | 63.7 | True | True |
| Potato | all | 864 | 132.1 | 155.9 | 9.4 | 10.6 | 68.4 | True | True |
| Tomato | all | 531 | 285.7 | 310.7 | 23.8 | 24.7 | 64.8 | True | True |

**Crops that do NOT beat the baseline on MAE (price):** none
**Crop x horizon rows that do NOT beat it on MAPE (price):** Onion h2, Onion h3, Tomato h3

## Arrivals

| crop | horizon | n | mae_model | mae_baseline | mape_model | mape_baseline | coverage_p10_p90 | beats_baseline | beats_baseline_mape |
|---|---|---|---|---|---|---|---|---|---|
| Onion | 1 | 372 | 98.6 | 109.6 | 41.6 | 54.2 | 65.9 | True | True |
| Onion | 2 | 372 | 102.0 | 110.7 | 43.8 | 53.6 | 64.0 | True | True |
| Onion | 3 | 372 | 101.1 | 113.6 | 44.0 | 56.9 | 63.4 | True | True |
| Potato | 1 | 290 | 38.7 | 54.3 | 73.1 | 89.3 | 61.4 | True | True |
| Potato | 2 | 290 | 39.6 | 53.9 | 78.6 | 87.0 | 59.7 | True | True |
| Potato | 3 | 290 | 40.2 | 56.3 | 79.8 | 93.5 | 61.7 | True | True |
| Onion | all | 1116 | 100.6 | 111.3 | 43.2 | 54.9 | 64.4 | True | True |
| Potato | all | 870 | 39.5 | 54.8 | 77.2 | 89.9 | 60.9 | True | True |

**Crops that do NOT beat the baseline on MAE (arrivals):** none
**Crop x horizon rows that do NOT beat it on MAPE (arrivals):** none

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
