"""Stage 6.3 supplementary MLP capacity check.

This script keeps the Stage 6.3 train/held-out split and compares the same four
feature families with a small tabular MLP. It is a model-capacity check, not the
main physics/feature ablation figure.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import apmd_stage6_compare_local_identifiability_models as stage6
from apmd_stage6_predict_local_heldout import TARGETS, load_heldout_states, prepare_training_states

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports"

OUT_METRICS = REPORTS_DIR / "apmd_stage6_mlp_model_metrics.csv"
OUT_PREDICTIONS = REPORTS_DIR / "apmd_stage6_mlp_predictions.csv"
OUT_FIGURE = REPORTS_DIR / "apmd_stage6_mlp_error_comparison.png"
OUT_FIGURE_PDF = REPORTS_DIR / "apmd_stage6_mlp_error_comparison.pdf"
OUT_REPORT = REPORTS_DIR / "APMD_STAGE6_MLP_MODEL_CHECK.md"

BLACK = "#222222"
BLUE = "#2c7fb8"
GRAY = "#7f7f7f"
RED = "#c23b3b"
LIGHT_GRAY = "#e7e7e7"
TEXT_GRAY = "#4d4d4d"

CATEGORICAL_FEATURES = {"path_family", "path_label", "local_zone_id"}


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
            "axes.titlesize": 11,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "legend.fontsize": 8.5,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def _preprocess(numeric_features: list[str], categorical_features: list[str]) -> ColumnTransformer:
    numeric_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("num", numeric_pipe, numeric_features),
            ("cat", categorical_pipe, categorical_features),
        ],
        remainder="drop",
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
            ("preprocess", _preprocess(numeric_features, categorical_features)),
            ("model", TransformedTargetRegressor(regressor=mlp, transformer=StandardScaler())),
        ]
    )


def mlp_model_specs() -> list[tuple[str, str, Pipeline, list[str]]]:
    ridge_specs = {name: (family, features) for name, family, _model, features in stage6.model_specs()}
    specs: list[tuple[str, str, Pipeline, list[str]]] = []
    for ridge_name in stage6.error_bar_model_order():
        family, features = ridge_specs[ridge_name]
        categorical = [feature for feature in features if feature in CATEGORICAL_FEATURES]
        numeric = [feature for feature in features if feature not in CATEGORICAL_FEATURES]
        mlp_name = ridge_name.replace("_ridge", "_mlp")
        specs.append((mlp_name, family, _mlp_model(numeric, categorical), features))
    return specs


def _ensure_features(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in features:
        if col not in out.columns:
            out[col] = ""
    return out


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
    y_train = train[TARGETS].to_numpy(float)
    pred_rows: list[pd.DataFrame] = []
    for name, family, model, features in mlp_model_specs():
        train_ready = _ensure_features(train, features)
        heldout_ready = _ensure_features(heldout, features)
        fitted = model.fit(train_ready[features], y_train)
        pred = fitted.predict(heldout_ready[features])

        cols = [
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
        ]
        out = _ensure_features(heldout_ready, cols)[cols].copy()
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


def _bar_labels(order: list[str]) -> list[str]:
    labels = {
        "plain_magnetic_mlp": "plain\nMLP",
        "lim_style_branch_mlp": "path-label\nMLP",
        "apmd_path_memory_mlp": "path-memory\nMLP",
        "apmd_local_identifiability_mlp": "local-ID\nMLP",
    }
    return [labels[model] for model in order]


def _add_value_labels(ax: plt.Axes, x: np.ndarray, values: pd.Series, fmt: str) -> None:
    upper = float(values.max())
    offset = upper * 0.030 if upper > 0 else 0.02
    for xpos, value in zip(x, values):
        ax.text(xpos, float(value) + offset, fmt.format(float(value)), ha="center", va="bottom", fontsize=8.2, color="#222222")


def _add_goal_label(ax: plt.Axes, y: float, label: str, color: str) -> None:
    ax.text(
        0.985,
        y,
        label,
        transform=ax.get_yaxis_transform(),
        ha="right",
        va="bottom",
        fontsize=8,
        color=color,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.80, "pad": 1.5},
    )


def plot_results(metrics: pd.DataFrame) -> None:
    _set_figure_style()
    order = [name for name, *_ in mlp_model_specs()]
    metric_index = metrics.set_index("model")
    labels = _bar_labels(order)
    colors = [BLACK, BLUE, GRAY, RED]
    x = np.arange(len(order))
    f_values = metric_index.loc[order, "F_MAE_N"]
    d_values = metric_index.loc[order, "d_MAE_mm"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.4, 3.9), dpi=300)
    ax1.bar(x, f_values, color=colors, width=0.62, edgecolor="none")
    ax1.axhline(0.75, color=GRAY, linestyle=(0, (1.0, 1.6)), linewidth=1.0)
    ax1.axhline(0.50, color=RED, linestyle=(0, (1.0, 1.6)), linewidth=1.0)
    _add_goal_label(ax1, 0.75, "current F goal", GRAY)
    _add_goal_label(ax1, 0.50, "ideal F goal", RED)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.set_ylabel("held-out F MAE (N)")
    ax1.set_title("a  Force error", loc="left", fontweight="bold")
    ax1.grid(axis="y", color=LIGHT_GRAY, linewidth=0.65)
    ax1.set_axisbelow(True)
    ax1.set_ylim(0, float(f_values.max()) * 1.22)
    _add_value_labels(ax1, x, f_values, "{:.3f}")

    ax2.bar(x, d_values, color=colors, width=0.62, edgecolor="none")
    ax2.axhline(0.05, color=RED, linestyle=(0, (1.0, 1.6)), linewidth=1.0)
    _add_goal_label(ax2, 0.05, "d goal", RED)
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.set_ylabel("held-out d MAE (mm)")
    ax2.set_title("b  Displacement error", loc="left", fontweight="bold")
    ax2.grid(axis="y", color=LIGHT_GRAY, linewidth=0.65)
    ax2.set_axisbelow(True)
    ax2.set_ylim(0, float(d_values.max()) * 1.22)
    _add_value_labels(ax2, x, d_values, "{:.3f}")

    for ax in [ax1, ax2]:
        ax.tick_params(length=3, width=0.8)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)

    train_n = int(metric_index.loc[order[0], "train_n_states"])
    heldout_n = int(metric_index.loc[order[0], "heldout_n_states"])
    fig.suptitle(
        "Stage 6.3 supplementary MLP capacity check",
        x=0.055,
        ha="left",
        fontsize=14.5,
        fontweight="bold",
    )
    fig.text(
        0.055,
        0.90,
        f"Train = {train_n} Stage 5 states; held-out = {heldout_n} Stage 6 states. Same four feature families, estimator fixed to MLP.",
        fontsize=9.2,
        color=TEXT_GRAY,
    )
    fig.subplots_adjust(left=0.075, right=0.985, top=0.76, bottom=0.24, wspace=0.30)
    fig.savefig(OUT_FIGURE, bbox_inches="tight")
    fig.savefig(OUT_FIGURE_PDF, bbox_inches="tight")
    plt.close(fig)


def write_report(metrics: pd.DataFrame) -> None:
    best_f = metrics.sort_values("F_MAE_N").iloc[0]
    best_d = metrics.sort_values("d_MAE_mm").iloc[0]
    ridge_metrics = pd.read_csv(stage6.OUT_METRICS).set_index("model")
    local_ridge = ridge_metrics.loc["apmd_local_identifiability_ridge"]
    local_mlp = metrics.set_index("model").loc["apmd_local_identifiability_mlp"]
    lines = [
        "# APMD Stage 6.3 MLP Model Check",
        "",
        "This report is generated by `apmd_stage6_neural_model_check.py`.",
        "",
        "## Purpose",
        "",
        "This is a supplementary neural-network capacity check. It uses the same Stage 6.3 train/held-out split and the same four feature families as the ridge-only comparison, but replaces the estimator with a small tabular MLP.",
        "",
        "## Metrics",
        "",
        metrics[
            [
                "model",
                "model_family",
                "train_n_states",
                "heldout_n_states",
                "F_MAE_N",
                "F_R2",
                "d_MAE_mm",
                "d_R2",
                "F_MAE_vs_plain_mlp_pct",
                "F_MAE_vs_lim_style_mlp_pct",
                "passes_current_F_goal",
                "passes_d_goal",
            ]
        ].to_markdown(index=False, floatfmt=".4f"),
        "",
        "## Main Result",
        "",
        f"- Best MLP force model: `{best_f['model']}` with F MAE `{best_f['F_MAE_N']:.3f} N`.",
        f"- Best MLP displacement model: `{best_d['model']}` with d MAE `{best_d['d_MAE_mm']:.3f} mm`.",
        f"- Compared with local-ID ridge (`F MAE {local_ridge['F_MAE_N']:.3f} N`, `d MAE {local_ridge['d_MAE_mm']:.3f} mm`), local-ID MLP has higher force error (`{local_mlp['F_MAE_N']:.3f} N`) but lower displacement error (`{local_mlp['d_MAE_mm']:.3f} mm`).",
        "- Read this as a capacity check, not as a replacement for the ridge-only physics/feature ablation.",
        "",
        "## Outputs",
        "",
        f"- Metrics: `{OUT_METRICS.relative_to(ROOT)}`",
        f"- Predictions: `{OUT_PREDICTIONS.relative_to(ROOT)}`",
        f"- Figure: `{OUT_FIGURE.relative_to(ROOT)}`",
        f"- Figure PDF: `{OUT_FIGURE_PDF.relative_to(ROOT)}`",
    ]
    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    train = prepare_training_states()
    heldout = load_heldout_states()
    jf, jd = stage6.load_sensitivity_tables()

    train = stage6.add_local_identifiability_features(train, jf, jd)
    heldout = stage6.add_local_identifiability_features(heldout, jf, jd)

    metrics, predictions = fit_predict_heldout(train, heldout)
    metrics.to_csv(OUT_METRICS, index=False)
    predictions.to_csv(OUT_PREDICTIONS, index=False)
    plot_results(metrics)
    write_report(metrics)

    print("Stage 6.3 MLP model check complete")
    print(f"  metrics    : {OUT_METRICS}")
    print(f"  predictions: {OUT_PREDICTIONS}")
    print(f"  figure     : {OUT_FIGURE}")
    print(f"  figure pdf : {OUT_FIGURE_PDF}")
    print(f"  report     : {OUT_REPORT}")
    print(metrics[["model", "F_MAE_N", "d_MAE_mm", "F_MAE_vs_lim_style_mlp_pct"]].to_string(index=False))


if __name__ == "__main__":
    main()
