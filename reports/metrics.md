# Model metrics

Model version `20260928T073941Z-asof20251030`. Data as_of **2025-10-30**; test = target dates after **2025-08-31** (last 60 days), time split by target date, never random. Metrics use REAL pairs only (synthetic pairs are trained on but never scored). Baseline = seasonal naive (same weekday last week; if that day was not reported, the last reported value). MAE in Rs/quintal (price) or tonnes (arrivals). Training took 41.1 s.

## Price

| crop | horizon | n | mae_model | mae_baseline | mape_model | mape_baseline | coverage_p10_p90 | beats_baseline | beats_baseline_mape |
|---|---|---|---|---|---|---|---|---|---|
| Onion | 1 | 369 | 106.1 | 137.7 | 9.7 | 12.5 | 81.6 | True | True |
| Onion | 2 | 369 | 115.2 | 138.4 | 10.6 | 12.6 | 81.8 | True | True |
| Onion | 3 | 369 | 115.3 | 139.9 | 10.6 | 12.8 | 82.1 | True | True |
| Potato | 1 | 290 | 119.7 | 154.5 | 8.2 | 10.4 | 77.6 | True | True |
| Potato | 2 | 290 | 128.5 | 156.1 | 8.8 | 10.6 | 79.0 | True | True |
| Potato | 3 | 290 | 132.3 | 158.1 | 9.0 | 10.8 | 80.0 | True | True |
| Tomato | 1 | 344 | 222.6 | 305.0 | 16.6 | 22.9 | 81.7 | True | True |
| Tomato | 2 | 344 | 246.8 | 319.4 | 18.4 | 23.7 | 79.4 | True | True |
| Tomato | 3 | 344 | 257.3 | 328.3 | 19.3 | 24.3 | 81.4 | True | True |
| Onion | all | 1107 | 112.2 | 138.7 | 10.3 | 12.6 | 81.8 | True | True |
| Potato | all | 870 | 126.8 | 156.2 | 8.7 | 10.6 | 78.9 | True | True |
| Tomato | all | 1032 | 242.2 | 317.6 | 18.1 | 23.6 | 80.8 | True | True |

**Crops that do NOT beat the baseline on MAE (price):** none
**Crop x horizon rows that do NOT beat it on MAPE (price):** none

## Arrivals

| crop | horizon | n | mae_model | mae_baseline | mape_model | mape_baseline | coverage_p10_p90 | beats_baseline | beats_baseline_mape |
|---|---|---|---|---|---|---|---|---|---|
| Onion | 1 | 372 | 83.5 | 109.6 | 37.4 | 54.2 | 78.8 | True | True |
| Onion | 2 | 372 | 86.1 | 110.7 | 39.0 | 53.6 | 77.4 | True | True |
| Onion | 3 | 372 | 90.6 | 113.6 | 40.7 | 56.9 | 78.2 | True | True |
| Potato | 1 | 290 | 36.8 | 54.3 | 62.2 | 89.3 | 76.6 | True | True |
| Potato | 2 | 290 | 37.9 | 53.9 | 63.8 | 87.0 | 74.5 | True | True |
| Potato | 3 | 290 | 39.4 | 56.3 | 66.3 | 93.5 | 73.1 | True | True |
| Tomato | 1 | 344 | 17.1 | 24.0 | 33.8 | 34.7 | 80.8 | True | True |
| Tomato | 2 | 344 | 17.0 | 26.8 | 33.9 | 38.8 | 77.9 | True | True |
| Tomato | 3 | 344 | 17.0 | 24.0 | 34.2 | 38.6 | 78.5 | True | True |
| Onion | all | 1116 | 86.7 | 111.3 | 39.0 | 54.9 | 78.1 | True | True |
| Potato | all | 870 | 38.1 | 54.8 | 64.1 | 89.9 | 74.7 | True | True |
| Tomato | all | 1032 | 17.0 | 24.9 | 34.0 | 37.3 | 79.1 | True | True |

**Crops that do NOT beat the baseline on MAE (arrivals):** none
**Crop x horizon rows that do NOT beat it on MAPE (arrivals):** none

## Data behind the models

- 33 of 48 market x crop pairs have real prices; the rest use synthetic prices.
- 33 pairs have real arrivals.
- Rows: price: train 177675, test 5046, arrivals: train 168250, test 5055

## Best-crop monthly model (SARIMAX)

- Pune x Onion: SARIMAX ok
- Pune x Tomato: SARIMAX ok
- Pune x Potato: SARIMAX ok
- Thane x Onion: SARIMAX ok
- Thane x Tomato: SARIMAX ok
- Thane x Potato: SARIMAX ok
