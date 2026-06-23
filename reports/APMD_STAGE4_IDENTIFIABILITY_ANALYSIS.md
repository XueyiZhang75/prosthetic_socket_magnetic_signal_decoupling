# APMD Stage 4 Local Identifiability Analysis

## Inputs

- Same-d/different-F formal table: `reports/experiment_3_1_complete_figure_data_replicates.csv`
- Same-F/different-d formal table: `reports/experiment_3_2_same_f_different_d_figure_data_replicates.csv`
- Conservative magnetic noise floor used for ratio reporting: `10.0 uT`.

## Method

- `j_F` is estimated from near-matched-displacement / different-force path pairs as `Delta B / |Delta F|`.
- `j_d` is estimated from near-matched-force / different-displacement path pairs as `Delta B / |Delta d|`.
- Because loading/return ordering can flip the sign convention, the identifiability angle uses the absolute cosine between the two vectors.
- The scaled condition number is computed after normalizing the two columns, so it reflects directional collinearity rather than unit choice.
- Candidate ranking combines angle, scaled condition number, magnetic signal-to-noise ratio, repeat directional consistency, and local proximity in `(d,F)` space.
- The selected zone is a local mechanism-validation candidate in the current bench-top setup, not a full prosthetic-socket application range.

## Primary Result

- Strict-gate primary sensitivity-pair candidate: same-d target `d = 3.40 mm` paired with same-F target `F = 4.90 N`.
- Pair-column angle: `48.5 deg`.
- Scaled condition number: `2.22`.
- Minimum magnetic noise ratio: `22.8`.
- Locality distance: `1.85`.
- Verdict: `candidate`.
- Best-score practical candidate: `d = 3.20 mm`, `F = 4.90 N`, angle `41.9 deg`, score `0.660`.

## Interpretation

At least one local pair passes the Stage 4 directional gate. The strict-gate candidate should be treated as the primary local mechanism-validation candidate, while the best-score practical candidate is useful if locality is prioritized. This does not claim full-range prosthetic-socket deployment.

## Top Candidates

| Rank | same-d d (mm) | same-F F (N) | angle (deg) | cond scaled | min B/noise | locality | score | verdict |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 3.20 | 4.90 | 41.9 | 2.61 | 20.1 | 0.83 | 0.660 | usable_but_weaker |
| 2 | 3.00 | 4.30 | 32.4 | 3.44 | 15.5 | 0.57 | 0.476 | exploratory |
| 3 | 3.00 | 3.75 | 33.4 | 3.33 | 15.5 | 0.66 | 0.465 | exploratory |
| 4 | 3.00 | 4.90 | 30.7 | 3.64 | 15.5 | 0.64 | 0.433 | exploratory |
| 5 | 3.20 | 4.30 | 43.7 | 2.50 | 20.1 | 1.35 | 0.393 | usable_but_weaker |
| 6 | 2.80 | 3.75 | 34.0 | 3.27 | 10.3 | 0.33 | 0.370 | exploratory |
| 7 | 2.80 | 4.30 | 33.0 | 3.37 | 10.3 | 0.77 | 0.283 | exploratory |
| 8 | 3.20 | 3.75 | 44.6 | 2.44 | 20.1 | 1.63 | 0.262 | usable_but_weaker |
| 9 | 3.40 | 4.90 | 48.5 | 2.22 | 22.8 | 1.85 | 0.224 | candidate |
| 10 | 2.60 | 3.75 | 33.3 | 3.34 | 11.0 | 1.11 | 0.220 | exploratory |

## Output Files

- Main figure: `reports/apmd_stage4_identifiability_complete.png`
- Candidate pair table: `reports/apmd_stage4_identifiability_pair_table.csv`
- `j_F` table: `reports/apmd_stage4_jF_from_same_d_pairs.csv`
- `j_d` table: `reports/apmd_stage4_jd_from_same_f_pairs.csv`
- Summary: `reports/apmd_stage4_identifiability_summary.csv`
