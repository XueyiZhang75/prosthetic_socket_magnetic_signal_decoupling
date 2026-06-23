from __future__ import annotations

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path
from statistics import median

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib as mpl
import matplotlib.pyplot as plt

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

EXP31_REPLICATES = REPORTS / "experiment_3_1_complete_figure_data_replicates.csv"
EXP32_REPLICATES = REPORTS / "experiment_3_2_same_f_different_d_figure_data_replicates.csv"

OUT_PAIR_TABLE = REPORTS / "apmd_stage4_identifiability_pair_table.csv"
OUT_JF_TABLE = REPORTS / "apmd_stage4_jF_from_same_d_pairs.csv"
OUT_JD_TABLE = REPORTS / "apmd_stage4_jd_from_same_f_pairs.csv"
OUT_SUMMARY = REPORTS / "apmd_stage4_identifiability_summary.csv"
OUT_REPORT = REPORTS / "APMD_STAGE4_IDENTIFIABILITY_ANALYSIS.md"
OUT_FIGURE = REPORTS / "apmd_stage4_identifiability_complete.png"

NOISE_FLOOR_UT = 10.0
D_LOCAL_SCALE_MM = 0.35
F_LOCAL_SCALE_N = 1.25

BLACK = "#222222"
RED = "#bf3f3f"
BLUE = "#2f84c5"
GRAY = "#777777"
LIGHT_GRAY = "#e5e5e5"
PALE = "#f1eadc"
GREEN = "#2ca25f"


mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": 8,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.9,
        "legend.frameon": False,
        "xtick.major.width": 0.9,
        "ytick.major.width": 0.9,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)


def ffloat(row: dict[str, str], key: str) -> float:
    return float(row[key])


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def vec_norm(v: np.ndarray) -> float:
    return float(np.linalg.norm(v))


def directional_consistency(vectors: list[np.ndarray], center: np.ndarray) -> float:
    center_norm = vec_norm(center)
    if center_norm == 0:
        return float("nan")
    vals: list[float] = []
    for v in vectors:
        n = vec_norm(v)
        if n == 0:
            continue
        vals.append(float(np.dot(v, center) / (n * center_norm)))
    return float(np.mean(vals)) if vals else float("nan")


def vector_angle_condition(jf: np.ndarray, jd: np.ndarray) -> tuple[float, float, float, float]:
    nf = vec_norm(jf)
    nd = vec_norm(jd)
    if nf == 0 or nd == 0:
        return float("nan"), float("nan"), float("nan"), float("nan")

    cos_signed = float(np.dot(jf, jd) / (nf * nd))
    cos_signed = max(-1.0, min(1.0, cos_signed))
    cos_abs = abs(cos_signed)
    angle_deg = math.degrees(math.acos(cos_abs))

    unit_j = np.column_stack([jf / nf, jd / nd])
    s_scaled = np.linalg.svd(unit_j, compute_uv=False)
    cond_scaled = float(s_scaled[0] / s_scaled[-1]) if s_scaled[-1] > 0 else float("inf")

    raw_j = np.column_stack([jf, jd])
    s_raw = np.linalg.svd(raw_j, compute_uv=False)
    cond_raw = float(s_raw[0] / s_raw[-1]) if s_raw[-1] > 0 else float("inf")
    return angle_deg, cos_abs, cond_scaled, cond_raw


def summarize_same_d(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    groups: dict[float, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("verdict") != "strong":
            continue
        groups[ffloat(row, "d_target_mm")].append(row)

    out: list[dict[str, object]] = []
    for d_target in sorted(groups):
        g = groups[d_target]
        vecs = [
            np.array(
                [
                    ffloat(r, "delta_Bx_uT"),
                    ffloat(r, "delta_By_uT"),
                    ffloat(r, "delta_Bz_uT"),
                ],
                dtype=float,
            )
            for r in g
        ]
        median_vec = np.array([median([float(v[i]) for v in vecs]) for i in range(3)], dtype=float)
        abs_delta_f = median([abs(ffloat(r, "delta_F_N")) for r in g])
        j_f = median_vec / abs_delta_f
        bvec = median([ffloat(r, "delta_Bvec_uT") for r in g])
        f_mid = median([(ffloat(r, "F_direct_N") + ffloat(r, "F_return_N")) / 2.0 for r in g])
        d_mid = median([(ffloat(r, "d_direct_mm") + ffloat(r, "d_return_mm")) / 2.0 for r in g])
        same_d_pass = sum(1 for r in g if r.get("same_d_ok") == "1") / len(g)
        force_pass = sum(1 for r in g if r.get("force_split_ok") == "1") / len(g)
        b_pass = sum(1 for r in g if r.get("b_signal_ok") == "1") / len(g)
        out.append(
            {
                "source": "same_d_different_F",
                "target_d_mm": d_target,
                "state_d_mid_mm": d_mid,
                "state_F_mid_N": f_mid,
                "n": len(g),
                "median_abs_delta_F_N": abs_delta_f,
                "median_delta_Bvec_uT": bvec,
                "noise_ratio": bvec / NOISE_FLOOR_UT,
                "median_delta_Bx_uT": median_vec[0],
                "median_delta_By_uT": median_vec[1],
                "median_delta_Bz_uT": median_vec[2],
                "jF_x_uT_per_N": j_f[0],
                "jF_y_uT_per_N": j_f[1],
                "jF_z_uT_per_N": j_f[2],
                "jF_norm_uT_per_N": vec_norm(j_f),
                "directional_consistency": directional_consistency(vecs, median_vec),
                "same_d_pass_rate": same_d_pass,
                "force_split_pass_rate": force_pass,
                "b_signal_pass_rate": b_pass,
            }
        )
    return out


def summarize_same_f(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    groups: dict[float, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[ffloat(row, "target_F")].append(row)

    out: list[dict[str, object]] = []
    for target_f in sorted(groups):
        g = groups[target_f]
        vecs = [
            np.array(
                [
                    ffloat(r, "delta_Bx"),
                    ffloat(r, "delta_By"),
                    ffloat(r, "delta_Bz"),
                ],
                dtype=float,
            )
            for r in g
        ]
        median_vec = np.array([median([float(v[i]) for v in vecs]) for i in range(3)], dtype=float)
        abs_delta_d = median([abs(ffloat(r, "delta_d")) for r in g])
        j_d = median_vec / abs_delta_d
        bvec = median([ffloat(r, "delta_Bvec") for r in g])
        d_mid = median([(ffloat(r, "d_loading") + ffloat(r, "d_unloading")) / 2.0 for r in g])
        same_f_pass = sum(1 for r in g if abs(ffloat(r, "delta_F")) <= 0.050) / len(g)
        disp_pass = sum(1 for r in g if abs(ffloat(r, "delta_d")) >= 0.100) / len(g)
        b_pass = sum(1 for r in g if ffloat(r, "delta_Bvec") >= 100.0) / len(g)
        out.append(
            {
                "source": "same_F_different_d",
                "target_F_N": target_f,
                "state_d_mid_mm": d_mid,
                "state_F_mid_N": target_f,
                "n": len(g),
                "median_abs_delta_d_mm": abs_delta_d,
                "median_delta_Bvec_uT": bvec,
                "noise_ratio": bvec / NOISE_FLOOR_UT,
                "median_delta_Bx_uT": median_vec[0],
                "median_delta_By_uT": median_vec[1],
                "median_delta_Bz_uT": median_vec[2],
                "jd_x_uT_per_mm": j_d[0],
                "jd_y_uT_per_mm": j_d[1],
                "jd_z_uT_per_mm": j_d[2],
                "jd_norm_uT_per_mm": vec_norm(j_d),
                "directional_consistency": directional_consistency(vecs, median_vec),
                "same_F_pass_rate": same_f_pass,
                "displacement_split_pass_rate": disp_pass,
                "b_signal_pass_rate": b_pass,
            }
        )
    return out


def make_pair_grid(jf_rows: list[dict[str, object]], jd_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    pairs: list[dict[str, object]] = []
    for frow in jf_rows:
        jf = np.array(
            [
                float(frow["jF_x_uT_per_N"]),
                float(frow["jF_y_uT_per_N"]),
                float(frow["jF_z_uT_per_N"]),
            ],
            dtype=float,
        )
        for drow in jd_rows:
            jd = np.array(
                [
                    float(drow["jd_x_uT_per_mm"]),
                    float(drow["jd_y_uT_per_mm"]),
                    float(drow["jd_z_uT_per_mm"]),
                ],
                dtype=float,
            )
            angle_deg, cos_abs, cond_scaled, cond_raw = vector_angle_condition(jf, jd)
            d_dist = abs(float(frow["state_d_mid_mm"]) - float(drow["state_d_mid_mm"]))
            f_dist = abs(float(frow["state_F_mid_N"]) - float(drow["state_F_mid_N"]))
            local_dist = math.sqrt((d_dist / D_LOCAL_SCALE_MM) ** 2 + (f_dist / F_LOCAL_SCALE_N) ** 2)
            local_score = math.exp(-0.5 * local_dist * local_dist)
            min_noise = min(float(frow["noise_ratio"]), float(drow["noise_ratio"]))
            consistency = (float(frow["directional_consistency"]) + float(drow["directional_consistency"])) / 2.0
            signal_score = min(min_noise / 10.0, 2.5)
            angle_score = angle_deg / 90.0
            condition_score = min(1.0, 5.0 / cond_scaled) if cond_scaled else 0.0
            ident_score = signal_score * angle_score * condition_score * consistency * local_score
            gate_angle = angle_deg >= 45.0
            gate_cond = cond_scaled <= 5.0
            gate_noise = min_noise >= 10.0
            gate_consistency = consistency >= 0.95
            gate_local = (d_dist <= 0.60) and (f_dist <= 1.75)
            if gate_angle and gate_cond and gate_noise and gate_consistency and gate_local:
                verdict = "candidate"
            elif angle_deg >= 35.0 and min_noise >= 8.0 and gate_local:
                verdict = "usable_but_weaker"
            else:
                verdict = "exploratory"
            pairs.append(
                {
                    "same_d_target_d_mm": frow["target_d_mm"],
                    "same_d_state_F_mid_N": frow["state_F_mid_N"],
                    "same_F_target_F_N": drow["target_F_N"],
                    "same_F_state_d_mid_mm": drow["state_d_mid_mm"],
                    "d_distance_mm": d_dist,
                    "F_distance_N": f_dist,
                    "jF_x_uT_per_N": jf[0],
                    "jF_y_uT_per_N": jf[1],
                    "jF_z_uT_per_N": jf[2],
                    "jF_norm_uT_per_N": frow["jF_norm_uT_per_N"],
                    "jd_x_uT_per_mm": jd[0],
                    "jd_y_uT_per_mm": jd[1],
                    "jd_z_uT_per_mm": jd[2],
                    "jd_norm_uT_per_mm": drow["jd_norm_uT_per_mm"],
                    "angle_deg": angle_deg,
                    "abs_cosine": cos_abs,
                    "condition_scaled": cond_scaled,
                    "condition_raw": cond_raw,
                    "same_d_noise_ratio": frow["noise_ratio"],
                    "same_F_noise_ratio": drow["noise_ratio"],
                    "min_noise_ratio": min_noise,
                    "directional_consistency_mean": consistency,
                    "locality_distance": local_dist,
                    "locality_score": local_score,
                    "identifiability_score": ident_score,
                    "verdict": verdict,
                }
            )
    pairs.sort(key=lambda r: float(r["identifiability_score"]), reverse=True)
    for i, row in enumerate(pairs, start=1):
        row["rank"] = i
    return pairs


def select_primary_pair(pairs: list[dict[str, object]]) -> dict[str, object]:
    for row in pairs:
        if row["verdict"] == "candidate":
            return row
    return pairs[0]


def fmt(x: object, digits: int = 3) -> str:
    try:
        return f"{float(x):.{digits}f}"
    except Exception:
        return str(x)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def plot_results(
    jf_rows: list[dict[str, object]],
    jd_rows: list[dict[str, object]],
    pairs: list[dict[str, object]],
) -> None:
    d_vals = [float(r["target_d_mm"]) for r in jf_rows]
    f_vals = [float(r["target_F_N"]) for r in jd_rows]
    angle_grid = np.zeros((len(d_vals), len(f_vals)))
    score_grid = np.zeros_like(angle_grid)
    cond_grid = np.zeros_like(angle_grid)
    pair_lookup = {
        (float(r["same_d_target_d_mm"]), float(r["same_F_target_F_N"])): r
        for r in pairs
    }
    for i, d in enumerate(d_vals):
        for j, f in enumerate(f_vals):
            r = pair_lookup[(d, f)]
            angle_grid[i, j] = float(r["angle_deg"])
            score_grid[i, j] = float(r["identifiability_score"])
            cond_grid[i, j] = float(r["condition_scaled"])

    best_score = pairs[0]
    primary = select_primary_pair(pairs)
    top_d = float(primary["same_d_target_d_mm"])
    top_f = float(primary["same_F_target_F_N"])

    fig = plt.figure(figsize=(12.5, 4.8))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.18, 1.0, 1.0], wspace=0.34)
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    ax2 = fig.add_subplot(gs[0, 2])

    fig.suptitle("Stage 4: local identifiability map from formal APMD path pairs", x=0.02, y=0.985, ha="left", fontsize=13, fontweight="bold")
    fig.text(0.02, 0.935, "Inputs: Experiment 3.1 same-d/different-F + Experiment 3.2 same-F/different-d formal accepted tables", ha="left", fontsize=9, color="#555555")
    fig.subplots_adjust(left=0.06, right=0.97, top=0.79, bottom=0.16)

    # Panel a: local work-zone map.
    f_d = [float(r["state_F_mid_N"]) for r in jf_rows]
    d_d = [float(r["state_d_mid_mm"]) for r in jf_rows]
    f_f = [float(r["target_F_N"]) for r in jd_rows]
    d_f = [float(r["state_d_mid_mm"]) for r in jd_rows]
    ax0.plot(d_d, f_d, color=BLACK, lw=1.6, marker="o", ms=4.5, label="same-d path: (d target, F mid)")
    ax0.plot(d_f, f_f, color=BLUE, lw=1.4, marker="s", ms=4.3, label="same-F path: (d mid, F target)")
    ax0.set_title("a  local j_F and j_d evidence curves", loc="left", fontsize=10)
    ax0.set_xlabel("d (mm)")
    ax0.set_ylabel("F (N)")
    ax0.grid(True, color=LIGHT_GRAY, lw=0.6)
    ax0.legend(loc="upper left", fontsize=7)

    # Panel b: angle heatmap.
    im1 = ax1.imshow(angle_grid, aspect="auto", cmap="Reds", vmin=0, vmax=90)
    ax1.set_xticks(range(len(f_vals)), [f"{v:.2g}" for v in f_vals], rotation=0)
    ax1.set_yticks(range(len(d_vals)), [f"{v:.1f}" for v in d_vals])
    ax1.set_xlabel("same-F target F (N)")
    ax1.set_ylabel("same-d target d (mm)")
    ax1.set_title("b  direction angle: angle(j_F, j_d)", loc="left", fontsize=10)
    for i in range(len(d_vals)):
        for j in range(len(f_vals)):
            color = "white" if angle_grid[i, j] > 55 else BLACK
            ax1.text(j, i, f"{angle_grid[i, j]:.0f}", ha="center", va="center", fontsize=7, color=color)
    ax1.scatter([f_vals.index(float(best_score["same_F_target_F_N"]))], [d_vals.index(float(best_score["same_d_target_d_mm"]))], s=100, facecolors="none", edgecolors=BLUE, linewidths=1.8)
    ax1.scatter([f_vals.index(top_f)], [d_vals.index(top_d)], s=120, facecolors="none", edgecolors=RED, linewidths=2.0)
    cb1 = fig.colorbar(im1, ax=ax1, fraction=0.046, pad=0.02)
    cb1.set_label("deg")

    # Panel c: score heatmap.
    im2 = ax2.imshow(score_grid, aspect="auto", cmap="Blues", vmin=0, vmax=max(0.001, float(score_grid.max())))
    ax2.set_xticks(range(len(f_vals)), [f"{v:.2g}" for v in f_vals], rotation=0)
    ax2.set_yticks(range(len(d_vals)), [f"{v:.1f}" for v in d_vals])
    ax2.set_xlabel("same-F target F (N)")
    ax2.set_ylabel("same-d target d (mm)")
    ax2.set_title("c  combined identifiability score", loc="left", fontsize=10)
    for i in range(len(d_vals)):
        for j in range(len(f_vals)):
            color = "white" if score_grid[i, j] > 0.55 * score_grid.max() else BLACK
            ax2.text(j, i, f"{score_grid[i, j]:.2f}", ha="center", va="center", fontsize=7, color=color)
    ax2.scatter([f_vals.index(float(best_score["same_F_target_F_N"]))], [d_vals.index(float(best_score["same_d_target_d_mm"]))], s=100, facecolors="none", edgecolors=BLUE, linewidths=1.8)
    ax2.scatter([f_vals.index(top_f)], [d_vals.index(top_d)], s=120, facecolors="none", edgecolors=RED, linewidths=2.0)
    cb2 = fig.colorbar(im2, ax=ax2, fraction=0.046, pad=0.02)
    cb2.set_label("score")

    fig.savefig(OUT_FIGURE, dpi=300, bbox_inches="tight")
    plt.close(fig)


def write_markdown_report(
    jf_rows: list[dict[str, object]],
    jd_rows: list[dict[str, object]],
    pairs: list[dict[str, object]],
) -> None:
    best_score = pairs[0]
    top = select_primary_pair(pairs)
    candidates = [r for r in pairs if r["verdict"] == "candidate"]
    lines = [
        "# APMD Stage 4 Local Identifiability Analysis",
        "",
        "## Inputs",
        "",
        f"- Same-d/different-F formal table: `{rel(EXP31_REPLICATES)}`",
        f"- Same-F/different-d formal table: `{rel(EXP32_REPLICATES)}`",
        f"- Conservative magnetic noise floor used for ratio reporting: `{NOISE_FLOOR_UT:.1f} uT`.",
        "",
        "## Method",
        "",
        "- `j_F` is estimated from near-matched-displacement / different-force path pairs as `Delta B / |Delta F|`.",
        "- `j_d` is estimated from near-matched-force / different-displacement path pairs as `Delta B / |Delta d|`.",
        "- Because loading/return ordering can flip the sign convention, the identifiability angle uses the absolute cosine between the two vectors.",
        "- The scaled condition number is computed after normalizing the two columns, so it reflects directional collinearity rather than unit choice.",
        "- Candidate ranking combines angle, scaled condition number, magnetic signal-to-noise ratio, repeat directional consistency, and local proximity in `(d,F)` space.",
        "- The selected zone is a local mechanism-validation candidate in the current bench-top setup, not a full prosthetic-socket application range.",
        "",
        "## Primary Result",
        "",
        f"- Strict-gate primary sensitivity-pair candidate: same-d target `d = {fmt(top['same_d_target_d_mm'], 2)} mm` paired with same-F target `F = {fmt(top['same_F_target_F_N'], 2)} N`.",
        f"- Pair-column angle: `{fmt(top['angle_deg'], 1)} deg`.",
        f"- Scaled condition number: `{fmt(top['condition_scaled'], 2)}`.",
        f"- Minimum magnetic noise ratio: `{fmt(top['min_noise_ratio'], 1)}`.",
        f"- Locality distance: `{fmt(top['locality_distance'], 2)}`.",
        f"- Verdict: `{top['verdict']}`.",
        f"- Best-score practical candidate: `d = {fmt(best_score['same_d_target_d_mm'], 2)} mm`, `F = {fmt(best_score['same_F_target_F_N'], 2)} N`, angle `{fmt(best_score['angle_deg'], 1)} deg`, score `{fmt(best_score['identifiability_score'], 3)}`.",
        "",
        "## Interpretation",
        "",
    ]
    if candidates:
        lines.append(
            "At least one local pair passes the Stage 4 directional gate. The strict-gate candidate should be treated as the primary local mechanism-validation candidate, while the best-score practical candidate is useful if locality is prioritized. This does not claim full-range prosthetic-socket deployment."
        )
    else:
        lines.append(
            "No strict candidate passes every Stage 4 gate simultaneously. The top rows still provide ranked local work-zone guidance, but Stage 5 should either use the top-ranked zone with caution or add local densification before model-data acquisition."
        )
    lines.extend(
        [
            "",
            "## Top Candidates",
            "",
            "| Rank | same-d d (mm) | same-F F (N) | angle (deg) | cond scaled | min B/noise | locality | score | verdict |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for r in pairs[:10]:
        lines.append(
            f"| {int(r['rank'])} | {fmt(r['same_d_target_d_mm'], 2)} | {fmt(r['same_F_target_F_N'], 2)} | "
            f"{fmt(r['angle_deg'], 1)} | {fmt(r['condition_scaled'], 2)} | {fmt(r['min_noise_ratio'], 1)} | "
            f"{fmt(r['locality_distance'], 2)} | {fmt(r['identifiability_score'], 3)} | {r['verdict']} |"
        )
    lines.extend(
        [
            "",
            "## Output Files",
            "",
            f"- Main figure: `{rel(OUT_FIGURE)}`",
            f"- Candidate pair table: `{rel(OUT_PAIR_TABLE)}`",
            f"- `j_F` table: `{rel(OUT_JF_TABLE)}`",
            f"- `j_d` table: `{rel(OUT_JD_TABLE)}`",
            f"- Summary: `{rel(OUT_SUMMARY)}`",
        ]
    )
    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    exp31 = read_csv(EXP31_REPLICATES)
    exp32 = read_csv(EXP32_REPLICATES)
    jf_rows = summarize_same_d(exp31)
    jd_rows = summarize_same_f(exp32)
    pairs = make_pair_grid(jf_rows, jd_rows)

    jf_fields = [
        "target_d_mm",
        "state_d_mid_mm",
        "state_F_mid_N",
        "n",
        "median_abs_delta_F_N",
        "median_delta_Bvec_uT",
        "noise_ratio",
        "median_delta_Bx_uT",
        "median_delta_By_uT",
        "median_delta_Bz_uT",
        "jF_x_uT_per_N",
        "jF_y_uT_per_N",
        "jF_z_uT_per_N",
        "jF_norm_uT_per_N",
        "directional_consistency",
        "same_d_pass_rate",
        "force_split_pass_rate",
        "b_signal_pass_rate",
    ]
    jd_fields = [
        "target_F_N",
        "state_d_mid_mm",
        "state_F_mid_N",
        "n",
        "median_abs_delta_d_mm",
        "median_delta_Bvec_uT",
        "noise_ratio",
        "median_delta_Bx_uT",
        "median_delta_By_uT",
        "median_delta_Bz_uT",
        "jd_x_uT_per_mm",
        "jd_y_uT_per_mm",
        "jd_z_uT_per_mm",
        "jd_norm_uT_per_mm",
        "directional_consistency",
        "same_F_pass_rate",
        "displacement_split_pass_rate",
        "b_signal_pass_rate",
    ]
    pair_fields = [
        "rank",
        "same_d_target_d_mm",
        "same_d_state_F_mid_N",
        "same_F_target_F_N",
        "same_F_state_d_mid_mm",
        "d_distance_mm",
        "F_distance_N",
        "jF_x_uT_per_N",
        "jF_y_uT_per_N",
        "jF_z_uT_per_N",
        "jF_norm_uT_per_N",
        "jd_x_uT_per_mm",
        "jd_y_uT_per_mm",
        "jd_z_uT_per_mm",
        "jd_norm_uT_per_mm",
        "angle_deg",
        "abs_cosine",
        "condition_scaled",
        "condition_raw",
        "same_d_noise_ratio",
        "same_F_noise_ratio",
        "min_noise_ratio",
        "directional_consistency_mean",
        "locality_distance",
        "locality_score",
        "identifiability_score",
        "verdict",
    ]
    write_csv(OUT_JF_TABLE, jf_rows, jf_fields)
    write_csv(OUT_JD_TABLE, jd_rows, jd_fields)
    write_csv(OUT_PAIR_TABLE, pairs, pair_fields)
    best_score = pairs[0]
    top = select_primary_pair(pairs)
    write_csv(
        OUT_SUMMARY,
        [
            {
                "primary_same_d_target_d_mm": top["same_d_target_d_mm"],
                "primary_same_F_target_F_N": top["same_F_target_F_N"],
                "angle_deg": top["angle_deg"],
                "condition_scaled": top["condition_scaled"],
                "condition_raw": top["condition_raw"],
                "min_noise_ratio": top["min_noise_ratio"],
                "locality_distance": top["locality_distance"],
                "identifiability_score": top["identifiability_score"],
                "verdict": top["verdict"],
                "best_score_same_d_target_d_mm": best_score["same_d_target_d_mm"],
                "best_score_same_F_target_F_N": best_score["same_F_target_F_N"],
                "best_score_angle_deg": best_score["angle_deg"],
                "best_score_value": best_score["identifiability_score"],
                "strict_candidate_count": sum(1 for r in pairs if r["verdict"] == "candidate"),
            }
        ],
        [
            "primary_same_d_target_d_mm",
            "primary_same_F_target_F_N",
            "angle_deg",
            "condition_scaled",
            "condition_raw",
            "min_noise_ratio",
            "locality_distance",
            "identifiability_score",
            "verdict",
            "best_score_same_d_target_d_mm",
            "best_score_same_F_target_F_N",
            "best_score_angle_deg",
            "best_score_value",
            "strict_candidate_count",
        ],
    )
    plot_results(jf_rows, jd_rows, pairs)
    write_markdown_report(jf_rows, jd_rows, pairs)

    print("APMD Stage 4 local identifiability analysis complete.")
    print(f"  strict primary same-d d = {float(top['same_d_target_d_mm']):.2f} mm")
    print(f"  strict primary same-F F = {float(top['same_F_target_F_N']):.2f} N")
    print(f"  angle            = {float(top['angle_deg']):.1f} deg")
    print(f"  cond scaled      = {float(top['condition_scaled']):.2f}")
    print(f"  min B/noise      = {float(top['min_noise_ratio']):.1f}")
    print(f"  verdict          = {top['verdict']}")
    print(f"  best-score pair  = d {float(best_score['same_d_target_d_mm']):.2f} mm / F {float(best_score['same_F_target_F_N']):.2f} N")
    print(f"  best-score angle = {float(best_score['angle_deg']):.1f} deg")
    print(f"  figure           = {OUT_FIGURE}")
    print(f"  report           = {OUT_REPORT}")


if __name__ == "__main__":
    main()
