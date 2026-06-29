# Stage 6.3 Work-Zone Analysis Figures

This note records four work-zone-level diagnostic figures generated from the current accepted Stage 6.3 local-identifiability prediction table.

## Generated Figures

- `apmd_stage6_work_zone_eight_panel_summary.png`: combined eight-panel summary linking zone-resolved residuals, coverage, geometry, branch errors, and transfer diagnostics.
- `apmd_stage6_work_zone_fd_coverage.png`: measured force-displacement coverage of the held-out dense-loop states.
- `apmd_stage6_work_zone_metric_heatmap.png`: zone-level error, local geometry, and residual feature map.
- `apmd_stage6_work_zone_branch_error.png`: branch-resolved error distributions by work zone.
- `apmd_stage6_work_zone_transfer_matrix.png`: train-zone by test-zone transfer diagnostic using local-ID coordinate features.

## Zone Metrics

| work_zone   |   n_states |   d_min_mm |   d_max_mm |   F_min_N |   F_max_N |   F_MAE_N |   d_MAE_mm |   F_p90_N |   d_p90_mm |   F_bias_N |   d_bias_mm |   angle_median_deg |   pF_median_kuT |   pD_median_kuT |   residual_median_kuT |
|:------------|-----------:|-----------:|-----------:|----------:|----------:|----------:|-----------:|----------:|-----------:|-----------:|------------:|-------------------:|----------------:|----------------:|----------------------:|
| 1.8-2.6 mm  |         78 |      1.820 |      2.580 |     1.592 |     6.097 |     0.108 |      0.016 |     0.250 |      0.033 |      0.017 |      -0.009 |             24.238 |           3.452 |           2.408 |                 0.138 |
| 2.4-3.2 mm  |         78 |      2.420 |      3.190 |     3.151 |    11.364 |     0.076 |      0.019 |     0.137 |      0.039 |     -0.037 |      -0.000 |             21.731 |           4.775 |           3.918 |                 0.617 |
| 3.0-3.8 mm  |         78 |      3.010 |      3.790 |     4.154 |    18.780 |     0.069 |      0.056 |     0.141 |      0.108 |      0.023 |       0.040 |             44.812 |           1.958 |           5.558 |                 0.260 |
| 3.4-4.2 mm  |         78 |      3.420 |      3.890 |    10.009 |    21.493 |     0.077 |      0.096 |     0.153 |      0.166 |     -0.043 |      -0.096 |              2.858 |           5.943 |           5.746 |                 4.450 |

## Transfer Matrix: Force MAE (N)

|            |   1.8-2.6 mm |   2.4-3.2 mm |   3.0-3.8 mm |   3.4-4.2 mm |
|:-----------|-------------:|-------------:|-------------:|-------------:|
| 1.8-2.6 mm |        0.121 |        2.020 |        7.566 |       12.618 |
| 2.4-3.2 mm |        1.906 |        0.279 |        2.064 |        9.681 |
| 3.0-3.8 mm |        7.601 |        9.761 |        0.727 |       46.688 |
| 3.4-4.2 mm |        6.493 |        2.058 |        4.032 |        0.996 |

## Transfer Matrix: Displacement MAE (mm)

|            |   1.8-2.6 mm |   2.4-3.2 mm |   3.0-3.8 mm |   3.4-4.2 mm |
|:-----------|-------------:|-------------:|-------------:|-------------:|
| 1.8-2.6 mm |        0.024 |        0.416 |        1.585 |        1.547 |
| 2.4-3.2 mm |        0.414 |        0.026 |        0.366 |        0.768 |
| 3.0-3.8 mm |        0.167 |        0.961 |        0.031 |        4.213 |
| 3.4-4.2 mm |        0.589 |        0.368 |        0.181 |        0.039 |

Interpretation note: the transfer matrix is a diagnostic, not a replacement for session-level held-out validation. Off-diagonal cells intentionally ask whether a mapping learned in one work zone can predict another work zone.
