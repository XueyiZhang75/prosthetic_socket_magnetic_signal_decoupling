"""Generate Stage F (load-unload hysteresis) plots.

Reads F_load_unload_rep{1,2,3}.csv from the latest Stage F session and
writes 3 PNGs to reports/figs/:

  F_main.png       F-d, |B|-d, |B|-F  with loading vs unloading
  F_3axis.png      Bx/By/Bz vs d, loading vs unloading
  F_loop_size.png  ΔF(d), Δ|B|(d)  -- hysteresis amplitude across trials

All plots use d_actual (not d_target) on the x-axis. Early Stage F signal-test
sessions skipped the repeated d_max point on unloading, so dotted connectors in
F_main.png are visual guides, not measured plateau points. Updated Stage F runs
measure d_max on both branches.
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
PHASE_STYLE = {
    "loading":   {"marker": "o", "ls": "-",  "alpha": 1.0, "label": "loading"},
    "unloading": {"marker": "s", "ls": "--", "alpha": 0.85, "label": "unloading"},
}


def _safe_float(x, default=float("nan")):
    try:
        return float(x)
    except (ValueError, TypeError):
        return default


def load_stage_f(session_dir):
    """Returns {trial_id: {phase: {col: np.array}}}."""
    out = {}
    for path in sorted(session_dir.glob("F_load_unload_rep*.csv")):
        try:
            tid = int(path.stem.split("rep")[-1])
        except ValueError:
            continue
        rows = []
        with open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows.append(r)
        if not rows:
            continue
        trial = {}
        for phase in ("loading", "unloading"):
            ph_rows = [r for r in rows if r["phase"] == phase]
            if not ph_rows:
                continue
            cols = {
                "d_target": np.array([_safe_float(r["d_target_mm"]) for r in ph_rows]),
                "d_actual": np.array([_safe_float(r["d_actual_mm"]) for r in ph_rows]),
                "F": np.array([_safe_float(r["F_mean_N"]) for r in ph_rows]),
                "F_std": np.array([_safe_float(r["F_std_N"]) for r in ph_rows]),
                "Bx": np.array([_safe_float(r["mean_Bx_uT"]) for r in ph_rows]),
                "By": np.array([_safe_float(r["mean_By_uT"]) for r in ph_rows]),
                "Bz": np.array([_safe_float(r["mean_Bz_uT"]) for r in ph_rows]),
                "Bmag": np.array([_safe_float(r["Bmag_uT"]) for r in ph_rows]),
            }
            d_limit = np.nanmax(cols["d_target"]) + 0.75
            valid = (np.isfinite(cols["d_actual"]) &
                     (cols["d_actual"] >= -0.25) &
                     (cols["d_actual"] <= d_limit))
            for key in cols:
                cols[key] = cols[key][valid]
            if len(cols["F"]) == 0:
                continue
            trial[phase] = cols
        out[tid] = trial
    return out


def has_finite_b(trials):
    for trial in trials.values():
        for data in trial.values():
            if np.isfinite(data["Bmag"]).any():
                return True
    return False


def _find_latest_stage_f(require_finite_b=True):
    for s in sorted(OUTPUT_ROOT.glob("session_*"), reverse=True):
        if not (s / "F_load_unload_rep1.csv").exists():
            continue
        if not require_finite_b:
            return s
        if has_finite_b(load_stage_f(s)):
            return s
    return None


def _setup(ax, title=None, xlabel=None, ylabel=None):
    if title: ax.set_title(title, fontsize=11, pad=8)
    if xlabel: ax.set_xlabel(xlabel, fontsize=10)
    if ylabel: ax.set_ylabel(ylabel, fontsize=10)
    ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)


def finite_xy(x, y):
    mask = np.isfinite(x) & np.isfinite(y)
    return x[mask], y[mask]


def draw_connected_loop(ax, load, unlo, x_key, y_key, color, label,
                        show_arrows=True):
    """Draw one Stage F loop as measured branches plus dotted connectors.

    Loading and unloading are measured as separate plateau branches. Some early
    Stage F sessions skipped the repeated d_max unloading point, so a connector
    from the loading end to the first unloading point may be an unmeasured
    transition. Likewise, the final unloading point may not return exactly to
    the first loading point because the temporary fixture has residual drift.
    Dotted connectors make that explicit while still showing the loop topology.
    """
    x_load, y_load = finite_xy(load[x_key], load[y_key])
    x_unlo, y_unlo = finite_xy(unlo[x_key], unlo[y_key])
    if len(x_load) == 0 or len(x_unlo) == 0:
        return

    # Measured branches.
    ax.plot(x_load, y_load, "o-", color=color, markersize=5, lw=1.6,
            alpha=0.95, label=f"{label} loading")
    ax.plot(x_unlo, y_unlo, "s--", color=color, markersize=5, lw=1.6,
            alpha=0.85, label=f"{label} unloading")

    # Transition from max compression to first unload plateau. In older
    # sessions this may be unmeasured because unloading skipped d_max.
    ax.plot([x_load[-1], x_unlo[0]], [y_load[-1], y_unlo[0]],
            ":", color=color, lw=1.2, alpha=0.65)

    # Residual closure from final unload to first load. This is not forced to
    # be zero; any gap is a useful drift/recovery diagnostic.
    ax.plot([x_unlo[-1], x_load[0]], [y_unlo[-1], y_load[0]],
            ":", color=color, lw=1.0, alpha=0.45)

    # Direction arrows at representative branch segments.
    if not show_arrows:
        return
    for x, y, frac in ((x_load, y_load, 0.70), (x_unlo, y_unlo, 0.35)):
        if len(x) < 3:
            continue
        i = max(0, min(len(x) - 2, int(frac * (len(x) - 1))))
        ax.annotate(
            "",
            xy=(x[i + 1], y[i + 1]),
            xytext=(x[i], y[i]),
            arrowprops=dict(arrowstyle="->", color=color, lw=1.2,
                            shrinkA=0, shrinkB=0),
        )


def plot_main(trials, session_dir):
    """F-d | |B|-d | |B|-F"""
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.4))
    tids = sorted(trials.keys())

    for i, t in enumerate(tids):
        color = TRIAL_COLORS[i % len(TRIAL_COLORS)]
        load = trials[t].get("loading")
        unlo = trials[t].get("unloading")
        if load is None or unlo is None:
            continue
        draw_connected_loop(
            axes[0], load, unlo, "d_actual", "F", color, f"trial {t}")
        draw_connected_loop(
            axes[1], load, unlo, "d_actual", "Bmag", color, f"trial {t}")
        draw_connected_loop(
            axes[2], load, unlo, "F", "Bmag", color, f"trial {t}")

    axes[0].axhline(0, color="black", alpha=0.3, lw=0.7)
    _setup(axes[0], title="F1: F vs d  (dotted connectors are visual guides)",
           xlabel="d_actual (mm)", ylabel="F (N)")
    axes[0].legend(loc="upper left", fontsize=8, ncol=2)

    _setup(axes[1], title="F2: |B| vs d  (dotted connectors are visual guides)",
           xlabel="d_actual (mm)", ylabel="|B| (µT)")
    axes[1].legend(loc="upper left", fontsize=8, ncol=2)

    _setup(axes[2], title="F3: |B| vs F  (dotted connectors are visual guides)",
           xlabel="F (N)", ylabel="|B| (µT)")
    axes[2].legend(loc="upper left", fontsize=8, ncol=2)

    fig.suptitle(f"Stage F — load/unload hysteresis  ({session_dir.name})",
                 fontsize=13, weight="bold", y=0.995)
    fig.tight_layout()
    out = FIGS_DIR / "F_main.png"
    fig.savefig(out, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out}")


def plot_3axis(trials, session_dir):
    """Bx | By | Bz vs d, loading vs unloading."""
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.4))
    tids = sorted(trials.keys())
    axis_keys = [("Bx", "Bx"), ("By", "By"), ("Bz", "Bz")]

    for ax_idx, (key, label) in enumerate(axis_keys):
        ax = axes[ax_idx]
        for i, t in enumerate(tids):
            color = TRIAL_COLORS[i % len(TRIAL_COLORS)]
            for phase, style in PHASE_STYLE.items():
                data = trials[t].get(phase)
                if data is None:
                    continue
                ax.plot(data["d_actual"], data[key],
                        marker=style["marker"], ls=style["ls"],
                        color=color, alpha=style["alpha"], markersize=4,
                        lw=1.2, label=f"trial {t} {style['label']}")
        ax.axhline(0, color="black", alpha=0.3, lw=0.7)
        _setup(ax, title=f"F4{'abc'[ax_idx]}: {label} vs d",
               xlabel="d_actual (mm)", ylabel=f"{label} (µT)")
        if ax_idx == 0:
            ax.legend(loc="best", fontsize=7, ncol=2)

    fig.suptitle(f"Stage F — 3-axis B  ({session_dir.name})",
                 fontsize=13, weight="bold", y=0.995)
    fig.tight_layout()
    out = FIGS_DIR / "F_3axis.png"
    fig.savefig(out, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out}")


def plot_loop_size(trials, session_dir):
    """ΔF(d) and Δ|B|(d) — hysteresis amplitude.

    Interpolate the unloading curve onto the loading d_actual grid, then
    compute Δ = loading - unloading at each loading d.
    """
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4))
    tids = sorted(trials.keys())

    for i, t in enumerate(tids):
        color = TRIAL_COLORS[i % len(TRIAL_COLORS)]
        load = trials[t].get("loading")
        unlo = trials[t].get("unloading")
        if load is None or unlo is None:
            continue
        if len(load["d_actual"]) == 0 or len(unlo["d_actual"]) == 0:
            continue

        # Interpolate unloading -> loading d grid.
        # Sort unloading by d_actual ascending so np.interp behaves.
        ord_u = np.argsort(unlo["d_actual"])
        d_u = unlo["d_actual"][ord_u]
        F_u = unlo["F"][ord_u]
        B_u = unlo["Bmag"][ord_u]

        d_load = load["d_actual"]
        F_load = load["F"]
        B_load = load["Bmag"]

        # only compare within the overlapping d range
        d_lo = max(d_load.min(), d_u.min())
        d_hi = min(d_load.max(), d_u.max())
        mask = (d_load >= d_lo) & (d_load <= d_hi)
        d_grid = d_load[mask]
        F_unl_interp = np.interp(d_grid, d_u, F_u)
        B_unl_interp = np.interp(d_grid, d_u, B_u)
        dF = F_load[mask] - F_unl_interp
        dB = B_load[mask] - B_unl_interp

        axes[0].plot(d_grid, dF * 1000, "o-", color=color,
                     markersize=5, lw=1.3, label=f"trial {t}")
        axes[1].plot(d_grid, dB, "o-", color=color,
                     markersize=5, lw=1.3, label=f"trial {t}")

    axes[0].axhline(0, color="black", alpha=0.3, lw=0.7)
    _setup(axes[0], title="F5: ΔF = F_load − F_unload  vs d",
           xlabel="d_actual (mm)", ylabel="ΔF (mN)")
    axes[0].legend(loc="best", fontsize=9)

    axes[1].axhline(0, color="black", alpha=0.3, lw=0.7)
    _setup(axes[1], title="F6: Δ|B| = |B|_load − |B|_unload  vs d",
           xlabel="d_actual (mm)", ylabel="Δ|B| (µT)")
    axes[1].legend(loc="best", fontsize=9)

    fig.suptitle(f"Stage F — hysteresis loop size  ({session_dir.name})",
                 fontsize=13, weight="bold", y=0.995)
    fig.tight_layout()
    out = FIGS_DIR / "F_loop_size.png"
    fig.savefig(out, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out}")


def main():
    FIGS_DIR.mkdir(parents=True, exist_ok=True)
    session = None
    if len(sys.argv) > 1:
        session = OUTPUT_ROOT / sys.argv[1]
    if session is None or not session.exists():
        session = _find_latest_stage_f(require_finite_b=True)

    if session is None:
        print("No Stage F session with finite B data found.")
        return

    print(f"\n=== Stage F ===\n  session: {session.name}")
    trials = load_stage_f(session)
    if not trials:
        print("  (no rep CSVs found)")
        return
    if not has_finite_b(trials):
        print("  ! selected session has no finite B values.")
        fallback = _find_latest_stage_f(require_finite_b=True)
        if fallback is not None and fallback != session:
            print(f"  latest usable Stage F session: {fallback.name}")
        return

    for t in sorted(trials.keys()):
        n_load = len(trials[t].get("loading", {}).get("F", []))
        n_unlo = len(trials[t].get("unloading", {}).get("F", []))
        print(f"  trial {t}: {n_load} loading + {n_unlo} unloading points")

    plot_main(trials, session)
    plot_3axis(trials, session)
    plot_loop_size(trials, session)
    print("\nDone.")


if __name__ == "__main__":
    main()
