# Experiment 3.1 Median Method Explanation

## Source hierarchy

1. Raw time-series replicate CSVs: 21 files, one per target-d/trial replicate.
2. Pair summary CSVs: 21 rows total, one row per target-d/trial pair summary.
3. Figure tables: per-panel values derived from the 21 pair-summary rows.

## Median level 1: within one trial/state

For each trial, the script records many samples during `direct_target`, `preload_deep`, and `return_target` hold states. The pair summary uses only `direct_target` and `return_target` for the figure. For each state, it takes samples from the last `10` seconds:

`t_rel_s >= max(t_rel_s) - 10`

Then it computes the median of `d_actual_mm`, `F_N`, `Bmag_uT`, `mean_Bx_uT`, `mean_By_uT`, `mean_Bz_uT`, and `delta_Bx/By/Bz_uT` within that tail window. So `F_direct_N` is already a within-trial, last-10-s median for the direct state; `F_return_N` is the same for the return state.

## Pair diagnostic formulas

For each trial/pair:

- `d_diff_mm = d_return_mm - d_direct_mm`
- `delta_F_N = F_return_N - F_direct_N`
- `delta_Bmag_uT = Bmag_return_uT - Bmag_direct_uT`
- `delta_Bx_uT = return_delta_Bx_uT - direct_delta_Bx_uT`
- `delta_By_uT = return_delta_By_uT - direct_delta_By_uT`
- `delta_Bz_uT = return_delta_Bz_uT - direct_delta_Bz_uT`
- `delta_Bvec_uT = sqrt(delta_Bx_uT^2 + delta_By_uT^2 + delta_Bz_uT^2)`

## Median level 2: across the 3 trials at one target d

The figure then groups the 21 pair-summary rows by `target d`. Each target d has 3 trial rows. The black line/heatmap/decision-plane values are medians across those 3 trial-level summary rows, not medians inside a single trial.

With 3 trials, the median is simply the middle value after sorting the three trial-level values. The source trial for each median can differ by metric; see the `median_audit` sheet.

## Panel mapping

- Panel a: raw colored points = trial-level `F_direct_N` and `F_return_N`; black lines = median across 3 trials at each target d.
- Panel b: raw points = trial-level `delta_Bvec_uT`; line = median across 3 trials; error bars = min and max across 3 trials.
- Panel c: x = median of `abs(delta_F_N)` across 3 trials; y = median of `delta_Bvec_uT` across 3 trials.
- Panels d/e: signed median of `delta_Bx_uT`, `delta_By_uT`, `delta_Bz_uT` across 3 trials.

## Thresholds

- same-d tolerance: `0.02` mm
- force split threshold: `0.2` N
- magnetic signal threshold: `50.0` uT
- candidate work zone in the figure: `3.18 <= target d <= 3.42` mm
