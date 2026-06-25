"""Build Stage 5 model-ready datasets from accepted APMD formal sessions.

This script is intentionally read-only with respect to experiment data. It
collects accepted formal path-pair results from the curated report CSVs and
their source raw rep files, then exports:

- state-level rows: one row per stable state summary, for B -> F,d modeling
- pair-level rows: one row per accepted path pair, for mechanism diagnostics
- a short Markdown summary with counts and missing-file warnings
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "decouple_data"
REPORTS_DIR = ROOT / "reports"

OUT_STATES = REPORTS_DIR / "apmd_stage5_model_dataset_states.csv"
OUT_PAIRS = REPORTS_DIR / "apmd_stage5_model_dataset_pairs.csv"
OUT_SUMMARY = REPORTS_DIR / "APMD_STAGE5_MODEL_DATASET_SUMMARY.md"

SUMMARY_WINDOW_S = 10.0

DENSE_LOOP_SUMMARIES = [
    DATA_DIR / "session_20260615_112044" / "local_minor_loop_dense_5p1B_state_summary.csv",
    DATA_DIR / "session_20260615_143640" / "local_minor_loop_dense_5p1B_state_summary.csv",
    DATA_DIR / "session_20260618_092135" / "local_minor_loop_dense_5p1B_state_summary.csv",
    DATA_DIR / "session_20260618_135532" / "local_minor_loop_dense_5p1B_state_summary.csv",
    DATA_DIR / "session_20260624_113311" / "local_minor_loop_dense_5p1B_S_state_summary.csv",
    DATA_DIR / "session_20260624_122802" / "local_minor_loop_dense_5p1B_S_state_summary.csv",
    DATA_DIR / "session_20260624_135659" / "local_minor_loop_dense_5p1B_S_state_summary.csv",
    DATA_DIR / "session_20260624_145548" / "local_minor_loop_dense_5p1B_S_state_summary.csv",
    DATA_DIR / "session_20260622_112307" / "local_minor_loop_dense_5p1B_L_state_summary.csv",
    DATA_DIR / "session_20260622_132503" / "local_minor_loop_dense_5p1B_L_state_summary.csv",
    DATA_DIR / "session_20260622_143801" / "local_minor_loop_dense_5p1B_L_state_summary.csv",
    DATA_DIR / "session_20260622_151834" / "local_minor_loop_dense_5p1B_L_state_summary.csv",
    DATA_DIR / "session_20260622_162129" / "local_minor_loop_dense_5p1B_L_state_summary.csv",
    DATA_DIR / "session_20260623_152502" / "local_minor_loop_dense_5p1B_H_state_summary.csv",
    DATA_DIR / "session_20260623_162301" / "local_minor_loop_dense_5p1B_H_state_summary.csv",
    DATA_DIR / "session_20260623_172014" / "local_minor_loop_dense_5p1B_H_state_summary.csv",
    DATA_DIR / "session_20260623_182650" / "local_minor_loop_dense_5p1B_H_state_summary.csv",
    DATA_DIR / "session_20260623_200232" / "local_minor_loop_dense_5p1B_H_state_summary.csv",
]

DENSE_LOOP_ACCEPTED_CYCLES = {
    DATA_DIR / "session_20260624_113311" / "local_minor_loop_dense_5p1B_S_state_summary.csv": {1, 2, 3, 4, 5},
    DATA_DIR / "session_20260624_122802" / "local_minor_loop_dense_5p1B_S_state_summary.csv": {1, 2, 3, 4, 5},
    DATA_DIR / "session_20260624_135659" / "local_minor_loop_dense_5p1B_S_state_summary.csv": {1, 2, 3, 4, 5},
    DATA_DIR / "session_20260624_145548" / "local_minor_loop_dense_5p1B_S_state_summary.csv": {1, 2, 3, 4, 5},
    DATA_DIR / "session_20260622_112307" / "local_minor_loop_dense_5p1B_L_state_summary.csv": {1, 2, 3, 4, 5},
    DATA_DIR / "session_20260622_132503" / "local_minor_loop_dense_5p1B_L_state_summary.csv": {1, 2, 3, 4, 5},
    DATA_DIR / "session_20260622_143801" / "local_minor_loop_dense_5p1B_L_state_summary.csv": {1, 2, 3},
    DATA_DIR / "session_20260622_151834" / "local_minor_loop_dense_5p1B_L_state_summary.csv": {1, 2, 3},
    DATA_DIR / "session_20260622_162129" / "local_minor_loop_dense_5p1B_L_state_summary.csv": {1, 2, 3, 4},
    DATA_DIR / "session_20260623_152502" / "local_minor_loop_dense_5p1B_H_state_summary.csv": {1, 2, 3, 4},
    DATA_DIR / "session_20260623_162301" / "local_minor_loop_dense_5p1B_H_state_summary.csv": {1, 2, 3, 4, 5},
    DATA_DIR / "session_20260623_172014" / "local_minor_loop_dense_5p1B_H_state_summary.csv": {1, 2, 3, 4, 5},
    DATA_DIR / "session_20260623_182650" / "local_minor_loop_dense_5p1B_H_state_summary.csv": {1, 2, 3, 4, 5},
    DATA_DIR / "session_20260623_200232" / "local_minor_loop_dense_5p1B_H_state_summary.csv": {1},
}


def _float(value, default=math.nan) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value, default=0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _target_code_from_mm(mm: float) -> str:
    return f"{int(round(mm * 100)):03d}"


def _target_code_from_force(force_n: float) -> str:
    return f"{int(round(force_n * 100)):03d}"


def _first_present(row: pd.Series, names: Iterable[str], default=None):
    for name in names:
        if name in row and pd.notna(row[name]) and row[name] != "":
            return row[name]
    return default


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _safe_relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _accepted(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    if df.empty:
        return df
    mask = pd.Series(True, index=df.index)
    for col in columns:
        if col in df.columns:
            mask &= df[col].astype(str).str.contains("strong", case=False, na=False)
    return df[mask].copy()


def _session_dir(session_id: str) -> Path:
    return DATA_DIR / session_id


def _find_raw_file(session_id: str, trial: int, tokens: list[str]) -> tuple[Path | None, str]:
    session_dir = _session_dir(session_id)
    if not session_dir.exists():
        return None, f"missing session dir: {session_id}"
    candidates = []
    rep_token = f"rep{trial}.csv"
    for path in session_dir.glob("*.csv"):
        name = path.name
        if "summary" in name or "conditioning" in name:
            continue
        if rep_token not in name:
            continue
        if all(token in name for token in tokens):
            candidates.append(path)
    if len(candidates) == 1:
        return candidates[0], ""
    if not candidates:
        return None, f"no raw file for {session_id} rep{trial} tokens={tokens}"
    names = ", ".join(p.name for p in candidates[:4])
    return None, f"ambiguous raw file for {session_id} rep{trial}: {names}"


@dataclass(frozen=True)
class SourceSpec:
    experiment: str
    path_family: str
    pair_csv: Path
    source_kind: str
    raw_tokens: Callable[[pd.Series], list[str]]
    accepted_filter: Callable[[pd.DataFrame], pd.DataFrame]


def _same_d_scan_tokens(row: pd.Series) -> list[str]:
    target = str(_int(_first_present(row, ["target_label"], 0))).zfill(3)
    return ["same_d_different_f_scan", target]


def _same_f_scan_tokens(row: pd.Series) -> list[str]:
    target_f = _float(_first_present(row, ["target_F", "target_F_N"], math.nan))
    return ["same_f_different_d_scan", _target_code_from_force(target_f)]


def _same_d_dosage_tokens(row: pd.Series) -> list[str]:
    target = str(_int(_first_present(row, ["target_label"], 0))).zfill(3)
    pre = _target_code_from_mm(_float(row.get("d_preload_mm")))
    return ["same_d_path_dosage_A", target, f"pre{pre}"]


def _same_d_hold_tokens(row: pd.Series) -> list[str]:
    target = str(_int(_first_present(row, ["target_label"], 0))).zfill(3)
    pre = _target_code_from_mm(_float(row.get("d_preload_mm")))
    hold = f"{_int(row.get('preload_hold_s')):03d}"
    return ["same_d_path_hold_time_B", target, f"pre{pre}", f"hold{hold}"]


def _same_f_dosage_tokens(row: pd.Series) -> list[str]:
    extra = f"{int(round(_float(row.get('preload_extra_mm')) * 100)):03d}"
    target_f = _float(_first_present(row, ["target_F_N"], 3.75))
    return ["same_f_path_dosage_A", f"extra{extra}", _target_code_from_force(target_f)]


def _same_f_hold_tokens(row: pd.Series) -> list[str]:
    hold = f"{_int(row.get('preload_hold_s')):03d}"
    target_f = _float(_first_present(row, ["target_F_N"], 3.75))
    return ["same_f_path_hold_time_B", f"hold{hold}", _target_code_from_force(target_f)]


def _recovery_tokens(row: pd.Series) -> list[str]:
    target = str(_int(_first_present(row, ["target_label"], 0))).zfill(3)
    pre = _target_code_from_mm(_float(row.get("d_preload_mm")))
    rec = f"{_int(row.get('recovery_s')):03d}"
    return ["recovery_time_path_memory_3p5A", target, f"pre{pre}", f"rec{rec}"]


SOURCES = [
    SourceSpec(
        experiment="3.1 same-d/different-F work-zone scan",
        path_family="same_d_different_F",
        pair_csv=REPORTS_DIR / "experiment_3_1_complete_figure_data_replicates.csv",
        source_kind="report_replicates",
        raw_tokens=_same_d_scan_tokens,
        accepted_filter=lambda df: _accepted(df, ["verdict"]),
    ),
    SourceSpec(
        experiment="3.2 same-F/different-d work-zone scan",
        path_family="same_F_different_d",
        pair_csv=REPORTS_DIR / "experiment_3_2_same_f_different_d_figure_data_replicates.csv",
        source_kind="report_replicates",
        raw_tokens=_same_f_scan_tokens,
        accepted_filter=lambda df: df.copy(),
    ),
    SourceSpec(
        experiment="3.3A same-d preload-depth dosage",
        path_family="same_d_different_F",
        pair_csv=DATA_DIR / "session_20260612_155336" / "same_d_path_dosage_A_pair_summary.csv",
        source_kind="session_pair_summary",
        raw_tokens=_same_d_dosage_tokens,
        accepted_filter=lambda df: _accepted(df, ["verdict"]),
    ),
    SourceSpec(
        experiment="3.3B same-d preload-hold-time dosage",
        path_family="same_d_different_F",
        pair_csv=DATA_DIR / "session_20260612_180059" / "same_d_path_hold_time_B_pair_summary.csv",
        source_kind="session_pair_summary",
        raw_tokens=_same_d_hold_tokens,
        accepted_filter=lambda df: _accepted(df, ["verdict"]),
    ),
    SourceSpec(
        experiment="3.4A same-F preload-depth dosage",
        path_family="same_F_different_d",
        pair_csv=REPORTS_DIR / "experiment_3_4A_same_f_path_dosage_replicates.csv",
        source_kind="report_replicates",
        raw_tokens=_same_f_dosage_tokens,
        accepted_filter=lambda df: _accepted(df, ["effective_verdict"]),
    ),
    SourceSpec(
        experiment="3.4B same-F preload-hold-time dosage",
        path_family="same_F_different_d",
        pair_csv=REPORTS_DIR / "experiment_3_4B_same_f_path_hold_time_replicates.csv",
        source_kind="report_replicates",
        raw_tokens=_same_f_hold_tokens,
        accepted_filter=lambda df: _accepted(df, ["effective_verdict"]),
    ),
    SourceSpec(
        experiment="3.5A same-d recovery-time path memory",
        path_family="same_d_different_F",
        pair_csv=REPORTS_DIR / "experiment_3_5A_recovery_time_path_memory_replicates.csv",
        source_kind="report_replicates",
        raw_tokens=_recovery_tokens,
        accepted_filter=lambda df: _accepted(df, ["verdict"]),
    ),
]


def _normalise_pair_row(spec: SourceSpec, row: pd.Series) -> dict:
    session_id = str(_first_present(row, ["session_id", "source_session", "source_session_id"], ""))
    trial = _int(_first_present(row, ["trial", "source_trial", "rep", "formal_rep"], 0))
    pair_id = _int(_first_present(row, ["pair_id", "rep", "formal_rep"], trial))

    target_f = _float(_first_present(row, ["target_F", "target_F_N", "F_target_N"], math.nan))
    target_label = _first_present(row, ["target_label"], "")
    if pd.isna(target_label):
        target_label = ""

    d_target = _float(_first_present(row, ["d_target_mm"], math.nan))
    d_preload = _float(_first_present(row, ["d_preload_mm"], math.nan))
    preload_extra = _float(_first_present(row, ["preload_extra_mm"], math.nan))
    preload_hold = _float(_first_present(row, ["preload_hold_s"], math.nan))
    recovery_s = _float(_first_present(row, ["recovery_s"], math.nan))

    d_direct = _float(_first_present(row, ["d_direct_mm", "d_loading", "d_loading_mm"], math.nan))
    d_return = _float(_first_present(row, ["d_return_mm", "d_unloading", "d_unloading_mm"], math.nan))
    delta_d = _float(_first_present(row, ["delta_d", "delta_d_mm", "d_diff_mm"], math.nan))
    abs_delta_d = abs(delta_d) if not math.isnan(delta_d) else _float(_first_present(row, ["abs_delta_d_mm"], math.nan))

    f_direct = _float(_first_present(row, ["F_direct_N", "F_loading", "F_loading_N"], math.nan))
    f_return = _float(_first_present(row, ["F_return_N", "F_unloading", "F_unloading_N"], math.nan))
    delta_f = _float(_first_present(row, ["delta_F", "delta_F_N"], math.nan))
    abs_delta_f = abs(delta_f) if not math.isnan(delta_f) else _float(_first_present(row, ["abs_delta_F_N"], math.nan))

    return {
        "experiment": spec.experiment,
        "path_family": spec.path_family,
        "source_kind": spec.source_kind,
        "source_pair_csv": str(spec.pair_csv.relative_to(ROOT)),
        "session_id": session_id,
        "trial": trial,
        "pair_id": pair_id,
        "target_label": target_label,
        "target_F_N": target_f,
        "d_target_mm": d_target,
        "d_preload_mm": d_preload,
        "preload_extra_mm": preload_extra,
        "preload_hold_s": preload_hold,
        "recovery_s": recovery_s,
        "d_direct_mm": d_direct,
        "d_return_mm": d_return,
        "delta_d_mm": delta_d,
        "abs_delta_d_mm": abs_delta_d,
        "F_direct_N": f_direct,
        "F_return_N": f_return,
        "delta_F_N": delta_f,
        "abs_delta_F_N": abs_delta_f,
        "delta_Bmag_uT": _float(_first_present(row, ["delta_Bmag", "delta_Bmag_uT"], math.nan)),
        "delta_Bx_uT": _float(_first_present(row, ["delta_Bx", "delta_Bx_uT"], math.nan)),
        "delta_By_uT": _float(_first_present(row, ["delta_By", "delta_By_uT"], math.nan)),
        "delta_Bz_uT": _float(_first_present(row, ["delta_Bz", "delta_Bz_uT"], math.nan)),
        "delta_Bvec_uT": _float(_first_present(row, ["delta_Bvec", "delta_Bvec_uT"], math.nan)),
        "verdict": str(_first_present(row, ["effective_verdict", "verdict", "original_verdict"], "accepted")),
        "same_d_ok": _int(_first_present(row, ["same_d_ok", "same_d_ok_effective"], 1)),
        "same_F_ok": _int(_first_present(row, ["same_F_ok", "same_F_ok_effective"], 1)),
        "force_split_ok": _int(_first_present(row, ["force_split_ok"], 1)),
        "disp_split_ok": _int(_first_present(row, ["disp_split_ok", "disp_split_ok_effective"], 1)),
        "b_signal_ok": _int(_first_present(row, ["b_signal_ok", "b_signal_ok_effective"], 1)),
    }


def _canonical_path_label(state_label: str) -> str:
    label = str(state_label)
    if "preload" in label:
        return "preload_deep"
    if "return" in label or "unloading" in label:
        return "return_unloading"
    if "direct" in label or "loading" in label:
        return "direct_loading"
    return label


def _column(df: pd.DataFrame, *names: str) -> str | None:
    for name in names:
        if name in df.columns:
            return name
    return None


def _summarise_state(raw: pd.DataFrame, pair: dict, raw_file: Path, state_label: str) -> dict | None:
    chunk = raw[raw["state_label"].astype(str) == state_label].copy()
    if chunk.empty:
        return None

    t_col = _column(chunk, "t_rel_s", "time_s")
    if t_col is not None:
        chunk[t_col] = pd.to_numeric(chunk[t_col], errors="coerce")
        max_t = chunk[t_col].max()
        if pd.notna(max_t):
            chunk = chunk[chunk[t_col] >= max_t - SUMMARY_WINDOW_S].copy()

    f_col = _column(chunk, "F_N")
    d_col = _column(chunk, "d_actual_mm", "d_mm")
    bx_col = _column(chunk, "mean_Bx_uT", "Bx_uT")
    by_col = _column(chunk, "mean_By_uT", "By_uT")
    bz_col = _column(chunk, "mean_Bz_uT", "Bz_uT")
    bmag_col = _column(chunk, "Bmag_uT")
    dbx_col = _column(chunk, "delta_Bx_uT")
    dby_col = _column(chunk, "delta_By_uT")
    dbz_col = _column(chunk, "delta_Bz_uT")

    for col in [f_col, d_col, bx_col, by_col, bz_col, bmag_col, dbx_col, dby_col, dbz_col]:
        if col:
            chunk[col] = pd.to_numeric(chunk[col], errors="coerce")

    bx = chunk[bx_col].median() if bx_col else math.nan
    by = chunk[by_col].median() if by_col else math.nan
    bz = chunk[bz_col].median() if bz_col else math.nan
    bmag = chunk[bmag_col].median() if bmag_col else math.sqrt(bx * bx + by * by + bz * bz)

    duration = math.nan
    if t_col is not None and chunk[t_col].notna().any():
        duration = float(chunk[t_col].max() - chunk[t_col].min())

    state = {
        "experiment": pair["experiment"],
        "path_family": pair["path_family"],
        "session_id": pair["session_id"],
        "trial": pair["trial"],
        "pair_id": pair["pair_id"],
        "raw_file": str(raw_file.relative_to(ROOT)),
        "state_label": state_label,
        "path_label": _canonical_path_label(state_label),
        "target_label": pair["target_label"],
        "target_F_N": pair["target_F_N"],
        "d_target_mm": pair["d_target_mm"],
        "d_preload_mm": pair["d_preload_mm"],
        "preload_extra_mm": pair["preload_extra_mm"],
        "preload_hold_s": pair["preload_hold_s"],
        "recovery_s": pair["recovery_s"],
        "F_N": chunk[f_col].median() if f_col else math.nan,
        "d_mm": chunk[d_col].median() if d_col else math.nan,
        "Bx_uT": bx,
        "By_uT": by,
        "Bz_uT": bz,
        "Bmag_uT": bmag,
        "delta_Bx_from_B0_uT": chunk[dbx_col].median() if dbx_col else math.nan,
        "delta_By_from_B0_uT": chunk[dby_col].median() if dby_col else math.nan,
        "delta_Bz_from_B0_uT": chunk[dbz_col].median() if dbz_col else math.nan,
        "summary_window_s": SUMMARY_WINDOW_S,
        "state_n_samples": int(len(chunk)),
        "state_duration_s": duration,
        "pair_delta_F_N": pair["delta_F_N"],
        "pair_delta_d_mm": pair["delta_d_mm"],
        "pair_delta_Bvec_uT": pair["delta_Bvec_uT"],
        "pair_verdict": pair["verdict"],
    }
    return state


def _dense_loop_path_label(branch: str, state_label: str) -> str:
    label = f"{branch} {state_label}".lower()
    if "preload" in label:
        return "preload_deep"
    if "unloading" in label:
        return "return_unloading"
    if "loading" in label:
        return "direct_loading"
    return str(state_label)


def _dense_loop_preload_hold_s(row: pd.Series) -> float:
    branch = str(row.get("branch", "")).lower()
    record_s = _float(row.get("record_s"), math.nan)
    if branch == "preload":
        return record_s
    if branch == "unloading":
        return 30.0
    return 0.0


def _dense_loop_experiment(summary_csv: Path) -> str:
    if "_S_" in summary_csv.name:
        return "5.1B-S shallow work-zone local minor-loop dense sampling"
    if "_L_" in summary_csv.name:
        return "5.1B-L Block L local minor-loop dense sampling"
    if "_H_" in summary_csv.name:
        return "5.1B-H upper work-zone local minor-loop dense sampling"
    return "5.1B local minor-loop dense sampling"


def _dense_loop_state_rows(summary_csv: Path, accepted_cycles: set[int] | None = None) -> list[dict]:
    df = _read_csv(summary_csv)
    if df.empty:
        return []

    rows: list[dict] = []
    source_csv = _safe_relative(summary_csv)
    experiment = _dense_loop_experiment(summary_csv)
    for _, row in df.iterrows():
        cycle = _int(row.get("cycle"))
        if accepted_cycles is not None and cycle not in accepted_cycles:
            continue
        state_index = _int(row.get("state_index"))
        branch = str(row.get("branch", ""))
        state_label = str(row.get("state_label", ""))
        d_target = _float(row.get("d_target_mm"))
        d_preload = _float(row.get("d_preload_mm"))
        preload_extra = d_preload - d_target if not math.isnan(d_preload) and not math.isnan(d_target) else math.nan

        bx = _float(row.get("Bx_median_uT"))
        by = _float(row.get("By_median_uT"))
        bz = _float(row.get("Bz_median_uT"))
        bmag = _float(row.get("Bmag_median_uT"))
        if math.isnan(bmag) and not any(math.isnan(v) for v in [bx, by, bz]):
            bmag = math.sqrt(bx * bx + by * by + bz * bz)

        rows.append(
            {
                "experiment": experiment,
                "path_family": "local_minor_loop_dense",
                "source_kind": "session_state_summary",
                "source_state_csv": source_csv,
                "session_id": str(row.get("session_id", "")),
                "trial": cycle,
                "pair_id": cycle,
                "cycle_index": cycle,
                "state_index": state_index,
                "branch": branch,
                "path_mode": str(row.get("path_mode", "")),
                "phase": str(row.get("phase", "")),
                "raw_file": source_csv,
                "state_label": state_label,
                "path_label": _dense_loop_path_label(branch, state_label),
                "target_label": _target_code_from_mm(d_target) if not math.isnan(d_target) else "",
                "target_F_N": math.nan,
                "d_target_mm": d_target,
                "d_preload_mm": d_preload,
                "preload_extra_mm": preload_extra,
                "preload_hold_s": _dense_loop_preload_hold_s(row),
                "recovery_s": math.nan,
                "F_N": _float(row.get("F_median_N")),
                "d_mm": _float(row.get("d_median_mm")),
                "Bx_uT": bx,
                "By_uT": by,
                "Bz_uT": bz,
                "Bmag_uT": bmag,
                "delta_Bx_from_B0_uT": _float(row.get("delta_Bx_median_uT")),
                "delta_By_from_B0_uT": _float(row.get("delta_By_median_uT")),
                "delta_Bz_from_B0_uT": _float(row.get("delta_Bz_median_uT")),
                "summary_window_s": _float(row.get("summary_window_s")),
                "state_n_samples": _int(row.get("n")),
                "state_duration_s": _float(row.get("summary_window_s")),
                "pair_delta_F_N": math.nan,
                "pair_delta_d_mm": math.nan,
                "pair_delta_Bvec_uT": math.nan,
                "pair_verdict": "accepted",
            }
        )
    return rows


def build_datasets() -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    pair_rows: list[dict] = []
    state_rows: list[dict] = []
    warnings: list[str] = []

    for spec in SOURCES:
        df = _read_csv(spec.pair_csv)
        if df.empty:
            warnings.append(f"missing or empty source: {spec.pair_csv}")
            continue

        accepted = spec.accepted_filter(df)
        for _, row in accepted.iterrows():
            pair = _normalise_pair_row(spec, row)
            tokens = spec.raw_tokens(row)
            raw_file, warning = _find_raw_file(pair["session_id"], pair["trial"], tokens)
            pair["raw_file_found"] = 1 if raw_file else 0
            pair["raw_file"] = str(raw_file.relative_to(ROOT)) if raw_file else ""
            pair["raw_file_warning"] = warning
            pair_rows.append(pair)

            if warning:
                warnings.append(f"{spec.experiment}: {warning}")
                continue

            raw = pd.read_csv(raw_file)
            if "state_label" not in raw.columns:
                warnings.append(f"{raw_file}: missing state_label column")
                continue
            for state_label in raw["state_label"].dropna().astype(str).unique():
                state = _summarise_state(raw, pair, raw_file, state_label)
                if state:
                    state_rows.append(state)

    for summary_csv in DENSE_LOOP_SUMMARIES:
        dense_rows = _dense_loop_state_rows(summary_csv, DENSE_LOOP_ACCEPTED_CYCLES.get(summary_csv))
        if not dense_rows:
            warnings.append(f"missing or empty dense-loop summary: {summary_csv}")
            continue
        state_rows.extend(dense_rows)

    pairs = pd.DataFrame(pair_rows)
    states = pd.DataFrame(state_rows)
    return states, pairs, warnings


def write_summary(states: pd.DataFrame, pairs: pd.DataFrame, warnings: list[str]) -> None:
    lines: list[str] = []
    lines.append("# APMD Stage 5 Model Dataset Summary")
    lines.append("")
    lines.append("This file is generated by `apmd_stage5_build_model_dataset.py`.")
    lines.append("")
    lines.append("## Outputs")
    lines.append("")
    lines.append(f"- State-level dataset: `{OUT_STATES.relative_to(ROOT)}`")
    lines.append(f"- Pair-level dataset: `{OUT_PAIRS.relative_to(ROOT)}`")
    lines.append("")
    lines.append("## Dataset Size")
    lines.append("")
    lines.append(f"- Accepted path pairs: {len(pairs)}")
    lines.append(f"- State summaries: {len(states)}")
    unique_sessions = states["session_id"].nunique() if not states.empty else pairs["session_id"].nunique() if not pairs.empty else 0
    lines.append(f"- Unique sessions: {unique_sessions}")
    lines.append("")

    if not pairs.empty:
        lines.append("## Pair Counts By Experiment")
        lines.append("")
        counts = pairs.groupby(["experiment", "path_family"]).size().reset_index(name="pairs")
        lines.append(counts.to_markdown(index=False))
        lines.append("")

    if not states.empty:
        lines.append("## State Counts")
        lines.append("")
        state_counts = states.groupby(["path_family", "path_label"]).size().reset_index(name="states")
        lines.append(state_counts.to_markdown(index=False))
        lines.append("")

        lines.append("## State Counts By Experiment")
        lines.append("")
        exp_counts = states.groupby(["experiment", "path_family"]).size().reset_index(name="states")
        lines.append(exp_counts.to_markdown(index=False))
        lines.append("")

        lines.append("## Local Candidate Coverage")
        lines.append("")
        same_d_340 = pairs[(pairs["path_family"] == "same_d_different_F") & (pairs["d_target_mm"].round(2) == 3.40)]
        same_f_490 = pairs[(pairs["path_family"] == "same_F_different_d") & (pairs["target_F_N"].round(2) == 4.90)]
        same_d_320 = pairs[(pairs["path_family"] == "same_d_different_F") & (pairs["d_target_mm"].round(2) == 3.20)]
        lines.append(f"- Strict primary same-d candidate `d=3.40 mm`: {len(same_d_340)} accepted pairs")
        lines.append(f"- Strict primary same-F candidate `F=4.90 N`: {len(same_f_490)} accepted pairs")
        lines.append(f"- Practical backup same-d candidate `d=3.20 mm`: {len(same_d_320)} accepted pairs")
        dense = states[states["experiment"] == "5.1B local minor-loop dense sampling"]
        if not dense.empty:
            dense_sessions = dense["session_id"].nunique()
            if {"session_id", "cycle_index"}.issubset(dense.columns):
                dense_cycles = dense[["session_id", "cycle_index"]].drop_duplicates().shape[0]
            else:
                dense_cycles = dense[["session_id", "trial"]].drop_duplicates().shape[0]
            dense_d = sorted(pd.to_numeric(dense["d_target_mm"], errors="coerce").dropna().round(2).unique().tolist())
            lines.append(f"- Dense local minor-loop dataset: {len(dense)} state rows across {dense_sessions} sessions and {dense_cycles} session-cycles")
            lines.append(f"- Dense local d grid: {dense_d}")
        block_s = states[states["experiment"] == "5.1B-S shallow work-zone local minor-loop dense sampling"]
        if not block_s.empty:
            block_s_sessions = block_s["session_id"].nunique()
            block_s_cycles = block_s[["session_id", "cycle_index"]].drop_duplicates().shape[0]
            block_s_d = sorted(pd.to_numeric(block_s["d_target_mm"], errors="coerce").dropna().round(2).unique().tolist())
            lines.append(f"- Shallow work-zone dense local dataset: {len(block_s)} state rows across {block_s_sessions} sessions and {block_s_cycles} accepted session-cycles")
            lines.append(f"- Shallow work-zone dense local d grid: {block_s_d}")
        block_l = states[states["experiment"] == "5.1B-L Block L local minor-loop dense sampling"]
        if not block_l.empty:
            block_l_sessions = block_l["session_id"].nunique()
            block_l_cycles = block_l[["session_id", "cycle_index"]].drop_duplicates().shape[0]
            block_l_d = sorted(pd.to_numeric(block_l["d_target_mm"], errors="coerce").dropna().round(2).unique().tolist())
            lines.append(f"- Block L dense local dataset: {len(block_l)} state rows across {block_l_sessions} sessions and {block_l_cycles} accepted session-cycles")
            lines.append(f"- Block L dense local d grid: {block_l_d}")
        block_h = states[states["experiment"] == "5.1B-H upper work-zone local minor-loop dense sampling"]
        if not block_h.empty:
            block_h_sessions = block_h["session_id"].nunique()
            block_h_cycles = block_h[["session_id", "cycle_index"]].drop_duplicates().shape[0]
            block_h_d = sorted(pd.to_numeric(block_h["d_target_mm"], errors="coerce").dropna().round(2).unique().tolist())
            lines.append(f"- Upper work-zone dense local dataset: {len(block_h)} state rows across {block_h_sessions} sessions and {block_h_cycles} accepted session-cycles")
            lines.append(f"- Upper work-zone dense local nominal d grid: {block_h_d}")
            lines.append("- Upper work-zone deep-end states are retained as boundary/weak-region model inputs rather than excluded a priori.")
        lines.append("")

    lines.append("## Modeling Readiness")
    lines.append("")
    lines.append("- This dataset is ready for a first local, proof-of-mechanism model.")
    lines.append("- It contains both absolute magnetic states (`Bx, By, Bz, |B|`) and path-pair deltas.")
    lines.append("- The next recommended step is to fit baseline models and compare plain magnetic regression against path-aware/path-memory features.")
    lines.append("")

    lines.append("## Warnings")
    lines.append("")
    if warnings:
        for warning in warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- None. All accepted pair rows were matched to raw rep files.")
    lines.append("")

    OUT_SUMMARY.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    states, pairs, warnings = build_datasets()
    states.to_csv(OUT_STATES, index=False)
    pairs.to_csv(OUT_PAIRS, index=False)
    write_summary(states, pairs, warnings)
    print(f"wrote {OUT_STATES.relative_to(ROOT)} ({len(states)} state rows)")
    print(f"wrote {OUT_PAIRS.relative_to(ROOT)} ({len(pairs)} pair rows)")
    print(f"wrote {OUT_SUMMARY.relative_to(ROOT)}")
    if warnings:
        print(f"warnings: {len(warnings)}")


if __name__ == "__main__":
    main()
