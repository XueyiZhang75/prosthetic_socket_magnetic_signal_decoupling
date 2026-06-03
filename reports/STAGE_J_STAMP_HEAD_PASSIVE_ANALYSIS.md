# Stage J Stamp-Head Fixed-Force Passive Analysis

First-look session: `session_20260603_093056`

Role in rerun: passive fixed-`F` contrast before Stage J+ same-`F` /
different-`d` path excitation.

## Configuration

- Head ID: `stamp_head_v1`
- Force calibration ID: `force_calibration_20260602_190856`
- Displacement zero ID: `stageD_session_20260602_201421`
- Target force: `F_target = 1.80 N`
- Hold duration: `120 s`
- Trials in this first-look run: `1`
- Formal passive rerun setting after review: `N_TRIALS = 3`
- Depth soft limit: `2.20 mm`
- Force hard limit: `5.0 N`
- No-contact live-tare check: `live_tare_N = -2.8284 N`
- B0: `(-779.52, +5021.92, +3094.61) uT`

## Run Summary

- Contact change point: descent `0.390 mm`, `F = 0.2378 N`.
- Target acquisition: reached `F = 1.816 N` at `d = 1.400 mm` after
  `15` iterations.
- Fixed-force hold: `n = 120` rows after skipping the first second for plotting.
- Force mean: `1.778 N`.
- Force standard deviation: `8.0 mN`.
- Mean force error: `-21.5 mN`.
- Control corrections: `27` downward nudges.
- Displacement change, first-to-last: `Delta d = +0.5200 mm`.
- Magnetic magnitude change, first-to-last: `Delta |B| = -5.6 uT`.
- 3-axis magnetic vector change, first-to-last: `||Delta B|| = 8.0 uT`.
- Head/tail mean comparison: `Delta d = +0.293 mm`,
  `Delta |B| = -2.3 uT`, `||Delta B|| = 2.6 uT`.
- Linear diagnostic from `plot_stage_J.py`: `d|B|/dd = -0.3 uT/mm`,
  `R2 = 0.00`.

Figures generated:

- `reports/figs/J_main.png`
- `reports/figs/J_3axis.png`
- `reports/figs/J_jq.png`

## Interpretation

This first-look Stage J run held force well enough to validate the passive
fixed-`F` protocol. The force stayed close to the `1.80 N` target, with
`8.0 mN` standard deviation and a mean bias of about `-21.5 mN`. The controller
had to move the stamp head downward repeatedly, producing a large
actuator-displacement creep of about `0.52 mm`.

However, this large stamp-head displacement did not produce a strong magnetic
response. `|B|` changed only a few microtesla, and the fitted `|B|-d` relation
had essentially no explanatory power (`R2 = 0.00`). This means the passive
fixed-force hold mainly drove macroscopic stamp-head/sample deformation, not a
clear local magnet-sensor displacement signal.

This is useful first-look contrast, not a failed run. It supports the refined
project story: passive relaxation/creep alone can produce mechanical state
changes, but does not necessarily create a clean magnetic decoupling excitation.
However, because this run has only one trial, it should not be treated as the
formal Stage J evidence package. Stage J has been updated to use three trials
before proceeding to the final Stage J+ interpretation.

## Caveat

The absolute B0 in this session differs noticeably from the previous day's I/I+
sessions. Treat Stage J as a within-session passive contrast and avoid comparing
absolute magnetic offsets across days without normalization. The within-session
conclusion remains valid because the weak `Delta B` is evaluated during the same
hold against the same B0.

## Decision

The single-trial Stage J run is accepted as a protocol check and first-look
contrast, but not as the formal passive evidence package. Rerun Stage J with
`N_TRIALS = 3` at the same target force, `F_target = 1.80 N`. If the repeated
trials show the same pattern, then proceed to Stage J+ with the pairwise
loading/unloading design to test whether path excitation creates a stronger
same-`F` magnetic contrast.

## Formal Rerun Attempt

`session_20260603_094854` was a 3-trial formal rerun attempt but is not accepted
as the Stage J evidence package. Trial 1 ran but stayed below target on average.
Trial 2 did not collect a hold because reset-to-start triggered a downward
overshoot from an already above-start position. Trial 3 completed but contained
two large force outliers (`2.756 N` and `1.387 N`). The Stage J script was
therefore updated to skip downward start trimming when already at/above the
no-contact start and to recheck/reacquire force after the 5 s pre-hold settle.

`session_20260603_100748` was aborted before collecting a hold. During contact
search, the precontact abort guard fired at `F = 1.5568 N` before the contact
baseline was established. This indicates the start position was still too close
to the sample/contact state. The next rerun should start about `7 mm` above the
physical lower limit with a clearly visible air gap.
