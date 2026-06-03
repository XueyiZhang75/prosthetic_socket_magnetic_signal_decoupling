# Normal Force-Displacement Identifiability Protocol v2

This protocol is the executable gate for the v2 APMD plan. It keeps the claim
narrow:

> In one fixed benchtop geometry and one defined normal-contact work zone, test
> whether three-axis magnetic data contain separable information for normal
> force `F` and normal displacement/gap `d/q`.

It does not claim full prosthetic socket readiness, shear sensing, curved-liner
performance, temperature robustness, or long-term drift compensation.

## Scientific Claim

The contribution is not a single `B-F` calibration curve. The claim is:

```text
controlled path excitation
  -> same-d / different-F and same-F / different-d state pairs
  -> local J=[j_F, j_d]
  -> a work-zone map showing where F and d are locally decouplable
```

Passive creep/relaxation can be diagnostic, but the current primary evidence
comes from active path-pair protocols:

- `I+`: same `d`, different `F` -> estimates `j_F = dB/dF | d`.
- `J+`: same `F`, different `d` -> estimates `j_d = dB/dd | F`.

## Command

Run the current readiness audit:

```powershell
python identifiability_analysis.py
```

Outputs:

- `reports/STAGE_N_identifiability_readiness.md`
- `reports/identifiability_summary.csv`

Run the held-out blind-test analysis after a separate blind session exists:

```powershell
python blind_test_analysis.py --train-session session_20260601_160931 --train-session session_20260602_103531 --blind-session session_YYYYMMDD_HHMMSS
```

See `reports/BLIND_TEST_PROTOCOL.md` for O1/O2 blind-session rules.

## Data Contract

The analysis normalizes plateau-like and path-pair rows into:

```text
stage, session, source_file, phase, path_mode, control_mode,
F_N, d_mm, q_mm,
delta_Bx_uT, delta_By_uT, delta_Bz_uT,
head_id, sample_id, magnet_id,
force_calibration_id, displacement_zero_id
```

For future data, keep this interface stable even if acquisition scripts store
extra fields.

## Gate Order

1. Pre-flight calibration gate: force sensor raw-to-N calibration, tare,
   displacement zero, MLX preset, serial ports, and metadata are frozen before
   the calibration session starts.
2. Force-label gate: the force calibration covers the planned working force
   range, has acceptable residuals/hysteresis, and is identified by a
   `force_calibration_id` carried by all calibration and blind sessions.
3. Geometry gate: the compression head, sample, magnet, and MLX geometry are
   fixed for the whole calibration set. For the final confirmatory run, the
   stamp-style head must be treated as a new geometry and all gates restart.
4. Baseline gate: Stage B must show acceptable B0, no-contact drift, and
   stage-motion disturbance before and after the session.
5. Working-zone Stage C gate: pure-displacement `B(q)` must cover the actual
   compression work zone. Far-field q=60-140 mm data are process evidence only.
6. Safety gate: Stage D/E must share one unchanged setup, and all later loading
   must stay below the conservative `F_max` and `d_max`.
7. Path-stability gate: Stage F/G must show repeatable loading/unloading path
   behavior after precycling; otherwise add precycles or recovery time.
8. Geometry-falsification gate: repeated contact at nominally identical `F,d`
   must not create magnetic jumps comparable to I+/J+ signals.
9. `j_F` gate: same-`d`, different-`F` evidence must exist from Stage I+ or an
   equivalent active path-pair protocol. Passive Stage I can support the story
   but does not replace I+.
10. `j_d` gate: same-`F`, different-`d` evidence must exist from Stage J+ or an
   equivalent active path-pair protocol. Passive Stage J can support the story
   but does not replace J+.
11. Local Jacobian gate: `J=[j_F, j_d]` must be numerically invertible in at
   least one declared green work zone.
12. Blind gate: O2 confirmatory blind-test errors inside the green work zone
    must beat single-variable baselines for both `F` and `d/q`.

## Acceptance Metrics

- `j_F` and `j_d` are not near-collinear.
- Jacobian condition number is below the analysis threshold.
- Each column causes magnetic changes above the relevant 3-sigma noise floor.
- Force calibration max residual is below the pre-declared tolerance, for
  example `max(0.03 N, 2% working F range)`, and zero drift is small relative to
  I+/J+ force splits.
- I+ pairs satisfy same-`d` tolerance and have sufficient `ΔF`.
- J+ pairs satisfy same-`F` tolerance or use force-matched interpolation, and
  residual `ΔF` is corrected with the local I+ `j_F` estimate.
- The green work zone is declared before O2 blind-test scoring.
- O2 blind-test errors for both `F` and `d/q` beat:
  - `F=h(d)` for force.
  - `d=g(|B|)` for displacement.
  - mean baseline as a sanity check.

## Current Status

Current clip-head data are useful pilot evidence. The live readiness report
shows:

- I+/J+ pair-column evidence supports local identifiability.
- Passive I/J holds remain diagnostic failures.
- Stage C and safety consistency still need confirmatory reruns.
- The first O1 pilot blind test did not pass.

Therefore the final readiness gate is not yet open. The next decisive step is a
stamp-head confirmatory run following `EXPERIMENT_PLAN.md` v2.
