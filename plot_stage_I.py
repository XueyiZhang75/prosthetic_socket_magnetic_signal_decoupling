"""Generate Stage I fixed-displacement hold plots.

Reads I_hold_disp_<30/60/90>_rep*.csv from the latest Stage I session and
writes:

  reports/figs/I_main.png
      F(t), |B|(t), and |B|-F at fixed d.

  reports/figs/I_3axis.png
      Bx/By/Bz time traces for each fixed d hold.

  reports/figs/I_jF.png
      Linear-slope estimates dB/dF at fixed d for |B| and three axes.

The script is intentionally descriptive rather than model-heavy. Stage I is
currently a signal-test stage, so the slopes are first-pass diagnostics, not
final calibrated Jacobian values.
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

HOLD_COLORS = {
    30: "#1f77b4",
    60: "#d62728",
    90: "#2ca02c",
}

REP_COLORS = {
    1: "#000000",
    2: "#d62728",
    3: "#1f77b4",
}


def series_color(hold, rep):
    return REP_COLORS.get(rep, HOLD_COLORS.get(hold, None))


def _safe_float(x, default=float("nan")):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _find_latest_stage_i():
    for s in sorted(OUTPUT_ROOT.glob("session_*"), reverse=True):
        if list(s.glob("I_hold_disp_*.csv")):
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


def load_stage_i(session_dir):
    """Return {(hold_label, rep): dict of arrays}."""
    data = {}
    for path in sorted(session_dir.glob("I_hold_disp_*.csv")):
        m = re.search(r"I_hold_disp_(\d+)_rep(\d+)", path.stem)
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
            "F": np.array([_safe_float(r["F_N"]) for r in rows]),
            "d": np.array([_safe_float(r["d_actual_mm"]) for r in rows]),
            "Bx": np.array([_safe_float(r["mean_Bx_uT"]) for r in rows]),
            "By": np.array([_safe_float(r["mean_By_uT"]) for r in rows]),
            "Bz": np.array([_safe_float(r["mean_Bz_uT"]) for r in rows]),
            "Bmag": np.array([_safe_float(r["Bmag_uT"]) for r in rows]),
        }
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


def hold_label(data):
    hold, rep = data
    return f"{hold}% dmax rep{rep}"


def plot_main(data, session_dir):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.4))

    for key in sorted(data):
        hold, rep = key
        d = data[key]
        color = series_color(hold, rep)
        label = f"{hold}%  d={np.nanmedian(d['d']):.2f} mm"
        t = d["t"]
        t = t - np.nanmin(t)
        axes[0].plot(t, d["F"] * 1000, color=color, lw=1.3, label=label)
        axes[1].plot(t, d["Bmag"], color=color, lw=1.3, label=label)
        axes[2].plot(d["F"], d["Bmag"], ".", color=color, ms=3.5,
                     alpha=0.75, label=label)

        slope, intercept, r2 = linfit(d["F"], d["Bmag"])
        if np.isfinite(slope):
            order = np.argsort(d["F"])
            x = d["F"][order]
            axes[2].plot(x, slope * x + intercept, color=color, lw=1.2,
                         alpha=0.9)

    _setup(axes[0], "I1: force relaxation at fixed d",
           "time (s)", "F (mN)")
    axes[0].legend(fontsize=8)

    _setup(axes[1], "I2: |B| drift at fixed d",
           "time (s)", "|B| (µT)")
    axes[1].legend(fontsize=8)

    _setup(axes[2], "I3: |B| vs F at fixed d",
           "F (N)", "|B| (µT)")
    axes[2].legend(fontsize=8)

    fig.suptitle(f"Stage I — fixed-displacement hold  ({session_dir.name})",
                 fontsize=13, weight="bold", y=0.995)
    fig.tight_layout()
    out = FIGS_DIR / "I_main.png"
    fig.savefig(out, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out}")


def plot_3axis(data, session_dir):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.4))
    for ax_i, axis_key in enumerate(("Bx", "By", "Bz")):
        ax = axes[ax_i]
        for key in sorted(data):
            hold, rep = key
            d = data[key]
            color = series_color(hold, rep)
            t = d["t"] - np.nanmin(d["t"])
            y = d[axis_key] - d[axis_key][0]
            label = f"{hold}%  d={np.nanmedian(d['d']):.2f} mm"
            ax.plot(t, y, color=color, lw=1.3, label=label)
        ax.axhline(0, color="black", alpha=0.3, lw=0.7)
        _setup(ax, f"I4{'abc'[ax_i]}: Δ{axis_key}(t)",
               "time (s)", f"Δ{axis_key} (µT)")
        if ax_i == 0:
            ax.legend(fontsize=8)

    fig.suptitle(f"Stage I — 3-axis magnetic relaxation  ({session_dir.name})",
                 fontsize=13, weight="bold", y=0.995)
    fig.tight_layout()
    out = FIGS_DIR / "I_3axis.png"
    fig.savefig(out, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out}")


def plot_jf(data, session_dir):
    holds = []
    slopes = {k: [] for k in ("Bmag", "Bx", "By", "Bz")}
    r2s = []
    deltas = []

    for key in sorted(data):
        hold, rep = key
        d = data[key]
        holds.append(f"{hold}%\n{np.nanmedian(d['d']):.2f} mm")
        for bkey in slopes:
            slope, intercept, r2 = linfit(d["F"], d[bkey])
            slopes[bkey].append(slope)
            if bkey == "Bmag":
                r2s.append(r2)
        deltas.append((
            (d["F"][-1] - d["F"][0]) * 1000,
            d["Bmag"][-1] - d["Bmag"][0],
        ))

    x = np.arange(len(holds))
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.4))

    axes[0].bar(x, slopes["Bmag"], color=[
        series_color(k[0], k[1]) for k in sorted(data)
    ])
    axes[0].set_xticks(x, holds)
    _setup(axes[0], "I5: j_F estimate from |B|",
           "hold depth", "d|B|/dF (µT/N)")
    for xi, r2 in zip(x, r2s):
        axes[0].text(xi, slopes["Bmag"][xi], f"R²={r2:.2f}",
                     ha="center", va="bottom", fontsize=8)

    width = 0.22
    for off, bkey, color in (
        (-width, "Bx", "#1f77b4"),
        (0.0, "By", "#d62728"),
        (width, "Bz", "#2ca02c"),
    ):
        axes[1].bar(x + off, slopes[bkey], width=width, label=bkey,
                    color=color)
    axes[1].set_xticks(x, holds)
    _setup(axes[1], "I6: 3-axis j_F components",
           "hold depth", "dB_axis/dF (µT/N)")
    axes[1].legend(fontsize=8)

    dF = [p[0] for p in deltas]
    dB = [p[1] for p in deltas]
    ax2 = axes[2]
    ax2.bar(x - 0.18, dF, width=0.36, color="#9467bd", label="ΔF (mN)")
    ax2.set_ylabel("ΔF (mN)", fontsize=10, color="#9467bd")
    ax2.tick_params(axis="y", labelcolor="#9467bd")
    ax2b = ax2.twinx()
    ax2b.bar(x + 0.18, dB, width=0.36, color="#8c564b", label="Δ|B| (µT)")
    ax2b.set_ylabel("Δ|B| (µT)", fontsize=10, color="#8c564b")
    ax2b.tick_params(axis="y", labelcolor="#8c564b")
    ax2.set_xticks(x, holds)
    _setup(ax2, "I7: relaxation amplitude", "hold depth", None)
    ax2.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)

    fig.suptitle(f"Stage I — first-pass j_F diagnostics  ({session_dir.name})",
                 fontsize=13, weight="bold", y=0.995)
    fig.tight_layout()
    out = FIGS_DIR / "I_jF.png"
    fig.savefig(out, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out}")


def print_summary(data):
    for key in sorted(data):
        hold, rep = key
        d = data[key]
        duration = d["t"][-1] - d["t"][0]
        rate = len(d["t"]) / duration if duration > 0 else float("nan")
        s_bmag, _, r2 = linfit(d["F"], d["Bmag"])
        print(
            f"  {hold}% rep{rep}: n={len(d['t'])}, "
            f"rate={rate:.1f} Hz, d={np.nanmedian(d['d']):.3f} mm, "
            f"ΔF={(d['F'][-1]-d['F'][0])*1000:+.1f} mN, "
            f"Δ|B|={d['Bmag'][-1]-d['Bmag'][0]:+.1f} µT, "
            f"d|B|/dF={s_bmag:.1f} µT/N, R²={r2:.2f}"
        )


def main():
    FIGS_DIR.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) > 1:
        session = OUTPUT_ROOT / sys.argv[1]
    else:
        session = _find_latest_stage_i()

    if session is None or not session.exists():
        print("No Stage I session found.")
        return

    print(f"\n=== Stage I ===\n  session: {session.name}")
    data = load_stage_i(session)
    if not data:
        print("  (no I_hold_disp_*.csv rows found)")
        return

    print_summary(data)
    plot_main(data, session)
    plot_3axis(data, session)
    plot_jf(data, session)
    print("\nDone.")


if __name__ == "__main__":
    main()
