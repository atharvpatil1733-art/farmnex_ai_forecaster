# Model metrics

Model version `20260928T113858Z-asof20260928`. Data as_of **2026-09-28**; test = target dates after **2026-07-30** (last 60 days), time split by target date, never random. Metrics use REAL pairs only (synthetic pairs are trained on but never scored). Baseline = seasonal naive (same weekday last week; if that day was not reported, the last reported value). MAE in Rs/quintal (price) or tonnes (arrivals). Training took 50.5 s.

## Price

| crop | horizon | n | mae_model | mae_baseline | mape_model | mape_baseline | coverage_p10_p90 | beats_baseline | beats_baseline_mape |
|---|---|---|---|---|---|---|---|---|---|
| Onion | 1 | 528 | 237.8 | 358.5 | 8.1 | 12.3 | 82.4 | True | True |
| Onion | 2 | 528 | 261.4 | 360.9 | 9.0 | 12.4 | 80.9 | True | True |
| Onion | 3 | 528 | 287.3 | 364.6 | 9.9 | 12.5 | 80.5 | True | True |
| Potato | 1 | 361 | 70.6 | 88.6 | 6.9 | 8.6 | 79.2 | True | True |
| Potato | 2 | 361 | 74.9 | 90.0 | 7.3 | 8.6 | 80.3 | True | True |
| Potato | 3 | 361 | 75.2 | 89.8 | 7.3 | 8.6 | 82.0 | True | True |
| Tomato | 1 | 426 | 158.9 | 236.5 | 12.9 | 18.5 | 82.2 | True | True |
| Tomato | 2 | 426 | 186.3 | 241.3 | 15.0 | 18.9 | 80.3 | True | True |
| Tomato | 3 | 426 | 203.4 | 245.1 | 16.4 | 19.3 | 80.8 | True | True |
| Onion | all | 1584 | 262.1 | 361.3 | 9.0 | 12.4 | 81.2 | True | True |
| Potato | all | 1083 | 73.6 | 89.5 | 7.2 | 8.6 | 80.5 | True | True |
| Tomato | all | 1278 | 182.9 | 241.0 | 14.7 | 18.9 | 81.1 | True | True |

**Crops that do NOT beat the baseline on MAE (price):** none
**Crop x horizon rows that do NOT beat it on MAPE (price):** none

## Arrivals

| crop | horizon | n | mae_model | mae_baseline | mape_model | mape_baseline | coverage_p10_p90 | beats_baseline | beats_baseline_mape |
|---|---|---|---|---|---|---|---|---|---|
| Onion | 1 | 490 | 68.6 | 93.3 | 34.3 | 46.3 | 80.8 | True | True |
| Onion | 2 | 490 | 70.2 | 92.8 | 34.8 | 43.1 | 81.6 | True | True |
| Onion | 3 | 490 | 71.3 | 92.9 | 35.0 | 42.2 | 82.2 | True | True |
| Potato | 1 | 332 | 53.2 | 68.6 | 44.7 | 48.6 | 78.6 | True | True |
| Potato | 2 | 332 | 54.8 | 68.0 | 46.1 | 40.3 | 77.7 | True | False |
| Potato | 3 | 332 | 55.1 | 68.3 | 43.4 | 41.7 | 78.3 | True | False |
| Tomato | 1 | 396 | 28.7 | 39.9 | 38.4 | 32.8 | 82.6 | True | False |
| Tomato | 2 | 396 | 30.3 | 41.0 | 39.2 | 34.8 | 81.8 | True | False |
| Tomato | 3 | 396 | 30.4 | 40.8 | 38.3 | 34.3 | 80.8 | True | False |
| Onion | all | 1470 | 70.1 | 93.0 | 34.7 | 43.9 | 81.6 | True | True |
| Potato | all | 996 | 54.4 | 68.3 | 44.7 | 43.5 | 78.2 | True | False |
| Tomato | all | 1188 | 29.8 | 40.6 | 38.6 | 34.0 | 81.7 | True | False |

**Crops that do NOT beat the baseline on MAE (arrivals):** none
**Crop x horizon rows that do NOT beat it on MAPE (arrivals):** Potato h2, Potato h3, Tomato h1, Tomato h2, Tomato h3, Potato hall, Tomato hall

## Data behind the models

- 39 of 48 market x crop pairs have real prices; the rest use synthetic prices.
- 36 pairs have real arrivals.
- Rows: price: train 224474, test 5178, arrivals: train 206871, test 5298

## Best-crop monthly model (SARIMAX)

- Pune x Onion: SARIMAX ok
- Pune x Tomato: SARIMAX ok
- Pune x Potato: SARIMAX ok
- Thane x Onion: SARIMAX ok
- Thane x Tomato: SARIMAX ok
- Thane x Potato: SARIMAX ok
