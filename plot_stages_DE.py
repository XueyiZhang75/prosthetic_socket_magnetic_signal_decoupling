"""Generate visualization plots for Stage D and Stage E data.

Defaults: finds the latest session containing each stage's CSV files,
then writes 8 PNGs to reports/figs/:

  Stage D:
    D_overview.png       F vs descent (Phase A & B), F vs d, |B| vs descent
    D_details.png        3-axis B, F vs |B|, dual-axis F&|B|

  Stage E:
    E_main.png           F-d, |B|-d, |B|-F  (the EXPERIMENT_PLAN.md triple)
    E_repeatability.png  mean ±2σ + std across trials, for F and |B|
    E_3axis.png          Bx, By, Bz vs d  (which axis carries the signal)
    E_deltaB.png         ΔBx, ΔBy, ΔBz vs d  (B0 subtracted)
    E_jacobian.png       dF/dd, d|B|/dd, d|B|/dF  (j_q & j_F estimates)

  Cross-stage:
    X_DvsE.png           Stage D Phase B vs Stage E trial 1  (F-d and |B|-d)

Usage:
    python plot_stages_DE.py
    python plot_stages_DE.py --stage-d session_20260525_191114
    python plot_stages_DE.py --stage-e session_20260526_153756
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
OUTPUT_ROOT = HERE / "decouple_data"
FIGS_DIR = HERE / "reports" / "figs"

TRIAL_COLORS = ["#1f77b4", "#d62728", "#2ca02c", "#ff7f0e", "#9467bd"]
PHASE_COLORS = {"approach": "#1f77b4", "probe": "#2ca02c"}


# ============================================================================
# Loaders
# ============================================================================

def _safe_float(x, default=float("nan")):
    try:
        return float(x)
    except (ValueError, TypeError):
        return default


def load_stage_d(session_dir):
    path = session_dir / "D_safety_range.csv"
    if not path.exists():
        return None
    rows = {"phase": [], "step": [], "mark10_pos_mm": [], "d_compression_mm": [],
            "F_mean_N": [], "F_std_N": [],
            "Bx": [], "By": [], "Bz": [], "Bmag": []}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows["phase"].append(r["phase"])
            rows["step"].append(int(r["step"]))
            rows["mark10_pos_mm"].append(_safe_float(r["mark10_pos_mm"]))
            rows["d_compression_mm"].append(_safe_float(r["d_compression_mm"]))
            rows["F_mean_N"].append(_safe_float(r["F_mean_N"]))
            rows["F_std_N"].append(_safe_float(r["F_std_N"]))
            rows["Bx"].append(_safe_float(r["mean_Bx_uT"]))
            rows["By"].append(_safe_float(r["mean_By_uT"]))
            rows["Bz"].append(_safe_float(r["mean_Bz_uT"]))
            rows["Bmag"].append(_safe_float(r["Bmag_uT"]))
    if not rows["step"]:
        return None
    for k in rows:
        if k != "phase":
            rows[k] = np.array(rows[k])
    rows["phase"] = np.array(rows["phase"])
    return rows


def load_stage_e(session_dir):
    """Returns {trial_id: dict of arrays}."""
    trials = {}
    for path in sorted(session_dir.glob("E_basic_loading_rep*.csv")):
        name = path.stem
        try:
            tid = int(name.split("rep")[-1])
        except ValueError:
            continue
        cols = {"d_target_mm": [], "d_actual_mm": [], "mark10_pos_mm": [],
                "F_mean_N": [], "F_std_N": [],
                "Bx": [], "By": [], "Bz": [],
                "Bx_std": [], "By_std": [], "Bz_std": [],
                "dBx": [], "dBy": [], "dBz": [],
                "Bmag": []}
        with open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                cols["d_target_mm"].append(_safe_float(r["d_target_mm"]))
                cols["d_actual_mm"].append(_safe_float(r["d_actual_mm"]))
                cols["mark10_pos_mm"].append(_safe_float(r["mark10_pos_mm"]))
                cols["F_mean_N"].append(_safe_float(r["F_mean_N"]))
                cols["F_std_N"].append(_safe_float(r["F_std_N"]))
                cols["Bx"].append(_safe_float(r["mean_Bx_uT"]))
                cols["By"].append(_safe_float(r["mean_By_uT"]))
                cols["Bz"].append(_safe_float(r["mean_Bz_uT"]))
                cols["Bx_std"].append(_safe_float(r["sigma_Bx_uT"]))
                cols["By_std"].append(_safe_float(r["sigma_By_uT"]))
                cols["Bz_std"].append(_safe_float(r["sigma_Bz_uT"]))
                cols["dBx"].append(_safe_float(r["delta_Bx_uT"]))
                cols["dBy"].append(_safe_float(r["delta_By_uT"]))
                cols["dBz"].append(_safe_float(r["delta_Bz_uT"]))
                cols["Bmag"].append(_safe_float(r["Bmag_uT"]))
        if not cols["d_target_mm"]:
            continue
        for k in cols:
            cols[k] = np.array(cols[k])
        trials[tid] = cols
    return trials


def _find_latest(filename):
    cands = []
    for s in sorted(OUTPUT_ROOT.glob("session_*")):
        if (s / filename).exists():
            cands.append(s)
    return cands[-1] if cands else None


def _setup(ax, title=None, xlabel=None, ylabel=None):
    if title: ax.set_title(title, fontsize=11, pad=8)
    if xlabel: ax.set_xlabel(xlabel, fontsize=10)
    if ylabel: ax.set_ylabel(ylabel, fontsize=10)
    ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)


# ============================================================================
# Stage D plots
# ============================================================================

def plot_stage_d(data, session_dir):
    is_a = data["phase"] == "approach"
    is_b = data["phase"] == "probe"
    pos = data["mark10_pos_mm"]
    descent = -pos                          # mark10 starts at 0, goes negative
    F = data["F_mean_N"]
    Fe = data["F_std_N"] * 2                # +/- 2 sigma
    Bm = data["Bmag"]
    d_cmp = data["d_compression_mm"]

    # --- D_overview.png (2 x 2) ---
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 9))

    # D1: F vs descent (Phase A only) -- magnetic attraction approach
    ax = axes[0, 0]
    if is_a.any():
        ax.errorbar(descent[is_a], F[is_a] * 1000, yerr=Fe[is_a] * 1000,
                    fmt="o-", color=PHASE_COLORS["approach"],
                    markersize=4, capsize=2, linewidth=1.3, label="approach")
    ax.axhline(25, color="#d62728", ls="--", alpha=0.5, lw=1,
               label="±25 mN threshold")
    ax.axhline(-25, color="#d62728", ls="--", alpha=0.5, lw=1)
    ax.axhline(0, color="black", alpha=0.3, lw=0.7)
    _setup(ax, title="D1: F vs descent  (Phase A — approach)",
           xlabel="descent (mm)", ylabel="F (mN)")
    ax.legend(loc="lower left", fontsize=9)

    # D2: F vs d_compression (Phase B only)
    ax = axes[0, 1]
    if is_b.any():
        ax.errorbar(d_cmp[is_b], F[is_b], yerr=Fe[is_b],
                    fmt="o-", color=PHASE_COLORS["probe"],
                    markersize=5, capsize=3, linewidth=1.3)
    ax.axhline(0, color="black", alpha=0.3, lw=0.7)
    _setup(ax, title="D2: F vs d  (Phase B — probe / loading curve)",
           xlabel="d_compression (mm)", ylabel="F (N)")

    # D3: F vs descent (combined, full sweep)
    ax = axes[1, 0]
    if is_a.any():
        ax.plot(descent[is_a], F[is_a], "o-", color=PHASE_COLORS["approach"],
                markersize=4, linewidth=1.2, label="approach")
    if is_b.any():
        ax.plot(descent[is_b], F[is_b], "s-", color=PHASE_COLORS["probe"],
                markersize=5, linewidth=1.3, label="probe")
    ax.axhline(0, color="black", alpha=0.3, lw=0.7)
    _setup(ax, title="D3: F vs descent  (full sweep)",
           xlabel="descent (mm)", ylabel="F (N)")
    ax.legend(loc="upper left", fontsize=9)

    # D4: |B| vs descent (full sweep)
    ax = axes[1, 1]
    if is_a.any():
        ax.plot(descent[is_a], Bm[is_a], "o-", color=PHASE_COLORS["approach"],
                markersize=4, linewidth=1.2, label="approach")
    if is_b.any():
        ax.plot(descent[is_b], Bm[is_b], "s-", color=PHASE_COLORS["probe"],
                markersize=5, linewidth=1.3, label="probe")
    _setup(ax, title="D4: |B| vs descent  (full sweep)",
           xlabel="descent (mm)", ylabel="|B| (µT)")
    ax.legend(loc="best", fontsize=9)

    fig.suptitle(f"Stage D — safety range probe  ({session_dir.name})",
                 fontsize=13, weight="bold", y=0.995)
    fig.tight_layout()
    out = FIGS_DIR / "D_overview.png"
    fig.savefig(out, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out}")

    # --- D_details.png (1 x 3) ---
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2))

    # D5: 3-axis B vs descent
    ax = axes[0]
    for color, key, label in [("#d62728", "Bx", "Bx"),
                               ("#2ca02c", "By", "By"),
                               ("#1f77b4", "Bz", "Bz")]:
        if is_a.any():
            ax.plot(descent[is_a], data[key][is_a], "o-", color=color,
                    markersize=3, lw=1, alpha=0.55,
                    label=f"{label} (approach)")
        if is_b.any():
            ax.plot(descent[is_b], data[key][is_b], "s-", color=color,
                    markersize=4, lw=1.3, alpha=1.0,
                    label=f"{label} (probe)")
    ax.axhline(0, color="black", alpha=0.3, lw=0.7)
    _setup(ax, title="D5: 3-axis B vs descent",
           xlabel="descent (mm)", ylabel="B (µT)")
    ax.legend(loc="best", fontsize=8, ncol=2)

    # D6: F vs |B| cross-plot
    ax = axes[1]
    if is_a.any():
        ax.plot(F[is_a], Bm[is_a], "o-", color=PHASE_COLORS["approach"],
                markersize=4, linewidth=1.2, label="approach")
    if is_b.any():
        ax.plot(F[is_b], Bm[is_b], "s-", color=PHASE_COLORS["probe"],
                markersize=5, linewidth=1.3, label="probe")
    _setup(ax, title="D6: |B| vs F  (cross-plot)",
           xlabel="F (N)", ylabel="|B| (µT)")
    ax.legend(loc="best", fontsize=9)

    # D7: F & |B| dual y-axis vs descent
    ax = axes[2]
    ax2 = ax.twinx()
    if is_a.any():
        ax.plot(descent[is_a], F[is_a], "o-",
                color=PHASE_COLORS["approach"], markersize=3, alpha=0.7)
        ax2.plot(descent[is_a], Bm[is_a], "x:",
                 color="#d62728", markersize=4, alpha=0.7)
    if is_b.any():
        ax.plot(descent[is_b], F[is_b], "s-",
                color=PHASE_COLORS["probe"], markersize=4, label="F")
        ax2.plot(descent[is_b], Bm[is_b], "^:",
                 color="#d62728", markersize=4, label="|B|")
    ax.set_xlabel("descent (mm)", fontsize=10)
    ax.set_ylabel("F (N)", color=PHASE_COLORS["probe"], fontsize=10)
    ax2.set_ylabel("|B| (µT)", color="#d62728", fontsize=10)
    ax.set_title("D7: F & |B| vs descent  (dual axis)", fontsize=11, pad=8)
    ax.grid(True, alpha=0.3, ls="--", lw=0.5)
    ax.axhline(0, color="black", alpha=0.3, lw=0.7)

    fig.suptitle(f"Stage D — details  ({session_dir.name})",
                 fontsize=13, weight="bold", y=0.995)
    fig.tight_layout()
    out = FIGS_DIR / "D_details.png"
    fig.savefig(out, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out}")


# ============================================================================
# Stage E plots
# ============================================================================

def plot_stage_e(trials, session_dir):
    if not trials:
        print("  no Stage E trial data")
        return
    tids = sorted(trials.keys())

    # --- E_main.png  (F-d | |B|-d | |B|-F) ---
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2))

    # E1: F vs d
    ax = axes[0]
    for i, t in enumerate(tids):
        d = trials[t]["d_actual_mm"]; F = trials[t]["F_mean_N"]
        Fe = trials[t]["F_std_N"] * 2
        ax.errorbar(d, F, yerr=Fe, fmt="o-",
                    color=TRIAL_COLORS[i % len(TRIAL_COLORS)],
                    markersize=5, capsize=3, lw=1.3, label=f"trial {t}")
    ax.axhline(0, color="black", alpha=0.3, lw=0.7)
    _setup(ax, title="E1: F vs d  (mechanical loading curve)",
           xlabel="d (mm)", ylabel="F (N)")
    ax.legend(loc="best", fontsize=9)

    # E2: |B| vs d
    ax = axes[1]
    for i, t in enumerate(tids):
        d = trials[t]["d_actual_mm"]; B = trials[t]["Bmag"]
        ax.plot(d, B, "o-", color=TRIAL_COLORS[i % len(TRIAL_COLORS)],
                markersize=5, lw=1.3, label=f"trial {t}")
    _setup(ax, title="E2: |B| vs d  (magnetic mechanism)",
           xlabel="d (mm)", ylabel="|B| (µT)")
    ax.legend(loc="best", fontsize=9)

    # E3: |B| vs F  (APMD main)
    ax = axes[2]
    for i, t in enumerate(tids):
        F = trials[t]["F_mean_N"]; B = trials[t]["Bmag"]
        ax.plot(F, B, "o-", color=TRIAL_COLORS[i % len(TRIAL_COLORS)],
                markersize=5, lw=1.3, label=f"trial {t}")
        if len(F) >= 2:
            ax.annotate("", xy=(F[1], B[1]), xytext=(F[0], B[0]),
                        arrowprops=dict(arrowstyle="->",
                                        color=TRIAL_COLORS[i % len(TRIAL_COLORS)],
                                        alpha=0.6, lw=1.2))
    _setup(ax, title="E3: |B| vs F  (APMD main)",
           xlabel="F (N)", ylabel="|B| (µT)")
    ax.legend(loc="best", fontsize=9)

    fig.suptitle(f"Stage E — main loading curves  ({session_dir.name})",
                 fontsize=13, weight="bold", y=0.995)
    fig.tight_layout()
    out = FIGS_DIR / "E_main.png"
    fig.savefig(out, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out}")

    # --- E_repeatability.png  (F std vs d | |B| std vs d) ---
    # Align by index across trials (truncate to shortest)
    n_min = min(len(trials[t]["d_target_mm"]) for t in tids)
    F_arr = np.array([trials[t]["F_mean_N"][:n_min] for t in tids])
    B_arr = np.array([trials[t]["Bmag"][:n_min] for t in tids])
    d_tgt = trials[tids[0]]["d_target_mm"][:n_min]

    if len(tids) >= 2:
        F_std_across = F_arr.std(axis=0, ddof=1)
        B_std_across = B_arr.std(axis=0, ddof=1)
        F_mean_across = F_arr.mean(axis=0)
        B_mean_across = B_arr.mean(axis=0)
    else:
        F_std_across = np.zeros(n_min)
        B_std_across = np.zeros(n_min)
        F_mean_across = F_arr[0]; B_mean_across = B_arr[0]

    fig, axes = plt.subplots(2, 2, figsize=(12.5, 9))

    # Top-left: F mean ± 2σ band + individual trials
    ax = axes[0, 0]
    ax.fill_between(d_tgt, (F_mean_across - 2 * F_std_across),
                    (F_mean_across + 2 * F_std_across),
                    alpha=0.18, color="gray", label="±2σ across trials")
    ax.plot(d_tgt, F_mean_across, "k-", lw=2, label="mean")
    for i, t in enumerate(tids):
        ax.plot(d_tgt, F_arr[i], "o", color=TRIAL_COLORS[i % len(TRIAL_COLORS)],
                markersize=4, alpha=0.7, label=f"trial {t}")
    _setup(ax, title="E4a: F vs d  (mean ±2σ across trials)",
           xlabel="d_target (mm)", ylabel="F (N)")
    ax.axhline(0, color="black", alpha=0.3, lw=0.7)
    ax.legend(loc="best", fontsize=9)

    # Top-right: F std across trials
    ax = axes[0, 1]
    ax.plot(d_tgt, F_std_across * 1000, "o-", color="#1f77b4",
            markersize=5, lw=1.3)
    _setup(ax, title="E4b: std(F) across trials vs d",
           xlabel="d_target (mm)", ylabel="std(F) (mN)")

    # Bottom-left: |B| mean ± 2σ band + individual trials
    ax = axes[1, 0]
    ax.fill_between(d_tgt, B_mean_across - 2 * B_std_across,
                    B_mean_across + 2 * B_std_across,
                    alpha=0.18, color="gray", label="±2σ across trials")
    ax.plot(d_tgt, B_mean_across, "k-", lw=2, label="mean")
    for i, t in enumerate(tids):
        ax.plot(d_tgt, B_arr[i], "o", color=TRIAL_COLORS[i % len(TRIAL_COLORS)],
                markersize=4, alpha=0.7, label=f"trial {t}")
    _setup(ax, title="E5a: |B| vs d  (mean ±2σ across trials)",
           xlabel="d_target (mm)", ylabel="|B| (µT)")
    ax.legend(loc="best", fontsize=9)

    # Bottom-right: |B| std across trials
    ax = axes[1, 1]
    ax.plot(d_tgt, B_std_across, "o-", color="#d62728",
            markersize=5, lw=1.3)
    _setup(ax, title="E5b: std(|B|) across trials vs d",
           xlabel="d_target (mm)", ylabel="std(|B|) (µT)")

    fig.suptitle(f"Stage E — repeatability  ({session_dir.name})",
                 fontsize=13, weight="bold", y=0.995)
    fig.tight_layout()
    out = FIGS_DIR / "E_repeatability.png"
    fig.savefig(out, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out}")

    # --- E_jacobian.png  (dF/dd | d|B|/dd | d|B|/dF) ---
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2))

    # E8: dF/dd vs d  (local stiffness)
    ax = axes[0]
    for i, t in enumerate(tids):
        d = trials[t]["d_actual_mm"]; F = trials[t]["F_mean_N"]
        if len(d) < 2:
            continue
        dFdd = np.gradient(F, d)
        ax.plot(d, dFdd, "o-", color=TRIAL_COLORS[i % len(TRIAL_COLORS)],
                markersize=4, lw=1.2, label=f"trial {t}")
    _setup(ax, title="E8: dF/dd vs d  (local stiffness)",
           xlabel="d (mm)", ylabel="dF/dd (N/mm)")
    ax.axhline(0, color="black", alpha=0.3, lw=0.7)
    ax.legend(loc="best", fontsize=9)

    # E10: d|B|/dd vs d  (j_q estimate along loading)
    ax = axes[1]
    for i, t in enumerate(tids):
        d = trials[t]["d_actual_mm"]; B = trials[t]["Bmag"]
        if len(d) < 2:
            continue
        dBdd = np.gradient(B, d)
        ax.plot(d, dBdd, "o-", color=TRIAL_COLORS[i % len(TRIAL_COLORS)],
                markersize=4, lw=1.2, label=f"trial {t}")
    _setup(ax, title="E10: d|B|/dd vs d  (j_q estimate)",
           xlabel="d (mm)", ylabel="d|B|/dd (µT/mm)")
    ax.axhline(0, color="black", alpha=0.3, lw=0.7)
    ax.legend(loc="best", fontsize=9)

    # E9: d|B|/dF vs F  (B-F coupling slope)
    ax = axes[2]
    for i, t in enumerate(tids):
        F = trials[t]["F_mean_N"]; B = trials[t]["Bmag"]
        if len(F) < 2:
            continue
        # Skip points where F is duplicate or non-monotonic
        order = np.argsort(F)
        F_sorted = F[order]; B_sorted = B[order]
        # Remove duplicate F values
        keep = np.concatenate([[True], np.diff(F_sorted) > 1e-6])
        F_sorted = F_sorted[keep]; B_sorted = B_sorted[keep]
        if len(F_sorted) < 2:
            continue
        dBdF = np.gradient(B_sorted, F_sorted)
        ax.plot(F_sorted, dBdF, "o-",
                color=TRIAL_COLORS[i % len(TRIAL_COLORS)],
                markersize=4, lw=1.2, label=f"trial {t}")
    _setup(ax, title="E9: d|B|/dF vs F  (B-F coupling slope)",
           xlabel="F (N)", ylabel="d|B|/dF (µT/N)")
    ax.axhline(0, color="black", alpha=0.3, lw=0.7)
    ax.legend(loc="best", fontsize=9)

    fig.suptitle(f"Stage E — derivatives & coupling  ({session_dir.name})",
                 fontsize=13, weight="bold", y=0.995)
    fig.tight_layout()
    out = FIGS_DIR / "E_jacobian.png"
    fig.savefig(out, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out}")

    # --- E_3axis.png  (Bx, By, Bz vs d  — which axis carries the signal) ---
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2))
    for axis_idx, (key, label, color) in enumerate(
        [("Bx", "Bx", "#d62728"),
         ("By", "By", "#2ca02c"),
         ("Bz", "Bz", "#1f77b4")]
    ):
        ax = axes[axis_idx]
        for i, t in enumerate(tids):
            d = trials[t]["d_actual_mm"]
            B = trials[t][key]
            Be = trials[t][key + "_std"] * 2
            ax.errorbar(d, B, yerr=Be, fmt="o-",
                        color=TRIAL_COLORS[i % len(TRIAL_COLORS)],
                        markersize=4, capsize=2, lw=1.2,
                        label=f"trial {t}")
        ax.axhline(0, color="black", alpha=0.3, lw=0.7)
        _setup(ax, title=f"E6{'abc'[axis_idx]}: {label} vs d",
               xlabel="d (mm)", ylabel=f"{label} (µT)")
        ax.legend(loc="best", fontsize=9)
    fig.suptitle(f"Stage E — 3-axis B vs d  ({session_dir.name})",
                 fontsize=13, weight="bold", y=0.995)
    fig.tight_layout()
    out = FIGS_DIR / "E_3axis.png"
    fig.savefig(out, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out}")

    # --- E_deltaB.png  (ΔBx, ΔBy, ΔBz vs d  — B0 subtracted) ---
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2))
    for axis_idx, (key, label, color) in enumerate(
        [("dBx", "ΔBx", "#d62728"),
         ("dBy", "ΔBy", "#2ca02c"),
         ("dBz", "ΔBz", "#1f77b4")]
    ):
        ax = axes[axis_idx]
        for i, t in enumerate(tids):
            d = trials[t]["d_actual_mm"]
            dB = trials[t][key]
            ax.plot(d, dB, "o-",
                    color=TRIAL_COLORS[i % len(TRIAL_COLORS)],
                    markersize=4, lw=1.3, label=f"trial {t}")
        ax.axhline(0, color="black", alpha=0.3, lw=0.7)
        _setup(ax, title=f"E7{'abc'[axis_idx]}: {label} vs d  (B0 subtracted)",
               xlabel="d (mm)", ylabel=f"{label} (µT)")
        ax.legend(loc="best", fontsize=9)
    fig.suptitle(f"Stage E — ΔB vs d  ({session_dir.name})",
                 fontsize=13, weight="bold", y=0.995)
    fig.tight_layout()
    out = FIGS_DIR / "E_deltaB.png"
    fig.savefig(out, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out}")


# ============================================================================
# Cross-stage comparison (D Phase B vs E trial 1)
# ============================================================================

def plot_cross(d_data, e_trials, d_session, e_session):
    """X1: Stage D Phase B F-d  vs  Stage E F-d (all trials)
       X2: Stage D Phase B |B|-d vs Stage E |B|-d (all trials)

    Caveat: D's d=0 and E's d=0 are not the same physical point (contact
    detection drifts session-to-session), so this is a qualitative trend
    comparison only.
    """
    if d_data is None or not e_trials:
        return
    is_b = d_data["phase"] == "probe"
    if not is_b.any():
        return
    d_D = d_data["d_compression_mm"][is_b]
    F_D = d_data["F_mean_N"][is_b]
    Fe_D = d_data["F_std_N"][is_b] * 2
    B_D = d_data["Bmag"][is_b]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4))

    # X1: F-d
    ax = axes[0]
    ax.errorbar(d_D, F_D, yerr=Fe_D, fmt="s-", color="#7f7f7f",
                markersize=5, capsize=3, lw=1.4,
                label=f"Stage D probe ({d_session.name[-6:]})")
    for i, t in enumerate(sorted(e_trials.keys())):
        d = e_trials[t]["d_actual_mm"]
        F = e_trials[t]["F_mean_N"]
        Fe = e_trials[t]["F_std_N"] * 2
        ax.errorbar(d, F, yerr=Fe, fmt="o-",
                    color=TRIAL_COLORS[i % len(TRIAL_COLORS)],
                    markersize=4, capsize=2, lw=1.2, alpha=0.85,
                    label=f"Stage E trial {t}")
    ax.axhline(0, color="black", alpha=0.3, lw=0.7)
    _setup(ax, title="X1: F vs d  —  Stage D probe vs Stage E",
           xlabel="d (mm)", ylabel="F (N)")
    ax.legend(loc="best", fontsize=9)

    # X2: |B|-d
    ax = axes[1]
    ax.plot(d_D, B_D, "s-", color="#7f7f7f", markersize=5, lw=1.4,
            label=f"Stage D probe ({d_session.name[-6:]})")
    for i, t in enumerate(sorted(e_trials.keys())):
        d = e_trials[t]["d_actual_mm"]
        B = e_trials[t]["Bmag"]
        ax.plot(d, B, "o-",
                color=TRIAL_COLORS[i % len(TRIAL_COLORS)],
                markersize=4, lw=1.2, alpha=0.85,
                label=f"Stage E trial {t}")
    _setup(ax, title="X2: |B| vs d  —  Stage D probe vs Stage E",
           xlabel="d (mm)", ylabel="|B| (µT)")
    ax.legend(loc="best", fontsize=9)

    fig.suptitle("Cross-stage trend comparison  "
                 "(d=0 is NOT the same physical point — qualitative only)",
                 fontsize=12, weight="bold", y=0.995)
    fig.tight_layout()
    out = FIGS_DIR / "X_DvsE.png"
    fig.savefig(out, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out}")


# ============================================================================
# Main
# ============================================================================

def main():
    FIGS_DIR.mkdir(parents=True, exist_ok=True)
    args = sys.argv[1:]
    d_session = e_session = None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--stage-d" and i + 1 < len(args):
            d_session = OUTPUT_ROOT / args[i + 1]; i += 2
        elif a == "--stage-e" and i + 1 < len(args):
            e_session = OUTPUT_ROOT / args[i + 1]; i += 2
        else:
            i += 1

    if d_session is None:
        d_session = _find_latest("D_safety_range.csv")
    if e_session is None:
        e_session = _find_latest("E_basic_loading_rep1.csv")

    d_data = None
    e_trials = {}

    print("\n=== Stage D ===")
    if d_session is None or not d_session.exists():
        print("  no Stage D session found")
    else:
        print(f"  session: {d_session.name}")
        d_data = load_stage_d(d_session)
        if d_data is None:
            print("  (no usable rows)")
        else:
            n_a = int((d_data["phase"] == "approach").sum())
            n_b = int((d_data["phase"] == "probe").sum())
            print(f"  rows: {n_a} approach + {n_b} probe")
            plot_stage_d(d_data, d_session)

    print("\n=== Stage E ===")
    if e_session is None or not e_session.exists():
        print("  no Stage E session found")
    else:
        print(f"  session: {e_session.name}")
        e_trials = load_stage_e(e_session)
        if not e_trials:
            print("  (no rep CSVs found)")
        else:
            for t in sorted(e_trials.keys()):
                print(f"  trial {t}: {len(e_trials[t]['d_target_mm'])} points")
            plot_stage_e(e_trials, e_session)

    print("\n=== Cross-stage D vs E ===")
    if d_data is not None and e_trials:
        plot_cross(d_data, e_trials, d_session, e_session)
    else:
        print("  skipped (need both Stage D and Stage E data)")

    print("\nDone.")


if __name__ == "__main__":
    main()
