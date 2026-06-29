"""Stage 6.3 local-identifiability model comparison.

This script keeps the Stage 6.2 held-out split, then adds local APMD
coordinates derived from Stage 4 active path-pair sensitivity estimates.
It asks whether j_F/j_d geometry improves F,d prediction beyond simple
loading/unloading label compensation.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.text import Text
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

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
DATA_DIR = ROOT / "decouple_data"

JF_DATA = REPORTS_DIR / "apmd_stage4_jF_from_same_d_pairs.csv"
JD_DATA = REPORTS_DIR / "apmd_stage4_jd_from_same_f_pairs.csv"
BLOCK_L_JF_SOURCES = [
    DATA_DIR / "session_20260622_203244" / "block_L_same_d_local_sensitivity_pair_summary.csv",
    DATA_DIR / "session_20260623_091618" / "block_L_same_d_local_sensitivity_pair_summary.csv",
]
BLOCK_S_JF_SOURCES = [
    DATA_DIR / "session_20260624_173531" / "shallow_same_d_local_sensitivity_pair_summary.csv",
    DATA_DIR / "session_20260624_183829" / "shallow_same_d_local_sensitivity_pair_summary.csv",
    DATA_DIR / "session_20260624_184739" / "shallow_same_d_local_sensitivity_pair_summary.csv",
    DATA_DIR / "session_20260624_190156" / "shallow_same_d_local_sensitivity_pair_summary.csv",
    DATA_DIR / "session_20260624_194759" / "shallow_same_d_local_sensitivity_pair_summary.csv",
]
BLOCK_H_JF_SOURCES = [
    DATA_DIR / "session_20260624_090338" / "upper_same_d_local_sensitivity_pair_summary.csv",
]

OUT_METRICS = REPORTS_DIR / "apmd_stage6_local_identifiability_model_metrics.csv"
OUT_PREDICTIONS = REPORTS_DIR / "apmd_stage6_local_identifiability_predictions.csv"
OUT_FIGURE = REPORTS_DIR / "apmd_stage6_local_identifiability_comparison.png"
OUT_FIGURE_PDF = REPORTS_DIR / "apmd_stage6_local_identifiability_comparison.pdf"
OUT_REPORT = REPORTS_DIR / "APMD_STAGE6_LOCAL_IDENTIFIABILITY_MODEL.md"

BLACK = "#222222"
RED = "#c23b3b"
BLUE = "#1f77b4"
GRAY = "#777777"
LIGHT_GRAY = "#e8e8e8"

plt.rcParams.update(
    {
        "font.family": "Arial",
        "font.sans-serif": ["Arial"],
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(math.sqrt(mean_squared_error(y_true, y_pred)))


def _safe_float(value: object, default: float = math.nan) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _norm(v: np.ndarray) -> float:
    return float(np.linalg.norm(v))


def _unit(v: np.ndarray) -> np.ndarray:
    n = _norm(v)
    if n <= 0:
        return np.zeros_like(v, dtype=float)
    return v / n


def _angle_deg(a: np.ndarray, b: np.ndarray) -> float:
    na = _norm(a)
    nb = _norm(b)
    if na <= 0 or nb <= 0:
        return math.nan
    cos_abs = abs(float(np.dot(a, b) / (na * nb)))
    cos_abs = max(-1.0, min(1.0, cos_abs))
    return float(math.degrees(math.acos(cos_abs)))


def _scaled_condition(a: np.ndarray, b: np.ndarray) -> float:
    ua = _unit(a)
    ub = _unit(b)
    if _norm(ua) <= 0 or _norm(ub) <= 0:
        return math.nan
    s = np.linalg.svd(np.column_stack([ua, ub]), compute_uv=False)
    return float(s[0] / s[-1]) if s[-1] > 0 else math.inf


def _nearest_row(table: pd.DataFrame, column: str, value: float) -> pd.Series:
    vals = pd.to_numeric(table[column], errors="coerce")
    idx = (vals - value).abs().idxmin()
    return table.loc[idx]


def _projection_residual(delta_b: np.ndarray, j_f: np.ndarray, j_d: np.ndarray) -> float:
    axes = np.column_stack([_unit(j_f), _unit(j_d)])
    if np.linalg.matrix_rank(axes) == 0:
        return _norm(delta_b)
    coeffs, *_ = np.linalg.lstsq(axes, delta_b, rcond=None)
    projection = axes @ coeffs
    return _norm(delta_b - projection)


def _dual_coordinate_features(delta_b: np.ndarray, j_f: np.ndarray, j_d: np.ndarray) -> dict[str, float]:
    axes = np.column_stack([_unit(j_f), _unit(j_d)])
    delta_norm = _norm(delta_b)

    if np.linalg.matrix_rank(axes) < 2:
        c_f = math.nan
        c_d = math.nan
        residual = delta_norm
    else:
        coeffs, *_ = np.linalg.lstsq(axes, delta_b, rcond=None)
        projection = axes @ coeffs
        c_f = float(coeffs[0])
        c_d = float(coeffs[1])
        residual = _norm(delta_b - projection)

    residual_fraction = residual / delta_norm if delta_norm > 1e-9 else 0.0
    return {
        "local_dual_c_F_uT": c_f,
        "local_dual_c_d_uT": c_d,
        "local_dual_residual_uT": residual,
        "local_dual_residual_fraction": residual_fraction,
        "local_delta_B_norm_uT": delta_norm,
    }


def _zone_id(d_target: float, f_target: float) -> str:
    d_code = int(round(d_target * 100.0))
    f_code = int(round(f_target * 100.0))
    return f"d{d_code:03d}_F{f_code:03d}"


def _load_block_jf_table(sources: list[Path], work_zone_id: str, strong_only: bool) -> pd.DataFrame:
    frames = [pd.read_csv(path) for path in sources if path.exists()]
    if not frames:
        return pd.DataFrame()

    rows = pd.concat(frames, ignore_index=True)
    if strong_only and "verdict" in rows.columns:
        rows = rows[rows["verdict"].astype(str).str.contains("strong", case=False, na=False)].copy()
    if rows.empty:
        return pd.DataFrame()

    out_rows: list[dict[str, object]] = []
    for target_d, chunk in rows.groupby("d_target_mm"):
        delta_f = pd.to_numeric(chunk["delta_F_N"], errors="coerce").abs()
        median_abs_delta_f = float(delta_f.median())
        median_delta_bx = float(pd.to_numeric(chunk["delta_Bx_uT"], errors="coerce").median())
        median_delta_by = float(pd.to_numeric(chunk["delta_By_uT"], errors="coerce").median())
        median_delta_bz = float(pd.to_numeric(chunk["delta_Bz_uT"], errors="coerce").median())
        median_delta_bvec = float(pd.to_numeric(chunk["delta_Bvec_uT"], errors="coerce").median())
        if median_abs_delta_f <= 0 or math.isnan(median_abs_delta_f):
            continue
        j_f = np.array(
            [
                median_delta_bx / median_abs_delta_f,
                median_delta_by / median_abs_delta_f,
                median_delta_bz / median_abs_delta_f,
            ],
            dtype=float,
        )
        out_rows.append(
            {
                "target_d_mm": float(target_d),
                "state_d_mid_mm": float(pd.to_numeric(chunk["d_direct_mm"], errors="coerce").median()),
                "state_F_mid_N": float(
                    ((pd.to_numeric(chunk["F_direct_N"], errors="coerce") + pd.to_numeric(chunk["F_return_N"], errors="coerce")) / 2.0).median()
                ),
                "n": int(len(chunk)),
                "median_abs_delta_F_N": median_abs_delta_f,
                "median_delta_Bvec_uT": median_delta_bvec,
                "noise_ratio": median_delta_bvec / 10.0,
                "median_delta_Bx_uT": median_delta_bx,
                "median_delta_By_uT": median_delta_by,
                "median_delta_Bz_uT": median_delta_bz,
                "jF_x_uT_per_N": float(j_f[0]),
                "jF_y_uT_per_N": float(j_f[1]),
                "jF_z_uT_per_N": float(j_f[2]),
                "jF_norm_uT_per_N": _norm(j_f),
                "directional_consistency": math.nan,
                "same_d_pass_rate": float(pd.to_numeric(chunk.get("same_d_ok", 1), errors="coerce").mean()),
                "force_split_pass_rate": float(pd.to_numeric(chunk.get("force_split_ok", 1), errors="coerce").mean()),
                "b_signal_pass_rate": float(pd.to_numeric(chunk.get("b_signal_ok", 1), errors="coerce").mean()),
                "work_zone_id": work_zone_id,
            }
        )
    return pd.DataFrame(out_rows)


def _load_block_l_jf_table() -> pd.DataFrame:
    return _load_block_jf_table(BLOCK_L_JF_SOURCES, work_zone_id="Block_L", strong_only=True)


def _load_block_s_jf_table() -> pd.DataFrame:
    return _load_block_jf_table(BLOCK_S_JF_SOURCES, work_zone_id="Block_S", strong_only=True)


def _load_block_h_jf_table() -> pd.DataFrame:
    # Keep weak/boundary upper-zone rows such as nominal d=4.0 mm so the model
    # can learn whether the deep end helps or hurts instead of excluding it here.
    return _load_block_jf_table(BLOCK_H_JF_SOURCES, work_zone_id="Block_H", strong_only=False)


def load_sensitivity_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    jf = pd.read_csv(JF_DATA)
    jf["work_zone_id"] = "Stage3_BlockM"
    block_s_jf = _load_block_s_jf_table()
    if not block_s_jf.empty:
        jf = pd.concat([jf, block_s_jf], ignore_index=True, sort=False)
    block_l_jf = _load_block_l_jf_table()
    if not block_l_jf.empty:
        jf = pd.concat([jf, block_l_jf], ignore_index=True, sort=False)
    block_h_jf = _load_block_h_jf_table()
    if not block_h_jf.empty:
        jf = pd.concat([jf, block_h_jf], ignore_index=True, sort=False)
    jd = pd.read_csv(JD_DATA)
    return jf, jd


def _work_zone_preference(row: pd.Series) -> str:
    text = " ".join(
        str(row.get(col, ""))
        for col in ["experiment", "source_state_csv", "raw_file", "session_id", "path_mode"]
    )
    if "Block S" in text or "shallow work-zone" in text or "_S_" in text or "5p1B_S" in text or "6p1_S" in text:
        return "Block_S"
    if "Block H" in text or "upper work-zone" in text or "_H_" in text or "5p1B_H" in text or "6p1_H" in text:
        return "Block_H"
    if "Block L" in text or "_L_" in text or "5p1B_L" in text or "6p1_L" in text:
        return "Block_L"
    return "Stage3_BlockM"


def _jf_candidates(jf_table: pd.DataFrame, row: pd.Series) -> pd.DataFrame:
    if "work_zone_id" not in jf_table.columns:
        return jf_table
    preferred = _work_zone_preference(row)
    candidates = jf_table[jf_table["work_zone_id"].astype(str) == preferred]
    if candidates.empty and preferred != "Stage3_BlockM":
        candidates = jf_table[jf_table["work_zone_id"].astype(str) == "Stage3_BlockM"]
    if candidates.empty:
        candidates = jf_table
    return candidates


def add_local_identifiability_features(
    states: pd.DataFrame,
    jf_table: pd.DataFrame,
    jd_table: pd.DataFrame,
) -> pd.DataFrame:
    """Add local j_F/j_d projection features to state-level model rows."""
    out = states.copy()
    for col in ["F_N", "d_mm", "delta_Bx_from_B0_uT", "delta_By_from_B0_uT", "delta_Bz_from_B0_uT"]:
        if col not in out.columns:
            out[col] = 0.0
        out[col] = pd.to_numeric(out[col], errors="coerce")

    rows: list[dict[str, object]] = []
    for _, row in out.iterrows():
        d_value = _safe_float(row.get("d_mm"))
        if math.isnan(d_value):
            d_value = _safe_float(row.get("d_target_mm"), 0.0)
        f_value = _safe_float(row.get("F_N"))
        if math.isnan(f_value):
            f_value = _safe_float(row.get("target_F_N"), 0.0)

        jf_candidates = _jf_candidates(jf_table, row)
        jf_row = _nearest_row(jf_candidates, "target_d_mm", d_value)
        jd_row = _nearest_row(jd_table, "target_F_N", f_value)

        j_f = np.array(
            [
                _safe_float(jf_row.get("jF_x_uT_per_N"), 0.0),
                _safe_float(jf_row.get("jF_y_uT_per_N"), 0.0),
                _safe_float(jf_row.get("jF_z_uT_per_N"), 0.0),
            ],
            dtype=float,
        )
        j_d = np.array(
            [
                _safe_float(jd_row.get("jd_x_uT_per_mm"), 0.0),
                _safe_float(jd_row.get("jd_y_uT_per_mm"), 0.0),
                _safe_float(jd_row.get("jd_z_uT_per_mm"), 0.0),
            ],
            dtype=float,
        )
        delta_b = np.array(
            [
                _safe_float(row.get("delta_Bx_from_B0_uT"), 0.0),
                _safe_float(row.get("delta_By_from_B0_uT"), 0.0),
                _safe_float(row.get("delta_Bz_from_B0_uT"), 0.0),
            ],
            dtype=float,
        )

        d_target = _safe_float(jf_row.get("target_d_mm"), 0.0)
        f_target = _safe_float(jd_row.get("target_F_N"), 0.0)
        j_f_source_zone = str(jf_row.get("work_zone_id", ""))
        zone_core = _zone_id(d_target, f_target)
        local_zone_id = f"{j_f_source_zone}_{zone_core}" if j_f_source_zone else zone_core
        unit_jf = _unit(j_f)
        unit_jd = _unit(j_d)
        angle_deg = _angle_deg(j_f, j_d)
        scaled_condition = _scaled_condition(j_f, j_d)
        d_distance = abs(d_value - d_target)
        f_distance = abs(f_value - f_target)
        dual_features = _dual_coordinate_features(delta_b, j_f, j_d)
        sin2 = math.sin(math.radians(angle_deg)) ** 2 if math.isfinite(angle_deg) else 0.0
        condition_penalty = scaled_condition if math.isfinite(scaled_condition) and scaled_condition > 1.0 else 1.0
        distance_penalty = 1.0 + d_distance / 0.2 + f_distance / 1.0
        residual_penalty = 1.0 + _safe_float(dual_features["local_dual_residual_fraction"], 0.0)
        confidence = sin2 / max(condition_penalty * distance_penalty * residual_penalty, 1e-9)
        uncertainty = 1.0 / max(confidence, 1e-9)
        rows.append(
            {
                "local_jF_target_d_mm": d_target,
                "local_jd_target_F_N": f_target,
                "local_zone_id": local_zone_id,
                "local_jF_source_zone": j_f_source_zone,
                "local_d_distance_mm": d_distance,
                "local_F_distance_N": f_distance,
                "local_jF_norm_uT_per_N": _norm(j_f),
                "local_jd_norm_uT_per_mm": _norm(j_d),
                "local_angle_deg": angle_deg,
                "local_scaled_condition": scaled_condition,
                "local_p_F_uT": float(np.dot(delta_b, unit_jf)),
                "local_p_d_uT": float(np.dot(delta_b, unit_jd)),
                "local_residual_uT": _projection_residual(delta_b, j_f, j_d),
                **dual_features,
                "local_geometry_confidence": confidence,
                "local_geometry_uncertainty": uncertainty,
            }
        )

    feature_df = pd.DataFrame(rows, index=out.index)
    return pd.concat([out, feature_df], axis=1)


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
                    n_estimators=500,
                    min_samples_leaf=2,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def model_specs() -> list[tuple[str, str, Pipeline, list[str]]]:
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
    local_numeric = [
        "local_p_F_uT",
        "local_p_d_uT",
        "local_residual_uT",
        "local_jF_norm_uT_per_N",
        "local_jd_norm_uT_per_mm",
        "local_angle_deg",
        "local_scaled_condition",
        "local_d_distance_mm",
        "local_F_distance_N",
    ]
    path_cats = ["path_family", "path_label"]
    local_cats = ["path_family", "path_label", "local_zone_id"]

    return [
        ("plain_magnetic_ridge", "plain magnetic", _ridge_model(magnetic, []), magnetic),
        (
            "lim_style_branch_ridge",
            "Lim-style branch compensation",
            _ridge_model(magnetic + path_numeric, path_cats),
            magnetic + path_numeric + path_cats,
        ),
        (
            "apmd_path_memory_ridge",
            "APMD path memory",
            _ridge_model(magnetic + path_numeric + memory_numeric, path_cats),
            magnetic + path_numeric + memory_numeric + path_cats,
        ),
        (
            "apmd_local_identifiability_ridge",
            "APMD local identifiability",
            _ridge_model(magnetic + path_numeric + memory_numeric + local_numeric, local_cats),
            magnetic + path_numeric + memory_numeric + local_numeric + local_cats,
        ),
        (
            "apmd_path_memory_random_forest",
            "APMD path memory",
            _rf_model(magnetic + path_numeric + memory_numeric, path_cats),
            magnetic + path_numeric + memory_numeric + path_cats,
        ),
        (
            "apmd_local_identifiability_random_forest",
            "APMD local identifiability",
            _rf_model(magnetic + path_numeric + memory_numeric + local_numeric, local_cats),
            magnetic + path_numeric + memory_numeric + local_numeric + local_cats,
        ),
    ]


def _ensure_features(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in features:
        if col not in out.columns:
            out[col] = ""
    return out


def error_bar_model_order() -> list[str]:
    return [
        "plain_magnetic_ridge",
        "lim_style_branch_ridge",
        "apmd_path_memory_ridge",
        "apmd_local_identifiability_ridge",
    ]


def _error_bar_labels(order: list[str]) -> list[str]:
    labels = {
        "plain_magnetic_ridge": "Plain Model",
        "lim_style_branch_ridge": "Path-label Model",
        "apmd_path_memory_ridge": "Path-memory Model",
        "apmd_local_identifiability_ridge": "Local-ID Model",
        "apmd_path_memory_random_forest": "path-memory\nRF",
        "apmd_local_identifiability_random_forest": "local-ID\nRF",
    }
    return [labels.get(model, model.replace("_", "\n")) for model in order]


def _error_bar_colors(order: list[str]) -> list[str]:
    colors = {
        "plain_magnetic_ridge": BLACK,
        "lim_style_branch_ridge": BLUE,
        "apmd_path_memory_ridge": GRAY,
        "apmd_local_identifiability_ridge": RED,
        "apmd_path_memory_random_forest": "#a6a6a6",
        "apmd_local_identifiability_random_forest": "#d66565",
    }
    return [colors.get(model, GRAY) for model in order]


def _add_value_labels(ax: plt.Axes, x: np.ndarray, values: pd.Series, fmt: str) -> None:
    upper = float(values.max())
    offset = upper * 0.025 if upper > 0 else 0.02
    for xpos, value in zip(x, values):
        ax.text(
            xpos,
            float(value) + offset,
            fmt.format(float(value)),
            ha="center",
            va="bottom",
            fontsize=7,
            fontfamily="Arial",
            color="#333333",
        )


def _force_arial(fig: plt.Figure) -> None:
    for text in fig.findobj(lambda obj: isinstance(obj, Text)):
        text.set_fontfamily("Arial")


def fit_predict_heldout(train: pd.DataFrame, heldout: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    leaked = _session_id_set(HELDOUT_SESSION_IDS) & set(train["session_id"].astype(str))
    if leaked:
        raise ValueError(f"held-out session leaked into training: {sorted(leaked)}")

    y_train = train[TARGETS].to_numpy(float)
    pred_rows: list[pd.DataFrame] = []
    for name, family, model, features in model_specs():
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
            "local_p_F_uT",
            "local_p_d_uT",
            "local_residual_uT",
            "local_angle_deg",
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
    plain = out[out["model"] == "plain_magnetic_ridge"].iloc[0]
    lim = out[out["model"] == "lim_style_branch_ridge"].iloc[0]
    out["F_MAE_vs_plain_pct"] = (plain["F_MAE_N"] - out["F_MAE_N"]) / plain["F_MAE_N"] * 100.0
    out["d_MAE_vs_plain_pct"] = (plain["d_MAE_mm"] - out["d_MAE_mm"]) / plain["d_MAE_mm"] * 100.0
    out["F_MAE_vs_lim_style_pct"] = (lim["F_MAE_N"] - out["F_MAE_N"]) / lim["F_MAE_N"] * 100.0
    out["d_MAE_vs_lim_style_pct"] = (lim["d_MAE_mm"] - out["d_MAE_mm"]) / lim["d_MAE_mm"] * 100.0
    out["balanced_relative_error"] = (out["F_MAE_N"] / plain["F_MAE_N"]) + (out["d_MAE_mm"] / plain["d_MAE_mm"])
    out["passes_current_F_goal"] = out["F_MAE_N"] <= 0.75
    out["passes_ideal_F_goal"] = out["F_MAE_N"] <= 0.50
    out["passes_d_goal"] = out["d_MAE_mm"] <= 0.05
    return out


def plot_results(metrics: pd.DataFrame, predictions: pd.DataFrame) -> None:
    order = error_bar_model_order()
    labels = _error_bar_labels(order)
    colors = _error_bar_colors(order)
    metric_index = metrics.set_index("model")
    missing = [model for model in order if model not in metric_index.index]
    if missing:
        raise RuntimeError(f"Missing metrics for error-bar plot: {missing}")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.8, 4.8), dpi=220)

    x = np.arange(len(order))
    f_values = metric_index.loc[order, "F_MAE_N"]
    d_values = metric_index.loc[order, "d_MAE_mm"]

    ax1.bar(x, f_values, color=colors, width=0.72)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=8)
    ax1.set_ylabel("held-out F MAE (N)")
    ax1.set_title("a  Force error")
    ax1.grid(axis="y", color=LIGHT_GRAY, linewidth=0.8)
    ax1.set_axisbelow(True)
    _add_value_labels(ax1, x, f_values, "{:.3f}")

    ax2.bar(x, d_values, color=colors, width=0.72)
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=8)
    ax2.set_ylabel("held-out d MAE (mm)")
    ax2.set_title("b  Displacement error")
    ax2.grid(axis="y", color=LIGHT_GRAY, linewidth=0.8)
    ax2.set_axisbelow(True)
    _add_value_labels(ax2, x, d_values, "{:.3f}")

    for ax in [ax1, ax2]:
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)

    train_n = int(metric_index.loc[order[0], "train_n_states"])
    heldout_n = int(metric_index.loc[order[0], "heldout_n_states"])
    fig.suptitle(
        "Held-out Model Error Comparison",
        x=0.055,
        ha="left",
        fontsize=16,
        fontweight="bold",
        fontfamily="Arial",
    )
    fig.text(
        0.055,
        0.91,
        f"Train = {train_n} states; test = {heldout_n} states.",
        fontsize=10,
        fontfamily="Arial",
        color="#555555",
    )
    fig.subplots_adjust(left=0.07, right=0.985, top=0.80, bottom=0.22, wspace=0.28)
    _force_arial(fig)
    fig.savefig(OUT_FIGURE, bbox_inches="tight")
    fig.savefig(OUT_FIGURE_PDF, bbox_inches="tight")
    plt.close(fig)


def write_report(metrics: pd.DataFrame, predictions: pd.DataFrame, train: pd.DataFrame, heldout: pd.DataFrame) -> None:
    best_f = metrics.sort_values("F_MAE_N").iloc[0]
    best_d = metrics.sort_values("d_MAE_mm").iloc[0]
    local_models = metrics[metrics["model"].str.contains("local_identifiability")]
    best_local_force = local_models.sort_values("F_MAE_N").iloc[0]
    best_local = local_models.sort_values("balanced_relative_error").iloc[0]
    lim = metrics[metrics["model"] == "lim_style_branch_ridge"].iloc[0]
    local_gain_vs_lim = best_local["F_MAE_vs_lim_style_pct"]

    branch_metrics = (
        predictions[predictions["model"] == best_local["model"]]
        .groupby("path_label")
        .agg(
            n_states=("F_N", "size"),
            F_MAE_N=("F_error_N", lambda x: float(np.mean(np.abs(x)))),
            d_MAE_mm=("d_error_mm", lambda x: float(np.mean(np.abs(x)))),
        )
        .reset_index()
    )

    conclusion = "partial pass"
    if best_local["passes_current_F_goal"] and best_local["passes_d_goal"] and local_gain_vs_lim >= 15.0:
        conclusion = "pass"
    elif local_gain_vs_lim < 0:
        conclusion = "does not beat Lim-style branch compensation"

    lines = [
        "# APMD Stage 6.3 Local-Identifiability Model Comparison",
        "",
        "This report is generated by `apmd_stage6_compare_local_identifiability_models.py`.",
        "",
        "## Purpose",
        "",
        "Stage 6.3 tests whether the Stage 4 active path-pair geometry (`j_F/j_d`) helps held-out `F,d` prediction beyond simple branch-label hysteresis compensation.",
        "",
        "## Data Split",
        "",
        f"- Training rows: {len(train)}",
        f"- Held-out sessions: {', '.join(f'`{sid}`' for sid in HELDOUT_SESSION_IDS)}",
        f"- Held-out rows: {len(heldout)}",
        f"- `j_F` table: `{JF_DATA.relative_to(ROOT)}`",
        f"- `j_d` table: `{JD_DATA.relative_to(ROOT)}`",
        "- Split rule: the entire held-out session stays excluded from training.",
        "",
        "## Models Compared",
        "",
        "- `plain_magnetic_ridge`: magnetic baseline.",
        "- `lim_style_branch_ridge`: literature-style branch-label compensation baseline.",
        "- `apmd_path_memory_ridge/random_forest`: magnetic signal plus path-memory features.",
        "- `apmd_local_identifiability_ridge/random_forest`: path-memory features plus local `j_F/j_d` projection coordinates.",
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
                "F_MAE_vs_plain_pct",
                "F_MAE_vs_lim_style_pct",
                "passes_current_F_goal",
                "passes_d_goal",
            ]
        ].to_markdown(index=False, floatfmt=".4f"),
        "",
        "## Best Local-Identifiability Model by Branch",
        "",
        branch_metrics.to_markdown(index=False, floatfmt=".4f"),
        "",
        "## Main Result",
        "",
        f"- Best force model: `{best_f['model']}` with F MAE `{best_f['F_MAE_N']:.3f} N`.",
        f"- Best displacement model: `{best_d['model']}` with d MAE `{best_d['d_MAE_mm']:.3f} mm`.",
        f"- Best force-only local-identifiability model: `{best_local_force['model']}` with F MAE `{best_local_force['F_MAE_N']:.3f} N`, d MAE `{best_local_force['d_MAE_mm']:.3f} mm`.",
        f"- Best balanced local-identifiability model: `{best_local['model']}` with F MAE `{best_local['F_MAE_N']:.3f} N`, d MAE `{best_local['d_MAE_mm']:.3f} mm`.",
        f"- Lim-style branch-label baseline: F MAE `{lim['F_MAE_N']:.3f} N`, d MAE `{lim['d_MAE_mm']:.3f} mm`.",
        f"- Local-identifiability F improvement vs Lim-style baseline: `{local_gain_vs_lim:.1f}%`.",
        f"- Stage 6.3 status: **{conclusion}**.",
        "",
        "## Interpretation",
        "",
        "If the local-identifiability model improves over the Lim-style branch-label model, the result supports the APMD claim that active path-pair experiments provide usable local coordinates rather than only labels for hysteresis compensation.",
        "If it does not improve, the next step is not a broad rerun; it is targeted Stage 6.4 supplementation at the local zones where held-out error concentrates.",
        "",
        "## Outputs",
        "",
        f"- Metrics: `{OUT_METRICS.relative_to(ROOT)}`",
        f"- Predictions: `{OUT_PREDICTIONS.relative_to(ROOT)}`",
        f"- Error comparison figure: `{OUT_FIGURE.relative_to(ROOT)}`",
        f"- Error comparison figure PDF: `{OUT_FIGURE_PDF.relative_to(ROOT)}`",
        "- Held-out fit grid: `reports\\apmd_stage6_model_fit_grid_2x4.png` / `reports\\apmd_stage6_model_fit_grid_2x4.pdf`.",
    ]
    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    train = prepare_training_states()
    heldout = load_heldout_states()
    jf, jd = load_sensitivity_tables()

    train = add_local_identifiability_features(train, jf, jd)
    heldout = add_local_identifiability_features(heldout, jf, jd)

    metrics, predictions = fit_predict_heldout(train, heldout)
    metrics.to_csv(OUT_METRICS, index=False)
    predictions.to_csv(OUT_PREDICTIONS, index=False)
    plot_results(metrics, predictions)
    write_report(metrics, predictions, train, heldout)

    print("Stage 6.3 local-identifiability model comparison complete")
    print(f"  metrics    : {OUT_METRICS}")
    print(f"  predictions: {OUT_PREDICTIONS}")
    print(f"  figure     : {OUT_FIGURE}")
    print(f"  figure pdf : {OUT_FIGURE_PDF}")
    print(f"  report     : {OUT_REPORT}")
    print(metrics[["model", "F_MAE_N", "d_MAE_mm", "F_MAE_vs_lim_style_pct"]].to_string(index=False))


if __name__ == "__main__":
    main()
