"""Plot Stage J+ same-F / different-d path-decoupling diagnostics.

The figure is organized around the experimental claim, not around the force
axis: after a preload path, the unloading state returns to nearly the same
force but lands at a different displacement and a strongly different magnetic
state.

PNG figure is written next to the session data:

  decouple_data/session_*/Jplus_same_f_diff_d.png
"""

import csv
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


HERE = Path(__file__).parent
OUTPUT_ROOT = HERE / "decouple_data"

SUMMARY_WINDOW_S = 5.0
FORCE_MATCH_TOL_N = 0.100
MIN_D_SPLIT_MM = 0.10
DYNAMIC_B_SIGNAL_UT = 12.5

PNG_DPI = 300

PALETTE = {
    "blue": "#0F4D92",
    "teal": "#42949E",
    "red": "#B64342",
    "green": "#2E9E44",
    "gold": "#D9A441",
    "purple": "#7F63B8",
    "brown": "#8C5A4A",
    "gray_light": "#D8D8D8",
    "gray": "#767676",
    "gray_dark": "#4D4D4D",
    "black": "#272727",
    "pass_fill": "#DCECDF",
    "fail_fill": "#F3D6D4",
}

AXIS_COLORS = {
    "Bx": PALETTE["black"],
    "By": PALETTE["red"],
    "Bz": PALETTE["blue"],
}

TRIAL_COLORS = [PALETTE["black"], PALETTE["red"], PALETTE["blue"]]


def apply_style():
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "DejaVu Sans", "Liberation Sans"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 7,
            "axes.titlesize": 7,
            "axes.labelsize": 7,
            "xtick.labelsize": 6,
            "ytick.labelsize": 6,
            "legend.fontsize": 6,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
            "lines.linewidth": 1.15,
            "lines.markersize": 3.8,
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


def find_latest_stage_j_plus():
    for session in sorted(OUTPUT_ROOT.glob("session_*"), reverse=True):
        if (session / "Jplus_pair_summary.csv").exists():
            return session
    return None


def setup_axis(ax, title=None, xlabel=None, ylabel=None):
    if title:
        ax.set_title(title, loc="left", pad=3)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.grid(False)
    ax.tick_params(direction="out")


def add_panel(ax, label, title=None):
    ax.text(
        -0.13,
        1.06,
        label,
        transform=ax.transAxes,
        fontsize=9,
        fontweight="bold",
        va="bottom",
        ha="left",
    )
    if title:
        ax.set_title(title, loc="left", pad=3)


def add_stage_header(fig, text):
    fig.text(
        0.01,
        0.992,
        text,
        va="top",
        ha="left",
        fontsize=7,
        color=PALETTE["gray_dark"],
    )


def export_figure_set(fig, output_dir, basename):
    output_dir.mkdir(parents=True, exist_ok=True)
    path = (output_dir / basename).with_suffix(".png")
    fig.savefig(path, dpi=PNG_DPI, bbox_inches="tight", facecolor="white")
    return [path]


def median_or_nan(values):
    clean = [v for v in values if np.isfinite(v)]
    return float(np.median(clean)) if len(clean) else float("nan")


def read_pair_summary(session):
    path = session / "Jplus_pair_summary.csv"
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    "trial": int(r["trial"]),
                    "target_label": r["target_label"],
                    "F_target_N": safe_float(r["F_target_N"]),
                    "F_loading_N": safe_float(r["F_loading_N"]),
                    "F_unloading_N": safe_float(r["F_unloading_N"]),
                    "delta_F_N": safe_float(r["delta_F_N"]),
                    "d_loading_mm": safe_float(r["d_loading_mm"]),
                    "d_unloading_mm": safe_float(r["d_unloading_mm"]),
                    "delta_d_mm": safe_float(r["delta_d_mm"]),
                    "Bmag_loading_uT": safe_float(r["Bmag_loading_uT"]),
                    "Bmag_unloading_uT": safe_float(r["Bmag_unloading_uT"]),
                    "delta_Bmag_uT": safe_float(r["delta_Bmag_uT"]),
                    "delta_Bx_uT": safe_float(r["delta_Bx_uT"]),
                    "delta_By_uT": safe_float(r["delta_By_uT"]),
                    "delta_Bz_uT": safe_float(r["delta_Bz_uT"]),
                    "delta_Bvec_uT": safe_float(r["delta_Bvec_uT"]),
                    "slope_Bmag_uT_per_mm": safe_float(
                        r["slope_Bmag_uT_per_mm"]
                    ),
                    "same_F_ok": r["same_F_ok"] == "1",
                    "disp_split_ok": r["disp_split_ok"] == "1",
                    "b_signal_ok": r["b_signal_ok"] == "1",
                    "verdict": r["verdict"],
                }
            )
    return rows


def summarize_state(rows, state_label):
    state_rows = [r for r in rows if r["state_label"] == state_label]
    if not state_rows:
        return None
    t0 = min(safe_float(r["t_rel_s"]) for r in state_rows)
    window = [
        r for r in state_rows
        if safe_float(r["t_rel_s"]) <= t0 + SUMMARY_WINDOW_S
    ]
    if not window:
        window = state_rows
    return {
        "F_N": median_or_nan([safe_float(r["F_N"]) for r in window]),
        "d_mm": median_or_nan([safe_float(r["d_actual_mm"]) for r in window]),
        "Bmag_uT": median_or_nan([safe_float(r["Bmag_uT"]) for r in window]),
        "Bx_uT": median_or_nan([safe_float(r["Bx_uT"]) for r in window]),
        "By_uT": median_or_nan([safe_float(r["By_uT"]) for r in window]),
        "Bz_uT": median_or_nan([safe_float(r["Bz_uT"]) for r in window]),
        "n": len(window),
    }


def read_path_states(session, summary_rows):
    states = {}
    for row in summary_rows:
        trial = row["trial"]
        path = session / f"Jplus_same_F_{row['target_label']}_rep{trial}.csv"
        with path.open(newline="", encoding="utf-8") as f:
            raw_rows = list(csv.DictReader(f))
        states[trial] = {
            "loading": summarize_state(raw_rows, "loading_target"),
            "preload": summarize_state(raw_rows, "preload_deep"),
            "unloading": summarize_state(raw_rows, "unloading_target"),
        }
    return states


def row_labels(rows):
    return [f"rep {r['trial']}" for r in rows]


def plot_displacement_split(ax, rows, labels, x):
    x = np.asarray(x, dtype=float)
    offset = 0.16
    loading_d = np.array([r["d_loading_mm"] for r in rows], dtype=float)
    unloading_d = np.array([r["d_unloading_mm"] for r in rows], dtype=float)
    delta_d = unloading_d - loading_d

    for i, (xi, dl, du, dd) in enumerate(zip(x, loading_d, unloading_d, delta_d)):
        color = TRIAL_COLORS[i % len(TRIAL_COLORS)]
        ax.plot(
            [xi - offset, xi + offset],
            [dl, du],
            color=color,
            lw=1.0,
            zorder=1,
        )
        ax.scatter(
            xi - offset,
            dl,
            s=34,
            color=color,
            edgecolor="white",
            linewidth=0.45,
            zorder=3,
            label="loading" if i == 0 else None,
        )
        ax.scatter(
            xi + offset,
            du,
            s=34,
            facecolor="white",
            edgecolor=color,
            linewidth=1.0,
            zorder=3,
            label="unloading" if i == 0 else None,
        )
        ax.text(
            xi + 0.03,
            max(dl, du) + 0.014,
            f"+{dd:.3f} mm",
            ha="center",
            va="bottom",
            fontsize=6,
            color=color,
        )

    finite = np.r_[loading_d[np.isfinite(loading_d)], unloading_d[np.isfinite(unloading_d)]]
    ymin = float(np.min(finite)) - 0.045
    ymax = float(np.max(finite)) + 0.075
    ax.set_ylim(ymin, ymax)
    ax.set_xlim(-0.45, len(rows) - 0.55)
    ax.set_xticks(x, labels)
    ax.yaxis.grid(True, color="#E5E5E5", linewidth=0.55)
    setup_axis(ax, None, "repeat at matched F", "d at matched force (mm)")
    add_panel(ax, "a", "Matched-force displacement split")
    ax.legend(loc="upper left", borderaxespad=0.2, labelspacing=0.25)


def plot_gate_table(ax, rows):
    n = len(rows)
    col_x = np.arange(n, dtype=float) + 0.78
    gate_x = col_x[-1] + 1.1
    metrics = [
        {
            "label": "|delta F|",
            "unit": "mN",
            "threshold": f"<= {FORCE_MATCH_TOL_N * 1000:.0f}",
            "values": [abs(r["delta_F_N"]) * 1000 for r in rows],
            "ok": [r["same_F_ok"] for r in rows],
            "fmt": "{:.0f}",
        },
        {
            "label": "delta d",
            "unit": "mm",
            "threshold": f">= {MIN_D_SPLIT_MM:.2f}",
            "values": [r["delta_d_mm"] for r in rows],
            "ok": [r["disp_split_ok"] for r in rows],
            "fmt": "{:.3f}",
        },
        {
            "label": "|delta B|",
            "unit": "uT",
            "threshold": f">= {DYNAMIC_B_SIGNAL_UT:.1f}",
            "values": [r["delta_Bvec_uT"] for r in rows],
            "ok": [r["b_signal_ok"] for r in rows],
            "fmt": "{:.0f}",
        },
    ]

    ax.set_xlim(-1.25, gate_x + 0.72)
    ax.set_ylim(len(metrics) - 0.45, -0.9)
    ax.axis("off")

    for xi, row in zip(col_x, rows):
        ax.text(
            xi,
            -0.62,
            f"rep {row['trial']}",
            ha="center",
            va="center",
            fontsize=6,
            color=PALETTE["gray_dark"],
        )
    ax.text(
        gate_x,
        -0.62,
        "gate",
        ha="left",
        va="center",
        fontsize=6,
        color=PALETTE["gray_dark"],
    )

    for j, metric in enumerate(metrics):
        ax.text(
            -1.18,
            j,
            f"{metric['label']}\n({metric['unit']})",
            ha="left",
            va="center",
            fontsize=6,
            color=PALETTE["black"],
        )
        ax.text(
            gate_x,
            j,
            metric["threshold"],
            ha="left",
            va="center",
            fontsize=6,
            color=PALETTE["gray_dark"],
        )
        for xi, value, ok in zip(col_x, metric["values"], metric["ok"]):
            fill = PALETTE["pass_fill"] if ok else PALETTE["fail_fill"]
            ax.add_patch(
                Rectangle(
                    (xi - 0.36, j - 0.36),
                    0.72,
                    0.72,
                    facecolor=fill,
                    edgecolor="white",
                    linewidth=0.8,
                )
            )
            ax.text(
                xi,
                j,
                metric["fmt"].format(value),
                ha="center",
                va="center",
                fontsize=6.2,
                color=PALETTE["black"],
            )

    strong = sum(r["verdict"] == "strong" for r in rows)
    ax.text(
        -1.18,
        len(metrics) - 0.08,
        f"{strong}/{n} pairs meet all gates",
        ha="left",
        va="top",
        fontsize=6,
        color=PALETTE["gray_dark"],
    )
    add_panel(ax, "b", "Same-force decoupling gates")


def plot_axis_components(ax, rows, labels, x):
    comp_width = 0.22
    for offset, key, axis_name in (
        (-comp_width, "delta_Bx_uT", "Bx"),
        (0.0, "delta_By_uT", "By"),
        (comp_width, "delta_Bz_uT", "Bz"),
    ):
        ax.bar(
            x + offset,
            [r[key] for r in rows],
            width=comp_width,
            color=AXIS_COLORS[axis_name],
            label=f"d{axis_name}",
            edgecolor="white",
            linewidth=0.35,
        )
    ax.axhline(0, color=PALETTE["black"], alpha=0.45, linewidth=0.7)
    ax.set_xticks(x, labels)
    setup_axis(ax, None, "repeat", "unloading - loading (uT)")
    add_panel(ax, "c", "3-axis magnetic split at matched force")
    ax.legend(
        handlelength=1.3,
        borderaxespad=0.2,
        labelspacing=0.25,
        loc="upper right",
        ncol=3,
        columnspacing=0.8,
    )


def plot_summary(rows, session):
    apply_style()
    labels = row_labels(rows)
    x = np.arange(len(rows))

    fig = plt.figure(figsize=(7.45, 3.12))
    gs = fig.add_gridspec(1, 3, width_ratios=(1.36, 1.42, 1.32), wspace=0.58)
    axes = [fig.add_subplot(gs[0, i]) for i in range(3)]

    plot_displacement_split(axes[0], rows, labels, x)
    plot_gate_table(axes[1], rows)
    plot_axis_components(axes[2], rows, labels, x)

    add_stage_header(
        fig,
        f"Stage J+ same-F / different-d path probe: {session.name}",
    )
    fig.subplots_adjust(left=0.075, right=0.99, bottom=0.18, top=0.82)
    saved = export_figure_set(fig, session, "Jplus_same_f_diff_d")
    plt.close(fig)
    for path in saved:
        print(f"  -> {path}")


def print_summary(rows):
    print(
        "trial target dF_mN dd_mm dBmag_uT dBvec_uT "
        "slope_Bmag_uT_per_mm verdict"
    )
    for r in rows:
        print(
            f"{r['trial']:5d} {r['F_target_N']:6.3f} "
            f"{r['delta_F_N']*1000:+7.1f} "
            f"{r['delta_d_mm']:+7.3f} "
            f"{r['delta_Bmag_uT']:+9.2f} "
            f"{r['delta_Bvec_uT']:8.2f} "
            f"{r['slope_Bmag_uT_per_mm']:+12.1f} "
            f"{r['verdict']}"
        )

    if not rows:
        return
    dF = np.array([abs(r["delta_F_N"]) for r in rows], dtype=float)
    dd = np.array([abs(r["delta_d_mm"]) for r in rows], dtype=float)
    dB = np.array([r["delta_Bvec_uT"] for r in rows], dtype=float)
    slope = np.array([r["slope_Bmag_uT_per_mm"] for r in rows], dtype=float)
    print()
    print(f"median |delta F|  = {np.nanmedian(dF) * 1000:.1f} mN")
    print(f"median |delta d|  = {np.nanmedian(dd):.3f} mm")
    print(f"median |delta B|  = {np.nanmedian(dB):.1f} uT")
    print(f"median d|B|/dd    = {np.nanmedian(slope):.1f} uT/mm")


def main():
    if len(sys.argv) > 1:
        session = OUTPUT_ROOT / sys.argv[1]
    else:
        session = find_latest_stage_j_plus()

    if session is None or not session.exists():
        print("No Stage J+ session found.")
        return

    rows = read_pair_summary(session)
    print(f"\n=== Stage J+ ===\n  session: {session.name}")
    if not rows:
        print("  (no summary rows found)")
        return

    print_summary(rows)
    plot_summary(rows, session)
    print("\nDone.")


if __name__ == "__main__":
    main()
