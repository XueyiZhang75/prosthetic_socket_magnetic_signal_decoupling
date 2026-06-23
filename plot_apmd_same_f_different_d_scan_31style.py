from __future__ import annotations

from pathlib import Path
from statistics import median

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

from plot_apmd_same_f_different_d_scan import load_formal_rows, save_csv


ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

BLACK = "#222222"
RED = "#bf3f3f"
BLUE = "#2f84c5"
GRAY = "#808080"
GRID = "#e9e9e9"
HIGHLIGHT = "#f3efe4"
REP_COLORS = {1: "#000000", 2: "#d62728", 3: "#1f77b4"}

SAME_F_GATE_MN = 50.0
DISP_GATE_MM = 0.10
MAG_GATE_UT = 100.0
CANDIDATE_FORCE_RANGE = (3.65, 4.45)


mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": 8,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 1.0,
        "legend.frameon": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)


def group_by_target(rows: list[dict[str, object]]) -> dict[float, list[dict[str, object]]]:
    out: dict[float, list[dict[str, object]]] = {}
    for row in rows:
        out.setdefault(float(row["target_F"]), []).append(row)
    return dict(sorted(out.items()))


def metric_by_target(rows: list[dict[str, object]], key: str, absolute: bool = False):
    groups = group_by_target(rows)
    targets = np.array(list(groups.keys()), dtype=float)
    raw: list[list[float]] = []
    med: list[float] = []
    low: list[float] = []
    high: list[float] = []
    for target in targets:
        vals = [float(r[key]) for r in groups[target]]
        if absolute:
            vals = [abs(v) for v in vals]
        raw.append(vals)
        med.append(float(np.median(vals)))
        low.append(float(np.min(vals)))
        high.append(float(np.max(vals)))
    return targets, np.array(med), np.array(low), np.array(high), raw


def ratio_by_target(rows: list[dict[str, object]], numerator_key: str, denominator_key: str):
    groups = group_by_target(rows)
    targets = np.array(list(groups.keys()), dtype=float)
    raw: list[list[float]] = []
    med: list[float] = []
    low: list[float] = []
    high: list[float] = []
    for target in targets:
        vals = []
        for row in groups[target]:
            denom = abs(float(row[denominator_key]))
            vals.append(float(row[numerator_key]) / denom if denom > 0 else float("nan"))
        vals = [v for v in vals if np.isfinite(v)]
        raw.append(vals)
        med.append(float(np.median(vals)))
        low.append(float(np.min(vals)))
        high.append(float(np.max(vals)))
    return targets, np.array(med), np.array(low), np.array(high), raw


def style_axis(ax):
    ax.grid(axis="y", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)


def add_candidate_band(ax):
    lo, hi = CANDIDATE_FORCE_RANGE
    ax.axvspan(lo, hi, color=HIGHLIGHT, zorder=0)
    y0, y1 = ax.get_ylim()
    ax.text(
        (lo + hi) / 2,
        y0 + 0.88 * (y1 - y0),
        "candidate\nforce zone",
        ha="center",
        va="top",
        fontsize=8,
        color="#555555",
    )


def panel_label(ax, label: str):
    ax.text(
        -0.12,
        1.08,
        label,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=15,
        fontweight="bold",
    )


def decorate(fig, title: str):
    fig.suptitle(title, x=0.02, y=0.99, ha="left", va="top", fontsize=15, fontweight="bold")
    fig.text(
        0.02,
        0.94,
        "Formal accepted data: target F = 1.50-4.90 N; three usable path-pairs per point",
        ha="left",
        va="top",
        fontsize=10,
        color="#555555",
    )


def save(fig, filename: str) -> Path:
    out = REPORTS / filename
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_displacement_state_split(rows: list[dict[str, object]], ax=None, panel: str = "a"):
    created = ax is None
    if created:
        fig, ax = plt.subplots(figsize=(8.0, 4.2))
        decorate(fig, "Experiment 3.2-1: near-matched force creates a displacement split")
    else:
        fig = ax.figure

    groups = group_by_target(rows)
    targets = np.array(list(groups.keys()), dtype=float)
    _, load_med, _, _, load_raw = metric_by_target(rows, "d_loading")
    _, unload_med, _, _, unload_raw = metric_by_target(rows, "d_unloading")

    ax.plot(
        targets,
        load_med,
        color=BLACK,
        lw=1.9,
        marker="o",
        markersize=6,
        markerfacecolor=BLACK,
        markeredgecolor=BLACK,
        label="loading target",
        zorder=4,
    )
    ax.plot(
        targets,
        unload_med,
        color=BLACK,
        lw=1.7,
        ls="--",
        marker="o",
        markersize=6,
        markerfacecolor="white",
        markeredgecolor=BLACK,
        label="return unloading",
        zorder=4,
    )

    for i, target in enumerate(targets):
        for j, value in enumerate(load_raw[i]):
            ax.scatter(
                target + (j - 1) * 0.025,
                value,
                s=32,
                facecolor=REP_COLORS.get(j + 1, GRAY),
                edgecolor="none",
                zorder=5,
            )
        for j, value in enumerate(unload_raw[i]):
            ax.scatter(
                target + (j - 1) * 0.025,
                value,
                s=40,
                facecolor="white",
                edgecolor=REP_COLORS.get(j + 1, GRAY),
                linewidth=1.1,
                zorder=5,
            )

    ymin = min(np.nanmin(load_med), np.nanmin(unload_med)) - 0.12
    ymax = max(np.nanmax(load_med), np.nanmax(unload_med)) + 0.15
    ax.set_ylim(ymin, ymax)
    add_candidate_band(ax)
    panel_label(ax, panel)
    ax.set_title("Matched-F displacement split across force targets", loc="left", pad=5)
    ax.set_xlabel("target F (N)")
    ax.set_ylabel("d at matched F (mm)")
    ax.set_xticks(targets)
    style_axis(ax)
    ax.legend(loc="upper left")
    if created:
        fig.tight_layout(rect=(0, 0, 1, 0.90))
    return fig


def plot_bvec_split(rows: list[dict[str, object]], ax=None, panel: str = "a"):
    created = ax is None
    if created:
        fig, ax = plt.subplots(figsize=(6.8, 3.8))
        decorate(fig, "Experiment 3.2-2: magnetic separation depends on force zone")
    else:
        fig = ax.figure

    targets, med, low, high, raw = metric_by_target(rows, "delta_Bvec")
    ax.plot(targets, med, color=BLACK, lw=1.8, marker="o", markersize=5.5, zorder=4)
    ax.errorbar(
        targets,
        med,
        yerr=[med - low, high - med],
        fmt="none",
        ecolor=BLACK,
        elinewidth=1.0,
        capsize=3,
        zorder=4,
    )
    for i, target in enumerate(targets):
        for j, value in enumerate(raw[i]):
            ax.scatter(
                target + (j - 1) * 0.045,
                value,
                s=32,
                facecolor=REP_COLORS.get(j + 1, GRAY),
                edgecolor="white",
                linewidth=0.5,
                zorder=5,
            )
    ax.set_ylim(min(MAG_GATE_UT * 0.75, float(np.nanmin(low)) - 25), float(np.nanmax(high)) + 35)
    add_candidate_band(ax)
    ax.axhline(MAG_GATE_UT, color=GRAY, lw=1.0, ls=":")
    ax.text(targets[0] + 0.06, MAG_GATE_UT + 6, "100 uT reference", ha="left", va="bottom", color="#666666")
    ax.set_title("Path-pair magnetic split at each target F", loc="left", pad=5)
    ax.set_xlabel("target F (N)")
    ax.set_ylabel("Delta Bvec (uT)")
    ax.set_xticks(targets)
    style_axis(ax)
    panel_label(ax, panel)
    if created:
        fig.tight_layout(rect=(0, 0, 1, 0.90))
    return fig


def plot_delta_d_bar(rows: list[dict[str, object]], ax=None, panel: str = "a"):
    created = ax is None
    if created:
        fig, ax = plt.subplots(figsize=(6.8, 3.8))
        decorate(fig, "Experiment 3.2-3: matched-force displacement split magnitude")
    else:
        fig = ax.figure

    targets, med, low, high, raw = metric_by_target(rows, "delta_d", absolute=True)
    colors = [RED if CANDIDATE_FORCE_RANGE[0] <= t <= CANDIDATE_FORCE_RANGE[1] else BLACK for t in targets]
    ax.bar(targets, med, width=0.22, color=colors, alpha=0.88, edgecolor="none", zorder=2)
    ax.errorbar(
        targets,
        med,
        yerr=[med - low, high - med],
        fmt="none",
        ecolor=BLACK,
        elinewidth=1.0,
        capsize=3,
        zorder=4,
    )
    for i, target in enumerate(targets):
        for j, value in enumerate(raw[i]):
            ax.scatter(
                target + (j - 1) * 0.045,
                value,
                s=32,
                facecolor=REP_COLORS.get(j + 1, GRAY),
                edgecolor="white",
                linewidth=0.5,
                zorder=5,
            )
    ax.set_ylim(0, float(np.nanmax(high)) + 0.04)
    add_candidate_band(ax)
    ax.axhline(DISP_GATE_MM, color=GRAY, lw=1.0, ls=":")
    ax.text(targets[0] + 0.06, DISP_GATE_MM + 0.006, "0.10 mm reference", ha="left", va="bottom", color="#666666")
    ax.set_title("Matched-F displacement split magnitude", loc="left", pad=5)
    ax.set_xlabel("target F (N)")
    ax.set_ylabel("|Delta d| (mm)")
    ax.set_xticks(targets)
    style_axis(ax)
    panel_label(ax, panel)
    if created:
        fig.tight_layout(rect=(0, 0, 1, 0.90))
    return fig


def plot_bvec_per_delta_d(rows: list[dict[str, object]], ax=None, panel: str = "a"):
    created = ax is None
    if created:
        fig, ax = plt.subplots(figsize=(6.8, 3.8))
        decorate(fig, "Experiment 3.2-3: magnetic signal normalized by displacement split")
    else:
        fig = ax.figure

    targets, med, low, high, raw = ratio_by_target(rows, "delta_Bvec", "delta_d")
    colors = [RED if CANDIDATE_FORCE_RANGE[0] <= t <= CANDIDATE_FORCE_RANGE[1] else BLACK for t in targets]
    ax.bar(targets, med, width=0.22, color=colors, alpha=0.88, edgecolor="none", zorder=2)
    ax.errorbar(
        targets,
        med,
        yerr=[med - low, high - med],
        fmt="none",
        ecolor=BLACK,
        elinewidth=1.0,
        capsize=3,
        zorder=4,
    )
    for i, target in enumerate(targets):
        for j, value in enumerate(raw[i]):
            ax.scatter(
                target + (j - 1) * 0.045,
                value,
                s=32,
                facecolor=REP_COLORS.get(j + 1, GRAY),
                edgecolor="white",
                linewidth=0.5,
                zorder=5,
            )
    ax.set_ylim(0, float(np.nanmax(high)) * 1.18)
    add_candidate_band(ax)
    ax.set_title("Magnetic signal normalized by displacement split", loc="left", pad=5)
    ax.set_xlabel("target F (N)")
    ax.set_ylabel("Delta Bvec / |Delta d| (uT/mm)")
    ax.set_xticks(targets)
    style_axis(ax)
    panel_label(ax, panel)
    if created:
        fig.tight_layout(rect=(0, 0, 1, 0.90))
    return fig


def axis_matrix(rows: list[dict[str, object]]):
    groups = group_by_target(rows)
    targets = np.array(list(groups.keys()), dtype=float)
    matrix = np.array(
        [
            [median(float(r["delta_Bx"]) for r in groups[t]) for t in targets],
            [median(float(r["delta_By"]) for r in groups[t]) for t in targets],
            [median(float(r["delta_Bz"]) for r in groups[t]) for t in targets],
        ],
        dtype=float,
    )
    return targets, matrix


def plot_axis_signature_heatmap(rows: list[dict[str, object]], ax=None, cax=None, panel: str = "a"):
    created = ax is None
    if created:
        fig = plt.figure(figsize=(7.0, 3.2))
        decorate(fig, "Experiment 3.2-4: magnetic-axis signature map")
        gs = fig.add_gridspec(
            nrows=1,
            ncols=2,
            width_ratios=[1.0, 0.045],
            left=0.10,
            right=0.92,
            bottom=0.22,
            top=0.78,
            wspace=0.05,
        )
        ax = fig.add_subplot(gs[0, 0])
        cax = fig.add_subplot(gs[0, 1])
    else:
        fig = ax.figure

    targets, matrix = axis_matrix(rows)
    labels = ["dBx", "dBy", "dBz"]
    vmax = max(1.0, float(np.nanmax(np.abs(matrix))))
    im = ax.imshow(matrix, aspect="auto", cmap="RdBu_r", vmin=-vmax, vmax=vmax)
    ax.set_xticks(np.arange(len(targets)), [f"{t:g}" for t in targets])
    ax.set_yticks(np.arange(len(labels)), labels)
    ax.tick_params(axis="both", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix[i, j]
            color = "white" if abs(value) >= 0.50 * vmax else BLACK
            ax.text(j, i, f"{value:+.0f}", ha="center", va="center", fontsize=8, color=color)
    ax.set_xticks(np.arange(-0.5, len(targets), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(labels), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.5)
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.set_title("Axis signature map", loc="left", pad=5)
    ax.set_xlabel("target F (N)")
    panel_label(ax, panel)
    if cax is not None:
        cbar = fig.colorbar(im, cax=cax)
        cbar.set_label("Delta B component (uT)")
    elif not created:
        cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.02)
        cbar.set_label("uT")
    if created:
        return fig
    return fig


def plot_component_magnitudes(rows: list[dict[str, object]], ax=None, panel: str = "a"):
    created = ax is None
    if created:
        fig, ax = plt.subplots(figsize=(6.8, 3.8))
        decorate(fig, "Experiment 3.2-5: component magnitudes across force zones")
    else:
        fig = ax.figure

    targets, matrix = axis_matrix(rows)
    x = np.arange(len(targets))
    width = 0.22
    for offset, row, color, label in [
        (-width, matrix[0], BLACK, "dBx"),
        (0.0, matrix[1], RED, "dBy"),
        (width, matrix[2], BLUE, "dBz"),
    ]:
        ax.bar(x + offset, row, width=width * 0.88, color=color, alpha=0.90, label=label, zorder=3)
    ax.axhline(0, color=GRAY, lw=1.0)
    ax.set_title("Component magnitudes across force zones", loc="left", pad=5)
    ax.set_xlabel("target F (N)")
    ax.set_ylabel("Delta B component (uT)")
    ax.set_xticks(x, [f"{t:g}" for t in targets])
    style_axis(ax)
    ax.legend(loc="upper left", ncol=3)
    panel_label(ax, panel)
    if created:
        fig.tight_layout(rect=(0, 0, 1, 0.90))
    return fig


def plot_axis_signature(rows: list[dict[str, object]], ax_heat=None, ax_bar=None, cax=None):
    created = ax_heat is None
    if created:
        fig = plt.figure(figsize=(8.2, 6.2))
        decorate(fig, "Experiment 3.2-3: magnetic-axis signature of the active path pair")
        gs = fig.add_gridspec(
            nrows=2,
            ncols=2,
            width_ratios=[1.0, 0.035],
            height_ratios=[1.0, 1.05],
            left=0.08,
            right=0.94,
            bottom=0.10,
            top=0.84,
            hspace=0.38,
            wspace=0.05,
        )
        ax_heat = fig.add_subplot(gs[0, 0])
        cax = fig.add_subplot(gs[0, 1])
        ax_bar = fig.add_subplot(gs[1, 0])
    else:
        fig = ax_heat.figure

    targets, matrix = axis_matrix(rows)
    labels = ["dBx", "dBy", "dBz"]
    vmax = max(1.0, float(np.nanmax(np.abs(matrix))))
    im = ax_heat.imshow(matrix, aspect="auto", cmap="RdBu_r", vmin=-vmax, vmax=vmax)
    ax_heat.set_xticks(np.arange(len(targets)), [f"{t:g}" for t in targets])
    ax_heat.set_yticks(np.arange(len(labels)), labels)
    ax_heat.tick_params(axis="both", length=0)
    for spine in ax_heat.spines.values():
        spine.set_visible(False)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix[i, j]
            color = "white" if abs(value) >= 0.50 * vmax else BLACK
            ax_heat.text(j, i, f"{value:+.0f}", ha="center", va="center", fontsize=8, color=color)
    ax_heat.set_xticks(np.arange(-0.5, len(targets), 1), minor=True)
    ax_heat.set_yticks(np.arange(-0.5, len(labels), 1), minor=True)
    ax_heat.grid(which="minor", color="white", linewidth=1.5)
    ax_heat.tick_params(which="minor", bottom=False, left=False)
    ax_heat.set_title("Axis signature map", loc="left", pad=5)
    panel_label(ax_heat, "a" if created else "c")
    if cax is not None:
        cbar = fig.colorbar(im, cax=cax)
        cbar.set_label("Delta B component (uT)")

    x = np.arange(len(targets))
    width = 0.22
    for offset, row, color, label in [
        (-width, matrix[0], BLACK, "dBx"),
        (0.0, matrix[1], RED, "dBy"),
        (width, matrix[2], BLUE, "dBz"),
    ]:
        ax_bar.bar(x + offset, row, width=width * 0.88, color=color, alpha=0.90, label=label, zorder=3)
    ax_bar.axhline(0, color=GRAY, lw=1.0)
    ax_bar.set_title("Component magnitudes across force zones", loc="left", pad=5)
    ax_bar.set_xlabel("target F (N)")
    ax_bar.set_ylabel("Delta B component (uT)")
    ax_bar.set_xticks(x, [f"{t:g}" for t in targets])
    style_axis(ax_bar)
    ax_bar.legend(loc="upper left", ncol=3)
    panel_label(ax_bar, "b" if created else "d")

    if created:
        return fig
    return fig


def plot_workzone_decision(rows: list[dict[str, object]], ax=None, panel: str = "a"):
    created = ax is None
    if created:
        fig, ax = plt.subplots(figsize=(6.2, 4.0))
        decorate(fig, "Experiment 3.2-4: force-zone selection from displacement and magnetic separation")
    else:
        fig = ax.figure

    groups = group_by_target(rows)
    targets = np.array(list(groups.keys()), dtype=float)
    med_d = np.array([median(abs(float(r["delta_d"])) for r in groups[t]) for t in targets])
    med_b = np.array([median(float(r["delta_Bvec"]) for r in groups[t]) for t in targets])
    ax.plot(med_d, med_b, color=GRAY, lw=1.1, zorder=1)
    for t, x, y in zip(targets, med_d, med_b):
        selected = CANDIDATE_FORCE_RANGE[0] <= t <= CANDIDATE_FORCE_RANGE[1]
        ax.scatter(
            x,
            y,
            s=84 if selected else 62,
            facecolor=RED if selected else "white",
            edgecolor=RED if selected else BLACK,
            linewidth=1.4,
            zorder=4,
        )
        ax.text(x + 0.004, y, f"{t:g}", va="center", ha="left", color=RED if selected else BLACK)
    ax.axhline(MAG_GATE_UT, color=GRAY, lw=1.0, ls=":")
    ax.axvline(DISP_GATE_MM, color=GRAY, lw=1.0, ls=":")
    ax.set_title("Balanced displacement split and magnetic split", loc="left", pad=5)
    ax.set_xlabel("median |Delta d| (mm)")
    ax.set_ylabel("median Delta Bvec (uT)")
    ax.set_xlim(0.095, max(med_d) + 0.03)
    ax.set_ylim(80, max(med_b) + 55)
    ax.grid(color=GRID, linewidth=0.7)
    panel_label(ax, panel)
    if created:
        fig.tight_layout(rect=(0, 0, 1, 0.90))
    return fig


def plot_force_match_check(rows: list[dict[str, object]], ax=None, panel: str = "a"):
    created = ax is None
    if created:
        fig, ax = plt.subplots(figsize=(6.8, 3.7))
        decorate(fig, "Experiment 3.2-5: force matching validates the path-pair test")
    else:
        fig = ax.figure

    targets, med, low, high, raw = metric_by_target(rows, "delta_F", absolute=True)
    med *= 1000
    low *= 1000
    high *= 1000
    raw = [[v * 1000 for v in vals] for vals in raw]
    ax.plot(targets, med, color=BLACK, lw=1.7, marker="o", markersize=5, zorder=4)
    ax.errorbar(targets, med, yerr=[med - low, high - med], fmt="none", ecolor=BLACK, capsize=3, zorder=4)
    for i, target in enumerate(targets):
        for j, value in enumerate(raw[i]):
            ax.scatter(
                target + (j - 1) * 0.045,
                value,
                s=36,
                facecolor=REP_COLORS.get(j + 1, GRAY),
                edgecolor="white",
                linewidth=0.5,
                zorder=5,
            )
    ax.axhline(SAME_F_GATE_MN, color=RED, lw=1.0, ls=":")
    ax.text(targets[-1] - 0.05, SAME_F_GATE_MN + 1.5, "50 mN gate", ha="right", va="bottom", color=RED)
    ax.set_title("Same-F acceptance check", loc="left", pad=5)
    ax.set_xlabel("target F (N)")
    ax.set_ylabel("|F_unloading - F_loading| (mN)")
    ax.set_xticks(targets)
    ax.set_ylim(0, max(SAME_F_GATE_MN, max(high)) * 1.25)
    style_axis(ax)
    panel_label(ax, panel)
    if created:
        fig.tight_layout(rect=(0, 0, 1, 0.90))
    return fig


def plot_complete_abcde(rows: list[dict[str, object]]):
    fig = plt.figure(figsize=(12.2, 12.2))
    gs = fig.add_gridspec(3, 2, height_ratios=[1.1, 1.0, 1.0], hspace=0.50, wspace=0.30)
    ax_a = fig.add_subplot(gs[0, :])
    ax_b = fig.add_subplot(gs[1, 0])
    ax_c = fig.add_subplot(gs[1, 1])
    ax_d = fig.add_subplot(gs[2, 0])
    ax_e = fig.add_subplot(gs[2, 1])

    plot_displacement_state_split(rows, ax_a, panel="a")
    plot_bvec_split(rows, ax_b, panel="b")
    plot_bvec_per_delta_d(rows, ax_c, panel="c")
    plot_axis_signature_heatmap(rows, ax_d, panel="d")
    plot_component_magnitudes(rows, ax_e, panel="e")

    fig.suptitle(
        "Experiment 3.2: work-zone screening for near-matched-F / different-d path-pair excitation",
        x=0.02,
        y=0.99,
        ha="left",
        va="top",
        fontsize=16,
        fontweight="bold",
    )
    fig.text(
        0.02,
        0.965,
        "Formal accepted data: target F = 1.50-4.90 N; three usable path-pairs per point",
        ha="left",
        va="top",
        fontsize=10,
        color="#555555",
    )
    return fig


def main() -> None:
    rows = load_formal_rows()
    csv_out = save_csv(rows)
    outputs = [csv_out]
    outputs.append(save(plot_displacement_state_split(rows), "experiment_3_2_style31_1_displacement_split.png"))
    outputs.append(save(plot_bvec_split(rows), "experiment_3_2_style31_2_bvec_split.png"))
    outputs.append(save(plot_bvec_per_delta_d(rows), "experiment_3_2_style31_3_bvec_per_delta_d.png"))
    outputs.append(save(plot_axis_signature_heatmap(rows), "experiment_3_2_style31_4_axis_signature_map.png"))
    outputs.append(save(plot_component_magnitudes(rows), "experiment_3_2_style31_5_component_magnitudes.png"))
    outputs.append(save(plot_complete_abcde(rows), "experiment_3_2_style31_complete_abcde.png"))

    print("Generated:")
    for out in outputs:
        print(f"  {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
