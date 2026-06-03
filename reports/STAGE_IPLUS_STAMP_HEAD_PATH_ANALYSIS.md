# Stage I+ Stamp-Head Same-d / Different-F Path Analysis

Final accepted session: `session_20260602_211458`

Role in rerun: path-excitation test against the Stage I passive fixed-`d`
contrast.

Earlier tuning session: `session_20260602_210102`. That run confirmed a large
path magnetic response, but two pairs returned `0.06 mm` deeper than the direct
state and were marked `bad_d_match`. The I+ target-position tolerance was then
tightened to `0.02 mm`.

## Configuration

- Head ID: `stamp_head_v1`
- Force calibration ID: `force_calibration_20260602_190856`
- Displacement zero ID: `stageD_session_20260602_201421`
- Target displacement: `d_target = 1.60 mm`
- Preload depth: `d_preload = 1.90 mm`
- Trials: `3`
- No-contact live-tare check: `live_tare_N = -2.9284 N`

## Pair Summary

Values are from `Iplus_pair_summary.csv`, comparing returned target state
against direct target state.

| Rep | d_direct (mm) | d_return (mm) | Delta d (mm) | Delta F (N) | Delta Bmag (uT) | Delta Bvec (uT) | Verdict |
|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 1.590 | 1.610 | +0.020 | -0.4866 | +105.6 | 119.3 | strong |
| 2 | 1.580 | 1.600 | +0.020 | -0.4432 | +97.6 | 113.3 | strong |
| 3 | 1.580 | 1.600 | +0.020 | -0.4407 | +100.6 | 118.0 | strong |

Summary:

- Clean same-`d` pairs: `3/3`
- Median `Delta d`: `+0.020 mm`
- Median `Delta F`: `-0.4432 N`
- Median `Delta Bmag`: `+100.6 uT`
- Median `Delta Bvec`: `118.0 uT`
- Median `dBmag/dF`: `-220.1 uT/N`

## Interpretation

Stage I+ produced a much stronger magnetic response than passive Stage I. The
passive Stage I hold at the same nominal depth showed only `Delta Bvec ~2-3 uT`
during `~85-95 mN` force relaxation. In contrast, the accepted I+ rerun produced
`Delta Bvec = 113-119 uT` while staying within `+0.020 mm` same-`d` mismatch.

This is the first clean stamp-head evidence that path excitation can create a
same-displacement, different-force pair with a clearly resolvable magnetic
change. It supports the main APMD argument: the soft interface path history is
not merely experimental drift or nuisance hysteresis; it can be used as an
identifiability-driving excitation.

## Decision

Stage I+ is accepted. Do not rerun I+ now unless later Stage J/J+ results create
a specific conflict. Proceed to the fixed-force passive Stage J contrast, then
Stage J+ same-`F` / different-`d` path excitation.
