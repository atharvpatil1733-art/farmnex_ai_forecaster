# Model metrics

Model version `20260928T081539Z-asof20251030`. Data as_of **2025-10-30**; test = target dates after **2025-08-31** (last 60 days), time split by target date, never random. Metrics use REAL pairs only (synthetic pairs are trained on but never scored). Baseline = seasonal naive (same weekday last week; if that day was not reported, the last reported value). MAE in Rs/quintal (price) or tonnes (arrivals). Training took 47.6 s.

## Price

| crop | horizon | n | mae_model | mae_baseline | mape_model | mape_baseline | coverage_p10_p90 | beats_baseline | beats_baseline_mape |
|---|---|---|---|---|---|---|---|---|---|
| Onion | 1 | 442 | 101.3 | 128.4 | 9.2 | 11.6 | 81.9 | True | True |
| Onion | 2 | 442 | 110.0 | 131.9 | 9.9 | 11.9 | 80.8 | True | True |
| Onion | 3 | 442 | 112.8 | 135.0 | 10.2 | 12.1 | 81.9 | True | True |
| Potato | 1 | 332 | 112.9 | 145.6 | 7.8 | 9.9 | 78.3 | True | True |
| Potato | 2 | 332 | 123.1 | 149.3 | 8.5 | 10.2 | 76.2 | True | True |
| Potato | 3 | 332 | 127.1 | 151.4 | 8.7 | 10.4 | 80.1 | True | True |
| Tomato | 1 | 418 | 236.3 | 336.2 | 19.6 | 28.6 | 79.2 | True | True |
| Tomato | 2 | 418 | 272.6 | 360.0 | 22.8 | 29.9 | 76.1 | True | True |
| Tomato | 3 | 418 | 294.8 | 384.0 | 25.6 | 32.6 | 77.5 | True | True |
| Onion | all | 1326 | 108.0 | 131.8 | 9.8 | 11.9 | 81.5 | True | True |
| Potato | all | 996 | 121.0 | 148.8 | 8.3 | 10.2 | 78.2 | True | True |
| Tomato | all | 1254 | 267.9 | 360.1 | 22.7 | 30.4 | 77.6 | True | True |

**Crops that do NOT beat the baseline on MAE (price):** none
**Crop x horizon rows that do NOT beat it on MAPE (price):** none

## Arrivals

| crop | horizon | n | mae_model | mae_baseline | mape_model | mape_baseline | coverage_p10_p90 | beats_baseline | beats_baseline_mape |
|---|---|---|---|---|---|---|---|---|---|
| Onion | 1 | 413 | 93.5 | 126.9 | 35.8 | 51.6 | 75.8 | True | True |
| Onion | 2 | 413 | 96.7 | 129.6 | 37.0 | 51.4 | 75.5 | True | True |
| Onion | 3 | 413 | 100.2 | 133.6 | 38.6 | 54.3 | 75.5 | True | True |
| Potato | 1 | 332 | 56.1 | 83.1 | 59.6 | 81.5 | 75.6 | True | True |
| Potato | 2 | 332 | 59.1 | 86.2 | 62.1 | 79.7 | 75.6 | True | True |
| Potato | 3 | 332 | 60.1 | 87.8 | 64.1 | 85.4 | 72.0 | True | True |
| Tomato | 1 | 385 | 17.6 | 26.8 | 32.7 | 33.7 | 80.0 | True | True |
| Tomato | 2 | 385 | 18.0 | 29.5 | 33.1 | 37.5 | 79.0 | True | True |
| Tomato | 3 | 385 | 18.3 | 27.1 | 33.2 | 37.4 | 78.4 | True | True |
| Onion | all | 1239 | 96.8 | 130.0 | 37.1 | 52.4 | 75.6 | True | True |
| Potato | all | 996 | 58.4 | 85.7 | 61.9 | 82.2 | 74.4 | True | True |
| Tomato | all | 1155 | 17.9 | 27.8 | 33.0 | 36.2 | 79.1 | True | True |

**Crops that do NOT beat the baseline on MAE (arrivals):** none
**Crop x horizon rows that do NOT beat it on MAPE (arrivals):** none

## Data behind the models

- 39 of 48 market x crop pairs have real prices; the rest use synthetic prices.
- 36 pairs have real arrivals.
- Rows: price: train 203838, test 4800, arrivals: train 187552, test 5025

## Best-crop monthly model (SARIMAX)

- Pune x Onion: SARIMAX ok
- Pune x Tomato: SARIMAX ok
- Pune x Potato: SARIMAX ok
- Thane x Onion: SARIMAX ok
- Thane x Tomato: SARIMAX ok
- Thane x Potato: SARIMAX ok
