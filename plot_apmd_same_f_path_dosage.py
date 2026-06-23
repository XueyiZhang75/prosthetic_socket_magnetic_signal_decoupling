from __future__ import annotations

import csv
import math
from pathlib import Path
from statistics import mean, median, pstdev

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "decouple_data"
REPORT_DIR = ROOT / "reports"

OUT_REPLICATES = REPORT_DIR / "experiment_3_4A_same_f_path_dosage_replicates.csv"
OUT_SUMMARY = REPORT_DIR / "experiment_3_4A_same_f_path_dosage_summary.csv"
OUT_MD = REPORT_DIR / "experiment_3_4A_same_f_path_dosage_tables.md"
OUT_FIG = REPORT_DIR / "experiment_3_4A_same_f_path_dosage_complete.png"

OUT_PANEL_A = REPORT_DIR / "experiment_3_4A_same_f_path_dosage_1_matched_force_displacement.png"
OUT_PANEL_B = REPORT_DIR / "experiment_3_4A_same_f_path_dosage_2_delta_d_response.png"
OUT_PANEL_C = REPORT_DIR / "experiment_3_4A_same_f_path_dosage_3_bvec_response.png"
OUT_PANEL_D = REPORT_DIR / "experiment_3_4A_same_f_path_dosage_4_decision_plane.png"
OUT_PANEL_E = REPORT_DIR / "experiment_3_4A_same_f_path_dosage_5_axis_signature.png"


TARGET_F_N = 3.75
SAME_F_GATE_N = 0.050
DISP_SPLIT_GATE_MM = 0.100
B_SIGNAL_GATE_UT = 100.0
MIN_D_SPLIT_EPS_MM = 1e-6

REPLICATE_COLORS = {
    1: "#222222",
    2: "#c23b3b",
    3: "#1f77b4",
}

AXIS_COLORS = {
    "dBx": "#333333",
    "dBy": "#c45252",
    "dBz": "#3182bd",
}


ACCEPTED_ROWS = [
    {
        "dose_label": "+0.20",
        "extra_mm": 0.20,
        "formal_rep": 1,
        "session": "session_20260612_203004",
        "summary": "same_f_path_dosage_A_extra020_pair_summary.csv",
        "trial": 1,
        "basis": "strict strong",
    },
    {
        "dose_label": "+0.20",
        "extra_mm": 0.20,
        "formal_rep": 2,
        "session": "session_20260613_141828",
        "summary": "same_f_path_dosage_A_extra020_pair_summary.csv",
        "trial": 1,
        "basis": "strict strong",
    },
    {
        "dose_label": "+0.20",
        "extra_mm": 0.20,
        "formal_rep": 3,
        "session": "session_20260613_162917",
        "summary": "same_f_path_dosage_A_extra020_pair_summary.csv",
        "trial": 3,
        "basis": "boundary accepted",
    },
    {
        "dose_label": "+0.30",
        "extra_mm": 0.30,
        "formal_rep": 1,
        "session": "session_20260613_174105",
        "summary": "same_f_path_dosage_A_extra030_pair_summary.csv",
        "trial": 1,
        "basis": "boundary accepted",
    },
    {
        "dose_label": "+0.30",
        "extra_mm": 0.30,
        "formal_rep": 2,
        "session": "session_20260613_174105",
        "summary": "same_f_path_dosage_A_extra030_pair_summary.csv",
        "trial": 2,
        "basis": "strict strong",
    },
    {
        "dose_label": "+0.30",
        "extra_mm": 0.30,
        "formal_rep": 3,
        "session": "session_20260613_174105",
        "summary": "same_f_path_dosage_A_extra030_pair_summary.csv",
        "trial": 3,
        "basis": "boundary accepted",
    },
    {
        "dose_label": "+0.40",
        "extra_mm": 0.40,
        "formal_rep": 1,
        "session": "session_20260613_192031",
        "summary": "same_f_path_dosage_A_extra040_pair_summary.csv",
        "trial": 1,
        "basis": "strict strong",
    },
    {
        "dose_label": "+0.40",
        "extra_mm": 0.40,
        "formal_rep": 2,
        "session": "session_20260613_192031",
        "summary": "same_f_path_dosage_A_extra040_pair_summary.csv",
        "trial": 2,
        "basis": "strict strong",
    },
    {
        "dose_label": "+0.40",
        "extra_mm": 0.40,
        "formal_rep": 3,
        "session": "session_20260613_194759",
        "summary": "same_f_path_dosage_A_extra040_pair_summary.csv",
        "trial": 1,
        "basis": "strict strong",
    },
]


def fnum(row: dict[str, str], key: str) -> float:
    return float(row[key])


def read_summary_row(spec: dict[str, object]) -> dict[str, str]:
    path = DATA_DIR / str(spec["session"]) / str(spec["summary"])
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    matches = [r for r in rows if int(r["trial"]) == int(spec["trial"])]
    if not matches:
        raise ValueError(f"No trial {spec['trial']} in {path}")
    if len(matches) > 1:
        raise ValueError(f"Multiple trial {spec['trial']} rows in {path}")
    return matches[0]


def effective_verdict(row: dict[str, object]) -> str:
    same_f = abs(float(row["delta_F_N"])) <= SAME_F_GATE_N
    disp = abs(float(row["delta_d_mm"])) + MIN_D_SPLIT_EPS_MM >= DISP_SPLIT_GATE_MM
    b_signal = float(row["delta_Bvec_uT"]) >= B_SIGNAL_GATE_UT
    if same_f and disp and b_signal:
        return "formal_strong"
    if same_f and b_signal:
        return "formal_boundary"
    if not same_f:
        return "bad_F_match"
    if not disp:
        return "weak_disp_split"
    return "weak_B_signal"


def load_replicates() -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for spec in ACCEPTED_ROWS:
        raw = read_summary_row(spec)
        rec: dict[str, object] = {
            "dose_label": spec["dose_label"],
            "preload_extra_mm": spec["extra_mm"],
            "formal_rep": spec["formal_rep"],
            "source_session": spec["session"],
            "source_trial": spec["trial"],
            "accepted_basis": spec["basis"],
            "target_F_N": TARGET_F_N,
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
            "same_F_ok_effective": int(abs(fnum(raw, "delta_F_N")) <= SAME_F_GATE_N),
            "disp_split_ok_effective": int(
                abs(fnum(raw, "delta_d_mm")) + MIN_D_SPLIT_EPS_MM >= DISP_SPLIT_GATE_MM
            ),
            "b_signal_ok_effective": int(fnum(raw, "delta_Bvec_uT") >= B_SIGNAL_GATE_UT),
        }
        rec["effective_verdict"] = effective_verdict(rec)
        out.append(rec)
    return out


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    REPORT_DIR.mkdir(exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def group_by_extra(rows: list[dict[str, object]]) -> dict[float, list[dict[str, object]]]:
    grouped: dict[float, list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(float(row["preload_extra_mm"]), []).append(row)
    return dict(sorted(grouped.items()))


def row_median(rows: list[dict[str, object]], key: str) -> float:
    return median(float(r[key]) for r in rows)


def row_mean(rows: list[dict[str, object]], key: str) -> float:
    return mean(float(r[key]) for r in rows)


def row_std(rows: list[dict[str, object]], key: str) -> float:
    if len(rows) < 2:
        return 0.0
    return pstdev(float(r[key]) for r in rows)


def build_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    summary: list[dict[str, object]] = []
    for extra, group in group_by_extra(rows).items():
        summary.append(
            {
                "preload_extra_mm": extra,
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
                "strict_strong_count": sum(1 for r in group if r["accepted_basis"] == "strict strong"),
                "boundary_accepted_count": sum(
                    1 for r in group if r["accepted_basis"] == "boundary accepted"
                ),
            }
        )
    return summary


def set_clean_axes(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color="#e6e6e6", lw=0.8)
    ax.set_axisbelow(True)


def add_panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.12,
        1.08,
        label,
        transform=ax.transAxes,
        fontsize=13,
        fontweight="bold",
        va="bottom",
        ha="left",
    )


def add_candidate_band(ax: plt.Axes) -> None:
    ax.axvspan(0.36, 0.44, color="#efe8d8", alpha=0.75, zorder=0)
    ylim = ax.get_ylim()
    ax.text(
        0.40,
        ylim[0] + 0.84 * (ylim[1] - ylim[0]),
        "stronger\ndose",
        color="#555555",
        fontsize=9,
        ha="center",
        va="center",
    )


def plot_displacement_states(ax: plt.Axes, rows: list[dict[str, object]]) -> None:
    grouped = group_by_extra(rows)
    xs = np.array(list(grouped.keys()))
    loading = np.array([row_median(grouped[x], "d_loading_mm") for x in xs])
    unloading = np.array([row_median(grouped[x], "d_unloading_mm") for x in xs])

    ax.plot(xs, loading, "-o", color="#222222", lw=2.0, ms=5, label="loading target")
    ax.plot(
        xs,
        unloading,
        "--o",
        color="#222222",
        lw=2.0,
        ms=5,
        mfc="white",
        label="return unloading",
    )

    jitters = {1: -0.012, 2: 0.0, 3: 0.012}
    for row in rows:
        x = float(row["preload_extra_mm"]) + jitters[int(row["formal_rep"])]
        color = REPLICATE_COLORS[int(row["formal_rep"])]
        ax.scatter(x, float(row["d_loading_mm"]), s=18, color=color, zorder=4)
        ax.scatter(
            x,
            float(row["d_unloading_mm"]),
            s=22,
            facecolors="white",
            edgecolors=color,
            linewidths=1.0,
            zorder=4,
        )

    ax.set_title("Matched-force displacement states", fontsize=12, loc="left")
    ax.set_xlabel("preload extra depth (mm)")
    ax.set_ylabel("d at matched F (mm)")
    ax.set_xticks(xs, [f"+{x:.2f}" for x in xs])
    set_clean_axes(ax)
    add_candidate_band(ax)
    ax.legend(frameon=False, loc="upper left", fontsize=9)


def plot_delta_d(ax: plt.Axes, rows: list[dict[str, object]]) -> None:
    grouped = group_by_extra(rows)
    xs = np.array(list(grouped.keys()))
    med = np.array([row_median(grouped[x], "abs_delta_d_mm") for x in xs])
    lo = np.array([min(float(r["abs_delta_d_mm"]) for r in grouped[x]) for x in xs])
    hi = np.array([max(float(r["abs_delta_d_mm"]) for r in grouped[x]) for x in xs])
    err = np.vstack([med - lo, hi - med])

    ax.errorbar(xs, med, yerr=err, color="#222222", lw=2.0, marker="o", capsize=4)
    for row in rows:
        jitter = {1: -0.010, 2: 0.0, 3: 0.010}[int(row["formal_rep"])]
        ax.scatter(
            float(row["preload_extra_mm"]) + jitter,
            float(row["abs_delta_d_mm"]),
            s=24,
            color=REPLICATE_COLORS[int(row["formal_rep"])],
            zorder=4,
        )

    ax.axhline(DISP_SPLIT_GATE_MM, color="#888888", ls=":", lw=1.2)
    ax.text(xs[0], DISP_SPLIT_GATE_MM + 0.006, "0.10 mm gate", color="#666666", fontsize=8)
    ax.set_title("Displacement split scales with preload dose", fontsize=12, loc="left")
    ax.set_xlabel("preload extra depth (mm)")
    ax.set_ylabel("|Delta d| (mm)")
    ax.set_xticks(xs, [f"+{x:.2f}" for x in xs])
    set_clean_axes(ax)
    add_candidate_band(ax)


def plot_bvec(ax: plt.Axes, rows: list[dict[str, object]]) -> None:
    grouped = group_by_extra(rows)
    xs = np.array(list(grouped.keys()))
    med = np.array([row_median(grouped[x], "delta_Bvec_uT") for x in xs])
    lo = np.array([min(float(r["delta_Bvec_uT"]) for r in grouped[x]) for x in xs])
    hi = np.array([max(float(r["delta_Bvec_uT"]) for r in grouped[x]) for x in xs])
    err = np.vstack([med - lo, hi - med])

    bars = ax.bar(xs, med, width=0.06, color="#333333", alpha=0.92)
    ax.errorbar(xs, med, yerr=err, fmt="none", color="#222222", capsize=4, lw=1.4)
    for row in rows:
        jitter = {1: -0.012, 2: 0.0, 3: 0.012}[int(row["formal_rep"])]
        ax.scatter(
            float(row["preload_extra_mm"]) + jitter,
            float(row["delta_Bvec_uT"]),
            s=24,
            color=REPLICATE_COLORS[int(row["formal_rep"])],
            edgecolors="white",
            linewidths=0.4,
            zorder=4,
        )
    bars[-1].set_color("#c45252")

    ax.axhline(B_SIGNAL_GATE_UT, color="#888888", ls=":", lw=1.2)
    ax.text(xs[0], B_SIGNAL_GATE_UT + 12, "100 uT gate", color="#666666", fontsize=8)
    ax.set_title("Magnetic separation remains strong", fontsize=12, loc="left")
    ax.set_xlabel("preload extra depth (mm)")
    ax.set_ylabel("Delta Bvec (uT)")
    ax.set_xticks(xs, [f"+{x:.2f}" for x in xs])
    set_clean_axes(ax)
    add_candidate_band(ax)


def plot_decision(ax: plt.Axes, summary: list[dict[str, object]]) -> None:
    xs = [float(r["median_delta_d_mm"]) for r in summary]
    ys = [float(r["median_delta_Bvec_uT"]) for r in summary]
    labels = [f"+{float(r['preload_extra_mm']):.2f}" for r in summary]

    ax.plot(xs, ys, color="#888888", lw=1.6, zorder=1)
    for x, y, label in zip(xs, ys, labels):
        color = "#c45252" if label == "+0.40" else "#222222"
        ax.scatter(x, y, s=120, facecolors=color if label == "+0.40" else "white",
                   edgecolors=color, linewidths=1.8, zorder=3)
        ax.text(x + 0.006, y + 8, label, color=color, fontsize=9)

    ax.axvline(DISP_SPLIT_GATE_MM, color="#888888", ls=":", lw=1.1)
    ax.axhline(B_SIGNAL_GATE_UT, color="#888888", ls=":", lw=1.1)
    ax.annotate(
        "preferred dose",
        xy=(xs[-1], ys[-1]),
        xytext=(xs[-1] - 0.004, ys[-1] + 24),
        arrowprops=dict(arrowstyle="-", color="#c45252", lw=1.2),
        color="#c45252",
        fontsize=9,
        ha="right",
    )
    ax.set_xlim(0.096, max(xs) + 0.010)
    ax.set_ylim(85, max(ys) + 70)
    ax.set_title("Dose decision plane", fontsize=12, loc="left")
    ax.set_xlabel("median |Delta d| (mm)")
    ax.set_ylabel("median Delta Bvec (uT)")
    set_clean_axes(ax)


def plot_axis_signature(ax: plt.Axes, summary: list[dict[str, object]]) -> None:
    extras = [float(r["preload_extra_mm"]) for r in summary]
    x = np.arange(len(extras))
    width = 0.24
    vals = {
        "dBx": [float(r["median_delta_Bx_uT"]) for r in summary],
        "dBy": [float(r["median_delta_By_uT"]) for r in summary],
        "dBz": [float(r["median_delta_Bz_uT"]) for r in summary],
    }
    for i, key in enumerate(["dBx", "dBy", "dBz"]):
        ax.bar(x + (i - 1) * width, vals[key], width=width, color=AXIS_COLORS[key], label=key)
    ax.axhline(0, color="#777777", lw=1.0)
    ax.set_title("3-axis magnetic signature", fontsize=12, loc="left")
    ax.set_xlabel("preload extra depth (mm)")
    ax.set_ylabel("median Delta B component (uT)")
    ax.set_xticks(x, [f"+{v:.2f}" for v in extras])
    set_clean_axes(ax)
    ax.legend(frameon=False, ncol=3, loc="upper left", fontsize=8)


def plot_axis_heatmap(path: Path, summary: list[dict[str, object]]) -> None:
    extras = [float(r["preload_extra_mm"]) for r in summary]
    data = np.array(
        [
            [float(r["median_delta_Bx_uT"]) for r in summary],
            [float(r["median_delta_By_uT"]) for r in summary],
            [float(r["median_delta_Bz_uT"]) for r in summary],
        ]
    )
    vmax = max(300.0, float(np.max(np.abs(data))) * 1.05)
    fig, ax = plt.subplots(figsize=(7.2, 3.0), dpi=220)
    im = ax.imshow(data, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_title("3-axis magnetic signature map", fontsize=12, loc="left")
    ax.set_xticks(np.arange(len(extras)), [f"+{v:.2f}" for v in extras])
    ax.set_yticks(np.arange(3), ["dBx", "dBy", "dBz"])
    ax.set_xlabel("preload extra depth (mm)")
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            value = data[i, j]
            ax.text(
                j,
                i,
                f"{value:+.0f}",
                ha="center",
                va="center",
                fontsize=9,
                color="white" if abs(value) > vmax * 0.45 else "#222222",
            )
    cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.02)
    cbar.set_label("Delta B component (uT)")
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def save_individual_panels(rows: list[dict[str, object]], summary: list[dict[str, object]]) -> None:
    specs = [
        (OUT_PANEL_A, (8.0, 4.2), lambda ax: plot_displacement_states(ax, rows), "a"),
        (OUT_PANEL_B, (6.4, 4.2), lambda ax: plot_delta_d(ax, rows), "b"),
        (OUT_PANEL_C, (6.4, 4.2), lambda ax: plot_bvec(ax, rows), "c"),
        (OUT_PANEL_D, (6.4, 4.2), lambda ax: plot_decision(ax, summary), "d"),
        (OUT_PANEL_E, (6.4, 4.2), lambda ax: plot_axis_signature(ax, summary), "e"),
    ]
    for path, size, fn, label in specs:
        fig, ax = plt.subplots(figsize=size, dpi=220)
        fn(ax)
        add_panel_label(ax, label)
        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)


def save_complete_figure(rows: list[dict[str, object]], summary: list[dict[str, object]]) -> None:
    fig = plt.figure(figsize=(13.2, 8.4), dpi=220)
    gs = fig.add_gridspec(
        2,
        3,
        left=0.07,
        right=0.985,
        top=0.83,
        bottom=0.09,
        wspace=0.38,
        hspace=0.48,
        width_ratios=[1.15, 1.0, 1.0],
    )
    ax_a = fig.add_subplot(gs[0, :2])
    ax_b = fig.add_subplot(gs[0, 2])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d = fig.add_subplot(gs[1, 1])
    ax_e = fig.add_subplot(gs[1, 2])

    plot_displacement_states(ax_a, rows)
    plot_delta_d(ax_b, rows)
    plot_bvec(ax_c, rows)
    plot_decision(ax_d, summary)
    plot_axis_signature(ax_e, summary)

    for label, ax in zip("abcde", [ax_a, ax_b, ax_c, ax_d, ax_e]):
        add_panel_label(ax, label)

    fig.text(
        0.03,
        0.965,
        "Experiment 3.4A: preload-extra depth tunes same-F path-pair separation",
        fontsize=16,
        fontweight="bold",
        ha="left",
    )
    fig.text(
        0.03,
        0.925,
        "Formal accepted data: target F = 3.75 N; three accepted path-pairs per preload-extra depth",
        fontsize=10,
        color="#555555",
        ha="left",
    )
    fig.savefig(OUT_FIG, bbox_inches="tight")
    plt.close(fig)


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
                "extra": f"+{float(r['preload_extra_mm']):.2f} mm",
                "n": int(r["n"]),
                "d_split": f"{float(r['median_delta_d_mm']):+.3f} mm",
                "dBvec": f"{float(r['median_delta_Bvec_uT']):.1f} uT",
                "dBy": f"{float(r['median_delta_By_uT']):+.1f} uT",
                "dBz": f"{float(r['median_delta_Bz_uT']):+.1f} uT",
                "abs_dF": f"{float(r['median_abs_delta_F_mN']):.1f} mN",
                "strict": int(r["strict_strong_count"]),
                "boundary": int(r["boundary_accepted_count"]),
            }
        )
    rep_rows = []
    for r in rows:
        rep_rows.append(
            {
                "extra": r["dose_label"],
                "rep": r["formal_rep"],
                "source": f"{r['source_session']} rep{r['source_trial']}",
                "d_load": f"{float(r['d_loading_mm']):.3f}",
                "d_unload": f"{float(r['d_unloading_mm']):.3f}",
                "dd": f"{float(r['delta_d_mm']):+.3f}",
                "dF": f"{float(r['delta_F_N']) * 1000:+.1f}",
                "dBvec": f"{float(r['delta_Bvec_uT']):.1f}",
                "basis": r["accepted_basis"],
            }
        )
    text = "\n".join(
        [
            "# Experiment 3.4A same-F preload-extra-depth dosage tables",
            "",
            "Target F = 3.75 N. Accepted rows only; excluded failed or diagnostic rows are not included.",
            "",
            "## Summary by preload extra depth",
            "",
            markdown_table(
                summary_rows,
                ["extra", "n", "d_split", "dBvec", "dBy", "dBz", "abs_dF", "strict", "boundary"],
                [
                    "Preload extra",
                    "n",
                    "Median Delta d",
                    "Median Delta Bvec",
                    "Median dBy",
                    "Median dBz",
                    "Median abs Delta F",
                    "Strict strong",
                    "Boundary accepted",
                ],
            ),
            "",
            "## Accepted replicate table",
            "",
            markdown_table(
                rep_rows,
                ["extra", "rep", "source", "d_load", "d_unload", "dd", "dF", "dBvec", "basis"],
                [
                    "Preload extra",
                    "Formal rep",
                    "Source",
                    "d loading (mm)",
                    "d unloading (mm)",
                    "Delta d (mm)",
                    "Delta F (mN)",
                    "Delta Bvec (uT)",
                    "Basis",
                ],
            ),
            "",
        ]
    )
    OUT_MD.write_text(text, encoding="utf-8")


def main() -> None:
    REPORT_DIR.mkdir(exist_ok=True)
    rows = load_replicates()
    summary = build_summary(rows)

    rep_fields = [
        "dose_label",
        "preload_extra_mm",
        "formal_rep",
        "source_session",
        "source_trial",
        "accepted_basis",
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
        "same_F_ok_effective",
        "disp_split_ok_effective",
        "b_signal_ok_effective",
    ]
    summary_fields = [
        "preload_extra_mm",
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
        "strict_strong_count",
        "boundary_accepted_count",
    ]
    write_csv(OUT_REPLICATES, rows, rep_fields)
    write_csv(OUT_SUMMARY, summary, summary_fields)
    write_markdown(rows, summary)

    save_complete_figure(rows, summary)
    save_individual_panels(rows, summary)
    plot_axis_heatmap(REPORT_DIR / "experiment_3_4A_same_f_path_dosage_axis_heatmap.png", summary)

    print("Saved:")
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
        REPORT_DIR / "experiment_3_4A_same_f_path_dosage_axis_heatmap.png",
    ]:
        print(f"  {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
