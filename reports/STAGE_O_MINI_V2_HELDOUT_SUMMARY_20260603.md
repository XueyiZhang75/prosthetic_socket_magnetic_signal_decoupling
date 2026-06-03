# Stage O-mini v2 Held-out Summary

Date: 2026-06-03

## Purpose

Test whether the path-excitation effect observed in I+/J+ calibration also appears at held-out interpolation states that were not used as training points.

Training sessions:

- I+ same-d/different-F: `session_20260602_211458`, `session_20260603_150122`
- J+ same-F/different-d: `session_20260603_135934`, `session_20260603_153110`

Held-out sessions:

- same-F/different-d: `session_20260603_160658`
- same-d/different-F: `session_20260603_161958`

## Phenomenon-Level Results

| held-out pair | target | controlled variable | split variable | magnetic split | verdict |
|---|---:|---:|---:|---:|---|
| same-F / different-d | 1.75 N | delta F = -58.1 mN | delta d = +0.160 mm | delta Bvec = 437.8 uT | strong |
| same-F / different-d | 1.85 N | delta F = -12.1 mN | delta d = +0.150 mm | delta Bvec = 460.1 uT | strong |
| same-d / different-F | 1.50 mm | delta d = +0.020 mm | delta F = -427.5 mN | delta Bvec = 74.0 uT | strong |

Conclusion: both complementary path-excitation modes are reproduced at held-out states. The effect is not limited to the exact calibration targets.

## Current Blind Model Result

Report: `reports/BLIND_TEST_ANALYSIS_Omini_v2_combined_20260603.md`

| output | Bxyz model MAE | baseline MAE | current status |
|---|---:|---:|---|
| F | 0.1575 N | 0.1244 N from F=h(d) | not pass |
| d | 0.0272 mm | 0.0158 mm from d=g(|B|) | not pass |

Interpretation: the held-out experiment strongly supports the path-excitation identifiability route, but the current simple linear `Bxyz -> [F,d]` model is not yet the final decoupling model.

## Recommended Next Step

Use the held-out data as validation evidence for the new research direction, then improve the inverse model rather than collecting more redundant path-pair evidence.

Near-term modeling upgrades:

- Add path/state features or paired constraints instead of fitting all points with one global linear Bxyz model.
- Evaluate local models around the working zone rather than one model across all path states.
- Report phenomenon-level identifiability and model-level accuracy separately.
