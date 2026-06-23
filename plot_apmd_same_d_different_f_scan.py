"""Plot formal APMD Experiment 3.1 same-d/different-F work-zone scan.

Default input:
  3.1A formal session: decouple_data/session_20260610_091145
  3.1B formal session: decouple_data/session_20260610_104017

The output is a set of four work-zone screening figures, not a single crowded
multi-panel diagnostic. Each figure answers one question: force-state split,
magnetic split, 3-axis magnetic signature, or work-zone selection.
"""

from __future__ import annotations

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib as mpl
import matplotlib.pyplot as plt

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


HERE = Path(__file__).parent
OUTPUT_ROOT = HERE / "decouple_data"

DEFAULT_INPUTS = [
    (
        "3.1A",
        OUTPUT_ROOT / "session_20260610_091145",
        "same_d_different_f_scan_A_pair_summary.csv",
    ),
    (
        "3.1B",
        OUTPUT_ROOT / "session_20260610_104017",
        "same_d_different_f_scan_B_pair_summary.csv",
    ),
]

FIGURE_FILENAMES = {
    "complete": "same_d_different_f_scan_complete_figure.png",
    "force_split": "same_d_different_f_scan_force_split.png",
    "bvec_split": "same_d_different_f_scan_bvec_split.png",
    "axis_signature": "same_d_different_f_scan_axis_signature.png",
    "workzone_decision": "same_d_different_f_scan_workzone_decision.png",
    "d_match_check": "same_d_different_f_scan_d_match_check.png",
    "efficiency": "same_d_different_f_scan_efficiency.png",
}
PNG_DPI = 300

D_MATCH_TOL_MM = 0.020
MIN_FORCE_SPLIT_N = 0.20
DYNAMIC_B_SIGNAL_UT = 50.0

REP_COLORS = {
    1: "#000000",
    2: "#D62728",
    3: "#1F77B4",
}

PALETTE = {
    "black": "#222222",
    "gray_dark": "#555555",
    "gray": "#808080",
    "gray_light": "#D9D9D9",
    "grid": "#E9E9E9",
    "red": "#B64342",
    "blue": "#1F77B4",
    "paper": "#FFFFFF",
    "highlight": "#F3EFE4",
}


def apply_style():
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "DejaVu Sans", "Liberation Sans"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 7,
            "axes.titlesize": 8,
            "axes.labelsize": 7,
            "xtick.labelsize": 6,
            "ytick.labelsize": 6,
            "legend.fontsize": 6,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
            "lines.linewidth": 1.15,
            "lines.markersize": 4.0,
            "xtick.major.width": 0.7,
            "ytick.major.width": 0.7,
            "xtick.major.size": 2.6,
            "ytick.major.size": 2.6,
        }
    )


def safe_float(value, default=float("nan")):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def read_summary(label: str, session: Path, filename: str):
    path = session / filename
    if not path.exists():
        raise FileNotFoundError(path)

    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    "block": label,
                    "session_id": r.get("session_id", session.name),
                    "trial": int(r["trial"]),
                    "target_label": r["target_label"],
                    "d_target_mm": safe_float(r["d_target_mm"]),
                    "d_preload_mm": safe_float(r["d_preload_mm"]),
                    "d_direct_mm": safe_float(r["d_direct_mm"]),
                    "d_return_mm": safe_float(r["d_return_mm"]),
                    "d_diff_mm": safe_float(r["d_diff_mm"]),
                    "F_direct_N": safe_float(r["F_direct_N"]),
                    "F_return_N": safe_float(r["F_return_N"]),
                    "delta_F_N": safe_float(r["delta_F_N"]),
                    "Bmag_direct_uT": safe_float(r["Bmag_direct_uT"]),
                    "Bmag_return_uT": safe_float(r["Bmag_return_uT"]),
                    "delta_Bmag_uT": safe_float(r["delta_Bmag_uT"]),
                    "delta_Bx_uT": safe_float(r["delta_Bx_uT"]),
                    "delta_By_uT": safe_float(r["delta_By_uT"]),
                    "delta_Bz_uT": safe_float(r["delta_Bz_uT"]),
                    "delta_Bvec_uT": safe_float(r["delta_Bvec_uT"]),
                    "same_d_ok": r["same_d_ok"] == "1",
                    "force_split_ok": r["force_split_ok"] == "1",
                    "b_signal_ok": r["b_signal_ok"] == "1",
                    "verdict": r["verdict"],
                }
            )
    return rows


def load_formal_rows(inputs=DEFAULT_INPUTS):
    rows = []
    for label, session, filename in inputs:
        rows.extend(read_summary(label, session, filename))
    rows.sort(key=lambda r: (r["d_target_mm"], r["trial"]))
    return rows


def grouped(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row["d_target_mm"]].append(row)
    return {k: sorted(v, key=lambda r: r["trial"]) for k, v in sorted(groups.items())}


def median(values):
    clean = [v for v in values if math.isfinite(v)]
    if not clean:
        return float("nan")
    return float(np.median(clean))


def span(values):
    clean = [v for v in values if math.isfinite(v)]
    if not clean:
        return (float("nan"), float("nan"))
    return (float(np.min(clean)), float(np.max(clean)))


def panel_label(ax, label):
    ax.text(
        -0.12,
        1.06,
        label,
        transform=ax.transAxes,
        fontsize=10,
        fontweight="bold",
        ha="left",
        va="bottom",
    )


def add_workzone_band(ax):
    ax.axvspan(3.18, 3.42, color=PALETTE["highlight"], zorder=0)


def target_values(rows_by_d):
    return np.array(list(rows_by_d.keys()), dtype=float)


def metric_by_target(rows_by_d, key_fn):
    ds = target_values(rows_by_d)
    med_vals = []
    low_vals = []
    high_vals = []
    raw_vals = []
    for d in ds:
        vals = [key_fn(r) for r in rows_by_d[d]]
        med_vals.append(median(vals))
        lo, hi = span(vals)
        low_vals.append(lo)
        high_vals.append(hi)
        raw_vals.append(vals)
    return (
        ds,
        np.array(med_vals, dtype=float),
        np.array(low_vals, dtype=float),
        np.array(high_vals, dtype=float),
        raw_vals,
    )


def prepare_single_figure(figsize=(5.2, 3.25)):
    apply_style()
    fig, ax = plt.subplots(figsize=figsize)
    return fig, ax


def decorate_single_figure(fig, title):
    fig.suptitle(
        title,
        x=0.02,
        y=0.99,
        ha="left",
        va="top",
        fontsize=8.6,
        fontweight="bold",
    )
    fig.text(
        0.02,
        0.94,
        "Formal data: session_20260610_091145 (3.1A) + session_20260610_104017 (3.1B)",
        ha="left",
        va="top",
        fontsize=6.2,
        color=PALETTE["gray_dark"],
    )


def plot_force_split_figure(rows_by_d):
    fig, ax = prepare_single_figure(figsize=(5.65, 3.35))
    decorate_single_figure(
        fig,
        "Experiment 3.1-1: near-matched displacement creates a force split",
    )

    ds = target_values(rows_by_d)
    direct = metric_by_target(rows_by_d, lambda r: r["F_direct_N"])
    returned = metric_by_target(rows_by_d, lambda r: r["F_return_N"])
    _, d_med, _d_low, _d_high, d_raw = direct
    _, r_med, _r_low, _r_high, r_raw = returned

    add_workzone_band(ax)
    ax.text(
        3.30,
        max(np.nanmax(d_med), np.nanmax(r_med)) * 0.93,
        "candidate\nwork zone",
        ha="center",
        va="top",
        fontsize=5.5,
        color=PALETTE["gray_dark"],
    )

    ax.plot(
        ds,
        d_med,
        color=PALETTE["black"],
        lw=1.2,
        marker="o",
        markersize=4.2,
        markerfacecolor=PALETTE["black"],
        markeredgecolor=PALETTE["black"],
        label="direct loading",
        zorder=4,
    )
    ax.plot(
        ds,
        r_med,
        color=PALETTE["black"],
        lw=1.05,
        ls="--",
        marker="o",
        markersize=4.2,
        markerfacecolor="white",
        markeredgecolor=PALETTE["black"],
        label="return unloading",
        zorder=4,
    )

    for i, d in enumerate(ds):
        for j, value in enumerate(d_raw[i]):
            ax.scatter(
                d + (j - 1) * 0.012,
                value,
                s=10,
                facecolor=REP_COLORS.get(j + 1, PALETTE["gray"]),
                edgecolor="none",
                alpha=0.90,
                zorder=5,
            )
        for j, value in enumerate(r_raw[i]):
            ax.scatter(
                d + (j - 1) * 0.012,
                value,
                s=14,
                facecolor="white",
                edgecolor=REP_COLORS.get(j + 1, PALETTE["gray"]),
                linewidth=0.65,
                alpha=0.95,
                zorder=5,
            )

    panel_label(ax, "a")
    ax.set_title("Matched-d force split across work zones", loc="left", pad=3)
    ax.set_xlabel("target d (mm)")
    ax.set_ylabel("F at target d (N)")
    ax.set_xticks(ds)
    ax.grid(axis="y", color=PALETTE["grid"], linewidth=0.6)
    ax.legend(loc="upper left")
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    return fig


def plot_force_state_split(ax, rows_by_d, panel="a"):
    ds = target_values(rows_by_d)
    direct = metric_by_target(rows_by_d, lambda r: r["F_direct_N"])
    returned = metric_by_target(rows_by_d, lambda r: r["F_return_N"])
    _, d_med, _d_low, _d_high, d_raw = direct
    _, r_med, _r_low, _r_high, r_raw = returned

    add_workzone_band(ax)
    ax.text(
        3.30,
        max(np.nanmax(d_med), np.nanmax(r_med)) * 0.93,
        "candidate\nwork zone",
        ha="center",
        va="top",
        fontsize=5.6,
        color=PALETTE["gray_dark"],
    )

    ax.plot(
        ds,
        d_med,
        color=PALETTE["black"],
        lw=1.25,
        marker="o",
        markersize=4.2,
        markerfacecolor=PALETTE["black"],
        markeredgecolor=PALETTE["black"],
        label="direct loading",
        zorder=4,
    )
    ax.plot(
        ds,
        r_med,
        color=PALETTE["black"],
        lw=1.05,
        ls="--",
        marker="o",
        markersize=4.2,
        markerfacecolor="white",
        markeredgecolor=PALETTE["black"],
        label="return unloading",
        zorder=4,
    )

    for i, d in enumerate(ds):
        for j, value in enumerate(d_raw[i]):
            ax.scatter(
                d + (j - 1) * 0.012,
                value,
                s=12,
                facecolor=REP_COLORS.get(j + 1, PALETTE["gray"]),
                edgecolor="none",
                alpha=0.90,
                zorder=5,
            )
        for j, value in enumerate(r_raw[i]):
            ax.scatter(
                d + (j - 1) * 0.012,
                value,
                s=16,
                facecolor="white",
                edgecolor=REP_COLORS.get(j + 1, PALETTE["gray"]),
                linewidth=0.70,
                alpha=0.95,
                zorder=5,
            )

    panel_label(ax, panel)
    ax.set_title("Matched-d force split across work zones", loc="left", pad=3)
    ax.set_xlabel("target d (mm)")
    ax.set_ylabel("F at target d (N)")
    ax.set_xticks(ds)
    ax.grid(axis="y", color=PALETTE["grid"], linewidth=0.6)
    ax.legend(loc="upper left")


def plot_bvec_split_figure(rows_by_d):
    fig, ax = prepare_single_figure(figsize=(5.6, 3.35))
    decorate_single_figure(
        fig,
        "Experiment 3.1-2: magnetic separation depends on work-zone depth",
    )

    ds, med_vals, low_vals, high_vals, raw_vals = metric_by_target(
        rows_by_d, lambda r: r["delta_Bvec_uT"]
    )
    colors = [
        PALETTE["red"] if 3.18 <= d <= 3.42 else PALETTE["black"]
        for d in ds
    ]

    add_workzone_band(ax)
    ax.bar(
        ds,
        med_vals,
        width=0.105,
        color=colors,
        alpha=0.86,
        edgecolor="none",
        zorder=2,
    )
    ax.errorbar(
        ds,
        med_vals,
        yerr=[med_vals - low_vals, high_vals - med_vals],
        fmt="none",
        ecolor=PALETTE["black"],
        elinewidth=0.9,
        capsize=2.4,
        zorder=4,
    )
    for i, d in enumerate(ds):
        for j, value in enumerate(raw_vals[i]):
            ax.scatter(
                d + (j - 1) * 0.025,
                value,
                s=15,
                facecolor="white",
                edgecolor=PALETTE["black"],
                linewidth=0.55,
                zorder=5,
            )

    ax.axhline(DYNAMIC_B_SIGNAL_UT, color=PALETTE["gray"], lw=0.8, ls=":")
    ax.text(
        ds[0] + 0.05,
        DYNAMIC_B_SIGNAL_UT + 4,
        "50 uT reference",
        ha="left",
        va="bottom",
        fontsize=5.8,
        color=PALETTE["gray_dark"],
    )
    ax.set_title("Path-pair magnetic split at each target d", loc="left", pad=3)
    ax.set_xlabel("target d (mm)")
    ax.set_ylabel("Delta Bvec (uT)")
    ax.set_xticks(ds)
    ax.grid(axis="y", color=PALETTE["grid"], linewidth=0.6)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    return fig


def axis_signature_matrix(rows_by_d):
    ds = target_values(rows_by_d)
    matrix = np.array(
        [
            [median([r["delta_Bx_uT"] for r in rows_by_d[d]]) for d in ds],
            [median([r["delta_By_uT"] for r in rows_by_d[d]]) for d in ds],
            [median([r["delta_Bz_uT"] for r in rows_by_d[d]]) for d in ds],
        ],
        dtype=float,
    )
    return ds, matrix


def plot_axis_signature_figure(rows_by_d):
    apply_style()
    fig = plt.figure(figsize=(6.1, 5.0))
    decorate_single_figure(
        fig,
        "Experiment 3.1-3: magnetic-axis signature of the active path pair",
    )

    ds, matrix = axis_signature_matrix(rows_by_d)
    axis_labels = ["dBx", "dBy", "dBz"]

    gs = fig.add_gridspec(
        nrows=2,
        ncols=2,
        width_ratios=[1.0, 0.035],
        height_ratios=[1.0, 1.05],
        left=0.08,
        right=0.94,
        bottom=0.09,
        top=0.86,
        hspace=0.34,
        wspace=0.04,
    )
    ax_heat = fig.add_subplot(gs[0, 0])
    cax = fig.add_subplot(gs[0, 1])
    ax_bar = fig.add_subplot(gs[1, 0])

    max_abs = max(1.0, float(np.nanmax(np.abs(matrix))))
    im = ax_heat.imshow(
        matrix,
        aspect="auto",
        cmap="RdBu_r",
        vmin=-max_abs,
        vmax=max_abs,
        zorder=1,
    )

    panel_label(ax_heat, "a")
    ax_heat.set_title("Axis signature map", loc="left", pad=3)
    ax_heat.set_xticks(np.arange(len(ds)), [f"{d:.1f}" for d in ds])
    ax_heat.set_yticks(np.arange(len(axis_labels)), axis_labels)
    ax_heat.tick_params(axis="both", length=0)
    ax_heat.spines.left.set_visible(False)
    ax_heat.spines.bottom.set_visible(False)

    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix[i, j]
            color = "white" if abs(value) >= 0.50 * max_abs else PALETTE["black"]
            ax_heat.text(
                j,
                i,
                f"{value:+.0f}",
                ha="center",
                va="center",
                fontsize=6.2,
                color=color,
            )

    # Thin cell borders make the heatmap readable when pasted into slides.
    ax_heat.set_xticks(np.arange(-0.5, len(ds), 1), minor=True)
    ax_heat.set_yticks(np.arange(-0.5, len(axis_labels), 1), minor=True)
    ax_heat.grid(which="minor", color="white", linewidth=1.2)
    ax_heat.tick_params(which="minor", bottom=False, left=False)

    cbar = fig.colorbar(im, cax=cax)
    cbar.ax.tick_params(labelsize=5.8, width=0.6, length=2)
    cbar.set_label("Delta B component (uT)", fontsize=6.2)

    x = np.arange(len(ds), dtype=float)
    width = 0.23
    bar_specs = [
        ("dBx", matrix[0], PALETTE["black"], -width),
        ("dBy", matrix[1], PALETTE["red"], 0.0),
        ("dBz", matrix[2], PALETTE["blue"], width),
    ]
    for label, values, color, offset in bar_specs:
        ax_bar.bar(
            x + offset,
            values,
            width=width * 0.88,
            color=color,
            alpha=0.9,
            label=label,
            zorder=3,
        )
    panel_label(ax_bar, "b")
    ax_bar.axhline(0, color=PALETTE["gray"], lw=0.8)
    ax_bar.set_title("Component magnitudes across work zones", loc="left", pad=3)
    ax_bar.set_xlabel("target d (mm)")
    ax_bar.set_ylabel("Delta B component (uT)")
    ax_bar.set_xticks(x, [f"{d:.1f}" for d in ds])
    ax_bar.grid(axis="y", color=PALETTE["grid"], linewidth=0.6)
    ax_bar.legend(loc="upper left", ncol=3)

    return fig


def plot_axis_component_bars(ax, rows_by_d, panel="e"):
    ds, matrix = axis_signature_matrix(rows_by_d)
    x = np.arange(len(ds), dtype=float)
    width = 0.23
    bar_specs = [
        ("dBx", matrix[0], PALETTE["black"], -width),
        ("dBy", matrix[1], PALETTE["red"], 0.0),
        ("dBz", matrix[2], PALETTE["blue"], width),
    ]
    for label, values, color, offset in bar_specs:
        ax.bar(
            x + offset,
            values,
            width=width * 0.88,
            color=color,
            alpha=0.9,
            label=label,
            zorder=3,
        )
    panel_label(ax, panel)
    ax.axhline(0, color=PALETTE["gray"], lw=0.8)
    ax.set_title("Component magnitudes across work zones", loc="left", pad=3)
    ax.set_xlabel("target d (mm)")
    ax.set_ylabel("Delta B component (uT)")
    ax.set_xticks(x, [f"{d:.1f}" for d in ds])
    ax.grid(axis="y", color=PALETTE["grid"], linewidth=0.6)
    ax.legend(loc="upper left", ncol=3)


def plot_workzone_decision_figure(rows_by_d):
    fig, ax = prepare_single_figure(figsize=(5.2, 3.45))
    decorate_single_figure(
        fig,
        "Experiment 3.1-4: work-zone selection from force and magnetic separation",
    )

    ds = target_values(rows_by_d)
    med_force = np.array(
        [median([abs(r["delta_F_N"]) for r in rows_by_d[d]]) for d in ds],
        dtype=float,
    )
    med_bvec = np.array(
        [median([r["delta_Bvec_uT"] for r in rows_by_d[d]]) for d in ds],
        dtype=float,
    )

    ax.plot(med_force, med_bvec, color=PALETTE["gray"], lw=0.85, zorder=1)
    for d, x, y in zip(ds, med_force, med_bvec):
        selected = 3.18 <= d <= 3.42
        edge = PALETTE["red"] if selected else PALETTE["black"]
        face = PALETTE["red"] if selected else "white"
        ax.scatter(
            x,
            y,
            s=62 if selected else 45,
            facecolor=face,
            edgecolor=edge,
            linewidth=1.0,
            zorder=4,
        )
        dx = 0.035 if d < 3.55 else -0.065
        ha = "left" if d < 3.55 else "right"
        ax.text(
            x + dx,
            y,
            f"{d:.1f}",
            ha=ha,
            va="center",
            fontsize=6.2,
            color=edge,
        )

    ax.annotate(
        "preferred work zone",
        xy=(med_force[np.where(ds == 3.4)[0][0]], med_bvec[np.where(ds == 3.4)[0][0]]),
        xytext=(1.34, 236),
        textcoords="data",
        arrowprops=dict(arrowstyle="-", lw=0.7, color=PALETTE["red"]),
        ha="left",
        va="center",
        fontsize=6,
        color=PALETTE["red"],
    )
    ax.set_title("Balanced force split and magnetic split", loc="left", pad=3)
    ax.set_xlabel("median |Delta F| (N)")
    ax.set_ylabel("median Delta Bvec (uT)")
    ax.set_xlim(0.35, 1.66)
    ax.set_ylim(55, 245)
    ax.grid(color=PALETTE["grid"], linewidth=0.6)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    return fig


def plot_d_match_check_figure(rows_by_d):
    fig, ax = prepare_single_figure(figsize=(5.5, 3.2))
    decorate_single_figure(
        fig,
        "Experiment 3.1-5: displacement matching validates the path-pair test",
    )
    plot_d_match_screen(ax, rows_by_d)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    return fig


def plot_d_match_screen(ax, rows_by_d, panel="a"):
    ds, med_vals, low_vals, high_vals, raw_vals = metric_by_target(
        rows_by_d, lambda r: abs(r["d_diff_mm"])
    )
    add_workzone_band(ax)
    ax.plot(
        ds,
        med_vals,
        color=PALETTE["black"],
        lw=1.25,
        marker="o",
        markersize=4.0,
        zorder=4,
    )
    ax.errorbar(
        ds,
        med_vals,
        yerr=[med_vals - low_vals, high_vals - med_vals],
        fmt="none",
        ecolor=PALETTE["black"],
        elinewidth=0.8,
        capsize=2.4,
        zorder=4,
    )
    for i, d in enumerate(ds):
        for j, value in enumerate(raw_vals[i]):
            ax.scatter(
                d + (j - 1) * 0.018,
                value,
                s=18,
                facecolor=REP_COLORS.get(j + 1, PALETTE["gray"]),
                edgecolor="white",
                linewidth=0.35,
                zorder=5,
            )

    ax.axhline(D_MATCH_TOL_MM, color=PALETTE["red"], lw=0.85, ls=":")
    ax.text(
        ds[-1] - 0.02,
        D_MATCH_TOL_MM + 0.0007,
        "0.020 mm gate",
        ha="right",
        va="bottom",
        fontsize=5.8,
        color=PALETTE["red"],
    )
    ax.text(
        3.30,
        max(max(high_vals), D_MATCH_TOL_MM) * 0.82,
        "candidate\nwork zone",
        ha="center",
        va="top",
        fontsize=5.7,
        color=PALETTE["gray_dark"],
    )
    panel_label(ax, panel)
    ax.set_title("Same-d acceptance check", loc="left", pad=3)
    ax.set_xlabel("target d (mm)")
    ax.set_ylabel("|d_return - d_direct| (mm)")
    ax.set_xticks(ds)
    ax.set_ylim(0, max(max(high_vals), D_MATCH_TOL_MM) * 1.22)
    ax.grid(axis="y", color=PALETTE["grid"], linewidth=0.6)


def plot_efficiency_figure(rows_by_d):
    fig, ax = prepare_single_figure(figsize=(5.5, 3.25))
    decorate_single_figure(
        fig,
        "Experiment 3.1-6: magnetic separation efficiency across work zones",
    )
    plot_efficiency_screen(ax, rows_by_d)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    return fig


def plot_efficiency_screen(ax, rows_by_d, panel="a"):
    def efficiency(row):
        denom = abs(row["delta_F_N"])
        if denom <= 1e-9:
            return float("nan")
        return row["delta_Bvec_uT"] / denom

    ds, med_vals, low_vals, high_vals, raw_vals = metric_by_target(
        rows_by_d, efficiency
    )
    add_workzone_band(ax)
    ax.plot(
        ds,
        med_vals,
        color=PALETTE["black"],
        lw=1.25,
        marker="o",
        markersize=4.0,
        zorder=4,
    )
    ax.errorbar(
        ds,
        med_vals,
        yerr=[med_vals - low_vals, high_vals - med_vals],
        fmt="none",
        ecolor=PALETTE["black"],
        elinewidth=0.8,
        capsize=2.4,
        zorder=4,
    )
    for i, d in enumerate(ds):
        for j, value in enumerate(raw_vals[i]):
            ax.scatter(
                d + (j - 1) * 0.018,
                value,
                s=18,
                facecolor=REP_COLORS.get(j + 1, PALETTE["gray"]),
                edgecolor="white",
                linewidth=0.35,
                zorder=5,
            )

    ax.text(
        3.30,
        max(high_vals) * 0.93,
        "candidate\nwork zone",
        ha="center",
        va="top",
        fontsize=5.7,
        color=PALETTE["gray_dark"],
    )
    panel_label(ax, panel)
    ax.set_title("Magnetic signal normalized by force split", loc="left", pad=3)
    ax.set_xlabel("target d (mm)")
    ax.set_ylabel("Delta Bvec / |Delta F| (uT/N)")
    ax.set_xticks(ds)
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", color=PALETTE["grid"], linewidth=0.6)


def plot_metric_screen(
    ax,
    rows_by_d,
    metric_fn,
    title,
    ylabel,
    threshold=None,
    threshold_label=None,
    panel="a",
):
    ds = np.array(list(rows_by_d.keys()), dtype=float)
    add_workzone_band(ax)

    med_vals = []
    lo_vals = []
    hi_vals = []
    for d in ds:
        vals = [metric_fn(r) for r in rows_by_d[d]]
        med_vals.append(median(vals))
        lo, hi = span(vals)
        lo_vals.append(lo)
        hi_vals.append(hi)
        for r in rows_by_d[d]:
            jitter = (r["trial"] - 2) * 0.020
            ax.scatter(
                d + jitter,
                metric_fn(r),
                s=22,
                color=REP_COLORS[r["trial"]],
                edgecolor="white",
                linewidth=0.35,
                zorder=3,
            )

    yerr = [
        np.array(med_vals) - np.array(lo_vals),
        np.array(hi_vals) - np.array(med_vals),
    ]
    ax.errorbar(
        ds,
        med_vals,
        yerr=yerr,
        color=PALETTE["black"],
        lw=1.45,
        marker="o",
        markersize=3.8,
        capsize=2.8,
        zorder=4,
    )

    if threshold is not None:
        ax.axhline(
            threshold,
            color=PALETTE["gray"],
            lw=0.8,
            ls=":",
        )
        if threshold_label:
            ax.text(
                ds[0] + 0.08,
                threshold,
                threshold_label,
                ha="left",
                va="bottom",
                fontsize=5.7,
                color=PALETTE["gray_dark"],
            )

    ymax = max(hi_vals) if hi_vals else 1.0
    ymin = min(lo_vals) if lo_vals else 0.0
    ax.text(
        3.30,
        ymin + 0.92 * (ymax - ymin),
        "candidate\nzone",
        ha="center",
        va="top",
        fontsize=5.8,
        color=PALETTE["gray_dark"],
    )

    ax.set_title(title, loc="left", pad=3)
    ax.set_xlabel("target d (mm)")
    ax.set_ylabel(ylabel)
    ax.set_xticks(ds)
    ax.grid(axis="y", color=PALETTE["grid"], linewidth=0.6)
    panel_label(ax, panel)


def plot_force_split(ax, rows_by_d):
    plot_metric_screen(
        ax,
        rows_by_d,
        lambda r: abs(r["delta_F_N"]),
        "Path-induced force separation",
        "|Delta F| at matched d (N)",
        threshold=MIN_FORCE_SPLIT_N,
        threshold_label="0.20 N reference",
        panel="a",
    )


def plot_bvec_screen(ax, rows_by_d):
    plot_metric_screen(
        ax,
        rows_by_d,
        lambda r: r["delta_Bvec_uT"],
        "Magnetic separation strength",
        "Delta Bvec (uT)",
        threshold=DYNAMIC_B_SIGNAL_UT,
        threshold_label="50 uT reference",
        panel="b",
    )


def plot_axis_heatmap(ax, rows_by_d, panel="c"):
    ds = np.array(list(rows_by_d.keys()), dtype=float)
    matrix = []
    for key in ("delta_Bx_uT", "delta_By_uT", "delta_Bz_uT"):
        matrix.append([median([r[key] for r in rows_by_d[d]]) for d in ds])
    matrix = np.array(matrix, dtype=float)

    max_abs = max(1.0, float(np.nanmax(np.abs(matrix))))
    im = ax.imshow(
        matrix,
        aspect="auto",
        cmap="RdBu_r",
        vmin=-max_abs,
        vmax=max_abs,
    )
    ax.set_title("Median 3-axis magnetic direction", loc="left", pad=3)
    ax.set_xticks(range(len(ds)), [f"{d:.1f}" for d in ds])
    ax.set_yticks(range(3), ["dBx", "dBy", "dBz"])
    ax.set_xlabel("target d (mm)")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix[i, j]
            color = "white" if abs(value) > 0.55 * max_abs else PALETTE["black"]
            ax.text(
                j,
                i,
                f"{value:+.0f}",
                ha="center",
                va="center",
                fontsize=5.8,
                color=color,
            )
    cbar = plt.colorbar(im, ax=ax, fraction=0.047, pad=0.025)
    cbar.ax.tick_params(labelsize=5.5, width=0.6, length=2)
    cbar.set_label("uT", fontsize=6)
    panel_label(ax, panel)


def plot_workzone_plane(ax, rows_by_d, panel="d"):
    ds = np.array(list(rows_by_d.keys()), dtype=float)
    med_force = np.array(
        [median([abs(r["delta_F_N"]) for r in rows_by_d[d]]) for d in ds],
        dtype=float,
    )
    med_bvec = np.array(
        [median([r["delta_Bvec_uT"] for r in rows_by_d[d]]) for d in ds],
        dtype=float,
    )

    ax.plot(med_force, med_bvec, color=PALETTE["gray"], lw=0.9, zorder=1)
    for d, x, y in zip(ds, med_force, med_bvec):
        selected = 3.18 <= d <= 3.42
        edge = PALETTE["red"] if selected else PALETTE["black"]
        face = PALETTE["red"] if selected else "white"
        ax.scatter(
            x,
            y,
            s=46 if selected else 35,
            facecolor=face,
            edgecolor=edge,
            linewidth=1.0,
            zorder=3,
        )
        dx = 0.030 if d < 3.55 else -0.060
        ha = "left" if d < 3.55 else "right"
        ax.text(
            x + dx,
            y,
            f"{d:.1f}",
            ha=ha,
            va="center",
            fontsize=6,
            color=edge,
        )

    ax.annotate(
        "preferred\nwork zone",
        xy=(med_force[np.where(ds == 3.4)[0][0]], med_bvec[np.where(ds == 3.4)[0][0]]),
        xytext=(1.34, 236),
        textcoords="data",
        arrowprops=dict(arrowstyle="-", lw=0.7, color=PALETTE["red"]),
        ha="left",
        va="center",
        fontsize=6,
        color=PALETTE["red"],
    )
    ax.set_title("Work-zone decision plane", loc="left", pad=3)
    ax.set_xlabel("median |Delta F| (N)")
    ax.set_ylabel("median Delta Bvec (uT)")
    ax.set_xlim(0.35, 1.66)
    ax.set_ylim(55, 245)
    ax.grid(color=PALETTE["grid"], linewidth=0.6)
    panel_label(ax, panel)


def print_numeric_summary(rows_by_d):
    print("target_d_mm same_d strong median_abs_dF_N median_dBvec_uT median_dBy_uT")
    for d, rows in rows_by_d.items():
        same_d = sum(r["same_d_ok"] for r in rows)
        strong = sum(r["verdict"] == "strong" for r in rows)
        med_df = median([abs(r["delta_F_N"]) for r in rows])
        med_db = median([r["delta_Bvec_uT"] for r in rows])
        med_dby = median([r["delta_By_uT"] for r in rows])
        print(f"{d:.2f} {same_d}/3 {strong}/3 {med_df:.4f} {med_db:.1f} {med_dby:+.1f}")


def save_figure(fig, output_dirs, filename):
    saved = []
    for out_dir in output_dirs:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / filename
        fig.savefig(path, dpi=PNG_DPI, bbox_inches="tight", facecolor="white")
        saved.append(path)
    return saved


def save_formal_figure_set(rows, output_dirs):
    rows_by_d = grouped(rows)
    figures = [
        ("force_split", plot_force_split_figure(rows_by_d)),
        ("bvec_split", plot_bvec_split_figure(rows_by_d)),
        ("axis_signature", plot_axis_signature_figure(rows_by_d)),
        ("workzone_decision", plot_workzone_decision_figure(rows_by_d)),
        ("d_match_check", plot_d_match_check_figure(rows_by_d)),
        ("efficiency", plot_efficiency_figure(rows_by_d)),
    ]
    saved = []
    for key, fig in figures:
        saved.extend(save_figure(fig, output_dirs, FIGURE_FILENAMES[key]))
        plt.close(fig)
    return saved


def plot_formal_scan(rows, output_dirs):
    apply_style()
    rows_by_d = grouped(rows)

    fig = plt.figure(figsize=(7.6, 5.1))
    gs = fig.add_gridspec(
        2,
        2,
        width_ratios=(1.23, 1.0),
        height_ratios=(1.05, 0.95),
        wspace=0.34,
        hspace=0.48,
    )
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d = fig.add_subplot(gs[1, 1])

    plot_force_split(ax_a, rows_by_d)
    plot_bvec_screen(ax_b, rows_by_d)
    plot_axis_heatmap(ax_c, rows_by_d)
    plot_workzone_plane(ax_d, rows_by_d)

    fig.suptitle(
        "Experiment 3.1: work-zone screening for near-matched-d / different-F path-pair excitation",
        x=0.01,
        y=0.99,
        ha="left",
        va="top",
        fontsize=8.8,
        fontweight="bold",
    )
    fig.text(
        0.01,
        0.955,
        "Formal data: session_20260610_091145 (3.1A) + session_20260610_104017 (3.1B)",
        ha="left",
        va="top",
        fontsize=6.2,
        color=PALETTE["gray_dark"],
    )

    saved = save_figure(
        fig,
        output_dirs,
        "same_d_different_f_scan_formal_workzone_legacy.png",
    )
    plt.close(fig)
    return saved


def plot_complete_workzone_figure(rows, output_dirs):
    apply_style()
    rows_by_d = grouped(rows)

    fig = plt.figure(figsize=(8.9, 7.8))
    gs = fig.add_gridspec(
        3,
        2,
        height_ratios=(1.25, 0.95, 1.05),
        width_ratios=(1.05, 1.0),
        left=0.07,
        right=0.97,
        bottom=0.06,
        top=0.90,
        wspace=0.34,
        hspace=0.62,
    )
    ax_a = fig.add_subplot(gs[0, :])
    ax_b = fig.add_subplot(gs[1, 0])
    ax_c = fig.add_subplot(gs[1, 1])
    ax_d = fig.add_subplot(gs[2, 0])
    ax_e = fig.add_subplot(gs[2, 1])

    plot_force_state_split(ax_a, rows_by_d, panel="a")
    plot_bvec_screen(ax_b, rows_by_d)
    plot_efficiency_screen(ax_c, rows_by_d, panel="c")
    plot_axis_heatmap(ax_d, rows_by_d, panel="d")
    plot_axis_component_bars(ax_e, rows_by_d, panel="e")

    fig.suptitle(
        "Experiment 3.1: work-zone screening for near-matched-d / different-F active path-pair excitation",
        x=0.02,
        y=0.985,
        ha="left",
        va="top",
        fontsize=10.5,
        fontweight="bold",
    )
    fig.text(
        0.02,
        0.952,
        "Formal data: session_20260610_091145 (3.1A) + session_20260610_104017 (3.1B)",
        ha="left",
        va="top",
        fontsize=7.2,
        color=PALETTE["gray_dark"],
    )
    saved = save_figure(fig, output_dirs, FIGURE_FILENAMES["complete"])
    plt.close(fig)
    return saved


def main():
    rows = load_formal_rows()
    output_dirs = [session for _, session, _ in DEFAULT_INPUTS]
    print_numeric_summary(grouped(rows))
    saved = save_formal_figure_set(rows, output_dirs)
    saved.extend(plot_complete_workzone_figure(rows, output_dirs))
    print("\nSaved:")
    for path in saved:
        print(f"  {path}")


if __name__ == "__main__":
    main()
