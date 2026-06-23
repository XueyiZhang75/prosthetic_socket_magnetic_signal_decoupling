"""Cross-session validation for Stage 5.1B dense-loop local APMD data.

This analysis intentionally uses only the dense minor-loop state summaries.
It trains on one dense-loop session and tests on the other, then reverses the
direction. The goal is to check whether the local path-memory mapping transfers
across repeated dense-loop acquisitions.
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
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports"
STATE_DATA = REPORTS_DIR / "apmd_stage5_model_dataset_states.csv"

OUT_METRICS = REPORTS_DIR / "apmd_stage5_dense_loop_cross_session_metrics.csv"
OUT_PREDICTIONS = REPORTS_DIR / "apmd_stage5_dense_loop_cross_session_predictions.csv"
OUT_FIGURE = REPORTS_DIR / "apmd_stage5_dense_loop_cross_session_validation.png"
OUT_REPORT = REPORTS_DIR / "APMD_STAGE5_DENSE_LOOP_CROSS_SESSION_VALIDATION.md"

TARGETS = ["F_N", "d_mm"]

BLACK = "#222222"
RED = "#c23b3b"
BLUE = "#1f77b4"
GRAY = "#888888"
LIGHT_GRAY = "#e8e8e8"


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(math.sqrt(mean_squared_error(y_true, y_pred)))


def prepare_dense_states(states: pd.DataFrame) -> pd.DataFrame:
    dense = states[states["path_family"] == "local_minor_loop_dense"].copy()
    dense = dense.dropna(subset=["F_N", "d_mm", "Bx_uT", "By_uT", "Bz_uT", "Bmag_uT"]).copy()

    numeric_cols = [
        "F_N",
        "d_mm",
        "Bx_uT",
        "By_uT",
        "Bz_uT",
        "Bmag_uT",
        "delta_Bx_from_B0_uT",
        "delta_By_from_B0_uT",
        "delta_Bz_from_B0_uT",
        "cycle_index",
        "state_index",
        "preload_extra_mm",
        "preload_hold_s",
    ]
    for col in numeric_cols:
        if col in dense.columns:
            dense[col] = pd.to_numeric(dense[col], errors="coerce")

    for col in ["cycle_index", "state_index", "preload_extra_mm", "preload_hold_s"]:
        if col not in dense.columns:
            dense[col] = 0.0
        dense[col] = dense[col].fillna(0.0)

    db_cols = ["delta_Bx_from_B0_uT", "delta_By_from_B0_uT", "delta_Bz_from_B0_uT"]
    for col in db_cols:
        if col not in dense.columns:
            dense[col] = 0.0
        dense[col] = dense[col].fillna(0.0)
    dense["delta_Bvec_from_B0_uT"] = np.sqrt(
        dense["delta_Bx_from_B0_uT"] ** 2
        + dense["delta_By_from_B0_uT"] ** 2
        + dense["delta_Bz_from_B0_uT"] ** 2
    )

    dense["is_preload"] = (dense["path_label"] == "preload_deep").astype(int)
    dense["is_return"] = (dense["path_label"] == "return_unloading").astype(int)
    dense["session_id"] = dense["session_id"].astype(str)
    return dense.reset_index(drop=True)


def directional_session_splits(df: pd.DataFrame):
    sessions = sorted(df["session_id"].dropna().astype(str).unique().tolist())
    if len(sessions) < 2:
        raise ValueError(f"need at least two dense-loop sessions, got {len(sessions)}")
    for test_session in sessions:
        train_sessions = [s for s in sessions if s != test_session]
        train_idx = df.index[df["session_id"].isin(train_sessions)].to_numpy()
        test_idx = df.index[df["session_id"] == test_session].to_numpy()
        train_label = "train " + "+".join(train_sessions)
        yield train_idx, test_idx, train_label, test_session


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
                    min_samples_leaf=2,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def fit_cross_session_models(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
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
    path_memory_numeric = [
        "is_preload",
        "is_return",
        "cycle_index",
        "state_index",
        "preload_extra_mm",
        "preload_hold_s",
    ]
    path_cats = ["path_label"]

    specs = [
        ("dense_magnetic_plain_ridge", _ridge_model(magnetic, []), magnetic),
        (
            "dense_path_memory_ridge",
            _ridge_model(magnetic + path_memory_numeric, path_cats),
            magnetic + path_memory_numeric + path_cats,
        ),
        ("dense_magnetic_plain_random_forest", _rf_model(magnetic, []), magnetic),
        (
            "dense_path_memory_random_forest",
            _rf_model(magnetic + path_memory_numeric, path_cats),
            magnetic + path_memory_numeric + path_cats,
        ),
    ]

    pred_rows: list[pd.DataFrame] = []
    y = df[TARGETS].to_numpy(float)
    for train_idx, test_idx, train_label, test_session in directional_session_splits(df):
        for model_name, model, features in specs:
            fitted = model.fit(df.iloc[train_idx][features], y[train_idx])
            pred = fitted.predict(df.iloc[test_idx][features])
            out = df.iloc[test_idx][
                [
                    "experiment",
                    "path_family",
                    "session_id",
                    "trial",
                    "pair_id",
                    "cycle_index",
                    "state_index",
                    "state_label",
                    "path_label",
                    "F_N",
                    "d_mm",
                ]
            ].copy()
            out["model"] = model_name
            out["train_label"] = train_label
            out["test_session"] = test_session
            out["F_pred_N"] = pred[:, 0]
            out["d_pred_mm"] = pred[:, 1]
            out["F_error_N"] = out["F_pred_N"] - out["F_N"]
            out["d_error_mm"] = out["d_pred_mm"] - out["d_mm"]
            pred_rows.append(out)

    predictions = pd.concat(pred_rows, ignore_index=True)
    metric_rows = []
    for (model, test_session), chunk in predictions.groupby(["model", "test_session"]):
        metric_rows.append(_metric_row(model, test_session, chunk))
    for model, chunk in predictions.groupby("model"):
        metric_rows.append(_metric_row(model, "overall", chunk))
    metrics = pd.DataFrame(metric_rows)
    return metrics.sort_values(["test_session", "F_MAE_N", "d_MAE_mm"]).reset_index(drop=True), predictions


def _metric_row(model: str, test_session: str, chunk: pd.DataFrame) -> dict:
    f_true = chunk["F_N"].to_numpy(float)
    f_pred = chunk["F_pred_N"].to_numpy(float)
    d_true = chunk["d_mm"].to_numpy(float)
    d_pred = chunk["d_pred_mm"].to_numpy(float)
    return {
        "model": model,
        "test_session": test_session,
        "n_states": len(chunk),
        "F_MAE_N": mean_absolute_error(f_true, f_pred),
        "F_RMSE_N": _rmse(f_true, f_pred),
        "F_R2": r2_score(f_true, f_pred),
        "d_MAE_mm": mean_absolute_error(d_true, d_pred),
        "d_RMSE_mm": _rmse(d_true, d_pred),
        "d_R2": r2_score(d_true, d_pred),
    }


def plot_results(metrics: pd.DataFrame, predictions: pd.DataFrame) -> None:
    overall = metrics[metrics["test_session"] == "overall"].copy()
    order = [
        "dense_magnetic_plain_ridge",
        "dense_path_memory_ridge",
        "dense_magnetic_plain_random_forest",
        "dense_path_memory_random_forest",
    ]
    labels = ["plain\nridge", "path-memory\nridge", "plain\nRF", "path-memory\nRF"]
    colors = [BLACK, RED, BLACK, RED]

    best_balanced = overall.assign(
        balanced=overall["F_MAE_N"] / overall["F_MAE_N"].min()
        + overall["d_MAE_mm"] / overall["d_MAE_mm"].min()
    ).sort_values("balanced").iloc[0]["model"]
    pred = predictions[predictions["model"] == best_balanced].copy()

    fig = plt.figure(figsize=(13.5, 8.5), dpi=180)
    gs = fig.add_gridspec(2, 2, hspace=0.42, wspace=0.30)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1])

    x = np.arange(len(order))
    metric_index = overall.set_index("model")
    ax1.bar(x, metric_index.loc[order, "F_MAE_N"], color=colors, width=0.68)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=9)
    ax1.set_ylabel("F MAE (N)")
    ax1.set_title("a  Cross-session force error")
    ax1.grid(axis="y", color=LIGHT_GRAY, linewidth=0.8)
    ax1.set_axisbelow(True)

    ax2.bar(x, metric_index.loc[order, "d_MAE_mm"], color=colors, width=0.68)
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=9)
    ax2.set_ylabel("d MAE (mm)")
    ax2.set_title("b  Cross-session displacement error")
    ax2.grid(axis="y", color=LIGHT_GRAY, linewidth=0.8)
    ax2.set_axisbelow(True)

    ax3.scatter(pred["F_N"], pred["F_pred_N"], s=24, c=pred["test_session"].map(_session_color), alpha=0.75)
    f_min = min(pred["F_N"].min(), pred["F_pred_N"].min())
    f_max = max(pred["F_N"].max(), pred["F_pred_N"].max())
    ax3.plot([f_min, f_max], [f_min, f_max], color=GRAY, linewidth=1.2)
    ax3.set_xlabel("measured F (N)")
    ax3.set_ylabel("predicted F (N)")
    ax3.set_title(f"c  Best balanced model: {best_balanced}")
    ax3.grid(color=LIGHT_GRAY, linewidth=0.8)

    ax4.scatter(pred["d_mm"], pred["d_pred_mm"], s=24, c=pred["test_session"].map(_session_color), alpha=0.75)
    d_min = min(pred["d_mm"].min(), pred["d_pred_mm"].min())
    d_max = max(pred["d_mm"].max(), pred["d_pred_mm"].max())
    ax4.plot([d_min, d_max], [d_min, d_max], color=GRAY, linewidth=1.2)
    ax4.set_xlabel("measured d (mm)")
    ax4.set_ylabel("predicted d (mm)")
    ax4.set_title("d  Predicted displacement")
    ax4.grid(color=LIGHT_GRAY, linewidth=0.8)

    fig.suptitle("Stage 5.3: dense-loop cross-session validation", x=0.06, ha="left", fontsize=16, fontweight="bold")
    fig.text(
        0.06,
        0.94,
        "Train on one 5.1B dense-loop session and test on the other; colors denote held-out sessions",
        fontsize=10,
        color="#555555",
    )
    fig.savefig(OUT_FIGURE, bbox_inches="tight")
    plt.close(fig)


def _session_color(session_id: str) -> str:
    return BLUE if str(session_id).endswith("112044") else RED


def write_report(metrics: pd.DataFrame, dense: pd.DataFrame) -> None:
    overall = metrics[metrics["test_session"] == "overall"].copy()
    plain = overall[overall["model"] == "dense_magnetic_plain_ridge"].iloc[0]
    memory = overall[overall["model"] == "dense_path_memory_ridge"].iloc[0]
    rf_memory = overall[overall["model"] == "dense_path_memory_random_forest"].iloc[0]
    best_f = overall.sort_values("F_MAE_N").iloc[0]
    best_d = overall.sort_values("d_MAE_mm").iloc[0]

    f_gain = (plain["F_MAE_N"] - memory["F_MAE_N"]) / plain["F_MAE_N"] * 100.0
    d_gain = (plain["d_MAE_mm"] - memory["d_MAE_mm"]) / plain["d_MAE_mm"] * 100.0

    lines = [
        "# APMD Stage 5.3 Dense-Loop Cross-Session Validation",
        "",
        "This report is generated by `apmd_stage5_dense_loop_cross_session_validation.py`.",
        "",
        "## Data",
        "",
        f"- Input states: `{STATE_DATA.relative_to(ROOT)}`",
        f"- Dense-loop state rows used: {len(dense)}",
        f"- Dense-loop sessions: {', '.join(sorted(dense['session_id'].unique()))}",
        "- Validation: train on one dense-loop session and test on the other, then reverse the direction.",
        "",
        "## Metrics",
        "",
        metrics[
            [
                "model",
                "test_session",
                "n_states",
                "F_MAE_N",
                "F_R2",
                "d_MAE_mm",
                "d_R2",
            ]
        ].to_markdown(index=False, floatfmt=".4f"),
        "",
        "## Main Result",
        "",
        f"- Best force model: `{best_f['model']}` with F MAE = {best_f['F_MAE_N']:.3f} N.",
        f"- Best displacement model: `{best_d['model']}` with d MAE = {best_d['d_MAE_mm']:.3f} mm.",
        f"- Ridge path-memory vs plain magnetic ridge: force MAE reduction = {f_gain:+.1f}%; displacement MAE reduction = {d_gain:+.1f}%.",
        f"- Nonlinear path-memory random forest: F MAE = {rf_memory['F_MAE_N']:.3f} N; d MAE = {rf_memory['d_MAE_mm']:.3f} mm.",
        "",
        "## Interpretation",
        "",
        "This is the direct repeatability test for the local dense-loop model-data sessions. A positive result means the model is not only fitting one acquisition; it can transfer between two independently acquired dense-loop sessions under the same local active-path protocol.",
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
    states = pd.read_csv(STATE_DATA)
    dense = prepare_dense_states(states)
    metrics, predictions = fit_cross_session_models(dense)
    metrics.to_csv(OUT_METRICS, index=False)
    predictions.to_csv(OUT_PREDICTIONS, index=False)
    plot_results(metrics, predictions)
    write_report(metrics, dense)
    print(f"wrote {OUT_METRICS.relative_to(ROOT)}")
    print(f"wrote {OUT_PREDICTIONS.relative_to(ROOT)}")
    print(f"wrote {OUT_FIGURE.relative_to(ROOT)}")
    print(f"wrote {OUT_REPORT.relative_to(ROOT)}")
    print(metrics[metrics["test_session"] == "overall"].to_string(index=False))


if __name__ == "__main__":
    main()
