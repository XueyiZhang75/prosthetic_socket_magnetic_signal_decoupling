# Weekly Group Meeting Summary: Stage H to Stage O

## One-Sentence Message

Since last week's Stage H force-control results, the project moved from simple
`B-F`/`B-d` correlation tests toward a stricter identifiability framework:
test whether the three-axis magnetic signal contains two separable local
directions for normal force and displacement. The current data support the
existence of separable local directions, but also reveal that the present
indenter/setup is not stable enough for a clean blind test, so the next round
will restart with a new indenter and a tighter protocol.

## What Changed After Stage H

### Stage I: Fixed-Displacement Hold

Purpose:

- Hold displacement constant and observe force relaxation.
- Intended to probe `j_F = dB/dF | d`.

Main result:

- Force relaxation was visible, but the magnetic response during passive hold
  was weak or inconsistent.
- The automated readiness report shows `0/9` Stage I hold files passed the
  excursion/linearity gate.
- Best magnetic-vs-force `R2` values were generally low, about `0.02-0.22`.

Interpretation:

- Passive relaxation alone is not a strong enough way to estimate the force
  column.
- This led to the improved I+ protocol.

### Stage I+: Same-d, Different-F Path Probe

Purpose:

- Create stronger same-displacement/different-force comparisons using path
  history:
  direct loading to target `d`, preload deeper, unload back near the same `d`.

Main result:

- I+ session `session_20260601_160931` produced `3/3` usable same-d/different-F
  pairs.
- Median magnetic vector change was about `140.6 uT`.
- Median force-column estimate:

```text
j_F = (30.8, -88.4, 267.2) uT/N
```

Interpretation:

- This is better evidence than passive Stage I that `B` contains force/path
  information even near the same displacement.

Latest repeat note:

- The later I+ repeat `session_20260602_151614` completed, but return states
  had about `0.06 mm` displacement mismatch and were flagged as `bad_d_match`.
- This suggests the current mechanical path and indenter make precise return
  to the same `d` difficult.

### Stage J: Fixed-Force Hold

Purpose:

- Hold force constant and let displacement creep/change.
- Intended to probe `j_d = dB/dd | F`.

Main result:

- The original Stage J active force hold was not stable enough.
- The readiness report shows `0/2` Stage J hold files passed the gate.
- Best magnetic-vs-displacement `R2` values were only about `0.01-0.07`.

Interpretation:

- Continuous force-hold control with the current hardware is not reliable
  enough to be the primary displacement-column evidence.
- This led to the J+ path-pair protocol.

### Stage J+: Same-F, Different-d Path Probe

Purpose:

- Create same-force/different-displacement comparisons through loading,
  preload, and unloading.

Main result:

- J+ session `session_20260602_103531` produced `4/6` usable same-F/different-d
  pairs.
- Median magnetic vector change was about `820.1 uT`.
- Median displacement-column estimate:

```text
j_d = (-552.2, 3299.2, 544.5) uT/mm
```

Key identifiability result:

- The I+ and J+ column estimates were separated by about `80.2 deg`
  (`abs cosine = 0.17`).
- This supports local identifiability: the estimated force and displacement
  directions in 3-axis magnetic space are not collinear.

Latest repeat note:

- Later J+ repeats showed that the `1.8 N` target can still generate useful
  same-F/different-d evidence.
- Example: `session_20260602_153140`, target `1.8 N`, had
  `delta_d = +0.200 mm`, `delta_F = -0.0028 N`, and
  `delta_Bvec = 456.8 uT`, verdict `strong`.
- Higher-force targets around `2.2 N` often reached very high displacement
  (`d > 4.6 mm`) and the preload step became too small or unstable, sometimes
  causing the script to stall.

Interpretation:

- J+ is scientifically useful, but the current indenter/setup makes the high-d
  preload window fragile.

### Stage O: Blind Test

Purpose:

- Train on I+/J+ calibration sessions.
- Test on a held-out blind session without using it for tuning.
- Compare `Bxyz -> [F,d]` against simple baselines:
  `F=h(d)` and `d=g(|B|)`.

Main result:

- Blind session `session_20260602_142058` did not pass:

```text
Bxyz -> F MAE = 6.31 N
baseline F=h(d) MAE = 0.96 N

Bxyz -> d MAE = 2.91 mm
baseline d=g(|B|) MAE = 0.36 mm
```

Interpretation:

- This is not evidence that magnetic decoupling is impossible.
- It shows that the training sessions and blind session were not in the same
  magnetic/mechanical state.
- For example, `delta_Bz` ranges were very different:

```text
I+ training:   delta_Bz about 4287-5655 uT
J+ training:   delta_Bz about 4251-4765 uT
Stage O blind: delta_Bz about 292-714 uT
```

That difference is too large to treat as ordinary noise. It indicates a change
in geometry, magnet orientation, baseline field, or assembly condition.

Stage O still had useful within-session evidence:

- Several loading/unloading pairs showed same-force/different-displacement
  magnetic response.
- Example within Stage O:
  `delta_d = 0.15-0.28 mm` with `delta_Bvec` roughly `323-663 uT`.

## Current Readiness Verdict

The current Stage N readiness report is still `NOT READY`.

Important pass/fail pattern:

- PASS: same-d/different-F evidence exists.
- PASS: I+/J+ pair-column evidence suggests separated `j_F` and `j_d`.
- FAIL: passive Stage I/J holds are not strong enough.
- FAIL: blind test does not pass across the current sessions.
- FAIL: small-q Stage C and safety consistency still need redesign for the
  final protocol.

## Main Scientific Takeaways

1. The original question should not be framed as "fit B directly to F and d"
   from uncontrolled data.

2. A better framing is local identifiability:

```text
Delta B = j_F Delta F + j_d Delta d + noise
```

3. I+ and J+ provide evidence that `j_F` and `j_d` are not collinear in the
   present benchtop setup.

4. However, the current experimental platform is sensitive to geometry and
   path history. A blind test only makes sense if calibration and blind data are
   collected under the same stable assembly.

5. The current indenter/setup creates practical control problems near
   `d = 4.7-4.9 mm`, especially during the preload step. This is why we are
   pausing and restarting with a different indenter.

## How To Tell The Professor

Recommended narrative:

1. "Last week I showed Stage H, where we started to see magnetic response under
   force-related loading. This week I tested whether that response can actually
   support force-displacement decoupling."

2. "The first passive designs, Stage I and Stage J, were not sufficient. They
   showed relaxation/creep, but the magnetic response was too weak or too
   inconsistent for a reliable Jacobian column."

3. "I then redesigned the experiments as controlled pairwise perturbations:
   I+ gives same-d/different-F points, and J+ gives same-F/different-d points."

4. "Those improved protocols gave a positive identifiability signal: the
   estimated `j_F` and `j_d` directions were separated by about `80 deg`, so the
   two effects are not simply collinear in the 3-axis magnetic space."

5. "The first blind test did not pass, but it revealed a setup issue rather
   than a pure model issue. The magnetic baseline/geometry changed strongly
   between calibration and blind sessions, especially in `Bz`, so the model was
   extrapolating across assemblies."

6. "The current mechanical setup also becomes unstable in high-displacement
   preload steps. I observed repeated stalls or weak preload splits near
   `d = 4.7-4.9 mm`."

7. "Therefore, the next step is to replace the indenter, restart the protocol
   from the beginning, and collect I+, J+, and O continuously in one unchanged
   setup."

## Suggested Slide Order

1. Motivation and updated hypothesis:
   `Delta B = j_F Delta F + j_d Delta d + noise`

2. Stage I/J passive holds:
   useful diagnostic, but failed as primary Jacobian evidence

3. I+ design and result:
   same-d/different-F, force-column evidence

4. J+ design and result:
   same-F/different-d, displacement-column evidence

5. Identifiability check:
   `j_F`/`j_d` angle about `80 deg`

6. Blind test:
   failed across sessions, with clear baseline/geometry mismatch

7. Experimental limitation:
   current indenter/preload control unstable near high displacement

8. Next plan:
   new indenter, stable assembly, repeat I+ -> J+ -> O in one continuous run

## Figures To Use

- `reports/figs/I_main.png`
- `reports/figs/I_jF.png`
- `reports/figs/Iplus_same_d_diff_f.png`
- `reports/figs/J_main.png`
- `reports/figs/J_jq.png`
- `reports/figs/Jplus_same_f_diff_d.png`
- `reports/BLIND_TEST_ANALYSIS.md` table for blind-test result

## Next Experimental Plan

After changing the indenter:

1. Re-run baseline/B0 check.
2. Re-run I+ under the same assembly.
3. Re-run J+ with lower target range, avoiding high-d preload stalls.
4. Immediately run O blind test without changing geometry.
5. Analyze:

```powershell
python .\blind_test_analysis.py `
  --train-session NEW_IPLUS_SESSION `
  --train-session NEW_JPLUS_SESSION `
  --blind-session NEW_O_SESSION
```

Expected decision:

- If blind test passes: proceed to local Jacobian modeling and repeatability.
- If blind test fails but B0/geometry are stable: revise model/features.
- If blind test fails because B0/geometry shifts again: add mechanical fixture
  constraints before further modeling.
