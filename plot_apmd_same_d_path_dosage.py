"""Plot APMD Experiment 3.3A same-d path-dose preload-depth scan.

Default input:
  decouple_data/session_20260612_155336/same_d_path_dosage_A_pair_summary.csv

Outputs are saved as PNG files in the same session folder.
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
DEFAULT_SESSION = HERE / "decouple_data" / "session_20260612_155336"
SUMMARY_FILENAME = "same_d_path_dosage_A_pair_summary.csv"
FIGURE_FILENAME = "same_d_path_dosage_A.png"
Dose_SUMMARY_FILENAME = "same_d_path_dosage_A_dose_summary.csv"
PNG_DPI = 300

REP_COLORS = {
    1: "#000000",
    2: "#D62728",
    3: "#1F77B4",
}

PALETTE = {
    "black": "#222222",
    "gray": "#777777",
    "gray_light": "#E8E8E8",
    "red": "#B64342",
    "blue": "#1F77B4",
    "highlight": "#F4EFE3",
}


def apply_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "DejaVu Sans", "Liberation Sans"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 8,
            "axes.titlesize": 10,
            "axes.labelsize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
            "lines.linewidth": 1.3,
            "lines.markersize": 4.2,
            "xtick.major.width": 0.7,
            "ytick.major.width": 0.7,
            "xtick.major.size": 2.8,
            "ytick.major.size": 2.8,
        }
    )


def safe_float(value: str | None, default: float = float("nan")) -> float:
    try:
        return float(value) if value is not None else default
    except ValueError:
        return default


def read_rows(session: Path) -> list[dict]:
    path = session / SUMMARY_FILENAME
    if not path.exists():
        raise FileNotFoundError(path)

    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    "session_id": r.get("session_id", session.name),
                    "trial": int(r["trial"]),
                    "pair_id": int(r["pair_id"]),
                    "d_target_mm": safe_float(r["d_target_mm"]),
                    "d_preload_mm": safe_float(r["d_preload_mm"]),
                    "d_direct_mm": safe_float(r["d_direct_mm"]),
                    "d_return_mm": safe_float(r["d_return_mm"]),
                    "d_diff_mm": safe_float(r["d_diff_mm"]),
                    "F_direct_N": safe_float(r["F_direct_N"]),
                    "F_return_N": safe_float(r["F_return_N"]),
                    "delta_F_N": safe_float(r["delta_F_N"]),
                    "delta_Bmag_uT": safe_float(r["delta_Bmag_uT"]),
                    "delta_Bx_uT": safe_float(r["delta_Bx_uT"]),
                    "delta_By_uT": safe_float(r["delta_By_uT"]),
                    "delta_Bz_uT": safe_float(r["delta_Bz_uT"]),
                    "delta_Bvec_uT": safe_float(r["delta_Bvec_uT"]),
                    "same_d_ok": r.get("same_d_ok") == "1",
                    "force_split_ok": r.get("force_split_ok") == "1",
                    "b_signal_ok": r.get("b_signal_ok") == "1",
                    "verdict": r.get("verdict", ""),
                }
            )
    rows.sort(key=lambda x: (x["d_preload_mm"], x["trial"]))
    return rows


def grouped_by_preload(rows: list[dict]) -> dict[float, list[dict]]:
    groups: dict[float, list[dict]] = defaultdict(list)
    for row in rows:
        groups[row["d_preload_mm"]].append(row)
    return {k: sorted(v, key=lambda r: r["trial"]) for k, v in sorted(groups.items())}


def finite(values) -> list[float]:
    return [float(v) for v in values if math.isfinite(float(v))]


def median(values) -> float:
    vals = finite(values)
    return float(np.median(vals)) if vals else float("nan")


def mean(values) -> float:
    vals = finite(values)
    return float(np.mean(vals)) if vals else float("nan")


def sem(values) -> float:
    vals = finite(values)
    if len(vals) <= 1:
        return 0.0
    return float(np.std(vals, ddof=1) / math.sqrt(len(vals)))


def panel_label(ax, label: str) -> None:
    ax.text(
        -0.12,
        1.07,
        label,
        transform=ax.transAxes,
        fontsize=11,
        fontweight="bold",
        ha="left",
        va="bottom",
    )


def dose_arrays(groups: dict[float, list[dict]]):
    preloads = np.array(list(groups.keys()), dtype=float)
    target_d = median([r["d_target_mm"] for rows in groups.values() for r in rows])
    extras = preloads - target_d
    return preloads, extras


def metric_summary(groups: dict[float, list[dict]], key_fn):
    values = []
    errors = []
    raw = []
    for rows in groups.values():
        vals = [key_fn(r) for r in rows]
        values.append(mean(vals))
        errors.append(sem(vals))
        raw.append(vals)
    return np.array(values), np.array(errors), raw


def write_dose_summary(session: Path, groups: dict[float, list[dict]]) -> Path:
    out = session / Dose_SUMMARY_FILENAME
    preloads, extras = dose_arrays(groups)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "d_target_mm",
                "d_preload_mm",
                "preload_extra_mm",
                "n",
                "same_d_pass",
                "strong_pass",
                "mean_abs_delta_F_N",
                "sem_abs_delta_F_N",
                "mean_delta_Bvec_uT",
                "sem_delta_Bvec_uT",
                "mean_delta_Bmag_uT",
                "median_delta_Bx_uT",
                "median_delta_By_uT",
                "median_delta_Bz_uT",
                "mean_Bvec_per_absF_uT_per_N",
            ]
        )
        for preload, extra, rows in zip(preloads, extras, groups.values()):
            abs_f = [abs(r["delta_F_N"]) for r in rows]
            bvec = [r["delta_Bvec_uT"] for r in rows]
            bmag = [r["delta_Bmag_uT"] for r in rows]
            writer.writerow(
                [
                    f"{median([r['d_target_mm'] for r in rows]):.4f}",
                    f"{preload:.4f}",
                    f"{extra:.4f}",
                    len(rows),
                    sum(r["same_d_ok"] for r in rows),
                    sum(r["verdict"] == "strong" for r in rows),
                    f"{mean(abs_f):.6f}",
                    f"{sem(abs_f):.6f}",
                    f"{mean(bvec):.6f}",
                    f"{sem(bvec):.6f}",
                    f"{mean(bmag):.6f}",
                    f"{median([r['delta_Bx_uT'] for r in rows]):.6f}",
                    f"{median([r['delta_By_uT'] for r in rows]):.6f}",
                    f"{median([r['delta_Bz_uT'] for r in rows]):.6f}",
                    f"{mean(bvec) / mean(abs_f):.6f}",
                ]
            )
    return out


def plot_force_dose(ax, groups):
    preloads, extras = dose_arrays(groups)
    y, yerr, raw = metric_summary(groups, lambda r: abs(r["delta_F_N"]))
    x = extras
    ax.errorbar(
        x,
        y,
        yerr=yerr,
        color=PALETTE["black"],
        marker="o",
        markersize=5,
        linewidth=1.6,
        capsize=3,
        zorder=3,
    )
    jitter = [-0.006, 0.0, 0.006]
    for vals in raw:
        pass
    for i, vals in enumerate(raw):
        for j, val in enumerate(vals):
            ax.scatter(
                x[i] + jitter[j % len(jitter)],
                val,
                s=18,
                color=REP_COLORS.get(j + 1, PALETTE["gray"]),
                edgecolor="white",
                linewidth=0.35,
                zorder=4,
            )
    ax.axhline(0.20, color=PALETTE["gray"], linestyle=":", linewidth=0.9)
    ax.text(x[0], 0.23, "0.20 N reference", color=PALETTE["gray"], fontsize=7)
    ax.set_title("Path-induced force separation")
    ax.set_xlabel("preload extra depth (mm)")
    ax.set_ylabel(r"mean |$\Delta F$| (N)")
    ax.set_xticks(x)
    ax.set_xticklabels([f"+{e:.2f}" for e in extras])
    ax.grid(axis="y", color=PALETTE["gray_light"], linewidth=0.8)
    panel_label(ax, "a")


def plot_bvec_dose(ax, groups):
    preloads, extras = dose_arrays(groups)
    y, yerr, raw = metric_summary(groups, lambda r: r["delta_Bvec_uT"])
    x = extras
    ax.errorbar(
        x,
        y,
        yerr=yerr,
        color=PALETTE["black"],
        marker="o",
        markersize=5,
        linewidth=1.6,
        capsize=3,
        zorder=3,
    )
    jitter = [-0.006, 0.0, 0.006]
    for i, vals in enumerate(raw):
        for j, val in enumerate(vals):
            ax.scatter(
                x[i] + jitter[j % len(jitter)],
                val,
                s=18,
                color=REP_COLORS.get(j + 1, PALETTE["gray"]),
                edgecolor="white",
                linewidth=0.35,
                zorder=4,
            )
    ax.axhline(50.0, color=PALETTE["gray"], linestyle=":", linewidth=0.9)
    ax.text(x[0], 55.0, "50 uT reference", color=PALETTE["gray"], fontsize=7)
    ax.set_title("Magnetic separation dose response")
    ax.set_xlabel("preload extra depth (mm)")
    ax.set_ylabel(r"mean $\Delta B_{\mathrm{vec}}$ (uT)")
    ax.set_xticks(x)
    ax.set_xticklabels([f"+{e:.2f}" for e in extras])
    ax.grid(axis="y", color=PALETTE["gray_light"], linewidth=0.8)
    panel_label(ax, "b")


def plot_axis_heatmap(ax, fig, groups):
    preloads, extras = dose_arrays(groups)
    matrix = np.array(
        [
            [median([r["delta_Bx_uT"] for r in rows]) for rows in groups.values()],
            [median([r["delta_By_uT"] for r in rows]) for rows in groups.values()],
            [median([r["delta_Bz_uT"] for r in rows]) for rows in groups.values()],
        ]
    )
    vmax = max(50.0, float(np.nanmax(np.abs(matrix))))
    im = ax.imshow(matrix, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_title("Median 3-axis magnetic signature")
    ax.set_xticks(np.arange(len(extras)))
    ax.set_xticklabels([f"+{e:.2f}" for e in extras])
    ax.set_yticks([0, 1, 2])
    ax.set_yticklabels(["dBx", "dBy", "dBz"])
    ax.set_xlabel("preload extra depth (mm)")
    ax.tick_params(length=0)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            val = matrix[i, j]
            color = "white" if abs(val) > 0.55 * vmax else PALETTE["black"]
            ax.text(j, i, f"{val:+.0f}", ha="center", va="center", color=color, fontsize=8)
    for x in np.arange(-0.5, len(extras), 1):
        ax.axvline(x, color="white", linewidth=1.2)
    for y in np.arange(-0.5, 3, 1):
        ax.axhline(y, color="white", linewidth=1.2)
    cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.025)
    cbar.set_label("Delta B component (uT)")
    panel_label(ax, "c")


def plot_decision_plane(ax, groups):
    preloads, extras = dose_arrays(groups)
    x, xerr, _ = metric_summary(groups, lambda r: abs(r["delta_F_N"]))
    y, yerr, _ = metric_summary(groups, lambda r: r["delta_Bvec_uT"])
    ratio = y / x
    ax.errorbar(
        x,
        y,
        xerr=xerr,
        yerr=yerr,
        color=PALETTE["gray"],
        marker="o",
        markersize=0,
        linewidth=1.2,
        capsize=3,
        zorder=1,
    )
    sizes = 85 + 45 * (extras - np.min(extras)) / max(0.001, np.ptp(extras))
    ax.scatter(x, y, s=sizes, color=PALETTE["red"], edgecolor="white", linewidth=0.7, zorder=3)
    for xi, yi, ri, extra in zip(x, y, ratio, extras):
        ax.text(
            xi + 0.015,
            yi,
            f"+{extra:.2f}\n{ri:.0f} uT/N",
            fontsize=7,
            color=PALETTE["black"],
            va="center",
        )
    ax.axhline(50.0, color=PALETTE["gray"], linestyle=":", linewidth=0.9)
    ax.axvline(0.20, color=PALETTE["gray"], linestyle=":", linewidth=0.9)
    ax.set_title("Dose plane: stronger path history gives larger signal")
    ax.set_xlabel(r"mean |$\Delta F$| (N)")
    ax.set_ylabel(r"mean $\Delta B_{\mathrm{vec}}$ (uT)")
    ax.grid(color=PALETTE["gray_light"], linewidth=0.8)
    panel_label(ax, "d")


def plot(session: Path) -> tuple[Path, Path]:
    apply_style()
    rows = read_rows(session)
    groups = grouped_by_preload(rows)
    summary_path = write_dose_summary(session, groups)

    fig = plt.figure(figsize=(8.7, 6.4), dpi=PNG_DPI)
    gs = fig.add_gridspec(2, 2, left=0.08, right=0.97, top=0.86, bottom=0.10, wspace=0.36, hspace=0.48)
    fig.text(
        0.02,
        0.965,
        "Experiment 3.3A: preload depth tunes same-d path-pair response",
        fontsize=14,
        fontweight="bold",
        ha="left",
        va="top",
    )
    fig.text(
        0.02,
        0.925,
        f"Formal data: {session.name}; target d = 3.40 mm; 3 pairs per preload depth",
        fontsize=8,
        color=PALETTE["gray"],
        ha="left",
        va="top",
    )

    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d = fig.add_subplot(gs[1, 1])

    plot_force_dose(ax_a, groups)
    plot_bvec_dose(ax_b, groups)
    plot_axis_heatmap(ax_c, fig, groups)
    plot_decision_plane(ax_d, groups)

    out = session / FIGURE_FILENAME
    fig.savefig(out, dpi=PNG_DPI, bbox_inches="tight")
    plt.close(fig)
    return out, summary_path


def main() -> None:
    session = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SESSION
    if not session.is_absolute():
        session = (HERE / session).resolve()
    out, summary = plot(session)
    print(f"Saved figure: {out}")
    print(f"Saved dose summary: {summary}")


if __name__ == "__main__":
    main()
