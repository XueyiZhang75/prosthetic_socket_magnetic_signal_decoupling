"""Stage 5.2 baseline model fitting for local APMD decoupling.

The goal is proof-of-mechanism, not socket-range deployment:
compare plain magnetic regression against path-aware magnetic models on
accepted formal Stage 3 path-pair summaries plus the Stage 5.1B dense
minor-loop state dataset.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports"
STATE_DATA = REPORTS_DIR / "apmd_stage5_model_dataset_states.csv"
PAIR_DATA = REPORTS_DIR / "apmd_stage5_model_dataset_pairs.csv"

OUT_METRICS = REPORTS_DIR / "apmd_stage5_local_model_metrics.csv"
OUT_PREDICTIONS = REPORTS_DIR / "apmd_stage5_local_model_predictions.csv"
OUT_FIGURE = REPORTS_DIR / "apmd_stage5_local_model_baseline_comparison.png"
OUT_REPORT = REPORTS_DIR / "APMD_STAGE5_LOCAL_MODEL_BASELINE.md"

TARGETS = ["F_N", "d_mm"]

BLACK = "#222222"
RED = "#c23b3b"
BLUE = "#1f77b4"
GRAY = "#888888"
LIGHT_GRAY = "#e8e8e8"


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(math.sqrt(mean_squared_error(y_true, y_pred)))


def load_states() -> pd.DataFrame:
    states = pd.read_csv(STATE_DATA)
    states = states.dropna(subset=["F_N", "d_mm", "Bx_uT", "By_uT", "Bz_uT", "Bmag_uT"]).copy()

    group_cols = ["session_id", "trial", "pair_id", "experiment", "path_family"]
    grouped = states.groupby(group_cols, dropna=False)
    states["pair_Bmag_max_uT"] = grouped["Bmag_uT"].transform("max")
    states["pair_Bmag_min_uT"] = grouped["Bmag_uT"].transform("min")
    states["pair_Bmag_range_uT"] = states["pair_Bmag_max_uT"] - states["pair_Bmag_min_uT"]
    states["pair_state_index"] = states.groupby(group_cols, dropna=False).cumcount()

    db_cols = ["delta_Bx_from_B0_uT", "delta_By_from_B0_uT", "delta_Bz_from_B0_uT"]
    for col in db_cols:
        states[col] = pd.to_numeric(states[col], errors="coerce")
    states["delta_Bvec_from_B0_uT"] = np.sqrt(
        states["delta_Bx_from_B0_uT"].fillna(0.0) ** 2
        + states["delta_By_from_B0_uT"].fillna(0.0) ** 2
        + states["delta_Bz_from_B0_uT"].fillna(0.0) ** 2
    )
    states["is_preload"] = (states["path_label"] == "preload_deep").astype(int)
    states["is_return"] = (states["path_label"] == "return_unloading").astype(int)
    states["is_same_d_family"] = (states["path_family"] == "same_d_different_F").astype(int)
    for col in ["preload_hold_s", "recovery_s"]:
        states[col] = pd.to_numeric(states[col], errors="coerce").fillna(0.0)
    return states


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


def _ridge_model(numeric_features: list[str], categorical_features: list[str]) -> Pipeline:
    return Pipeline(
        steps=[
            ("preprocess", _preprocess(numeric_features, categorical_features)),
            ("model", Ridge(alpha=1.0)),
        ]
    )


def _rf_model(numeric_features: list[str], categorical_features: list[str]) -> Pipeline:
    return Pipeline(
        steps=[
            ("preprocess", _preprocess(numeric_features, categorical_features)),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=400,
                    min_samples_leaf=3,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def _group_predict(
    name: str,
    model: Pipeline,
    df: pd.DataFrame,
    feature_cols: list[str],
    target_cols: list[str],
) -> pd.DataFrame:
    groups = df["session_id"].astype(str)
    unique_groups = groups.nunique()
    n_splits = min(5, unique_groups)
    if n_splits < 2:
        raise ValueError(f"not enough groups for cross-validation: {unique_groups}")

    y = df[target_cols].to_numpy(dtype=float)
    preds = np.full_like(y, np.nan, dtype=float)
    fold_id = np.full(len(df), -1, dtype=int)
    splitter = GroupKFold(n_splits=n_splits)

    for fold, (train_idx, test_idx) in enumerate(splitter.split(df[feature_cols], y, groups=groups), start=1):
        fitted = model.fit(df.iloc[train_idx][feature_cols], y[train_idx])
        preds[test_idx] = fitted.predict(df.iloc[test_idx][feature_cols])
        fold_id[test_idx] = fold

    out = df[
        [
            "experiment",
            "path_family",
            "session_id",
            "trial",
            "pair_id",
            "state_label",
            "path_label",
            "F_N",
            "d_mm",
        ]
    ].copy()
    out["model"] = name
    out["fold"] = fold_id
    out["F_pred_N"] = preds[:, 0]
    out["d_pred_mm"] = preds[:, 1]
    out["F_error_N"] = out["F_pred_N"] - out["F_N"]
    out["d_error_mm"] = out["d_pred_mm"] - out["d_mm"]
    return out


def _mechanical_cross_baseline(df: pd.DataFrame) -> pd.DataFrame:
    """Traditional F-d coupling reference; not a magnetic decoupling model."""
    out = df[
        [
            "experiment",
            "path_family",
            "session_id",
            "trial",
            "pair_id",
            "state_label",
            "path_label",
            "F_N",
            "d_mm",
        ]
    ].copy()
    groups = df["session_id"].astype(str)
    splitter = GroupKFold(n_splits=min(5, groups.nunique()))

    f_pred = np.full(len(df), np.nan)
    d_pred = np.full(len(df), np.nan)
    fold_id = np.full(len(df), -1, dtype=int)

    f_model = Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=1.0))])
    d_model = Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=1.0))])

    for fold, (train_idx, test_idx) in enumerate(splitter.split(df[["d_mm"]], df["F_N"], groups), start=1):
        f_model.fit(df.iloc[train_idx][["d_mm"]], df.iloc[train_idx]["F_N"])
        d_model.fit(df.iloc[train_idx][["F_N"]], df.iloc[train_idx]["d_mm"])
        f_pred[test_idx] = f_model.predict(df.iloc[test_idx][["d_mm"]])
        d_pred[test_idx] = d_model.predict(df.iloc[test_idx][["F_N"]])
        fold_id[test_idx] = fold

    out["model"] = "mechanical_cross_label_ridge"
    out["fold"] = fold_id
    out["F_pred_N"] = f_pred
    out["d_pred_mm"] = d_pred
    out["F_error_N"] = out["F_pred_N"] - out["F_N"]
    out["d_error_mm"] = out["d_pred_mm"] - out["d_mm"]
    return out


def _metric_rows(predictions: pd.DataFrame) -> list[dict]:
    rows = []
    for model, chunk in predictions.groupby("model"):
        f_true = chunk["F_N"].to_numpy(float)
        f_pred = chunk["F_pred_N"].to_numpy(float)
        d_true = chunk["d_mm"].to_numpy(float)
        d_pred = chunk["d_pred_mm"].to_numpy(float)
        rows.append(
            {
                "model": model,
                "n_states": len(chunk),
                "F_MAE_N": mean_absolute_error(f_true, f_pred),
                "F_RMSE_N": _rmse(f_true, f_pred),
                "F_R2": r2_score(f_true, f_pred),
                "d_MAE_mm": mean_absolute_error(d_true, d_pred),
                "d_RMSE_mm": _rmse(d_true, d_pred),
                "d_R2": r2_score(d_true, d_pred),
            }
        )
    return rows


def _add_relative_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    out = metrics.copy()
    plain = out[out["model"] == "magnetic_plain_ridge"].iloc[0]
    out["F_MAE_vs_plain_pct"] = (plain["F_MAE_N"] - out["F_MAE_N"]) / plain["F_MAE_N"] * 100.0
    out["d_MAE_vs_plain_pct"] = (plain["d_MAE_mm"] - out["d_MAE_mm"]) / plain["d_MAE_mm"] * 100.0
    out["balanced_relative_error"] = (out["F_MAE_N"] / plain["F_MAE_N"]) + (out["d_MAE_mm"] / plain["d_MAE_mm"])
    return out


def fit_models(states: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
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
    path_cats = ["path_family", "path_label"]

    specs = [
        (
            "magnetic_plain_ridge",
            _ridge_model(magnetic, []),
            magnetic,
        ),
        (
            "magnetic_path_label_ridge",
            _ridge_model(magnetic + path_numeric, path_cats),
            magnetic + path_numeric + path_cats,
        ),
        (
            "magnetic_path_memory_ridge",
            _ridge_model(magnetic + path_numeric + memory_numeric, path_cats),
            magnetic + path_numeric + memory_numeric + path_cats,
        ),
        (
            "magnetic_plain_random_forest",
            _rf_model(magnetic, []),
            magnetic,
        ),
        (
            "magnetic_path_memory_random_forest",
            _rf_model(magnetic + path_numeric + memory_numeric, path_cats),
            magnetic + path_numeric + memory_numeric + path_cats,
        ),
    ]

    preds = [_mechanical_cross_baseline(states)]
    for name, model, features in specs:
        preds.append(_group_predict(name, model, states, features, TARGETS))

    predictions = pd.concat(preds, ignore_index=True)
    metrics = _add_relative_metrics(pd.DataFrame(_metric_rows(predictions)))
    metrics = metrics.sort_values(["F_MAE_N", "d_MAE_mm"]).reset_index(drop=True)
    return metrics, predictions


def plot_results(metrics: pd.DataFrame, predictions: pd.DataFrame) -> None:
    plot_metrics = metrics.copy()
    order = plot_metrics.sort_values("F_MAE_N")["model"].tolist()
    labels = [m.replace("magnetic_", "").replace("_", "\n") for m in order]
    colors = []
    for model in order:
        if "mechanical" in model:
            colors.append(GRAY)
        elif "path_memory" in model:
            colors.append(RED)
        elif "path_label" in model:
            colors.append(BLUE)
        else:
            colors.append(BLACK)

    best_f_model = metrics.sort_values("F_MAE_N").iloc[0]["model"]
    best_d_model = metrics.sort_values("d_MAE_mm").iloc[0]["model"]
    best_f = predictions[predictions["model"] == best_f_model]
    best_d = predictions[predictions["model"] == best_d_model]

    fig = plt.figure(figsize=(13, 9), dpi=180)
    gs = fig.add_gridspec(2, 2, hspace=0.38, wspace=0.30)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1])

    x = np.arange(len(order))
    ax1.bar(x, plot_metrics.set_index("model").loc[order, "F_MAE_N"], color=colors, width=0.72)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=0, fontsize=8)
    ax1.set_ylabel("F MAE (N)")
    ax1.set_title("a  Force prediction error")
    ax1.grid(axis="y", color=LIGHT_GRAY, linewidth=0.8)
    ax1.set_axisbelow(True)

    ax2.bar(x, plot_metrics.set_index("model").loc[order, "d_MAE_mm"], color=colors, width=0.72)
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=0, fontsize=8)
    ax2.set_ylabel("d MAE (mm)")
    ax2.set_title("b  Displacement prediction error")
    ax2.grid(axis="y", color=LIGHT_GRAY, linewidth=0.8)
    ax2.set_axisbelow(True)

    ax3.scatter(best_f["F_N"], best_f["F_pred_N"], s=24, color=BLACK, alpha=0.75)
    f_min = min(best_f["F_N"].min(), best_f["F_pred_N"].min())
    f_max = max(best_f["F_N"].max(), best_f["F_pred_N"].max())
    ax3.plot([f_min, f_max], [f_min, f_max], color=RED, linewidth=1.2)
    ax3.set_xlabel("measured F (N)")
    ax3.set_ylabel("predicted F (N)")
    ax3.set_title(f"c  Best F model: {best_f_model}")
    ax3.grid(color=LIGHT_GRAY, linewidth=0.8)

    ax4.scatter(best_d["d_mm"], best_d["d_pred_mm"], s=24, color=BLUE, alpha=0.75)
    d_min = min(best_d["d_mm"].min(), best_d["d_pred_mm"].min())
    d_max = max(best_d["d_mm"].max(), best_d["d_pred_mm"].max())
    ax4.plot([d_min, d_max], [d_min, d_max], color=RED, linewidth=1.2)
    ax4.set_xlabel("measured d (mm)")
    ax4.set_ylabel("predicted d (mm)")
    ax4.set_title(f"d  Best d model: {best_d_model}")
    ax4.grid(color=LIGHT_GRAY, linewidth=0.8)

    fig.suptitle("Stage 5.2: local APMD baseline model comparison", x=0.06, ha="left", fontsize=16, fontweight="bold")
    fig.text(
        0.06,
        0.94,
        "Grouped cross-validation by session; formal Stage 3 path-pair states plus Stage 5.1B dense-loop states",
        fontsize=10,
        color="#555555",
    )
    fig.savefig(OUT_FIGURE, bbox_inches="tight")
    plt.close(fig)


def write_report(metrics: pd.DataFrame, predictions: pd.DataFrame) -> None:
    best_f = metrics.sort_values("F_MAE_N").iloc[0]
    best_d = metrics.sort_values("d_MAE_mm").iloc[0]
    balanced = metrics.sort_values("balanced_relative_error").iloc[0]
    plain = metrics[metrics["model"] == "magnetic_plain_ridge"].iloc[0]
    label = metrics[metrics["model"] == "magnetic_path_label_ridge"].iloc[0]
    memory = metrics[metrics["model"] == "magnetic_path_memory_ridge"].iloc[0]
    rf_memory = metrics[metrics["model"] == "magnetic_path_memory_random_forest"].iloc[0]

    label_f_gain = label["F_MAE_vs_plain_pct"]
    label_d_gain = label["d_MAE_vs_plain_pct"]
    memory_f_gain = memory["F_MAE_vs_plain_pct"]
    memory_d_gain = memory["d_MAE_vs_plain_pct"]

    lines = [
        "# APMD Stage 5.2 Local Model Baseline",
        "",
        "This report is generated by `apmd_stage5_fit_local_models.py`.",
        "",
        "## Data",
        "",
        f"- Input states: `{STATE_DATA.relative_to(ROOT)}`",
        f"- State rows used: {predictions[predictions['model'] == best_f['model']].shape[0]}",
        "- Validation: grouped cross-validation by `session_id`, so rows from the same session are not split across train and test.",
        "",
        "## Models",
        "",
        "- `mechanical_cross_label_ridge`: traditional F-d coupling reference. It uses one true label to predict the other, so it is not a magnetic decoupling model.",
        "- `magnetic_plain_ridge`: magnetic features only.",
        "- `magnetic_path_label_ridge`: magnetic features plus path-family/path-state labels.",
        "- `magnetic_path_memory_ridge`: magnetic features plus path labels and magnetic-history/protocol timing features.",
        "- `magnetic_path_memory_random_forest`: nonlinear version of the path-memory model.",
        "",
        "## Metrics",
        "",
        metrics[
            [
                "model",
                "n_states",
                "F_MAE_N",
                "F_R2",
                "d_MAE_mm",
                "d_R2",
                "F_MAE_vs_plain_pct",
                "d_MAE_vs_plain_pct",
                "balanced_relative_error",
            ]
        ].to_markdown(index=False, floatfmt=".4f"),
        "",
        "## Main Result",
        "",
        f"- Best force model: `{best_f['model']}` with F MAE = {best_f['F_MAE_N']:.3f} N.",
        f"- Best displacement model: `{best_d['model']}` with d MAE = {best_d['d_MAE_mm']:.3f} mm.",
        f"- Best balanced model by relative F+d error: `{balanced['model']}`.",
        f"- Path-label ridge vs plain magnetic ridge: force MAE reduction = {label_f_gain:+.1f}%; displacement MAE reduction = {label_d_gain:+.1f}%.",
        f"- Path-memory ridge vs plain magnetic ridge: force MAE reduction = {memory_f_gain:+.1f}%; displacement MAE reduction = {memory_d_gain:+.1f}%.",
        f"- Nonlinear path-memory random forest: force MAE = {rf_memory['F_MAE_N']:.3f} N; displacement MAE = {rf_memory['d_MAE_mm']:.3f} mm.",
        "",
        "## Interpretation",
        "",
        "This is the first local proof-of-mechanism modeling check. The key question is not whether the model already covers socket-scale loads, but whether path-aware magnetic features improve simultaneous prediction of force and displacement compared with plain magnetic regression.",
        "",
        "The newly added 5.1B dense-loop sessions expand the state coverage inside the selected local work zone. Because validation is grouped by `session_id`, each dense-loop session is held out as a whole in one fold. Therefore, these metrics should be read as a conservative first check, not as the final dense-loop model capacity. More dense-loop sessions or cycle-level held-out validation will be needed for a stronger model-specific conclusion.",
        "",
        "## Outputs",
        "",
        f"- Metrics: `{OUT_METRICS.relative_to(ROOT)}`",
        f"- Predictions: `{OUT_PREDICTIONS.relative_to(ROOT)}`",
        f"- Figure: `{OUT_FIGURE.relative_to(ROOT)}`",
        "",
    ]
    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    states = load_states()
    metrics, predictions = fit_models(states)
    metrics.to_csv(OUT_METRICS, index=False)
    predictions.to_csv(OUT_PREDICTIONS, index=False)
    plot_results(metrics, predictions)
    write_report(metrics, predictions)
    print(f"wrote {OUT_METRICS.relative_to(ROOT)}")
    print(f"wrote {OUT_PREDICTIONS.relative_to(ROOT)}")
    print(f"wrote {OUT_FIGURE.relative_to(ROOT)}")
    print(f"wrote {OUT_REPORT.relative_to(ROOT)}")
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
