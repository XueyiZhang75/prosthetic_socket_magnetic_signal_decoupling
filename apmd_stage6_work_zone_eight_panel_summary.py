from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parent
REPORT_DIR = ROOT / "reports"
PREDICTION_CSV = REPORT_DIR / "apmd_stage6_local_identifiability_predictions.csv"

OUT_PNG = REPORT_DIR / "apmd_stage6_work_zone_eight_panel_summary.png"
OUT_PDF = REPORT_DIR / "apmd_stage6_work_zone_eight_panel_summary.pdf"

RIDGE_MODELS = [
    "plain_magnetic_ridge",
    "lim_style_branch_ridge",
    "apmd_path_memory_ridge",
    "apmd_local_identifiability_ridge",
]
LOCAL_ID_MODEL = "apmd_local_identifiability_ridge"

MODEL_LABELS = {
    "plain_magnetic_ridge": "plain\nmagnetic",
    "lim_style_branch_ridge": "branch\nlabel",
    "apmd_path_memory_ridge": "path\nmemory",
    "apmd_local_identifiability_ridge": "local-ID",
}
MODEL_COLORS = {
    "plain_magnetic_ridge": "#222222",
    "lim_style_branch_ridge": "#2C7FB8",
    "apmd_path_memory_ridge": "#858585",
    "apmd_local_identifiability_ridge": "#C43C39",
}

ZONE_ORDER = ["1.8-2.6 mm", "2.4-3.2 mm", "3.0-3.8 mm", "3.4-4.2 mm"]
ZONE_COLORS = {
    "1.8-2.6 mm": "#4C78A8",
    "2.4-3.2 mm": "#59A14F",
    "3.0-3.8 mm": "#C43C39",
    "3.4-4.2 mm": "#7B61A8",
}
BRANCH_ORDER = ["direct_loading", "return_unloading", "preload_deep"]
BRANCH_LABELS = {
    "direct_loading": "direct",
    "return_unloading": "return",
    "preload_deep": "preload",
}
BRANCH_COLORS = {
    "direct_loading": "#222222",
    "return_unloading": "#2C7FB8",
    "preload_deep": "#858585",
}
BRANCH_MARKERS = {
    "direct_loading": "o",
    "return_unloading": "s",
    "preload_deep": "^",
}


def set_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.sans-serif": ["Arial"],
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.linewidth": 0.9,
            "axes.labelsize": 9,
            "axes.titlesize": 10.5,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 7,
        }
    )


def assign_work_zone(experiment: str) -> str:
    text = str(experiment)
    if "6.1-S" in text or "shallow" in text:
        return "1.8-2.6 mm"
    if "6.1-L" in text or "Block L" in text:
        return "2.4-3.2 mm"
    if "6.1-H" in text or "upper" in text:
        return "3.4-4.2 mm"
    return "3.0-3.8 mm"


def load_predictions() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(PREDICTION_CSV)
    df = df[df["model"].isin(RIDGE_MODELS)].copy()
    df["work_zone"] = df["experiment"].map(assign_work_zone)
    df["work_zone"] = pd.Categorical(df["work_zone"], ZONE_ORDER, ordered=True)
    df["abs_F_error_N"] = df["F_error_N"].abs()
    df["abs_d_error_mm"] = df["d_error_mm"].abs()
    local = df[df["model"].eq(LOCAL_ID_MODEL)].copy()
    return df, local


def model_metric_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (zone, model), chunk in df.groupby(["work_zone", "model"], observed=True):
        rows.append(
            {
                "work_zone": str(zone),
                "model": model,
                "F_MAE_N": chunk["abs_F_error_N"].mean(),
                "d_MAE_mm": chunk["abs_d_error_mm"].mean(),
            }
        )
    return pd.DataFrame(rows)


def local_zone_metric_table(local: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for zone, sub in local.groupby("work_zone", observed=True):
        rows.append(
            {
                "work_zone": str(zone),
                "F_MAE_N": sub["abs_F_error_N"].mean(),
                "d_MAE_mm": sub["abs_d_error_mm"].mean(),
                "F_p90_N": sub["abs_F_error_N"].quantile(0.90),
                "d_p90_mm": sub["abs_d_error_mm"].quantile(0.90),
                "angle_median_deg": sub["local_angle_deg"].median(),
                "pF_median_kuT": sub["local_p_F_uT"].abs().median() / 1000.0,
                "pD_median_kuT": sub["local_p_d_uT"].abs().median() / 1000.0,
                "residual_median_kuT": sub["local_residual_uT"].abs().median() / 1000.0,
            }
        )
    return pd.DataFrame(rows)


def branch_metric_table(local: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (zone, branch), sub in local.groupby(["work_zone", "path_label"], observed=True):
        rows.append(
            {
                "work_zone": str(zone),
                "branch": branch,
                "F_MAE_N": sub["abs_F_error_N"].mean(),
                "d_MAE_mm": sub["abs_d_error_mm"].mean(),
            }
        )
    return pd.DataFrame(rows)


def transfer_features(local: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    x = local[["local_p_F_uT", "local_p_d_uT", "local_residual_uT", "local_angle_deg"]].copy()
    dummies = pd.get_dummies(local["path_label"], prefix="branch")
    for branch in BRANCH_ORDER:
        col = f"branch_{branch}"
        if col not in dummies:
            dummies[col] = 0
    x = pd.concat([x, dummies[[f"branch_{b}" for b in BRANCH_ORDER]]], axis=1)
    y = local[["F_N", "d_mm"]].copy()
    return x, y


def build_transfer_matrices(local: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    x, y = transfer_features(local)
    f_mat = pd.DataFrame(index=ZONE_ORDER, columns=ZONE_ORDER, dtype=float)
    d_mat = pd.DataFrame(index=ZONE_ORDER, columns=ZONE_ORDER, dtype=float)
    for train_zone in ZONE_ORDER:
        train_mask = local["work_zone"].astype(str).eq(train_zone)
        for test_zone in ZONE_ORDER:
            test_mask = local["work_zone"].astype(str).eq(test_zone)
            if train_zone == test_zone:
                groups = (
                    local.loc[train_mask, "session_id"].astype(str)
                    + "|"
                    + local.loc[train_mask, "cycle_index"].astype(str)
                )
                splitter = GroupKFold(n_splits=min(5, groups.nunique()))
                pred = np.full((train_mask.sum(), 2), np.nan)
                local_x = x.loc[train_mask].reset_index(drop=True)
                local_y = y.loc[train_mask].reset_index(drop=True)
                local_groups = groups.reset_index(drop=True)
                for tr, te in splitter.split(local_x, local_y, groups=local_groups):
                    model = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
                    model.fit(local_x.iloc[tr], local_y.iloc[tr])
                    pred[te] = model.predict(local_x.iloc[te])
                f_mat.loc[train_zone, test_zone] = mean_absolute_error(local_y.iloc[:, 0], pred[:, 0])
                d_mat.loc[train_zone, test_zone] = mean_absolute_error(local_y.iloc[:, 1], pred[:, 1])
            else:
                model = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
                model.fit(x.loc[train_mask], y.loc[train_mask])
                pred = model.predict(x.loc[test_mask])
                f_mat.loc[train_zone, test_zone] = mean_absolute_error(
                    y.loc[test_mask].iloc[:, 0], pred[:, 0]
                )
                d_mat.loc[train_zone, test_zone] = mean_absolute_error(
                    y.loc[test_mask].iloc[:, 1], pred[:, 1]
                )
    return f_mat, d_mat


def add_panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.12,
        1.08,
        label,
        transform=ax.transAxes,
        fontsize=13,
        fontweight="bold",
        ha="left",
        va="top",
    )


def format_axes(ax: plt.Axes) -> None:
    ax.grid(color="#E8E8E8", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def add_bar_labels(ax: plt.Axes, bars, fmt: str, stagger: int = 0) -> None:
    ymax = max((bar.get_height() for bar in bars), default=0)
    offset = ymax * 0.018 if ymax > 0 else 0.01
    for bar in bars:
        value = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + offset * (1.0 + 0.75 * stagger),
            fmt.format(value),
            ha="center",
            va="bottom",
            fontsize=5.7,
        )


def draw_model_bars(ax: plt.Axes, metrics: pd.DataFrame, value_col: str, ylabel: str, title: str) -> None:
    x = np.arange(len(ZONE_ORDER)) * 1.55
    width = 0.16
    offsets = np.array([-0.36, -0.12, 0.12, 0.36])
    for model_index, (model, offset) in enumerate(zip(RIDGE_MODELS, offsets)):
        values = (
            metrics[metrics["model"].eq(model)]
            .set_index("work_zone")
            .reindex(ZONE_ORDER)[value_col]
            .to_numpy(float)
        )
        bars = ax.bar(
            x + offset,
            values,
            width=width,
            color=MODEL_COLORS[model],
            label=MODEL_LABELS[model].replace("\n", " "),
        )
        add_bar_labels(
            ax,
            bars,
            "{:.2f}" if value_col == "F_MAE_N" else "{:.3f}",
            stagger=model_index % 2,
        )
    ax.set_xticks(x)
    ax.set_xticklabels(ZONE_ORDER)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_ylim(top=ax.get_ylim()[1] * 1.12)
    ax.legend(
        frameon=False,
        ncol=2,
        loc="upper left",
        bbox_to_anchor=(0.00, 0.995),
        columnspacing=0.75,
        handletextpad=0.35,
        borderaxespad=0.0,
        fontsize=6.4,
    )
    format_axes(ax)


def draw_local_violin(ax: plt.Axes, local: pd.DataFrame) -> None:
    data = [
        local.loc[local["work_zone"].astype(str).eq(zone), "abs_F_error_N"].to_numpy(float)
        for zone in ZONE_ORDER
    ]
    x = np.arange(len(ZONE_ORDER))
    parts = ax.violinplot(data, positions=x, widths=0.72, showmedians=True, showextrema=False)
    for body, zone in zip(parts["bodies"], ZONE_ORDER):
        body.set_facecolor(ZONE_COLORS[zone])
        body.set_edgecolor(ZONE_COLORS[zone])
        body.set_alpha(0.23)
    parts["cmedians"].set_color("#222222")
    parts["cmedians"].set_linewidth(1.1)
    rng = np.random.default_rng(11)
    for i, zone in enumerate(ZONE_ORDER):
        vals = local.loc[local["work_zone"].astype(str).eq(zone), "abs_F_error_N"].to_numpy(float)
        ax.scatter(
            np.full(len(vals), i) + rng.normal(0, 0.045, size=len(vals)),
            vals,
            s=11,
            color=ZONE_COLORS[zone],
            alpha=0.55,
            edgecolor="white",
            linewidth=0.2,
        )
    ax.set_xticks(x)
    ax.set_xticklabels(ZONE_ORDER)
    ax.set_ylabel("|F error| (N)")
    ax.set_title("Local-ID absolute force residual distribution")
    format_axes(ax)


def draw_signed_force_residual(ax: plt.Axes, local: pd.DataFrame) -> None:
    for zone, sub in local.sort_values("d_mm").groupby("work_zone", observed=True):
        ax.scatter(
            sub["d_mm"],
            sub["F_error_N"],
            s=15,
            color=ZONE_COLORS[str(zone)],
            alpha=0.62,
            edgecolor="white",
            linewidth=0.25,
            label=str(zone),
        )
    ax.axhline(0, color="#222222", linewidth=0.8)
    ax.set_xlabel("measured d (mm)")
    ax.set_ylabel("F prediction error (N)")
    ax.set_title("Local-ID signed force residual across d")
    ax.legend(frameon=False, ncol=2, fontsize=6.5, loc="upper right")
    format_axes(ax)


def draw_fd_coverage(ax: plt.Axes, local: pd.DataFrame) -> None:
    for zone in ZONE_ORDER:
        zone_df = local[local["work_zone"].astype(str).eq(zone)]
        if zone_df.empty:
            continue
        d_min, d_max = zone_df["d_mm"].min(), zone_df["d_mm"].max()
        f_min, f_max = zone_df["F_N"].min(), zone_df["F_N"].max()
        ax.add_patch(
            plt.Rectangle(
                (d_min, f_min),
                d_max - d_min,
                f_max - f_min,
                facecolor=ZONE_COLORS[zone],
                edgecolor=ZONE_COLORS[zone],
                alpha=0.07,
                linewidth=1.0,
            )
        )
        for branch in BRANCH_ORDER:
            sub = zone_df[zone_df["path_label"].eq(branch)]
            ax.scatter(
                sub["d_mm"],
                sub["F_N"],
                s=18,
                marker=BRANCH_MARKERS[branch],
                facecolor=ZONE_COLORS[zone],
                edgecolor="white",
                linewidth=0.28,
                alpha=0.84,
            )
    ax.set_xlabel("measured d (mm)")
    ax.set_ylabel("measured F (N)")
    ax.set_title("F-d coverage of held-out dense-loop states")
    zone_handles = [
        Line2D([0], [0], marker="o", linestyle="", color=ZONE_COLORS[z], markersize=5.5, label=z)
        for z in ZONE_ORDER
    ]
    ax.legend(handles=zone_handles, frameon=False, fontsize=6.2, loc="upper left")
    format_axes(ax)


def draw_metric_heatmap(ax: plt.Axes, metrics: pd.DataFrame) -> None:
    columns = [
        ("F_MAE_N", "F\nMAE", "{:.3f}"),
        ("d_MAE_mm", "d\nMAE", "{:.3f}"),
        ("F_p90_N", "F\np90", "{:.3f}"),
        ("d_p90_mm", "d\np90", "{:.3f}"),
        ("angle_median_deg", "angle", "{:.1f}"),
        ("pF_median_kuT", "|pF|", "{:.2f}"),
        ("pD_median_kuT", "|pD|", "{:.2f}"),
        ("residual_median_kuT", "resid.", "{:.2f}"),
    ]
    table = metrics.set_index("work_zone").reindex(ZONE_ORDER)
    raw = table[[c[0] for c in columns]].to_numpy(float)
    norm = np.zeros_like(raw)
    for j in range(raw.shape[1]):
        col = raw[:, j]
        span = np.nanmax(col) - np.nanmin(col)
        norm[:, j] = 0.5 if span <= 1e-12 else (col - np.nanmin(col)) / span
    im = ax.imshow(norm, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(len(columns)))
    ax.set_xticklabels([c[1] for c in columns], fontsize=7)
    ax.set_yticks(np.arange(len(ZONE_ORDER)))
    ax.set_yticklabels(ZONE_ORDER)
    for i in range(len(ZONE_ORDER)):
        for j, (col, _, fmt) in enumerate(columns):
            color = "white" if norm[i, j] > 0.58 else "#222222"
            ax.text(j, i, fmt.format(raw[i, j]), ha="center", va="center", fontsize=6.4, color=color)
    for x in np.arange(-0.5, len(columns), 1):
        ax.axvline(x, color="white", linewidth=1)
    for y in np.arange(-0.5, len(ZONE_ORDER), 1):
        ax.axhline(y, color="white", linewidth=1)
    ax.tick_params(length=0)
    ax.set_title("Work-zone metric map")
    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.038, pad=0.018)
    cbar.set_label("relative value", fontsize=7)
    cbar.ax.tick_params(labelsize=6, length=2)


def draw_branch_heatmap(ax: plt.Axes, branch_metrics: pd.DataFrame) -> None:
    row_specs = []
    for metric, prefix in [("F_MAE_N", "F"), ("d_MAE_mm", "d")]:
        for branch in BRANCH_ORDER:
            row_specs.append((metric, branch, f"{prefix} {BRANCH_LABELS[branch]}"))
    raw = np.full((len(row_specs), len(ZONE_ORDER)), np.nan)
    for i, (metric, branch, _) in enumerate(row_specs):
        for j, zone in enumerate(ZONE_ORDER):
            match = branch_metrics[
                branch_metrics["work_zone"].eq(zone) & branch_metrics["branch"].eq(branch)
            ]
            if not match.empty:
                raw[i, j] = match[metric].iloc[0]
    norm = np.zeros_like(raw)
    for i in range(raw.shape[0]):
        row = raw[i, :]
        span = np.nanmax(row) - np.nanmin(row)
        norm[i, :] = 0.5 if span <= 1e-12 else (row - np.nanmin(row)) / span
    im = ax.imshow(norm, cmap="Purples", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(len(ZONE_ORDER)))
    ax.set_xticklabels(ZONE_ORDER, rotation=20, ha="right")
    ax.set_yticks(np.arange(len(row_specs)))
    ax.set_yticklabels([r[2] for r in row_specs])
    for i, (metric, _, _) in enumerate(row_specs):
        fmt = "{:.2f}" if metric == "F_MAE_N" else "{:.3f}"
        for j in range(len(ZONE_ORDER)):
            color = "white" if norm[i, j] > 0.58 else "#222222"
            ax.text(j, i, fmt.format(raw[i, j]), ha="center", va="center", fontsize=6.2, color=color)
    for x in np.arange(-0.5, len(ZONE_ORDER), 1):
        ax.axvline(x, color="white", linewidth=1)
    for y in np.arange(-0.5, len(row_specs), 1):
        ax.axhline(y, color="white", linewidth=1)
    ax.tick_params(length=0)
    ax.set_title("Branch-wise local-ID error map")
    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.038, pad=0.018)
    cbar.set_label("row-normalized error", fontsize=7)
    cbar.ax.tick_params(labelsize=6, length=2)


def draw_transfer_heatmaps(fig: plt.Figure, subplot_spec, f_mat: pd.DataFrame, d_mat: pd.DataFrame) -> list[plt.Axes]:
    sub = subplot_spec.subgridspec(1, 2, wspace=0.62)
    axes = [fig.add_subplot(sub[0, 0]), fig.add_subplot(sub[0, 1])]
    for ax, matrix, title, fmt in [
        (axes[0], f_mat, "F transfer\nMAE (N)", "{:.1f}"),
        (axes[1], d_mat, "d transfer\nMAE (mm)", "{:.2f}"),
    ]:
        data = matrix.loc[ZONE_ORDER, ZONE_ORDER].to_numpy(float)
        im = ax.imshow(data, cmap="Reds", aspect="auto")
        ax.set_xticks(np.arange(len(ZONE_ORDER)))
        ax.set_xticklabels([z.replace(" mm", "") for z in ZONE_ORDER], rotation=35, ha="right", fontsize=6)
        ax.set_yticks(np.arange(len(ZONE_ORDER)))
        ax.set_yticklabels([z.replace(" mm", "") for z in ZONE_ORDER], fontsize=6)
        threshold = np.nanmin(data) + 0.62 * (np.nanmax(data) - np.nanmin(data))
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                color = "white" if data[i, j] > threshold else "#222222"
                ax.text(j, i, fmt.format(data[i, j]), ha="center", va="center", fontsize=6.1, color=color)
        for x in np.arange(-0.5, len(ZONE_ORDER), 1):
            ax.axvline(x, color="white", linewidth=1)
        for y in np.arange(-0.5, len(ZONE_ORDER), 1):
            ax.axhline(y, color="white", linewidth=1)
        ax.tick_params(length=0)
        ax.set_title(title, fontsize=9.2)
        cbar = fig.colorbar(im, ax=ax, fraction=0.050, pad=0.025)
        cbar.set_label(title.replace("\n", " "), fontsize=6.3)
        cbar.ax.tick_params(labelsize=5.8, length=2)
    axes[0].set_ylabel("train zone")
    axes[0].set_xlabel("test zone")
    axes[1].set_xlabel("test zone")
    return axes


def main() -> None:
    set_style()
    df, local = load_predictions()
    model_metrics = model_metric_table(df)
    local_metrics = local_zone_metric_table(local)
    branch_metrics = branch_metric_table(local)
    f_transfer, d_transfer = build_transfer_matrices(local)

    fig = plt.figure(figsize=(27.0, 12.2), dpi=240)
    gs = fig.add_gridspec(
        2,
        4,
        width_ratios=[1.18, 1.18, 1.12, 1.48],
        hspace=0.44,
        wspace=0.34,
        left=0.038,
        right=0.988,
        top=0.965,
        bottom=0.080,
    )
    axes = [
        fig.add_subplot(gs[0, 0]),
        fig.add_subplot(gs[0, 1]),
        fig.add_subplot(gs[0, 2]),
        fig.add_subplot(gs[0, 3]),
        fig.add_subplot(gs[1, 0]),
        fig.add_subplot(gs[1, 1]),
        fig.add_subplot(gs[1, 2]),
    ]
    transfer_axes = draw_transfer_heatmaps(fig, gs[1, 3], f_transfer, d_transfer)

    draw_model_bars(axes[0], model_metrics, "F_MAE_N", "F MAE (N)", "Force MAE by work zone")
    draw_model_bars(axes[1], model_metrics, "d_MAE_mm", "d MAE (mm)", "Displacement MAE by work zone")
    draw_local_violin(axes[2], local)
    draw_signed_force_residual(axes[3], local)
    draw_fd_coverage(axes[4], local)
    draw_metric_heatmap(axes[5], local_metrics)
    draw_branch_heatmap(axes[6], branch_metrics)

    for label, ax in zip("abcdefg", axes):
        add_panel_label(ax, label)
    add_panel_label(transfer_axes[0], "h")

    fig.savefig(OUT_PNG, bbox_inches="tight", dpi=300)
    fig.savefig(OUT_PDF, bbox_inches="tight")
    plt.close(fig)

    print(f"saved {OUT_PNG.relative_to(ROOT)}")
    print(f"saved {OUT_PDF.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
