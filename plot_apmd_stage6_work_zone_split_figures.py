from __future__ import annotations

import matplotlib.pyplot as plt

from apmd_stage6_predict_local_heldout import load_heldout_states, prepare_training_states
from apmd_stage6_work_zone_eight_panel_summary import (
    ROOT,
    REPORT_DIR,
    ZONE_ORDER,
    add_panel_label,
    assign_work_zone,
    build_transfer_matrices,
    branch_metric_table,
    draw_branch_heatmap,
    draw_fd_coverage,
    draw_local_violin,
    draw_metric_heatmap,
    draw_model_bars,
    draw_signed_force_residual,
    draw_transfer_heatmaps,
    load_predictions,
    local_zone_metric_table,
    model_metric_table,
    set_style,
)


OUT_RESIDUAL_PNG = REPORT_DIR / "apmd_stage6_zone_resolved_heldout_residuals.png"
OUT_RESIDUAL_PDF = REPORT_DIR / "apmd_stage6_zone_resolved_heldout_residuals.pdf"
OUT_GEOMETRY_PNG = REPORT_DIR / "apmd_stage6_work_zone_geometry_transfer_summary.png"
OUT_GEOMETRY_PDF = REPORT_DIR / "apmd_stage6_work_zone_geometry_transfer_summary.pdf"


def add_figure_header(
    fig: plt.Figure,
    title: str,
    subtitle: str,
    title_size: float = 17,
    subtitle_size: float = 9.6,
) -> None:
    fig.text(
        0.018,
        0.982,
        title,
        ha="left",
        va="top",
        fontsize=title_size,
        fontweight="bold",
        fontfamily="Arial",
    )
    fig.text(
        0.018,
        0.942,
        subtitle,
        ha="left",
        va="top",
        fontsize=subtitle_size,
        color="#555555",
        fontfamily="Arial",
    )


def save(fig: plt.Figure, png_path, pdf_path) -> None:
    fig.savefig(png_path, bbox_inches="tight", dpi=300)
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {png_path.relative_to(ROOT)}")
    print(f"saved {pdf_path.relative_to(ROOT)}")


def enlarge_geometry_text(fig: plt.Figure) -> None:
    """Increase readability for the dense geometry/transfer panels."""
    for text in fig.texts:
        text.set_fontfamily("Arial")

    for ax in fig.axes:
        ax.title.set_fontsize(13.2)
        ax.title.set_fontfamily("Arial")
        ax.xaxis.label.set_fontsize(11.4)
        ax.xaxis.label.set_fontfamily("Arial")
        ax.yaxis.label.set_fontsize(11.4)
        ax.yaxis.label.set_fontfamily("Arial")
        ax.tick_params(axis="both", labelsize=9.4)
        for tick_text in [*ax.get_xticklabels(), *ax.get_yticklabels()]:
            tick_text.set_fontfamily("Arial")

        for text in ax.texts:
            text.set_fontfamily("Arial")
            if text.get_text() in {"a", "b", "c", "d"}:
                text.set_fontsize(16.5)
            else:
                text.set_fontsize(max(text.get_fontsize() * 1.65, 10.6))

        legend = ax.get_legend()
        if legend is not None:
            for text in legend.get_texts():
                text.set_fontsize(9.2)
                text.set_fontfamily("Arial")
            legend.get_frame().set_linewidth(0.0)


def build_state_count_subtitle() -> str:
    train = prepare_training_states().copy()
    test = load_heldout_states().copy()
    train["work_zone"] = train["experiment"].map(assign_work_zone)
    test["work_zone"] = test["experiment"].map(assign_work_zone)

    parts = []
    for zone in ZONE_ORDER:
        train_n = int(train["work_zone"].eq(zone).sum())
        test_n = int(test["work_zone"].eq(zone).sum())
        parts.append(f"{zone}: train {train_n}, test {test_n}")
    return "States by work zone - " + "; ".join(parts) + "."


def draw_residual_figure(df, local) -> None:
    model_metrics = model_metric_table(df)

    fig = plt.figure(figsize=(16.8, 10.0), dpi=240)
    gs = fig.add_gridspec(
        2,
        2,
        hspace=0.30,
        wspace=0.22,
        left=0.055,
        right=0.985,
        top=0.855,
        bottom=0.075,
    )
    axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2)]

    draw_model_bars(axes[0], model_metrics, "F_MAE_N", "F MAE (N)", "Force MAE by work zone")
    draw_model_bars(
        axes[1],
        model_metrics,
        "d_MAE_mm",
        "d MAE (mm)",
        "Displacement MAE by work zone",
    )
    draw_local_violin(axes[2], local)
    draw_signed_force_residual(axes[3], local)

    for label, ax in zip("abcd", axes):
        add_panel_label(ax, label)

    add_figure_header(
        fig,
        "Stage 6.3 zone-resolved held-out residuals",
        "Same Stage 6.3 ridge predictions; held-out states split by actual dense-loop work-zone sessions.",
    )
    save(fig, OUT_RESIDUAL_PNG, OUT_RESIDUAL_PDF)


def draw_geometry_figure(local) -> None:
    local_metrics = local_zone_metric_table(local)
    branch_metrics = branch_metric_table(local)
    f_transfer, d_transfer = build_transfer_matrices(local)

    fig = plt.figure(figsize=(20.2, 11.3), dpi=240)
    gs = fig.add_gridspec(
        2,
        2,
        width_ratios=[1.0, 1.18],
        hspace=0.40,
        wspace=0.28,
        left=0.058,
        right=0.982,
        top=0.840,
        bottom=0.100,
    )
    axes = [
        fig.add_subplot(gs[0, 0]),
        fig.add_subplot(gs[0, 1]),
        fig.add_subplot(gs[1, 0]),
    ]
    transfer_axes = draw_transfer_heatmaps(fig, gs[1, 1], f_transfer, d_transfer)

    draw_fd_coverage(axes[0], local)
    draw_metric_heatmap(axes[1], local_metrics)
    draw_branch_heatmap(axes[2], branch_metrics)

    for label, ax in zip("abc", axes):
        add_panel_label(ax, label)
    add_panel_label(transfer_axes[0], "d")

    add_figure_header(
        fig,
        "Stage 6.3 work-zone geometry and transfer diagnostics",
        build_state_count_subtitle(),
        title_size=20,
        subtitle_size=11.2,
    )
    enlarge_geometry_text(fig)
    save(fig, OUT_GEOMETRY_PNG, OUT_GEOMETRY_PDF)


def main() -> None:
    set_style()
    df, local = load_predictions()
    draw_residual_figure(df, local)
    draw_geometry_figure(local)


if __name__ == "__main__":
    main()
