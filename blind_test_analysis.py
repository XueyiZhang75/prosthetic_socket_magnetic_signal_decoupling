"""Pilot blind-test analysis for normal F-d magnetic decoupling.

This script keeps training and blind sessions separated:

    train: calibration sessions used to fit B -> [F, d]
    blind: held-out sessions used only for final error reporting

It reads state time-series CSV files from I+/J+/future blind protocols, reduces
each state to one head-window summary point, fits a small linear ridge model,
and compares it against simple single-variable baselines.
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np


B_COLS = ("delta_Bx_uT", "delta_By_uT", "delta_Bz_uT")
STATE_FILE_PATTERNS = (
    "Iplus_same_d_*_rep*.csv",
    "Jplus_same_F_*_rep*.csv",
    "Blind_*_rep*.csv",
    "O_blind_*_rep*.csv",
)
DEFAULT_REPORT = Path("reports") / "BLIND_TEST_ANALYSIS.md"


@dataclass(frozen=True)
class LinearModel:
    x_mean: np.ndarray
    x_scale: np.ndarray
    coef: np.ndarray
    intercept: np.ndarray


def safe_float(value, default=math.nan):
    try:
        if value is None:
            return default
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def median_or_nan(values: Iterable[float]) -> float:
    clean = [float(v) for v in values if math.isfinite(float(v))]
    return float(np.median(clean)) if clean else math.nan


def first_finite(*values) -> float:
    for value in values:
        parsed = safe_float(value)
        if math.isfinite(parsed):
            return parsed
    return math.nan


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    true = np.asarray(y_true, dtype=float)
    pred = np.asarray(y_pred, dtype=float)
    err = pred - true
    return {
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err**2))),
        "max_abs": float(np.max(np.abs(err))),
    }


def fit_linear_ridge(x: np.ndarray, y: np.ndarray, *, alpha: float = 1e-6) -> LinearModel:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.ndim != 2:
        raise ValueError("x must be a 2-D array")
    if y.ndim == 1:
        y = y[:, None]
    if len(x) != len(y):
        raise ValueError("x and y must have the same number of rows")
    if len(x) < 2:
        raise ValueError("Need at least two rows to fit a linear model")

    x_mean = np.mean(x, axis=0)
    x_scale = np.std(x, axis=0)
    x_scale[x_scale <= 1e-12] = 1.0
    xs = (x - x_mean) / x_scale
    design = np.column_stack([xs, np.ones(len(xs))])
    penalty = np.eye(design.shape[1]) * float(alpha)
    penalty[-1, -1] = 0.0
    beta = np.linalg.solve(design.T @ design + penalty, design.T @ y)
    return LinearModel(
        x_mean=x_mean,
        x_scale=x_scale,
        coef=beta[:-1, :],
        intercept=beta[-1, :],
    )


def predict_linear(model: LinearModel, x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    xs = (x - model.x_mean) / model.x_scale
    return xs @ model.coef + model.intercept


def summarize_state_rows(
    rows: Sequence[dict[str, str]],
    *,
    session: str,
    source_file: str,
    stage: str,
    window_s: float = 5.0,
) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        state = str(row.get("state_label") or row.get("phase") or "state")
        trial = str(row.get("trial") or row.get("repeat_id") or "")
        pair = str(row.get("pair_id") or row.get("target_label") or "")
        groups.setdefault((state, trial, pair), []).append(row)

    points: list[dict[str, object]] = []
    for (state, trial, pair), group_rows in sorted(groups.items()):
        t_values = [safe_float(r.get("t_rel_s")) for r in group_rows]
        finite_t = [t for t in t_values if math.isfinite(t)]
        if finite_t:
            t0 = min(finite_t)
            window_rows = [
                r for r in group_rows
                if safe_float(r.get("t_rel_s")) <= t0 + window_s
            ]
        else:
            window_rows = group_rows
        if not window_rows:
            continue

        point = {
            "session": session,
            "source_file": source_file,
            "stage": stage,
            "state_label": state,
            "trial": trial,
            "pair_id": pair,
            "n_rows": len(window_rows),
            "F_N": median_or_nan(safe_float(r.get("F_N")) for r in window_rows),
            "d_mm": median_or_nan(
                first_finite(r.get("d_mm"), r.get("d_actual_mm")) for r in window_rows
            ),
            "Bmag_uT": median_or_nan(safe_float(r.get("Bmag_uT")) for r in window_rows),
        }
        for col in B_COLS:
            point[col] = median_or_nan(safe_float(r.get(col)) for r in window_rows)
        if not math.isfinite(float(point["Bmag_uT"])):
            point["Bmag_uT"] = float(
                np.linalg.norm([float(point[col]) for col in B_COLS])
            )
        if all(math.isfinite(float(point[col])) for col in ("F_N", "d_mm", *B_COLS)):
            points.append(point)
    return points


def load_session_points(data_root: Path, session_name: str, *, window_s: float = 5.0) -> list[dict[str, object]]:
    session = data_root / session_name
    if not session.exists():
        raise FileNotFoundError(f"Session not found: {session}")
    points: list[dict[str, object]] = []
    for pattern in STATE_FILE_PATTERNS:
        for path in sorted(session.glob(pattern)):
            stage = _stage_from_filename(path.name)
            points.extend(
                summarize_state_rows(
                    read_csv(path),
                    session=session_name,
                    source_file=path.name,
                    stage=stage,
                    window_s=window_s,
                )
            )
    return points


def is_preload_state(point: dict[str, object]) -> bool:
    state = str(point.get("state_label", "")).lower()
    return "preload" in state


def filter_preload_points(
    points: Sequence[dict[str, object]],
    *,
    include_preload: bool = False,
) -> list[dict[str, object]]:
    if include_preload:
        return list(points)
    return [p for p in points if not is_preload_state(p)]


def _stage_from_filename(name: str) -> str:
    if name.startswith("Iplus"):
        return "Iplus"
    if name.startswith("Jplus"):
        return "Jplus"
    if name.startswith("Blind") or name.startswith("O_blind"):
        return "blind"
    return "unknown"


def points_to_arrays(points: Sequence[dict[str, object]]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.asarray([[safe_float(p[c]) for c in B_COLS] for p in points], dtype=float)
    y = np.asarray([[safe_float(p["F_N"]), safe_float(p["d_mm"])] for p in points], dtype=float)
    bmag = np.asarray([[safe_float(p.get("Bmag_uT"))] for p in points], dtype=float)
    mask = np.isfinite(x).all(axis=1) & np.isfinite(y).all(axis=1)
    return x[mask], y[mask], bmag[mask]


def evaluate_models(
    train_points: Sequence[dict[str, object]],
    blind_points: Sequence[dict[str, object]],
    *,
    alpha: float = 1e-6,
) -> dict[str, object]:
    x_train, y_train, bmag_train = points_to_arrays(train_points)
    x_blind, y_blind, bmag_blind = points_to_arrays(blind_points)
    if len(x_train) < 4:
        raise ValueError("Need at least four training state points")
    if len(x_blind) < 1:
        raise ValueError("Need at least one blind state point")

    main_model = fit_linear_ridge(x_train, y_train, alpha=alpha)
    main_pred = predict_linear(main_model, x_blind)

    force_from_d = fit_linear_ridge(y_train[:, [1]], y_train[:, [0]], alpha=alpha)
    force_baseline_pred = predict_linear(force_from_d, y_blind[:, [1]])[:, 0]

    d_from_bmag = fit_linear_ridge(bmag_train, y_train[:, [1]], alpha=alpha)
    d_baseline_pred = predict_linear(d_from_bmag, bmag_blind)[:, 0]

    mean_pred = np.repeat(np.mean(y_train, axis=0, keepdims=True), len(y_blind), axis=0)

    return {
        "n_train": int(len(x_train)),
        "n_blind": int(len(x_blind)),
        "main_F": compute_metrics(y_blind[:, 0], main_pred[:, 0]),
        "main_d": compute_metrics(y_blind[:, 1], main_pred[:, 1]),
        "baseline_F_from_d": compute_metrics(y_blind[:, 0], force_baseline_pred),
        "baseline_d_from_Bmag": compute_metrics(y_blind[:, 1], d_baseline_pred),
        "baseline_mean_F": compute_metrics(y_blind[:, 0], mean_pred[:, 0]),
        "baseline_mean_d": compute_metrics(y_blind[:, 1], mean_pred[:, 1]),
    }


def render_report(
    result: dict[str, object],
    *,
    train_sessions: Sequence[str],
    blind_sessions: Sequence[str],
    include_preload: bool = False,
) -> str:
    lines = [
        "# Pilot Blind-Test Analysis",
        "",
        f"Training sessions: `{', '.join(train_sessions)}`",
        f"Blind sessions: `{', '.join(blind_sessions)}`",
        f"Auxiliary preload states: `{'included' if include_preload else 'excluded'}`",
        "",
        f"Training state points: {result['n_train']}",
        f"Blind state points: {result['n_blind']}",
        "",
        "## Error Metrics",
        "",
        "| Output | Model | MAE | RMSE | Max abs |",
        "|---|---|---:|---:|---:|",
    ]
    rows = [
        ("F_N", "Bxyz -> F", result["main_F"], "N"),
        ("F_N", "baseline F=h(d)", result["baseline_F_from_d"], "N"),
        ("F_N", "baseline mean", result["baseline_mean_F"], "N"),
        ("d_mm", "Bxyz -> d", result["main_d"], "mm"),
        ("d_mm", "baseline d=g(|B|)", result["baseline_d_from_Bmag"], "mm"),
        ("d_mm", "baseline mean", result["baseline_mean_d"], "mm"),
    ]
    for output, model, metrics, unit in rows:
        assert isinstance(metrics, dict)
        lines.append(
            f"| {output} | {model} | {metrics['mae']:.4f} {unit} | "
            f"{metrics['rmse']:.4f} {unit} | {metrics['max_abs']:.4f} {unit} |"
        )

    main_f = result["main_F"]
    main_d = result["main_d"]
    base_f = result["baseline_F_from_d"]
    base_d = result["baseline_d_from_Bmag"]
    assert isinstance(main_f, dict) and isinstance(main_d, dict)
    assert isinstance(base_f, dict) and isinstance(base_d, dict)
    verdict = (
        "PASS"
        if main_f["mae"] < base_f["mae"] and main_d["mae"] < base_d["mae"]
        else "NOT PASS"
    )
    lines.extend(
        [
            "",
            "## Verdict",
            "",
            f"`{verdict}`: Bxyz model must beat `F=h(d)` for force and `d=g(|B|)` for displacement by MAE.",
            "",
        ]
    )
    return "\n".join(lines)


def _parse_session_list(values: Sequence[str]) -> list[str]:
    sessions: list[str] = []
    for value in values:
        for part in value.split(","):
            clean = part.strip()
            if clean:
                sessions.append(clean)
    return sessions


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("decouple_data"))
    parser.add_argument("--train-session", action="append", default=[])
    parser.add_argument("--blind-session", action="append", default=[])
    parser.add_argument("--alpha", type=float, default=1e-6)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--include-preload",
        action="store_true",
        help="include auxiliary preload_deep states in training/scoring",
    )
    args = parser.parse_args(argv)

    train_sessions = _parse_session_list(args.train_session)
    blind_sessions = _parse_session_list(args.blind_session)
    if not train_sessions:
        raise SystemExit("Provide at least one --train-session.")
    if not blind_sessions:
        raise SystemExit("Provide at least one --blind-session.")

    train_points: list[dict[str, object]] = []
    blind_points: list[dict[str, object]] = []
    for session in train_sessions:
        train_points.extend(load_session_points(args.data_root, session))
    for session in blind_sessions:
        blind_points.extend(load_session_points(args.data_root, session))
    train_points = filter_preload_points(
        train_points,
        include_preload=args.include_preload,
    )
    blind_points = filter_preload_points(
        blind_points,
        include_preload=args.include_preload,
    )

    result = evaluate_models(train_points, blind_points, alpha=args.alpha)
    report = render_report(
        result,
        train_sessions=train_sessions,
        blind_sessions=blind_sessions,
        include_preload=args.include_preload,
    )
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(report, encoding="utf-8")
    print(f"Wrote {args.report_path}")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
