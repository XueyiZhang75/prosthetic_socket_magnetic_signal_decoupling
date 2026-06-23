"""N-mini analysis for the stamp-head key-evidence rerun.

This is intentionally narrower than the full Stage N audit. It reads one I+
session and one J+ session, estimates the two pair-derived Jacobian columns,
and reports their angle/condition number for a quick go/no-go decision.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from identifiability_analysis import (
    PairColumnEstimate,
    SAME_D_DIFF_F_SUMMARY_NAMES,
    jacobian_metrics,
    estimate_pair_column,
    pair_column_angle_check,
    read_csv,
)


DEFAULT_REPORT = Path("reports") / "STAMP_HEAD_KEY_RERUN_ANALYSIS.md"


@dataclass(frozen=True)
class KeyRerunResult:
    force_session: str
    displacement_session: str
    force: PairColumnEstimate
    displacement: PairColumnEstimate
    metrics: object
    verdict: str
    messages: tuple[str, ...]


def _session_path(data_root: Path, session_name: str) -> Path:
    path = data_root / session_name
    if not path.exists():
        raise FileNotFoundError(f"Session not found: {path}")
    return path


def _first_existing(path: Path, names: Sequence[str], label: str) -> Path:
    for name in names:
        candidate = path / name
        if candidate.exists():
            return candidate
    joined = " or ".join(names)
    raise FileNotFoundError(f"{label} pair summary not found: {path} ({joined})")


def analyze_pair_sessions(
    data_root: Path,
    iplus_session: str,
    jplus_session: str,
    *,
    min_iplus_pairs: int = 2,
    min_jplus_pairs: int = 3,
    min_angle_deg: float = 30.0,
) -> KeyRerunResult:
    i_session_path = _session_path(data_root, iplus_session)
    i_path = _first_existing(
        i_session_path,
        SAME_D_DIFF_F_SUMMARY_NAMES,
        "same-d/different-F",
    )
    j_path = _session_path(data_root, jplus_session) / "Jplus_pair_summary.csv"
    if not j_path.exists():
        raise FileNotFoundError(f"J+ pair summary not found: {j_path}")

    force = estimate_pair_column(
        read_csv(i_path),
        stage_name=f"same-d/different-F ({iplus_session})",
        denominator_col="delta_F_N",
        required_flags=("same_d_ok", "force_split_ok", "b_signal_ok"),
        output_unit="uT/N",
    )
    displacement = estimate_pair_column(
        read_csv(j_path),
        stage_name=f"J+ ({jplus_session})",
        denominator_col="delta_d_mm",
        required_flags=("same_F_ok", "disp_split_ok", "b_signal_ok"),
        output_unit="uT/mm",
    )
    metrics = jacobian_metrics(force.vector, displacement.vector)
    check = pair_column_angle_check(
        force,
        displacement,
        min_usable_force_pairs=min_iplus_pairs,
        min_usable_displacement_pairs=min_jplus_pairs,
        min_angle_deg=min_angle_deg,
    )
    return KeyRerunResult(
        force_session=iplus_session,
        displacement_session=jplus_session,
        force=force,
        displacement=displacement,
        metrics=metrics,
        verdict=check.verdict.upper(),
        messages=tuple(check.messages),
    )


def _fmt_vec(vector: Sequence[float]) -> str:
    return f"({vector[0]:.1f}, {vector[1]:.1f}, {vector[2]:.1f})"


def render_report(result: KeyRerunResult) -> str:
    lines = [
        "# Stamp-Head Key Rerun N-mini Analysis",
        "",
        "This report uses only the specified I+ and J+ pair-summary sessions.",
        "It is a quick local-identifiability check, not the full Stage N audit.",
        "",
        "## Sessions",
        "",
        f"- I+ force-column session: `{result.force_session}`",
        f"- J+ displacement-column session: `{result.displacement_session}`",
        "",
        "## Pair Columns",
        "",
        "| Source | Usable pairs | Column estimate | Median signal | Median denominator |",
        "|---|---:|---|---:|---:|",
        (
            f"| {result.force.stage_name} | {result.force.n_usable}/"
            f"{result.force.n_total} | {_fmt_vec(result.force.vector)} "
            f"{result.force.output_unit} | {result.force.median_signal_uT:.1f} uT | "
            f"{result.force.median_denominator:.4f} |"
        ),
        (
            f"| {result.displacement.stage_name} | "
            f"{result.displacement.n_usable}/{result.displacement.n_total} | "
            f"{_fmt_vec(result.displacement.vector)} {result.displacement.output_unit} | "
            f"{result.displacement.median_signal_uT:.1f} uT | "
            f"{result.displacement.median_denominator:.4f} |"
        ),
        "",
        "## Local Identifiability",
        "",
        f"- Pair-column angle: {result.metrics.angle_deg:.1f} deg",
        f"- Absolute cosine: {result.metrics.cosine_abs:.3f}",
        f"- Column condition number: {result.metrics.condition_number:.2f}",
        f"- Verdict: `{result.verdict}`",
        "",
        "## Interpretation Notes",
        "",
    ]
    lines.extend(f"- {message}" for message in result.messages)
    lines.append("")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("decouple_data"))
    parser.add_argument("--iplus-session", required=True)
    parser.add_argument("--jplus-session", required=True)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--min-iplus-pairs", type=int, default=2)
    parser.add_argument("--min-jplus-pairs", type=int, default=3)
    parser.add_argument("--min-angle-deg", type=float, default=30.0)
    args = parser.parse_args(argv)

    result = analyze_pair_sessions(
        args.data_root,
        args.iplus_session,
        args.jplus_session,
        min_iplus_pairs=args.min_iplus_pairs,
        min_jplus_pairs=args.min_jplus_pairs,
        min_angle_deg=args.min_angle_deg,
    )
    report = render_report(result)
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
