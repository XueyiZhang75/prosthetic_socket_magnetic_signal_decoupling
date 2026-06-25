"""Create a Nature-style candidate figure for APMD Stage 6.3.

This is a preview figure, separate from the existing formal bar and parity plots.
It emphasizes path-pair mechanism, local identifiability, held-out trace behavior,
and error-distribution evidence.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, Ellipse
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PREDICTIONS_CSV = REPORTS_DIR / "apmd_stage6_local_identifiability_predictions.csv"
METRICS_CSV = REPORTS_DIR / "apmd_stage6_local_identifiability_model_metrics.csv"
QC_CSV = REPORTS_DIR / "apmd_stage6_heldout_qc_by_d.csv"
JF_CSV = REPORTS_DIR / "apmd_stage4_jF_from_same_d_pairs.csv"
JD_CSV = REPORTS_DIR / "apmd_stage4_jd_from_same_f_pairs.csv"
PAIR_TABLE_CSV = REPORTS_DIR / "apmd_stage4_identifiability_pair_table.csv"

OUT_BASE = REPORTS_DIR / "apmd_stage6_nature_candidate_overview"
OUT_PNG = OUT_BASE.with_suffix(".png")
OUT_PDF = OUT_BASE.with_suffix(".pdf")
OUT_SVG = OUT_BASE.with_suffix(".svg")

BLACK = "#222222"
TEXT_GRAY = "#555555"
MID_GRAY = "#8a8a8a"
LIGHT_GRAY = "#e7e7e7"
VERY_LIGHT_GRAY = "#f5f5f5"
BLUE = "#2c7fb8"
TEAL = "#1b9e77"
RED = "#c23b3b"
AMBER = "#d89c26"
LILAC = "#7b6aa9"

PATH_COLORS = {
    "direct_loading": BLACK,
    "return_unloading": BLUE,
    "preload_deep": MID_GRAY,
}

MODEL_ORDER = [
    ("plain_magnetic_ridge", "plain magnetic", BLACK),
    ("lim_style_branch_ridge", "branch label", MID_GRAY),
    ("apmd_path_memory_ridge", "path memory", BLUE),
    ("apmd_local_identifiability_ridge", "local-ID", RED),
]


def _set_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "font.size": 7,
            "axes.labelsize": 7.5,
            "axes.titlesize": 8,
            "xtick.labelsize": 6.5,
            "ytick.labelsize": 6.5,
            "legend.fontsize": 6.5,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.8,
            "xtick.major.width": 0.7,
            "ytick.major.width": 0.7,
            "xtick.major.size": 3,
            "ytick.major.size": 3,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "legend.frameon": False,
        }
    )


def _panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.09,
        1.06,
        label,
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
        fontweight="bold",
        color="black",
    )


def _clean_axis(ax: plt.Axes, grid: bool = True) -> None:
    if grid:
        ax.grid(color=LIGHT_GRAY, linewidth=0.65)
        ax.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)


def _infer_zone_sort_key(zone: str) -> tuple[int, int, str]:
    block_rank = 1
    if "Block_L" in zone:
        block_rank = 0
    elif "Block_H" in zone:
        block_rank = 2
    m = re.search(r"d(\d+)", zone)
    d_int = int(m.group(1)) if m else 9999
    return block_rank, d_int, zone


def _zone_label(zone: str) -> str:
    if "Block_L" in zone:
        prefix = "L"
    elif "Block_H" in zone:
        prefix = "H"
    elif "BlockM" in zone:
        prefix = "M"
    else:
        prefix = "Z"
    m = re.search(r"d(\d+)", zone)
    if not m:
        return prefix
    d_mm = int(m.group(1)) / 100.0
    f_match = re.search(r"F(\d+)", zone)
    if f_match:
        return f"{prefix} {d_mm:.2f}\nF{f_match.group(1)}"
    return f"{prefix} {d_mm:.2f}"


def _ecdf(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.sort(np.asarray(values, dtype=float))
    y = np.arange(1, len(x) + 1, dtype=float) / len(x)
    return x, y


def _cov_ellipse(
    ax: plt.Axes,
    x: np.ndarray,
    y: np.ndarray,
    color: str,
    label: str,
    n_std: float = 2.0,
) -> None:
    xy = np.column_stack([x, y])
    cov = np.cov(xy, rowvar=False)
    vals, vecs = np.linalg.eigh(cov)
    order = vals.argsort()[::-1]
    vals = vals[order]
    vecs = vecs[:, order]
    angle = np.degrees(np.arctan2(vecs[1, 0], vecs[0, 0]))
    width, height = 2 * n_std * np.sqrt(np.maximum(vals, 0))
    ell = Ellipse(
        xy=(float(np.mean(x)), float(np.mean(y))),
        width=float(width),
        height=float(height),
        angle=float(angle),
        facecolor=color,
        edgecolor=color,
        alpha=0.12,
        linewidth=1.2,
        label=label,
        zorder=2,
    )
    ax.add_patch(ell)


def _add_arrow(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    color: str = BLACK,
    lw: float = 1.0,
    mutation_scale: float = 10,
    alpha: float = 1.0,
) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=mutation_scale,
            linewidth=lw,
            color=color,
            alpha=alpha,
            shrinkA=0,
            shrinkB=0,
        )
    )


def _plot_core_principle(ax: plt.Axes) -> None:
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_title("APMD principle: use path memory to create local perturbation pairs", loc="left", fontweight="bold")

    # Left: why ordinary loading is ambiguous.
    ax.plot([0.055, 0.18], [0.28, 0.78], color=BLACK, lw=1.2)
    _add_arrow(ax, (0.055, 0.28), (0.18, 0.78), color=BLACK, lw=1.2, mutation_scale=11)
    ax.scatter([0.055, 0.18], [0.28, 0.78], s=22, color=BLACK, zorder=3)
    ax.text(0.09, 0.88, "ordinary loading", ha="center", fontsize=7, fontweight="bold")
    ax.text(0.09, 0.13, "F and d co-vary\nin one direction", ha="center", fontsize=6, color=TEXT_GRAY)

    _add_arrow(ax, (0.22, 0.53), (0.31, 0.53), color=TEXT_GRAY, lw=0.9, mutation_scale=10)

    # Middle: active minor loop generates the two useful paired states.
    loop_x = [0.36, 0.48, 0.43]
    loop_y = [0.36, 0.78, 0.36]
    ax.plot(loop_x, loop_y, color=BLACK, lw=1.2)
    ax.scatter(loop_x, loop_y, s=28, color=[BLACK, MID_GRAY, BLUE], zorder=3)
    ax.text(0.36, 0.25, "direct", ha="center", fontsize=5.8, color=BLACK)
    ax.text(0.48, 0.86, "preload", ha="center", fontsize=5.8, color=MID_GRAY)
    ax.text(0.43, 0.25, "return", ha="center", fontsize=5.8, color=BLUE)
    ax.text(0.42, 0.93, "active preload-return loop", ha="center", fontsize=7, fontweight="bold")
    ax.text(0.42, 0.10, "same-d and same-F\npair states", ha="center", fontsize=6, color=TEXT_GRAY)

    _add_arrow(ax, (0.54, 0.53), (0.62, 0.53), color=TEXT_GRAY, lw=0.9, mutation_scale=10)

    # Right: two local mechanical perturbations become two magnetic directions.
    ax.plot([0.67, 0.67], [0.25, 0.80], color=TEAL, lw=2.0)
    ax.scatter([0.67, 0.67], [0.25, 0.80], s=28, color=TEAL, edgecolor="white", linewidth=0.4, zorder=3)
    ax.plot([0.78, 0.93], [0.50, 0.50], color=AMBER, lw=2.0)
    ax.scatter([0.78, 0.93], [0.50, 0.50], s=28, color=AMBER, edgecolor="white", linewidth=0.4, zorder=3)
    ax.text(0.64, 0.88, "same d", ha="center", fontsize=6.5, color=TEAL, fontweight="bold")
    ax.text(0.64, 0.13, "different F -> jF", ha="center", fontsize=6, color=TEAL)
    ax.text(0.855, 0.61, "same F", ha="center", fontsize=6.5, color=AMBER, fontweight="bold")
    ax.text(0.855, 0.38, "different d -> jd", ha="center", fontsize=6, color=AMBER)
    ax.text(0.78, 0.93, "two local magnetic response directions", ha="center", fontsize=7, fontweight="bold")
    ax.text(0.78, 0.08, "features: pF = B dot jF,  pd = B dot jd", ha="center", fontsize=6, color=TEXT_GRAY)
    _panel_label(ax, "a")


def _plot_active_path_pairs(ax: plt.Axes, jF: pd.DataFrame, jd: pd.DataFrame) -> None:
    for _, row in jF.sort_values("state_d_mid_mm").iterrows():
        x = float(row["state_d_mid_mm"])
        y = float(row["state_F_mid_N"])
        half = float(row["median_abs_delta_F_N"]) / 2.0
        ax.plot([x, x], [y - half, y + half], color=TEAL, linewidth=1.5, alpha=0.9, zorder=2)
        ax.scatter([x, x], [y - half, y + half], s=17, color=TEAL, edgecolor="white", linewidth=0.3, zorder=3)

    for _, row in jd.sort_values("target_F_N").iterrows():
        x = float(row["state_d_mid_mm"])
        y = float(row["target_F_N"])
        half = float(row["median_abs_delta_d_mm"]) / 2.0
        ax.plot([x - half, x + half], [y, y], color=AMBER, linewidth=1.5, alpha=0.9, zorder=2)
        ax.scatter([x - half, x + half], [y, y], s=17, color=AMBER, edgecolor="white", linewidth=0.3, zorder=3)

    ax.text(
        0.03,
        0.95,
        "vertical split: same d, different F -> jF",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=6.2,
        color=TEAL,
    )
    ax.text(
        0.03,
        0.87,
        "horizontal split: same F, different d -> jd",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=6.2,
        color=AMBER,
    )
    ax.set_title("Mechanical perturbation pairs", loc="left", fontweight="bold")
    ax.set_xlabel("displacement d (mm)")
    ax.set_ylabel("force F (N)")
    ax.set_xlim(1.45, 3.78)
    ax.set_ylim(1.0, 8.9)
    _clean_axis(ax)
    _panel_label(ax, "b")


def _local_id_rows(predictions: pd.DataFrame) -> pd.DataFrame:
    return predictions[predictions["model"] == "apmd_local_identifiability_ridge"].copy()


def _path_label_for_legend(path_label: str) -> str:
    return {
        "direct_loading": "direct loading",
        "return_unloading": "return unloading",
        "preload_deep": "preload state",
    }.get(path_label, path_label)


def _scatter_by_path(ax: plt.Axes, data: pd.DataFrame, x: np.ndarray, y: np.ndarray) -> None:
    for path_label, color in PATH_COLORS.items():
        mask = data["path_label"].to_numpy() == path_label
        if not np.any(mask):
            continue
        ax.scatter(
            x[mask],
            y[mask],
            s=15,
            color=color,
            alpha=0.76,
            edgecolor="white",
            linewidth=0.25,
            label=_path_label_for_legend(path_label),
            zorder=3,
        )


def _add_fit_line(ax: plt.Axes, x: np.ndarray, y: np.ndarray, color: str = RED) -> tuple[float, float]:
    coeff = np.polyfit(x, y, 1)
    xx = np.linspace(float(np.min(x)), float(np.max(x)), 120)
    yy = coeff[0] * xx + coeff[1]
    ax.plot(xx, yy, color=color, linewidth=1.15, zorder=4)
    r = float(np.corrcoef(x, y)[0, 1])
    return r, r * r


def _plot_pd_coordinate(ax: plt.Axes, predictions: pd.DataFrame) -> None:
    data = _local_id_rows(predictions)
    x = data["local_p_d_uT"].to_numpy(float) / 1000.0
    y = data["d_mm"].to_numpy(float)
    _scatter_by_path(ax, data, x, y)
    r, r2 = _add_fit_line(ax, x, y)
    ax.text(
        0.04,
        0.96,
        f"held-out states\nr = {r:.2f}; R2 = {r2:.2f}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=6.2,
        color=TEXT_GRAY,
    )
    ax.set_title("Local pd coordinate tracks d", loc="left", fontweight="bold")
    ax.set_xlabel("pd = Delta B dot unit jd (k uT)")
    ax.set_ylabel("measured d (mm)")
    ax.legend(loc="lower right", fontsize=5.5, handlelength=1.2)
    _clean_axis(ax)
    _panel_label(ax, "a")


def _plot_force_residual_coordinate(ax: plt.Axes, predictions: pd.DataFrame) -> None:
    data = _local_id_rows(predictions)
    d = data["d_mm"].to_numpy(float)
    force = data["F_N"].to_numpy(float)
    coeff = np.polyfit(d, force, 1)
    force_after_d = force - (coeff[0] * d + coeff[1])
    x = data["local_residual_uT"].to_numpy(float) / 1000.0
    _scatter_by_path(ax, data, x, force_after_d)
    r, r2 = _add_fit_line(ax, x, force_after_d)
    d_only_pred = coeff[0] * d + coeff[1]
    d_only_r2 = 1.0 - float(np.sum((force - d_only_pred) ** 2) / np.sum((force - np.mean(force)) ** 2))
    ax.axhline(0, color=BLACK, linewidth=0.7, alpha=0.55)
    ax.text(
        0.04,
        0.96,
        f"after removing F-d trend\nr = {r:.2f}; R2 = {r2:.2f}\nd-only R2 = {d_only_r2:.2f}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=6.2,
        color=TEXT_GRAY,
    )
    ax.set_title("Force information beyond d", loc="left", fontweight="bold")
    ax.set_xlabel("local residual from jF/jd plane (k uT)")
    ax.set_ylabel("F residual after d-only fit (N)")
    _clean_axis(ax)
    _panel_label(ax, "b")


def _pick_primary_pair(pair_table: pd.DataFrame) -> pd.Series:
    candidates = pair_table[pair_table["verdict"] == "candidate"]
    if not candidates.empty:
        return candidates.sort_values("rank").iloc[0]
    return pair_table.sort_values("rank").iloc[0]


def _plot_identifiability_landscape(ax: plt.Axes, pair_table: pd.DataFrame) -> None:
    data = pair_table.copy()
    x = data["same_d_target_d_mm"].to_numpy(float)
    y = data["same_F_target_F_N"].to_numpy(float)
    angle = data["angle_deg"].to_numpy(float)

    sc = ax.scatter(
        x,
        y,
        c=angle,
        s=48,
        cmap="viridis",
        alpha=0.88,
        edgecolor="white",
        linewidth=0.35,
        zorder=3,
    )

    primary = _pick_primary_pair(data)
    ax.scatter(
        [float(primary["same_d_target_d_mm"])],
        [float(primary["same_F_target_F_N"])],
        s=155,
        facecolor="none",
        edgecolor=RED,
        linewidth=1.35,
        zorder=5,
    )
    ax.text(
        float(primary["same_d_target_d_mm"]),
        float(primary["same_F_target_F_N"]) + 0.18,
        "selected",
        color=RED,
        fontsize=5.6,
        ha="center",
        va="bottom",
    )

    top = data.nsmallest(6, "rank")
    for _, row in top.iterrows():
        ax.text(
            float(row["same_d_target_d_mm"]),
            float(row["same_F_target_F_N"]),
            str(int(row["rank"])),
            ha="center",
            va="center",
            fontsize=5.2,
            color="white" if float(row["angle_deg"]) > np.median(angle) else BLACK,
            zorder=6,
        )

    ax.set_title("Measured identifiability landscape", loc="left", fontweight="bold")
    ax.set_xlabel("same-d pair target d (mm)")
    ax.set_ylabel("same-F pair target F (N)")
    ax.set_xlim(float(x.min()) - 0.12, float(x.max()) + 0.18)
    ax.set_ylim(float(y.min()) - 0.28, float(y.max()) + 0.38)
    _clean_axis(ax)
    cbar = plt.colorbar(sc, ax=ax, fraction=0.047, pad=0.02)
    cbar.set_label("angle (deg)")
    cbar.ax.tick_params(labelsize=5.3, length=2)
    _panel_label(ax, "a")


def _unit(v: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(v))
    if norm == 0:
        return v
    return v / norm


def _plot_response_component_signatures(ax: plt.Axes, pair_table: pd.DataFrame) -> None:
    primary = _pick_primary_pair(pair_table)
    jF_vec = np.array(
        [
            float(primary["jF_x_uT_per_N"]),
            float(primary["jF_y_uT_per_N"]),
            float(primary["jF_z_uT_per_N"]),
        ]
    )
    jd_vec = np.array(
        [
            float(primary["jd_x_uT_per_mm"]),
            float(primary["jd_y_uT_per_mm"]),
            float(primary["jd_z_uT_per_mm"]),
        ]
    )
    jF_u = _unit(jF_vec)
    jd_u = _unit(jd_vec)
    x = np.arange(3)
    width = 0.36
    ax.bar(x - width / 2, jF_u, width, color=TEAL, alpha=0.92, label="jF per N")
    ax.bar(x + width / 2, jd_u, width, color=AMBER, alpha=0.92, label="jd per mm")
    ax.axhline(0, color=BLACK, linewidth=0.65, alpha=0.55)
    ax.set_xticks(x)
    ax.set_xticklabels(["Bx", "By", "Bz"])
    ax.set_ylim(-0.08, 1.08)
    ax.set_ylabel("unit-vector component")
    ax.set_title("jF/jd directions used for projection", loc="left", fontweight="bold")
    ax.text(
        0.04,
        0.94,
        (
            f"pF = Delta B dot unit jF\n"
            f"pd = Delta B dot unit jd\n"
            f"angle {float(primary['angle_deg']):.1f} deg"
        ),
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=5.8,
        color=TEXT_GRAY,
    )
    ax.legend(loc="upper right", handlelength=1.2, fontsize=5.9)
    _clean_axis(ax)
    _panel_label(ax, "c")


def _plot_magnetic_basis(ax: plt.Axes, pair_table: pd.DataFrame) -> None:
    primary = pair_table.sort_values(["verdict", "rank"]).iloc[0]
    candidates = pair_table[pair_table["verdict"] == "candidate"]
    if not candidates.empty:
        primary = candidates.sort_values("rank").iloc[0]

    jF_vec = np.array(
        [
            float(primary["jF_x_uT_per_N"]),
            float(primary["jF_y_uT_per_N"]),
            float(primary["jF_z_uT_per_N"]),
        ]
    )
    jd_vec = np.array(
        [
            float(primary["jd_x_uT_per_mm"]),
            float(primary["jd_y_uT_per_mm"]),
            float(primary["jd_z_uT_per_mm"]),
        ]
    )
    jF_u = _unit(jF_vec)
    jd_u = _unit(jd_vec)

    # Use the By-Bz plane because it carries the dominant separation in the current data.
    scale = 1.0
    origin = np.array([0.0, 0.0])
    f_end = np.array([jF_u[1], jF_u[2]]) * scale
    d_end = np.array([jd_u[1], jd_u[2]]) * scale

    ax.axhline(0, color=LIGHT_GRAY, lw=0.8)
    ax.axvline(0, color=LIGHT_GRAY, lw=0.8)
    _add_arrow(ax, tuple(origin), tuple(f_end), color=TEAL, lw=1.8, mutation_scale=13)
    _add_arrow(ax, tuple(origin), tuple(d_end), color=AMBER, lw=1.8, mutation_scale=13)
    ax.scatter([0], [0], s=18, color=BLACK, zorder=3)

    angle = float(primary["angle_deg"])
    theta_f = np.arctan2(f_end[1], f_end[0])
    theta_d = np.arctan2(d_end[1], d_end[0])
    arc_angles = np.linspace(theta_f, theta_d, 80)
    ax.plot(0.33 * np.cos(arc_angles), 0.33 * np.sin(arc_angles), color=RED, lw=1.0)
    mid = (theta_f + theta_d) / 2.0
    ax.text(0.43 * np.cos(mid), 0.43 * np.sin(mid), f"{angle:.1f} deg", color=RED, fontsize=6.4)

    ax.text(f_end[0] - 0.03, f_end[1] + 0.06, "jF", color=TEAL, fontsize=7, ha="right", va="bottom", fontweight="bold")
    ax.text(d_end[0] + 0.04, d_end[1], "jd", color=AMBER, fontsize=7, ha="left", va="center", fontweight="bold")
    ax.text(
        0.04,
        0.94,
        "Delta B = jF Delta F + jd Delta d",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=6.3,
        color=TEXT_GRAY,
    )
    ax.set_title("Magnetic response basis", loc="left", fontweight="bold")
    ax.set_xlabel("normalized By response")
    ax.set_ylabel("normalized Bz response")
    ax.set_xlim(-0.08, 1.08)
    ax.set_ylim(-0.08, 1.08)
    ax.set_aspect("equal", adjustable="box")
    _clean_axis(ax)
    _panel_label(ax, "c")


def _plot_path_pair_qc(ax: plt.Axes, qc: pd.DataFrame) -> None:
    ax.text(
        0.04,
        0.94,
        "near-same d\nforce split",
        transform=ax.transAxes,
        ha="left",
        va="top",
        color=TEXT_GRAY,
        fontsize=7,
    )
    ax.set_title("Path-pair QC", loc="left", fontweight="bold")
    ax.set_xlabel("target d (mm)")
    ax.set_ylabel("F at matched d (N)")
    _clean_axis(ax)
    _panel_label(ax, "a")


def _branch_spans(data: pd.DataFrame) -> list[tuple[float, float, str]]:
    ordered = data.sort_values("state_index")
    spans: list[tuple[float, float, str]] = []
    current = None
    start = None
    last = None
    for _, row in ordered.iterrows():
        label = str(row["path_label"])
        idx = float(row["state_index"])
        if current is None:
            current = label
            start = idx - 0.5
        elif label != current:
            spans.append((float(start), float(last) + 0.5, str(current)))
            current = label
            start = idx - 0.5
        last = idx
    if current is not None and start is not None and last is not None:
        spans.append((float(start), float(last) + 0.5, str(current)))
    return spans


def _plot_trace(
    ax_f: plt.Axes,
    ax_d: plt.Axes,
    predictions: pd.DataFrame,
) -> None:
    local = predictions[predictions["model"] == "apmd_local_identifiability_ridge"].copy()
    lim = predictions[predictions["model"] == "lim_style_branch_ridge"].copy()
    first = (
        local.groupby(["session_id", "trial", "pair_id"], as_index=False)
        .size()
        .sort_values(["size", "session_id", "trial", "pair_id"], ascending=[False, True, True, True])
        .iloc[0]
    )
    keys = {
        "session_id": first["session_id"],
        "trial": first["trial"],
        "pair_id": first["pair_id"],
    }
    mask_local = (
        (local["session_id"] == keys["session_id"])
        & (local["trial"] == keys["trial"])
        & (local["pair_id"] == keys["pair_id"])
    )
    mask_lim = (
        (lim["session_id"] == keys["session_id"])
        & (lim["trial"] == keys["trial"])
        & (lim["pair_id"] == keys["pair_id"])
    )
    data_local = local[mask_local].sort_values("state_index")
    data_lim = lim[mask_lim].sort_values("state_index")
    x = data_local["state_index"].to_numpy(dtype=float)

    span_colors = {
        "direct_loading": "#f0f0f0",
        "preload_deep": "#e6e6e6",
        "return_unloading": "#eef5fb",
    }
    for ax in [ax_f, ax_d]:
        for start, stop, label in _branch_spans(data_local):
            ax.axvspan(start, stop, color=span_colors.get(label, "#f7f7f7"), zorder=0)

    ax_f.plot(x, data_local["F_N"], color=BLACK, linewidth=1.35, label="measured")
    ax_f.plot(x, data_lim["F_pred_N"], color=MID_GRAY, linewidth=1.0, linestyle="--", label="branch label")
    ax_f.plot(x, data_local["F_pred_N"], color=RED, linewidth=1.3, label="local-ID")
    ax_f.scatter(x, data_local["F_N"], s=12, color=BLACK, zorder=3)
    ax_f.set_ylabel("F (N)")
    ax_f.set_title("Representative held-out loop", loc="left", fontweight="bold")
    ax_f.legend(loc="upper left", ncol=3, handlelength=1.8)
    ax_f.tick_params(labelbottom=False)

    ax_d.plot(x, data_local["d_mm"], color=BLACK, linewidth=1.35, label="measured")
    ax_d.plot(x, data_local["d_pred_mm"], color=RED, linewidth=1.3, label="local-ID")
    ax_d.scatter(x, data_local["d_mm"], s=12, color=BLACK, zorder=3)
    ax_d.set_ylabel("d (mm)")
    ax_d.set_xlabel("state index along loop")
    ax_d.set_xticks(x)

    for ax in [ax_f, ax_d]:
        _clean_axis(ax)
        ax.set_xlim(float(x.min()) - 0.5, float(x.max()) + 0.5)
    _panel_label(ax_f, "b")


def _plot_identifiability_map(ax: plt.Axes, predictions: pd.DataFrame) -> None:
    local = predictions[predictions["model"] == "apmd_local_identifiability_ridge"].copy()
    grouped = (
        local.groupby("local_zone_id")
        .agg(
            angle=("local_angle_deg", "mean"),
            residual=("local_residual_uT", "median"),
            f_mae=("F_error_N", lambda s: float(np.mean(np.abs(s)))),
            d_mae=("d_error_mm", lambda s: float(np.mean(np.abs(s)))),
        )
        .reset_index()
    )
    grouped = grouped.sort_values("local_zone_id", key=lambda s: s.map(_infer_zone_sort_key))
    values = np.vstack(
        [
            grouped["angle"].to_numpy(float),
            grouped["residual"].to_numpy(float) / 1000.0,
            grouped["f_mae"].to_numpy(float),
            grouped["d_mae"].to_numpy(float),
        ]
    )
    row_labels = ["angle\n(deg)", "residual\n(k uT)", "F MAE\n(N)", "d MAE\n(mm)"]
    norm = np.zeros_like(values)
    for i, row in enumerate(values):
        span = np.ptp(row)
        norm[i] = 0.5 if span == 0 else (row - row.min()) / span

    im = ax.imshow(norm, aspect="auto", cmap="viridis", vmin=0, vmax=1)
    ax.set_yticks(np.arange(len(row_labels)))
    ax.set_yticklabels(row_labels)
    ax.set_xticks(np.arange(len(grouped)))
    ax.set_xticklabels(
        [_zone_label(z) for z in grouped["local_zone_id"]],
        rotation=45,
        ha="right",
        rotation_mode="anchor",
    )
    ax.tick_params(length=0)
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            if i == 0:
                text = f"{values[i, j]:.0f}"
            elif i == 1:
                text = f"{values[i, j]:.1f}"
            elif i == 2:
                text = f"{values[i, j]:.2f}"
            else:
                text = f"{values[i, j]:.3f}"
            ax.text(
                j,
                i,
                text,
                ha="center",
                va="center",
                fontsize=5.4,
                color="white" if norm[i, j] > 0.58 else "black",
            )
    ax.set_title("Local identifiability map", loc="left", fontweight="bold")
    cbar = plt.colorbar(im, ax=ax, fraction=0.026, pad=0.012)
    cbar.set_label("within-row normalized")
    cbar.ax.tick_params(labelsize=5.5, length=2)
    for spine in ax.spines.values():
        spine.set_visible(False)
    _panel_label(ax, "c")


def _plot_paired_error(ax: plt.Axes, predictions: pd.DataFrame) -> None:
    keys = ["session_id", "trial", "pair_id", "cycle_index", "state_index"]
    base = predictions[predictions["model"] == "lim_style_branch_ridge"].copy()
    local = predictions[predictions["model"] == "apmd_local_identifiability_ridge"].copy()
    merged = base[keys + ["path_label", "F_error_N"]].merge(
        local[keys + ["F_error_N"]],
        on=keys,
        suffixes=("_branch", "_local"),
    )
    x = np.abs(merged["F_error_N_branch"].to_numpy(float))
    y = np.abs(merged["F_error_N_local"].to_numpy(float))
    colors = merged["path_label"].map(PATH_COLORS).fillna(MID_GRAY)
    ax.scatter(x, y, s=18, c=colors, alpha=0.82, edgecolor="white", linewidth=0.25)
    lim = max(float(np.max(x)), float(np.max(y))) * 1.05
    ax.plot([0, lim], [0, lim], color=MID_GRAY, linewidth=0.9, linestyle=":")
    ax.set_xlim(0, lim)
    ax.set_ylim(0, lim)
    ax.set_aspect("equal", adjustable="box")
    improved = float(np.mean(y < x) * 100.0)
    median_drop = float((1.0 - np.median(y) / max(np.median(x), 1e-12)) * 100.0)
    ax.text(
        0.04,
        0.96,
        f"{improved:.0f}% states below 1:1\nmedian |F error| drop {median_drop:.0f}%",
        transform=ax.transAxes,
        ha="left",
        va="top",
        color=TEXT_GRAY,
        fontsize=6.7,
    )
    ax.set_title("Paired force-error reduction", loc="left", fontweight="bold")
    ax.set_xlabel("branch-label |F error| (N)")
    ax.set_ylabel("local-ID |F error| (N)")
    _clean_axis(ax)
    _panel_label(ax, "d")


def _plot_ecdf(ax: plt.Axes, predictions: pd.DataFrame) -> None:
    for model, label, color in MODEL_ORDER:
        data = predictions[predictions["model"] == model]
        x, y = _ecdf(np.abs(data["F_error_N"].to_numpy(float)))
        ax.plot(x, y, color=color, linewidth=1.35, label=label)
    ax.axvline(0.50, color=RED, linewidth=0.9, linestyle=":", alpha=0.8)
    ax.axvline(0.75, color=MID_GRAY, linewidth=0.9, linestyle=":", alpha=0.8)
    ax.text(0.50, 0.05, "0.50 N", rotation=90, ha="right", va="bottom", color=RED, fontsize=6)
    ax.text(0.75, 0.05, "0.75 N", rotation=90, ha="right", va="bottom", color=MID_GRAY, fontsize=6)
    ax.set_xlim(0, 3.0)
    ax.set_ylim(0, 1.01)
    ax.set_title("Held-out force-error distribution", loc="left", fontweight="bold")
    ax.set_xlabel("|F error| (N)")
    ax.set_ylabel("fraction of states")
    ax.legend(loc="lower right", ncol=1, fontsize=5.8, handlelength=1.55, borderaxespad=0.3)
    _clean_axis(ax)
    _panel_label(ax, "e")


def _plot_error_phase(ax: plt.Axes, predictions: pd.DataFrame) -> None:
    phase_models = [
        ("lim_style_branch_ridge", "branch label", MID_GRAY),
        ("apmd_local_identifiability_ridge", "local-ID", RED),
    ]
    for model, label, color in phase_models:
        data = predictions[predictions["model"] == model]
        x = data["F_error_N"].to_numpy(float)
        y = data["d_error_mm"].to_numpy(float)
        ax.scatter(x, y, s=11, color=color, alpha=0.32, edgecolor="none", zorder=3)
        _cov_ellipse(ax, x, y, color, label)
    ax.axvline(0, color=BLACK, linewidth=0.7, alpha=0.55)
    ax.axhline(0, color=BLACK, linewidth=0.7, alpha=0.55)
    ax.set_xlim(-3.2, 3.2)
    ax.set_ylim(-0.20, 0.20)
    ax.set_title("Two-output residual portrait", loc="left", fontweight="bold")
    ax.set_xlabel("F residual (N)")
    ax.set_ylabel("d residual (mm)")
    ax.legend(loc="upper left")
    _clean_axis(ax)
    _panel_label(ax, "f")


def main() -> None:
    _set_style()
    predictions = pd.read_csv(PREDICTIONS_CSV)
    metrics = pd.read_csv(METRICS_CSV)
    pair_table = pd.read_csv(PAIR_TABLE_CSV)

    if predictions.empty or metrics.empty or pair_table.empty:
        raise RuntimeError("Missing Stage 6.3 inputs.")

    fig = plt.figure(figsize=(7.25, 5.72), dpi=300)
    gs = GridSpec(
        2,
        3,
        figure=fig,
        width_ratios=[1.0, 1.05, 1.0],
        left=0.07,
        right=0.985,
        top=0.865,
        bottom=0.095,
        wspace=0.58,
        hspace=0.58,
    )

    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[0, 2])
    ax_d = fig.add_subplot(gs[1, 0])
    ax_e = fig.add_subplot(gs[1, 1])
    ax_f = fig.add_subplot(gs[1, 2])

    _plot_pd_coordinate(ax_a, predictions)
    _plot_force_residual_coordinate(ax_b, predictions)
    _plot_response_component_signatures(ax_c, pair_table)
    _plot_paired_error(ax_d, predictions)
    _plot_ecdf(ax_e, predictions)
    _plot_error_phase(ax_f, predictions)

    train_n = int(metrics.iloc[0]["train_n_states"])
    heldout_n = int(metrics.iloc[0]["heldout_n_states"])
    fig.suptitle(
        "APMD local-identifiability: path-pair data and held-out decoding",
        x=0.07,
        y=0.965,
        ha="left",
        fontsize=10.5,
        fontweight="bold",
    )
    fig.text(
        0.07,
        0.932,
        (
            "Stage 4 path-pair measurements define jF/jd directions; Stage 6.3 projects held-out states into "
            "pd, pF and residual coordinates and tests two-output decoding. "
            f"Model evidence: train = {train_n} states; held-out = {heldout_n} states."
        ),
        ha="left",
        va="top",
        fontsize=6.8,
        color=TEXT_GRAY,
    )

    fig.savefig(OUT_PNG, bbox_inches="tight")
    fig.savefig(OUT_PDF, bbox_inches="tight")
    fig.savefig(OUT_SVG, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved {OUT_PNG.relative_to(ROOT)}")
    print(f"Saved {OUT_PDF.relative_to(ROOT)}")
    print(f"Saved {OUT_SVG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
