"""Stage 6.5 linear estimator sweep for local-ID dot+dual features.

This is an estimator-only check.  It keeps the same accepted multi-zone
train/held-out split and the same APMD local-identifiability dot+dual feature
family used in Stage 6.4, then swaps the linear estimator.
"""

from __future__ import annotations

import math
import sys
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.cross_decomposition import PLSRegression
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import BayesianRidge, ElasticNetCV, HuberRegressor, Ridge, RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.multioutput import MultiOutputRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import apmd_stage6_compare_local_identifiability_models as stage6
import apmd_stage6_dual_coordinate_model_check as dual6
from apmd_stage6_predict_local_heldout import HELDOUT_SESSION_IDS, TARGETS

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports"

OUT_METRICS = REPORTS_DIR / "apmd_stage6_linear_estimator_sweep_metrics.csv"
OUT_PREDICTIONS = REPORTS_DIR / "apmd_stage6_linear_estimator_sweep_predictions.csv"
OUT_PAIR = REPORTS_DIR / "apmd_stage6_linear_estimator_sweep_pair_consistency.csv"
OUT_PAIR_SUMMARY = REPORTS_DIR / "apmd_stage6_linear_estimator_sweep_pair_summary.csv"
OUT_COMPARISON_FIGURE = REPORTS_DIR / "apmd_stage6_linear_estimator_sweep_comparison.png"
OUT_COMPARISON_PDF = REPORTS_DIR / "apmd_stage6_linear_estimator_sweep_comparison.pdf"
OUT_BEST_FIT_FIGURE = REPORTS_DIR / "apmd_stage6_linear_estimator_sweep_best_fit.png"
OUT_BEST_FIT_PDF = REPORTS_DIR / "apmd_stage6_linear_estimator_sweep_best_fit.pdf"
OUT_REPORT = REPORTS_DIR / "APMD_STAGE6_LINEAR_ESTIMATOR_SWEEP_REPORT.md"

BLACK = "#222222"
BLUE = "#2c7fb8"
GRAY = "#8a8a8a"
RED = "#c43c39"
ORANGE = "#d98c2b"
PURPLE = "#7b61a8"
GREEN = "#4c9f70"
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
            "axes.labelsize": 9.2,
            "axes.titlesize": 10.5,
            "xtick.labelsize": 8.2,
            "ytick.labelsize": 8.2,
            "legend.fontsize": 7.8,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def local_id_dot_dual_features() -> list[str]:
    """Return the exact Stage 6.4 local-ID dot+dual feature set."""

    for name, _family, _model, features in dual6.model_specs():
        if name == "apmd_local_identifiability_dot_dual_ridge":
            return list(dict.fromkeys(features))
    raise RuntimeError("Could not find Stage 6.4 dot+dual feature set.")


def _linear_model(estimator: object, numeric_features: list[str], categorical_features: list[str]) -> Pipeline:
    return Pipeline(
        steps=[
            ("preprocess", stage6._preprocess(numeric_features, categorical_features)),
            (
                "model",
                TransformedTargetRegressor(
                    regressor=estimator,
                    transformer=StandardScaler(),
                ),
            ),
        ]
    )


def model_specs() -> list[tuple[str, str, Pipeline]]:
    features = local_id_dot_dual_features()
    categorical = [feature for feature in features if feature in CATEGORICAL_FEATURES]
    numeric = [feature for feature in features if feature not in CATEGORICAL_FEATURES]

    alphas = np.logspace(-4, 4, 25)
    return [
        (
            "ridge_alpha1",
            "Ridge alpha=1",
            _linear_model(Ridge(alpha=1.0), numeric, categorical),
        ),
        (
            "ridge_cv",
            "RidgeCV",
            _linear_model(RidgeCV(alphas=alphas), numeric, categorical),
        ),
        (
            "bayesian_ridge",
            "BayesianRidge",
            _linear_model(MultiOutputRegressor(BayesianRidge()), numeric, categorical),
        ),
        (
            "elastic_net_cv",
            "ElasticNetCV",
            _linear_model(
                MultiOutputRegressor(
                    ElasticNetCV(
                        l1_ratio=[0.05, 0.1, 0.3, 0.5, 0.8, 0.95],
                        alphas=np.logspace(-5, 1, 35),
                        cv=5,
                        max_iter=50000,
                        random_state=42,
                    )
                ),
                numeric,
                categorical,
            ),
        ),
        (
            "huber",
            "Huber",
            _linear_model(
                MultiOutputRegressor(HuberRegressor(epsilon=1.35, alpha=1e-4, max_iter=3000)),
                numeric,
                categorical,
            ),
        ),
        (
            "pls8",
            "PLS 8 comp.",
            _linear_model(PLSRegression(n_components=8, scale=False), numeric, categorical),
        ),
    ]


def model_order() -> list[str]:
    return [name for name, _label, _model in model_specs()]


def model_labels() -> dict[str, str]:
    return {
        "ridge_alpha1": "ridge\nalpha=1",
        "ridge_cv": "ridge\nCV",
        "bayesian_ridge": "bayesian\nridge",
        "elastic_net_cv": "elastic\nnet CV",
        "huber": "huber",
        "pls8": "PLS\n8 comp.",
    }


def model_colors() -> dict[str, str]:
    return {
        "ridge_alpha1": BLACK,
        "ridge_cv": BLUE,
        "bayesian_ridge": GRAY,
        "elastic_net_cv": RED,
        "huber": ORANGE,
        "pls8": PURPLE,
    }


def _metric_row(model: str, estimator_label: str, chunk: pd.DataFrame, train_n_states: int) -> dict[str, object]:
    f_true = chunk["F_N"].to_numpy(float)
    f_pred = chunk["F_pred_N"].to_numpy(float)
    d_true = chunk["d_mm"].to_numpy(float)
    d_pred = chunk["d_pred_mm"].to_numpy(float)
    f_mae = mean_absolute_error(f_true, f_pred)
    d_mae = mean_absolute_error(d_true, d_pred)
    return {
        "model": model,
        "estimator": estimator_label,
        "model_family": "APMD local-ID dot+dual",
        "train_n_states": train_n_states,
        "heldout_n_states": len(chunk),
        "F_MAE_N": f_mae,
        "F_RMSE_N": _rmse(f_true, f_pred),
        "F_R2": r2_score(f_true, f_pred),
        "d_MAE_mm": d_mae,
        "d_RMSE_mm": _rmse(d_true, d_pred),
        "d_R2": r2_score(d_true, d_pred),
        "passes_current_F_goal": f_mae <= 0.75,
        "passes_ideal_F_goal": f_mae <= 0.50,
        "passes_d_goal": d_mae <= 0.05,
        "balanced_score_ideal": f_mae / 0.50 + d_mae / 0.05,
    }


def fit_predict_heldout(train: pd.DataFrame, heldout: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    leaked = dual6._session_id_set(HELDOUT_SESSION_IDS) & set(train["session_id"].astype(str))
    if leaked:
        raise ValueError(f"held-out session leaked into training: {sorted(leaked)}")

    features = local_id_dot_dual_features()
    y_train = train[TARGETS].to_numpy(float)
    pred_rows: list[pd.DataFrame] = []
    metric_rows: list[dict[str, object]] = []
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

    train_ready = stage6._ensure_features(train, features)
    heldout_ready = stage6._ensure_features(heldout, features)

    for name, estimator_label, model in model_specs():
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=ConvergenceWarning)
            fitted = model.fit(train_ready[features], y_train)
        pred = fitted.predict(heldout_ready[features])

        out = stage6._ensure_features(heldout_ready, keep_cols)[keep_cols].copy()
        out["model"] = name
        out["estimator"] = estimator_label
        out["model_family"] = "APMD local-ID dot+dual"
        out["F_pred_N"] = pred[:, 0]
        out["d_pred_mm"] = pred[:, 1]
        out["F_error_N"] = out["F_pred_N"] - out["F_N"]
        out["d_error_mm"] = out["d_pred_mm"] - out["d_mm"]
        pred_rows.append(out)
        metric_rows.append(_metric_row(name, estimator_label, out, len(train)))

    predictions = pd.concat(pred_rows, ignore_index=True)
    metrics = pd.DataFrame(metric_rows).sort_values(["balanced_score_ideal", "F_MAE_N"]).reset_index(drop=True)
    return metrics, predictions


def _add_value_labels(ax: plt.Axes, x: np.ndarray, values: pd.Series, fmt: str) -> None:
    upper = float(values.max()) if len(values) else 0.0
    offset = upper * 0.025 if upper > 0 else 0.02
    for xpos, value in zip(x, values):
        ax.text(xpos, float(value) + offset, fmt.format(float(value)), ha="center", va="bottom", fontsize=7)


def plot_comparison(metrics: pd.DataFrame, pair_summary: pd.DataFrame) -> None:
    _set_figure_style()
    order = model_order()
    labels = [model_labels()[name] for name in order]
    colors = [model_colors()[name] for name in order]
    metric_index = metrics.set_index("model")
    pair_index = pair_summary.set_index("model") if not pair_summary.empty else pd.DataFrame()

    fig, axes = plt.subplots(2, 2, figsize=(12.0, 7.5), dpi=240)
    ax1, ax2, ax3, ax4 = axes.ravel()
    x = np.arange(len(order))

    f_values = metric_index.loc[order, "F_MAE_N"]
    d_values = metric_index.loc[order, "d_MAE_mm"]
    ax1.bar(x, f_values, color=colors, width=0.72)
    ax1.axhline(0.75, color="#777777", linestyle=":", linewidth=1.0, label="current F goal")
    ax1.axhline(0.50, color=RED, linestyle=":", linewidth=1.0, label="ideal F goal")
    ax1.set_title("a  Held-out force MAE")
    ax1.set_ylabel("F MAE (N)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.grid(axis="y", color=LIGHT_GRAY, linewidth=0.8)
    ax1.legend(frameon=False, fontsize=7)
    _add_value_labels(ax1, x, f_values, "{:.3f}")

    ax2.bar(x, d_values, color=colors, width=0.72)
    ax2.axhline(0.05, color=RED, linestyle=":", linewidth=1.0, label="d goal")
    ax2.set_title("b  Held-out displacement MAE")
    ax2.set_ylabel("d MAE (mm)")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.grid(axis="y", color=LIGHT_GRAY, linewidth=0.8)
    ax2.legend(frameon=False, fontsize=7, loc="upper right")
    _add_value_labels(ax2, x, d_values, "{:.3f}")

    if not pair_summary.empty:
        pair_values = pair_index.loc[order, "pair_delta_F_MAE_N"]
        ax3.bar(x, pair_values, color=colors, width=0.72)
        _add_value_labels(ax3, x, pair_values, "{:.3f}")
    ax3.set_title("c  Same-d pair force-split consistency")
    ax3.set_ylabel("|predicted - measured Delta F| (N)")
    ax3.set_xticks(x)
    ax3.set_xticklabels(labels)
    ax3.grid(axis="y", color=LIGHT_GRAY, linewidth=0.8)

    best = metrics.sort_values(["balanced_score_ideal", "F_MAE_N"]).iloc[0]["model"]
    for _, row in metrics.iterrows():
        model = row["model"]
        ax4.scatter(
            row["d_MAE_mm"],
            row["F_MAE_N"],
            s=80 if model == best else 55,
            color=model_colors()[model],
            edgecolor="black" if model == best else "white",
            linewidth=0.9 if model == best else 0.4,
            label=model_labels()[model].replace("\n", " "),
            zorder=3 if model == best else 2,
        )
    ax4.axhline(0.75, color="#777777", linestyle=":", linewidth=1.0)
    ax4.axhline(0.50, color=RED, linestyle=":", linewidth=1.0)
    ax4.axvline(0.05, color=RED, linestyle=":", linewidth=1.0)
    ax4.set_title("d  Force-displacement tradeoff")
    ax4.set_xlabel("d MAE (mm)")
    ax4.set_ylabel("F MAE (N)")
    ax4.grid(color=LIGHT_GRAY, linewidth=0.8)
    ax4.legend(frameon=False, fontsize=6.8, loc="upper left")

    for ax in axes.ravel():
        ax.set_axisbelow(True)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)

    train_n = int(metric_index.iloc[0]["train_n_states"])
    heldout_n = int(metric_index.iloc[0]["heldout_n_states"])
    fig.suptitle(
        "Stage 6.5: linear estimator sweep with fixed local-ID dot+dual features",
        x=0.02,
        y=0.99,
        ha="left",
        fontsize=15,
        fontweight="bold",
    )
    fig.text(
        0.02,
        0.955,
        f"Train = {train_n} states; held-out = {heldout_n} states. Same features and split; estimator is the only variable.",
        ha="left",
        va="top",
        fontsize=9,
        color="#555555",
    )
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.92])
    fig.savefig(OUT_COMPARISON_FIGURE, bbox_inches="tight")
    fig.savefig(OUT_COMPARISON_PDF, bbox_inches="tight")
    plt.close(fig)


def plot_best_fit(metrics: pd.DataFrame, predictions: pd.DataFrame) -> None:
    _set_figure_style()
    best = str(metrics.sort_values(["balanced_score_ideal", "F_MAE_N"]).iloc[0]["model"])
    best_row = metrics.set_index("model").loc[best]
    best_df = predictions[predictions["model"] == best].copy()
    colors = {
        "direct_loading": BLACK,
        "return_unloading": BLUE,
        "preload_deep": GRAY,
    }

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), dpi=240)
    ax1, ax2 = axes
    for label, chunk in best_df.groupby("path_label"):
        color = colors.get(label, GREEN)
        ax1.scatter(
            chunk["F_N"],
            chunk["F_pred_N"],
            s=24,
            color=color,
            alpha=0.78,
            edgecolor="white",
            linewidth=0.35,
            label=label.replace("_", " "),
        )
        ax2.scatter(
            chunk["d_mm"],
            chunk["d_pred_mm"],
            s=24,
            color=color,
            alpha=0.78,
            edgecolor="white",
            linewidth=0.35,
        )

    f_min = min(float(best_df["F_N"].min()), float(best_df["F_pred_N"].min()))
    f_max = max(float(best_df["F_N"].max()), float(best_df["F_pred_N"].max()))
    d_min = min(float(best_df["d_mm"].min()), float(best_df["d_pred_mm"].min()))
    d_max = max(float(best_df["d_mm"].max()), float(best_df["d_pred_mm"].max()))
    f_pad = (f_max - f_min) * 0.08
    d_pad = (d_max - d_min) * 0.12
    ax1.plot([f_min - f_pad, f_max + f_pad], [f_min - f_pad, f_max + f_pad], color=RED, linewidth=1.0, label="ideal 1:1")
    ax2.plot([d_min - d_pad, d_max + d_pad], [d_min - d_pad, d_max + d_pad], color=RED, linewidth=1.0)
    ax1.set_xlim(f_min - f_pad, f_max + f_pad)
    ax1.set_ylim(f_min - f_pad, f_max + f_pad)
    ax2.set_xlim(d_min - d_pad, d_max + d_pad)
    ax2.set_ylim(d_min - d_pad, d_max + d_pad)

    estimator = str(best_row["estimator"])
    ax1.set_title(f"a  Best linear estimator for force: {estimator}")
    ax1.set_xlabel("measured F (N)")
    ax1.set_ylabel("predicted F (N)")
    ax1.text(
        0.04,
        0.95,
        f"F MAE = {best_row['F_MAE_N']:.3f} N",
        transform=ax1.transAxes,
        ha="left",
        va="top",
        fontsize=8,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": LIGHT_GRAY},
    )
    ax1.legend(frameon=False, loc="lower right", fontsize=7)

    ax2.set_title("b  Same estimator for displacement")
    ax2.set_xlabel("measured d (mm)")
    ax2.set_ylabel("predicted d (mm)")
    ax2.text(
        0.04,
        0.95,
        f"d MAE = {best_row['d_MAE_mm']:.3f} mm",
        transform=ax2.transAxes,
        ha="left",
        va="top",
        fontsize=8,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": LIGHT_GRAY},
    )

    for ax in axes:
        ax.grid(color=LIGHT_GRAY, linewidth=0.8)
        ax.set_axisbelow(True)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)

    fig.suptitle(
        "Stage 6.5 best linear local-ID dot+dual fit",
        x=0.02,
        y=0.99,
        ha="left",
        fontsize=14,
        fontweight="bold",
    )
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.91])
    fig.savefig(OUT_BEST_FIT_FIGURE, bbox_inches="tight")
    fig.savefig(OUT_BEST_FIT_PDF, bbox_inches="tight")
    plt.close(fig)


def write_report(metrics: pd.DataFrame, pair_summary: pd.DataFrame, train_n: int, heldout_n: int) -> None:
    best_balanced = metrics.sort_values(["balanced_score_ideal", "F_MAE_N"]).iloc[0]
    best_force = metrics.sort_values("F_MAE_N").iloc[0]
    best_d = metrics.sort_values("d_MAE_mm").iloc[0]
    ridge_ref = metrics[metrics["model"] == "ridge_alpha1"].iloc[0]
    pair_table = pair_summary.sort_values("pair_delta_F_MAE_N").to_markdown(index=False) if not pair_summary.empty else "_No matched pairs found._"
    metrics_table = metrics.sort_values("balanced_score_ideal").to_markdown(index=False)

    text = f"""# Stage 6.5 Linear Estimator Sweep

This report keeps the Stage 6.4 multi-zone accepted train/held-out split and
the same APMD local-ID dot+dual features.  It changes only the linear estimator.

## Data Split

- Training states: `{train_n}`
- Held-out states: `{heldout_n}`
- Feature family: `B + path history + local-ID dot projections + local-ID dual coordinates`
- Held-out sessions are excluded from training before fitting.

## Why This Check Was Needed

Ridge regression had been the strongest stable baseline, but ridge is only one
linear regularized estimator.  This sweep asks whether another linear estimator
can give a better force/displacement tradeoff without changing the APMD feature
logic.

## Estimators Compared

1. Ridge, fixed `alpha=1.0`
2. RidgeCV over log-spaced alphas
3. BayesianRidge, wrapped as a multi-output model
4. ElasticNetCV, wrapped as a multi-output model
5. HuberRegressor, wrapped as a multi-output robust model
6. PLSRegression with 8 components

## Key Result

- Best balanced estimator: `{best_balanced['estimator']}` with
  `F_MAE = {best_balanced['F_MAE_N']:.3f} N`,
  `d_MAE = {best_balanced['d_MAE_mm']:.4f} mm`.
- Best force estimator: `{best_force['estimator']}` with
  `F_MAE = {best_force['F_MAE_N']:.3f} N`.
- Best displacement estimator: `{best_d['estimator']}` with
  `d_MAE = {best_d['d_MAE_mm']:.4f} mm`.
- Ridge alpha=1 reference:
  `F_MAE = {ridge_ref['F_MAE_N']:.3f} N`,
  `d_MAE = {ridge_ref['d_MAE_mm']:.4f} mm`.

## Metrics

{metrics_table}

## Same-d Pair Consistency

This checks whether the estimator preserves the measured loading/return
force-split structure within same-d held-out dense-loop pairs.

{pair_table}

## Figures

![Stage 6.5 linear estimator sweep](apmd_stage6_linear_estimator_sweep_comparison.png)

![Stage 6.5 best linear fit](apmd_stage6_linear_estimator_sweep_best_fit.png)

## Interpretation

This is an estimator-selection check, not a new mechanism claim.  If one of the
linear alternatives beats fixed ridge, it can be used as the cleaner baseline
for the current local-ID model.  If fixed ridge remains near-optimal, then the
main performance gain is more likely coming from the APMD local-ID feature
coordinates rather than from estimator tuning.
"""
    OUT_REPORT.write_text(text, encoding="utf-8")


def main() -> None:
    train, heldout = dual6.prepare_data()
    metrics, predictions = fit_predict_heldout(train, heldout)
    pair_df, pair_summary = dual6.pair_consistency(predictions)

    OUT_METRICS.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(OUT_METRICS, index=False)
    predictions.to_csv(OUT_PREDICTIONS, index=False)
    pair_df.to_csv(OUT_PAIR, index=False)
    pair_summary.to_csv(OUT_PAIR_SUMMARY, index=False)

    plot_comparison(metrics, pair_summary)
    plot_best_fit(metrics, predictions)
    write_report(metrics, pair_summary, len(train), len(heldout))

    print("Stage 6.5 linear estimator sweep complete")
    print(f"  metrics      : {OUT_METRICS}")
    print(f"  predictions  : {OUT_PREDICTIONS}")
    print(f"  comparison   : {OUT_COMPARISON_FIGURE}")
    print(f"  best fit     : {OUT_BEST_FIT_FIGURE}")
    print(f"  report       : {OUT_REPORT}")
    print(metrics[["model", "estimator", "F_MAE_N", "d_MAE_mm", "balanced_score_ideal"]].to_string(index=False))


if __name__ == "__main__":
    main()
