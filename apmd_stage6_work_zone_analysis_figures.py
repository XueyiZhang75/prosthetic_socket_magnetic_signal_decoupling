from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import GroupKFold, KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parent
REPORT_DIR = ROOT / "reports"
PREDICTION_CSV = REPORT_DIR / "apmd_stage6_local_identifiability_predictions.csv"

LOCAL_ID_MODEL = "apmd_local_identifiability_ridge"

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
    "preload_deep": "#888888",
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
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 8,
            "figure.titlesize": 15,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 1.0,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
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


def load_local_id_predictions() -> pd.DataFrame:
    if not PREDICTION_CSV.exists():
        raise FileNotFoundError(PREDICTION_CSV)
    all_rows = pd.read_csv(PREDICTION_CSV)
    df = all_rows[all_rows["model"].eq(LOCAL_ID_MODEL)].copy()
    if df.empty:
        raise RuntimeError(f"No rows found for {LOCAL_ID_MODEL}")
    df["work_zone"] = df["experiment"].map(assign_work_zone)
    df["abs_F_error_N"] = df["F_error_N"].abs()
    df["abs_d_error_mm"] = df["d_error_mm"].abs()
    df["state_uid"] = (
        df["session_id"].astype(str)
        + "|"
        + df["cycle_index"].astype(str)
        + "|"
        + df["state_index"].astype(str)
        + "|"
        + df["path_label"].astype(str)
    )
    return df


def save_figure(fig: plt.Figure, stem: str) -> None:
    png = REPORT_DIR / f"{stem}.png"
    pdf = REPORT_DIR / f"{stem}.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {png.relative_to(ROOT)}")
    print(f"saved {pdf.relative_to(ROOT)}")


def plot_fd_coverage(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7.6, 5.3), dpi=220)

    for zone in ZONE_ORDER:
        zdf = df[df["work_zone"].eq(zone)]
        for branch in BRANCH_ORDER:
            sub = zdf[zdf["path_label"].eq(branch)]
            if sub.empty:
                continue
            ax.scatter(
                sub["d_mm"],
                sub["F_N"],
                s=28,
                marker=BRANCH_MARKERS[branch],
                facecolor=ZONE_COLORS[zone],
                edgecolor="white",
                linewidth=0.45,
                alpha=0.86,
                zorder=3,
            )

    for zone in ZONE_ORDER:
        zdf = df[df["work_zone"].eq(zone)]
        if zdf.empty:
            continue
        d_min, d_max = zdf["d_mm"].min(), zdf["d_mm"].max()
        f_min, f_max = zdf["F_N"].min(), zdf["F_N"].max()
        ax.add_patch(
            plt.Rectangle(
                (d_min, f_min),
                d_max - d_min,
                f_max - f_min,
                facecolor=ZONE_COLORS[zone],
                edgecolor=ZONE_COLORS[zone],
                linewidth=1.2,
                alpha=0.075,
                zorder=1,
            )
        )
        ax.text(
            (d_min + d_max) / 2,
            f_max + 0.35,
            zone,
            ha="center",
            va="bottom",
            color=ZONE_COLORS[zone],
            fontsize=8,
            weight="bold",
        )

    zone_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="",
            markerfacecolor=ZONE_COLORS[z],
            markeredgecolor="white",
            markersize=7,
            label=z,
        )
        for z in ZONE_ORDER
    ]
    branch_handles = [
        Line2D(
            [0],
            [0],
            marker=BRANCH_MARKERS[b],
            linestyle="",
            color="#444444",
            markerfacecolor="#444444",
            markeredgecolor="white",
            markersize=7,
            label=BRANCH_LABELS[b],
        )
        for b in BRANCH_ORDER
    ]
    first = ax.legend(handles=zone_handles, title="work zone", frameon=False, loc="upper left")
    ax.add_artist(first)
    ax.legend(handles=branch_handles, title="state", frameon=False, loc="lower right")

    ax.set_title("F-d coverage of accepted held-out dense-loop states")
    ax.set_xlabel("measured d (mm)")
    ax.set_ylabel("measured F (N)")
    ax.grid(True, color="#E7E7E7", linewidth=0.8)
    fig.suptitle(
        "Stage 6.3 work-zone state coverage",
        x=0.02,
        y=1.02,
        ha="left",
        weight="bold",
    )
    fig.text(
        0.02,
        0.965,
        "Rectangles show the observed F-d span of each held-out dense-loop work zone.",
        ha="left",
        color="#555555",
    )
    save_figure(fig, "apmd_stage6_work_zone_fd_coverage")


def build_metric_table(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for zone in ZONE_ORDER:
        sub = df[df["work_zone"].eq(zone)]
        records.append(
            {
                "work_zone": zone,
                "n_states": len(sub),
                "d_min_mm": sub["d_mm"].min(),
                "d_max_mm": sub["d_mm"].max(),
                "F_min_N": sub["F_N"].min(),
                "F_max_N": sub["F_N"].max(),
                "F_MAE_N": sub["abs_F_error_N"].mean(),
                "d_MAE_mm": sub["abs_d_error_mm"].mean(),
                "F_p90_N": sub["abs_F_error_N"].quantile(0.90),
                "d_p90_mm": sub["abs_d_error_mm"].quantile(0.90),
                "F_bias_N": sub["F_error_N"].mean(),
                "d_bias_mm": sub["d_error_mm"].mean(),
                "angle_median_deg": sub["local_angle_deg"].median(),
                "pF_median_kuT": sub["local_p_F_uT"].abs().median() / 1000.0,
                "pD_median_kuT": sub["local_p_d_uT"].abs().median() / 1000.0,
                "residual_median_kuT": sub["local_residual_uT"].abs().median()
                / 1000.0,
            }
        )
    metrics = pd.DataFrame(records)
    metrics.to_csv(REPORT_DIR / "apmd_stage6_work_zone_metric_table.csv", index=False)
    return metrics


def plot_metric_heatmap(metrics: pd.DataFrame) -> None:
    cols = [
        ("F_MAE_N", "F MAE\n(N)", "{:.3f}"),
        ("d_MAE_mm", "d MAE\n(mm)", "{:.3f}"),
        ("F_p90_N", "|F err|\np90", "{:.3f}"),
        ("d_p90_mm", "|d err|\np90", "{:.3f}"),
        ("angle_median_deg", "angle\n(deg)", "{:.1f}"),
        ("pF_median_kuT", "|pF|\n(k uT)", "{:.2f}"),
        ("pD_median_kuT", "|pD|\n(k uT)", "{:.2f}"),
        ("residual_median_kuT", "residual\n(k uT)", "{:.2f}"),
    ]
    data = metrics[[c[0] for c in cols]].to_numpy(dtype=float)
    norm = np.zeros_like(data)
    for j in range(data.shape[1]):
        col = data[:, j]
        span = np.nanmax(col) - np.nanmin(col)
        if span <= 1e-12:
            norm[:, j] = 0.5
        else:
            norm[:, j] = (col - np.nanmin(col)) / span

    fig, ax = plt.subplots(figsize=(9.0, 3.6), dpi=220)
    im = ax.imshow(norm, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(len(cols)))
    ax.set_xticklabels([c[1] for c in cols])
    ax.set_yticks(np.arange(len(ZONE_ORDER)))
    ax.set_yticklabels(ZONE_ORDER)
    ax.set_title("Work-zone metrics from local-ID ridge held-out predictions")
    ax.tick_params(length=0)

    for i, zone in enumerate(ZONE_ORDER):
        for j, (col, _, fmt) in enumerate(cols):
            value = metrics.loc[metrics["work_zone"].eq(zone), col].iloc[0]
            color = "white" if norm[i, j] > 0.58 else "#222222"
            ax.text(j, i, fmt.format(value), ha="center", va="center", color=color)

    for x in np.arange(-0.5, len(cols), 1):
        ax.axvline(x, color="white", linewidth=1.2)
    for y in np.arange(-0.5, len(ZONE_ORDER), 1):
        ax.axhline(y, color="white", linewidth=1.2)
    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("column-normalized magnitude")
    fig.suptitle(
        "Stage 6.3 work-zone metric map",
        x=0.02,
        y=1.05,
        ha="left",
        weight="bold",
    )
    fig.text(
        0.02,
        0.965,
        "Color intensity is normalized within each metric column; cell text shows the actual value.",
        ha="left",
        color="#555555",
    )
    save_figure(fig, "apmd_stage6_work_zone_metric_heatmap")


def _draw_grouped_distribution(
    ax: plt.Axes,
    df: pd.DataFrame,
    value_col: str,
    ylabel: str,
    title: str,
) -> None:
    offsets = {"direct_loading": -0.23, "return_unloading": 0.0, "preload_deep": 0.23}
    width = 0.18
    rng = np.random.default_rng(42)

    for zi, zone in enumerate(ZONE_ORDER):
        for branch in BRANCH_ORDER:
            vals = (
                df[df["work_zone"].eq(zone) & df["path_label"].eq(branch)][value_col]
                .dropna()
                .to_numpy()
            )
            if vals.size == 0:
                continue
            pos = zi + offsets[branch]
            bp = ax.boxplot(
                [vals],
                positions=[pos],
                widths=width,
                showfliers=False,
                patch_artist=True,
                medianprops={"color": "white", "linewidth": 1.2},
                boxprops={"linewidth": 0.9, "color": BRANCH_COLORS[branch]},
                whiskerprops={"linewidth": 0.8, "color": BRANCH_COLORS[branch]},
                capprops={"linewidth": 0.8, "color": BRANCH_COLORS[branch]},
            )
            bp["boxes"][0].set_facecolor(BRANCH_COLORS[branch])
            bp["boxes"][0].set_alpha(0.52)
            jitter = rng.normal(0, 0.018, size=vals.size)
            ax.scatter(
                np.full(vals.size, pos) + jitter,
                vals,
                s=14,
                color=BRANCH_COLORS[branch],
                alpha=0.58,
                edgecolor="none",
                zorder=3,
            )

    ax.set_xticks(np.arange(len(ZONE_ORDER)))
    ax.set_xticklabels(ZONE_ORDER)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis="y", color="#E8E8E8", linewidth=0.8)


def plot_branch_error(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.3), dpi=220)
    _draw_grouped_distribution(
        axes[0],
        df,
        "abs_F_error_N",
        "|F prediction error| (N)",
        "Force residual by work zone and branch",
    )
    _draw_grouped_distribution(
        axes[1],
        df,
        "abs_d_error_mm",
        "|d prediction error| (mm)",
        "Displacement residual by work zone and branch",
    )
    handles = [
        Line2D(
            [0],
            [0],
            marker="s",
            linestyle="",
            markerfacecolor=BRANCH_COLORS[b],
            markeredgecolor=BRANCH_COLORS[b],
            markersize=8,
            label=BRANCH_LABELS[b],
        )
        for b in BRANCH_ORDER
    ]
    fig.legend(handles=handles, frameon=False, loc="upper center", ncol=3, bbox_to_anchor=(0.54, 0.96))
    fig.suptitle(
        "Stage 6.3 branch-resolved local-ID residuals",
        x=0.02,
        y=1.03,
        ha="left",
        weight="bold",
    )
    fig.text(
        0.02,
        0.96,
        "Each distribution uses the same held-out dense-loop states and the same local-ID ridge predictions.",
        ha="left",
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    save_figure(fig, "apmd_stage6_work_zone_branch_error")


def transfer_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    feature_cols = [
        "local_p_F_uT",
        "local_p_d_uT",
        "local_residual_uT",
        "local_angle_deg",
    ]
    x = df[feature_cols].copy()
    dummies = pd.get_dummies(df["path_label"], prefix="branch")
    for branch in BRANCH_ORDER:
        col = f"branch_{branch}"
        if col not in dummies:
            dummies[col] = 0
    dummies = dummies[[f"branch_{b}" for b in BRANCH_ORDER]]
    x = pd.concat([x, dummies], axis=1)
    y = df[["F_N", "d_mm"]].copy()
    return x, y


def _fit_predict_mae(x_train, y_train, x_test, y_test) -> tuple[float, float]:
    model = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    model.fit(x_train, y_train)
    pred = model.predict(x_test)
    return (
        float(mean_absolute_error(y_test.iloc[:, 0], pred[:, 0])),
        float(mean_absolute_error(y_test.iloc[:, 1], pred[:, 1])),
    )


def _within_zone_cv_mae(x: pd.DataFrame, y: pd.DataFrame, groups: pd.Series) -> tuple[float, float]:
    unique_groups = groups.astype(str).unique()
    if len(unique_groups) >= 3:
        splitter = GroupKFold(n_splits=min(5, len(unique_groups)))
        splits = splitter.split(x, y, groups=groups)
    else:
        splitter = KFold(n_splits=min(5, len(x)), shuffle=True, random_state=13)
        splits = splitter.split(x, y)

    preds = np.full((len(y), 2), np.nan)
    for train_idx, test_idx in splits:
        model = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
        model.fit(x.iloc[train_idx], y.iloc[train_idx])
        preds[test_idx, :] = model.predict(x.iloc[test_idx])

    ok = ~np.isnan(preds[:, 0])
    return (
        float(mean_absolute_error(y.iloc[ok, 0], preds[ok, 0])),
        float(mean_absolute_error(y.iloc[ok, 1], preds[ok, 1])),
    )


def build_transfer_matrices(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    x_all, y_all = transfer_features(df)
    f_matrix = pd.DataFrame(index=ZONE_ORDER, columns=ZONE_ORDER, dtype=float)
    d_matrix = pd.DataFrame(index=ZONE_ORDER, columns=ZONE_ORDER, dtype=float)

    for train_zone in ZONE_ORDER:
        train_mask = df["work_zone"].eq(train_zone)
        for test_zone in ZONE_ORDER:
            test_mask = df["work_zone"].eq(test_zone)
            if train_zone == test_zone:
                group = (
                    df.loc[train_mask, "session_id"].astype(str)
                    + "|"
                    + df.loc[train_mask, "cycle_index"].astype(str)
                )
                f_mae, d_mae = _within_zone_cv_mae(
                    x_all.loc[train_mask],
                    y_all.loc[train_mask],
                    group,
                )
            else:
                f_mae, d_mae = _fit_predict_mae(
                    x_all.loc[train_mask],
                    y_all.loc[train_mask],
                    x_all.loc[test_mask],
                    y_all.loc[test_mask],
                )
            f_matrix.loc[train_zone, test_zone] = f_mae
            d_matrix.loc[train_zone, test_zone] = d_mae

    f_matrix.to_csv(REPORT_DIR / "apmd_stage6_work_zone_transfer_F_MAE_matrix.csv")
    d_matrix.to_csv(REPORT_DIR / "apmd_stage6_work_zone_transfer_d_MAE_matrix.csv")
    return f_matrix, d_matrix


def _draw_transfer_heatmap(
    ax: plt.Axes,
    matrix: pd.DataFrame,
    title: str,
    cbar_label: str,
    fmt: str,
) -> None:
    data = matrix.loc[ZONE_ORDER, ZONE_ORDER].to_numpy(dtype=float)
    im = ax.imshow(data, cmap="Reds", aspect="auto")
    ax.set_xticks(np.arange(len(ZONE_ORDER)))
    ax.set_xticklabels(ZONE_ORDER, rotation=30, ha="right")
    ax.set_yticks(np.arange(len(ZONE_ORDER)))
    ax.set_yticklabels(ZONE_ORDER)
    ax.set_xlabel("test work zone")
    ax.set_ylabel("train work zone")
    ax.set_title(title)

    threshold = np.nanmin(data) + 0.62 * (np.nanmax(data) - np.nanmin(data))
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            color = "white" if data[i, j] > threshold else "#222222"
            ax.text(j, i, fmt.format(data[i, j]), ha="center", va="center", color=color)
    for x in np.arange(-0.5, len(ZONE_ORDER), 1):
        ax.axvline(x, color="white", linewidth=1.2)
    for y in np.arange(-0.5, len(ZONE_ORDER), 1):
        ax.axhline(y, color="white", linewidth=1.2)
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    cbar.set_label(cbar_label)


def plot_transfer_matrices(f_matrix: pd.DataFrame, d_matrix: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.8), dpi=220)
    _draw_transfer_heatmap(
        axes[0],
        f_matrix,
        "Zone-transfer force MAE",
        "F MAE (N)",
        "{:.2f}",
    )
    _draw_transfer_heatmap(
        axes[1],
        d_matrix,
        "Zone-transfer displacement MAE",
        "d MAE (mm)",
        "{:.3f}",
    )
    fig.suptitle(
        "Stage 6.3 work-zone transfer diagnostic",
        x=0.02,
        y=1.04,
        ha="left",
        weight="bold",
    )
    fig.text(
        0.02,
        0.965,
        "Rows train a local-ID coordinate ridge on one zone; columns test on another. Diagonal cells use grouped within-zone cross-validation.",
        ha="left",
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    save_figure(fig, "apmd_stage6_work_zone_transfer_matrix")


def write_report(metrics: pd.DataFrame, f_matrix: pd.DataFrame, d_matrix: pd.DataFrame) -> None:
    report = REPORT_DIR / "APMD_STAGE6_WORK_ZONE_ANALYSIS_FIGURES.md"
    lines = [
        "# Stage 6.3 Work-Zone Analysis Figures",
        "",
        "This note records four work-zone-level diagnostic figures generated from the current accepted Stage 6.3 local-identifiability prediction table.",
        "",
        "## Generated Figures",
        "",
        "- `apmd_stage6_work_zone_fd_coverage.png`: measured force-displacement coverage of the held-out dense-loop states.",
        "- `apmd_stage6_work_zone_metric_heatmap.png`: zone-level error, local geometry, and residual feature map.",
        "- `apmd_stage6_work_zone_branch_error.png`: branch-resolved error distributions by work zone.",
        "- `apmd_stage6_work_zone_transfer_matrix.png`: train-zone by test-zone transfer diagnostic using local-ID coordinate features.",
        "",
        "## Zone Metrics",
        "",
        metrics.to_markdown(index=False, floatfmt=".3f"),
        "",
        "## Transfer Matrix: Force MAE (N)",
        "",
        f_matrix.to_markdown(floatfmt=".3f"),
        "",
        "## Transfer Matrix: Displacement MAE (mm)",
        "",
        d_matrix.to_markdown(floatfmt=".3f"),
        "",
        "Interpretation note: the transfer matrix is a diagnostic, not a replacement for session-level held-out validation. Off-diagonal cells intentionally ask whether a mapping learned in one work zone can predict another work zone.",
        "",
    ]
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"saved {report.relative_to(ROOT)}")


def main() -> None:
    set_style()
    REPORT_DIR.mkdir(exist_ok=True)
    df = load_local_id_predictions()
    metrics = build_metric_table(df)
    f_matrix, d_matrix = build_transfer_matrices(df)
    plot_fd_coverage(df)
    plot_metric_heatmap(metrics)
    plot_branch_error(df)
    plot_transfer_matrices(f_matrix, d_matrix)
    write_report(metrics, f_matrix, d_matrix)


if __name__ == "__main__":
    main()
