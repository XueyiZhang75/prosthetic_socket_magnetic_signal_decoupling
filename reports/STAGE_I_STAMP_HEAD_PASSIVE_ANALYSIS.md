# Stage I Stamp-Head Passive Fixed-Displacement Analysis

Session: `session_20260602_203043`

Role in rerun: passive fixed-`d` contrast for Stage I+ path excitation.

## Configuration

- Head ID: `stamp_head_v1`
- Force calibration ID: `force_calibration_20260602_190856`
- Displacement zero ID: `stageD_session_20260602_201421`
- Target displacement: `d_target = 1.60 mm`
- Actual displacement: `d_actual = 1.59 mm`
- Hold duration: `120 s`
- Trials: `3`

## Results

Values below compare the median of the first 10 s and last 10 s of each hold.

| Rep | d_actual (mm) | Delta F (N) | Delta |B| (uT) | Delta Bvec (uT) | Full-hold Bmag/F slope (uT/N) |
|---:|---:|---:|---:|---:|---:|
| 1 | 1.590 | -0.0951 | -3.96 | 3.16 | +31.46 |
| 2 | 1.590 | -0.0848 | -3.72 | 3.06 | +36.21 |
| 3 | 1.590 | -0.0910 | -2.43 | 2.13 | +25.17 |

## Interpretation

The passive fixed-displacement hold produced measurable force relaxation
(`~85-95 mN`) but only very small magnetic changes (`Delta Bvec ~2-3 uT`).
The magnetic response is close to the short-term point-to-point `|B|` jitter
observed in the raw stream (`~3 uT` median adjacent change), so this passive
path does not provide a strong or reliable `j_F` column.

This is useful negative/contrast evidence: in the same stamp-head work zone,
passive relaxation is too weak as an excitation, motivating Stage I+ where the
same target displacement is revisited after a preload path to create a larger
same-`d`/different-`F` split.

## Decision

Stage I passive contrast is complete and usable as the weak-path comparison.
Proceed to Stage I+ with:

- `D_TARGETS_MM = [1.60]`
- `D_PRELOAD_MM = 1.90`
- `N_TRIALS = 3`
