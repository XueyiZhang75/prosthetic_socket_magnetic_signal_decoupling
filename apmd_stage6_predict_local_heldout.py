"""Stage 6.2 held-out local dense-loop model validation.

Train only on the Stage 5 model dataset, then test the Stage 6.1 dense-loop
session as a whole. The held-out session is never mixed into training.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports"
DATA_DIR = ROOT / "decouple_data"

TRAIN_STATE_DATA = REPORTS_DIR / "apmd_stage5_model_dataset_states.csv"
HELDOUT_SESSION_IDS = [
    "session_20260615_160438",
    "session_20260618_161152",
]
HELDOUT_SUMMARIES = [
    DATA_DIR / session_id / "local_heldout_dense_loop_6p1_state_summary.csv"
    for session_id in HELDOUT_SESSION_IDS
]

# Backward-compatible default for tests and one-off debugging.
HELDOUT_SESSION_ID = HELDOUT_SESSION_IDS[0]
HELDOUT_SUMMARY = HELDOUT_SUMMARIES[0]

OUT_METRICS = REPORTS_DIR / "apmd_stage6_heldout_model_metrics.csv"
OUT_PREDICTIONS = REPORTS_DIR / "apmd_stage6_heldout_model_predictions.csv"
OUT_FIGURE = REPORTS_DIR / "apmd_stage6_heldout_model_validation.png"
OUT_REPORT = REPORTS_DIR / "APMD_STAGE6_HELDOUT_MODEL_VALIDATION.md"

TARGETS = ["F_N", "d_mm"]

BLACK = "#222222"
RED = "#c23b3b"
BLUE = "#1f77b4"
GRAY = "#888888"
LIGHT_GRAY = "#e8e8e8"


def _float(value, default: float = math.nan) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _target_code_from_mm(mm: float) -> str:
    if math.isnan(mm):
        return ""
    return f"{int(round(mm * 100)):03d}"


def _dense_loop_path_label(branch: str, state_label: str) -> str:
    label = f"{branch} {state_label}".lower()
    if "preload" in label:
        return "preload_deep"
    if "unloading" in label:
        return "return_unloading"
    if "loading" in label:
        return "direct_loading"
    return str(state_label)


def _dense_loop_preload_hold_s(row: pd.Series) -> float:
    branch = str(row.get("branch", "")).lower()
    record_s = _float(row.get("record_s"), math.nan)
    if branch == "preload":
        return record_s
    if branch == "unloading":
        return 30.0
    return 0.0


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(math.sqrt(mean_squared_error(y_true, y_pred)))


def _session_id_set(session_ids: object) -> set[str]:
    if session_ids is None:
        return set(HELDOUT_SESSION_IDS)
    if isinstance(session_ids, (str, bytes)):
        return {str(session_ids)}
    return {str(session_id) for session_id in session_ids}


def select_training_states(states: pd.DataFrame, heldout_session_id: object = None) -> pd.DataFrame:
    """Return training states with the held-out session strictly excluded."""
    if "session_id" not in states.columns:
        raise ValueError("states must include session_id")
    heldout_ids = _session_id_set(heldout_session_id)
    return states[~states["session_id"].astype(str).isin(heldout_ids)].copy()


def prepare_heldout_states(summary: pd.DataFrame, summary_path: Path = HELDOUT_SUMMARY) -> pd.DataFrame:
    """Convert the Stage 6.1 state-summary CSV to the Stage 5 state schema."""
    rows: list[dict] = []
    session_id_default = summary_path.parent.name
    source_csv = str(summary_path.relative_to(ROOT))
    for _, row in summary.iterrows():
        cycle = _int(row.get("cycle"))
        state_index = _int(row.get("state_index"))
        branch = str(row.get("branch", ""))
        state_label = str(row.get("state_label", ""))
        d_target = _float(row.get("d_target_mm"))
        d_preload = _float(row.get("d_preload_mm"))
        preload_extra = d_preload - d_target if not math.isnan(d_preload) and not math.isnan(d_target) else math.nan

        bx = _float(row.get("Bx_median_uT"))
        by = _float(row.get("By_median_uT"))
        bz = _float(row.get("Bz_median_uT"))
        bmag = _float(row.get("Bmag_median_uT"))
        if math.isnan(bmag) and not any(math.isnan(v) for v in [bx, by, bz]):
            bmag = math.sqrt(bx * bx + by * by + bz * bz)

        rows.append(
            {
                "experiment": "6.1 local held-out dense-loop validation",
                # Same protocol family as Stage 5.1B; held-out status is carried by session_id/experiment.
                "path_family": "local_minor_loop_dense",
                "source_kind": "heldout_state_summary",
                "source_state_csv": source_csv,
                "session_id": str(row.get("session_id", session_id_default)),
                "trial": cycle,
                "pair_id": cycle,
                "cycle_index": cycle,
                "state_index": state_index,
                "branch": branch,
                "path_mode": str(row.get("path_mode", "")),
                "phase": str(row.get("phase", "")),
                "raw_file": source_csv,
                "state_label": state_label,
                "path_label": _dense_loop_path_label(branch, state_label),
                "target_label": _target_code_from_mm(d_target),
                "target_F_N": math.nan,
                "d_target_mm": d_target,
                "d_preload_mm": d_preload,
                "preload_extra_mm": preload_extra,
                "preload_hold_s": _dense_loop_preload_hold_s(row),
                "recovery_s": math.nan,
                "F_N": _float(row.get("F_median_N")),
                "d_mm": _float(row.get("d_median_mm")),
                "Bx_uT": bx,
                "By_uT": by,
                "Bz_uT": bz,
                "Bmag_uT": bmag,
                "delta_Bx_from_B0_uT": _float(row.get("delta_Bx_median_uT")),
                "delta_By_from_B0_uT": _float(row.get("delta_By_median_uT")),
                "delta_Bz_from_B0_uT": _float(row.get("delta_Bz_median_uT")),
                "summary_window_s": _float(row.get("summary_window_s")),
                "state_n_samples": _int(row.get("n")),
                "state_duration_s": _float(row.get("summary_window_s")),
                "pair_delta_F_N": math.nan,
                "pair_delta_d_mm": math.nan,
                "pair_delta_Bvec_uT": math.nan,
                "pair_verdict": "heldout",
            }
        )
    return _add_model_features(pd.DataFrame(rows))


def load_heldout_states(summary_paths: list[Path] | None = None) -> pd.DataFrame:
    """Load all accepted held-out dense-loop state summaries."""
    paths = HELDOUT_SUMMARIES if summary_paths is None else summary_paths
    frames = [prepare_heldout_states(pd.read_csv(path), summary_path=path) for path in paths]
    return pd.concat(frames, ignore_index=True)


def _add_model_features(states: pd.DataFrame) -> pd.DataFrame:
    states = states.copy()
    states = states.dropna(subset=["F_N", "d_mm", "Bx_uT", "By_uT", "Bz_uT", "Bmag_uT"]).copy()

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
        "recovery_s",
    ]
    for col in numeric_cols:
        if col not in states.columns:
            states[col] = 0.0
        states[col] = pd.to_numeric(states[col], errors="coerce")

    for col in ["cycle_index", "state_index", "preload_extra_mm", "preload_hold_s", "recovery_s"]:
        states[col] = states[col].fillna(0.0)

    db_cols = ["delta_Bx_from_B0_uT", "delta_By_from_B0_uT", "delta_Bz_from_B0_uT"]
    for col in db_cols:
        states[col] = states[col].fillna(0.0)
    states["delta_Bvec_from_B0_uT"] = np.sqrt(
        states["delta_Bx_from_B0_uT"] ** 2
        + states["delta_By_from_B0_uT"] ** 2
        + states["delta_Bz_from_B0_uT"] ** 2
    )

    if "path_label" not in states.columns:
        states["path_label"] = ""
    if "path_family" not in states.columns:
        states["path_family"] = ""

    group_cols = ["session_id", "trial", "pair_id", "experiment", "path_family"]
    for col in group_cols:
        if col not in states.columns:
            states[col] = ""
    grouped = states.groupby(group_cols, dropna=False)
    states["pair_Bmag_max_uT"] = grouped["Bmag_uT"].transform("max")
    states["pair_Bmag_min_uT"] = grouped["Bmag_uT"].transform("min")
    states["pair_Bmag_range_uT"] = states["pair_Bmag_max_uT"] - states["pair_Bmag_min_uT"]
    states["pair_state_index"] = states.groupby(group_cols, dropna=False).cumcount()

    states["is_preload"] = (states["path_label"] == "preload_deep").astype(int)
    states["is_return"] = (states["path_label"] == "return_unloading").astype(int)
    states["is_same_d_family"] = (states["path_family"] == "same_d_different_F").astype(int)
    states["session_id"] = states["session_id"].astype(str)
    return states.reset_index(drop=True)


def prepare_training_states() -> pd.DataFrame:
    states = pd.read_csv(TRAIN_STATE_DATA)
    train = select_training_states(states, HELDOUT_SESSION_IDS)
    return _add_model_features(train)


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


def model_specs() -> list[tuple[str, Pipeline, list[str]]]:
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

    return [
        ("magnetic_plain_ridge", _ridge_model(magnetic, []), magnetic),
        ("magnetic_path_label_ridge", _ridge_model(magnetic + path_numeric, path_cats), magnetic + path_numeric + path_cats),
        (
            "magnetic_path_memory_ridge",
            _ridge_model(magnetic + path_numeric + memory_numeric, path_cats),
            magnetic + path_numeric + memory_numeric + path_cats,
        ),
        ("magnetic_plain_random_forest", _rf_model(magnetic, []), magnetic),
        (
            "magnetic_path_memory_random_forest",
            _rf_model(magnetic + path_numeric + memory_numeric, path_cats),
            magnetic + path_numeric + memory_numeric + path_cats,
        ),
    ]


def fit_predict_heldout(train: pd.DataFrame, heldout: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    leaked = _session_id_set(HELDOUT_SESSION_IDS) & set(train["session_id"].astype(str))
    if leaked:
        raise ValueError(f"held-out session leaked into training: {sorted(leaked)}")

    y_train = train[TARGETS].to_numpy(float)
    pred_rows: list[pd.DataFrame] = []
    for name, model, features in model_specs():
        fitted = model.fit(train[features], y_train)
        pred = fitted.predict(heldout[features])
        out = heldout[
            [
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
            ]
        ].copy()
        out["model"] = name
        out["F_pred_N"] = pred[:, 0]
        out["d_pred_mm"] = pred[:, 1]
        out["F_error_N"] = out["F_pred_N"] - out["F_N"]
        out["d_error_mm"] = out["d_pred_mm"] - out["d_mm"]
        pred_rows.append(out)

    predictions = pd.concat(pred_rows, ignore_index=True)
    metric_rows = [_metric_row(model, chunk, len(train)) for model, chunk in predictions.groupby("model")]
    metrics = _add_relative_metrics(pd.DataFrame(metric_rows))
    metrics = metrics.sort_values(["F_MAE_N", "d_MAE_mm"]).reset_index(drop=True)
    return metrics, predictions


def _metric_row(model: str, chunk: pd.DataFrame, train_n_states: int) -> dict:
    f_true = chunk["F_N"].to_numpy(float)
    f_pred = chunk["F_pred_N"].to_numpy(float)
    d_true = chunk["d_mm"].to_numpy(float)
    d_pred = chunk["d_pred_mm"].to_numpy(float)
    return {
        "model": model,
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
    plain = out[out["model"] == "magnetic_plain_ridge"].iloc[0]
    out["F_MAE_vs_plain_pct"] = (plain["F_MAE_N"] - out["F_MAE_N"]) / plain["F_MAE_N"] * 100.0
    out["d_MAE_vs_plain_pct"] = (plain["d_MAE_mm"] - out["d_MAE_mm"]) / plain["d_MAE_mm"] * 100.0
    out["balanced_relative_error"] = (out["F_MAE_N"] / plain["F_MAE_N"]) + (out["d_MAE_mm"] / plain["d_MAE_mm"])
    return out


def plot_results(metrics: pd.DataFrame, predictions: pd.DataFrame) -> None:
    order = [
        "magnetic_plain_ridge",
        "magnetic_path_label_ridge",
        "magnetic_path_memory_ridge",
        "magnetic_plain_random_forest",
        "magnetic_path_memory_random_forest",
    ]
    labels = ["plain\nridge", "path-label\nridge", "path-memory\nridge", "plain\nRF", "path-memory\nRF"]
    colors = [BLACK, BLUE, RED, BLACK, RED]
    metric_index = metrics.set_index("model")

    best_balanced = metrics.sort_values("balanced_relative_error").iloc[0]["model"]
    best = predictions[predictions["model"] == best_balanced].copy()
    path_colors = {"direct_loading": BLACK, "preload_deep": GRAY, "return_unloading": BLUE}
    point_colors = best["path_label"].map(path_colors).fillna(RED)

    fig = plt.figure(figsize=(13.5, 8.4), dpi=180)
    gs = fig.add_gridspec(2, 2, hspace=0.38, wspace=0.30)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1])

    x = np.arange(len(order))
    ax1.bar(x, metric_index.loc[order, "F_MAE_N"], color=colors, width=0.70)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=8)
    ax1.set_ylabel("held-out F MAE (N)")
    ax1.set_title("a  Force prediction error")
    ax1.grid(axis="y", color=LIGHT_GRAY, linewidth=0.8)
    ax1.set_axisbelow(True)

    ax2.bar(x, metric_index.loc[order, "d_MAE_mm"], color=colors, width=0.70)
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=8)
    ax2.set_ylabel("held-out d MAE (mm)")
    ax2.set_title("b  Displacement prediction error")
    ax2.grid(axis="y", color=LIGHT_GRAY, linewidth=0.8)
    ax2.set_axisbelow(True)

    ax3.scatter(best["F_N"], best["F_pred_N"], s=32, c=point_colors, alpha=0.82)
    f_min = min(best["F_N"].min(), best["F_pred_N"].min())
    f_max = max(best["F_N"].max(), best["F_pred_N"].max())
    ax3.plot([f_min, f_max], [f_min, f_max], color=RED, linewidth=1.1)
    ax3.set_xlabel("measured F (N)")
    ax3.set_ylabel("predicted F (N)")
    ax3.set_title(f"c  Best balanced held-out model: {best_balanced}")
    ax3.grid(color=LIGHT_GRAY, linewidth=0.8)

    ax4.scatter(best["d_mm"], best["d_pred_mm"], s=32, c=point_colors, alpha=0.82)
    d_min = min(best["d_mm"].min(), best["d_pred_mm"].min())
    d_max = max(best["d_mm"].max(), best["d_pred_mm"].max())
    ax4.plot([d_min, d_max], [d_min, d_max], color=RED, linewidth=1.1)
    ax4.set_xlabel("measured d (mm)")
    ax4.set_ylabel("predicted d (mm)")
    ax4.set_title("d  Held-out displacement prediction")
    ax4.grid(color=LIGHT_GRAY, linewidth=0.8)

    legend_handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=BLACK, markeredgecolor=BLACK, label="loading", markersize=6),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=GRAY, markeredgecolor=GRAY, label="preload", markersize=6),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=BLUE, markeredgecolor=BLUE, label="unloading", markersize=6),
    ]
    ax3.legend(handles=legend_handles, frameon=False, fontsize=8, loc="upper left")

    fig.suptitle("Stage 6.2: model-level held-out local dense-loop validation", x=0.06, ha="left", fontsize=16, fontweight="bold")
    fig.text(
        0.06,
        0.94,
        "Train on Stage 5 model dataset; test only on session_20260615_160438 interleaved held-out d grid",
        fontsize=10,
        color="#555555",
    )
    fig.savefig(OUT_FIGURE, bbox_inches="tight")
    plt.close(fig)


def write_report(metrics: pd.DataFrame, predictions: pd.DataFrame, train: pd.DataFrame, heldout: pd.DataFrame) -> None:
    best_f = metrics.sort_values("F_MAE_N").iloc[0]
    best_d = metrics.sort_values("d_MAE_mm").iloc[0]
    balanced = metrics.sort_values("balanced_relative_error").iloc[0]
    plain = metrics[metrics["model"] == "magnetic_plain_ridge"].iloc[0]
    memory = metrics[metrics["model"] == "magnetic_path_memory_ridge"].iloc[0]

    memory_f_gain = memory["F_MAE_vs_plain_pct"]
    memory_d_gain = memory["d_MAE_vs_plain_pct"]

    branch_metrics = (
        predictions[predictions["model"] == balanced["model"]]
        .groupby("path_label")
        .agg(
            n_states=("F_N", "size"),
            F_MAE_N=("F_error_N", lambda x: float(np.mean(np.abs(x)))),
            d_MAE_mm=("d_error_mm", lambda x: float(np.mean(np.abs(x)))),
        )
        .reset_index()
    )

    lines = [
        "# APMD Stage 6.2 Held-Out Model Validation",
        "",
        "This report is generated by `apmd_stage6_predict_local_heldout.py`.",
        "",
        "## Data Split",
        "",
        f"- Training states: `{TRAIN_STATE_DATA.relative_to(ROOT)}`",
        f"- Training rows used: {len(train)}",
        f"- Held-out sessions: {', '.join(f'`{sid}`' for sid in HELDOUT_SESSION_IDS)}",
        f"- Held-out rows used: {len(heldout)}",
        "- Split rule: the entire held-out session is excluded from training and used only for testing.",
        "",
        "## Metrics",
        "",
        metrics[
            [
                "model",
                "train_n_states",
                "heldout_n_states",
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
        "## Best Balanced Model Branch Check",
        "",
        branch_metrics.to_markdown(index=False, floatfmt=".4f"),
        "",
        "## Main Result",
        "",
        f"- Best force model: `{best_f['model']}` with held-out F MAE = {best_f['F_MAE_N']:.3f} N.",
        f"- Best displacement model: `{best_d['model']}` with held-out d MAE = {best_d['d_MAE_mm']:.3f} mm.",
        f"- Best balanced model: `{balanced['model']}`.",
        f"- Path-memory ridge vs plain magnetic ridge: force MAE change = {memory_f_gain:+.1f}%; displacement MAE change = {memory_d_gain:+.1f}%.",
        f"- Plain magnetic ridge reference: F MAE = {plain['F_MAE_N']:.3f} N; d MAE = {plain['d_MAE_mm']:.3f} mm.",
        "",
        "## Interpretation",
        "",
        "This is a stricter model-level test than Stage 5 cross-validation because the held-out d grid is interleaved between the dense-loop training grid points and the full session is never used for training. A useful result here supports the local proof-of-mechanism claim: active path information can help map magnetic states to force and displacement inside the selected local work zone.",
        "",
        "This still remains a local mechanism-validation result. It should not be interpreted as full prosthetic-socket range deployment.",
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
    train = prepare_training_states()
    heldout = load_heldout_states()
    metrics, predictions = fit_predict_heldout(train, heldout)
    metrics.to_csv(OUT_METRICS, index=False)
    predictions.to_csv(OUT_PREDICTIONS, index=False)
    plot_results(metrics, predictions)
    write_report(metrics, predictions, train, heldout)
    print(f"training rows: {len(train)}")
    print(f"held-out rows: {len(heldout)}")
    print(f"wrote {OUT_METRICS.relative_to(ROOT)}")
    print(f"wrote {OUT_PREDICTIONS.relative_to(ROOT)}")
    print(f"wrote {OUT_FIGURE.relative_to(ROOT)}")
    print(f"wrote {OUT_REPORT.relative_to(ROOT)}")
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
