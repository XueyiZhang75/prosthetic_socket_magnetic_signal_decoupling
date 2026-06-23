from __future__ import annotations

import csv
import math
from pathlib import Path
from statistics import median

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

FORMAL_SUMMARIES = [
    (1.50, ROOT / "decouple_data/session_20260610_153403/same_f_different_d_scan_150_pair_summary.csv"),
    (1.80, ROOT / "decouple_data/session_20260611_093557/same_f_different_d_scan_180_pair_summary.csv"),
    (2.50, ROOT / "decouple_data/session_20260611_110131/same_f_different_d_scan_250_pair_summary.csv"),
    (3.20, ROOT / "decouple_data/session_20260611_142649/same_f_different_d_scan_320_formal_composite_summary.csv"),
    (3.75, ROOT / "decouple_data/session_20260611_153032/same_f_different_d_scan_375_formal_composite_summary.csv"),
    (4.30, ROOT / "decouple_data/session_20260611_164622/same_f_different_d_scan_430_pair_summary.csv"),
    (4.90, ROOT / "decouple_data/session_20260611_183729/same_f_different_d_scan_490_formal_composite_summary.csv"),
]

REPRESENTATIVE_RAW = ROOT / "decouple_data/session_20260611_164622/same_f_different_d_scan_430_rep2.csv"

BLACK = "#222222"
RED = "#bf3f3f"
BLUE = "#2f84c5"
GRAY = "#8a8a8a"
LIGHT_GRAY = "#d8d8d8"
PALE_BAND = "#efe8d8"


mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": 9,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 1.0,
        "legend.frameon": False,
        "xtick.major.width": 1.0,
        "ytick.major.width": 1.0,
        "axes.titlelocation": "left",
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)


def ffloat(row: dict[str, str], key: str) -> float:
    return float(row[key])


def load_formal_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for target_f, path in FORMAL_SUMMARIES:
        if not path.exists():
            raise FileNotFoundError(path)
        with path.open(newline="", encoding="utf-8") as f:
            for i, row in enumerate(csv.DictReader(f), start=1):
                verdict = row.get("verdict", "")
                if verdict != "strong":
                    continue
                rows.append(
                    {
                        "target_F": target_f,
                        "rep": int(row.get("formal_rep") or row.get("trial") or i),
                        "source_session_id": row.get("source_session_id") or row.get("session_id", ""),
                        "source_trial": row.get("source_trial") or row.get("trial", ""),
                        "F_loading": ffloat(row, "F_loading_N"),
                        "F_unloading": ffloat(row, "F_unloading_N"),
                        "delta_F": ffloat(row, "delta_F_N"),
                        "d_loading": ffloat(row, "d_loading_mm"),
                        "d_unloading": ffloat(row, "d_unloading_mm"),
                        "delta_d": ffloat(row, "delta_d_mm"),
                        "delta_Bmag": ffloat(row, "delta_Bmag_uT"),
                        "delta_Bx": ffloat(row, "delta_Bx_uT"),
                        "delta_By": ffloat(row, "delta_By_uT"),
                        "delta_Bz": ffloat(row, "delta_Bz_uT"),
                        "delta_Bvec": ffloat(row, "delta_Bvec_uT"),
                    }
                )
    return rows


def grouped(rows: list[dict[str, object]]) -> dict[float, list[dict[str, object]]]:
    out: dict[float, list[dict[str, object]]] = {}
    for row in rows:
        out.setdefault(float(row["target_F"]), []).append(row)
    return dict(sorted(out.items()))


def median_by_target(rows: list[dict[str, object]], key: str) -> dict[float, float]:
    return {target: median(float(r[key]) for r in rs) for target, rs in grouped(rows).items()}


def sem(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return float(np.std(values, ddof=1) / math.sqrt(len(values)))


def save_csv(rows: list[dict[str, object]]) -> Path:
    out = REPORTS / "experiment_3_2_same_f_different_d_figure_data_replicates.csv"
    fieldnames = [
        "target_F",
        "rep",
        "source_session_id",
        "source_trial",
        "F_loading",
        "F_unloading",
        "delta_F",
        "d_loading",
        "d_unloading",
        "delta_d",
        "delta_Bmag",
        "delta_Bx",
        "delta_By",
        "delta_Bz",
        "delta_Bvec",
    ]
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return out


def save_fig(fig: mpl.figure.Figure, stem: str) -> Path:
    out = REPORTS / f"{stem}.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out


def style_grid(ax: mpl.axes.Axes) -> None:
    ax.grid(axis="y", color="#e8e8e8", linewidth=0.8)
    ax.set_axisbelow(True)


def panel_path_loop(rows: list[dict[str, object]], ax: mpl.axes.Axes | None = None) -> mpl.figure.Figure:
    created = ax is None
    if created:
        fig, ax = plt.subplots(figsize=(5.2, 4.0))
    else:
        fig = ax.figure

    raw = list(csv.DictReader(REPRESENTATIVE_RAW.open(newline="", encoding="utf-8")))
    states = {
        "loading_target": ("loading target", BLACK, "o"),
        "preload_deep": ("deeper preload", BLUE, "o"),
        "unloading_target": ("unloading target", RED, "o"),
    }
    med = {}
    for state, (_, color, marker) in states.items():
        sr = [r for r in raw if r.get("state_label") == state]
        if not sr:
            continue
        med[state] = (
            median(float(r["d_actual_mm"]) for r in sr),
            median(float(r["F_N"]) for r in sr),
        )
        ax.scatter(
            [float(r["d_actual_mm"]) for r in sr[:: max(1, len(sr) // 90)]],
            [float(r["F_N"]) for r in sr[:: max(1, len(sr) // 90)]],
            s=10,
            color=color,
            alpha=0.16,
            linewidth=0,
        )
        ax.scatter(
            med[state][0],
            med[state][1],
            s=72,
            color=color if state != "unloading_target" else "white",
            edgecolor=color,
            linewidth=1.7,
            marker=marker,
            zorder=4,
            label=states[state][0],
        )
    order = ["loading_target", "preload_deep", "unloading_target"]
    for a, b in zip(order[:-1], order[1:]):
        if a in med and b in med:
            ax.annotate(
                "",
                xy=med[b],
                xytext=med[a],
                arrowprops=dict(arrowstyle="->", color=GRAY, lw=1.7, shrinkA=7, shrinkB=7),
                zorder=3,
            )
    if "loading_target" in med and "unloading_target" in med:
        dd = med["unloading_target"][0] - med["loading_target"][0]
        ax.text(
            0.03,
            0.96,
            f"example: 4.30 N\\nmatched F, Δd={dd:+.2f} mm",
            transform=ax.transAxes,
            ha="left",
            va="top",
            color="#555555",
        )
    ax.set_title("Representative same-F / different-d path pair", fontsize=12, pad=8)
    ax.set_xlabel("d (mm)")
    ax.set_ylabel("F (N)")
    style_grid(ax)
    ax.legend(loc="lower right", fontsize=8)
    return fig


def panel_force_match(rows: list[dict[str, object]], ax: mpl.axes.Axes | None = None) -> mpl.figure.Figure:
    created = ax is None
    if created:
        fig, ax = plt.subplots(figsize=(5.6, 3.4))
    else:
        fig = ax.figure
    groups = grouped(rows)
    targets = list(groups)
    x = np.arange(len(targets))
    max_abs = [max(abs(float(r["delta_F"]) * 1000) for r in groups[t]) for t in targets]
    med_abs = [median(abs(float(r["delta_F"]) * 1000) for r in groups[t]) for t in targets]
    ax.bar(x, max_abs, width=0.58, color="#eeeeee", edgecolor="#777777", linewidth=1.0, zorder=1)
    jitter = [-0.14, 0.0, 0.14]
    for xi, target in zip(x, targets):
        for i, r in enumerate(groups[target]):
            ax.scatter(
                xi + jitter[i % 3],
                abs(float(r["delta_F"]) * 1000),
                s=42,
                color=[BLACK, RED, BLUE][i % 3],
                edgecolor="white",
                linewidth=0.6,
                zorder=3,
            )
        ax.plot([xi - 0.22, xi + 0.22], [med_abs[xi], med_abs[xi]], color=BLACK, lw=1.8, zorder=4)
    ax.axhline(50, color=GRAY, lw=1.0, ls="--")
    ax.text(len(targets) - 0.12, 52, "50 mN gate", ha="right", va="bottom", fontsize=8, color="#666666")
    ax.set_title("Same-force matching quality", fontsize=12, pad=8)
    ax.set_xlabel("target F (N)")
    ax.set_ylabel("max |F_unloading - F_loading| (mN)")
    ax.set_xticks(x, [f"{t:g}" for t in targets])
    ax.set_ylim(0, max(62, max(max_abs) * 1.25))
    style_grid(ax)
    return fig


def panel_displacement_split(rows: list[dict[str, object]], ax: mpl.axes.Axes | None = None) -> mpl.figure.Figure:
    created = ax is None
    if created:
        fig, ax = plt.subplots(figsize=(5.6, 3.6))
    else:
        fig = ax.figure
    groups = grouped(rows)
    targets = list(groups)
    x = np.arange(len(targets))
    med_dd = [median(float(r["delta_d"]) for r in groups[t]) for t in targets]
    err_dd = [sem([float(r["delta_d"]) for r in groups[t]]) for t in targets]
    ax.bar(x, med_dd, width=0.58, color=BLACK, edgecolor=BLACK, linewidth=1.0, zorder=2)
    ax.errorbar(x, med_dd, yerr=err_dd, fmt="none", ecolor=BLACK, elinewidth=1.2, capsize=3, zorder=4)
    jitter = [-0.14, 0.0, 0.14]
    for xi, target in zip(x, targets):
        for i, r in enumerate(groups[target]):
            ax.scatter(
                xi + jitter[i % 3],
                float(r["delta_d"]),
                s=42,
                color=[BLACK, RED, BLUE][i % 3],
                edgecolor="white",
                linewidth=0.6,
                zorder=5,
            )
        ax.text(
            xi,
            med_dd[xi] + err_dd[xi] + 0.017,
            f"+{med_dd[xi]:.2f}",
            ha="center",
            va="bottom",
            fontsize=8,
            color=BLACK,
        )
    ax.axhline(0.10, color=GRAY, lw=1.0, ls="--")
    ax.text(
        -0.42,
        0.103,
        "0.10 mm gate",
        ha="left",
        va="bottom",
        fontsize=8,
        color="#666666",
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.75, pad=1.0),
    )
    ax.set_title("Matched force creates displacement separation", fontsize=12, pad=8)
    ax.set_xlabel("target F (N)")
    ax.set_ylabel("d_unloading - d_loading (mm)")
    ax.set_xticks(x, [f"{t:g}" for t in targets])
    ax.set_ylim(0, max(0.19, max(med_dd) + max(err_dd) + 0.035))
    style_grid(ax)
    return fig


def panel_magnetic_strength(rows: list[dict[str, object]], ax: mpl.axes.Axes | None = None) -> mpl.figure.Figure:
    created = ax is None
    if created:
        fig, ax = plt.subplots(figsize=(5.2, 3.6))
    else:
        fig = ax.figure
    groups = grouped(rows)
    targets = list(groups)
    jitter = [-0.018, 0.0, 0.018]
    for target in targets:
        for i, r in enumerate(groups[target]):
            ax.scatter(
                target + jitter[i % 3],
                float(r["delta_Bvec"]),
                s=34,
                color=[BLACK, RED, BLUE][i % 3],
                edgecolor="white",
                linewidth=0.4,
                zorder=3,
            )
    meds = [median(float(r["delta_Bvec"]) for r in groups[t]) for t in targets]
    errs = [sem([float(r["delta_Bvec"]) for r in groups[t]]) for t in targets]
    ax.errorbar(targets, meds, yerr=errs, color=BLACK, lw=1.8, marker="o", ms=4, capsize=3, zorder=4)
    ax.axhline(100, color=GRAY, lw=1.0, ls=":")
    ax.text(min(targets), 105, "100 uT reference", ha="left", va="bottom", color="#666666", fontsize=8)
    ax.set_title("Magnetic separation remains strong at matched force", fontsize=12, pad=8)
    ax.set_xlabel("target F (N)")
    ax.set_ylabel("ΔBvec (uT)")
    ax.set_xlim(min(targets) - 0.22, max(targets) + 0.22)
    style_grid(ax)
    return fig


def panel_axis_heatmap(rows: list[dict[str, object]], ax: mpl.axes.Axes | None = None) -> mpl.figure.Figure:
    created = ax is None
    if created:
        fig, ax = plt.subplots(figsize=(6.4, 3.4))
    else:
        fig = ax.figure
    groups = grouped(rows)
    targets = list(groups)
    components = ["delta_Bx", "delta_By", "delta_Bz"]
    labels = ["ΔBx", "ΔBy", "ΔBz"]
    data = np.array([[median(float(r[c]) for r in groups[t]) for t in targets] for c in components])
    vmax = max(230, float(np.max(np.abs(data))))
    im = ax.imshow(data, aspect="auto", cmap="RdBu_r", vmin=-vmax, vmax=vmax)
    ax.set_xticks(range(len(targets)), [f"{t:g}" for t in targets])
    ax.set_yticks(range(len(labels)), labels)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            color = "white" if abs(data[i, j]) > 0.55 * vmax else BLACK
            ax.text(j, i, f"{data[i, j]:+.0f}", ha="center", va="center", color=color, fontsize=9)
    ax.set_xlabel("target F (N)")
    ax.set_title("Three-axis magnetic signature of same-F path excitation", fontsize=12, pad=8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks(np.arange(-0.5, len(targets), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(labels), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.tick_params(which="minor", bottom=False, left=False)
    if created:
        cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.03)
        cbar.set_label("ΔB component (uT)")
    else:
        cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.03)
        cbar.set_label("uT")
    return fig


def panel_decision_map(rows: list[dict[str, object]], ax: mpl.axes.Axes | None = None) -> mpl.figure.Figure:
    created = ax is None
    if created:
        fig, ax = plt.subplots(figsize=(5.0, 3.8))
    else:
        fig = ax.figure
    groups = grouped(rows)
    targets = list(groups)
    xs = [median(abs(float(r["delta_d"])) for r in groups[t]) for t in targets]
    ys = [median(float(r["delta_Bvec"]) for r in groups[t]) for t in targets]
    ax.plot(xs, ys, color=GRAY, lw=1.4, zorder=1)
    for t, x, y in zip(targets, xs, ys):
        selected = t in {3.75, 4.30}
        ax.scatter(
            x,
            y,
            s=110 if selected else 82,
            color=RED if selected else "white",
            edgecolor=RED if selected else BLACK,
            linewidth=1.7,
            zorder=3,
        )
        ax.text(x + 0.003, y + 8, f"{t:g}", color=RED if selected else BLACK, fontsize=9)
    ax.axhline(100, color=GRAY, lw=1.0, ls=":")
    ax.axvline(0.10, color=GRAY, lw=1.0, ls=":")
    ax.annotate(
        "candidate work zone",
        xy=(xs[targets.index(3.75)], ys[targets.index(3.75)]),
        xytext=(0.145, max(ys) + 30),
        arrowprops=dict(arrowstyle="-", lw=1.2, color=RED),
        color=RED,
        ha="left",
    )
    ax.set_title("Work-zone selection from displacement and magnetic separation", fontsize=12, pad=8)
    ax.set_xlabel("median |Δd| (mm)")
    ax.set_ylabel("median ΔBvec (uT)")
    ax.set_xlim(0.095, max(xs) + 0.02)
    ax.set_ylim(80, max(ys) + 70)
    ax.grid(color="#e8e8e8", linewidth=0.8)
    return fig


def make_combined(rows: list[dict[str, object]]) -> mpl.figure.Figure:
    fig = plt.figure(figsize=(11.2, 8.3))
    gs = fig.add_gridspec(2, 2, hspace=0.50, wspace=0.32)
    axes = [
        fig.add_subplot(gs[0, 0]),
        fig.add_subplot(gs[0, 1]),
        fig.add_subplot(gs[1, 0]),
        fig.add_subplot(gs[1, 1]),
    ]
    panel_force_match(rows, axes[0])
    panel_displacement_split(rows, axes[1])
    panel_magnetic_strength(rows, axes[2])
    panel_axis_heatmap(rows, axes[3])
    labels = list("abcd")
    for label, ax in zip(labels, axes):
        ax.text(-0.13, 1.08, label, transform=ax.transAxes, fontsize=16, fontweight="bold", va="top")
    fig.suptitle(
        "Experiment 3.2: matched-force active path pairs separate displacement and magnetic states",
        x=0.02,
        ha="left",
        fontsize=16,
        fontweight="bold",
    )
    fig.text(
        0.02,
        0.955,
        "Formal accepted data: target F = 1.50-4.90 N; three usable path-pairs per point",
        ha="left",
        va="top",
        color="#555555",
        fontsize=10,
    )
    return fig


def main() -> None:
    rows = load_formal_rows()
    csv_out = save_csv(rows)
    outputs = [csv_out]

    panel_specs = [
        ("experiment_3_2_v2_1_force_matching_quality", panel_force_match),
        ("experiment_3_2_v2_2_displacement_split_delta", panel_displacement_split),
        ("experiment_3_2_v2_3_magnetic_separation_strength", panel_magnetic_strength),
        ("experiment_3_2_v2_4_axis_signature_map", panel_axis_heatmap),
    ]
    for stem, func in panel_specs:
        fig = func(rows)
        outputs.append(save_fig(fig, stem))

    fig = make_combined(rows)
    outputs.append(save_fig(fig, "experiment_3_2_v2_complete_same_f_different_d_figure"))

    print("Generated:")
    for out in outputs:
        print(f"  {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
