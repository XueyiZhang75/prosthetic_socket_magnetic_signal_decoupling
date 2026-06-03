# Stage N - Normal Force-Displacement Identifiability Readiness

Generated from `decouple_data`.

**Gate verdict:** NOT READY

This report implements the v1 claim: test whether three-axis magnetic data contain separable information for normal force `F` and normal displacement/gap `d/q` in a fixed benchtop geometry.

## Executive Checks

| Check | Verdict | Main finding |
|---|---:|---|
| Small-q Stage C | FAIL | Latest Stage C session session_20260520_161359 covers q=60.00-140.00 mm. |
| Stage D/E safety consistency | FAIL | Stage E/F observed F_max=3.055 N exceeds recommended F_max=1.146 N. |
| Same-d different-F evidence | PASS | 22 matched loading/unloading points provide same-d different-F evidence. |
| I+/J+ pair-column evidence | PASS | Pair-column angle=80.2 deg (abs cosine=0.17) from I+ j_F and J+ j_d estimates. |
| Stage I j_F evidence | FAIL | 0/9 hold files pass the excursion and linearity gate. |
| Stage J j_q evidence | FAIL | 0/2 hold files pass the excursion and linearity gate. |
| Local Jacobian windows | FAIL | 2/3 displacement windows have usable local J metrics. |
| Global exploratory Jacobian | PASS | Fit used 122 E/F/H plateau rows with RMSE=503.7 uT. |

## Details

### Small-q Stage C: FAIL
- Latest Stage C session session_20260520_161359 covers q=60.00-140.00 mm.
- Current compression data reach d~4.29 mm.
- This is a far-field calibration, so it is process evidence only; it should not be used as the main working-zone q calibration.

### Stage D/E safety consistency: FAIL
- Stage E/F observed F_max=3.055 N exceeds recommended F_max=1.146 N.

### Same-d different-F evidence: PASS
- 22 matched loading/unloading points provide same-d different-F evidence.
- Mean |delta F|=0.190 N; mean |delta |B||=59.2 uT.

### I+/J+ pair-column evidence: PASS
- Pair-column angle=80.2 deg (abs cosine=0.17) from I+ j_F and J+ j_d estimates.
- I+ (session_20260601_160931): 3/3 usable pairs, median |delta B3|=140.6 uT.
- J+ (session_20260602_103531): 4/6 usable pairs, median |delta B3|=820.1 uT.
- Median j_F=(30.8, -88.4, 267.2) uT/N; median j_d=(-552.2, 3299.2, 544.5) uT/mm.
- The pair-column directions are well separated; this supports local identifiability.

### Stage I j_F evidence: FAIL
- 0/9 hold files pass the excursion and linearity gate.
- I_hold_disp_100_rep1: Best magnetic-vs-F_N R2=0.15; not strong enough for a Jacobian column.
- I_hold_disp_100_rep2: Best magnetic-vs-F_N R2=0.14; not strong enough for a Jacobian column.
- I_hold_disp_100_rep3: Best magnetic-vs-F_N R2=0.17; not strong enough for a Jacobian column.
- I_hold_disp_75_rep1: Best magnetic-vs-F_N R2=0.07; not strong enough for a Jacobian column.
- I_hold_disp_75_rep2: Best magnetic-vs-F_N R2=0.22; not strong enough for a Jacobian column.
- I_hold_disp_75_rep3: Best magnetic-vs-F_N R2=0.14; not strong enough for a Jacobian column.
- I_hold_disp_90_rep1: Best magnetic-vs-F_N R2=0.02; not strong enough for a Jacobian column.
- I_hold_disp_90_rep2: Best magnetic-vs-F_N R2=0.12; not strong enough for a Jacobian column.
- I_hold_disp_90_rep3: Best magnetic-vs-F_N R2=0.11; not strong enough for a Jacobian column.

### Stage J j_q evidence: FAIL
- 0/2 hold files pass the excursion and linearity gate.
- J_hold_force_200_rep1: Best magnetic-vs-d_actual_mm R2=0.01; not strong enough for a Jacobian column.
- J_hold_force_250_rep1: Best magnetic-vs-d_actual_mm R2=0.07; not strong enough for a Jacobian column.

### Local Jacobian windows: FAIL
- 2/3 displacement windows have usable local J metrics.
- d~1.05 mm: n=26, angle=29.7 deg, cond=7.43, state-cond=7.74, RMSE=244.3 uT.
- d~2.10 mm: n=33, angle=40.9 deg, cond=5.31, state-cond=3.29, RMSE=287.0 uT.
- d~2.91 mm: n=36, angle=18.1 deg, cond=6.45, state-cond=2.47, RMSE=445.8 uT.

### Global exploratory Jacobian: PASS
- Fit used 122 E/F/H plateau rows with RMSE=503.7 uT.
- j_F=(-113.7, -1679.6, 766.6) uT/N.
- j_d=(-1.5, -82.4, -273.6) uT/mm.
- Jacobian angle=82.3 deg, condition=6.54.
- State-space design condition=3.62.
- The fitted columns are numerically invertible, pending local/blind validation.

## Pair-Column Evidence

| Source | Usable pairs | Column estimate | Median signal | Median denominator |
|---|---:|---|---:|---:|
| I+ (session_20260601_160931) | 3/3 | (30.8, -88.4, 267.2) uT/N | 140.6 uT | 0.4826 |
| J+ (session_20260602_103531) | 4/6 | (-552.2, 3299.2, 544.5) uT/mm | 820.1 uT | 0.2400 |

## Hold Diagnostics

| Stage | File | Samples | Excursion | Best axis | Best R2 | Verdict |
|---|---|---:|---:|---|---:|---:|
| I | `I_hold_disp_100_rep1` | 1364 | 0.1333 N | By | 0.15 | FAIL |
| I | `I_hold_disp_100_rep2` | 1366 | 0.1361 N | By | 0.14 | FAIL |
| I | `I_hold_disp_100_rep3` | 1365 | 0.1268 N | By | 0.17 | FAIL |
| I | `I_hold_disp_75_rep1` | 1365 | 0.2600 N | Bz | 0.07 | FAIL |
| I | `I_hold_disp_75_rep2` | 1365 | 0.0499 N | Bz | 0.22 | FAIL |
| I | `I_hold_disp_75_rep3` | 1365 | 0.0438 N | Bz | 0.14 | FAIL |
| I | `I_hold_disp_90_rep1` | 1365 | 2.0815 N | Bz | 0.02 | FAIL |
| I | `I_hold_disp_90_rep2` | 1365 | 0.0904 N | By | 0.12 | FAIL |
| I | `I_hold_disp_90_rep3` | 1365 | 0.0803 N | By | 0.11 | FAIL |
| J | `J_hold_force_200_rep1` | 1627 | 0.9600 mm | Bx | 0.01 | FAIL |
| J | `J_hold_force_250_rep1` | 44 | 0.7600 mm | Bz | 0.07 | FAIL |

## Local Jacobian Windows

| Center d | Samples | j_F (uT/N) | j_d (uT/mm) | Angle | Cond | State Cond | RMSE | Verdict |
|---:|---:|---|---|---:|---:|---:|---:|---:|
| 1.05 mm | 26 | (-195.7, -591.7, 1738.9) | (-18.6, -398.5, 354.9) | 29.7 | 7.43 | 7.74 | 244.3 | PASS |
| 2.10 mm | 33 | (10.0, -1468.4, 309.6) | (-74.6, -396.0, -210.7) | 40.9 | 5.31 | 3.29 | 287.0 | PASS |
| 2.91 mm | 36 | (-179.5, -3594.6, 3960.2) | (91.2, 1750.0, -3904.4) | 18.1 | 6.45 | 2.47 | 445.8 | FAIL |

## Required Next Experiments

1. Repeat small-q Stage C in the actual compression working zone; do not train the decoupling model on the far-field q=60-140 mm calibration.
2. Repeat Stage D/E in one unchanged setup and keep all subsequent loading below the conservative force and displacement limits.
3. Use the I+ and J+ pair protocols as the current primary `j_F`/`j_d` evidence; do not rely on passive Stage I/J holds alone.
4. Fit a local Jacobian around the I+/J+ working region and check whether the pair-derived columns remain separated from the E/F/H exploratory fit.
5. Only after these gates pass, run a separate blind test against single-variable baselines.

## Normalized Data Contract

The analysis normalizes existing E/F/H rows into: `stage, session, source_file, phase, control_mode, F_N, d_mm, q_mm, delta_Bx_uT, delta_By_uT, delta_Bz_uT`.
Current normalized plateau-like rows: 122.
