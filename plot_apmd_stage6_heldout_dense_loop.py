"""Plot the Stage 6.1 held-out dense-loop validation summary.

The figure is regenerated from the state-summary CSV so the held-out QC plot
can be edited without touching the raw acquisition files.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DEFAULT_SESSION = "session_20260615_160438"
SUMMARY_NAME = "local_heldout_dense_loop_6p1_state_summary.csv"
FIGURE_NAME = "local_heldout_dense_loop_6p1.png"
REPORT_QC = ROOT / "reports" / "apmd_stage6_heldout_qc_by_d.csv"

BLACK = "#222222"
RED = "#d43d3d"
BLUE = "#2f88c9"
GRAY = "#777777"
LIGHT_GRAY = "#e6e6e6"

FORCE_GATE_N = 0.20
B_GATE_UT = 50.0


def _median(values: pd.Series) -> float:
    return float(pd.to_numeric(values, errors="coerce").median())


def _component_delta(unloading: pd.Series, loading: pd.Series, name: str) -> float:
    return float(unloading[name]) - float(loading[name])


def load_state_summary(session_dir: Path) -> pd.DataFrame:
    path = session_dir / SUMMARY_NAME
    if not path.exists():
        raise FileNotFoundError(f"Missing state summary: {path}")
    df = pd.read_csv(path)
    numeric_cols = [
        "cycle",
        "state_index",
        "d_target_mm",
        "d_median_mm",
        "F_median_N",
        "Bmag_median_uT",
        "Bx_median_uT",
        "By_median_uT",
        "Bz_median_uT",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def build_pair_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (cycle, d_target), group in df.groupby(["cycle", "d_target_mm"]):
        loading_rows = group[group["branch"] == "loading"]
        unloading_rows = group[group["branch"] == "unloading"]
        if loading_rows.empty or unloading_rows.empty:
            continue
        loading = loading_rows.iloc[0]
        unloading = unloading_rows.iloc[0]
        d_mismatch = float(unloading["d_median_mm"]) - float(loading["d_median_mm"])
        delta_f = float(unloading["F_median_N"]) - float(loading["F_median_N"])
        delta_bx = _component_delta(unloading, loading, "Bx_median_uT")
        delta_by = _component_delta(unloading, loading, "By_median_uT")
        delta_bz = _component_delta(unloading, loading, "Bz_median_uT")
        delta_bvec = math.sqrt(delta_bx**2 + delta_by**2 + delta_bz**2)
        rows.append(
            {
                "d_target_mm": float(d_target),
                "cycle": int(cycle),
                "d_mismatch_mm": d_mismatch,
                "delta_F_N": delta_f,
                "abs_delta_F_N": abs(delta_f),
                "delta_Bx_uT": delta_bx,
                "delta_By_uT": delta_by,
                "delta_Bz_uT": delta_bz,
                "delta_Bvec_uT": delta_bvec,
                "loading_F_N": float(loading["F_median_N"]),
                "unloading_F_N": float(unloading["F_median_N"]),
                "loading_Bmag_uT": float(loading["Bmag_median_uT"]),
                "unloading_Bmag_uT": float(unloading["Bmag_median_uT"]),
            }
        )
    return pd.DataFrame(rows).sort_values(["d_target_mm", "cycle"])


def build_depth_summary(pair_df: pd.DataFrame) -> pd.DataFrame:
    grouped = pair_df.groupby("d_target_mm", as_index=False)
    return grouped.agg(
        med_abs_delta_F_N=("abs_delta_F_N", "median"),
        med_delta_Bvec_uT=("delta_Bvec_uT", "median"),
        med_delta_Bx_uT=("delta_Bx_uT", "median"),
        med_delta_By_uT=("delta_By_uT", "median"),
        med_delta_Bz_uT=("delta_Bz_uT", "median"),
        max_abs_d_mismatch_mm=("d_mismatch_mm", lambda s: float(np.abs(s).max())),
    )


def _style_axis(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, axis="y", color=LIGHT_GRAY, linewidth=0.8)
    ax.tick_params(labelsize=9)


def plot_figure(df: pd.DataFrame, pair_df: pd.DataFrame, out_path: Path) -> None:
    summary = build_depth_summary(pair_df)
    d_vals = summary["d_target_mm"].to_numpy()

    fig = plt.figure(figsize=(14.6, 9.2), constrained_layout=False)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.05, 1.0])
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d = fig.add_subplot(gs[1, 1])

    fig.suptitle(
        "Stage 6.1 held-out dense-loop validation: session_20260615_160438",
        x=0.02,
        y=0.99,
        ha="left",
        fontsize=15,
        fontweight="bold",
    )
    fig.text(
        0.02,
        0.957,
        "Test-only d grid: 3.05/3.15/3.25/3.35/3.45/3.55 mm; preload = 3.80 mm; cycles = 3",
        ha="left",
        fontsize=9,
        color="#555555",
    )
    fig.subplots_adjust(left=0.06, right=0.965, top=0.885, bottom=0.075, hspace=0.42, wspace=0.28)

    # Panel a: force branches.
    cycle_colors = {1: BLACK, 2: RED, 3: BLUE}
    for cycle in sorted(df["cycle"].dropna().unique()):
        color = cycle_colors.get(int(cycle), GRAY)
        for branch, marker, linestyle, fill in [
            ("loading", "o", "-", color),
            ("unloading", "o", "--", "white"),
        ]:
            rows = df[(df["cycle"] == cycle) & (df["branch"] == branch)].sort_values(
                "d_target_mm"
            )
            ax_a.plot(
                rows["d_target_mm"],
                rows["F_median_N"],
                color=color,
                linestyle=linestyle,
                linewidth=1.4,
                marker=marker,
                markersize=4.8,
                markerfacecolor=fill,
                markeredgecolor=color,
                markeredgewidth=1.2,
                label=f"cycle {int(cycle)} {branch}",
            )
    ax_a.set_title("a  Held-out loading/unloading force branches", loc="left", fontsize=11, fontweight="bold")
    ax_a.set_xlabel("target d (mm)")
    ax_a.set_ylabel("F at state median (N)")
    _style_axis(ax_a)
    ax_a.legend(loc="upper left", fontsize=7, ncol=2, frameon=False)

    # Panel b: force and magnetic split.
    ax_b.bar(
        d_vals,
        summary["med_abs_delta_F_N"],
        width=0.055,
        color=BLACK,
        label="median |Delta F| (N)",
    )
    ax_b.axhline(FORCE_GATE_N, color=GRAY, linestyle=":", linewidth=1.0)
    ax_b.set_ylabel("median |Delta F| (N)")
    ax_b.set_xlabel("held-out target d (mm)")
    ax_b.set_title("b  Held-out path-pair separation strength", loc="left", fontsize=11, fontweight="bold")
    _style_axis(ax_b)

    ax_b2 = ax_b.twinx()
    ax_b2.plot(
        d_vals,
        summary["med_delta_Bvec_uT"],
        color=RED,
        linewidth=1.8,
        marker="o",
        markersize=4.5,
        label="median Delta Bvec (uT)",
    )
    ax_b2.axhline(B_GATE_UT, color=RED, linestyle=":", linewidth=1.0, alpha=0.75)
    ax_b2.set_ylabel("median Delta Bvec (uT)", color=RED)
    ax_b2.tick_params(axis="y", colors=RED, labelsize=9)
    ax_b2.spines["right"].set_color(RED)
    ax_b2.spines["top"].set_visible(False)
    ax_b2.yaxis.label.set_color(RED)

    handles_1, labels_1 = ax_b.get_legend_handles_labels()
    handles_2, labels_2 = ax_b2.get_legend_handles_labels()
    ax_b.legend(handles_1 + handles_2, labels_1 + labels_2, loc="upper left", fontsize=8, frameon=False)

    # Panel c: component signature heatmap.
    component_matrix = np.vstack(
        [
            summary["med_delta_Bx_uT"],
            summary["med_delta_By_uT"],
            summary["med_delta_Bz_uT"],
        ]
    )
    vmax = max(220.0, float(np.nanmax(np.abs(component_matrix))) * 1.05)
    im = ax_c.imshow(
        component_matrix,
        aspect="auto",
        cmap="RdBu_r",
        vmin=-vmax,
        vmax=vmax,
    )
    ax_c.set_title("c  Median magnetic-axis signature (unloading - loading)", loc="left", fontsize=11, fontweight="bold")
    ax_c.set_xticks(range(len(d_vals)), [f"{v:.2f}" for v in d_vals])
    ax_c.set_yticks(range(3), ["dBx", "dBy", "dBz"])
    ax_c.set_xlabel("held-out target d (mm)")
    ax_c.tick_params(labelsize=9)
    for i in range(component_matrix.shape[0]):
        for j in range(component_matrix.shape[1]):
            value = component_matrix[i, j]
            ax_c.text(
                j,
                i,
                f"{value:+.0f}",
                ha="center",
                va="center",
                fontsize=8,
                color="white" if abs(value) > 0.55 * vmax else "#222222",
            )
    cbar = fig.colorbar(im, ax=ax_c, fraction=0.04, pad=0.025)
    cbar.set_label("uT", fontsize=9)
    cbar.ax.tick_params(labelsize=8)
    for spine in ax_c.spines.values():
        spine.set_visible(False)

    # Panel d: gate-margin bar chart, replacing the less readable decision plane.
    x = np.arange(len(d_vals))
    width = 0.36
    force_margin = summary["med_abs_delta_F_N"].to_numpy() / FORCE_GATE_N
    b_margin = summary["med_delta_Bvec_uT"].to_numpy() / B_GATE_UT
    ax_d.bar(
        x - width / 2,
        force_margin,
        width=width,
        color=BLACK,
        label="|Delta F| / 0.20 N gate",
    )
    ax_d.bar(
        x + width / 2,
        b_margin,
        width=width,
        color=RED,
        alpha=0.88,
        label="Delta Bvec / 50 uT gate",
    )
    ax_d.axhline(1.0, color=GRAY, linestyle=":", linewidth=1.1)
    ax_d.set_xticks(x, [f"{v:.2f}" for v in d_vals])
    ax_d.set_xlabel("held-out target d (mm)")
    ax_d.set_ylabel("gate margin (x threshold)")
    ax_d.set_title("d  Held-out gate margins", loc="left", fontsize=11, fontweight="bold")
    _style_axis(ax_d)
    ax_d.set_ylim(0, max(np.nanmax(force_margin), np.nanmax(b_margin)) * 1.22)
    ax_d.legend(loc="upper right", fontsize=8, frameon=False)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180)
    plt.close(fig)

    REPORT_QC.parent.mkdir(parents=True, exist_ok=True)
    pair_df.to_csv(REPORT_QC, index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--session-id",
        default=DEFAULT_SESSION,
        help="Session folder under decouple_data.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional figure output path. Defaults to the session figure path.",
    )
    return parser.parse_args()


def display_path(path: Path) -> Path:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT)
    except ValueError:
        return path


def main() -> None:
    args = parse_args()
    session_dir = ROOT / "decouple_data" / args.session_id
    df = load_state_summary(session_dir)
    pair_df = build_pair_table(df)
    out_path = Path(args.output) if args.output else session_dir / FIGURE_NAME
    plot_figure(df, pair_df, out_path)
    print(f"Wrote {display_path(out_path)}")
    print(f"Wrote {display_path(REPORT_QC)}")


if __name__ == "__main__":
    main()
