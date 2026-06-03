# Stage O-mini Analysis - session_20260603_143946

Date: 2026-06-03

This is a local held-out pilot for the stamp-head path-excitation storyline. It
is not the final O2 confirmatory blind test.

## Acquisition QC

| Item | Result |
|---|---|
| Session | `session_20260603_143946` |
| Force live tare | `-2.9093 N`, stable |
| Blind target order | `1.80 N`, `1.70 N`, `1.90 N` |
| Blind states recorded | `6/6` |
| Samples per state summary | `60` |
| Hardware aborts / force jumps | None observed |

The acquisition is usable as an O-mini held-out pilot.

## Held-Out Path-Pair Reproduction

| Target | Delta F | Delta d | Delta \|B\| | Delta B vector |
|---:|---:|---:|---:|---:|
| 1.80 N | -40.0 mN | +0.150 mm | +467.8 uT | 469.1 uT |
| 1.70 N | -10.0 mN | +0.160 mm | +453.6 uT | 455.4 uT |
| 1.90 N | -24.0 mN | +0.170 mm | +437.0 uT | 436.8 uT |

Interpretation: the J+ phenomenon reproduced very clearly in the held-out
O-mini session. At approximately matched force, the preload/unloading path
created `0.15-0.17 mm` displacement splits and `~437-469 uT` three-axis magnetic
splits.

This is strong evidence that the path-excitation effect is real and not only a
single calibration-session artifact.

## Blind Model Check

Training sessions:

- `session_20260602_211458` (I+ same-d / different-F)
- `session_20260603_135934` (J+ same-F / different-d)

Blind session:

- `session_20260603_143946`

Using the current `blind_test_analysis.py` default, auxiliary `preload_deep`
states are excluded from training/scoring because they are path-conditioning
steps rather than declared target states. The result was:

| Output | Model | MAE |
|---|---|---:|
| F | Bxyz -> F | 0.2091 N |
| F | baseline F=h(d) | 0.0853 N |
| d | Bxyz -> d | 0.0498 mm |
| d | baseline d=g(\|B\|) | 0.0649 mm |

Verdict: `PARTIAL PASS / MODEL NOT FINAL`

- Displacement inversion improved over the scalar magnetic baseline.
- Force inversion did not beat the mechanical `F=h(d)` baseline.

## Diagnostic Interpretation

The O-mini result should not be read as a failure of the physical discovery.
The held-out path pairs reproduce the key same-F/different-d magnetic split
very strongly.

The weaker part is the current inverse model:

- The stamp-head pair-column angle from I+/J+ is about `40 deg`, so the two
  columns are separated but moderately conditioned.
- The blind force range is narrow (`~1.59-1.81 N`), so `F=h(d)` is a strong
  baseline in this small window.
- The current training set has only 12 target states if auxiliary preload states
  are excluded, or 18 states if they are included. This is too small for a robust
  final inverse model.

## Recommendation

Do not rerun this exact O-mini immediately. The pilot did its job:

1. It confirms that the stamp-head path-excitation phenomenon persists in a
   held-out session.
2. It shows that the current simple inverse model is not yet strong enough for
   a final O2 claim, especially for force.

Next, expand the calibration design before the next blind test:

- Add one more I+ target depth near the O-mini loading depths:
  `d=1.40 mm`, preload to `1.70 mm`.
- Add two more J+ force targets:
  `1.70 N` and `1.90 N`, using the same `loading d + 0.30 mm` preload rule.
- Refit the local inverse using target states separately from auxiliary preload
  states, then repeat an O-mini blind session.

Current scripts have been configured for this expansion:

```powershell
python .\stageI_plus_same_d_diff_f.py
python .\stageJ_plus_same_f_diff_d.py
```

Calibration expansion progress:

| New calibration | Session | Result |
|---|---|---|
| I+ at `d=1.40 mm`, preload `1.70 mm` | `session_20260603_150122` | `3/3` strong pairs; median `|delta F|=384.5 mN`, median `|delta B|=56.2 uT`, `d mismatch=0.030 mm` |

After those two calibration sessions are collected, the next O-mini analysis
should use four training sessions:

```powershell
python .\blind_test_analysis.py `
  --train-session session_20260602_211458 `
  --train-session session_NEW_IPLUS_140 `
  --train-session session_20260603_135934 `
  --train-session session_NEW_JPLUS_170_190 `
  --blind-session session_NEW_OMINI
```

The strongest current claim is:

> A stamp-head soft interface can use path excitation to generate held-out
> same-force states with resolvable displacement and magnetic-state splits.

The stronger final claim:

> Bxyz can blindly recover both force and displacement better than single-variable
> baselines

requires a broader local calibration set before O2.
