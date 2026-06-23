from __future__ import annotations

import csv
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

OUT_REPLICATES = REPORT_DIR / "experiment_3_4B_same_f_path_hold_time_replicates.csv"
OUT_SUMMARY = REPORT_DIR / "experiment_3_4B_same_f_path_hold_time_summary.csv"
OUT_MD = REPORT_DIR / "experiment_3_4B_same_f_path_hold_time_tables.md"
OUT_FIG = REPORT_DIR / "experiment_3_4B_same_f_path_hold_time_complete.png"

OUT_PANEL_A = REPORT_DIR / "experiment_3_4B_same_f_path_hold_time_1_matched_force_displacement.png"
OUT_PANEL_B = REPORT_DIR / "experiment_3_4B_same_f_path_hold_time_2_delta_d_response.png"
OUT_PANEL_C = REPORT_DIR / "experiment_3_4B_same_f_path_hold_time_3_bvec_response.png"
OUT_PANEL_D = REPORT_DIR / "experiment_3_4B_same_f_path_hold_time_4_decision_plane.png"
OUT_PANEL_E = REPORT_DIR / "experiment_3_4B_same_f_path_hold_time_5_axis_signature.png"
OUT_PANEL_HEATMAP = REPORT_DIR / "experiment_3_4B_same_f_path_hold_time_axis_heatmap.png"


TARGET_F_N = 3.75
PRELOAD_EXTRA_MM = 0.40
SAME_F_GATE_N = 0.050
DISP_SPLIT_GATE_MM = 0.100
B_SIGNAL_GATE_UT = 100.0

BLACK = "#222222"
RED = "#c45252"
BLUE = "#3182bd"
GRAY = "#777777"
GRID = "#e8e8e8"
HIGHLIGHT = "#f3efe4"
REP_COLORS = {1: "#000000", 2: "#d62728", 3: "#1f77b4"}
AXIS_COLORS = {"dBx": "#333333", "dBy": "#c45252", "dBz": "#3182bd"}


ACCEPTED_ROWS = [
    {
        "hold_label": "5 s",
        "preload_hold_s": 5.0,
        "formal_rep": 1,
        "session": "session_20260614_142325",
        "summary": "same_f_path_hold_time_B_hold005_pair_summary.csv",
        "trial": 1,
    },
    {
        "hold_label": "5 s",
        "preload_hold_s": 5.0,
        "formal_rep": 2,
        "session": "session_20260614_145304",
        "summary": "same_f_path_hold_time_B_hold005_pair_summary.csv",
        "trial": 1,
    },
    {
        "hold_label": "5 s",
        "preload_hold_s": 5.0,
        "formal_rep": 3,
        "session": "session_20260614_150342",
        "summary": "same_f_path_hold_time_B_hold005_pair_summary.csv",
        "trial": 1,
    },
    {
        "hold_label": "30 s",
        "preload_hold_s": 30.0,
        "formal_rep": 1,
        "session": "session_20260614_171435",
        "summary": "same_f_path_hold_time_B_hold030_pair_summary.csv",
        "trial": 1,
    },
    {
        "hold_label": "30 s",
        "preload_hold_s": 30.0,
        "formal_rep": 2,
        "session": "session_20260614_171435",
        "summary": "same_f_path_hold_time_B_hold030_pair_summary.csv",
        "trial": 2,
    },
    {
        "hold_label": "30 s",
        "preload_hold_s": 30.0,
        "formal_rep": 3,
        "session": "session_20260614_171435",
        "summary": "same_f_path_hold_time_B_hold030_pair_summary.csv",
        "trial": 3,
    },
    {
        "hold_label": "90 s",
        "preload_hold_s": 90.0,
        "formal_rep": 1,
        "session": "session_20260614_175601",
        "summary": "same_f_path_hold_time_B_hold090_pair_summary.csv",
        "trial": 1,
    },
    {
        "hold_label": "90 s",
        "preload_hold_s": 90.0,
        "formal_rep": 2,
        "session": "session_20260614_183107",
        "summary": "same_f_path_hold_time_B_hold090_pair_summary.csv",
        "trial": 1,
    },
    {
        "hold_label": "90 s",
        "preload_hold_s": 90.0,
        "formal_rep": 3,
        "session": "session_20260614_193530",
        "summary": "same_f_path_hold_time_B_hold090_pair_summary.csv",
        "trial": 1,
    },
]


def apply_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
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


def read_summary_row(spec: dict[str, object]) -> dict[str, str]:
    path = DATA_DIR / str(spec["session"]) / str(spec["summary"])
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    matches = [r for r in rows if int(r["trial"]) == int(spec["trial"])]
    if len(matches) != 1:
        raise ValueError(f"Expected one trial {spec['trial']} in {path}, found {len(matches)}")
    return matches[0]


def load_replicates() -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for spec in ACCEPTED_ROWS:
        raw = read_summary_row(spec)
        rec: dict[str, object] = {
            "hold_label": spec["hold_label"],
            "preload_hold_s": spec["preload_hold_s"],
            "formal_rep": spec["formal_rep"],
            "source_session": spec["session"],
            "source_trial": spec["trial"],
            "target_F_N": TARGET_F_N,
            "preload_extra_mm": PRELOAD_EXTRA_MM,
            "original_verdict": raw["verdict"],
            "F_loading_N": fnum(raw, "F_loading_N"),
            "F_unloading_N": fnum(raw, "F_unloading_N"),
            "delta_F_N": fnum(raw, "delta_F_N"),
            "abs_delta_F_mN": abs(fnum(raw, "delta_F_N")) * 1000.0,
            "d_loading_mm": fnum(raw, "d_loading_mm"),
            "d_unloading_mm": fnum(raw, "d_unloading_mm"),
            "delta_d_mm": fnum(raw, "delta_d_mm"),
            "abs_delta_d_mm": abs(fnum(raw, "delta_d_mm")),
            "delta_Bmag_uT": fnum(raw, "delta_Bmag_uT"),
            "delta_Bx_uT": fnum(raw, "delta_Bx_uT"),
            "delta_By_uT": fnum(raw, "delta_By_uT"),
            "delta_Bz_uT": fnum(raw, "delta_Bz_uT"),
            "delta_Bvec_uT": fnum(raw, "delta_Bvec_uT"),
            "same_F_ok": int(abs(fnum(raw, "delta_F_N")) <= SAME_F_GATE_N),
            "disp_split_ok": int(abs(fnum(raw, "delta_d_mm")) >= DISP_SPLIT_GATE_MM),
            "b_signal_ok": int(fnum(raw, "delta_Bvec_uT") >= B_SIGNAL_GATE_UT),
        }
        rec["effective_verdict"] = (
            "formal_strong"
            if rec["same_F_ok"] and rec["disp_split_ok"] and rec["b_signal_ok"]
            else raw["verdict"]
        )
        out.append(rec)
    return out


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    REPORT_DIR.mkdir(exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def group_by_hold(rows: list[dict[str, object]]) -> dict[float, list[dict[str, object]]]:
    grouped: dict[float, list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(float(row["preload_hold_s"]), []).append(row)
    return dict(sorted(grouped.items()))


def row_median(rows: list[dict[str, object]], key: str) -> float:
    return median(float(r[key]) for r in rows)


def row_mean(rows: list[dict[str, object]], key: str) -> float:
    return float(np.mean([float(r[key]) for r in rows]))


def row_std(rows: list[dict[str, object]], key: str) -> float:
    if len(rows) < 2:
        return 0.0
    return pstdev(float(r[key]) for r in rows)


def build_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    summary: list[dict[str, object]] = []
    for hold_s, group in group_by_hold(rows).items():
        summary.append(
            {
                "preload_hold_s": hold_s,
                "n": len(group),
                "median_abs_delta_F_mN": row_median(group, "abs_delta_F_mN"),
                "median_d_loading_mm": row_median(group, "d_loading_mm"),
                "median_d_unloading_mm": row_median(group, "d_unloading_mm"),
                "median_delta_d_mm": row_median(group, "delta_d_mm"),
                "mean_delta_d_mm": row_mean(group, "delta_d_mm"),
                "std_delta_d_mm": row_std(group, "delta_d_mm"),
                "median_delta_Bvec_uT": row_median(group, "delta_Bvec_uT"),
                "mean_delta_Bvec_uT": row_mean(group, "delta_Bvec_uT"),
                "std_delta_Bvec_uT": row_std(group, "delta_Bvec_uT"),
                "median_delta_Bmag_uT": row_median(group, "delta_Bmag_uT"),
                "median_delta_Bx_uT": row_median(group, "delta_Bx_uT"),
                "median_delta_By_uT": row_median(group, "delta_By_uT"),
                "median_delta_Bz_uT": row_median(group, "delta_Bz_uT"),
                "median_Bvec_per_abs_delta_d_uT_per_mm": row_median(group, "delta_Bvec_uT")
                / max(row_median(group, "abs_delta_d_mm"), 1e-12),
                "strong_count": sum(1 for r in group if r["effective_verdict"] == "formal_strong"),
                "same_F_count": sum(int(r["same_F_ok"]) for r in group),
                "disp_split_count": sum(int(r["disp_split_ok"]) for r in group),
                "b_signal_count": sum(int(r["b_signal_ok"]) for r in group),
            }
        )
    return summary


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


def add_nominal_band(ax: plt.Axes) -> None:
    ax.axvspan(20, 45, color=HIGHLIGHT, zorder=0)
    y0, y1 = ax.get_ylim()
    ax.text(
        32.5,
        y0 + 0.86 * (y1 - y0),
        "nominal\n30 s",
        ha="center",
        va="top",
        fontsize=8,
        color="#555555",
    )


def x_jitter(row: dict[str, object]) -> float:
    return {1: -2.5, 2: 0.0, 3: 2.5}[int(row["formal_rep"])]


def plot_displacement_states(ax: plt.Axes, rows: list[dict[str, object]]) -> None:
    groups = group_by_hold(rows)
    holds = np.array(list(groups.keys()), dtype=float)
    loading = np.array([row_median(groups[h], "d_loading_mm") for h in holds])
    unloading = np.array([row_median(groups[h], "d_unloading_mm") for h in holds])

    ax.plot(holds, loading, "-o", color=BLACK, lw=2.0, ms=6, label="loading target")
    ax.plot(
        holds,
        unloading,
        "--o",
        color=BLACK,
        lw=1.8,
        ms=6,
        markerfacecolor="white",
        label="return unloading",
    )
    for row in rows:
        x = float(row["preload_hold_s"]) + x_jitter(row)
        color = REP_COLORS[int(row["formal_rep"])]
        ax.scatter(x, float(row["d_loading_mm"]), s=26, color=color, zorder=5)
        ax.scatter(
            x,
            float(row["d_unloading_mm"]),
            s=34,
            facecolors="white",
            edgecolors=color,
            linewidths=1.1,
            zorder=5,
        )
    ax.set_ylim(min(np.min(loading), np.min(unloading)) - 0.16, max(np.max(loading), np.max(unloading)) + 0.16)
    add_nominal_band(ax)
    ax.set_title("Matched-F displacement states across preload hold time", loc="left", pad=5)
    ax.set_xlabel("preload hold time (s)")
    ax.set_ylabel("d at matched F (mm)")
    ax.set_xticks(holds, [f"{int(h)}" for h in holds])
    ax.legend(loc="upper left")
    style_axis(ax)


def plot_delta_d(ax: plt.Axes, rows: list[dict[str, object]]) -> None:
    groups = group_by_hold(rows)
    holds = np.array(list(groups.keys()), dtype=float)
    med = np.array([row_median(groups[h], "abs_delta_d_mm") for h in holds])
    low = np.array([min(float(r["abs_delta_d_mm"]) for r in groups[h]) for h in holds])
    high = np.array([max(float(r["abs_delta_d_mm"]) for r in groups[h]) for h in holds])

    colors = [BLACK, RED, BLUE]
    ax.bar(holds, med, width=14, color=colors, alpha=0.88, edgecolor="none", zorder=2)
    ax.errorbar(holds, med, yerr=[med - low, high - med], fmt="none", ecolor=BLACK, capsize=4, zorder=4)
    for row in rows:
        ax.scatter(
            float(row["preload_hold_s"]) + x_jitter(row),
            float(row["abs_delta_d_mm"]),
            s=28,
            color=REP_COLORS[int(row["formal_rep"])],
            edgecolors="white",
            linewidth=0.5,
            zorder=5,
        )
    ax.axhline(DISP_SPLIT_GATE_MM, color=GRAY, lw=1.1, ls=":")
    ax.text(holds[0] + 1, DISP_SPLIT_GATE_MM + 0.005, "0.10 mm gate", color="#666666", fontsize=8)
    ax.set_ylim(0, max(high) + 0.05)
    add_nominal_band(ax)
    ax.set_title("Displacement split does not increase monotonically with hold time", loc="left", pad=5)
    ax.set_xlabel("preload hold time (s)")
    ax.set_ylabel("|Delta d| (mm)")
    ax.set_xticks(holds, [f"{int(h)}" for h in holds])
    style_axis(ax)


def plot_bvec(ax: plt.Axes, rows: list[dict[str, object]]) -> None:
    groups = group_by_hold(rows)
    holds = np.array(list(groups.keys()), dtype=float)
    med = np.array([row_median(groups[h], "delta_Bvec_uT") for h in holds])
    low = np.array([min(float(r["delta_Bvec_uT"]) for r in groups[h]) for h in holds])
    high = np.array([max(float(r["delta_Bvec_uT"]) for r in groups[h]) for h in holds])

    ax.plot(holds, med, "-o", color=BLACK, lw=1.9, ms=6, zorder=4)
    ax.errorbar(holds, med, yerr=[med - low, high - med], fmt="none", ecolor=BLACK, capsize=4, zorder=4)
    for row in rows:
        ax.scatter(
            float(row["preload_hold_s"]) + x_jitter(row),
            float(row["delta_Bvec_uT"]),
            s=32,
            color=REP_COLORS[int(row["formal_rep"])],
            edgecolors="white",
            linewidth=0.5,
            zorder=5,
        )
    ax.axhline(B_SIGNAL_GATE_UT, color=GRAY, lw=1.1, ls=":")
    ax.text(holds[0] + 1, B_SIGNAL_GATE_UT + 12, "100 uT gate", color="#666666", fontsize=8)
    ax.set_ylim(80, max(high) + 85)
    add_nominal_band(ax)
    ax.set_title("Magnetic separation remains strong but non-monotonic", loc="left", pad=5)
    ax.set_xlabel("preload hold time (s)")
    ax.set_ylabel("Delta Bvec (uT)")
    ax.set_xticks(holds, [f"{int(h)}" for h in holds])
    style_axis(ax)


def plot_decision(ax: plt.Axes, summary: list[dict[str, object]]) -> None:
    xs = [float(r["median_delta_d_mm"]) for r in summary]
    ys = [float(r["median_delta_Bvec_uT"]) for r in summary]
    labels = [f"{int(float(r['preload_hold_s']))} s" for r in summary]

    ax.plot(xs, ys, color=GRAY, lw=1.4, zorder=1)
    for x, y, label in zip(xs, ys, labels):
        selected = label == "30 s"
        ax.scatter(
            x,
            y,
            s=100 if selected else 78,
            facecolor=RED if selected else "white",
            edgecolor=RED if selected else BLACK,
            linewidth=1.6,
            zorder=4,
        )
        ax.text(x + 0.004, y + 5, label, fontsize=9, color=RED if selected else BLACK)
    ax.axvline(DISP_SPLIT_GATE_MM, color=GRAY, ls=":", lw=1.0)
    ax.axhline(B_SIGNAL_GATE_UT, color=GRAY, ls=":", lw=1.0)
    ax.set_xlim(0.095, max(xs) + 0.035)
    ax.set_ylim(85, max(ys) + 70)
    ax.set_title("Hold-time decision plane", loc="left", pad=5)
    ax.set_xlabel("median |Delta d| (mm)")
    ax.set_ylabel("median Delta Bvec (uT)")
    ax.grid(color=GRID, linewidth=0.75)


def axis_matrix(summary: list[dict[str, object]]) -> tuple[np.ndarray, np.ndarray]:
    holds = np.array([float(r["preload_hold_s"]) for r in summary], dtype=float)
    matrix = np.array(
        [
            [float(r["median_delta_Bx_uT"]) for r in summary],
            [float(r["median_delta_By_uT"]) for r in summary],
            [float(r["median_delta_Bz_uT"]) for r in summary],
        ],
        dtype=float,
    )
    return holds, matrix


def plot_axis_signature(ax: plt.Axes, summary: list[dict[str, object]]) -> None:
    holds, matrix = axis_matrix(summary)
    x = np.arange(len(holds))
    width = 0.24
    for offset, row, color, label in [
        (-width, matrix[0], AXIS_COLORS["dBx"], "dBx"),
        (0.0, matrix[1], AXIS_COLORS["dBy"], "dBy"),
        (width, matrix[2], AXIS_COLORS["dBz"], "dBz"),
    ]:
        ax.bar(x + offset, row, width=width * 0.88, color=color, alpha=0.90, label=label, zorder=3)
    ax.axhline(0, color=GRAY, lw=1.0)
    ax.set_title("3-axis magnetic signature", loc="left", pad=5)
    ax.set_xlabel("preload hold time (s)")
    ax.set_ylabel("median Delta B component (uT)")
    ax.set_xticks(x, [f"{int(h)}" for h in holds])
    ax.legend(loc="upper left", ncol=3)
    style_axis(ax)


def plot_axis_heatmap(path: Path, summary: list[dict[str, object]]) -> None:
    holds, matrix = axis_matrix(summary)
    vmax = max(350.0, float(np.max(np.abs(matrix))) * 1.05)
    fig, ax = plt.subplots(figsize=(7.2, 3.0), dpi=260)
    im = ax.imshow(matrix, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_title("3-axis magnetic signature map", fontsize=12, loc="left")
    ax.set_xticks(np.arange(len(holds)), [f"{int(h)}" for h in holds])
    ax.set_yticks(np.arange(3), ["dBx", "dBy", "dBz"])
    ax.set_xlabel("preload hold time (s)")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix[i, j]
            ax.text(
                j,
                i,
                f"{value:+.0f}",
                ha="center",
                va="center",
                fontsize=9,
                color="white" if abs(value) > vmax * 0.45 else BLACK,
            )
    cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.02)
    cbar.set_label("Delta B component (uT)")
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def decorate(fig: plt.Figure) -> None:
    fig.suptitle(
        "Experiment 3.4B: preload hold time has limited effect at fixed same-F path dose",
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
        "Formal accepted data: target F = 3.75 N; preload extra = +0.40 mm; three accepted path-pairs per hold time",
        ha="left",
        va="top",
        fontsize=10,
        color="#555555",
    )


def save(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def save_complete_figure(rows: list[dict[str, object]], summary: list[dict[str, object]]) -> None:
    fig = plt.figure(figsize=(13.2, 8.4), dpi=260)
    gs = fig.add_gridspec(
        2,
        3,
        left=0.07,
        right=0.985,
        top=0.83,
        bottom=0.09,
        wspace=0.36,
        hspace=0.50,
        width_ratios=[1.15, 1.0, 1.0],
    )
    axes = [
        fig.add_subplot(gs[0, :2]),
        fig.add_subplot(gs[0, 2]),
        fig.add_subplot(gs[1, 0]),
        fig.add_subplot(gs[1, 1]),
        fig.add_subplot(gs[1, 2]),
    ]
    plot_displacement_states(axes[0], rows)
    plot_delta_d(axes[1], rows)
    plot_bvec(axes[2], rows)
    plot_decision(axes[3], summary)
    plot_axis_signature(axes[4], summary)
    for label, ax in zip("abcde", axes):
        panel_label(ax, label)
    decorate(fig)
    save(fig, OUT_FIG)


def save_individual_panels(rows: list[dict[str, object]], summary: list[dict[str, object]]) -> None:
    specs = [
        (OUT_PANEL_A, (8.0, 4.2), lambda ax: plot_displacement_states(ax, rows), "a"),
        (OUT_PANEL_B, (6.4, 4.2), lambda ax: plot_delta_d(ax, rows), "b"),
        (OUT_PANEL_C, (6.4, 4.2), lambda ax: plot_bvec(ax, rows), "c"),
        (OUT_PANEL_D, (6.4, 4.2), lambda ax: plot_decision(ax, summary), "d"),
        (OUT_PANEL_E, (6.4, 4.2), lambda ax: plot_axis_signature(ax, summary), "e"),
    ]
    for path, size, fn, label in specs:
        fig, ax = plt.subplots(figsize=size, dpi=260)
        fn(ax)
        panel_label(ax, label)
        fig.tight_layout()
        save(fig, path)


def markdown_table(rows: list[dict[str, object]], fields: list[str], headers: list[str]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return "\n".join(lines)


def write_markdown(rows: list[dict[str, object]], summary: list[dict[str, object]]) -> None:
    summary_rows = []
    for r in summary:
        summary_rows.append(
            {
                "hold": f"{int(float(r['preload_hold_s']))} s",
                "n": int(r["n"]),
                "d_split": f"{float(r['median_delta_d_mm']):+.3f} mm",
                "dBvec": f"{float(r['median_delta_Bvec_uT']):.1f} uT",
                "dBy": f"{float(r['median_delta_By_uT']):+.1f} uT",
                "dBz": f"{float(r['median_delta_Bz_uT']):+.1f} uT",
                "abs_dF": f"{float(r['median_abs_delta_F_mN']):.1f} mN",
                "strong": f"{int(r['strong_count'])}/3",
            }
        )
    rep_rows = []
    for r in rows:
        rep_rows.append(
            {
                "hold": r["hold_label"],
                "rep": r["formal_rep"],
                "source": f"{r['source_session']} rep{r['source_trial']}",
                "d_load": f"{float(r['d_loading_mm']):.3f}",
                "d_unload": f"{float(r['d_unloading_mm']):.3f}",
                "dd": f"{float(r['delta_d_mm']):+.3f}",
                "dF": f"{float(r['delta_F_N']) * 1000:+.1f}",
                "dBvec": f"{float(r['delta_Bvec_uT']):.1f}",
            }
        )
    text = "\n".join(
        [
            "# Experiment 3.4B same-F preload holding-time tables",
            "",
            "Target F = 3.75 N. Preload extra depth = +0.40 mm. Accepted rows only.",
            "",
            "## Summary by preload hold time",
            "",
            markdown_table(
                summary_rows,
                ["hold", "n", "d_split", "dBvec", "dBy", "dBz", "abs_dF", "strong"],
                [
                    "Preload hold",
                    "n",
                    "Median Delta d",
                    "Median Delta Bvec",
                    "Median dBy",
                    "Median dBz",
                    "Median abs Delta F",
                    "Strong",
                ],
            ),
            "",
            "## Accepted replicate table",
            "",
            markdown_table(
                rep_rows,
                ["hold", "rep", "source", "d_load", "d_unload", "dd", "dF", "dBvec"],
                [
                    "Preload hold",
                    "Formal rep",
                    "Source",
                    "d loading (mm)",
                    "d unloading (mm)",
                    "Delta d (mm)",
                    "Delta F (mN)",
                    "Delta Bvec (uT)",
                ],
            ),
            "",
        ]
    )
    OUT_MD.write_text(text, encoding="utf-8")


def main() -> None:
    apply_style()
    REPORT_DIR.mkdir(exist_ok=True)
    rows = load_replicates()
    summary = build_summary(rows)

    rep_fields = [
        "hold_label",
        "preload_hold_s",
        "formal_rep",
        "source_session",
        "source_trial",
        "target_F_N",
        "preload_extra_mm",
        "original_verdict",
        "effective_verdict",
        "F_loading_N",
        "F_unloading_N",
        "delta_F_N",
        "abs_delta_F_mN",
        "d_loading_mm",
        "d_unloading_mm",
        "delta_d_mm",
        "abs_delta_d_mm",
        "delta_Bmag_uT",
        "delta_Bx_uT",
        "delta_By_uT",
        "delta_Bz_uT",
        "delta_Bvec_uT",
        "same_F_ok",
        "disp_split_ok",
        "b_signal_ok",
    ]
    summary_fields = [
        "preload_hold_s",
        "n",
        "median_abs_delta_F_mN",
        "median_d_loading_mm",
        "median_d_unloading_mm",
        "median_delta_d_mm",
        "mean_delta_d_mm",
        "std_delta_d_mm",
        "median_delta_Bvec_uT",
        "mean_delta_Bvec_uT",
        "std_delta_Bvec_uT",
        "median_delta_Bmag_uT",
        "median_delta_Bx_uT",
        "median_delta_By_uT",
        "median_delta_Bz_uT",
        "median_Bvec_per_abs_delta_d_uT_per_mm",
        "strong_count",
        "same_F_count",
        "disp_split_count",
        "b_signal_count",
    ]
    write_csv(OUT_REPLICATES, rows, rep_fields)
    write_csv(OUT_SUMMARY, summary, summary_fields)
    write_markdown(rows, summary)
    save_complete_figure(rows, summary)
    save_individual_panels(rows, summary)
    plot_axis_heatmap(OUT_PANEL_HEATMAP, summary)

    print("Generated:")
    for path in [
        OUT_REPLICATES,
        OUT_SUMMARY,
        OUT_MD,
        OUT_FIG,
        OUT_PANEL_A,
        OUT_PANEL_B,
        OUT_PANEL_C,
        OUT_PANEL_D,
        OUT_PANEL_E,
        OUT_PANEL_HEATMAP,
    ]:
        print(f"  {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
