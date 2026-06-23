"""Plot APMD same-d / different-F active path-pair diagnostics.

Reads a session containing same_d_different_f_pair_summary.csv and writes the
session-local PNG figure next to the raw data:

  decouple_data/session_*/same_d_different_f_path_pair.png

Historical sessions that still contain Iplus_pair_summary.csv are supported as
a fallback for plotting only.

The key comparison is return_target - direct_target at the same target d.

Figure contract:
Core conclusion: at matched displacement, path history creates a repeatable
force split with a measurable 3-axis magnetic response.
Archetype: quantitative grid.
Backend: Python / matplotlib only.
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

D_MATCH_TOL_MM = 0.020
MIN_FORCE_SPLIT_N = 0.20
DYNAMIC_B_SIGNAL_UT = 50.0

SUMMARY_FILENAMES = (
    "same_d_different_f_pair_summary.csv",
    "same_d_different_f_old_timing_pair_summary.csv",
    "Iplus_pair_summary.csv",
)

FIGURE_BASENAME = "same_d_different_f_path_pair"

PNG_DPI = 300

PALETTE = {
    "blue": "#0F4D92",
    "blue_mid": "#3775BA",
    "teal": "#42949E",
    "red": "#B64342",
    "green": "#2E9E44",
    "gold": "#D9A441",
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

REP_COLORS = {
    1: "#000000",
    2: "#D62728",
    3: "#1F77B4",
}


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


def find_latest_same_d_path_pair():
    for session in sorted(OUTPUT_ROOT.glob("session_*"), reverse=True):
        if any((session / name).exists() for name in SUMMARY_FILENAMES):
            return session
    return None


def read_summary(session):
    path = next(
        (session / name for name in SUMMARY_FILENAMES if (session / name).exists()),
        None,
    )
    if path is None:
        expected = " or ".join(SUMMARY_FILENAMES)
        raise FileNotFoundError(f"No same-d/different-F summary found: {expected}")
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "trial": int(r["trial"]),
                "target_label": r["target_label"],
                "d_target_mm": safe_float(r["d_target_mm"]),
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
                "slope_Bmag_uT_per_N": safe_float(
                    r["slope_Bmag_uT_per_N"]
                ),
                "same_d_ok": r["same_d_ok"] == "1",
                "force_split_ok": r["force_split_ok"] == "1",
                "b_signal_ok": r["b_signal_ok"] == "1",
                "verdict": r["verdict"],
            })
    return rows


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


def row_labels(rows):
    target_values = {r["d_target_mm"] for r in rows if np.isfinite(r["d_target_mm"])}
    if len(target_values) == 1:
        return [f"rep {r['trial']}" for r in rows]
    return [f"{r['target_label']}\nrep {r['trial']}" for r in rows]


def add_value_labels(ax, x, values, fmt, y_offset, color=PALETTE["gray_dark"]):
    for xi, value in zip(x, values):
        if not np.isfinite(value):
            continue
        ax.text(
            xi,
            value + y_offset,
            fmt.format(value),
            ha="center",
            va="bottom" if y_offset >= 0 else "top",
            fontsize=6,
            color=color,
        )


def plot_force_pair(ax, rows, labels, x):
    width = 0.32
    direct = np.array([r["F_direct_N"] for r in rows], dtype=float)
    returned = np.array([r["F_return_N"] for r in rows], dtype=float)
    colors = [REP_COLORS.get(r["trial"], PALETTE["gray_dark"]) for r in rows]

    ax.bar(
        x - width / 2,
        direct,
        width=width,
        label="direct",
        color=colors,
        edgecolor="white",
        linewidth=0.45,
    )
    ax.bar(
        x + width / 2,
        returned,
        width=width,
        label="return",
        color="white",
        hatch="///",
        edgecolor=colors,
        linewidth=0.75,
    )

    for xi, fd, fr, color in zip(x, direct, returned, colors):
        ax.plot(
            [xi - width / 2, xi + width / 2],
            [fd, fr],
            color=color,
            lw=0.75,
            alpha=0.65,
            zorder=3,
        )

    delta_f = (returned - direct) * 1000
    y_offset = 0.04 * np.nanmax([np.nanmax(direct), np.nanmax(returned), 1.0])
    for xi, fd, fr, df in zip(x, direct, returned, delta_f):
        ax.text(
            xi,
            max(fd, fr) + y_offset,
            f"{df:+.0f} mN",
            ha="center",
            va="bottom",
            fontsize=6,
            color=REP_COLORS.get(rows[int(xi)]["trial"], PALETTE["gray_dark"]),
        )

    target_d = np.nanmedian([r["d_target_mm"] for r in rows])
    xlabel = "repeat"
    if np.isfinite(target_d):
        xlabel = f"repeat at target d = {target_d:.2f} mm"
    ax.set_xticks(x, labels)
    ax.set_ylim(0, np.nanmax([np.nanmax(direct), np.nanmax(returned)]) * 1.22)
    setup_axis(ax, None, xlabel, "F (N)")
    add_panel(ax, "a", "Matched-displacement force split")
    ax.legend(handlelength=1.3, borderaxespad=0.2, labelspacing=0.25, loc="upper left")


def plot_gate_table(ax, rows):
    n = len(rows)
    col_x = np.arange(n, dtype=float) + 0.78
    gate_x = col_x[-1] + 1.15
    metrics = [
        {
            "label": "d mismatch",
            "unit": "mm",
            "threshold": f"<= {D_MATCH_TOL_MM:.2f}",
            "values": [abs(r["d_diff_mm"]) for r in rows],
            "ok": [r["same_d_ok"] for r in rows],
            "fmt": "{:.3f}",
        },
        {
            "label": "Force split",
            "unit": "mN",
            "threshold": f">= {MIN_FORCE_SPLIT_N * 1000:.0f}",
            "values": [abs(r["delta_F_N"]) * 1000 for r in rows],
            "ok": [r["force_split_ok"] for r in rows],
            "fmt": "{:.0f}",
        },
        {
            "label": "Vector dB",
            "unit": "uT",
            "threshold": f">= {DYNAMIC_B_SIGNAL_UT:.1f}",
            "values": [r["delta_Bvec_uT"] for r in rows],
            "ok": [r["b_signal_ok"] for r in rows],
            "fmt": "{:.0f}",
        },
    ]

    ax.set_xlim(-1.35, gate_x + 0.75)
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
            -1.28,
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
            text = "nan" if not np.isfinite(value) else metric["fmt"].format(value)
            ax.text(
                xi,
                j,
                text,
                ha="center",
                va="center",
                fontsize=6.2,
                color=PALETTE["black"],
            )

    strong = sum(r["verdict"] == "strong" for r in rows)
    ax.text(
        -1.28,
        len(metrics) - 0.08,
        f"{strong}/{n} pairs meet all gates",
        ha="left",
        va="top",
        fontsize=6,
        color=PALETTE["gray_dark"],
    )
    add_panel(ax, "b", "Live diagnostic gates")


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
    setup_axis(ax, None, "repeat", "return - direct dB (uT)")
    add_panel(ax, "c", "3-axis magnetic response")
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
    gs = fig.add_gridspec(1, 3, width_ratios=(1.22, 1.48, 1.34), wspace=0.58)
    axes = [fig.add_subplot(gs[0, i]) for i in range(3)]

    plot_force_pair(axes[0], rows, labels, x)
    plot_gate_table(axes[1], rows)
    plot_axis_components(axes[2], rows, labels, x)

    add_stage_header(
        fig,
        f"APMD same-d / different-F active path-pair test: {session.name}",
    )
    fig.subplots_adjust(left=0.075, right=0.99, bottom=0.18, top=0.82)
    saved = export_figure_set(fig, session, FIGURE_BASENAME)
    plt.close(fig)
    for path in saved:
        print(f"  -> {path}")


def print_summary(rows):
    print(
        "trial target d_diff_mm dF_mN dBmag_uT dBvec_uT "
        "slope_Bmag_uT_per_N verdict"
    )
    for r in rows:
        print(
            f"{r['trial']:5d} {r['d_target_mm']:6.3f} "
            f"{r['d_diff_mm']:+9.4f} "
            f"{r['delta_F_N']*1000:+7.1f} "
            f"{r['delta_Bmag_uT']:+9.2f} "
            f"{r['delta_Bvec_uT']:8.2f} "
            f"{r['slope_Bmag_uT_per_N']:+12.1f} "
            f"{r['verdict']}"
        )

    if not rows:
        return
    dF = np.array([abs(r["delta_F_N"]) for r in rows], dtype=float)
    dB = np.array([r["delta_Bvec_uT"] for r in rows], dtype=float)
    dd = np.array([abs(r["d_diff_mm"]) for r in rows], dtype=float)
    print()
    print(f"median |d mismatch| = {np.nanmedian(dd):.4f} mm")
    print(f"median |delta F|    = {np.nanmedian(dF) * 1000:.1f} mN")
    print(f"median |delta B3|   = {np.nanmedian(dB):.1f} uT")


def main():
    if len(sys.argv) > 1:
        session = OUTPUT_ROOT / sys.argv[1]
    else:
        session = find_latest_same_d_path_pair()

    if session is None or not session.exists():
        print("No APMD same-d/different-F path-pair session found.")
        return

    rows = read_summary(session)
    print(f"\n=== APMD same-d/different-F ===\n  session: {session.name}")
    if not rows:
        print("  (no summary rows found)")
        return
    print_summary(rows)
    plot_summary(rows, session)
    print("\nDone.")


if __name__ == "__main__":
    main()
