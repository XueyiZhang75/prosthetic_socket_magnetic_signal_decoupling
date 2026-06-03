# Blind-Test Protocol v2

This protocol separates the current pilot blind test from the final
confirmatory blind test.

The narrow question is:

> After fitting only calibration sessions from a declared work zone, can
> magnetic data `B=[Bx, By, Bz]` estimate both normal force `F` and displacement
> `d` on a held-out session better than single-variable baselines?

Do not reuse a calibration session as a real blind session. You may reuse one
only as a software smoke test.

## O1 vs O2

### O1: pilot blind test

O1 is the current clip-head feasibility blind test. It is allowed to fail. Its
purpose is to expose issues in geometry repeatability, training coverage,
normalization, path control, and model scope.

The current O1 result is preserved in:

```text
reports/BLIND_TEST_ANALYSIS.md
```

Do not overwrite that report manually. If the script is rerun, treat the output
as a new generated result.

### O2: confirmatory blind test

O2 is the final stamp-head blind test. It can only be run after:

- Pre-flight force calibration, tare, displacement zero, MLX preset, and
  metadata checks pass.
- Stage B confirms acceptable B0/no-contact drift and stage-motion baseline.
- Stage C covers the actual compression work zone.
- Stage D defines conservative `F_max` and `d_max`.
- Stage F/G show repeatable path behavior after precycling.
- Stage X1/X2/X3 control geometry error, recovery time, and preload strength.
- Stage I+/J+ provide usable local `j_F` and `j_d` evidence.
- Stage N declares a green work zone before blind scoring.

O2 points must be chosen inside the declared green work zone. The blind session
must not be used for normalization, tuning, target selection after seeing
errors, model choice, or green-zone selection.

## Calibration Data

For O1, the current pilot training sessions are:

```text
session_20260601_160931
session_20260602_103531
```

For O2, use only stamp-head calibration sessions collected after the final
geometry reset. Do not mix clip-head and stamp-head data in the final model
unless the analysis explicitly treats `head_id` as a separate domain and the
claim is downgraded to cross-head exploratory analysis.

The force calibration used to label `F_N` must be fixed before the O2
calibration set starts. The same `force_calibration_id` should be used for the
calibration sessions and the blind session. If a force recalibration is needed
between calibration and blind acquisition, either recompute all force labels
consistently from raw data or restart the O2 calibration set.

Training data should include:

- I+ same-`d`, different-`F` state pairs for `j_F`.
- J+ same-`F`, different-`d` state pairs for `j_d`.
- Optional Stage F/L matched path pairs inside the same green work zone.
- Baseline Stage E/F data for `F=h(d)` and `d=g(|B|)` comparison.

## O2 Blind Session Design

Run O2 on a different day or after a full reset, but keep the same stamp head,
sample, magnet, MLX position, force sensor, tare convention, and contact
definition as the calibration runs.

Use randomized or semi-random target states inside the Stage N green zone:

- 10-20 blind state points minimum.
- Both direct loading and unloading-after-preload paths.
- At least 3 target depths or force levels, not one narrow line.
- Mixed order, not monotonic low-to-high.
- At least 10-20 s recording per state.
- No blind point outside the declared green zone.

The preload step is used only to create a different path/internal state. It is
not itself scored unless it was declared as a blind target before acquisition.

## Recommended O2 Target Logic

Prefer green-zone sampling over fixed historical values. If Stage N says the
usable region is around `d=4.2-4.8 mm` and `F=1.6-2.3 N`, choose targets such
as:

```text
loading state at low/mid/high green-zone force
unloading state matched to the same force after preload
intermediate states that test interpolation, not extrapolation
```

The actual numeric targets must be written into the lab notebook before the run.

## Data Contract

The analysis script reads state-level time-series CSVs matching these names:

```text
Iplus_same_d_*_rep*.csv
Jplus_same_F_*_rep*.csv
Blind_*_rep*.csv
O_blind_*_rep*.csv
```

Each row should contain at least:

```text
t_rel_s, F_N, d_mm, delta_Bx_uT, delta_By_uT, delta_Bz_uT
```

Optional but recommended:

```text
Bmag_uT, state_label, trial, pair_id, target_label,
path_mode, head_id, sample_id, magnet_id,
force_calibration_id, displacement_zero_id
```

If `d_mm` is missing, `d_actual_mm` is accepted. If `Bmag_uT` is missing, the
script uses the norm of the three delta-B components for the scalar baseline.

## Analysis Command

For O1 pilot reruns:

```powershell
python blind_test_analysis.py `
  --train-session session_20260601_160931 `
  --train-session session_20260602_103531 `
  --blind-session session_YYYYMMDD_HHMMSS
```

For O2 confirmatory analysis, replace all sessions with stamp-head sessions:

```powershell
python blind_test_analysis.py `
  --train-session session_STAMP_CAL_1 `
  --train-session session_STAMP_CAL_2 `
  --blind-session session_STAMP_BLIND
```

Output:

```text
reports/BLIND_TEST_ANALYSIS.md
```

If preserving the O1 report is important, copy or rename the generated report
before running O2 analysis.

## Models Compared

The report must include:

- Main model: `Bxyz -> [F, d]` or local APMD inverse.
- Force baseline: `F=h(d)`.
- Displacement baseline: `d=g(|B|)`.
- Mean baseline.

For the final claim, the preferred main model is the APMD/local-J model from
Stage N, not an unrestricted black-box model chosen after viewing blind errors.

## Acceptance Rule

O2 passes only if:

- Force calibration and tare were frozen before the blind run, and the blind
  data were not used to adjust force labels.
- The green zone was declared before blind scoring.
- `Bxyz/APMD -> F` has lower force MAE than `F=h(d)`.
- `Bxyz/APMD -> d` has lower displacement MAE than `d=g(|B|)`.
- Errors are physically reasonable relative to the force and displacement
  range used in the blind session.
- The blind data were not used to choose the model, tune parameters, adjust
  preprocessing, or change the reported work zone.

If the model beats one output but not the other, the result is still useful but
the final claim must be downgraded to partial separability.
