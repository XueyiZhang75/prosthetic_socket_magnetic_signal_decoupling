"""Create Nature-style paper figures for the latest session of each stage.

The script reads the latest available session for each completed data stage
(B, C, D, E, F, H, I, J) and writes publication-oriented figures to
reports/nature_figures. SVG is the primary output; PDF, PNG, and TIFF previews
are written alongside it.

Figure contract:
Core conclusion: the final stage sessions form a traceable APMD evidence chain,
from baseline stability through displacement, force, hysteresis, and hold-based
Jacobian diagnostics.
Archetype: quantitative grid.
Backend: Python / matplotlib only.
Target output: editable Nature-style SVG plus PDF/PNG/TIFF exports.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).parent
DATA_ROOT = ROOT / "decouple_data"
OUT_DIR = ROOT / "reports" / "nature_figures"

EXPORT_FORMATS = ("svg", "pdf", "png", "tiff")
PNG_DPI = 300
TIFF_DPI = 600

PALETTE = {
    "blue": "#0F4D92",
    "blue_mid": "#3775BA",
    "teal": "#42949E",
    "violet": "#9A4D8E",
    "red": "#B64342",
    "red_soft": "#E9A6A1",
    "green": "#2E9E44",
    "gold": "#D9A441",
    "gray_light": "#CFCECE",
    "gray": "#767676",
    "gray_dark": "#4D4D4D",
    "black": "#272727",
}

AXIS_COLORS = {
    "Bx": PALETTE["red"],
    "By": PALETTE["green"],
    "Bz": PALETTE["blue"],
    "Bmag": PALETTE["black"],
}

SERIES_COLORS = [
    PALETTE["blue"],
    PALETTE["red"],
    PALETTE["green"],
    PALETTE["teal"],
    PALETTE["violet"],
    PALETTE["gold"],
]


def apply_style() -> None:
    """Apply compact journal-style defaults with editable SVG text."""
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "DejaVu Sans", "Liberation Sans"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 7,
            "axes.titlesize": 7,
            "axes.labelsize": 7,
            "xtick.labelsize": 6,
            "ytick.labelsize": 6,
            "legend.fontsize": 6,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
            "lines.linewidth": 1.25,
            "lines.markersize": 3.8,
            "xtick.major.width": 0.7,
            "ytick.major.width": 0.7,
            "xtick.major.size": 2.6,
            "ytick.major.size": 2.6,
        }
    )


def safe_float(value, default=np.nan) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def latest_session_with(pattern: str) -> Path | None:
    sessions = sorted(DATA_ROOT.glob("session_*"), reverse=True)
    for session in sessions:
        if list(session.glob(pattern)):
            return session
    return None


def array_from(rows: list[dict[str, str]], key: str) -> np.ndarray:
    return np.array([safe_float(r.get(key)) for r in rows], dtype=float)


def finite_mask(*arrays: np.ndarray) -> np.ndarray:
    mask = np.ones(len(arrays[0]), dtype=bool)
    for arr in arrays:
        mask &= np.isfinite(arr)
    return mask


def linfit(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    mask = finite_mask(x, y)
    x = x[mask]
    y = y[mask]
    if len(x) < 3 or np.nanstd(x) <= 1e-12:
        return np.nan, np.nan, np.nan
    slope, intercept = np.polyfit(x, y, 1)
    y_hat = slope * x + intercept
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return slope, intercept, r2


def gradient_unique(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mask = finite_mask(x, y)
    x = x[mask]
    y = y[mask]
    if len(x) < 2:
        return np.array([]), np.array([])
    order = np.argsort(x)
    x = x[order]
    y = y[order]
    uniq_x, inv = np.unique(x, return_inverse=True)
    if len(uniq_x) < 2:
        return np.array([]), np.array([])
    y_mean = np.array([np.mean(y[inv == i]) for i in range(len(uniq_x))])
    return uniq_x, np.gradient(y_mean, uniq_x)


def setup_axis(ax, xlabel: str | None = None, ylabel: str | None = None) -> None:
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.grid(False)
    ax.tick_params(direction="out")


def add_panel(ax, label: str, title: str | None = None) -> None:
    ax.text(
        -0.12,
        1.05,
        label,
        transform=ax.transAxes,
        fontsize=9,
        fontweight="bold",
        va="bottom",
        ha="left",
    )
    if title:
        ax.set_title(title, loc="left", pad=3)


def add_stage_header(fig, text: str) -> None:
    fig.text(
        0.01,
        0.995,
        text,
        va="top",
        ha="left",
        fontsize=7,
        color=PALETTE["gray_dark"],
    )


def export_figure(fig, basename: str) -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = OUT_DIR / basename
    fig.tight_layout(rect=(0, 0, 1, 0.965), pad=0.6)
    saved: list[Path] = []
    for fmt in EXPORT_FORMATS:
        path = base.with_suffix(f".{fmt}")
        kwargs = {"bbox_inches": "tight"}
        if fmt == "png":
            kwargs["dpi"] = PNG_DPI
        elif fmt == "tiff":
            kwargs["dpi"] = TIFF_DPI
            kwargs["pil_kwargs"] = {"compression": "tiff_lzw"}
        fig.savefig(path, **kwargs)
        saved.append(path)
    plt.close(fig)
    return saved


def set_compact_legend(ax, **kwargs) -> None:
    ax.legend(handlelength=1.4, borderaxespad=0.2, labelspacing=0.25, **kwargs)


def load_stage_b(session: Path) -> dict[str, dict[str, dict[str, float]]]:
    rows = read_csv(session / "B_baseline_summary.csv")
    out: dict[str, dict[str, dict[str, float]]] = {}
    for r in rows:
        step = r.get("step", "")
        axis = r.get("axis", "")
        out.setdefault(step, {})[axis] = {
            "mean": safe_float(r.get("mean_uT")),
            "sigma": safe_float(r.get("sigma_uT")),
            "sigma_detrend": safe_float(r.get("sigma_detrend_uT")),
            "drift": safe_float(r.get("drift_uT_per_s")),
            "p2p": safe_float(r.get("p2p_uT")),
        }
    return out


def plot_stage_b(session: Path) -> list[Path]:
    data = load_stage_b(session)
    step_labels = {
        "b1": "health",
        "b2": "no magnet",
        "b3": "magnet",
        "b4": "stage motion",
    }
    steps = [s for s in ("b1", "b2", "b3", "b4") if s in data]
    axes_names = ["Bx", "By", "Bz"]

    fig, axs = plt.subplots(2, 2, figsize=(7.2, 5.3))
    ax = axs[0, 0]
    x = np.arange(len(steps))
    width = 0.23
    for i, axis in enumerate(axes_names):
        y = [data[s].get(axis, {}).get("sigma", np.nan) for s in steps]
        ax.bar(
            x + (i - 1) * width,
            y,
            width=width,
            color=AXIS_COLORS[axis],
            alpha=0.88,
            label=axis,
            edgecolor="white",
            linewidth=0.3,
        )
    ax.set_xticks(x, [step_labels.get(s, s) for s in steps], rotation=20, ha="right")
    setup_axis(ax, None, "noise sigma (uT)")
    add_panel(ax, "a", "Noise landscape across baseline states")
    set_compact_legend(ax, ncol=3, loc="upper left")

    ax = axs[0, 1]
    b2 = np.array([data.get("b2", {}).get(a, {}).get("mean", np.nan) for a in axes_names])
    b3 = np.array([data.get("b3", {}).get(a, {}).get("mean", np.nan) for a in axes_names])
    magnet = b3 - b2
    x2 = np.arange(len(axes_names))
    ax.bar(x2 - 0.18, b2, width=0.36, color=PALETTE["gray_light"], label="fixture + Earth")
    ax.bar(x2 + 0.18, magnet, width=0.36, color=PALETTE["gold"], label="magnet contribution")
    ax.axhline(0, color=PALETTE["black"], lw=0.6, alpha=0.45)
    ax.set_xticks(x2, axes_names)
    setup_axis(ax, None, "field component (uT)")
    add_panel(ax, "b", "Start-position field decomposition")
    set_compact_legend(ax, loc="best")

    ax = axs[1, 0]
    for axis in axes_names:
        y = [data[s].get(axis, {}).get("p2p", np.nan) for s in steps]
        ax.plot(x, y, "o-", color=AXIS_COLORS[axis], label=axis)
    ax.set_xticks(x, [step_labels.get(s, s) for s in steps], rotation=20, ha="right")
    setup_axis(ax, None, "peak-to-peak span (uT)")
    add_panel(ax, "c", "Transient span remains bounded")
    set_compact_legend(ax, ncol=3, loc="upper left")

    ax = axs[1, 1]
    for axis in axes_names:
        y = [data[s].get(axis, {}).get("drift", np.nan) for s in steps]
        ax.plot(x, y, "o-", color=AXIS_COLORS[axis], label=axis)
    ax.axhline(0, color=PALETTE["black"], lw=0.6, alpha=0.45)
    ax.set_xticks(x, [step_labels.get(s, s) for s in steps], rotation=20, ha="right")
    setup_axis(ax, None, "linear drift (uT s$^{-1}$)")
    add_panel(ax, "d", "Drift check for baseline subtraction")
    set_compact_legend(ax, ncol=3, loc="upper left")

    add_stage_header(fig, f"Stage B final session: {session.name}")
    return export_figure(fig, "stage_B_baseline")


def load_stage_c(session: Path) -> list[dict[str, str]]:
    return read_csv(session / "C_summary.csv")


def plot_stage_c(session: Path) -> list[Path]:
    rows = load_stage_c(session)
    directions = [d for d in ("down", "up") if any(r.get("direction") == d for r in rows)]
    fig, axs = plt.subplots(2, 2, figsize=(7.2, 5.4))

    ax = axs[0, 0]
    for i, direction in enumerate(directions):
        sub = [r for r in rows if r.get("direction") == direction]
        q = array_from(sub, "q_mm")
        bmag = array_from(sub, "Bmag_uT")
        order = np.argsort(q)
        label = direction if len(q) >= 5 else f"{direction} (n={len(q)})"
        linestyle = "-" if len(q) >= 5 else "none"
        ax.plot(
            q[order],
            bmag[order],
            marker="o",
            linestyle=linestyle,
            color=SERIES_COLORS[i],
            label=label,
        )
    setup_axis(ax, "gap q (mm)", "|B| (uT)")
    add_panel(ax, "a", "Pure-displacement response")
    set_compact_legend(ax, loc="best")

    ax = axs[0, 1]
    down = [r for r in rows if r.get("direction") == (directions[0] if directions else "down")]
    q = array_from(down, "q_mm")
    order = np.argsort(q)
    for axis, key in (("Bx", "mean_Bx_uT"), ("By", "mean_By_uT"), ("Bz", "mean_Bz_uT")):
        y = array_from(down, key)
        ax.plot(q[order], y[order], "o-", color=AXIS_COLORS[axis], label=axis)
    ax.axhline(0, color=PALETTE["black"], lw=0.6, alpha=0.45)
    setup_axis(ax, "gap q (mm)", "B component (uT)")
    add_panel(ax, "b", "Three-axis geometric fingerprint")
    set_compact_legend(ax, ncol=3, loc="best")

    ax = axs[1, 0]
    if {"down", "up"}.issubset(set(directions)):
        q_match_key = "q_target_mm" if "q_target_mm" in rows[0] else "q_mm"
        down_by_q = {safe_float(r.get(q_match_key)): r for r in rows if r.get("direction") == "down"}
        up_by_q = {safe_float(r.get(q_match_key)): r for r in rows if r.get("direction") == "up"}
        q_common = np.array(sorted(set(down_by_q).intersection(up_by_q)))
    else:
        q_common = np.array([])
    if len(q_common) >= 5:
        for axis, key in (("Bx", "mean_Bx_uT"), ("By", "mean_By_uT"), ("Bz", "mean_Bz_uT")):
            resid = np.array(
                [
                    safe_float(down_by_q[qv].get(key)) - safe_float(up_by_q[qv].get(key))
                    for qv in q_common
                ]
            )
            ax.plot(q_common, resid, "o-", color=AXIS_COLORS[axis], label=axis)
        ax.axhline(0, color=PALETTE["black"], lw=0.6, alpha=0.45)
        setup_axis(ax, "gap q (mm)", "down - up (uT)")
        add_panel(ax, "c", "Direction hysteresis residual")
    else:
        for axis, key in (("Bx", "sigma_Bx_uT"), ("By", "sigma_By_uT"), ("Bz", "sigma_Bz_uT")):
            sigma = array_from(down, key)
            ax.plot(q[order], sigma[order], "o-", color=AXIS_COLORS[axis], label=axis)
        setup_axis(ax, "gap q (mm)", "plateau sigma (uT)")
        add_panel(ax, "c", "Plateau-noise QA")
    set_compact_legend(ax, ncol=3, loc="best")

    ax = axs[1, 1]
    q_s, dbdq = gradient_unique(q, array_from(down, "Bmag_uT"))
    if len(q_s):
        ax.plot(q_s, np.abs(dbdq), "o-", color=PALETTE["black"], label="|d|B|/dq|")
    for axis, key in (("Bx", "mean_Bx_uT"), ("By", "mean_By_uT"), ("Bz", "mean_Bz_uT")):
        q_s, dydq = gradient_unique(q, array_from(down, key))
        if len(q_s):
            ax.plot(q_s, np.abs(dydq), "-", color=AXIS_COLORS[axis], alpha=0.75, label=axis)
    setup_axis(ax, "gap q (mm)", "local sensitivity (uT mm$^{-1}$)")
    add_panel(ax, "d", "Jacobian prior from B(q)")
    set_compact_legend(ax, ncol=2, loc="best")

    add_stage_header(fig, f"Stage C final session: {session.name}")
    return export_figure(fig, "stage_C_pure_displacement")


def load_stage_d(session: Path) -> dict[str, np.ndarray]:
    rows = read_csv(session / "D_safety_range.csv")
    out = {
        "phase": np.array([r.get("phase", "") for r in rows]),
        "step": array_from(rows, "step"),
        "mark10_pos_mm": array_from(rows, "mark10_pos_mm"),
        "d": array_from(rows, "d_compression_mm"),
        "F": array_from(rows, "F_mean_N"),
        "F_std": array_from(rows, "F_std_N"),
        "Bx": array_from(rows, "mean_Bx_uT"),
        "By": array_from(rows, "mean_By_uT"),
        "Bz": array_from(rows, "mean_Bz_uT"),
        "Bmag": array_from(rows, "Bmag_uT"),
    }
    return out


def plot_stage_d(session: Path) -> list[Path]:
    data = load_stage_d(session)
    approach = data["phase"] == "approach"
    probe = data["phase"] == "probe"
    descent = -data["mark10_pos_mm"]

    fig, axs = plt.subplots(2, 2, figsize=(7.2, 5.4))

    ax = axs[0, 0]
    if probe.any():
        ax.errorbar(
            data["d"][probe],
            data["F"][probe],
            yerr=2 * data["F_std"][probe],
            fmt="o-",
            color=PALETTE["blue"],
            capsize=2,
        )
    ax.axhline(0, color=PALETTE["black"], lw=0.6, alpha=0.45)
    setup_axis(ax, "compression d (mm)", "F (N)")
    add_panel(ax, "a", "Safety sweep force envelope")

    ax = axs[0, 1]
    if probe.any():
        ax.plot(data["d"][probe], data["Bmag"][probe], "o-", color=PALETTE["red"])
    setup_axis(ax, "compression d (mm)", "|B| (uT)")
    add_panel(ax, "b", "Magnetic amplitude during probe")

    ax = axs[1, 0]
    if approach.any():
        ax.plot(descent[approach], data["F"][approach] * 1000, "o-", color=PALETTE["gray"], label="approach")
    if probe.any():
        ax.plot(descent[probe], data["F"][probe] * 1000, "s-", color=PALETTE["blue"], label="probe")
    ax.axhline(0, color=PALETTE["black"], lw=0.6, alpha=0.45)
    setup_axis(ax, "stage descent (mm)", "F (mN)")
    add_panel(ax, "c", "Contact emergence across sweep")
    set_compact_legend(ax, loc="best")

    ax = axs[1, 1]
    for axis in ("Bx", "By", "Bz"):
        if approach.any():
            ax.plot(descent[approach], data[axis][approach], "o-", color=AXIS_COLORS[axis], alpha=0.35)
        if probe.any():
            ax.plot(descent[probe], data[axis][probe], "s-", color=AXIS_COLORS[axis], label=axis)
    ax.axhline(0, color=PALETTE["black"], lw=0.6, alpha=0.45)
    setup_axis(ax, "stage descent (mm)", "B component (uT)")
    add_panel(ax, "d", "Three-axis response at safe range")
    set_compact_legend(ax, ncol=3, loc="best")

    add_stage_header(fig, f"Stage D final session: {session.name}")
    return export_figure(fig, "stage_D_safety_range")


def load_stage_e(session: Path) -> dict[int, dict[str, np.ndarray]]:
    trials: dict[int, dict[str, np.ndarray]] = {}
    for path in sorted(session.glob("E_basic_loading_rep*.csv")):
        m = re.search(r"rep(\d+)$", path.stem)
        trial = int(m.group(1)) if m else len(trials) + 1
        rows = read_csv(path)
        trials[trial] = {
            "d_target": array_from(rows, "d_target_mm"),
            "d": array_from(rows, "d_actual_mm"),
            "F": array_from(rows, "F_mean_N"),
            "F_std": array_from(rows, "F_std_N"),
            "Bx": array_from(rows, "mean_Bx_uT"),
            "By": array_from(rows, "mean_By_uT"),
            "Bz": array_from(rows, "mean_Bz_uT"),
            "Bmag": array_from(rows, "Bmag_uT"),
        }
    return trials


def plot_stage_e(session: Path) -> list[Path]:
    trials = load_stage_e(session)
    fig, axs = plt.subplots(2, 2, figsize=(7.2, 5.4))

    ax = axs[0, 0]
    for i, trial in enumerate(sorted(trials)):
        d = trials[trial]["d"]
        f = trials[trial]["F"]
        ferr = 2 * trials[trial]["F_std"]
        ax.errorbar(d, f, yerr=ferr, fmt="o-", color=SERIES_COLORS[i], capsize=2, label=f"rep {trial}")
    ax.axhline(0, color=PALETTE["black"], lw=0.6, alpha=0.45)
    setup_axis(ax, "compression d (mm)", "F (N)")
    add_panel(ax, "a", "Mechanical loading curve")
    set_compact_legend(ax, ncol=3, loc="best")

    ax = axs[0, 1]
    for i, trial in enumerate(sorted(trials)):
        ax.plot(trials[trial]["d"], trials[trial]["Bmag"], "o-", color=SERIES_COLORS[i], label=f"rep {trial}")
    setup_axis(ax, "compression d (mm)", "|B| (uT)")
    add_panel(ax, "b", "Magnetic response to compression")
    set_compact_legend(ax, ncol=3, loc="best")

    ax = axs[1, 0]
    for i, trial in enumerate(sorted(trials)):
        ax.plot(trials[trial]["F"], trials[trial]["Bmag"], "o-", color=SERIES_COLORS[i], label=f"rep {trial}")
    setup_axis(ax, "F (N)", "|B| (uT)")
    add_panel(ax, "c", "Force-magnetic coupling")
    set_compact_legend(ax, ncol=3, loc="best")

    ax = axs[1, 1]
    for i, trial in enumerate(sorted(trials)):
        f_s, dbdf = gradient_unique(trials[trial]["F"], trials[trial]["Bmag"])
        if len(f_s):
            ax.plot(f_s, dbdf, "o-", color=SERIES_COLORS[i], label=f"rep {trial}")
    ax.axhline(0, color=PALETTE["black"], lw=0.6, alpha=0.45)
    setup_axis(ax, "F (N)", "d|B|/dF (uT N$^{-1}$)")
    add_panel(ax, "d", "Local B-F sensitivity")
    set_compact_legend(ax, ncol=3, loc="best")

    add_stage_header(fig, f"Stage E final session: {session.name}")
    return export_figure(fig, "stage_E_basic_loading")


def load_stage_f(session: Path) -> dict[int, dict[str, dict[str, np.ndarray]]]:
    trials: dict[int, dict[str, dict[str, np.ndarray]]] = {}
    for path in sorted(session.glob("F_load_unload_rep*.csv")):
        m = re.search(r"rep(\d+)$", path.stem)
        trial = int(m.group(1)) if m else len(trials) + 1
        rows = read_csv(path)
        by_phase: dict[str, dict[str, np.ndarray]] = {}
        for phase in ("loading", "unloading"):
            sub = [r for r in rows if r.get("phase") == phase]
            if not sub:
                continue
            cols = {
                "d_target": array_from(sub, "d_target_mm"),
                "d": array_from(sub, "d_actual_mm"),
                "F": array_from(sub, "F_mean_N"),
                "Bx": array_from(sub, "mean_Bx_uT"),
                "By": array_from(sub, "mean_By_uT"),
                "Bz": array_from(sub, "mean_Bz_uT"),
                "Bmag": array_from(sub, "Bmag_uT"),
            }
            limit = np.nanmax(cols["d_target"]) + 0.75 if np.isfinite(cols["d_target"]).any() else np.inf
            valid = np.isfinite(cols["d"]) & (cols["d"] >= -0.25) & (cols["d"] <= limit)
            for key in cols:
                cols[key] = cols[key][valid]
            by_phase[phase] = cols
        if by_phase:
            trials[trial] = by_phase
    return trials


def plot_branch_pair(ax, load, unload, x_key, y_key, color) -> None:
    ax.plot(load[x_key], load[y_key], "o-", color=color, label="_nolegend_")
    ax.plot(unload[x_key], unload[y_key], "s--", color=color, alpha=0.78, label="_nolegend_")
    if len(load[x_key]) and len(unload[x_key]):
        ax.plot(
            [load[x_key][-1], unload[x_key][0]],
            [load[y_key][-1], unload[y_key][0]],
            ":",
            color=color,
            alpha=0.55,
            lw=0.9,
        )


def plot_stage_f(session: Path) -> list[Path]:
    trials = load_stage_f(session)
    fig, axs = plt.subplots(2, 2, figsize=(7.2, 5.4))

    for i, trial in enumerate(sorted(trials)):
        load = trials[trial].get("loading")
        unload = trials[trial].get("unloading")
        if load is None or unload is None:
            continue
        color = SERIES_COLORS[i]
        plot_branch_pair(axs[0, 0], load, unload, "d", "F", color)
        plot_branch_pair(axs[0, 1], load, unload, "d", "Bmag", color)
        plot_branch_pair(axs[1, 0], load, unload, "F", "Bmag", color)

        ord_u = np.argsort(unload["d"])
        d_u = unload["d"][ord_u]
        f_u = unload["F"][ord_u]
        b_u = unload["Bmag"][ord_u]
        d_load = load["d"]
        overlap = finite_mask(d_load, load["F"], load["Bmag"]) & (d_load >= np.nanmin(d_u)) & (d_load <= np.nanmax(d_u))
        if overlap.any() and len(np.unique(d_u[np.isfinite(d_u)])) >= 2:
            f_un = np.interp(d_load[overlap], d_u, f_u)
            b_un = np.interp(d_load[overlap], d_u, b_u)
            axs[1, 1].plot(d_load[overlap], (load["F"][overlap] - f_un) * 1000, "o-", color=color, label=f"F rep {trial}")
            axs[1, 1].plot(d_load[overlap], load["Bmag"][overlap] - b_un, "s--", color=color, alpha=0.72, label=f"|B| rep {trial}")

    axs[0, 0].axhline(0, color=PALETTE["black"], lw=0.6, alpha=0.45)
    setup_axis(axs[0, 0], "compression d (mm)", "F (N)")
    add_panel(axs[0, 0], "a", "Load-unload mechanical loop")

    setup_axis(axs[0, 1], "compression d (mm)", "|B| (uT)")
    add_panel(axs[0, 1], "b", "Magnetic hysteresis loop")

    setup_axis(axs[1, 0], "F (N)", "|B| (uT)")
    add_panel(axs[1, 0], "c", "B-F path dependence")

    rep_handles = [
        Line2D([0], [0], color=SERIES_COLORS[i], marker="o", lw=1.2, label=f"rep {trial}")
        for i, trial in enumerate(sorted(trials))
    ]
    phase_handles = [
        Line2D([0], [0], color=PALETTE["gray_dark"], marker="o", lw=1.2, ls="-", label="loading"),
        Line2D([0], [0], color=PALETTE["gray_dark"], marker="s", lw=1.2, ls="--", label="unloading"),
    ]
    for ax in (axs[0, 0], axs[0, 1], axs[1, 0]):
        leg1 = ax.legend(handles=rep_handles, loc="upper left", ncol=3, handlelength=1.4, borderaxespad=0.2)
        ax.add_artist(leg1)
        ax.legend(handles=phase_handles, loc="lower right", handlelength=1.4, borderaxespad=0.2)

    axs[1, 1].axhline(0, color=PALETTE["black"], lw=0.6, alpha=0.45)
    setup_axis(axs[1, 1], "compression d (mm)", "load - unload (mN or uT)")
    add_panel(axs[1, 1], "d", "Loop amplitude at matched d")
    set_compact_legend(axs[1, 1], ncol=2, loc="best")

    add_stage_header(fig, f"Stage F final session: {session.name}")
    return export_figure(fig, "stage_F_hysteresis")


def load_stage_h(session: Path) -> dict[int, dict[str, np.ndarray]]:
    trials: dict[int, dict[str, np.ndarray]] = {}
    for path in sorted(session.glob("H_force_control_rep*.csv")):
        m = re.search(r"rep(\d+)$", path.stem)
        trial = int(m.group(1)) if m else len(trials) + 1
        rows = read_csv(path)
        trials[trial] = {
            "target_F": array_from(rows, "F_target_N"),
            "F": array_from(rows, "F_mean_N"),
            "F_err": array_from(rows, "F_error_N"),
            "d": array_from(rows, "d_actual_mm"),
            "Bmag": array_from(rows, "Bmag_uT"),
            "reached": np.array([safe_int(r.get("target_reached")) for r in rows], dtype=bool),
        }
    return trials


def plot_stage_h(session: Path) -> list[Path]:
    trials = load_stage_h(session)
    fig, axs = plt.subplots(2, 2, figsize=(7.2, 5.4))

    all_targets = []
    for i, trial in enumerate(sorted(trials)):
        d = trials[trial]
        color = SERIES_COLORS[i]
        reached = d["reached"]
        all_targets.extend(d["target_F"][np.isfinite(d["target_F"])])
        axs[0, 0].plot(d["target_F"], d["F"], "o-", color=color, label=f"rep {trial}")
        axs[0, 0].scatter(d["target_F"][~reached], d["F"][~reached], s=28, facecolors="none", edgecolors=color, lw=0.8)
        axs[0, 1].plot(d["F"], d["Bmag"], "o-", color=color, label=f"rep {trial}")
        axs[0, 1].scatter(d["F"][~reached], d["Bmag"][~reached], s=28, facecolors="none", edgecolors=color, lw=0.8)
        axs[1, 0].plot(d["F"], d["d"], "o-", color=color, label=f"rep {trial}")
        axs[1, 1].plot(d["target_F"], d["F_err"] * 1000, "o-", color=color, label=f"rep {trial}")

    if all_targets:
        lo, hi = np.nanmin(all_targets), np.nanmax(all_targets)
        axs[0, 0].plot([lo, hi], [lo, hi], ":", color=PALETTE["black"], lw=0.9, label="ideal")

    setup_axis(axs[0, 0], "target F (N)", "actual F (N)")
    add_panel(axs[0, 0], "a", "Force-control tracking")
    set_compact_legend(axs[0, 0], loc="best")

    setup_axis(axs[0, 1], "actual F (N)", "|B| (uT)")
    add_panel(axs[0, 1], "b", "B-F response under force control")
    set_compact_legend(axs[0, 1], loc="best")

    setup_axis(axs[1, 0], "actual F (N)", "d (mm)")
    add_panel(axs[1, 0], "c", "Compression needed to hold force")
    set_compact_legend(axs[1, 0], loc="best")

    axs[1, 1].axhline(0, color=PALETTE["black"], lw=0.6, alpha=0.45)
    setup_axis(axs[1, 1], "target F (N)", "F error (mN)")
    add_panel(axs[1, 1], "d", "Residual control error")
    set_compact_legend(axs[1, 1], loc="best")

    add_stage_header(fig, f"Stage H final session: {session.name}")
    return export_figure(fig, "stage_H_force_control")


def load_stage_i(session: Path) -> dict[tuple[int, int], dict[str, np.ndarray]]:
    data: dict[tuple[int, int], dict[str, np.ndarray]] = {}
    for path in sorted(session.glob("I_hold_disp_*.csv")):
        m = re.search(r"I_hold_disp_(\d+)_rep(\d+)", path.stem)
        if not m:
            continue
        hold = int(m.group(1))
        rep = int(m.group(2))
        rows = read_csv(path)
        data[(hold, rep)] = {
            "t": array_from(rows, "t_rel_s"),
            "F": array_from(rows, "F_N"),
            "d": array_from(rows, "d_actual_mm"),
            "Bx": array_from(rows, "mean_Bx_uT"),
            "By": array_from(rows, "mean_By_uT"),
            "Bz": array_from(rows, "mean_Bz_uT"),
            "Bmag": array_from(rows, "Bmag_uT"),
        }
    return data


def plot_stage_i(session: Path) -> list[Path]:
    data = load_stage_i(session)
    fig, axs = plt.subplots(2, 2, figsize=(7.2, 5.4))

    labels = []
    slopes = []
    colors = []
    for i, key in enumerate(sorted(data)):
        hold, rep = key
        d = data[key]
        color = SERIES_COLORS[i]
        colors.append(color)
        t = d["t"] - np.nanmin(d["t"])
        label = f"{hold}% dmax"
        labels.append(label)
        axs[0, 0].plot(t, d["F"] * 1000, color=color, label=label)
        axs[0, 1].plot(t, d["Bmag"], color=color, label=label)
        axs[1, 0].plot(d["F"], d["Bmag"], ".", color=color, alpha=0.7, label=label)
        slope, intercept, r2 = linfit(d["F"], d["Bmag"])
        slopes.append(slope)
        if np.isfinite(slope):
            order = np.argsort(d["F"])
            x = d["F"][order]
            axs[1, 0].plot(x, slope * x + intercept, color=color, lw=1.1)

    setup_axis(axs[0, 0], "time (s)", "F (mN)")
    add_panel(axs[0, 0], "a", "Force relaxation at fixed d")
    set_compact_legend(axs[0, 0], loc="best")

    setup_axis(axs[0, 1], "time (s)", "|B| (uT)")
    add_panel(axs[0, 1], "b", "Magnetic drift during hold")
    set_compact_legend(axs[0, 1], loc="best")

    setup_axis(axs[1, 0], "F (N)", "|B| (uT)")
    add_panel(axs[1, 0], "c", "Fixed-d slope for j_F")
    set_compact_legend(axs[1, 0], loc="best")

    ax = axs[1, 1]
    x = np.arange(len(labels))
    ax.bar(x, slopes, color=colors, edgecolor="white", linewidth=0.3)
    ax.axhline(0, color=PALETTE["black"], lw=0.6, alpha=0.45)
    ax.set_xticks(x, labels, rotation=20, ha="right")
    setup_axis(ax, None, "d|B|/dF (uT N$^{-1}$)")
    add_panel(ax, "d", "First-pass j_F diagnostic")

    add_stage_header(fig, f"Stage I final session: {session.name}")
    return export_figure(fig, "stage_I_fixed_displacement_hold")


def load_stage_j(session: Path) -> dict[tuple[int, int], dict[str, np.ndarray]]:
    data: dict[tuple[int, int], dict[str, np.ndarray]] = {}
    for path in sorted(session.glob("J_hold_force_*.csv")):
        m = re.search(r"J_hold_force_(\d+)_rep(\d+)", path.stem)
        if not m:
            continue
        hold = int(m.group(1))
        rep = int(m.group(2))
        rows = read_csv(path)
        cols = {
            "t": array_from(rows, "t_rel_s"),
            "F_target": array_from(rows, "F_target_N"),
            "F": array_from(rows, "F_N"),
            "d": array_from(rows, "d_actual_mm"),
            "Bx": array_from(rows, "mean_Bx_uT"),
            "By": array_from(rows, "mean_By_uT"),
            "Bz": array_from(rows, "mean_Bz_uT"),
            "Bmag": array_from(rows, "Bmag_uT"),
        }
        if len(cols["t"]) > 3 and np.isfinite(cols["t"]).any():
            t0 = np.nanmin(cols["t"])
            mask = cols["t"] >= t0 + 1.0
            if mask.sum() >= 3:
                for k in cols:
                    cols[k] = cols[k][mask]
        data[(hold, rep)] = cols
    return data


def plot_stage_j(session: Path) -> list[Path]:
    data = load_stage_j(session)
    fig, axs = plt.subplots(2, 2, figsize=(7.2, 5.4))

    labels = []
    slopes = []
    colors = []
    for i, key in enumerate(sorted(data)):
        hold, rep = key
        d = data[key]
        color = SERIES_COLORS[i]
        colors.append(color)
        t = d["t"] - np.nanmin(d["t"])
        label = f"{hold}% Fmax"
        labels.append(label)
        axs[0, 0].plot(t, d["F"], color=color, label=label)
        if np.isfinite(d["F_target"]).any():
            axs[0, 0].axhline(np.nanmedian(d["F_target"]), color=color, ls=":", lw=0.8, alpha=0.75)
        axs[0, 1].plot(t, d["d"], color=color, label=label)
        axs[1, 0].plot(d["d"], d["Bmag"], ".", color=color, alpha=0.7, label=label)
        slope, intercept, r2 = linfit(d["d"], d["Bmag"])
        slopes.append(slope)
        if np.isfinite(slope):
            order = np.argsort(d["d"])
            x = d["d"][order]
            axs[1, 0].plot(x, slope * x + intercept, color=color, lw=1.1)

    setup_axis(axs[0, 0], "time (s)", "F (N)")
    add_panel(axs[0, 0], "a", "Fixed-force hold tracking")
    set_compact_legend(axs[0, 0], loc="best")

    setup_axis(axs[0, 1], "time (s)", "d (mm)")
    add_panel(axs[0, 1], "b", "Creep or controller displacement")
    set_compact_legend(axs[0, 1], loc="best")

    setup_axis(axs[1, 0], "d (mm)", "|B| (uT)")
    add_panel(axs[1, 0], "c", "Fixed-F slope for j_q")
    set_compact_legend(axs[1, 0], loc="best")

    ax = axs[1, 1]
    x = np.arange(len(labels))
    ax.bar(x, slopes, color=colors, edgecolor="white", linewidth=0.3)
    ax.axhline(0, color=PALETTE["black"], lw=0.6, alpha=0.45)
    ax.set_xticks(x, labels, rotation=20, ha="right")
    setup_axis(ax, None, "d|B|/dd (uT mm$^{-1}$)")
    add_panel(ax, "d", "First-pass j_q diagnostic")

    add_stage_header(fig, f"Stage J final session: {session.name}")
    return export_figure(fig, "stage_J_fixed_force_hold")


STAGE_SPECS = [
    ("B", "B_baseline_summary.csv", plot_stage_b),
    ("C", "C_summary.csv", plot_stage_c),
    ("D", "D_safety_range.csv", plot_stage_d),
    ("E", "E_basic_loading_rep1.csv", plot_stage_e),
    ("F", "F_load_unload_rep1.csv", plot_stage_f),
    ("H", "H_force_control_rep1.csv", plot_stage_h),
    ("I", "I_hold_disp_*_rep1.csv", plot_stage_i),
    ("J", "J_hold_force_*_rep1.csv", plot_stage_j),
]


def write_index(records: list[dict[str, str]], skipped: list[str]) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index = OUT_DIR / "FIGURE_INDEX.md"
    lines = [
        "# Nature-style stage figures",
        "",
        "Primary format is SVG with editable text. PDF, PNG, and TIFF previews are exported next to each SVG.",
        "",
        "Selection rule: latest `decouple_data/session_*` folder containing the stage-specific final-session file pattern.",
        "",
        "| Stage | Session | Figure base | Source pattern |",
        "|---|---|---|---|",
    ]
    for r in records:
        lines.append(f"| {r['stage']} | {r['session']} | `{r['figure']}` | `{r['pattern']}` |")
    if skipped:
        lines.extend(["", "Skipped stages without matching data:", ""])
        for item in skipped:
            lines.append(f"- {item}")
    lines.append("")
    index.write_text("\n".join(lines), encoding="utf-8")
    return index


def main() -> None:
    apply_style()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Nature figure contract:")
    print("  Core conclusion: final sessions form the APMD evidence chain.")
    print("  Archetype: quantitative grid")
    print("  Backend: Python/matplotlib")
    print(f"  Output: {OUT_DIR}")

    records: list[dict[str, str]] = []
    skipped: list[str] = []

    for stage, pattern, plotter in STAGE_SPECS:
        session = latest_session_with(pattern)
        if session is None:
            skipped.append(f"Stage {stage} ({pattern})")
            print(f"Stage {stage}: skipped, no data matching {pattern}")
            continue
        print(f"Stage {stage}: {session.name}")
        saved = plotter(session)
        figure_base = saved[0].with_suffix("").name if saved else ""
        records.append(
            {
                "stage": stage,
                "session": session.name,
                "figure": figure_base,
                "pattern": pattern,
            }
        )
        for path in saved:
            print(f"  saved {path.relative_to(ROOT)}")

    index = write_index(records, skipped)
    print(f"Index: {index.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
