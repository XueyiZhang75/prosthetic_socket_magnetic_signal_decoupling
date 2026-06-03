# Stamp-Head Key Rerun Protocol

This is the ultra-minimal rerun after replacing the clip-style head with the
stamp-style 3D-printed head. It is not a full A-P confirmatory run.

## Goal

Show that the revised APMD storyline survives the head change:

```text
stamp head reduces geometric ambiguity
  -> path excitation still creates same-d/different-F and same-F/different-d pairs
  -> I+ and J+ columns are both above noise
  -> local j_F and j_d are not collinear
```

The target deliverable is one quick N-mini report:

```text
reports/STAMP_HEAD_KEY_RERUN_ANALYSIS.md
```

## Do Not Run Yet If

- Force channel has not been tared or quick-checked after reassembly.
- The new head contact point is not defined.
- The new head can slip, rotate, or hit the sensor.
- The planned I+/J+ depth exceeds the quick safety check.
- B0 is drifting visibly before loading.

## Minimal Run Order

```text
1. Pre-flight quick checks
2. D-map contact/F-d-B mapping
3. Stage I passive fixed-d hold at the I+ target depth
4. Stage I+ same-d/different-F path excitation
5. Stage J passive fixed-F hold at the J+ target force
6. Stage J+ same-F/different-d path excitation
7. N-mini pair-column analysis
```

## 1. Pre-flight Quick Checks

### Force quick check

Minimum:

- Warm up force electronics for 10-15 min if possible.
- Tare with no load.
- Check 2-3 known loads or equivalent standard contacts.
- Confirm the force reading is not obviously biased.

For the stamp-head rerun, use the same calibration route as the previous force
calibration:

- Remove or flip the force-sensor + stamp-head assembly so the stamp face points
  upward.
- Apply known weights directly on the stamp face, along the same local sensing
  direction that sample contact will use after reinstalling.
- Run `python force_calibration.py [COMx]`.
- Paste the printed `TARE_OFFSET` and `CALIBRATION_FACTOR` into
  `uno_force/uno_force.ino`, then upload the sketch to the UNO.
- Reinstall the assembly, perform a software live tare in the experimental
  orientation, and lightly press the stamp head to confirm the tared force
  becomes positive.

The reinstalled orientation may shift the zero offset because the stamp-head
weight changes sign relative to gravity. This is acceptable if the post-install
live tare is stable and contact force has the correct sign.

Record:

```text
force_calibration_id = force_quick_YYYYMMDD
tare_raw or live_tare_N
known-load readings
```

If the quick check fails, stop and redo full force calibration before running
I+/J+.

### Metadata

Before running scripts, set or record:

```text
head_id = stamp_head_v1
sample_id = <current sample>
magnet_id = <current magnet>
force_calibration_id = force_quick_YYYYMMDD
displacement_zero_id = contact_YYYYMMDD
```

The I/J/I+/J+ scripts now write these fields when their constants are filled.

## 2. D Quick Contact/Safety

Purpose:

- Define `d=0` for the stamp head using a force change point.
- Map the full safe `F-d-B` curve until the configured physical lower limit.
- Use the full curve to choose I+ depth/preload and J+ force/depth caps.

Minimum:

- Run `stageD_safety_range.py` with the stamp-head quick settings:
  `APPROACH_STEP_MM = 0.1`, `F_CONTACT_N = 0.080`
  as the required force rise from the no-contact rolling baseline,
  `CONTACT_STEP_DELTA_N = 0.015`, `CONTACT_SLOPE_N_PER_MM = 0.12`,
  `PROBE_STEP_MM = 0.1`, `PROBE_STOP_MODE = "physical_limit"`,
  `PROBE_FORCE_MARKER_N = 2.2`, `F_HARD_LIMIT_N = 8.0`,
  `PROBE_MAX_DEPTH_MM = 12.0`.
- Contact is a force change point, not an absolute-force threshold. With the
  current setup, the script accepts the change point automatically after start.
- Set the physical lower limit to the maximum safe compression/depth for this
  sample/head setup. Phase B records every step automatically until this lower
  limit, MLX saturation, emergency force limit, or the software depth backstop.
- `2.2 N` is only a force marker in the output/log, not a stopping target.

Output:

```text
d_safe_quick
F_safe_quick
chosen I+ d_target
chosen preload depth
chosen J+ force target(s)
```

## 3. B0 Quick Check

Before I+ and after J+, record no-contact B0 for 30-60 s or use the script's
startup B0 capture. If B0 changes by a magnitude comparable to I+/J+ pair
signals, stop and diagnose drift.

## 4. Stage I Passive Contrast

Purpose:

- Repeat the original fixed-displacement hold in the same stamp-head work zone.
- Show whether passive relaxation alone creates enough `F` and `B` variation.
- Provide the contrast for Stage I+.

Current stamp-head config:

```python
N_TRIALS = 3
D_HOLDS = [(160, 1.60)]
HOLD_S = 120.0
F_HARD_LIMIT_N = 5.0
```

Run:

```powershell
python .\stageI_hold_disp.py
```

## 5. I+ Minimal Rerun

Use:

```powershell
python .\stageI_plus_same_d_diff_f.py
```

Current stamp-head config:

```python
N_TRIALS = 3
D_TARGETS_MM = [1.60]
D_PRELOAD_MM = 1.90
F_HARD_LIMIT_N = 5.0
HEAD_ID = "stamp_head_v1"
FORCE_CALIBRATION_ID = "force_calibration_20260602_190856"
DISPLACEMENT_ZERO_ID = "stageD_session_20260602_201421"
```

Pass target:

- At least 2 strong I+ pairs.
- Prefer 3 or more.
- `|delta d| <= 0.03-0.05 mm`.
- `|delta F| >= 0.2 N` if possible.
- `delta_Bvec` above dynamic noise.

## 6. Stage J Passive Contrast

Purpose:

- Repeat the original fixed-force hold in the same stamp-head work zone.
- Show whether active/passive force holding alone creates a useful
  same-F/different-d contrast.
- Provide the contrast for Stage J+.

Current stamp-head config:

```python
START_CLEARANCE_GUIDE_MM = 7.0
N_TRIALS = 3
F_HOLDS = [(180, 1.80)]
HOLD_S = 120.0
D_SOFT_LIMIT_MM = 2.20
F_HARD_LIMIT_N = 5.0
```

Run:

```powershell
python .\stageJ_hold_force.py
```

Implementation notes after `session_20260603_094854`:

- If the crosshead is already at or above the no-contact start position, Stage J
  skips the downward trim-to-zero move. This avoids a downward overshoot during
  the reset phase when the previous retract ended slightly above zero.
- After the 5 s pre-hold settle, Stage J rechecks force immediately before
  recording. If the settled force has relaxed outside the hold tolerance, it
  reacquires the `1.80 N` target before starting the timed hold.
- After `session_20260603_100748`, use a more conservative no-contact start:
  set the crosshead about `7 mm` above the physical lower limit with a clearly
  visible gap before starting the script. The `15 mm` approach backstop remains
  sufficient and does not need to change.
- If the force live-tare baseline is shifted from the historical `-2.9 N`
  value but a clear visual gap is confirmed, Stage J may ask for an explicit
  `YES` confirmation to accept the shifted baseline for that session. Use this
  only when the stamp head is visibly not touching the sample and no fixture or
  cable is preloading the force sensor.
- Do not override an unstable live tare. If the live-tare sample standard
  deviation is large, or the min/max range jumps by hundreds of mN to >1 N, stop
  and let the force chain settle; check cable pull, fixture side-load, and
  whether the load cell/head assembly is mechanically relaxed. Stage J now
  rejects unstable live-tare statistics before offering the visual-gap override.
- If the live-tare median is stable and close to the historical no-contact
  baseline, but rare force-channel outliers inflate the sample standard
  deviation/range, Stage J continues with the robust median tare and records
  fixed-force hold rows using a short-window median force reading instead of a
  single force sample.

## 7. J+ Minimal Rerun

Use:

```powershell
python .\stageJ_plus_same_f_diff_d.py
```

Current stamp-head config:

```python
N_TRIALS = 3
F_TARGETS = [(180, 1.80)]
D_PRELOAD_EXTRA_MM = 0.30
D_PRELOAD_MAX_MM = 2.00
D_SOFT_LIMIT_MM = 2.20
F_HARD_LIMIT_N = 5.0
HEAD_ID = "stamp_head_v1"
FORCE_CALIBRATION_ID = "force_calibration_20260602_190856"
DISPLACEMENT_ZERO_ID = "stageD_session_20260602_201421"
```

Pass target:

- At least 3 usable J+ pairs preferred.
- `|delta F| <= 0.05-0.08 N` preferred.
- `|delta d| >= 0.15-0.20 mm`.
- `delta_Bvec` above dynamic noise.

If only 2 J+ pairs pass but the vector direction is clean, treat it as a
promising pilot, not final evidence.

## 8. N-mini Analysis

After I+ and J+ complete, run:

```powershell
python .\stamp_key_rerun_analysis.py `
  --iplus-session session_YYYYMMDD_HHMMSS `
  --jplus-session session_YYYYMMDD_HHMMSS
```

The script writes and prints:

```text
reports/STAMP_HEAD_KEY_RERUN_ANALYSIS.md
```

Pass target:

- I+ has at least 2 usable pairs.
- J+ has at least 3 usable pairs.
- Pair-column angle >= 30 deg.
- Condition number is finite and not obviously pathological.
- The result is interpretable as local evidence, not a full heatmap.

## Decision After the Minimal Run

### Strong

I+ and J+ both pass, angle is clearly separated, and B0 is stable.

Next: run O-mini or expand to two depths / two force targets.

### Promising but incomplete

One side passes and the other has insufficient usable pairs, but the signal is
large and the failure is a matching tolerance issue.

Next: rerun only the weak side with tighter target matching or adjusted preload.

### Not usable

B0 drift, contact drift, force label uncertainty, or geometric slip is
comparable to the path-pair signal.

Next: fix hardware/force calibration before collecting more path-pair data.
