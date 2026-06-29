"""Stage 6.4 MLP check for dual-coordinate local-identifiability features.

This script uses the same accepted multi-zone train/held-out split as
``apmd_stage6_dual_coordinate_model_check.py``.  The only intended change is the
estimator: every feature family is fit with the same small tabular MLP.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import apmd_stage6_compare_local_identifiability_models as stage6
import apmd_stage6_dual_coordinate_model_check as dual6
from apmd_stage6_predict_local_heldout import TARGETS, HELDOUT_SESSION_IDS

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports"

OUT_METRICS = REPORTS_DIR / "apmd_stage6_dual_coordinate_mlp_metrics.csv"
OUT_PREDICTIONS = REPORTS_DIR / "apmd_stage6_dual_coordinate_mlp_predictions.csv"
OUT_PAIR = REPORTS_DIR / "apmd_stage6_dual_coordinate_mlp_pair_consistency.csv"
OUT_CONFIDENCE = REPORTS_DIR / "apmd_stage6_dual_coordinate_mlp_confidence.csv"
OUT_FIGURE = REPORTS_DIR / "apmd_stage6_dual_coordinate_mlp_comparison.png"
OUT_FIGURE_PDF = REPORTS_DIR / "apmd_stage6_dual_coordinate_mlp_comparison.pdf"
OUT_REPORT = REPORTS_DIR / "APMD_STAGE6_DUAL_COORDINATE_MLP_REPORT.md"

BLACK = "#222222"
BLUE = "#2c7fb8"
GRAY = "#8a8a8a"
RED = "#c43c39"
ORANGE = "#d98c2b"
PURPLE = "#7b61a8"
LIGHT_GRAY = "#e8e8e8"

CATEGORICAL_FEATURES = {
    "path_family",
    "path_label",
    "local_zone_id",
    "local_jF_source_zone",
}


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(math.sqrt(mean_squared_error(y_true, y_pred)))


def _set_figure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "axes.linewidth": 0.9,
            "axes.labelsize": 9.5,
            "axes.titlesize": 11.0,
            "xtick.labelsize": 8.4,
            "ytick.labelsize": 8.4,
            "legend.fontsize": 7.8,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def _mlp_model(numeric_features: list[str], categorical_features: list[str]) -> Pipeline:
    mlp = MLPRegressor(
        hidden_layer_sizes=(32, 16),
        activation="relu",
        solver="lbfgs",
        alpha=1e-2,
        max_iter=8000,
        max_fun=50000,
        random_state=42,
    )
    return Pipeline(
        steps=[
            ("preprocess", stage6._preprocess(numeric_features, categorical_features)),
            ("model", TransformedTargetRegressor(regressor=mlp, transformer=StandardScaler())),
        ]
    )


def model_specs() -> list[tuple[str, str, Pipeline, list[str]]]:
    specs: list[tuple[str, str, Pipeline, list[str]]] = []
    for ridge_name, family, _ridge_model, features in dual6.model_specs():
        features = list(dict.fromkeys(features))
        categorical = [feature for feature in features if feature in CATEGORICAL_FEATURES]
        numeric = [feature for feature in features if feature not in CATEGORICAL_FEATURES]
        mlp_name = ridge_name.replace("_ridge", "_mlp")
        specs.append((mlp_name, family, _mlp_model(numeric, categorical), features))
    return specs


def model_order() -> list[str]:
    return [spec[0] for spec in model_specs()]


def model_labels() -> dict[str, str]:
    return {
        "plain_magnetic_mlp": "plain\nmagnetic",
        "lim_style_branch_mlp": "branch\nlabel",
        "apmd_path_memory_mlp": "path\nmemory",
        "apmd_local_identifiability_dot_mlp": "local-ID\ndot",
        "apmd_local_identifiability_dual_mlp": "local-ID\ndual",
        "apmd_local_identifiability_dot_dual_mlp": "local-ID\ndot+dual",
    }


def model_colors() -> dict[str, str]:
    return {
        "plain_magnetic_mlp": BLACK,
        "lim_style_branch_mlp": BLUE,
        "apmd_path_memory_mlp": GRAY,
        "apmd_local_identifiability_dot_mlp": RED,
        "apmd_local_identifiability_dual_mlp": ORANGE,
        "apmd_local_identifiability_dot_dual_mlp": PURPLE,
    }


def _metric_row(model: str, chunk: pd.DataFrame, train_n_states: int) -> dict[str, object]:
    f_true = chunk["F_N"].to_numpy(float)
    f_pred = chunk["F_pred_N"].to_numpy(float)
    d_true = chunk["d_mm"].to_numpy(float)
    d_pred = chunk["d_pred_mm"].to_numpy(float)
    return {
        "model": model,
        "model_family": str(chunk["model_family"].iloc[0]),
        "train_n_states": train_n_states,
        "heldout_n_states": len(chunk),
        "F_MAE_N": mean_absolute_error(f_true, f_pred),
        "F_RMSE_N": _rmse(f_true, f_pred),
        "F_R2": r2_score(f_true, f_pred),
        "d_MAE_mm": mean_absolute_error(d_true, d_pred),
        "d_RMSE_mm": _rmse(d_true, d_pred),
        "d_R2": r2_score(d_true, d_pred),
    }


def _add_relative_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    out = metrics.copy()
    plain = out[out["model"] == "plain_magnetic_mlp"].iloc[0]
    lim = out[out["model"] == "lim_style_branch_mlp"].iloc[0]
    out["F_MAE_vs_plain_mlp_pct"] = (plain["F_MAE_N"] - out["F_MAE_N"]) / plain["F_MAE_N"] * 100.0
    out["d_MAE_vs_plain_mlp_pct"] = (plain["d_MAE_mm"] - out["d_MAE_mm"]) / plain["d_MAE_mm"] * 100.0
    out["F_MAE_vs_lim_style_mlp_pct"] = (lim["F_MAE_N"] - out["F_MAE_N"]) / lim["F_MAE_N"] * 100.0
    out["d_MAE_vs_lim_style_mlp_pct"] = (lim["d_MAE_mm"] - out["d_MAE_mm"]) / lim["d_MAE_mm"] * 100.0
    out["passes_current_F_goal"] = out["F_MAE_N"] <= 0.75
    out["passes_ideal_F_goal"] = out["F_MAE_N"] <= 0.50
    out["passes_d_goal"] = out["d_MAE_mm"] <= 0.05
    return out


def fit_predict_heldout(train: pd.DataFrame, heldout: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    leaked = dual6._session_id_set(HELDOUT_SESSION_IDS) & set(train["session_id"].astype(str))
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
    metrics = pd.DataFrame([_metric_row(model, chunk, len(train)) for model, chunk in predictions.groupby("model")])
    metrics = _add_relative_metrics(metrics)
    metrics = metrics.sort_values(["F_MAE_N", "d_MAE_mm"]).reset_index(drop=True)
    return metrics, predictions


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
    _set_figure_style()
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

    best = "apmd_local_identifiability_dot_dual_mlp"
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
        "Stage 6.4: MLP dual-coordinate local-identifiability check",
        x=0.02,
        y=0.99,
        ha="left",
        fontsize=15,
        fontweight="bold",
    )
    fig.text(
        0.02,
        0.955,
        f"Train = {train_n} states; held-out = {heldout_n} states. Same split, MLP estimator, feature-family ablation.",
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
    dot_dual = metric_index.loc["apmd_local_identifiability_dot_dual_mlp"]
    lim = metric_index.loc["lim_style_branch_mlp"]
    force_improve = (lim["F_MAE_N"] - dot_dual["F_MAE_N"]) / lim["F_MAE_N"] * 100.0

    ridge_text = ""
    if dual6.OUT_METRICS.exists():
        ridge = pd.read_csv(dual6.OUT_METRICS).set_index("model")
        ridge_dot_dual = ridge.loc["apmd_local_identifiability_dot_dual_ridge"]
        ridge_text = (
            f"- Ridge dot+dual reference: `F_MAE = {ridge_dot_dual['F_MAE_N']:.3f} N`, "
            f"`d_MAE = {ridge_dot_dual['d_MAE_mm']:.4f} mm`.\n"
        )

    pair_table = pair_summary.sort_values("pair_delta_F_MAE_N").to_markdown(index=False) if not pair_summary.empty else "_No matched pairs found._"
    conf_table = confidence.to_markdown(index=False)
    metrics_table = metrics.to_markdown(index=False)

    text = f"""# Stage 6.4 MLP Dual-Coordinate Local-Identifiability Check

This report uses the current accepted multi-zone dense-loop dataset without
modifying any experimental records.

## Data Split

- Training states: `{train_n}`
- Held-out states: `{heldout_n}`
- Held-out sessions are excluded from training before fitting.
- Estimator: small tabular MLP for every model family, so this is an
  estimator-capacity check using the same feature-family ablation as the ridge
  Stage 6.4 figure.

## Model Families Compared

1. Plain magnetic MLP: `B -> F,d`
2. Branch-label MLP: `B + loading/unloading/preload label -> F,d`
3. Path-memory MLP: `B + path history -> F,d`
4. Local-ID dot MLP: `B + path history + dot projections -> F,d`
5. Local-ID dual MLP: `B + path history + dual coordinates -> F,d`
6. Local-ID dot+dual MLP: `B + path history + dot + dual -> F,d`

## Key Result

- Best force MAE: `{best_force['model']}` with `F_MAE = {best_force['F_MAE_N']:.3f} N`.
- Best displacement MAE: `{best_d['model']}` with `d_MAE = {best_d['d_MAE_mm']:.4f} mm`.
- Dot+dual local-ID MLP: `F_MAE = {dot_dual['F_MAE_N']:.3f} N`,
  `d_MAE = {dot_dual['d_MAE_mm']:.4f} mm`.
- Compared with the Lim-style branch-label MLP baseline, dot+dual local-ID
  changes force MAE by `{force_improve:.1f}%`.
{ridge_text}
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

![Stage 6.4 MLP dual-coordinate local-ID check](apmd_stage6_dual_coordinate_mlp_comparison.png)

## Interpretation

This MLP check answers whether the local-ID feature advantage is only an artifact
of linear ridge regression. If local-ID MLP still outperforms plain magnetic and
branch-label MLP on the same held-out sessions, then the active-path local
geometry remains useful even when the estimator has nonlinear capacity.
"""
    OUT_REPORT.write_text(text, encoding="utf-8")


def main() -> None:
    train, heldout = dual6.prepare_data()
    metrics, predictions = fit_predict_heldout(train, heldout)
    pair_df, pair_summary = dual6.pair_consistency(predictions)
    confidence = dual6.confidence_summary(predictions)

    OUT_METRICS.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(OUT_METRICS, index=False)
    predictions.to_csv(OUT_PREDICTIONS, index=False)
    pair_df.to_csv(OUT_PAIR, index=False)
    confidence.to_csv(OUT_CONFIDENCE, index=False)

    plot_results(metrics, predictions, pair_summary, confidence)
    write_report(metrics, pair_summary, confidence, len(train), len(heldout))

    print("Stage 6.4 MLP dual-coordinate local-ID check complete")
    print(f"  metrics    : {OUT_METRICS}")
    print(f"  predictions: {OUT_PREDICTIONS}")
    print(f"  figure     : {OUT_FIGURE}")
    print(f"  report     : {OUT_REPORT}")
    print(metrics[["model", "F_MAE_N", "d_MAE_mm", "F_MAE_vs_lim_style_mlp_pct"]].to_string(index=False))


if __name__ == "__main__":
    main()
