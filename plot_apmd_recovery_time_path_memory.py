from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from statistics import median, pstdev

import matplotlib

matplotlib.use("Agg")
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "decouple_data"
REPORT_DIR = ROOT / "reports"

SESSION = DATA_DIR / "session_20260614_201905"
SUMMARY_CSV = SESSION / "recovery_time_path_memory_3p5A_pair_summary.csv"

OUT_REPLICATES = REPORT_DIR / "experiment_3_5A_recovery_time_path_memory_replicates.csv"
OUT_SUMMARY = REPORT_DIR / "experiment_3_5A_recovery_time_path_memory_summary.csv"
OUT_MD = REPORT_DIR / "experiment_3_5A_recovery_time_path_memory_tables.md"
OUT_COMPLETE = REPORT_DIR / "experiment_3_5A_recovery_time_path_memory_complete.png"

OUT_PANEL_A = REPORT_DIR / "experiment_3_5A_recovery_time_path_memory_1_force_states.png"
OUT_PANEL_B = REPORT_DIR / "experiment_3_5A_recovery_time_path_memory_2_force_split_decay.png"
OUT_PANEL_C = REPORT_DIR / "experiment_3_5A_recovery_time_path_memory_3_bvec_decay.png"
OUT_PANEL_D = REPORT_DIR / "experiment_3_5A_recovery_time_path_memory_4_decision_plane.png"
OUT_PANEL_E = REPORT_DIR / "experiment_3_5A_recovery_time_path_memory_5_axis_signature.png"
OUT_HEATMAP = REPORT_DIR / "experiment_3_5A_recovery_time_path_memory_axis_heatmap.png"

SESSION_FIG = SESSION / "recovery_time_path_memory_3p5A.png"
SESSION_SUMMARY = SESSION / "recovery_time_path_memory_3p5A_recovery_summary.csv"

BLACK = "#222222"
RED = "#bf3f3f"
BLUE = "#2f84c5"
GRAY = "#777777"
GRID = "#e8e8e8"
HIGHLIGHT = "#f3efe4"
REP_COLORS = {1: "#000000", 2: "#d62728", 3: "#1f77b4"}
AXIS_COLORS = {"dBx": BLACK, "dBy": RED, "dBz": BLUE}

FORCE_SPLIT_GATE_N = 0.20
B_SIGNAL_GATE_UT = 50.0


def apply_style() -> None:
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


def fnum(row: dict[str, str], key: str) -> float:
    return float(row[key])


def load_rows() -> list[dict[str, object]]:
    if not SUMMARY_CSV.exists():
        raise FileNotFoundError(SUMMARY_CSV)

    rows: list[dict[str, object]] = []
    with SUMMARY_CSV.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rec = {
                "session_id": row["session_id"],
                "trial": int(row["trial"]),
                "pair_id": int(row["pair_id"]),
                "target_label": row["target_label"],
                "d_target_mm": fnum(row, "d_target_mm"),
                "d_preload_mm": fnum(row, "d_preload_mm"),
                "preload_hold_s": fnum(row, "preload_hold_s"),
                "recovery_s": fnum(row, "recovery_s"),
                "d_direct_mm": fnum(row, "d_direct_mm"),
                "d_return_mm": fnum(row, "d_return_mm"),
                "d_diff_mm": fnum(row, "d_diff_mm"),
                "abs_d_diff_mm": abs(fnum(row, "d_diff_mm")),
                "F_direct_N": fnum(row, "F_direct_N"),
                "F_return_N": fnum(row, "F_return_N"),
                "delta_F_N": fnum(row, "delta_F_N"),
                "abs_delta_F_N": abs(fnum(row, "delta_F_N")),
                "abs_delta_F_mN": abs(fnum(row, "delta_F_N")) * 1000.0,
                "Bmag_direct_uT": fnum(row, "Bmag_direct_uT"),
                "Bmag_return_uT": fnum(row, "Bmag_return_uT"),
                "delta_Bmag_uT": fnum(row, "delta_Bmag_uT"),
                "delta_Bx_uT": fnum(row, "delta_Bx_uT"),
                "delta_By_uT": fnum(row, "delta_By_uT"),
                "delta_Bz_uT": fnum(row, "delta_Bz_uT"),
                "delta_Bvec_uT": fnum(row, "delta_Bvec_uT"),
                "same_d_ok": int(row["same_d_ok"]),
                "force_split_ok": int(row["force_split_ok"]),
                "b_signal_ok": int(row["b_signal_ok"]),
                "verdict": row["verdict"],
            }
            rows.append(rec)
    rows.sort(key=lambda r: (float(r["recovery_s"]), int(r["trial"])))
    return rows


def group_by_recovery(rows: list[dict[str, object]]) -> dict[float, list[dict[str, object]]]:
    grouped: dict[float, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[float(row["recovery_s"])].append(row)
    return {k: sorted(v, key=lambda r: int(r["trial"])) for k, v in sorted(grouped.items())}


def row_values(rows: list[dict[str, object]], key: str) -> list[float]:
    return [float(r[key]) for r in rows]


def row_median(rows: list[dict[str, object]], key: str) -> float:
    return float(median(row_values(rows, key)))


def row_std(rows: list[dict[str, object]], key: str) -> float:
    values = row_values(rows, key)
    return float(pstdev(values)) if len(values) > 1 else 0.0


def build_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    summary: list[dict[str, object]] = []
    for recovery_s, group in group_by_recovery(rows).items():
        median_bvec = row_median(group, "delta_Bvec_uT")
        median_abs_f = row_median(group, "abs_delta_F_N")
        summary.append(
            {
                "recovery_s": recovery_s,
                "n": len(group),
                "strong_count": sum(1 for r in group if r["verdict"] == "strong"),
                "same_d_count": sum(int(r["same_d_ok"]) for r in group),
                "force_split_count": sum(int(r["force_split_ok"]) for r in group),
                "b_signal_count": sum(int(r["b_signal_ok"]) for r in group),
                "median_abs_d_diff_mm": row_median(group, "abs_d_diff_mm"),
                "median_F_direct_N": row_median(group, "F_direct_N"),
                "median_F_return_N": row_median(group, "F_return_N"),
                "median_delta_F_N": row_median(group, "delta_F_N"),
                "median_abs_delta_F_N": median_abs_f,
                "median_abs_delta_F_mN": median_abs_f * 1000.0,
                "std_abs_delta_F_mN": row_std(group, "abs_delta_F_mN"),
                "median_delta_Bmag_uT": row_median(group, "delta_Bmag_uT"),
                "median_delta_Bx_uT": row_median(group, "delta_Bx_uT"),
                "median_delta_By_uT": row_median(group, "delta_By_uT"),
                "median_delta_Bz_uT": row_median(group, "delta_Bz_uT"),
                "median_delta_Bvec_uT": median_bvec,
                "std_delta_Bvec_uT": row_std(group, "delta_Bvec_uT"),
                "median_Bvec_per_absF_uT_per_N": median_bvec / median_abs_f,
            }
        )
    return summary


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def style_axis(ax: plt.Axes) -> None:
    ax.grid(axis="y", color=GRID, linewidth=0.75)
    ax.set_axisbelow(True)


def panel_label(ax: plt.Axes, label: str) -> None:
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


def jitter(row: dict[str, object], scale: float = 5.0) -> float:
    return {1: -scale, 2: 0.0, 3: scale}[int(row["trial"])]


def recoveries(groups: dict[float, list[dict[str, object]]]) -> np.ndarray:
    return np.array(list(groups.keys()), dtype=float)


def metric_arrays(groups: dict[float, list[dict[str, object]]], key: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xs = recoveries(groups)
    med = np.array([row_median(groups[x], key) for x in xs], dtype=float)
    low = np.array([min(row_values(groups[x], key)) for x in xs], dtype=float)
    high = np.array([max(row_values(groups[x], key)) for x in xs], dtype=float)
    return med, low, high


def plot_force_states(ax: plt.Axes, rows: list[dict[str, object]]) -> None:
    groups = group_by_recovery(rows)
    xs = recoveries(groups)
    direct = np.array([row_median(groups[x], "F_direct_N") for x in xs], dtype=float)
    ret = np.array([row_median(groups[x], "F_return_N") for x in xs], dtype=float)

    ax.plot(xs, direct, "-o", color=BLACK, lw=2.0, ms=6, label="direct loading")
    ax.plot(
        xs,
        ret,
        "--o",
        color=BLACK,
        lw=1.8,
        ms=6,
        markerfacecolor="white",
        label="return unloading",
    )
    for row in rows:
        x = float(row["recovery_s"]) + jitter(row)
        color = REP_COLORS[int(row["trial"])]
        ax.scatter(x, float(row["F_direct_N"]), s=30, color=color, zorder=5)
        ax.scatter(
            x,
            float(row["F_return_N"]),
            s=38,
            facecolors="white",
            edgecolors=color,
            linewidths=1.2,
            zorder=5,
        )

    ax.set_title("Matched-d force states persist after recovery", loc="left", pad=5)
    ax.set_xlabel("recovery time before pair (s)")
    ax.set_ylabel("F at target d (N)")
    ax.set_xticks(xs, [f"{int(x)}" for x in xs])
    ax.set_ylim(float(np.min(ret)) - 0.35, float(np.max(direct)) + 0.55)
    ax.legend(loc="upper right")
    style_axis(ax)


def plot_force_split(ax: plt.Axes, rows: list[dict[str, object]]) -> None:
    groups = group_by_recovery(rows)
    xs = recoveries(groups)
    med, low, high = metric_arrays(groups, "abs_delta_F_N")

    ax.plot(xs, med, "-o", color=BLACK, lw=1.9, ms=6, zorder=4)
    ax.errorbar(xs, med, yerr=[med - low, high - med], fmt="none", ecolor=BLACK, capsize=4, zorder=4)
    for row in rows:
        ax.scatter(
            float(row["recovery_s"]) + jitter(row),
            float(row["abs_delta_F_N"]),
            s=32,
            color=REP_COLORS[int(row["trial"])],
            edgecolors="white",
            linewidth=0.5,
            zorder=5,
        )
    ax.axhline(FORCE_SPLIT_GATE_N, color=GRAY, lw=1.0, ls=":")
    ax.text(xs[0] + 6, FORCE_SPLIT_GATE_N + 0.08, "0.20 N gate", color="#666666", fontsize=8)
    ax.set_title("Force split weakly decays with recovery time", loc="left", pad=5)
    ax.set_xlabel("recovery time before pair (s)")
    ax.set_ylabel("|Delta F| (N)")
    ax.set_xticks(xs, [f"{int(x)}" for x in xs])
    ax.set_ylim(0, float(np.max(high)) + 0.35)
    style_axis(ax)


def plot_bvec(ax: plt.Axes, rows: list[dict[str, object]]) -> None:
    groups = group_by_recovery(rows)
    xs = recoveries(groups)
    med, low, high = metric_arrays(groups, "delta_Bvec_uT")

    ax.plot(xs, med, "-o", color=BLACK, lw=1.9, ms=6, zorder=4)
    ax.errorbar(xs, med, yerr=[med - low, high - med], fmt="none", ecolor=BLACK, capsize=4, zorder=4)
    for row in rows:
        ax.scatter(
            float(row["recovery_s"]) + jitter(row),
            float(row["delta_Bvec_uT"]),
            s=32,
            color=REP_COLORS[int(row["trial"])],
            edgecolors="white",
            linewidth=0.5,
            zorder=5,
        )
    ax.axhline(B_SIGNAL_GATE_UT, color=GRAY, lw=1.0, ls=":")
    ax.text(xs[0] + 6, B_SIGNAL_GATE_UT + 10, "50 uT gate", color="#666666", fontsize=8)
    ax.set_title("Magnetic separation remains far above threshold", loc="left", pad=5)
    ax.set_xlabel("recovery time before pair (s)")
    ax.set_ylabel("Delta Bvec (uT)")
    ax.set_xticks(xs, [f"{int(x)}" for x in xs])
    ax.set_ylim(0, float(np.max(high)) + 45)
    style_axis(ax)


def plot_decision(ax: plt.Axes, summary: list[dict[str, object]]) -> None:
    xs = [float(r["median_abs_delta_F_N"]) for r in summary]
    ys = [float(r["median_delta_Bvec_uT"]) for r in summary]
    labels = [f"{int(float(r['recovery_s']))} s" for r in summary]

    ax.plot(xs, ys, color=GRAY, lw=1.3, zorder=1)
    for x, y, label in zip(xs, ys, labels):
        selected = label == "30 s"
        ax.scatter(
            x,
            y,
            s=96 if selected else 76,
            facecolor=RED if selected else "white",
            edgecolor=RED if selected else BLACK,
            linewidth=1.6,
            zorder=4,
        )
        ax.text(x + 0.008, y + 1.5, label, fontsize=9, color=RED if selected else BLACK)
    label_offsets = {
        "30 s": (0.010, 5.0),
        "120 s": (0.010, -1.5),
        "300 s": (0.010, -7.5),
    }
    ax.set_title("Recovery-time decision plane", loc="left", pad=5)
    ax.set_xlabel("median |Delta F| (N)")
    ax.set_ylabel("median Delta Bvec (uT)")
    for text in list(ax.texts):
        text.remove()
    for x, y, label in zip(xs, ys, labels):
        dx, dy = label_offsets[label]
        ax.text(x + dx, y + dy, label, fontsize=9, color=RED if label == "30 s" else BLACK)
    ax.text(
        0.02,
        0.08,
        "gates: |Delta F| >= 0.20 N, Delta Bvec >= 50 uT",
        transform=ax.transAxes,
        fontsize=8,
        color="#666666",
    )
    ax.set_xlim(min(xs) - 0.06, max(xs) + 0.12)
    ax.set_ylim(min(ys) - 18, max(ys) + 25)
    ax.grid(color=GRID, linewidth=0.75)


def axis_matrix(summary: list[dict[str, object]]) -> tuple[np.ndarray, np.ndarray]:
    xs = np.array([float(r["recovery_s"]) for r in summary], dtype=float)
    matrix = np.array(
        [
            [float(r["median_delta_Bx_uT"]) for r in summary],
            [float(r["median_delta_By_uT"]) for r in summary],
            [float(r["median_delta_Bz_uT"]) for r in summary],
        ],
        dtype=float,
    )
    return xs, matrix


def plot_axis_signature(ax: plt.Axes, summary: list[dict[str, object]]) -> None:
    xs, matrix = axis_matrix(summary)
    x = np.arange(len(xs))
    width = 0.24
    for offset, row, color, label in [
        (-width, matrix[0], AXIS_COLORS["dBx"], "dBx"),
        (0.0, matrix[1], AXIS_COLORS["dBy"], "dBy"),
        (width, matrix[2], AXIS_COLORS["dBz"], "dBz"),
    ]:
        ax.bar(x + offset, row, width=width * 0.88, color=color, alpha=0.90, label=label, zorder=3)
    ax.axhline(0, color=GRAY, lw=1.0)
    ax.set_title("3-axis magnetic signature stays directionally consistent", loc="left", pad=5)
    ax.set_xlabel("recovery time before pair (s)")
    ax.set_ylabel("median Delta B component (uT)")
    ax.set_xticks(x, [f"{int(v)}" for v in xs])
    ax.legend(loc="upper right", ncol=3)
    style_axis(ax)


def plot_axis_heatmap(path: Path, summary: list[dict[str, object]]) -> None:
    xs, matrix = axis_matrix(summary)
    vmax = max(250.0, float(np.max(np.abs(matrix))) * 1.05)
    fig, ax = plt.subplots(figsize=(6.7, 2.8), dpi=260)
    im = ax.imshow(matrix, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_title("Recovery-time 3-axis signature map", fontsize=12, loc="left")
    ax.set_xticks(np.arange(len(xs)), [f"{int(v)}" for v in xs])
    ax.set_yticks(np.arange(3), ["dBx", "dBy", "dBz"])
    ax.set_xlabel("recovery time before pair (s)")
    ax.tick_params(axis="both", length=0)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix[i, j]
            color = "white" if abs(value) > vmax * 0.45 else BLACK
            ax.text(j, i, f"{value:+.0f}", ha="center", va="center", fontsize=9, color=color)
    ax.set_xticks(np.arange(-0.5, len(xs), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, 3, 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.5)
    ax.tick_params(which="minor", bottom=False, left=False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.02)
    cbar.set_label("Delta B component (uT)")
    fig.tight_layout()
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def decorate(fig: plt.Figure) -> None:
    fig.suptitle(
        "Experiment 3.5A: active path memory persists after recovery",
        x=0.03,
        y=0.99,
        ha="left",
        va="top",
        fontsize=16,
        fontweight="bold",
    )
    fig.text(
        0.03,
        0.955,
        "Formal data: target d = 3.40 mm; preload d = 3.80 mm; recovery = 30/120/300 s; three measured pairs per recovery time",
        ha="left",
        va="top",
        fontsize=10,
        color="#555555",
    )


def save(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def save_complete(rows: list[dict[str, object]], summary: list[dict[str, object]]) -> None:
    fig = plt.figure(figsize=(13.2, 8.5), dpi=260)
    gs = fig.add_gridspec(
        2,
        3,
        left=0.07,
        right=0.985,
        top=0.83,
        bottom=0.09,
        wspace=0.36,
        hspace=0.50,
        width_ratios=[1.20, 1.0, 1.0],
    )
    axes = [
        fig.add_subplot(gs[0, :2]),
        fig.add_subplot(gs[0, 2]),
        fig.add_subplot(gs[1, 0]),
        fig.add_subplot(gs[1, 1]),
        fig.add_subplot(gs[1, 2]),
    ]
    plot_force_states(axes[0], rows)
    plot_force_split(axes[1], rows)
    plot_bvec(axes[2], rows)
    plot_decision(axes[3], summary)
    plot_axis_signature(axes[4], summary)
    for label, ax in zip("abcde", axes):
        panel_label(ax, label)
    decorate(fig)
    save(fig, OUT_COMPLETE)
    fig = plt.figure(figsize=(13.2, 8.5), dpi=260)
    gs = fig.add_gridspec(
        2,
        3,
        left=0.07,
        right=0.985,
        top=0.83,
        bottom=0.09,
        wspace=0.36,
        hspace=0.50,
        width_ratios=[1.20, 1.0, 1.0],
    )
    axes = [
        fig.add_subplot(gs[0, :2]),
        fig.add_subplot(gs[0, 2]),
        fig.add_subplot(gs[1, 0]),
        fig.add_subplot(gs[1, 1]),
        fig.add_subplot(gs[1, 2]),
    ]
    plot_force_states(axes[0], rows)
    plot_force_split(axes[1], rows)
    plot_bvec(axes[2], rows)
    plot_decision(axes[3], summary)
    plot_axis_signature(axes[4], summary)
    for label, ax in zip("abcde", axes):
        panel_label(ax, label)
    decorate(fig)
    save(fig, SESSION_FIG)


def save_panels(rows: list[dict[str, object]], summary: list[dict[str, object]]) -> None:
    specs = [
        (OUT_PANEL_A, (8.2, 4.2), lambda ax: plot_force_states(ax, rows), "a"),
        (OUT_PANEL_B, (6.2, 4.0), lambda ax: plot_force_split(ax, rows), "b"),
        (OUT_PANEL_C, (6.2, 4.0), lambda ax: plot_bvec(ax, rows), "c"),
        (OUT_PANEL_D, (6.2, 4.0), lambda ax: plot_decision(ax, summary), "d"),
        (OUT_PANEL_E, (6.2, 4.0), lambda ax: plot_axis_signature(ax, summary), "e"),
    ]
    for path, size, draw, label in specs:
        fig, ax = plt.subplots(figsize=size, dpi=260)
        draw(ax)
        panel_label(ax, label)
        fig.tight_layout()
        save(fig, path)


def markdown_table(rows: list[dict[str, object]], fields: list[str], headers: list[str]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return "\n".join(lines)


def write_markdown(rows: list[dict[str, object]], summary: list[dict[str, object]]) -> None:
    summary_rows = [
        {
            "recovery": f"{int(float(r['recovery_s']))} s",
            "n": int(r["n"]),
            "strong": f"{int(r['strong_count'])}/3",
            "same_d": f"{int(r['same_d_count'])}/3",
            "abs_dF": f"{float(r['median_abs_delta_F_mN']):.1f} mN",
            "dBvec": f"{float(r['median_delta_Bvec_uT']):.1f} uT",
            "dBy": f"{float(r['median_delta_By_uT']):+.1f} uT",
            "dBz": f"{float(r['median_delta_Bz_uT']):+.1f} uT",
        }
        for r in summary
    ]
    rep_rows = [
        {
            "recovery": f"{int(float(r['recovery_s']))} s",
            "rep": r["trial"],
            "d_direct": f"{float(r['d_direct_mm']):.3f}",
            "d_return": f"{float(r['d_return_mm']):.3f}",
            "dF": f"{float(r['delta_F_N']) * 1000:+.1f}",
            "dBvec": f"{float(r['delta_Bvec_uT']):.1f}",
            "verdict": r["verdict"],
        }
        for r in rows
    ]
    text = "\n".join(
        [
            "# Experiment 3.5A recovery-time path-memory tables",
            "",
            "Target d = 3.40 mm. Preload d = 3.80 mm. Preload hold = 30 s.",
            "",
            "## Summary by recovery time",
            "",
            markdown_table(
                summary_rows,
                ["recovery", "n", "strong", "same_d", "abs_dF", "dBvec", "dBy", "dBz"],
                [
                    "Recovery",
                    "n",
                    "Strong",
                    "Same-d",
                    "Median abs Delta F",
                    "Median Delta Bvec",
                    "Median dBy",
                    "Median dBz",
                ],
            ),
            "",
            "## Replicates",
            "",
            markdown_table(
                rep_rows,
                ["recovery", "rep", "d_direct", "d_return", "dF", "dBvec", "verdict"],
                [
                    "Recovery",
                    "Rep",
                    "d direct (mm)",
                    "d return (mm)",
                    "Delta F (mN)",
                    "Delta Bvec (uT)",
                    "Verdict",
                ],
            ),
            "",
        ]
    )
    OUT_MD.write_text(text, encoding="utf-8")


def main() -> None:
    apply_style()
    REPORT_DIR.mkdir(exist_ok=True)
    rows = load_rows()
    summary = build_summary(rows)

    replicate_fields = [
        "session_id",
        "trial",
        "pair_id",
        "target_label",
        "d_target_mm",
        "d_preload_mm",
        "preload_hold_s",
        "recovery_s",
        "d_direct_mm",
        "d_return_mm",
        "d_diff_mm",
        "abs_d_diff_mm",
        "F_direct_N",
        "F_return_N",
        "delta_F_N",
        "abs_delta_F_N",
        "abs_delta_F_mN",
        "Bmag_direct_uT",
        "Bmag_return_uT",
        "delta_Bmag_uT",
        "delta_Bx_uT",
        "delta_By_uT",
        "delta_Bz_uT",
        "delta_Bvec_uT",
        "same_d_ok",
        "force_split_ok",
        "b_signal_ok",
        "verdict",
    ]
    summary_fields = [
        "recovery_s",
        "n",
        "strong_count",
        "same_d_count",
        "force_split_count",
        "b_signal_count",
        "median_abs_d_diff_mm",
        "median_F_direct_N",
        "median_F_return_N",
        "median_delta_F_N",
        "median_abs_delta_F_N",
        "median_abs_delta_F_mN",
        "std_abs_delta_F_mN",
        "median_delta_Bmag_uT",
        "median_delta_Bx_uT",
        "median_delta_By_uT",
        "median_delta_Bz_uT",
        "median_delta_Bvec_uT",
        "std_delta_Bvec_uT",
        "median_Bvec_per_absF_uT_per_N",
    ]
    write_csv(OUT_REPLICATES, rows, replicate_fields)
    write_csv(OUT_SUMMARY, summary, summary_fields)
    write_csv(SESSION_SUMMARY, summary, summary_fields)
    write_markdown(rows, summary)
    save_complete(rows, summary)
    save_panels(rows, summary)
    plot_axis_heatmap(OUT_HEATMAP, summary)

    print("Generated:")
    for path in [
        OUT_REPLICATES,
        OUT_SUMMARY,
        OUT_MD,
        OUT_COMPLETE,
        OUT_PANEL_A,
        OUT_PANEL_B,
        OUT_PANEL_C,
        OUT_PANEL_D,
        OUT_PANEL_E,
        OUT_HEATMAP,
        SESSION_FIG,
        SESSION_SUMMARY,
    ]:
        print(f"  {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
