"""Plot QC-accepted Stage J fixed-force trials across sessions.

This script is intentionally narrow: it combines the three clean Stage J
trials selected after stamp-head reruns, without overwriting the generic
single-session Stage J figures.
"""

import csv
import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


HERE = Path(__file__).parent
DATA_ROOT = HERE / "decouple_data"
FIGS_DIR = HERE / "reports" / "figs"
REPORTS_DIR = HERE / "reports"

ANALYSIS_SKIP_S = 1.0
EDGE_WINDOW_S = 10.0
PLOT_BIN_S = 4.0

TRIALS = [
    {
        "session": "session_20260603_122143",
        "rep": 3,
        "label": "trial 1",
        "note": "clean",
        "color": "#2f6f8f",
    },
    {
        "session": "session_20260603_124327",
        "rep": 1,
        "label": "trial 2",
        "note": "clean",
        "color": "#6b8e23",
    },
    {
        "session": "session_20260603_124327",
        "rep": 2,
        "label": "trial 3",
        "note": "clean",
        "color": "#9a6b3f",
    },
]


def safe_float(value, default=np.nan):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def setup_axis(ax, title, xlabel=None, ylabel=None):
    ax.set_title(title, fontsize=10, pad=7)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=9)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=9)
    ax.grid(True, alpha=0.28, linestyle="--", linewidth=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def load_trial(spec):
    path = (
        DATA_ROOT
        / spec["session"]
        / f"J_hold_force_180_rep{spec['rep']}.csv"
    )
    rows = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise RuntimeError(f"No rows in {path}")

    data = {
        "t": np.array([safe_float(r["t_rel_s"]) for r in rows]),
        "F": np.array([safe_float(r["F_N"]) for r in rows]),
        "F_target": np.array([safe_float(r["F_target_N"]) for r in rows]),
        "d": np.array([safe_float(r["d_actual_mm"]) for r in rows]),
        "Bx": np.array([safe_float(r["mean_Bx_uT"]) for r in rows]),
        "By": np.array([safe_float(r["mean_By_uT"]) for r in rows]),
        "Bz": np.array([safe_float(r["mean_Bz_uT"]) for r in rows]),
        "Bmag": np.array([safe_float(r["Bmag_uT"]) for r in rows]),
        "action": np.array([r["control_action"] for r in rows]),
        "source": path,
    }

    mask = np.isfinite(data["t"]) & (data["t"] >= np.nanmin(data["t"]) + ANALYSIS_SKIP_S)
    if np.sum(mask) >= 3:
        for key, value in list(data.items()):
            if isinstance(value, np.ndarray) and len(value) == len(mask):
                data[key] = value[mask]

    return data


def edge_mean(values, times, first=True):
    if len(values) == 0:
        return np.nan
    if first:
        mask = times <= np.nanmin(times) + EDGE_WINDOW_S
    else:
        mask = times >= np.nanmax(times) - EDGE_WINDOW_S
    if np.sum(mask) == 0:
        return float(values[0] if first else values[-1])
    return float(np.nanmean(values[mask]))


def summarize_trial(spec, data):
    t = data["t"] - np.nanmin(data["t"])
    F = data["F"]
    d = data["d"]
    Bmag = data["Bmag"]
    Bx = data["Bx"]
    By = data["By"]
    Bz = data["Bz"]
    duration = float(np.nanmax(t) - np.nanmin(t))

    F_first = edge_mean(F, t, first=True)
    F_last = edge_mean(F, t, first=False)
    d_first = edge_mean(d, t, first=True)
    d_last = edge_mean(d, t, first=False)
    B_first = edge_mean(Bmag, t, first=True)
    B_last = edge_mean(Bmag, t, first=False)

    return {
        "label": spec["label"],
        "session": spec["session"],
        "rep": spec["rep"],
        "note": spec["note"],
        "n_rows": len(t),
        "duration_s": duration,
        "F_mean_N": float(np.nanmean(F)),
        "F_std_mN": float(np.nanstd(F) * 1000.0),
        "F_median_N": float(np.nanmedian(F)),
        "delta_F_mN_edge": (F_last - F_first) * 1000.0,
        "d_start_mm_edge": d_first,
        "d_end_mm_edge": d_last,
        "delta_d_mm_edge": d_last - d_first,
        "Bmag_start_uT_edge": B_first,
        "Bmag_end_uT_edge": B_last,
        "delta_Bmag_uT_edge": B_last - B_first,
        "delta_Bx_uT_edge": edge_mean(Bx, t, False) - edge_mean(Bx, t, True),
        "delta_By_uT_edge": edge_mean(By, t, False) - edge_mean(By, t, True),
        "delta_Bz_uT_edge": edge_mean(Bz, t, False) - edge_mean(Bz, t, True),
    }


def binned_median_trace(t, *values, bin_s=PLOT_BIN_S):
    t = np.asarray(t)
    values = [np.asarray(v) for v in values]
    if len(t) == 0:
        return (np.array([]),) + tuple(np.array([]) for _ in values)

    t0 = float(np.nanmin(t))
    t1 = float(np.nanmax(t))
    bins = np.arange(t0, t1 + bin_s, bin_s)
    if len(bins) < 2:
        return (t,) + tuple(values)

    centers = []
    out = [[] for _ in values]
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (t >= lo) & (t < hi)
        if not np.any(mask):
            continue
        centers.append((lo + hi) / 2.0)
        for idx, v in enumerate(values):
            out[idx].append(float(np.nanmedian(v[mask])))

    return (np.array(centers),) + tuple(np.array(v) for v in out)


def save_summary(summaries):
    out = REPORTS_DIR / "stage_J_clean_trial_summary.csv"
    fieldnames = list(summaries[0].keys())
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in summaries:
            writer.writerow(row)
    print(f"  -> {out}")


def plot_clean_trials(trials):
    FIGS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(12.2, 7.8))
    ax_force, ax_d, ax_b, ax_sum = axes.ravel()

    summaries = []
    for spec, data in trials:
        t = data["t"] - np.nanmin(data["t"])
        t_plot, F_plot, d_plot, Bmag_plot = binned_median_trace(
            t,
            data["F"] * 1000.0,
            data["d"],
            data["Bmag"],
        )
        dBmag_plot = Bmag_plot - Bmag_plot[0]
        color = spec["color"]
        label = f"{spec['label']} ({spec['session']}, rep{spec['rep']})"

        ax_force.plot(t_plot, F_plot, color=color, lw=1.35, label=label)
        ax_d.plot(t_plot, d_plot, color=color, lw=1.35)
        ax_b.plot(t_plot, dBmag_plot, color=color, lw=1.35)

        summaries.append(summarize_trial(spec, data))

    target_mN = np.nanmedian(trials[0][1]["F_target"]) * 1000.0
    ax_force.axhline(target_mN, color="#444444", ls=":", lw=1.0)
    setup_axis(ax_force, "a  Force held near target", "time (s)", "F (mN)")
    ax_force.legend(fontsize=7, loc="best")

    setup_axis(ax_d, "b  Displacement creep under fixed force", "time (s)", "d (mm)")
    setup_axis(ax_b, "c  Weak magnetic drift during creep", "time (s)", "Delta |B| (uT)")
    ax_b.axhline(0, color="#555555", lw=0.8, alpha=0.5)

    x = np.arange(len(summaries))
    labels = [s["label"] for s in summaries]
    dd = np.array([s["delta_d_mm_edge"] for s in summaries])
    dB = np.array([s["delta_Bmag_uT_edge"] for s in summaries])
    colors = [spec["color"] for spec, _ in trials]

    ax_sum.bar(x - 0.18, dd, width=0.34, color=colors, alpha=0.8, label="Delta d")
    ax_sum.set_ylabel("Delta d (mm)", fontsize=9)
    ax_sum.set_xticks(x, labels)
    setup_axis(ax_sum, "d  Large creep, small magnetic change", None, None)
    ax_sum_b = ax_sum.twinx()
    ax_sum_b.plot(x + 0.18, dB, "o", color="#2a9d55", ms=6, label="Delta |B|")
    ax_sum_b.axhline(0, color="#555555", lw=0.8, alpha=0.4)
    ax_sum_b.set_ylabel("Delta |B| (uT)", fontsize=9, color="#2a9d55")
    ax_sum_b.tick_params(axis="y", labelcolor="#2a9d55")
    ax_sum_b.spines["top"].set_visible(False)

    for xi, yi in zip(x - 0.18, dd):
        ax_sum.text(xi, yi, f"{yi:+.2f}", ha="center", va="bottom", fontsize=7)
    for xi, yi in zip(x + 0.18, dB):
        ax_sum_b.text(xi, yi, f"{yi:+.1f}", ha="center",
                      va="bottom" if yi >= 0 else "top", fontsize=7,
                      color="#2a9d55")

    fig.suptitle(
        "Stage J fixed-force control: displacement changes are much larger than magnetic drift",
        fontsize=11,
        weight="bold",
        y=0.992,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.97])

    out_png = FIGS_DIR / "J_clean_trials.png"
    out_svg = FIGS_DIR / "J_clean_trials.svg"
    fig.savefig(out_png, dpi=220, bbox_inches="tight", facecolor="white")
    fig.savefig(out_svg, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    print(f"  -> {out_png}")
    print(f"  -> {out_svg}")
    save_summary(summaries)
    return summaries


def main():
    loaded = [(spec, load_trial(spec)) for spec in TRIALS]
    summaries = plot_clean_trials(loaded)
    print("\nStage J clean-trial summary:")
    for s in summaries:
        print(
            f"  {s['label']}: {s['session']} rep{s['rep']}, "
            f"F={s['F_mean_N']:.4f} +/- {s['F_std_mN']:.1f} mN, "
            f"Delta d={s['delta_d_mm_edge']:+.3f} mm, "
            f"Delta |B|={s['delta_Bmag_uT_edge']:+.2f} uT"
        )


if __name__ == "__main__":
    main()
