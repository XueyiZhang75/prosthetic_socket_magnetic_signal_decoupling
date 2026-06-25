"""Plot predicted state distributions in F-d space for Stage 6.3 models.

This plot complements measured-vs-predicted fit panels.  Instead of asking
whether each point lies on the 1:1 line, it asks whether the predicted states
reconstruct the held-out work-zone state cloud in physical F-d space.
"""

from __future__ import annotations

from pathlib import Path
import sys

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PREDICTIONS_CSV = REPORTS_DIR / "apmd_stage6_local_identifiability_predictions.csv"
METRICS_CSV = REPORTS_DIR / "apmd_stage6_local_identifiability_model_metrics.csv"
OUT_PNG = REPORTS_DIR / "apmd_stage6_state_distribution_by_model.png"
OUT_PDF = REPORTS_DIR / "apmd_stage6_state_distribution_by_model.pdf"

BLACK = "#222222"
BLUE = "#2c7fb8"
GRAY = "#8a8a8a"
RED = "#c23b3b"
LIGHT_GRAY = "#e7e7e7"
TRUE_GRAY = "#b9b9b9"

MODELS = [
    ("plain_magnetic_ridge", "Plain magnetic", "B only"),
    ("lim_style_branch_ridge", "Path-label", "B + branch label"),
    ("apmd_path_memory_ridge", "Path-memory", "B + path history"),
    ("apmd_local_identifiability_ridge", "Local-ID", "B + path history + local jF/jd"),
]

PATH_COLORS = {
    "direct_loading": BLACK,
    "return_unloading": BLUE,
    "preload_deep": GRAY,
}

PATH_LABELS = {
    "direct_loading": "direct loading",
    "return_unloading": "return unloading",
    "preload_deep": "preload state",
}


def _set_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "axes.linewidth": 0.9,
            "axes.labelsize": 9.5,
            "axes.titlesize": 11,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "legend.fontsize": 8.8,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def _limits(values: pd.Series, pred: pd.Series, step: float, pad_frac: float = 0.04) -> tuple[float, float]:
    low = float(min(values.min(), pred.min()))
    high = float(max(values.max(), pred.max()))
    span = high - low
    pad = span * pad_frac if span > 0 else step
    return (
        float(np.floor((low - pad) / step) * step),
        float(np.ceil((high + pad) / step) * step),
    )


def _panel(
    ax: plt.Axes,
    truth: pd.DataFrame,
    pred: pd.DataFrame,
    metrics: pd.Series,
    x_lims: tuple[float, float],
    y_lims: tuple[float, float],
    title: str,
) -> None:
    ax.scatter(
        truth["d_mm"],
        truth["F_N"],
        s=20,
        c=TRUE_GRAY,
        edgecolors="none",
        alpha=0.26,
        label="measured state cloud",
        zorder=1,
    )
    for path_label, group in pred.groupby("path_label", sort=False):
        ax.scatter(
            group["d_pred_mm"],
            group["F_pred_N"],
            s=30,
            c=PATH_COLORS.get(path_label, RED),
            edgecolors="white",
            linewidths=0.35,
            alpha=0.88,
            zorder=3,
        )

    ax.set_xlim(*x_lims)
    ax.set_ylim(*y_lims)
    ax.xaxis.set_major_locator(MultipleLocator(0.5))
    ax.xaxis.set_minor_locator(MultipleLocator(0.25))
    ax.yaxis.set_major_locator(MultipleLocator(5.0))
    ax.yaxis.set_minor_locator(MultipleLocator(2.5))
    ax.grid(which="major", color=LIGHT_GRAY, linewidth=0.75)
    ax.grid(which="minor", color="#f2f2f2", linewidth=0.45)
    ax.set_axisbelow(True)
    ax.set_xlabel("predicted or measured d (mm)")
    ax.set_ylabel("predicted or measured F (N)")
    ax.set_title(title, loc="left", fontweight="bold", pad=8)
    ax.text(
        0.04,
        0.94,
        f"F MAE = {float(metrics['F_MAE_N']):.3f} N\n"
        f"d MAE = {float(metrics['d_MAE_mm']):.3f} mm",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.8,
        color="#333333",
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "none", "alpha": 0.86},
    )
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)


def main() -> None:
    _set_style()
    predictions = pd.read_csv(PREDICTIONS_CSV)
    metrics = pd.read_csv(METRICS_CSV).set_index("model")

    selected = predictions[predictions["model"].isin([m[0] for m in MODELS])].copy()
    if selected.empty:
        raise RuntimeError("No selected model predictions found.")

    truth = selected.drop_duplicates(
        ["session_id", "cycle_index", "state_index", "path_label", "d_mm", "F_N"]
    )
    x_lims = _limits(selected["d_mm"], selected["d_pred_mm"], step=0.5)
    y_lims = _limits(selected["F_N"], selected["F_pred_N"], step=5.0)

    fig, axes = plt.subplots(1, len(MODELS), figsize=(16.6, 4.9), dpi=260, sharex=True, sharey=True)
    for idx, (model_name, model_title, subtitle) in enumerate(MODELS):
        if model_name not in metrics.index:
            raise RuntimeError(f"Missing metrics for {model_name}")
        data = predictions[predictions["model"] == model_name].copy()
        _panel(
            axes[idx],
            truth,
            data,
            metrics.loc[model_name],
            x_lims,
            y_lims,
            f"{chr(ord('a') + idx)}  {model_title}\n{subtitle}",
        )

    legend_handles = [
        Line2D([0], [0], marker="o", linestyle="none", markerfacecolor=TRUE_GRAY, markeredgecolor="none", alpha=0.45, markersize=7, label="measured states"),
        *[
            Line2D(
                [0],
                [0],
                marker="o",
                linestyle="none",
                markerfacecolor=PATH_COLORS[key],
                markeredgecolor="white",
                markeredgewidth=0.35,
                markersize=7,
                label=f"predicted {PATH_LABELS[key]}",
            )
            for key in ["direct_loading", "return_unloading", "preload_deep"]
        ],
    ]

    train_n = int(metrics.iloc[0]["train_n_states"])
    heldout_n = int(metrics.iloc[0]["heldout_n_states"])
    fig.suptitle(
        "Stage 6.3 predicted state distributions in F-d space",
        x=0.055,
        y=1.02,
        ha="left",
        fontsize=15.5,
        fontweight="bold",
    )
    fig.text(
        0.055,
        0.965,
        f"Gray background: measured held-out state cloud. Colored points: model-predicted states "
        f"(train = {train_n}, held-out = {heldout_n}).",
        ha="left",
        fontsize=9.6,
        color="#555555",
    )
    fig.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.54, 0.92),
        ncol=4,
        frameon=False,
        columnspacing=1.55,
        handletextpad=0.5,
    )
    fig.subplots_adjust(left=0.055, right=0.99, top=0.76, bottom=0.14, wspace=0.18)

    fig.savefig(OUT_PNG, bbox_inches="tight")
    fig.savefig(OUT_PDF, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved {OUT_PNG.relative_to(ROOT)}")
    print(f"Saved {OUT_PDF.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
