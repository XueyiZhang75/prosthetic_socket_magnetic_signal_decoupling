"""Stage 6.3 work-zone residual analysis.

This script reuses the existing Stage 6.3 ridge held-out prediction table and
does not refit any model.  It asks where the local-ID model works best and which
work zones still dominate the remaining residuals.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports"

IN_PREDICTIONS = REPORTS_DIR / "apmd_stage6_local_identifiability_predictions.csv"

OUT_METRICS = REPORTS_DIR / "apmd_stage6_zone_residual_metrics.csv"
OUT_LOCAL_ID_STATES = REPORTS_DIR / "apmd_stage6_zone_local_id_state_errors.csv"
OUT_PAIR = REPORTS_DIR / "apmd_stage6_zone_pair_consistency.csv"
OUT_PAIR_SUMMARY = REPORTS_DIR / "apmd_stage6_zone_pair_summary.csv"
OUT_SUMMARY_FIGURE = REPORTS_DIR / "apmd_stage6_zone_residual_summary.png"
OUT_SUMMARY_PDF = REPORTS_DIR / "apmd_stage6_zone_residual_summary.pdf"
OUT_FIT_GRID = REPORTS_DIR / "apmd_stage6_zone_local_id_fit_grid.png"
OUT_FIT_GRID_PDF = REPORTS_DIR / "apmd_stage6_zone_local_id_fit_grid.pdf"
OUT_REPORT = REPORTS_DIR / "APMD_STAGE6_ZONE_RESIDUAL_ANALYSIS.md"

TRAIN_STATES = 1461

BLACK = "#222222"
BLUE = "#2c7fb8"
GRAY = "#858585"
RED = "#c43c39"
LIGHT_GRAY = "#e8e8e8"

RIDGE_MODELS = [
    "plain_magnetic_ridge",
    "lim_style_branch_ridge",
    "apmd_path_memory_ridge",
    "apmd_local_identifiability_ridge",
]

MODEL_LABELS = {
    "plain_magnetic_ridge": "plain\nmagnetic",
    "lim_style_branch_ridge": "branch\nlabel",
    "apmd_path_memory_ridge": "path\nmemory",
    "apmd_local_identifiability_ridge": "local-ID",
}

MODEL_COLORS = {
    "plain_magnetic_ridge": BLACK,
    "lim_style_branch_ridge": BLUE,
    "apmd_path_memory_ridge": GRAY,
    "apmd_local_identifiability_ridge": RED,
}

ZONE_ORDER = [
    "1.8-2.6 mm",
    "2.4-3.2 mm",
    "3.0-3.8 mm",
    "3.4-4.2 mm",
]

ZONE_COLORS = {
    "1.8-2.6 mm": "#4C78A8",
    "2.4-3.2 mm": "#59A14F",
    "3.0-3.8 mm": "#C43C39",
    "3.4-4.2 mm": "#7B61A8",
}

PATH_COLORS = {
    "direct_loading": BLACK,
    "return_unloading": BLUE,
    "preload_deep": GRAY,
}


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(math.sqrt(mean_squared_error(y_true, y_pred)))


def _set_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.sans-serif": ["Arial"],
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "axes.linewidth": 0.9,
            "axes.labelsize": 9.4,
            "axes.titlesize": 11.0,
            "xtick.labelsize": 8.2,
            "ytick.labelsize": 8.2,
            "legend.fontsize": 7.5,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def assign_work_zone(row: pd.Series) -> str:
    experiment = str(row.get("experiment", ""))
    if "6.1-S" in experiment or "shallow" in experiment:
        return "1.8-2.6 mm"
    if "6.1-L" in experiment or "Block L" in experiment:
        return "2.4-3.2 mm"
    if "6.1-H" in experiment or "upper" in experiment:
        return "3.4-4.2 mm"
    return "3.0-3.8 mm"


def load_predictions() -> pd.DataFrame:
    df = pd.read_csv(IN_PREDICTIONS)
    df = df[df["model"].isin(RIDGE_MODELS)].copy()
    df["work_zone"] = df.apply(assign_work_zone, axis=1)
    df["work_zone"] = pd.Categorical(df["work_zone"], categories=ZONE_ORDER, ordered=True)
    df["abs_F_error_N"] = pd.to_numeric(df["F_error_N"], errors="coerce").abs()
    df["abs_d_error_mm"] = pd.to_numeric(df["d_error_mm"], errors="coerce").abs()
    return df


def metric_rows(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (zone, model), chunk in df.groupby(["work_zone", "model"], observed=False):
        if chunk.empty:
            continue
        f_true = chunk["F_N"].to_numpy(float)
        f_pred = chunk["F_pred_N"].to_numpy(float)
        d_true = chunk["d_mm"].to_numpy(float)
        d_pred = chunk["d_pred_mm"].to_numpy(float)
        rows.append(
            {
                "work_zone": str(zone),
                "model": model,
                "model_label": MODEL_LABELS[model].replace("\n", " "),
                "n_states": int(len(chunk)),
                "n_sessions": int(chunk["session_id"].nunique()),
                "actual_d_min_mm": float(chunk["d_mm"].min()),
                "actual_d_max_mm": float(chunk["d_mm"].max()),
                "F_min_N": float(chunk["F_N"].min()),
                "F_max_N": float(chunk["F_N"].max()),
                "F_MAE_N": mean_absolute_error(f_true, f_pred),
                "F_RMSE_N": _rmse(f_true, f_pred),
                "F_R2": r2_score(f_true, f_pred),
                "d_MAE_mm": mean_absolute_error(d_true, d_pred),
                "d_RMSE_mm": _rmse(d_true, d_pred),
                "d_R2": r2_score(d_true, d_pred),
                "F_error_median_N": float(chunk["F_error_N"].median()),
                "d_error_median_mm": float(chunk["d_error_mm"].median()),
                "F_abs_error_p90_N": float(chunk["abs_F_error_N"].quantile(0.90)),
                "d_abs_error_p90_mm": float(chunk["abs_d_error_mm"].quantile(0.90)),
            }
        )
    return pd.DataFrame(rows)


def pair_consistency(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    usable = df[df["path_label"].isin(["direct_loading", "return_unloading"])].copy()
    group_cols = ["work_zone", "model", "session_id", "cycle_index", "d_target_mm"]
    for keys, chunk in usable.groupby(group_cols, observed=False):
        direct = chunk[chunk["path_label"] == "direct_loading"]
        ret = chunk[chunk["path_label"] == "return_unloading"]
        if direct.empty or ret.empty:
            continue
        direct_row = direct.iloc[0]
        ret_row = ret.iloc[0]
        measured_delta_f = float(ret_row["F_N"] - direct_row["F_N"])
        predicted_delta_f = float(ret_row["F_pred_N"] - direct_row["F_pred_N"])
        measured_delta_d = float(ret_row["d_mm"] - direct_row["d_mm"])
        predicted_delta_d = float(ret_row["d_pred_mm"] - direct_row["d_pred_mm"])
        rows.append(
            {
                "work_zone": str(keys[0]),
                "model": keys[1],
                "session_id": keys[2],
                "cycle_index": keys[3],
                "d_target_mm": keys[4],
                "measured_delta_F_N": measured_delta_f,
                "predicted_delta_F_N": predicted_delta_f,
                "abs_delta_F_residual_N": abs(predicted_delta_f - measured_delta_f),
                "measured_delta_d_mm": measured_delta_d,
                "predicted_delta_d_mm": predicted_delta_d,
                "abs_delta_d_residual_mm": abs(predicted_delta_d - measured_delta_d),
            }
        )
    pair_df = pd.DataFrame(rows)
    if pair_df.empty:
        return pair_df, pd.DataFrame()
    pair_summary = (
        pair_df.groupby(["work_zone", "model"], observed=False)
        .agg(
            n_pairs=("model", "size"),
            pair_delta_F_MAE_N=("abs_delta_F_residual_N", "mean"),
            pair_delta_d_MAE_mm=("abs_delta_d_residual_mm", "mean"),
        )
        .reset_index()
    )
    return pair_df, pair_summary


def _add_value_labels(ax: plt.Axes, xs: np.ndarray, values: np.ndarray, fmt: str, fontsize: float = 6.8) -> None:
    ymax = np.nanmax(values) if len(values) else 0.0
    offset = ymax * 0.025 if ymax > 0 else 0.01
    for x, value in zip(xs, values):
        ax.text(x, float(value) + offset, fmt.format(float(value)), ha="center", va="bottom", fontsize=fontsize)


def plot_summary(metrics: pd.DataFrame, local_id: pd.DataFrame, pair_summary: pd.DataFrame) -> None:
    _set_style()
    fig, axes = plt.subplots(2, 2, figsize=(12.6, 8.0), dpi=240)
    ax1, ax2, ax3, ax4 = axes.ravel()
    test_states = len(local_id)

    x = np.arange(len(ZONE_ORDER))
    width = 0.18
    offsets = np.linspace(-1.5 * width, 1.5 * width, len(RIDGE_MODELS))
    for model, offset in zip(RIDGE_MODELS, offsets):
        vals = (
            metrics[metrics["model"] == model]
            .set_index("work_zone")
            .reindex(ZONE_ORDER)["F_MAE_N"]
            .to_numpy(float)
        )
        ax1.bar(x + offset, vals, width=width, color=MODEL_COLORS[model], label=MODEL_LABELS[model].replace("\n", " "))
        _add_value_labels(ax1, x + offset, vals, "{:.2f}", fontsize=6.1)
    ax1.set_ylim(top=ax1.get_ylim()[1] * 1.12)
    ax1.set_title("a  Force MAE by work zone")
    ax1.set_ylabel("F MAE (N)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(ZONE_ORDER)
    ax1.legend(frameon=False, ncol=2, fontsize=6.8)

    for model, offset in zip(RIDGE_MODELS, offsets):
        vals = (
            metrics[metrics["model"] == model]
            .set_index("work_zone")
            .reindex(ZONE_ORDER)["d_MAE_mm"]
            .to_numpy(float)
        )
        ax2.bar(x + offset, vals, width=width, color=MODEL_COLORS[model], label=MODEL_LABELS[model].replace("\n", " "))
        _add_value_labels(ax2, x + offset, vals, "{:.3f}", fontsize=6.1)
    ax2.set_ylim(top=ax2.get_ylim()[1] * 1.12)
    ax2.set_title("b  Displacement MAE by work zone")
    ax2.set_ylabel("d MAE (mm)")
    ax2.set_xticks(x)
    ax2.set_xticklabels(ZONE_ORDER)

    data_by_zone = [local_id.loc[local_id["work_zone"] == zone, "abs_F_error_N"].to_numpy(float) for zone in ZONE_ORDER]
    parts = ax3.violinplot(data_by_zone, positions=x, widths=0.72, showmedians=True, showextrema=False)
    for body, zone in zip(parts["bodies"], ZONE_ORDER):
        body.set_facecolor(ZONE_COLORS[zone])
        body.set_alpha(0.25)
        body.set_edgecolor(ZONE_COLORS[zone])
    parts["cmedians"].set_color(BLACK)
    parts["cmedians"].set_linewidth(1.2)
    rng = np.random.default_rng(42)
    for i, zone in enumerate(ZONE_ORDER):
        vals = local_id.loc[local_id["work_zone"] == zone, "abs_F_error_N"].to_numpy(float)
        jitter = rng.normal(0, 0.045, size=len(vals))
        ax3.scatter(np.full(len(vals), i) + jitter, vals, s=12, color=ZONE_COLORS[zone], alpha=0.55, edgecolor="white", linewidth=0.2)
    ax3.set_title("c  Local-ID absolute force residual distribution")
    ax3.set_ylabel("|F error| (N)")
    ax3.set_xticks(x)
    ax3.set_xticklabels(ZONE_ORDER)

    local_id_sorted = local_id.sort_values("d_mm")
    for zone, chunk in local_id_sorted.groupby("work_zone", observed=False):
        ax4.scatter(
            chunk["d_mm"],
            chunk["F_error_N"],
            s=18,
            color=ZONE_COLORS[str(zone)],
            alpha=0.65,
            edgecolor="white",
            linewidth=0.25,
            label=str(zone),
        )
    ax4.axhline(0, color=BLACK, linewidth=0.8)
    ax4.set_title("d  Local-ID signed force residual across d")
    ax4.set_xlabel("measured d (mm)")
    ax4.set_ylabel("F prediction error (N)")
    ax4.legend(frameon=False, fontsize=6.8, ncol=2)

    for ax in axes.ravel():
        ax.grid(color=LIGHT_GRAY, linewidth=0.8)
        ax.set_axisbelow(True)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)

    fig.suptitle(
        "Zone-resolved held-out residuals",
        x=0.02,
        y=0.99,
        ha="left",
        fontsize=15,
        fontweight="bold",
    )
    fig.text(
        0.02,
        0.955,
        f"Train states = {TRAIN_STATES}; test states = {test_states}.",
        ha="left",
        va="top",
        fontsize=9,
        color="#555555",
    )
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.92])
    fig.savefig(OUT_SUMMARY_FIGURE, bbox_inches="tight")
    fig.savefig(OUT_SUMMARY_PDF, bbox_inches="tight")
    plt.close(fig)


def _axis_limits(true: pd.Series, pred: pd.Series, pad_fraction: float = 0.08) -> tuple[float, float]:
    lo = min(float(true.min()), float(pred.min()))
    hi = max(float(true.max()), float(pred.max()))
    pad = (hi - lo) * pad_fraction if hi > lo else 0.1
    return lo - pad, hi + pad


def plot_fit_grid(local_id: pd.DataFrame, metrics: pd.DataFrame) -> None:
    _set_style()
    fig, axes = plt.subplots(2, 4, figsize=(14.0, 6.4), dpi=240)
    metric_index = metrics[metrics["model"] == "apmd_local_identifiability_ridge"].set_index("work_zone")
    for col, zone in enumerate(ZONE_ORDER):
        chunk = local_id[local_id["work_zone"] == zone]
        ax_f = axes[0, col]
        ax_d = axes[1, col]
        for label, group in chunk.groupby("path_label"):
            color = PATH_COLORS.get(label, GRAY)
            display = label.replace("_", " ")
            ax_f.scatter(group["F_N"], group["F_pred_N"], s=20, color=color, alpha=0.72, edgecolor="white", linewidth=0.25, label=display)
            ax_d.scatter(group["d_mm"], group["d_pred_mm"], s=20, color=color, alpha=0.72, edgecolor="white", linewidth=0.25)

        f_lo, f_hi = _axis_limits(chunk["F_N"], chunk["F_pred_N"], 0.10)
        d_lo, d_hi = _axis_limits(chunk["d_mm"], chunk["d_pred_mm"], 0.12)
        ax_f.plot([f_lo, f_hi], [f_lo, f_hi], color=RED, linewidth=1.0)
        ax_d.plot([d_lo, d_hi], [d_lo, d_hi], color=RED, linewidth=1.0)
        ax_f.set_xlim(f_lo, f_hi)
        ax_f.set_ylim(f_lo, f_hi)
        ax_d.set_xlim(d_lo, d_hi)
        ax_d.set_ylim(d_lo, d_hi)

        row = metric_index.loc[zone]
        ax_f.set_title(f"{zone}\nF MAE={row['F_MAE_N']:.3f} N")
        ax_d.set_title(f"d MAE={row['d_MAE_mm']:.3f} mm")
        if col == 0:
            ax_f.set_ylabel("predicted F (N)")
            ax_d.set_ylabel("predicted d (mm)")
        ax_f.set_xlabel("measured F (N)")
        ax_d.set_xlabel("measured d (mm)")

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, loc="upper center", ncol=4, bbox_to_anchor=(0.55, 0.93))
    for ax in axes.ravel():
        ax.grid(color=LIGHT_GRAY, linewidth=0.8)
        ax.set_axisbelow(True)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)

    fig.suptitle(
        "Stage 6.3 local-ID ridge fits by work zone",
        x=0.02,
        y=0.995,
        ha="left",
        fontsize=15,
        fontweight="bold",
    )
    fig.text(
        0.02,
        0.955,
        "Each column is a held-out work zone; top row predicts force, bottom row predicts displacement.",
        ha="left",
        va="top",
        fontsize=9,
        color="#555555",
    )
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.88])
    fig.savefig(OUT_FIT_GRID, bbox_inches="tight")
    fig.savefig(OUT_FIT_GRID_PDF, bbox_inches="tight")
    plt.close(fig)


def write_report(metrics: pd.DataFrame, pair_summary: pd.DataFrame, local_id: pd.DataFrame) -> None:
    local_metrics = metrics[metrics["model"] == "apmd_local_identifiability_ridge"].copy()
    metric_table = metrics.sort_values(["work_zone", "model"]).to_markdown(index=False)
    local_table = local_metrics.sort_values("work_zone").to_markdown(index=False)
    pair_table = (
        pair_summary[pair_summary["model"] == "apmd_local_identifiability_ridge"]
        .sort_values("work_zone")
        .to_markdown(index=False)
        if not pair_summary.empty
        else "_No same-d-like pairs found._"
    )

    best_force = local_metrics.sort_values("F_MAE_N").iloc[0]
    worst_force = local_metrics.sort_values("F_MAE_N").iloc[-1]
    best_d = local_metrics.sort_values("d_MAE_mm").iloc[0]
    worst_d = local_metrics.sort_values("d_MAE_mm").iloc[-1]

    text = f"""# Stage 6.3 Work-Zone Residual Analysis

This analysis reuses the existing Stage 6.3 ridge held-out prediction table:

```text
{IN_PREDICTIONS.as_posix()}
```

No model was refit and no experimental record was changed.  The purpose is to
split the same held-out predictions by dense-loop work zone and identify where
the local-ID ridge model is reliable or weak.

## Work-Zone Definition

The split uses the held-out session protocol, not the nearest local sensitivity
ID:

| Work zone | Source protocol |
|---|---|
| 1.8-2.6 mm | shallow held-out dense-loop sessions |
| 2.4-3.2 mm | lower held-out dense-loop sessions |
| 3.0-3.8 mm | original mid held-out dense-loop sessions |
| 3.4-4.2 mm | upper held-out dense-loop sessions |

Each zone contributes `78` local-ID held-out states.

## Local-ID Ridge Summary

Best force zone: `{best_force['work_zone']}` with `F_MAE = {best_force['F_MAE_N']:.3f} N`.

Worst force zone: `{worst_force['work_zone']}` with `F_MAE = {worst_force['F_MAE_N']:.3f} N`.

Best displacement zone: `{best_d['work_zone']}` with `d_MAE = {best_d['d_MAE_mm']:.3f} mm`.

Worst displacement zone: `{worst_d['work_zone']}` with `d_MAE = {worst_d['d_MAE_mm']:.3f} mm`.

## Local-ID Ridge Metrics by Zone

{local_table}

## All Ridge Model Metrics by Zone

{metric_table}

## Same-d Pair Consistency by Zone

{pair_table}

## Figures

![Stage 6.3 zone-resolved residual summary](apmd_stage6_zone_residual_summary.png)

![Stage 6.3 local-ID fit grid by work zone](apmd_stage6_zone_local_id_fit_grid.png)

## Interpretation

This zone-level view should be read as an applicability-map check.  The global
Stage 6.3 result shows that local-ID features strongly improve force
decoupling overall, but the residual distribution reveals which work zones are
already robust and which zones remain boundary or calibration-limited.  This is
the right basis for deciding whether the next experiment should add more
dense-loop states, more same-d force-sensitivity pairs, or missing same-F
displacement-sensitivity information in a specific work zone.
"""
    OUT_REPORT.write_text(text, encoding="utf-8")


def main() -> None:
    df = load_predictions()
    metrics = metric_rows(df)
    pair_df, pair_summary = pair_consistency(df)
    local_id = df[df["model"] == "apmd_local_identifiability_ridge"].copy()

    OUT_METRICS.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(OUT_METRICS, index=False)
    local_id.to_csv(OUT_LOCAL_ID_STATES, index=False)
    pair_df.to_csv(OUT_PAIR, index=False)
    pair_summary.to_csv(OUT_PAIR_SUMMARY, index=False)
    plot_summary(metrics, local_id, pair_summary)
    plot_fit_grid(local_id, metrics)
    write_report(metrics, pair_summary, local_id)

    print("Stage 6.3 zone residual analysis complete")
    print(f"  metrics   : {OUT_METRICS}")
    print(f"  local-ID  : {OUT_LOCAL_ID_STATES}")
    print(f"  summary   : {OUT_SUMMARY_FIGURE}")
    print(f"  fit grid  : {OUT_FIT_GRID}")
    print(f"  report    : {OUT_REPORT}")
    print(
        metrics[metrics["model"] == "apmd_local_identifiability_ridge"][
            ["work_zone", "n_states", "actual_d_min_mm", "actual_d_max_mm", "F_MAE_N", "d_MAE_mm"]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
