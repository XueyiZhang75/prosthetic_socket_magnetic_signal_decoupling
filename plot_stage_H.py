"""Generate Stage H pseudo force-control plots.

Reads H_force_control_rep*.csv from the latest Stage H session and writes:

  reports/figs/H_main.png
      H1: actual F vs target F, H2: |B| vs actual F,
      H3: d vs actual F, H4: target error vs target F.

  reports/figs/H_3axis.png
      Bx/By/Bz vs actual F.

  reports/figs/H_compare_EFH.png
      Qualitative B-F comparison against latest Stage E and Stage F sessions.

Important: Stage H should be interpreted using F_mean_N (actual force), not
F_target_N, because the temporary pseudo-force loop may fail to reach some
requested targets before hitting the displacement soft limit.
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

TRIAL_COLORS = ["#1f77b4", "#d62728", "#2ca02c"]


def _safe_float(x, default=float("nan")):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _find_latest_with(pattern):
    for s in sorted(OUTPUT_ROOT.glob("session_*"), reverse=True):
        if list(s.glob(pattern)):
            return s
    return None


def _setup(ax, title=None, xlabel=None, ylabel=None):
    if title:
        ax.set_title(title, fontsize=11, pad=8)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=10)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=10)
    ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)


def load_stage_h(session_dir):
    trials = {}
    for path in sorted(session_dir.glob("H_force_control_rep*.csv")):
        try:
            trial = int(path.stem.split("rep")[-1])
        except ValueError:
            continue

        rows = []
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows.append({
                    "trial": trial,
                    "step": int(r["step"]),
                    "target_F": _safe_float(r["F_target_N"]),
                    "F": _safe_float(r["F_mean_N"]),
                    "F_err": _safe_float(r["F_error_N"]),
                    "F_std": _safe_float(r["F_std_N"]),
                    "d": _safe_float(r["d_actual_mm"]),
                    "Bmag": _safe_float(r["Bmag_uT"]),
                    "Bx": _safe_float(r["mean_Bx_uT"]),
                    "By": _safe_float(r["mean_By_uT"]),
                    "Bz": _safe_float(r["mean_Bz_uT"]),
                    "reached": int(r["target_reached"]),
                    "status": r["status"],
                    "iters": int(r["control_iters"]),
                })
        if rows:
            trials[trial] = rows
    return trials


def load_stage_e(session_dir):
    out = []
    if session_dir is None:
        return out
    for path in sorted(session_dir.glob("E_basic_loading_rep*.csv")):
        try:
            trial = int(path.stem.split("rep")[-1])
        except ValueError:
            trial = 0
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                B = _safe_float(r.get("Bmag_uT"))
                F = _safe_float(r.get("F_mean_N"))
                if np.isfinite(B) and np.isfinite(F):
                    out.append((trial, F, B))
    return out


def load_stage_f(session_dir):
    out = []
    if session_dir is None:
        return out
    for path in sorted(session_dir.glob("F_load_unload_rep*.csv")):
        try:
            trial = int(path.stem.split("rep")[-1])
        except ValueError:
            trial = 0
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                B = _safe_float(r.get("Bmag_uT"))
                F = _safe_float(r.get("F_mean_N"))
                d = _safe_float(r.get("d_actual_mm"))
                if np.isfinite(B) and np.isfinite(F) and d >= -0.25:
                    out.append((trial, r.get("phase", ""), F, B))
    return out


def plot_main(trials, session_dir):
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 9.5))
    axes = axes.ravel()

    for i, trial in enumerate(sorted(trials)):
        rows = trials[trial]
        color = TRIAL_COLORS[i % len(TRIAL_COLORS)]
        target = np.array([r["target_F"] for r in rows])
        F = np.array([r["F"] for r in rows])
        B = np.array([r["Bmag"] for r in rows])
        d = np.array([r["d"] for r in rows])
        err = np.array([r["F_err"] for r in rows])
        reached = np.array([r["reached"] for r in rows], dtype=bool)

        axes[0].plot(target, F, "o-", color=color, lw=1.3,
                     label=f"trial {trial}")
        axes[0].scatter(target[~reached], F[~reached], s=62,
                        facecolors="none", edgecolors=color, linewidths=1.2)

        axes[1].plot(F, B, "o-", color=color, lw=1.3,
                     label=f"trial {trial}")
        axes[1].scatter(F[~reached], B[~reached], s=62,
                        facecolors="none", edgecolors=color, linewidths=1.2)

        axes[2].plot(F, d, "o-", color=color, lw=1.3,
                     label=f"trial {trial}")
        axes[2].scatter(F[~reached], d[~reached], s=62,
                        facecolors="none", edgecolors=color, linewidths=1.2)

        axes[3].plot(target, err * 1000, "o-", color=color, lw=1.3,
                     label=f"trial {trial}")
        axes[3].scatter(target[~reached], err[~reached] * 1000, s=62,
                        facecolors="none", edgecolors=color, linewidths=1.2)

    all_targets = np.concatenate([
        np.array([r["target_F"] for r in rows])
        for rows in trials.values()
    ])
    lo, hi = np.nanmin(all_targets), np.nanmax(all_targets)
    axes[0].plot([lo, hi], [lo, hi], "k:", lw=1.0, label="ideal")

    _setup(axes[0], "H1: actual F vs target F",
           "F_target (N)", "F_actual (N)")
    axes[0].legend(fontsize=8)

    _setup(axes[1], "H2: |B| vs actual F  (force-control B-F)",
           "F_actual (N)", "|B| (µT)")
    axes[1].legend(fontsize=8)

    _setup(axes[2], "H3: d vs actual F",
           "F_actual (N)", "d_actual (mm)")
    axes[2].legend(fontsize=8)

    axes[3].axhline(0, color="black", alpha=0.4, lw=0.8)
    _setup(axes[3], "H4: force target error",
           "F_target (N)", "F_actual - F_target (mN)")
    axes[3].legend(fontsize=8)

    fig.suptitle(
        f"Stage H — pseudo force-control plateaus  ({session_dir.name})\n"
        "filled markers = target reached; open markers = actual plateau recorded but target not reached",
        fontsize=13, weight="bold", y=0.995,
    )
    fig.tight_layout()
    out = FIGS_DIR / "H_main.png"
    fig.savefig(out, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out}")


def plot_3axis(trials, session_dir):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2))
    for ax_i, key in enumerate(("Bx", "By", "Bz")):
        ax = axes[ax_i]
        for i, trial in enumerate(sorted(trials)):
            rows = trials[trial]
            color = TRIAL_COLORS[i % len(TRIAL_COLORS)]
            F = np.array([r["F"] for r in rows])
            Y = np.array([r[key] for r in rows])
            reached = np.array([r["reached"] for r in rows], dtype=bool)
            ax.plot(F, Y, "o-", color=color, lw=1.2,
                    label=f"trial {trial}")
            ax.scatter(F[~reached], Y[~reached], s=54,
                       facecolors="none", edgecolors=color, linewidths=1.1)
        ax.axhline(0, color="black", alpha=0.3, lw=0.7)
        _setup(ax, f"H5{'abc'[ax_i]}: {key} vs actual F",
               "F_actual (N)", f"{key} (µT)")
        if ax_i == 0:
            ax.legend(fontsize=8)

    fig.suptitle(f"Stage H — 3-axis B under pseudo force control  ({session_dir.name})",
                 fontsize=13, weight="bold", y=0.995)
    fig.tight_layout()
    out = FIGS_DIR / "H_3axis.png"
    fig.savefig(out, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out}")


def plot_compare(trials, h_session):
    e_session = _find_latest_with("E_basic_loading_rep*.csv")
    f_session = _find_latest_with("F_load_unload_rep*.csv")
    e_rows = load_stage_e(e_session)
    f_rows = load_stage_f(f_session)

    fig, ax = plt.subplots(1, 1, figsize=(8.5, 6.2))

    if e_rows:
        F = np.array([r[1] for r in e_rows])
        B = np.array([r[2] for r in e_rows])
        ax.plot(F, B, ".", color="#777777", alpha=0.45,
                label=f"Stage E disp-control ({e_session.name})")

    if f_rows:
        for phase, color, marker in (
            ("loading", "#1f77b4", "o"),
            ("unloading", "#ff7f0e", "s"),
        ):
            rows = [r for r in f_rows if r[1] == phase]
            if rows:
                F = np.array([r[2] for r in rows])
                B = np.array([r[3] for r in rows])
                ax.plot(F, B, marker, ms=3.5, linestyle="none",
                        color=color, alpha=0.45,
                        label=f"Stage F {phase} ({f_session.name})")

    for i, trial in enumerate(sorted(trials)):
        rows = trials[trial]
        color = TRIAL_COLORS[i % len(TRIAL_COLORS)]
        F = np.array([r["F"] for r in rows])
        B = np.array([r["Bmag"] for r in rows])
        ax.plot(F, B, "o-", color=color, lw=1.4,
                label=f"Stage H trial {trial}")

    _setup(ax, "H6: qualitative B-F comparison",
           "F_actual (N)", "|B| (µT)")
    ax.legend(fontsize=8)
    ax.text(
        0.02, 0.02,
        "Caveat: sessions may have different B0/contact geometry;\n"
        "compare trend shape, not absolute calibration.",
        transform=ax.transAxes,
        fontsize=8,
        va="bottom",
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#cccccc", alpha=0.85),
    )

    fig.suptitle(f"Stage H vs previous E/F  ({h_session.name})",
                 fontsize=13, weight="bold", y=0.995)
    fig.tight_layout()
    out = FIGS_DIR / "H_compare_EFH.png"
    fig.savefig(out, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out}")


def main():
    FIGS_DIR.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) > 1:
        session = OUTPUT_ROOT / sys.argv[1]
    else:
        session = _find_latest_with("H_force_control_rep*.csv")

    if session is None or not session.exists():
        print("No Stage H session found.")
        return

    print(f"\n=== Stage H ===\n  session: {session.name}")
    trials = load_stage_h(session)
    if not trials:
        print("  (no H_force_control_rep*.csv rows found)")
        return

    for trial in sorted(trials):
        rows = trials[trial]
        n_reached = sum(r["reached"] for r in rows)
        max_f = max(r["F"] for r in rows)
        print(f"  trial {trial}: {len(rows)} points, "
              f"{n_reached} targets reached, max actual F={max_f:.3f} N")

    plot_main(trials, session)
    plot_3axis(trials, session)
    plot_compare(trials, session)
    print("\nDone.")


if __name__ == "__main__":
    main()
