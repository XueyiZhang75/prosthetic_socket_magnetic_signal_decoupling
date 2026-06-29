"""Stage 6 dual-coordinate local-identifiability check.

This is a non-destructive analysis layer on top of the current Stage 6
train/held-out split. It compares the existing APMD local-ID dot projection
features with a dual-coordinate solve in the local (j_F, j_d) basis.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import apmd_stage6_compare_local_identifiability_models as stage6
from apmd_stage6_predict_local_heldout import (
    HELDOUT_SESSION_IDS,
    TARGETS,
    load_heldout_states,
    _session_id_set,
    prepare_training_states,
)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports"

OUT_METRICS = REPORTS_DIR / "apmd_stage6_dual_coordinate_model_metrics.csv"
OUT_PREDICTIONS = REPORTS_DIR / "apmd_stage6_dual_coordinate_predictions.csv"
OUT_PAIR = REPORTS_DIR / "apmd_stage6_dual_coordinate_pair_consistency.csv"
OUT_CONFIDENCE = REPORTS_DIR / "apmd_stage6_dual_coordinate_confidence.csv"
OUT_FIGURE = REPORTS_DIR / "apmd_stage6_dual_coordinate_model_comparison.png"
OUT_FIGURE_PDF = REPORTS_DIR / "apmd_stage6_dual_coordinate_model_comparison.pdf"
OUT_REPORT = REPORTS_DIR / "APMD_STAGE6_DUAL_COORDINATE_LOCAL_ID_REPORT.md"

BLACK = "#222222"
BLUE = "#2f80b7"
GRAY = "#8a8a8a"
RED = "#c43c39"
ORANGE = "#d98c2b"
PURPLE = "#7b61a8"
LIGHT_GRAY = "#e8e8e8"


def model_specs() -> list[tuple[str, str, object, list[str]]]:
    magnetic = [
        "Bx_uT",
        "By_uT",
        "Bz_uT",
        "Bmag_uT",
        "delta_Bx_from_B0_uT",
        "delta_By_from_B0_uT",
        "delta_Bz_from_B0_uT",
        "delta_Bvec_from_B0_uT",
    ]
    path_numeric = ["is_preload", "is_return", "is_same_d_family"]
    memory_numeric = [
        "preload_hold_s",
        "recovery_s",
        "pair_Bmag_max_uT",
        "pair_Bmag_min_uT",
        "pair_Bmag_range_uT",
        "pair_state_index",
    ]
    geometry_numeric = [
        "local_jF_norm_uT_per_N",
        "local_jd_norm_uT_per_mm",
        "local_angle_deg",
        "local_scaled_condition",
        "local_d_distance_mm",
        "local_F_distance_N",
    ]
    dot_numeric = [
        "local_p_F_uT",
        "local_p_d_uT",
        "local_residual_uT",
    ] + geometry_numeric
    dual_numeric = [
        "local_dual_c_F_uT",
        "local_dual_c_d_uT",
        "local_dual_residual_uT",
        "local_dual_residual_fraction",
        "local_delta_B_norm_uT",
        "local_geometry_confidence",
        "local_geometry_uncertainty",
    ] + geometry_numeric

    path_cats = ["path_family", "path_label"]
    local_cats = ["path_family", "path_label", "local_zone_id", "local_jF_source_zone"]

    return [
        ("plain_magnetic_ridge", "plain magnetic", stage6._ridge_model(magnetic, []), magnetic),
        (
            "lim_style_branch_ridge",
            "branch-label baseline",
            stage6._ridge_model(magnetic + path_numeric, path_cats),
            magnetic + path_numeric + path_cats,
        ),
        (
            "apmd_path_memory_ridge",
            "APMD path memory",
            stage6._ridge_model(magnetic + path_numeric + memory_numeric, path_cats),
            magnetic + path_numeric + memory_numeric + path_cats,
        ),
        (
            "apmd_local_identifiability_dot_ridge",
            "APMD local-ID dot",
            stage6._ridge_model(magnetic + path_numeric + memory_numeric + dot_numeric, local_cats),
            magnetic + path_numeric + memory_numeric + dot_numeric + local_cats,
        ),
        (
            "apmd_local_identifiability_dual_ridge",
            "APMD local-ID dual",
            stage6._ridge_model(magnetic + path_numeric + memory_numeric + dual_numeric, local_cats),
            magnetic + path_numeric + memory_numeric + dual_numeric + local_cats,
        ),
        (
            "apmd_local_identifiability_dot_dual_ridge",
            "APMD local-ID dot+dual",
            stage6._ridge_model(magnetic + path_numeric + memory_numeric + dot_numeric + dual_numeric, local_cats),
            magnetic + path_numeric + memory_numeric + dot_numeric + dual_numeric + local_cats,
        ),
    ]


def model_order() -> list[str]:
    return [spec[0] for spec in model_specs()]


def model_labels() -> dict[str, str]:
    return {
        "plain_magnetic_ridge": "plain\nmagnetic",
        "lim_style_branch_ridge": "branch\nlabel",
        "apmd_path_memory_ridge": "path\nmemory",
        "apmd_local_identifiability_dot_ridge": "local-ID\ndot",
        "apmd_local_identifiability_dual_ridge": "local-ID\ndual",
        "apmd_local_identifiability_dot_dual_ridge": "local-ID\ndot+dual",
    }


def model_colors() -> dict[str, str]:
    return {
        "plain_magnetic_ridge": BLACK,
        "lim_style_branch_ridge": BLUE,
        "apmd_path_memory_ridge": GRAY,
        "apmd_local_identifiability_dot_ridge": RED,
        "apmd_local_identifiability_dual_ridge": ORANGE,
        "apmd_local_identifiability_dot_dual_ridge": PURPLE,
    }


def prepare_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    jf, jd = stage6.load_sensitivity_tables()
    train = prepare_training_states()
    heldout = load_heldout_states()
    train = stage6.add_local_identifiability_features(train, jf, jd)
    heldout = stage6.add_local_identifiability_features(heldout, jf, jd)
    return train, heldout


def fit_predict_heldout(train: pd.DataFrame, heldout: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    leaked = _session_id_set(HELDOUT_SESSION_IDS) & set(train["session_id"].astype(str))
    if leaked:
        raise ValueError(f"held-out session leaked into training: {sorted(leaked)}")

    y_train = train[TARGETS].to_numpy(float)
    pred_rows: list[pd.DataFrame] = []
    keep_cols = [
        "experiment",
        "path_family",
        "session_id",
        "trial",
        "pair_id",
        "cycle_index",
        "state_index",
        "branch",
        "state_label",
        "path_label",
        "d_target_mm",
        "F_N",
        "d_mm",
        "local_zone_id",
        "local_jF_source_zone",
        "local_p_F_uT",
        "local_p_d_uT",
        "local_residual_uT",
        "local_dual_c_F_uT",
        "local_dual_c_d_uT",
        "local_dual_residual_uT",
        "local_dual_residual_fraction",
        "local_geometry_confidence",
        "local_geometry_uncertainty",
        "local_angle_deg",
        "local_scaled_condition",
    ]

    for name, family, model, features in model_specs():
        features = list(dict.fromkeys(features))
        train_ready = stage6._ensure_features(train, features)
        heldout_ready = stage6._ensure_features(heldout, features)
        fitted = model.fit(train_ready[features], y_train)
        pred = fitted.predict(heldout_ready[features])

        out = stage6._ensure_features(heldout_ready, keep_cols)[keep_cols].copy()
        out["model"] = name
        out["model_family"] = family
        out["F_pred_N"] = pred[:, 0]
        out["d_pred_mm"] = pred[:, 1]
        out["F_error_N"] = out["F_pred_N"] - out["F_N"]
        out["d_error_mm"] = out["d_pred_mm"] - out["d_mm"]
        pred_rows.append(out)

    predictions = pd.concat(pred_rows, ignore_index=True)
    metrics = pd.DataFrame([stage6._metric_row(model, chunk, len(train)) for model, chunk in predictions.groupby("model")])
    metrics = stage6._add_relative_metrics(metrics)
    metrics = metrics.sort_values(["F_MAE_N", "d_MAE_mm"]).reset_index(drop=True)
    return metrics, predictions


def pair_consistency(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    usable = predictions[predictions["path_label"].isin(["direct_loading", "return_unloading"])].copy()
    usable["d_target_mm"] = pd.to_numeric(usable["d_target_mm"], errors="coerce")
    usable = usable.dropna(subset=["d_target_mm"])

    group_cols = ["model", "session_id", "cycle_index", "d_target_mm"]
    for keys, chunk in usable.groupby(group_cols):
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
                "model": keys[0],
                "session_id": keys[1],
                "cycle_index": keys[2],
                "d_target_mm": keys[3],
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
        summary = pd.DataFrame()
    else:
        summary = (
            pair_df.groupby("model")
            .agg(
                pair_n=("model", "size"),
                pair_delta_F_MAE_N=("abs_delta_F_residual_N", "mean"),
                pair_delta_d_MAE_mm=("abs_delta_d_residual_mm", "mean"),
            )
            .reset_index()
        )
    return pair_df, summary


def confidence_summary(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for model, chunk in predictions.groupby("model"):
        data = chunk.copy()
        data["abs_F_error_N"] = data["F_error_N"].abs()
        data["abs_d_error_mm"] = data["d_error_mm"].abs()
        for feature in ["local_geometry_confidence", "local_geometry_uncertainty", "local_dual_residual_fraction"]:
            vals = pd.to_numeric(data[feature], errors="coerce").replace([np.inf, -np.inf], np.nan)
            finite = data.loc[vals.notna()].copy()
            finite[feature] = vals[vals.notna()]
            if len(finite) < 5:
                corr_f = math.nan
                corr_d = math.nan
            else:
                corr_f = float(finite[feature].corr(finite["abs_F_error_N"], method="spearman"))
                corr_d = float(finite[feature].corr(finite["abs_d_error_mm"], method="spearman"))
            rows.append(
                {
                    "model": model,
                    "feature": feature,
                    "spearman_abs_F_error": corr_f,
                    "spearman_abs_d_error": corr_d,
                    "n": int(len(finite)),
                }
            )
    return pd.DataFrame(rows)


def _add_value_labels(ax: plt.Axes, x: np.ndarray, values: pd.Series, fmt: str) -> None:
    upper = float(values.max()) if len(values) else 0.0
    offset = upper * 0.025 if upper > 0 else 0.02
    for xpos, value in zip(x, values):
        ax.text(xpos, float(value) + offset, fmt.format(float(value)), ha="center", va="bottom", fontsize=7)


def plot_results(
    metrics: pd.DataFrame,
    predictions: pd.DataFrame,
    pair_summary: pd.DataFrame,
    confidence: pd.DataFrame,
) -> None:
    order = model_order()
    labels = [model_labels()[name] for name in order]
    colors = [model_colors()[name] for name in order]
    metric_index = metrics.set_index("model")
    pair_index = pair_summary.set_index("model") if not pair_summary.empty else pd.DataFrame()

    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.0), dpi=220)
    ax1, ax2, ax3, ax4 = axes.ravel()
    x = np.arange(len(order))

    f_values = metric_index.loc[order, "F_MAE_N"]
    d_values = metric_index.loc[order, "d_MAE_mm"]
    ax1.bar(x, f_values, color=colors, width=0.72)
    ax1.axhline(0.75, color="#777777", linestyle=":", linewidth=1.0, label="current F goal")
    ax1.axhline(0.50, color=RED, linestyle=":", linewidth=1.0, label="ideal F goal")
    ax1.set_title("a  Held-out force error")
    ax1.set_ylabel("F MAE (N)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=8)
    ax1.grid(axis="y", color=LIGHT_GRAY, linewidth=0.8)
    ax1.legend(frameon=False, fontsize=7)
    _add_value_labels(ax1, x, f_values, "{:.3f}")

    ax2.bar(x, d_values, color=colors, width=0.72)
    ax2.axhline(0.05, color=RED, linestyle=":", linewidth=1.0, label="d goal")
    ax2.set_title("b  Held-out displacement error")
    ax2.set_ylabel("d MAE (mm)")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=8)
    ax2.grid(axis="y", color=LIGHT_GRAY, linewidth=0.8)
    ax2.legend(frameon=False, fontsize=7)
    _add_value_labels(ax2, x, d_values, "{:.3f}")

    if not pair_summary.empty:
        pair_values = pair_index.loc[order, "pair_delta_F_MAE_N"]
        ax3.bar(x, pair_values, color=colors, width=0.72)
        _add_value_labels(ax3, x, pair_values, "{:.3f}")
    ax3.set_title("c  Same-d pair force-split consistency")
    ax3.set_ylabel("|predicted - measured Delta F| (N)")
    ax3.set_xticks(x)
    ax3.set_xticklabels(labels, fontsize=8)
    ax3.grid(axis="y", color=LIGHT_GRAY, linewidth=0.8)

    best = "apmd_local_identifiability_dot_dual_ridge"
    best_df = predictions[predictions["model"] == best].copy()
    best_df["abs_F_error_N"] = best_df["F_error_N"].abs()
    best_df["local_geometry_uncertainty"] = pd.to_numeric(best_df["local_geometry_uncertainty"], errors="coerce")
    best_df = best_df.replace([np.inf, -np.inf], np.nan).dropna(subset=["local_geometry_uncertainty", "abs_F_error_N"])
    colors_by_label = {
        "direct_loading": BLACK,
        "return_unloading": BLUE,
        "preload_deep": GRAY,
    }
    for label, chunk in best_df.groupby("path_label"):
        ax4.scatter(
            chunk["local_geometry_uncertainty"],
            chunk["abs_F_error_N"],
            s=20,
            color=colors_by_label.get(label, GRAY),
            alpha=0.75,
            edgecolor="white",
            linewidth=0.3,
            label=label.replace("_", " "),
        )
    if len(best_df) >= 5:
        corr = best_df["local_geometry_uncertainty"].corr(best_df["abs_F_error_N"], method="spearman")
        ax4.text(
            0.03,
            0.95,
            f"Spearman rho = {corr:.2f}",
            transform=ax4.transAxes,
            ha="left",
            va="top",
            fontsize=8,
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": LIGHT_GRAY},
        )
    ax4.set_xscale("log")
    ax4.set_title("d  Geometry uncertainty vs force error")
    ax4.set_xlabel("local geometry uncertainty (log scale)")
    ax4.set_ylabel("|F error| (N)")
    ax4.grid(color=LIGHT_GRAY, linewidth=0.8)
    ax4.legend(frameon=False, fontsize=7, loc="upper right")

    for ax in axes.ravel():
        ax.set_axisbelow(True)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)

    train_n = int(metric_index.iloc[0]["train_n_states"])
    heldout_n = int(metric_index.iloc[0]["heldout_n_states"])
    fig.suptitle(
        "Stage 6.4: dual-coordinate local-identifiability check",
        x=0.02,
        y=0.99,
        ha="left",
        fontsize=15,
        fontweight="bold",
    )
    fig.text(
        0.02,
        0.955,
        f"Train = {train_n} states; held-out = {heldout_n} states. Same split, ridge estimator, feature-family ablation.",
        ha="left",
        va="top",
        fontsize=9,
        color="#555555",
    )
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.92])
    fig.savefig(OUT_FIGURE, bbox_inches="tight")
    fig.savefig(OUT_FIGURE_PDF, bbox_inches="tight")
    plt.close(fig)


def write_report(
    metrics: pd.DataFrame,
    pair_summary: pd.DataFrame,
    confidence: pd.DataFrame,
    train_n: int,
    heldout_n: int,
) -> None:
    metric_index = metrics.set_index("model")
    best_force = metrics.sort_values("F_MAE_N").iloc[0]
    best_d = metrics.sort_values("d_MAE_mm").iloc[0]
    dot_dual = metric_index.loc["apmd_local_identifiability_dot_dual_ridge"]
    lim = metric_index.loc["lim_style_branch_ridge"]
    force_improve = (lim["F_MAE_N"] - dot_dual["F_MAE_N"]) / lim["F_MAE_N"] * 100.0

    pair_table = pair_summary.sort_values("pair_delta_F_MAE_N").to_markdown(index=False) if not pair_summary.empty else "_No matched pairs found._"
    conf_table = confidence.to_markdown(index=False)
    metrics_table = metrics.to_markdown(index=False)

    text = f"""# Stage 6.4 Dual-Coordinate Local-Identifiability Check

This report uses the current accepted multi-zone dense-loop dataset without
modifying any experimental records.

## Data Split

- Training states: `{train_n}`
- Held-out states: `{heldout_n}`
- Held-out sessions are excluded from training before fitting.
- Estimator: ridge regression for every model family, so this is a feature
  ablation rather than an estimator-capacity comparison.

## What Was Added

The previous local-ID model used dot projections:

```text
p_F = Delta B dot unit(j_F)
p_d = Delta B dot unit(j_d)
```

This check adds a dual-coordinate solve:

```text
[c_F, c_d]^T = (U^T U)^-1 U^T Delta B
U = [unit(j_F), unit(j_d)]
```

The dual solve estimates how much of the observed magnetic state lies along the
local force-like direction and the local displacement-like direction
simultaneously. It also records the residual fraction and a geometry confidence
score derived from angle, condition number, distance to the nearest local
sensitivity calibration, and residual fraction.

## Model Families Compared

1. Plain magnetic ridge: `B -> F,d`
2. Branch-label ridge: `B + loading/unloading/preload label -> F,d`
3. Path-memory ridge: `B + path history -> F,d`
4. Local-ID dot ridge: `B + path history + dot projections -> F,d`
5. Local-ID dual ridge: `B + path history + dual coordinates -> F,d`
6. Local-ID dot+dual ridge: `B + path history + dot + dual -> F,d`

## Key Result

- Best force MAE: `{best_force['model']}` with `F_MAE = {best_force['F_MAE_N']:.3f} N`.
- Best displacement MAE: `{best_d['model']}` with `d_MAE = {best_d['d_MAE_mm']:.4f} mm`.
- Dot+dual local-ID ridge: `F_MAE = {dot_dual['F_MAE_N']:.3f} N`,
  `d_MAE = {dot_dual['d_MAE_mm']:.4f} mm`.
- Compared with the Lim-style branch-label baseline, dot+dual local-ID changes
  force MAE by `{force_improve:.1f}%`.

## Metrics

{metrics_table}

## Pair Consistency

This evaluates whether the model preserves same-d loading/return force-split
structure in held-out dense-loop pairs.

{pair_table}

## Geometry Confidence

Positive correlation with error means the confidence/uncertainty feature is
useful as a warning flag; weak correlation means it is mostly descriptive.

{conf_table}

## Figure

![Stage 6.4 dual-coordinate local-ID check](apmd_stage6_dual_coordinate_model_comparison.png)

## Interpretation

The dual-coordinate model is not a new experiment. It is a stricter test of the
APMD claim that actively measured local `j_F/j_d` geometry can be used as a
model coordinate. If the dual or dot+dual feature family outperforms plain
magnetic and branch-label baselines on the same held-out sessions, then the
benefit comes from local response geometry rather than merely giving the model a
loading/unloading label.
"""
    OUT_REPORT.write_text(text, encoding="utf-8")


def main() -> None:
    train, heldout = prepare_data()
    metrics, predictions = fit_predict_heldout(train, heldout)
    pair_df, pair_summary = pair_consistency(predictions)
    confidence = confidence_summary(predictions)

    OUT_METRICS.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(OUT_METRICS, index=False)
    predictions.to_csv(OUT_PREDICTIONS, index=False)
    pair_df.to_csv(OUT_PAIR, index=False)
    confidence.to_csv(OUT_CONFIDENCE, index=False)

    plot_results(metrics, predictions, pair_summary, confidence)
    write_report(metrics, pair_summary, confidence, len(train), len(heldout))

    print("Stage 6.4 dual-coordinate local-ID check complete.")
    print(f"  metrics    : {OUT_METRICS}")
    print(f"  predictions: {OUT_PREDICTIONS}")
    print(f"  figure     : {OUT_FIGURE}")
    print(f"  report     : {OUT_REPORT}")


if __name__ == "__main__":
    main()
