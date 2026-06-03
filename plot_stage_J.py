"""Generate Stage J fixed-force hold plots.

Reads J_hold_force_<30/60/90>_rep*.csv from the latest Stage J session and
writes:

  reports/figs/J_main.png
      F(t), d(t), |B|(t), and |B|-d at fixed force.

  reports/figs/J_3axis.png
      ΔBx/ΔBy/ΔBz time traces for each fixed-force hold.

  reports/figs/J_jq.png
      First-pass dB/dd slopes at approximately fixed force.

Stage J is currently a signal-test stage. Because the pseudo-force controller
uses stepwise Mark-10 nudges, d may have only a few distinct levels; slopes
are diagnostics, not final calibrated Jacobian values.

The first second is skipped in the plotted/summary data. Stage J starts right
after serial buffers are reset, and previous runs showed a reproducible
sub-second MLX warmup/stale-buffer jump at the beginning of each hold.
"""

import csv
import re
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
ANALYSIS_SKIP_S = 1.0

HOLD_COLORS = {
    30: "#1f77b4",
    45: "#9467bd",
    60: "#d62728",
    75: "#ff7f0e",
    90: "#2ca02c",
}


def _safe_float(x, default=float("nan")):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _find_latest_stage_j():
    for s in sorted(OUTPUT_ROOT.glob("session_*"), reverse=True):
        if list(s.glob("J_hold_force_*.csv")):
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


def load_stage_j(session_dir):
    data = {}
    for path in sorted(session_dir.glob("J_hold_force_*.csv")):
        m = re.search(r"J_hold_force_(\d+)_rep(\d+)", path.stem)
        if not m:
            continue
        hold = int(m.group(1))
        rep = int(m.group(2))
        rows = []
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows.append(r)
        if not rows:
            continue
        cols = {
            "t": np.array([_safe_float(r["t_rel_s"]) for r in rows]),
            "F_target": np.array([_safe_float(r["F_target_N"]) for r in rows]),
            "F": np.array([_safe_float(r["F_N"]) for r in rows]),
            "F_err": np.array([_safe_float(r["F_error_N"]) for r in rows]),
            "d": np.array([_safe_float(r["d_actual_mm"]) for r in rows]),
            "Bx": np.array([_safe_float(r["mean_Bx_uT"]) for r in rows]),
            "By": np.array([_safe_float(r["mean_By_uT"]) for r in rows]),
            "Bz": np.array([_safe_float(r["mean_Bz_uT"]) for r in rows]),
            "Bmag": np.array([_safe_float(r["Bmag_uT"]) for r in rows]),
            "action": np.array([r["control_action"] for r in rows]),
        }
        if len(cols["t"]) > 3:
            t0 = np.nanmin(cols["t"])
            mask = cols["t"] >= t0 + ANALYSIS_SKIP_S
            if np.sum(mask) >= 3:
                for k, v in list(cols.items()):
                    cols[k] = v[mask]
        data[(hold, rep)] = cols
    return data


def linfit(x, y):
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if len(x) < 3 or np.nanstd(x) == 0:
        return float("nan"), float("nan"), float("nan")
    slope, intercept = np.polyfit(x, y, 1)
    y_hat = slope * x + intercept
    ss_res = np.sum((y - y_hat) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot else float("nan")
    return slope, intercept, r2


def plot_main(data, session_dir):
    fig, axes = plt.subplots(2, 2, figsize=(14, 9.5))
    axes = axes.ravel()

    for key in sorted(data):
        hold, rep = key
        dct = data[key]
        color = HOLD_COLORS.get(hold)
        t = dct["t"] - np.nanmin(dct["t"])
        label = (
            f"{hold}%  target={np.nanmedian(dct['F_target']):.2f} N"
        )

        axes[0].plot(t, dct["F"] * 1000, color=color, lw=1.3,
                     label=label)
        axes[0].axhline(np.nanmedian(dct["F_target"]) * 1000,
                        color=color, ls=":", lw=1.0, alpha=0.75)

        axes[1].plot(t, dct["d"], color=color, lw=1.3, label=label)
        axes[2].plot(t, dct["Bmag"], color=color, lw=1.3, label=label)

        axes[3].plot(dct["d"], dct["Bmag"], ".", color=color, ms=4,
                     alpha=0.8, label=label)
        slope, intercept, r2 = linfit(dct["d"], dct["Bmag"])
        if np.isfinite(slope):
            order = np.argsort(dct["d"])
            x = dct["d"][order]
            axes[3].plot(x, slope * x + intercept, color=color, lw=1.2)

    _setup(axes[0], "J1: force during fixed-force hold",
           "time (s)", "F (mN)")
    axes[0].legend(fontsize=8)

    _setup(axes[1], "J2: displacement creep / controller nudges",
           "time (s)", "d_actual (mm)")
    axes[1].legend(fontsize=8)

    _setup(axes[2], "J3: |B| during fixed-force hold",
           "time (s)", "|B| (µT)")
    axes[2].legend(fontsize=8)

    _setup(axes[3], "J4: |B| vs d at approximately fixed F",
           "d_actual (mm)", "|B| (µT)")
    axes[3].legend(fontsize=8)

    fig.suptitle(f"Stage J — fixed-force hold  ({session_dir.name})",
                 fontsize=13, weight="bold", y=0.995)
    fig.tight_layout()
    out = FIGS_DIR / "J_main.png"
    fig.savefig(out, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out}")


def plot_3axis(data, session_dir):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.4))
    for ax_i, axis_key in enumerate(("Bx", "By", "Bz")):
        ax = axes[ax_i]
        for key in sorted(data):
            hold, rep = key
            dct = data[key]
            color = HOLD_COLORS.get(hold)
            t = dct["t"] - np.nanmin(dct["t"])
            y = dct[axis_key] - dct[axis_key][0]
            label = f"{hold}%  target={np.nanmedian(dct['F_target']):.2f} N"
            ax.plot(t, y, color=color, lw=1.3, label=label)
        ax.axhline(0, color="black", alpha=0.3, lw=0.7)
        _setup(ax, f"J5{'abc'[ax_i]}: Δ{axis_key}(t)",
               "time (s)", f"Δ{axis_key} (µT)")
        if ax_i == 0:
            ax.legend(fontsize=8)

    fig.suptitle(f"Stage J — 3-axis magnetic response  ({session_dir.name})",
                 fontsize=13, weight="bold", y=0.995)
    fig.tight_layout()
    out = FIGS_DIR / "J_3axis.png"
    fig.savefig(out, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out}")


def plot_jq(data, session_dir):
    labels = []
    slopes = {k: [] for k in ("Bmag", "Bx", "By", "Bz")}
    r2s = []
    amplitudes = []
    force_stats = []

    for key in sorted(data):
        hold, rep = key
        dct = data[key]
        labels.append(f"{hold}%\n{np.nanmedian(dct['F_target']):.2f} N")
        for bkey in slopes:
            slope, intercept, r2 = linfit(dct["d"], dct[bkey])
            slopes[bkey].append(slope)
            if bkey == "Bmag":
                r2s.append(r2)
        amplitudes.append((
            dct["d"][-1] - dct["d"][0],
            dct["Bmag"][-1] - dct["Bmag"][0],
        ))
        force_stats.append(np.nanstd(dct["F"]) * 1000)

    x = np.arange(len(labels))
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.4))

    axes[0].bar(x, slopes["Bmag"], color=[
        HOLD_COLORS.get(k[0], "#777777") for k in sorted(data)
    ])
    axes[0].set_xticks(x, labels)
    _setup(axes[0], "J6: j_q estimate from |B|",
           "force hold", "d|B|/dd (µT/mm)")
    for xi, r2 in zip(x, r2s):
        if np.isfinite(r2):
            y = slopes["Bmag"][xi]
            va = "bottom" if y >= 0 else "top"
            axes[0].text(xi, y, f"R²={r2:.2f}",
                         ha="center", va=va, fontsize=8)

    width = 0.22
    for off, bkey, color in (
        (-width, "Bx", "#1f77b4"),
        (0.0, "By", "#d62728"),
        (width, "Bz", "#2ca02c"),
    ):
        axes[1].bar(x + off, slopes[bkey], width=width, label=bkey,
                    color=color)
    axes[1].set_xticks(x, labels)
    _setup(axes[1], "J7: 3-axis j_q components",
           "force hold", "dB_axis/dd (µT/mm)")
    axes[1].legend(fontsize=8)

    dd = [p[0] for p in amplitudes]
    dB = [p[1] for p in amplitudes]
    ax2 = axes[2]
    ax2.bar(x - 0.18, dd, width=0.36, color="#9467bd", label="Δd (mm)")
    ax2.set_ylabel("Δd (mm)", fontsize=10, color="#9467bd")
    ax2.tick_params(axis="y", labelcolor="#9467bd")
    ax2b = ax2.twinx()
    ax2b.bar(x + 0.18, dB, width=0.36, color="#8c564b", label="Δ|B| (µT)")
    ax2b.set_ylabel("Δ|B| (µT)", fontsize=10, color="#8c564b")
    ax2b.tick_params(axis="y", labelcolor="#8c564b")
    ax2.set_xticks(x, labels)
    _setup(ax2, "J8: creep and magnetic amplitude", "force hold", None)

    fig.suptitle(f"Stage J — first-pass j_q diagnostics  ({session_dir.name})",
                 fontsize=13, weight="bold", y=0.995)
    fig.tight_layout()
    out = FIGS_DIR / "J_jq.png"
    fig.savefig(out, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out}")


def print_summary(data):
    for key in sorted(data):
        hold, rep = key
        dct = data[key]
        duration = dct["t"][-1] - dct["t"][0]
        rate = len(dct["t"]) / duration if duration > 0 else float("nan")
        s_bmag, _, r2 = linfit(dct["d"], dct["Bmag"])
        actions = {
            a: int(np.sum(dct["action"] == a))
            for a in sorted(set(dct["action"]))
        }
        print(
            f"  {hold}% rep{rep}: n={len(dct['t'])}, "
            f"rate={rate:.1f} Hz, target={np.nanmedian(dct['F_target']):.3f} N, "
            f"Fmean={np.nanmean(dct['F']):.3f} N, "
            f"Fstd={np.nanstd(dct['F'])*1000:.1f} mN, "
            f"Δd={dct['d'][-1]-dct['d'][0]:+.4f} mm, "
            f"Δ|B|={dct['Bmag'][-1]-dct['Bmag'][0]:+.1f} µT, "
            f"d|B|/dd={s_bmag:.1f} µT/mm, R²={r2:.2f}, "
            f"actions={actions}"
        )


def main():
    FIGS_DIR.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) > 1:
        session = OUTPUT_ROOT / sys.argv[1]
    else:
        session = _find_latest_stage_j()

    if session is None or not session.exists():
        print("No Stage J session found.")
        return

    print(f"\n=== Stage J ===\n  session: {session.name}")
    data = load_stage_j(session)
    if not data:
        print("  (no J_hold_force_*.csv rows found)")
        return

    print_summary(data)
    plot_main(data, session)
    plot_3axis(data, session)
    plot_jq(data, session)
    print("\nDone.")


if __name__ == "__main__":
    main()
