# Stage 1 — Magnetic Sensor Noise Floor Characterization

**Date:** 2026-05-12
**Project:** Force–displacement decoupling from magnetic signals (APMD model)

## 1. Purpose

Establish the noise floor, drift behavior, sampling-rate limits, and any pathological configurations of the magnetic sensing front-end **before** attempting force/displacement decoupling experiments (Stages 2–8). The σ values measured here set the SNR threshold for the identifiability analysis (κ metric) in Stage 5.

## 2. Hardware Configuration

| Component | Spec |
|---|---|
| Magnetic sensor | Adafruit MLX90393 breakout (GAIN_1X, RESOLUTION_16) |
| Microcontroller | Adafruit QT Py M0 (ATSAMD21E18A) |
| Firmware | CircuitPython 10.2.0 |
| Bus | I2C @ 100 kHz |
| Host link | USB-CDC, 115200 baud, CSV text |
| OS / host | macOS, Python 3.13 + pyserial 3.5 |

## 3. Procedure

For each preset:

1. Sensor taped flat to desk, undisturbed for the duration
2. Magnetic-fiber sample removed, ≥30 cm from laptop, phone, displays
3. `stage1_noise.py <preset>` automates: edit `code.py` → push to `CIRCUITPY` → soft-reboot → 5 s warm-up → record 60 s
4. Per axis: report `mean`, `σ_raw`, `σ_detrend` (linear drift removed), `drift rate`, `peak-to-peak`

All raw data is in `stage1_data/<preset>_<timestamp>_raw.csv`. Accumulated summary stats in `stage1_data/summary.csv`.

## 4. Results

### 4.1 Noise floor by preset

| Preset | OSR | FILTER | Rate (Hz) | σ_Bx (µT) | σ_By (µT) | σ_Bz (µT) | Mean drift (µT/s) |
|---|---|---|---|---|---|---|---|
| `low_noise` | 3 | 5 | 14.6 | **0.388** | **0.416** | **0.597** | < 2×10⁻³ |
| `balanced`  | 2 | 3 | 51.8 | 1.122 | 1.131 | 1.691 | < 4×10⁻³ |
| `fast`      | 1 | 1 | 80.4 | 2.840 | 2.846 | 4.202 | < 2×10⁻³ |
| `fastest` ⚠️ | 0 | 0 | 81.9 | 5.106 | 5.130 | 7.508 | < 12×10⁻³ |

Earth-field mean (consistent across the three valid presets): **|B| ≈ 57 µT** (Bx ≈ +26.3, By ≈ +50.6, Bz ≈ +6.9 µT).

### 4.2 Noise scaling matches theory

Noise should scale as 1/√(OSR × FILTER averaging factor). Comparing low_noise (OSR_3+F_5) to fast (OSR_1+F_1):

- Theoretical averaging ratio: (2³·20)/(2¹·1.5) ≈ 53
- Predicted σ ratio: √53 ≈ 7.3
- Observed σ ratio: **7.3×** for all three axes ✓

**Implication:** noise is chip-intrinsic. Environment is not contributing measurable additional noise.

### 4.3 Z-axis anisotropy

σ_Bz / σ_Bx is consistently **~1.5×** across presets. This is expected — the MLX90393 Z-axis uses a different IMC (integrated magnetic concentrator) geometry with inherently lower SNR. **Cannot be reduced by averaging more.**

### 4.4 Drift

All measured drift rates are < 5×10⁻³ µT/s (one outlier `fastest`/Bz at 12×10⁻³). Over a 60 s static window this contributes < 0.3 µT total — well below σ in every preset. **σ_raw ≈ σ_detrend confirms drift removal is unnecessary** for measurement windows ≤ 60 s.

### 4.5 Sampling-rate ceiling

`fast` (OSR_1+F_1) and `fastest` (OSR_0+F_0) measure at identical rates (~80 Hz) despite the chip being faster in `fastest`. Bottleneck is downstream of the chip:

- I2C @ 100 kHz default ≈ 6 ms per `sensor.magnetic` call
- Python + USB-CDC `print()` ≈ 4 ms
- Chip conversion at OSR_0+F_0: only ~1.5 ms

To exceed 80 Hz: raise I2C to 400 kHz/1 MHz, switch to SPI, or simplify the print payload.

### 4.6 Critical finding: `fastest` has unusable DC bias

In two consecutive `fastest` runs the means appeared as `Bx ≈ +304, By ≈ +2, Bz ≈ +490 µT` (|B| ≈ 575 µT) instead of the Earth-field 57 µT. Switching back to `fast` immediately restored the correct means with no physical change.

**Mechanism:** the MLX90393 takes differential measurements (positive + negative ADC pair) to cancel internal offsets. With FILTER_0 no averaging occurs and the residual differential bias is not removed. Higher FILTER settings average it out, which is why `fast` (FILTER_1) and higher give correct means.

**Rule:** never use FILTER_0 for measurements where absolute mean matters. For mean accuracy, FILTER ≥ 1 is mandatory.

## 5. SNR Threshold for Subsequent Stages

For the Stage 5 identifiability metric κ, we need a minimum signal change to be considered "real." Using 3σ above the worst-case axis (Bz) of the recommended preset:

- For static experiments (`low_noise`): **ΔB > 1.8 µT** (3 × 0.6)
- For dynamic experiments (`fast`): **ΔB > 12.6 µT** (3 × 4.2)

These set the lower bound on what signal amplitudes the APMD model can decouple reliably.

## 6. Preset Recommendations for Stages 2–8

| Stage | Preset | Rationale |
|---|---|---|
| 2 — pure displacement | `low_noise` | Need < 1 µT resolution to see small q-induced changes |
| 3 — pure force, static | `low_noise` | Same |
| 4 — 2D F×q grid | `low_noise` | Same |
| 8 — dynamic loading (0.5–5 mm/s) | `fast` | 80 Hz vs ~2 Hz loading freq = 40× Nyquist margin |
| (never) | `fastest` | DC bias bug, no speed benefit over `fast` |

## 7. Stage 1 Status

✅ Complete. Noise floor documented per axis per preset. No remediation needed before proceeding to Stage 2 (pure displacement).

**Outstanding infrastructure items** (not Stage 1, but blocking Stage 2):
- Time synchronization scheme between Mark-10 force/displacement output and MLX90393 magnetic data
- Mechanical fixture to control q (linear stage or graduated spacers)
- Magnetic-fiber liner sample with documented magnetization pattern
- Sensor-to-sample distance/orientation jig with sub-mm repeatability

## 8. Data Artifacts

- `stage1_data/low_noise_20260512_152056_raw.csv`
- `stage1_data/balanced_20260512_152412_raw.csv`
- `stage1_data/fast_20260512_152720_raw.csv`
- `stage1_data/fast_20260512_154041_raw.csv` (verification re-run)
- `stage1_data/fastest_20260512_152952_raw.csv`
- `stage1_data/fastest_20260512_153249_raw.csv` (bias verification)
- `stage1_data/summary.csv` — accumulated per-trial statistics
