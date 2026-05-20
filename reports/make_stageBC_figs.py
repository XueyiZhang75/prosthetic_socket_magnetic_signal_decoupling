"""Generate supplementary figures for the Stage B / Stage C reports.

Six figures, each with a single advisor-facing story:

    B1_noise_scaling.png   noise σ vs theoretical √(OSR·FILTER) averaging
                            count — proves chip-intrinsic noise
    B2_baseline_landscape.png  σ across all 4 baseline conditions
                                (B.0 / B.2 / B.3 / B.4) — SNR landscape
    B3_B0_decomposition.png    B.3 start-position field split into
                                fixture+Earth background vs magnet
    C1_dipole_fit.png      log-log |B_magnet| vs (q+q0) fit — checks
                            ~1/r^3 dipole law, extracts effective offset
    C2_sigma_vs_q.png      per-plateau σ vs q — quality assurance
    C3_vector_angle.png    B_magnet direction angle vs q — visualises
                            three-axis "fingerprint"

Run from project root:  python3 reports/make_stageBC_figs.py
"""

from pathlib import Path
import csv

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
FIGS = HERE / "figs"
FIGS.mkdir(exist_ok=True)
ROOT = HERE.parent
SESSION_B = ROOT / "decouple_data" / "session_20260518_173029"
SESSION_C = ROOT / "decouple_data" / "session_20260519_095753"

# --- approximate MLX90393 filter averaging counts (datasheet) ---
F_FACTOR = {0: 1.0, 1: 1.5, 2: 2.5, 3: 4.0, 4: 8.0, 5: 20.0, 6: 32.0, 7: 64.0}
PRESETS = {
    "fastest":   dict(osr=0, flt=0),
    "fast":      dict(osr=1, flt=1),
    "balanced":  dict(osr=2, flt=3),
    "low_noise": dict(osr=3, flt=5),
}


def load_b0():
    """{ preset: {'Bx':sigma, 'By':sigma, 'Bz':sigma, 'N':averaging_count} }"""
    rows = list(csv.DictReader(open(ROOT / "stage1_data" / "summary.csv")))
    latest = {}
    for r in rows:
        if r["timestamp"].startswith("20260518"):
            latest[(r["preset"], r["axis"])] = float(r["sigma_raw_uT"])
    out = {}
    for p, cfg in PRESETS.items():
        N = (2 ** cfg["osr"]) * F_FACTOR[cfg["flt"]]
        out[p] = dict(N=N,
                      Bx=latest[(p, "Bx")],
                      By=latest[(p, "By")],
                      Bz=latest[(p, "Bz")])
    return out


def load_baselines():
    """{ step: {'Bx':(mean,sigma), ...} } for B.2/B.3/B.4 (low_noise)."""
    rows = list(csv.DictReader(open(SESSION_B / "B_baseline_summary.csv")))
    by_step = {}
    for r in rows:
        s = r["step"]; a = r["axis"]
        by_step.setdefault(s, {})[a] = (float(r["mean_uT"]), float(r["sigma_uT"]))
    return by_step


def load_C():
    rows = list(csv.DictReader(open(SESSION_C / "C_summary.csv")))
    def col(name, d):
        return np.array([float(r[name]) for r in rows if r["direction"] == d])
    qd = col("q_mm", "down"); i = np.argsort(qd)
    out = dict(
        q=qd[i],
        Bx=col("mean_Bx_uT", "down")[i],
        By=col("mean_By_uT", "down")[i],
        Bz=col("mean_Bz_uT", "down")[i],
        sBx=col("sigma_Bx_uT", "down")[i],
        sBy=col("sigma_By_uT", "down")[i],
        sBz=col("sigma_Bz_uT", "down")[i],
    )
    return out


# ======================================================================
# Figure B1 — noise σ vs averaging count (√N law)
# ======================================================================
def fig_noise_scaling(b0):
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    Ns = np.array([b0[p]["N"] for p in PRESETS])
    for axis, color in zip(["Bx", "By", "Bz"], ["tab:red", "tab:green", "tab:blue"]):
        sigs = np.array([b0[p][axis] for p in PRESETS])
        ax.loglog(Ns, sigs, "o", color=color, ms=8, label=axis)
    # theory line: σ ∝ 1/√N, anchored on Bz @ low_noise
    sigma_ref = b0["low_noise"]["Bz"]; N_ref = b0["low_noise"]["N"]
    N_line = np.logspace(np.log10(min(Ns) * 0.5), np.log10(max(Ns) * 2), 50)
    ax.loglog(N_line, sigma_ref * np.sqrt(N_ref / N_line),
              "k--", alpha=0.7, label=r"theory: $\sigma \propto 1/\sqrt{N}$")
    for p in PRESETS:
        ax.annotate(p, (b0[p]["N"], b0[p]["Bz"]),
                    xytext=(8, -4), textcoords="offset points", fontsize=9)
    ax.set_xlabel(r"averaging count $N = 2^{\rm OSR} \times F_{\rm filter}$")
    ax.set_ylabel(r"$\sigma_{\rm raw}$ (µT)")
    ax.set_title("Stage B.0: noise σ follows √N averaging law\n"
                 "→ noise is chip-intrinsic; environment contributes nothing")
    ax.grid(True, which="both", alpha=0.3); ax.legend()
    fig.tight_layout(); fig.savefig(FIGS / "B1_noise_scaling.png", dpi=130)
    print("  saved", FIGS / "B1_noise_scaling.png")


# ======================================================================
# Figure B2 — σ across 4 baseline conditions
# ======================================================================
def fig_baseline_landscape(b0, base):
    conds = ["B.0 static\n(low_noise, no magnet far)",
             "B.2 static\n(no magnet, fixture)",
             "B.3 static\n(magnet at start)",
             "B.4 dynamic\n(Mark-10 moving)"]
    sigs = {
        "Bx": [b0["low_noise"]["Bx"], base["b2"]["Bx"][1], base["b3"]["Bx"][1], base["b4"]["Bx"][1]],
        "By": [b0["low_noise"]["By"], base["b2"]["By"][1], base["b3"]["By"][1], base["b4"]["By"][1]],
        "Bz": [b0["low_noise"]["Bz"], base["b2"]["Bz"][1], base["b3"]["Bz"][1], base["b4"]["Bz"][1]],
    }
    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = np.arange(len(conds)); w = 0.25
    colors = {"Bx": "tab:red", "By": "tab:green", "Bz": "tab:blue"}
    for i, (k, vals) in enumerate(sigs.items()):
        bars = ax.bar(x + (i - 1) * w, vals, w, label=k, color=colors[k])
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.2f}",
                    ha="center", va="bottom", fontsize=8)
    ax.axhline(b0["low_noise"]["Bz"], color="gray", ls=":",
               label=f"chip noise floor σ_Bz = {b0['low_noise']['Bz']:.2f} µT")
    ax.set_xticks(x); ax.set_xticklabels(conds, fontsize=9)
    ax.set_ylabel(r"$\sigma$ (µT)")
    ax.set_title("Stage B: noise σ landscape across 4 baseline conditions\n"
                 "→ chip floor stays clean; only Mark-10 motion inflates σ")
    ax.grid(True, axis="y", alpha=0.3); ax.legend(fontsize=9)
    fig.tight_layout(); fig.savefig(FIGS / "B2_baseline_landscape.png", dpi=130)
    print("  saved", FIGS / "B2_baseline_landscape.png")


# ======================================================================
# Figure B3 — B0 decomposition: background vs magnet contribution
# ======================================================================
def fig_b0_decomposition(base):
    bg = np.array([base["b2"]["Bx"][0], base["b2"]["By"][0], base["b2"]["Bz"][0]])
    b3 = np.array([base["b3"]["Bx"][0], base["b3"]["By"][0], base["b3"]["Bz"][0]])
    mag = b3 - bg

    axes_lbl = ["Bx", "By", "Bz"]
    fig, axs = plt.subplots(1, 2, figsize=(13, 5.2),
                            gridspec_kw=dict(width_ratios=[2, 1]))
    # left: per-axis grouped bar
    x = np.arange(3); w = 0.35
    axs[0].bar(x - w/2, bg, w, color="lightgray", edgecolor="k",
               label=f"fixture + Earth background  (|B|={np.linalg.norm(bg):.0f} µT)")
    axs[0].bar(x + w/2, mag, w, color="tab:orange", edgecolor="k",
               label=f"magnet at start position    (|B|={np.linalg.norm(mag):.0f} µT)")
    for i, (b, m) in enumerate(zip(bg, mag)):
        axs[0].text(i - w/2, b + (50 if b > 0 else -50) * np.sign(b or 1),
                    f"{b:+.0f}", ha="center", fontsize=9)
        axs[0].text(i + w/2, m + (50 if m > 0 else -50) * np.sign(m or 1),
                    f"{m:+.0f}", ha="center", fontsize=9)
    axs[0].axhline(0, color="k", lw=0.5)
    axs[0].set_xticks(x); axs[0].set_xticklabels(axes_lbl)
    axs[0].set_ylabel("field component (µT)")
    axs[0].set_title("Per-axis decomposition of the B.3 start-position field")
    axs[0].grid(True, axis="y", alpha=0.3); axs[0].legend(fontsize=9)

    # right: |B| magnitude pie/bar
    mags = [np.linalg.norm(bg), np.linalg.norm(mag)]
    labels = [f"background\n{mags[0]:.0f} µT", f"magnet\n{mags[1]:.0f} µT"]
    axs[1].bar([0, 1], mags, color=["lightgray", "tab:orange"], edgecolor="k")
    for i, m in enumerate(mags):
        axs[1].text(i, m, f"{m:.0f} µT", ha="center", va="bottom")
    axs[1].set_xticks([0, 1]); axs[1].set_xticklabels(["background", "magnet"])
    axs[1].set_ylabel("|B| (µT)")
    axs[1].set_yscale("log")
    ratio = mags[1] / mags[0]
    axs[1].set_title(f"Magnitude: magnet is {ratio:.0f}× background\n"
                     "→ working-position magnet field dominates")
    axs[1].grid(True, axis="y", alpha=0.3)
    fig.tight_layout(); fig.savefig(FIGS / "B3_B0_decomposition.png", dpi=130)
    print("  saved", FIGS / "B3_B0_decomposition.png")


# ======================================================================
# Figure C1 — log-log |B_magnet(q)| dipole fit
# ======================================================================
def fig_dipole_fit(C, base):
    """Fit |B_magnet| ≈ A / (q + q0)^n with q0, n, A by grid search on q0."""
    bg = np.array([base["b2"]["Bx"][0], base["b2"]["By"][0], base["b2"]["Bz"][0]])
    Bvec = np.column_stack([C["Bx"], C["By"], C["Bz"]]) - bg
    Bmag = np.linalg.norm(Bvec, axis=1)
    q = C["q"]

    best = (np.inf, None, None, None)
    for q0 in np.linspace(-30, 80, 221):
        x = np.log(q + q0)
        y = np.log(Bmag)
        if not np.isfinite(x).all():
            continue
        # linear fit y = log A - n x
        slope, intercept = np.polyfit(x, y, 1)
        resid = y - (slope * x + intercept)
        rss = float(np.sum(resid ** 2))
        if rss < best[0]:
            best = (rss, q0, -slope, np.exp(intercept))
    _, q0, n_fit, A_fit = best

    fig, axs = plt.subplots(1, 2, figsize=(13, 5.2))
    # left: log-log
    xfit = np.linspace(min(q + q0) * 0.95, max(q + q0) * 1.05, 100)
    yfit = A_fit / xfit ** n_fit
    axs[0].loglog(q + q0, Bmag, "o", color="tab:purple", ms=5, label="data")
    axs[0].loglog(xfit, yfit, "k--", alpha=0.7,
                  label=fr"$|B_{{\rm mag}}| = {A_fit:.2g}\,(q+q_0)^{{-{n_fit:.2f}}}$"
                        f"\n$q_0={q0:.1f}$ mm")
    axs[0].set_xlabel(r"$q + q_0$ (mm)"); axs[0].set_ylabel(r"$|B_{\rm magnet}|$ (µT)")
    axs[0].set_title("Stage C: log-log dipole fit on magnet-only field\n"
                     f"→ exponent n = {n_fit:.2f} (ideal dipole = 3)")
    axs[0].grid(True, which="both", alpha=0.3); axs[0].legend(fontsize=9)
    # right: linear scale with fit overlay
    qfit = np.linspace(q.min(), q.max(), 200)
    axs[1].plot(q, Bmag, "o", color="tab:purple", ms=5, label="data")
    axs[1].plot(qfit, A_fit / (qfit + q0) ** n_fit, "k--", alpha=0.7, label="fit")
    axs[1].set_xlabel("gap q (mm)"); axs[1].set_ylabel(r"$|B_{\rm magnet}|$ (µT)")
    axs[1].set_title("Same fit, linear scale")
    axs[1].grid(True, alpha=0.3); axs[1].legend(fontsize=9)
    fig.tight_layout(); fig.savefig(FIGS / "C1_dipole_fit.png", dpi=130)
    print(f"  saved {FIGS / 'C1_dipole_fit.png'}  "
          f"(q0={q0:.2f} mm, n={n_fit:.3f}, A={A_fit:.3g})")
    return q0, n_fit, A_fit


# ======================================================================
# Figure C2 — σ per plateau vs q (QA)
# ======================================================================
def fig_sigma_vs_q(C, b0):
    fig, ax = plt.subplots(figsize=(10, 5))
    for name, vals, color in [("σ_Bx", C["sBx"], "tab:red"),
                              ("σ_By", C["sBy"], "tab:green"),
                              ("σ_Bz", C["sBz"], "tab:blue")]:
        ax.plot(C["q"], vals, "o-", color=color, ms=4, label=name)
    for ax_name, color in zip(["Bx", "By", "Bz"], ["tab:red", "tab:green", "tab:blue"]):
        ax.axhline(b0["low_noise"][ax_name], ls=":", color=color, alpha=0.7,
                   label=f"B.0 floor {ax_name} ({b0['low_noise'][ax_name]:.2f})")
    ax.set_xlabel("gap q (mm)"); ax.set_ylabel("σ per plateau (µT)")
    ax.set_title("Stage C QA: per-plateau noise σ stays at the chip floor\n"
                 "across all 41 q points → uniform data quality")
    ax.grid(True, alpha=0.3); ax.legend(fontsize=8, ncol=2)
    fig.tight_layout(); fig.savefig(FIGS / "C2_sigma_vs_q.png", dpi=130)
    print("  saved", FIGS / "C2_sigma_vs_q.png")


# ======================================================================
# Figure C3 — B_magnet direction angle vs q
# ======================================================================
def fig_vector_angle(C, base):
    bg = np.array([base["b2"]["Bx"][0], base["b2"]["By"][0], base["b2"]["Bz"][0]])
    Bvec = np.column_stack([C["Bx"], C["By"], C["Bz"]]) - bg
    bx, by, bz = Bvec.T
    theta_xy = np.degrees(np.arctan2(by, bx))
    theta_polar = np.degrees(np.arctan2(np.sqrt(bx**2 + by**2), bz))  # from +z

    fig, axs = plt.subplots(1, 2, figsize=(13, 5))
    axs[0].plot(C["q"], theta_xy, "o-", color="tab:purple", ms=4)
    axs[0].set_xlabel("gap q (mm)")
    axs[0].set_ylabel(r"$\theta_{xy}$ = atan2($B_y$, $B_x$) (deg)")
    axs[0].set_title("Azimuthal angle in the xy-plane")
    axs[0].grid(True, alpha=0.3)

    axs[1].plot(C["q"], theta_polar, "o-", color="tab:olive", ms=4)
    axs[1].set_xlabel("gap q (mm)")
    axs[1].set_ylabel(r"$\theta_{\rm polar}$ from +$z$-axis (deg)")
    axs[1].set_title("Polar angle from +z")
    axs[1].grid(True, alpha=0.3)

    fig.suptitle("Stage C: B_magnet vector direction rotates with q\n"
                 "→ three-axis 'fingerprint' that scalar |B| alone hides")
    fig.tight_layout(); fig.savefig(FIGS / "C3_vector_angle.png", dpi=130)
    print("  saved", FIGS / "C3_vector_angle.png")


def main():
    print("loading data ...")
    b0 = load_b0()
    base = load_baselines()
    C = load_C()

    print("generating figures ...")
    fig_noise_scaling(b0)
    fig_baseline_landscape(b0, base)
    fig_b0_decomposition(base)
    fig_dipole_fit(C, base)
    fig_sigma_vs_q(C, b0)
    fig_vector_angle(C, base)
    print("done.")


if __name__ == "__main__":
    main()
