"""Normal force-displacement identifiability analysis for MLX90393 data.

This module turns the v1 research plan into executable checks:

* fit the local linear model dB = J [dF, dd]^T + b;
* report whether the two Jacobian columns are independent enough to invert;
* audit whether the current stage data are suitable for a real Stage N claim.

The script is deliberately conservative. A "pass" here means the data are
usable evidence for the next modeling step; a "fail" means the experiment must
be repeated or redesigned before making a decoupling claim.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np


B_COLS = ("delta_Bx_uT", "delta_By_uT", "delta_Bz_uT")
AXIS_COLS = ("mean_Bx_uT", "mean_By_uT", "mean_Bz_uT")
SAME_D_DIFF_F_SUMMARY_NAMES = (
    "same_d_different_f_pair_summary.csv",
    "Iplus_pair_summary.csv",
)

STATIC_B_NOISE_3SIGMA_UT = 3.4
DYNAMIC_B_NOISE_3SIGMA_UT = 12.5
MIN_FORCE_EXCURSION_N = 0.02
MIN_DISPLACEMENT_EXCURSION_MM = 0.10
MIN_HOLD_R2 = 0.50
SMALL_Q_MAX_MM = 10.0


@dataclass(frozen=True)
class JacobianMetrics:
    cosine_abs: float
    angle_deg: float
    min_singular: float
    max_singular: float
    condition_number: float
    verdict: str


@dataclass(frozen=True)
class LocalJacobianFit:
    n_samples: int
    j_force: tuple[float, float, float]
    j_displacement: tuple[float, float, float]
    intercept: tuple[float, float, float]
    rmse_uT: float
    metrics: JacobianMetrics
    state_condition_number: float


@dataclass(frozen=True)
class LocalWindowFit:
    center_d_mm: float
    n_candidates: int
    fit: LocalJacobianFit


@dataclass(frozen=True)
class StageDSummary:
    session: str
    path: Path
    verdict: str
    observed_force_n: float
    observed_displacement_mm: float
    recommended_force_n: float
    recommended_displacement_mm: float


@dataclass(frozen=True)
class CheckResult:
    name: str
    verdict: str
    messages: tuple[str, ...]


@dataclass(frozen=True)
class HoldDiagnostic:
    label: str
    n_samples: int
    x_range: float
    best_r2: float
    best_axis: str
    slopes: tuple[float, float, float]
    verdict: str
    note: str


@dataclass(frozen=True)
class PairColumnEstimate:
    stage_name: str
    n_total: int
    n_usable: int
    vector: tuple[float, float, float]
    median_signal_uT: float
    median_denominator: float
    denominator_label: str
    output_unit: str


def safe_float(value, default: float = math.nan) -> float:
    try:
        if value is None:
            return default
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def latest_session_with(data_root: Path, pattern: str) -> Path | None:
    for session in sorted(data_root.glob("session_*"), reverse=True):
        if list(session.glob(pattern)):
            return session
    return None


def latest_session_with_any(data_root: Path, patterns: Sequence[str]) -> tuple[Path, str] | tuple[None, None]:
    for session in sorted(data_root.glob("session_*"), reverse=True):
        for pattern in patterns:
            if list(session.glob(pattern)):
                return session, pattern
    return None, None


def norm3(vec: Sequence[float]) -> float:
    return math.sqrt(sum(float(v) ** 2 for v in vec))


def jacobian_metrics(
    j_force: Sequence[float],
    j_displacement: Sequence[float],
    *,
    collinear_cosine_threshold: float = 0.95,
    max_condition_number: float = 10.0,
) -> JacobianMetrics:
    """Return independence metrics for the two 3-D Jacobian columns."""
    jf = np.asarray(j_force, dtype=float)
    jq = np.asarray(j_displacement, dtype=float)
    jf_norm = float(np.linalg.norm(jf))
    jq_norm = float(np.linalg.norm(jq))
    if jf_norm <= 0 or jq_norm <= 0:
        return JacobianMetrics(
            cosine_abs=math.nan,
            angle_deg=math.nan,
            min_singular=0.0,
            max_singular=0.0,
            condition_number=math.inf,
            verdict="insufficient",
        )

    cosine_abs = float(abs(np.dot(jf, jq) / (jf_norm * jq_norm)))
    cosine_abs = min(1.0, max(0.0, cosine_abs))
    angle_deg = math.degrees(math.acos(cosine_abs))
    singular = np.linalg.svd(np.column_stack([jf, jq]), compute_uv=False)
    max_s = float(singular[0])
    min_s = float(singular[-1])
    condition = max_s / min_s if min_s > 0 else math.inf

    verdict = "good"
    if cosine_abs >= collinear_cosine_threshold or condition > max_condition_number:
        verdict = "ill-conditioned"
    if not math.isfinite(condition):
        verdict = "insufficient"

    return JacobianMetrics(
        cosine_abs=cosine_abs,
        angle_deg=angle_deg,
        min_singular=min_s,
        max_singular=max_s,
        condition_number=condition,
        verdict=verdict,
    )


def fit_local_jacobian(
    rows: Iterable[dict[str, object]],
    *,
    state_cols: tuple[str, str] = ("F_N", "d_mm"),
    b_cols: tuple[str, str, str] = B_COLS,
) -> LocalJacobianFit:
    """Fit dB = J [F, d]^T + b with an intercept.

    The first state column is interpreted as force and the second as
    displacement/gap. Callers can pass q_mm as the second state column when
    true gap data are available.
    """
    clean_rows: list[dict[str, object]] = []
    for row in rows:
        values = [safe_float(row.get(c)) for c in (*state_cols, *b_cols)]
        if all(math.isfinite(v) for v in values):
            clean_rows.append(row)

    if len(clean_rows) < 4:
        raise ValueError("Need at least four finite samples to fit a 2-state Jacobian")

    x = np.asarray(
        [[safe_float(r[state_cols[0]]), safe_float(r[state_cols[1]]), 1.0] for r in clean_rows],
        dtype=float,
    )
    y = np.asarray([[safe_float(r[c]) for c in b_cols] for r in clean_rows], dtype=float)
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    pred = x @ beta
    residual = y - pred
    rmse = float(np.sqrt(np.mean(residual**2)))

    state_design = x[:, :2] - np.mean(x[:, :2], axis=0)
    singular = np.linalg.svd(state_design, compute_uv=False)
    if len(singular) < 2 or singular[-1] <= 0:
        state_condition = math.inf
    else:
        state_condition = float(singular[0] / singular[-1])

    j_force = tuple(float(v) for v in beta[0, :])
    j_displacement = tuple(float(v) for v in beta[1, :])
    intercept = tuple(float(v) for v in beta[2, :])

    return LocalJacobianFit(
        n_samples=len(clean_rows),
        j_force=j_force,
        j_displacement=j_displacement,
        intercept=intercept,
        rmse_uT=rmse,
        metrics=jacobian_metrics(j_force, j_displacement),
        state_condition_number=state_condition,
    )


def local_jacobian_windows(
    rows: Sequence[dict[str, object]],
    *,
    centers: Sequence[float] | None = None,
    half_width_mm: float = 0.45,
    min_samples: int = 8,
) -> list[LocalWindowFit]:
    """Fit local Jacobians in displacement-centered windows.

    The current benchtop data use `d_mm` as the reliable second state. Future
    data can still map physical gap into `q_mm`, but the windowing here is by
    the compression coordinate that exists in E/F/H files.
    """
    finite_rows = [r for r in rows if math.isfinite(safe_float(r.get("d_mm")))]
    if not finite_rows:
        return []

    if centers is None:
        d_values = np.asarray([safe_float(r["d_mm"]) for r in finite_rows], dtype=float)
        centers = tuple(float(v) for v in np.nanpercentile(d_values, [25, 50, 75]))

    fits: list[LocalWindowFit] = []
    used_centers: set[float] = set()
    for center in centers:
        center_key = round(float(center), 3)
        if center_key in used_centers:
            continue
        used_centers.add(center_key)

        window_rows = [
            r
            for r in finite_rows
            if abs(safe_float(r.get("d_mm")) - float(center)) <= half_width_mm
        ]
        if len(window_rows) < min_samples:
            continue
        try:
            fit = fit_local_jacobian(window_rows, state_cols=("F_N", "d_mm"))
        except ValueError:
            continue
        fits.append(
            LocalWindowFit(
                center_d_mm=float(center),
                n_candidates=len(window_rows),
                fit=fit,
            )
        )
    return fits


def linfit(x_values: Sequence[float], y_values: Sequence[float]) -> tuple[float, float, float]:
    x = np.asarray(x_values, dtype=float)
    y = np.asarray(y_values, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if len(x) < 3 or float(np.nanstd(x)) <= 1e-12:
        return math.nan, math.nan, math.nan
    slope, intercept = np.polyfit(x, y, 1)
    y_hat = slope * x + intercept
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else math.nan
    return float(slope), float(intercept), float(r2)


def parse_stage_d_summary(path: Path) -> StageDSummary:
    text = path.read_text(encoding="utf-8", errors="replace")
    session = _match_text(text, r"session:\s*([0-9_]+)", default=path.parent.name)
    verdict = _match_text(text, r"verdict\s*:\s*(.+)", default="unknown").strip()
    observed_force = _match_float(text, r"F_max observed in probe\s*:\s*([+\-0-9.]+)")
    observed_disp = _match_float(text, r"d_max observed in probe\s*:\s*([+\-0-9.]+)")
    recommended_force = _match_float(text, r"F_max\s*=\s*([+\-0-9.]+)\s*N")
    recommended_disp = _match_float(text, r"d_max\s*=\s*([+\-0-9.]+)\s*mm")
    return StageDSummary(
        session=session,
        path=path,
        verdict=verdict,
        observed_force_n=observed_force,
        observed_displacement_mm=observed_disp,
        recommended_force_n=recommended_force,
        recommended_displacement_mm=recommended_disp,
    )


def _match_text(text: str, pattern: str, *, default: str = "") -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1) if match else default


def _match_float(text: str, pattern: str) -> float:
    value = _match_text(text, pattern, default="")
    return safe_float(value)


def assess_safety_consistency(
    summary: StageDSummary,
    *,
    observed_force_max: float,
    observed_displacement_max: float,
    tolerance: float = 1.02,
) -> CheckResult:
    messages: list[str] = []
    verdict = "pass"

    if not math.isfinite(summary.recommended_force_n):
        verdict = "fail"
        messages.append("Stage D has no finite recommended F_max.")
    elif observed_force_max > summary.recommended_force_n * tolerance:
        verdict = "fail"
        messages.append(
            f"Stage E/F observed F_max={observed_force_max:.3f} N exceeds "
            f"recommended F_max={summary.recommended_force_n:.3f} N."
        )

    if not math.isfinite(summary.recommended_displacement_mm):
        verdict = "fail"
        messages.append("Stage D has no finite recommended d_max.")
    elif observed_displacement_max > summary.recommended_displacement_mm * tolerance:
        verdict = "fail"
        messages.append(
            f"Observed d_max={observed_displacement_max:.3f} mm exceeds "
            f"recommended d_max={summary.recommended_displacement_mm:.3f} mm."
        )

    if not messages:
        messages.append(
            f"Observed F_max={observed_force_max:.3f} N and d_max={observed_displacement_max:.3f} mm "
            "stay within the latest Stage D recommendation."
        )

    return CheckResult("Stage D/E safety consistency", verdict, tuple(messages))


def normalize_stage_rows(data_root: Path) -> list[dict[str, object]]:
    """Load existing E/F/H plateau-like rows into a shared schema."""
    rows: list[dict[str, object]] = []
    stage_specs = [
        ("E", "E_basic_loading_rep*.csv", "F_mean_N"),
        ("F", "F_load_unload_rep*.csv", "F_mean_N"),
        ("H", "H_force_control_rep*.csv", "F_mean_N"),
    ]
    for stage, pattern, force_col in stage_specs:
        session = latest_session_with(data_root, pattern)
        if session is None:
            continue
        for path in sorted(session.glob(pattern)):
            for raw in read_csv(path):
                d_value = safe_float(raw.get("d_actual_mm"))
                f_value = safe_float(raw.get(force_col))
                row = {
                    "stage": stage,
                    "session": session.name,
                    "source_file": path.name,
                    "phase": raw.get("phase", "loading"),
                    "control_mode": _control_mode_for_stage(stage),
                    "F_N": f_value,
                    "d_mm": d_value,
                    "q_mm": -d_value if math.isfinite(d_value) else math.nan,
                    "delta_Bx_uT": safe_float(raw.get("delta_Bx_uT")),
                    "delta_By_uT": safe_float(raw.get("delta_By_uT")),
                    "delta_Bz_uT": safe_float(raw.get("delta_Bz_uT")),
                }
                if all(math.isfinite(safe_float(row[c])) for c in ("F_N", "d_mm", *B_COLS)):
                    rows.append(row)
    return rows


def _control_mode_for_stage(stage: str) -> str:
    return {
        "E": "disp_ctrl",
        "F": "disp_ctrl_hysteresis",
        "H": "force_ctrl",
    }.get(stage, "unknown")


def stage_c_check(data_root: Path, work_d_max: float | None = None) -> CheckResult:
    session = latest_session_with(data_root, "C_summary.csv")
    if session is None:
        return CheckResult("Small-q Stage C", "fail", ("No Stage C summary found.",))

    rows = read_csv(session / "C_summary.csv")
    q_values = [safe_float(r.get("q_mm")) for r in rows]
    q_values = [q for q in q_values if math.isfinite(q)]
    if not q_values:
        return CheckResult("Small-q Stage C", "fail", (f"{session.name} has no finite q_mm values.",))

    q_min = min(q_values)
    q_max = max(q_values)
    messages = [
        f"Latest Stage C session {session.name} covers q={q_min:.2f}-{q_max:.2f} mm."
    ]
    if work_d_max and math.isfinite(work_d_max):
        messages.append(f"Current compression data reach d~{work_d_max:.2f} mm.")

    if q_min > SMALL_Q_MAX_MM:
        messages.append(
            "This is a far-field calibration, so it is process evidence only; "
            "it should not be used as the main working-zone q calibration."
        )
        return CheckResult("Small-q Stage C", "fail", tuple(messages))

    messages.append("Stage C overlaps the intended small-q working zone.")
    return CheckResult("Small-q Stage C", "pass", tuple(messages))


def latest_stage_d_summary(data_root: Path) -> StageDSummary | None:
    summaries = []
    for path in sorted(data_root.glob("session_*/D_summary.txt"), reverse=True):
        summary = parse_stage_d_summary(path)
        if summary.verdict.upper().startswith("OK"):
            summaries.append(summary)
    return summaries[0] if summaries else None


def observed_force_displacement_max(rows: Sequence[dict[str, object]]) -> tuple[float, float]:
    force_values = [safe_float(r.get("F_N")) for r in rows]
    disp_values = [safe_float(r.get("d_mm")) for r in rows]
    force_max = max([f for f in force_values if math.isfinite(f)], default=math.nan)
    disp_max = max([d for d in disp_values if math.isfinite(d)], default=math.nan)
    return force_max, disp_max


def hold_diagnostics(
    data_root: Path,
    *,
    stage: str,
    pattern: str,
    x_col: str,
    skip_initial_s: float = 0.0,
) -> list[HoldDiagnostic]:
    session = latest_session_with(data_root, pattern)
    if session is None:
        return []

    diagnostics: list[HoldDiagnostic] = []
    for path in sorted(session.glob(pattern)):
        rows = read_csv(path)
        if skip_initial_s > 0:
            t0 = min((safe_float(r.get("t_rel_s")) for r in rows), default=math.nan)
            rows = [
                r
                for r in rows
                if math.isfinite(t0) and safe_float(r.get("t_rel_s")) >= t0 + skip_initial_s
            ]
        x = [safe_float(r.get(x_col)) for r in rows]
        x_finite = [v for v in x if math.isfinite(v)]
        if len(x_finite) < 3:
            diagnostics.append(
                HoldDiagnostic(path.stem, len(rows), math.nan, math.nan, "", (math.nan,) * 3, "fail", "Not enough finite samples.")
            )
            continue

        slopes: list[float] = []
        r2s: list[float] = []
        for b_col in _hold_b_cols(rows):
            slope, _, r2 = linfit(x, [safe_float(r.get(b_col)) for r in rows])
            slopes.append(slope)
            r2s.append(r2)

        best_idx = int(np.nanargmax(np.asarray(r2s))) if any(math.isfinite(r) for r in r2s) else 0
        best_r2 = r2s[best_idx] if r2s else math.nan
        best_axis = ("Bx", "By", "Bz")[best_idx] if len(r2s) == 3 else ""
        x_range = max(x_finite) - min(x_finite)

        min_excursion = MIN_FORCE_EXCURSION_N if stage == "I" else MIN_DISPLACEMENT_EXCURSION_MM
        unit = "N" if stage == "I" else "mm"
        if x_range < min_excursion:
            verdict = "fail"
            note = f"{x_col} excursion is only {x_range:.4f} {unit}; increase hold duration or active perturbation."
        elif not math.isfinite(best_r2) or best_r2 < MIN_HOLD_R2:
            verdict = "fail"
            note = f"Best magnetic-vs-{x_col} R2={best_r2:.2f}; not strong enough for a Jacobian column."
        else:
            verdict = "pass"
            note = f"Best axis {best_axis} has R2={best_r2:.2f} over {x_range:.4f} {unit}."

        diagnostics.append(
            HoldDiagnostic(
                label=path.stem,
                n_samples=len(rows),
                x_range=x_range,
                best_r2=best_r2,
                best_axis=best_axis,
                slopes=tuple(float(s) for s in slopes[:3]),
                verdict=verdict,
                note=note,
            )
        )
    return diagnostics


def _truthy_flag(row: dict[str, object], key: str) -> bool:
    value = str(row.get(key, "")).strip().lower()
    return value in {"1", "true", "yes", "pass", "strong"}


def estimate_pair_column(
    rows: Sequence[dict[str, object]],
    *,
    stage_name: str,
    denominator_col: str,
    required_flags: Sequence[str],
    output_unit: str,
) -> PairColumnEstimate:
    """Estimate one Jacobian column from pair-summary delta rows.

    I+ rows use `delta_B / delta_F` as a force-column estimate. J+ rows use
    `delta_B / delta_d` as a displacement-column estimate. Component medians
    are used because a small number of path pairs can have sign or magnitude
    outliers.
    """
    usable: list[dict[str, object]] = []
    slopes: list[tuple[float, float, float]] = []
    signals: list[float] = []
    denominators: list[float] = []

    for row in rows:
        if required_flags and not all(_truthy_flag(row, flag) for flag in required_flags):
            continue
        denom = safe_float(row.get(denominator_col))
        b_values = [safe_float(row.get(c)) for c in B_COLS]
        signal = safe_float(row.get("delta_Bvec_uT"))
        if not math.isfinite(signal):
            signal = norm3(b_values)
        if (
            not math.isfinite(denom)
            or abs(denom) <= 1e-12
            or not all(math.isfinite(v) for v in b_values)
            or not math.isfinite(signal)
        ):
            continue
        usable.append(row)
        denominators.append(abs(denom))
        signals.append(signal)
        slopes.append(tuple(float(v / denom) for v in b_values))

    if slopes:
        arr = np.asarray(slopes, dtype=float)
        vector = tuple(float(v) for v in np.nanmedian(arr, axis=0))
        median_signal = float(np.nanmedian(np.asarray(signals, dtype=float)))
        median_denom = float(np.nanmedian(np.asarray(denominators, dtype=float)))
    else:
        vector = (math.nan, math.nan, math.nan)
        median_signal = math.nan
        median_denom = math.nan

    return PairColumnEstimate(
        stage_name=stage_name,
        n_total=len(rows),
        n_usable=len(usable),
        vector=vector,
        median_signal_uT=median_signal,
        median_denominator=median_denom,
        denominator_label=denominator_col,
        output_unit=output_unit,
    )


def latest_pair_column_estimates(data_root: Path) -> tuple[PairColumnEstimate | None, PairColumnEstimate | None]:
    iplus_session, iplus_summary_name = latest_session_with_any(
        data_root, SAME_D_DIFF_F_SUMMARY_NAMES
    )
    jplus_session = latest_session_with(data_root, "Jplus_pair_summary.csv")

    force_estimate = None
    displacement_estimate = None
    if iplus_session is not None and iplus_summary_name is not None:
        force_estimate = estimate_pair_column(
            read_csv(iplus_session / iplus_summary_name),
            stage_name=f"same-d/different-F ({iplus_session.name})",
            denominator_col="delta_F_N",
            required_flags=("same_d_ok", "force_split_ok", "b_signal_ok"),
            output_unit="uT/N",
        )
    if jplus_session is not None:
        displacement_estimate = estimate_pair_column(
            read_csv(jplus_session / "Jplus_pair_summary.csv"),
            stage_name=f"J+ ({jplus_session.name})",
            denominator_col="delta_d_mm",
            required_flags=("same_F_ok", "disp_split_ok", "b_signal_ok"),
            output_unit="uT/mm",
        )
    return force_estimate, displacement_estimate


def pair_column_angle_check(
    force_estimate: PairColumnEstimate | None,
    displacement_estimate: PairColumnEstimate | None,
    *,
    min_usable_force_pairs: int = 2,
    min_usable_displacement_pairs: int = 3,
    min_angle_deg: float = 30.0,
) -> CheckResult:
    if force_estimate is None:
        return CheckResult("I+/J+ pair-column evidence", "fail", ("No I+ pair summary found.",))
    if displacement_estimate is None:
        return CheckResult("I+/J+ pair-column evidence", "fail", ("No J+ pair summary found.",))
    if force_estimate.n_usable < min_usable_force_pairs:
        return CheckResult(
            "I+/J+ pair-column evidence",
            "fail",
            (
                f"{force_estimate.stage_name} has only {force_estimate.n_usable}/"
                f"{force_estimate.n_total} usable j_F pairs.",
            ),
        )
    if displacement_estimate.n_usable < min_usable_displacement_pairs:
        return CheckResult(
            "I+/J+ pair-column evidence",
            "fail",
            (
                f"{displacement_estimate.stage_name} has only "
                f"{displacement_estimate.n_usable}/{displacement_estimate.n_total} "
                "usable j_d pairs.",
            ),
        )

    metrics = jacobian_metrics(force_estimate.vector, displacement_estimate.vector)
    messages = [
        f"Pair-column angle={metrics.angle_deg:.1f} deg "
        f"(abs cosine={metrics.cosine_abs:.2f}) from I+ j_F and J+ j_d estimates.",
        (
            f"{force_estimate.stage_name}: {force_estimate.n_usable}/"
            f"{force_estimate.n_total} usable pairs, median |delta B3|="
            f"{force_estimate.median_signal_uT:.1f} uT."
        ),
        (
            f"{displacement_estimate.stage_name}: "
            f"{displacement_estimate.n_usable}/{displacement_estimate.n_total} "
            f"usable pairs, median |delta B3|="
            f"{displacement_estimate.median_signal_uT:.1f} uT."
        ),
        (
            f"Median j_F=({force_estimate.vector[0]:.1f}, "
            f"{force_estimate.vector[1]:.1f}, {force_estimate.vector[2]:.1f}) "
            f"{force_estimate.output_unit}; median j_d="
            f"({displacement_estimate.vector[0]:.1f}, "
            f"{displacement_estimate.vector[1]:.1f}, "
            f"{displacement_estimate.vector[2]:.1f}) "
            f"{displacement_estimate.output_unit}."
        ),
    ]

    if not math.isfinite(metrics.angle_deg):
        verdict = "fail"
        messages.append("One of the pair-column vectors is not finite.")
    elif metrics.angle_deg < min_angle_deg:
        verdict = "fail"
        messages.append("The I+/J+ pair-column directions are too close to collinear.")
    else:
        verdict = "pass"
        messages.append("The pair-column directions are well separated; this supports local identifiability.")
    return CheckResult("I+/J+ pair-column evidence", verdict, tuple(messages))


def _hold_b_cols(rows: Sequence[dict[str, str]]) -> tuple[str, str, str]:
    if rows and all(c in rows[0] for c in B_COLS):
        return B_COLS
    return AXIS_COLS


def stage_f_hysteresis_check(data_root: Path) -> CheckResult:
    session = latest_session_with(data_root, "F_load_unload_rep*.csv")
    if session is None:
        return CheckResult("Same-d different-F evidence", "fail", ("No Stage F load/unload data found.",))

    pairs: list[tuple[float, float, float]] = []
    for path in sorted(session.glob("F_load_unload_rep*.csv")):
        rows = read_csv(path)
        by_key: dict[tuple[str, float], dict[str, str]] = {}
        for row in rows:
            phase = str(row.get("phase", ""))
            d_target = round(safe_float(row.get("d_target_mm")), 3)
            trial = str(row.get("trial", ""))
            if math.isfinite(d_target):
                by_key[(f"{trial}:{phase}", d_target)] = row
        trials = sorted({key[0].split(":")[0] for key in by_key})
        for trial in trials:
            load = {
                d: row
                for (key, d), row in by_key.items()
                if key == f"{trial}:loading"
            }
            unload = {
                d: row
                for (key, d), row in by_key.items()
                if key == f"{trial}:unloading"
            }
            for d in sorted(set(load) & set(unload)):
                f_load = safe_float(load[d].get("F_mean_N"))
                f_unload = safe_float(unload[d].get("F_mean_N"))
                b_load = safe_float(load[d].get("Bmag_uT"))
                b_unload = safe_float(unload[d].get("Bmag_uT"))
                if all(math.isfinite(v) for v in (f_load, f_unload, b_load, b_unload)):
                    pairs.append((d, f_load - f_unload, b_load - b_unload))

    useful = [p for p in pairs if abs(p[1]) >= MIN_FORCE_EXCURSION_N]
    if len(useful) < 3:
        return CheckResult(
            "Same-d different-F evidence",
            "fail",
            (f"Only {len(useful)} matched loading/unloading points have |delta F| >= {MIN_FORCE_EXCURSION_N:.2f} N.",),
        )

    mean_delta_f = sum(abs(p[1]) for p in useful) / len(useful)
    mean_delta_b = sum(abs(p[2]) for p in useful) / len(useful)
    return CheckResult(
        "Same-d different-F evidence",
        "pass",
        (
            f"{len(useful)} matched loading/unloading points provide same-d different-F evidence.",
            f"Mean |delta F|={mean_delta_f:.3f} N; mean |delta |B||={mean_delta_b:.1f} uT.",
        ),
    )


def global_jacobian_check(rows: Sequence[dict[str, object]]) -> CheckResult:
    if len(rows) < 6:
        return CheckResult("Global exploratory Jacobian", "fail", ("Not enough plateau rows to fit J.",))
    fit = fit_local_jacobian(rows, state_cols=("F_N", "d_mm"))
    messages = [
        f"Fit used {fit.n_samples} E/F/H plateau rows with RMSE={fit.rmse_uT:.1f} uT.",
        f"j_F=({fit.j_force[0]:.1f}, {fit.j_force[1]:.1f}, {fit.j_force[2]:.1f}) uT/N.",
        f"j_d=({fit.j_displacement[0]:.1f}, {fit.j_displacement[1]:.1f}, {fit.j_displacement[2]:.1f}) uT/mm.",
        f"Jacobian angle={fit.metrics.angle_deg:.1f} deg, condition={fit.metrics.condition_number:.2f}.",
        f"State-space design condition={fit.state_condition_number:.2f}.",
    ]
    verdict = fit.metrics.verdict
    if fit.state_condition_number > 10:
        verdict = "fail"
        messages.append("F and d coverage is highly correlated; treat this fit as descriptive, not proof of decoupling.")
    elif fit.metrics.verdict != "good":
        verdict = "fail"
        messages.append("The fitted Jacobian columns are too collinear for robust inversion.")
    else:
        verdict = "pass"
        messages.append("The fitted columns are numerically invertible, pending local/blind validation.")
    return CheckResult("Global exploratory Jacobian", verdict, tuple(messages))


def local_jacobian_window_check(windows: Sequence[LocalWindowFit]) -> CheckResult:
    if not windows:
        return CheckResult(
            "Local Jacobian windows",
            "fail",
            ("No displacement-centered window had enough samples for a local 2-state fit.",),
        )

    usable = [
        w
        for w in windows
        if w.fit.metrics.verdict == "good" and w.fit.state_condition_number <= 10.0
    ]
    messages = [
        f"{len(usable)}/{len(windows)} displacement windows have usable local J metrics."
    ]
    for w in windows:
        messages.append(
            f"d~{w.center_d_mm:.2f} mm: n={w.fit.n_samples}, "
            f"angle={w.fit.metrics.angle_deg:.1f} deg, "
            f"cond={w.fit.metrics.condition_number:.2f}, "
            f"state-cond={w.fit.state_condition_number:.2f}, "
            f"RMSE={w.fit.rmse_uT:.1f} uT."
        )
    verdict = "pass" if len(usable) == len(windows) else "fail"
    return CheckResult("Local Jacobian windows", verdict, tuple(messages))


def build_report(data_root: Path, report_path: Path) -> list[CheckResult]:
    rows = normalize_stage_rows(data_root)
    force_max, disp_max = observed_force_displacement_max(rows)
    local_windows = local_jacobian_windows(rows)
    pair_columns = latest_pair_column_estimates(data_root)

    checks: list[CheckResult] = []
    checks.append(stage_c_check(data_root, disp_max))

    summary = latest_stage_d_summary(data_root)
    if summary is None:
        checks.append(CheckResult("Stage D/E safety consistency", "fail", ("No OK Stage D summary found.",)))
    else:
        checks.append(
            assess_safety_consistency(
                summary,
                observed_force_max=force_max,
                observed_displacement_max=disp_max,
            )
        )

    checks.append(stage_f_hysteresis_check(data_root))
    checks.append(pair_column_angle_check(*pair_columns))

    stage_i = hold_diagnostics(
        data_root,
        stage="I",
        pattern="I_hold_disp_*_rep*.csv",
        x_col="F_N",
    )
    stage_j = hold_diagnostics(
        data_root,
        stage="J",
        pattern="J_hold_force_*_rep*.csv",
        x_col="d_actual_mm",
        skip_initial_s=1.0,
    )

    checks.extend(_summarize_hold_checks("Stage I j_F evidence", stage_i))
    checks.extend(_summarize_hold_checks("Stage J j_q evidence", stage_j))
    checks.append(local_jacobian_window_check(local_windows))
    checks.append(global_jacobian_check(rows))

    report_text = render_report(
        checks,
        data_root=data_root,
        normalized_rows=rows,
        stage_i=stage_i,
        stage_j=stage_j,
        local_windows=local_windows,
        pair_columns=pair_columns,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")

    summary_csv = report_path.parent / "identifiability_summary.csv"
    write_summary_csv(summary_csv, checks)
    return checks


def _summarize_hold_checks(name: str, diagnostics: Sequence[HoldDiagnostic]) -> list[CheckResult]:
    if not diagnostics:
        return [CheckResult(name, "fail", ("No hold data found.",))]
    passed = [d for d in diagnostics if d.verdict == "pass"]
    verdict = "pass" if passed else "fail"
    messages = [
        f"{len(passed)}/{len(diagnostics)} hold files pass the excursion and linearity gate."
    ]
    for diag in diagnostics:
        messages.append(f"{diag.label}: {diag.note}")
    return [CheckResult(name, verdict, tuple(messages))]


def render_report(
    checks: Sequence[CheckResult],
    *,
    data_root: Path,
    normalized_rows: Sequence[dict[str, object]],
    stage_i: Sequence[HoldDiagnostic],
    stage_j: Sequence[HoldDiagnostic],
    local_windows: Sequence[LocalWindowFit],
    pair_columns: tuple[PairColumnEstimate | None, PairColumnEstimate | None],
) -> str:
    verdict_counts = {v: sum(1 for c in checks if c.verdict == v) for v in ("pass", "fail", "warning")}
    gate = "NOT READY"
    if verdict_counts["fail"] == 0:
        gate = "READY FOR LOCAL J AND BLIND TEST"

    lines = [
        "# Stage N - Normal Force-Displacement Identifiability Readiness",
        "",
        f"Generated from `{data_root}`.",
        "",
        f"**Gate verdict:** {gate}",
        "",
        "This report implements the v1 claim: test whether three-axis magnetic data contain separable information for normal force `F` and normal displacement/gap `d/q` in a fixed benchtop geometry.",
        "",
        "## Executive Checks",
        "",
        "| Check | Verdict | Main finding |",
        "|---|---:|---|",
    ]

    for check in checks:
        main = check.messages[0] if check.messages else ""
        lines.append(f"| {check.name} | {check.verdict.upper()} | {main} |")

    lines.extend(
        [
            "",
            "## Details",
            "",
        ]
    )
    for check in checks:
        lines.append(f"### {check.name}: {check.verdict.upper()}")
        for msg in check.messages:
            lines.append(f"- {msg}")
        lines.append("")

    lines.extend(
        [
            "## Pair-Column Evidence",
            "",
            "| Source | Usable pairs | Column estimate | Median signal | Median denominator |",
            "|---|---:|---|---:|---:|",
        ]
    )
    for estimate in pair_columns:
        if estimate is None:
            lines.append("| - | 0 | - | - | - |")
            continue
        vector_text = (
            f"({estimate.vector[0]:.1f}, {estimate.vector[1]:.1f}, "
            f"{estimate.vector[2]:.1f}) {estimate.output_unit}"
        )
        lines.append(
            f"| {estimate.stage_name} | {estimate.n_usable}/{estimate.n_total} | "
            f"{vector_text} | {estimate.median_signal_uT:.1f} uT | "
            f"{estimate.median_denominator:.4f} |"
        )
    lines.append("")

    lines.extend(
        [
            "## Hold Diagnostics",
            "",
            "| Stage | File | Samples | Excursion | Best axis | Best R2 | Verdict |",
            "|---|---|---:|---:|---|---:|---:|",
        ]
    )
    for stage_name, diagnostics, unit in (
        ("I", stage_i, "N"),
        ("J", stage_j, "mm"),
    ):
        for diag in diagnostics:
            lines.append(
                f"| {stage_name} | `{diag.label}` | {diag.n_samples} | "
                f"{diag.x_range:.4f} {unit} | {diag.best_axis or '-'} | "
                f"{diag.best_r2:.2f} | {diag.verdict.upper()} |"
            )

    lines.extend(
        [
            "",
            "## Local Jacobian Windows",
            "",
            "| Center d | Samples | j_F (uT/N) | j_d (uT/mm) | Angle | Cond | State Cond | RMSE | Verdict |",
            "|---:|---:|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    if local_windows:
        for window in local_windows:
            fit = window.fit
            verdict = (
                "PASS"
                if fit.metrics.verdict == "good" and fit.state_condition_number <= 10.0
                else "FAIL"
            )
            lines.append(
                f"| {window.center_d_mm:.2f} mm | {fit.n_samples} | "
                f"({fit.j_force[0]:.1f}, {fit.j_force[1]:.1f}, {fit.j_force[2]:.1f}) | "
                f"({fit.j_displacement[0]:.1f}, {fit.j_displacement[1]:.1f}, {fit.j_displacement[2]:.1f}) | "
                f"{fit.metrics.angle_deg:.1f} | {fit.metrics.condition_number:.2f} | "
                f"{fit.state_condition_number:.2f} | {fit.rmse_uT:.1f} | {verdict} |"
            )
    else:
        lines.append("| - | 0 | - | - | - | - | - | - | FAIL |")

    lines.extend(
        [
            "",
            "## Required Next Experiments",
            "",
            "1. Repeat small-q Stage C in the actual compression working zone; do not train the decoupling model on the far-field q=60-140 mm calibration.",
            "2. Repeat Stage D/E in one unchanged setup and keep all subsequent loading below the conservative force and displacement limits.",
            "3. Use the I+ and J+ pair protocols as the current primary `j_F`/`j_d` evidence; do not rely on passive Stage I/J holds alone.",
            "4. Fit a local Jacobian around the I+/J+ working region and check whether the pair-derived columns remain separated from the E/F/H exploratory fit.",
            "5. Only after these gates pass, run a separate blind test against single-variable baselines.",
            "",
            "## Normalized Data Contract",
            "",
            "The analysis normalizes existing E/F/H rows into: `stage, session, source_file, phase, control_mode, F_N, d_mm, q_mm, delta_Bx_uT, delta_By_uT, delta_Bz_uT`.",
            f"Current normalized plateau-like rows: {len(normalized_rows)}.",
            "",
        ]
    )
    return "\n".join(lines)


def write_summary_csv(path: Path, checks: Sequence[CheckResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["check", "verdict", "message"])
        for check in checks:
            writer.writerow([check.name, check.verdict, " ".join(check.messages)])


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("decouple_data"))
    parser.add_argument(
        "--report-path",
        type=Path,
        default=Path("reports") / "STAGE_N_identifiability_readiness.md",
    )
    args = parser.parse_args(argv)

    checks = build_report(args.data_root, args.report_path)
    print(f"Wrote {args.report_path}")
    print(f"Wrote {args.report_path.parent / 'identifiability_summary.csv'}")
    for check in checks:
        print(f"{check.verdict.upper():4} {check.name}: {check.messages[0] if check.messages else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
