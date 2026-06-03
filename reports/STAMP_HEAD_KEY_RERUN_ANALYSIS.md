# Stamp-Head Key Rerun Analysis

Date: 2026-06-03

This report uses the stamp-head rerun sessions collected after replacing the
clip-style head with `stamp_head_v1`. It is a focused N-mini check for the new
path-excitation storyline, not the full Stage N readiness audit.

## Sessions

| Role | Session / source |
|---|---|
| Stage I passive fixed-d contrast | `session_20260602_203043` |
| Stage I+ same-d / different-F path excitation | `session_20260602_211458` |
| Stage J passive fixed-F contrast | `reports/stage_J_clean_trial_summary.csv` |
| Stage J+ same-F / different-d path excitation | `session_20260603_135934` |

## Passive Controls

Stage I fixed-displacement holds at `d = 1.59 mm` showed force relaxation but
only weak magnetic drift:

| Rep | Delta F | Delta \|B\| |
|---:|---:|---:|
| 1 | -110.5 mN | -8.0 uT |
| 2 | -95.1 mN | -4.4 uT |
| 3 | -109.4 mN | -3.0 uT |

Stage J fixed-force holds maintained force tightly while displacement crept by
about `0.48-0.52 mm`, but magnetic drift remained small:

| Clean trial | Mean F | Delta d | Delta \|B\| |
|---|---:|---:|---:|
| `session_20260603_122143 rep3` | 1.758 N | +0.483 mm | -5.1 uT |
| `session_20260603_124327 rep1` | 1.772 N | +0.480 mm | +5.8 uT |
| `session_20260603_124327 rep2` | 1.775 N | +0.520 mm | -1.5 uT |

Interpretation: passive creep/relaxation alone does not create a large,
repeatable magnetic contrast in this stamp-head work zone.

## Path-Excited Pair Evidence

I+ same-d / different-F pairs:

- Usable pairs: `3/3`
- Median matched displacement mismatch: `0.020 mm`
- Median force split: `0.443 N`
- Median three-axis magnetic split: `118.0 uT`
- Pair-column estimate: `j_F = (0.0, -248.2, 61.2) uT/N`

J+ same-F / different-d pairs:

- Usable pairs: `3/3`
- Median force mismatch: `36.6 mN`
- Median displacement split: `0.150 mm`
- Median three-axis magnetic split: `462.5 uT`
- Pair-column estimate: `j_d = (-166.3, 2764.6, 1355.2) uT/mm`

## Local Identifiability Check

- Pair-column angle: `40.1 deg`
- Absolute cosine: `0.765`
- Raw unscaled column condition number: `18.8`
- Verdict: `PROCEED TO O-MINI, NOT FINAL O2`

The stamp-head I+ and J+ effects are both strong and repeatable, but the two
pair-column directions are only moderately separated. This is sufficient for a
local blind-test pilot, but not enough to claim final confirmatory decoupling
without held-out validation.

## O-mini Update

Stage O-mini has now been run:

```text
session_20260603_143946
```

Detailed analysis:

```text
reports/STAGE_O_MINI_ANALYSIS_20260603_143946.md
```

The held-out path-pair phenomenon reproduced strongly: all three O-mini
loading/unloading pairs produced `0.15-0.17 mm` displacement splits and
`~437-469 uT` three-axis magnetic splits at approximately matched force.

The current simple blind inverse was only a partial pass: `Bxyz -> d` beat the
scalar `d=g(|B|)` baseline, but `Bxyz -> F` did not beat `F=h(d)`. The next
experimental step is therefore not final O2, but a broader local calibration
set with at least one additional I+ depth and one additional J+ force target.

## Historical O-mini Command

```powershell
python .\stageO_blind_test.py
```

Current O-mini targets:

```text
1.80 N -> loading/unloading pair
1.70 N -> loading/unloading pair
1.90 N -> loading/unloading pair
```

This produces six blind states in one trial. After the run, analyze with:

```powershell
python .\blind_test_analysis.py `
  --train-session session_20260602_211458 `
  --train-session session_20260603_135934 `
  --blind-session session_YYYYMMDD_HHMMSS
```

Acceptance for this O-mini pilot is qualitative/diagnostic:

- The blind session must be held out from target tuning and model choice.
- The main `Bxyz -> [F, d]` model should beat the simple baselines for at least
  one output and ideally both.
- If O-mini fails, do not discard the I+/J+ finding; instead treat it as evidence
  that the current two-column calibration is too narrow or moderately
  ill-conditioned and expand the green-zone training design.
