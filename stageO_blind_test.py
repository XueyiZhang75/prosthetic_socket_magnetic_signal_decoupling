"""Stage O -- automatic blind-test acquisition.

Purpose:
  Collect held-out state points for the final Bxyz -> [F, d] blind test.
  I+/J+ data are used for calibration; this script creates a new session that
  should only be used for final model evaluation.

Protocol:
  1. Open MLX first, then Mark-10, then the UNO force reader.
  2. Live-tare force and capture a no-contact B0.
  3. For each non-monotonic force target:
       - reset path and find contact
       - acquire target F on direct loading, record a blind state
       - preload deeper to change path/internal state, without writing blind rows
       - reacquire the matched loading F on unloading, record a blind state
  4. Save one O_blind_states_rep*.csv file and one state summary file.

The preload is a path-conditioning step only. It is deliberately not written to
the O_blind CSV, because the blind analysis should score planned target states
rather than auxiliary high-force preload points.
"""

from __future__ import annotations

import csv
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import serial

import stageJ_plus_same_f_diff_d as jplus
from force_serial import ForceReader, find_force_port
from mark10_control import Mark10, Mark10Error
from mlx_serial import find_mlx_port
from stageI_hold_disp import (
    MlxNoDataError,
    bmag,
    find_contact,
    quick_mlx_sample,
    read_force_one,
    read_mlx_one,
    require_mlx_sample,
    soft_reboot_mlx,
)


# ============================================================================
# CONFIG
# ============================================================================

# --- Mark-10 ---
MARK10_PORT = "COM5"
MARK10_BAUD = 9600
MARK10_SPEED_MM_PER_MIN = 200.0

# --- MLX90393 ---
MLX_PORT = None
MLX_BAUD = 115200
MLX_STARTUP_WAIT_S = 2.0
MLX_SOFT_REBOOT_ON_OPEN = False

# --- Blind state plan ---
# O-mini v2 held-out pilot: force targets are interpolation points between the
# stamp-head J+ calibration targets (1.70, 1.80, 1.90 N), not training points.
N_TRIALS = 1
BLIND_FORCE_TARGETS = [
    (175, 1.75),
    (185, 1.85),
]

TARGET_RECORD_S = 20.0
PRE_RECORD_SETTLE_S = 3.0
STREAM_DISCARD_S = 1.0
SUMMARY_WINDOW_S = 5.0
ROW_PRINT_EVERY_S = 5.0

# --- Tare ---
LIVE_TARE_S = 2.0
TARE_PRE_SETTLE_S = 3.0

# --- Recovery ---
INTER_TARGET_SETTLE_S = 5.0
INTER_TARGET_REST_S = 20.0
INTER_TRIAL_REST_S = 60.0

# --- Metadata ---
SAMPLE_ID = ""
MAGNET_ID = ""

# --- Output ---
HERE = Path(__file__).parent
OUTPUT_ROOT = HERE / "decouple_data"


@dataclass(frozen=True)
class BlindStateSpec:
    state_index: int
    pair_id: int
    target_label_int: int
    nominal_F_N: float
    state_label: str
    path_mode: str


def blind_csv_name(trial: int) -> str:
    return f"O_blind_states_rep{trial}.csv"


def make_blind_state_specs(
    force_targets: list[tuple[int, float]] | tuple[tuple[int, float], ...]
) -> list[BlindStateSpec]:
    specs: list[BlindStateSpec] = []
    state_index = 1
    for pair_id, (target_label_int, target_F_N) in enumerate(force_targets, start=1):
        specs.append(
            BlindStateSpec(
                state_index=state_index,
                pair_id=pair_id,
                target_label_int=target_label_int,
                nominal_F_N=target_F_N,
                state_label=f"blind_{state_index:02d}_loading",
                path_mode="direct_loading",
            )
        )
        state_index += 1
        specs.append(
            BlindStateSpec(
                state_index=state_index,
                pair_id=pair_id,
                target_label_int=target_label_int,
                nominal_F_N=target_F_N,
                state_label=f"blind_{state_index:02d}_unloading",
                path_mode="return_unloading",
            )
        )
        state_index += 1
    return specs


def has_planned_preload_split(loading_d_mm: float) -> bool:
    preload_d = jplus.compute_preload_depth(loading_d_mm)
    return jplus.is_usable_preload_stop(loading_d_mm, preload_d)


def blind_fieldnames() -> list[str]:
    return [
        "time_s", "session_id", "trial", "repeat_id", "pair_id",
        "state_index", "stage", "state_label", "phase", "control_mode",
        "path_mode", "target_label", "target", "actual",
        "nominal_F_target_N", "F_target_N", "F_N", "F_error_N",
        "d_preload_mm", "d_actual_mm", "d_mm", "q_mm", "mark10_pos_mm",
        "t_rel_s", "Bx_uT", "By_uT", "Bz_uT",
        "mean_Bx_uT", "mean_By_uT", "mean_Bz_uT",
        "delta_Bx_uT", "delta_By_uT", "delta_Bz_uT", "Bmag_uT",
        "sample_id", "magnet_id", "note",
    ]


def summary_fieldnames() -> list[str]:
    return [
        "session_id", "trial", "state_index", "pair_id", "state_label",
        "path_mode", "target_label", "nominal_F_target_N", "F_target_N",
        "F_N", "F_error_N", "d_mm", "mark10_pos_mm", "Bmag_uT",
        "delta_Bx_uT", "delta_By_uT", "delta_Bz_uT", "n",
        "acquire_status", "preload_status", "note",
    ]


def median_or_nan(values):
    clean = [v for v in values if v == v]
    return statistics.median(clean) if clean else float("nan")


def summarize_samples(samples, window_s=SUMMARY_WINDOW_S):
    if not samples:
        nan = float("nan")
        return {
            "n": 0,
            "d_mm": nan,
            "F_N": nan,
            "Bmag_uT": nan,
            "Bx_uT": nan,
            "By_uT": nan,
            "Bz_uT": nan,
            "delta_Bx_uT": nan,
            "delta_By_uT": nan,
            "delta_Bz_uT": nan,
            "mark10_pos_mm": nan,
        }

    t_min = min(s["t_rel_s"] for s in samples)
    window = [s for s in samples if s["t_rel_s"] <= t_min + window_s]
    if not window:
        window = samples

    return {
        "n": len(window),
        "d_mm": median_or_nan([s["d_actual_mm"] for s in window]),
        "F_N": median_or_nan([s["F_N"] for s in window]),
        "Bmag_uT": median_or_nan([s["Bmag_uT"] for s in window]),
        "Bx_uT": median_or_nan([s["Bx_uT"] for s in window]),
        "By_uT": median_or_nan([s["By_uT"] for s in window]),
        "Bz_uT": median_or_nan([s["Bz_uT"] for s in window]),
        "delta_Bx_uT": median_or_nan([s["delta_Bx_uT"] for s in window]),
        "delta_By_uT": median_or_nan([s["delta_By_uT"] for s in window]),
        "delta_Bz_uT": median_or_nan([s["delta_Bz_uT"] for s in window]),
        "mark10_pos_mm": median_or_nan([
            s.get("mark10_pos_mm", float("nan")) for s in window
        ]),
    }


def flush_streams(force, mlx_ser):
    force.ser.reset_input_buffer()
    mlx_ser.reset_input_buffer()
    if STREAM_DISCARD_S > 0:
        force.drain(STREAM_DISCARD_S)
        quick_mlx_sample(mlx_ser, STREAM_DISCARD_S)
        force.ser.reset_input_buffer()
        mlx_ser.reset_input_buffer()


def collect_blind_state(
    *,
    mark10,
    force,
    mlx_ser,
    contact_pos,
    B0,
    session_id,
    trial,
    spec: BlindStateSpec,
    target_F_N,
    d_preload_mm,
    record_s,
    csv_writer,
    log,
    note="",
):
    print(
        f"\n  {spec.state_label}: record {record_s:.0f} s "
        f"({spec.path_mode}, target F={target_F_N:.3f} N)"
    )
    time.sleep(PRE_RECORD_SETTLE_S)
    flush_streams(force, mlx_ser)

    pos = mark10.position_stable()
    d_actual = contact_pos - pos
    print(f"    d_actual={d_actual:.3f} mm")
    log.write(
        f"[trial {trial} state {spec.state_index}] start "
        f"targetF={target_F_N:.4f} d_actual={d_actual:.4f} pos={pos:.4f}\n"
    )
    log.flush()

    t0 = time.perf_counter()
    next_print = 0.0
    samples = []

    while True:
        t_rel = time.perf_counter() - t0
        if t_rel >= record_s:
            break

        F_N = read_force_one(force, timeout_s=1.0)
        B = read_mlx_one(mlx_ser, timeout_s=1.0)
        if F_N is None or B is None:
            continue

        bx, by, bz = B
        Bm = bmag(bx, by, bz)
        dbx, dby, dbz = bx - B0[0], by - B0[1], bz - B0[2]
        row = {
            "time_s": f"{time.time():.6f}",
            "session_id": session_id,
            "trial": trial,
            "repeat_id": trial,
            "pair_id": spec.pair_id,
            "state_index": spec.state_index,
            "stage": "O_blind",
            "state_label": spec.state_label,
            "phase": "holding",
            "control_mode": "blind_force_path_state",
            "path_mode": spec.path_mode,
            "target_label": str(spec.target_label_int),
            "target": f"{target_F_N:.5f}",
            "actual": f"{F_N:.5f}",
            "nominal_F_target_N": f"{spec.nominal_F_N:.5f}",
            "F_target_N": f"{target_F_N:.5f}",
            "F_N": f"{F_N:.6f}",
            "F_error_N": f"{F_N - target_F_N:+.6f}",
            "d_preload_mm": f"{d_preload_mm:.4f}",
            "d_actual_mm": f"{d_actual:.4f}",
            "d_mm": f"{d_actual:.4f}",
            "q_mm": "",
            "mark10_pos_mm": f"{pos:.4f}",
            "t_rel_s": f"{t_rel:.4f}",
            "Bx_uT": f"{bx:.4f}",
            "By_uT": f"{by:.4f}",
            "Bz_uT": f"{bz:.4f}",
            "mean_Bx_uT": f"{bx:.4f}",
            "mean_By_uT": f"{by:.4f}",
            "mean_Bz_uT": f"{bz:.4f}",
            "delta_Bx_uT": f"{dbx:.4f}",
            "delta_By_uT": f"{dby:.4f}",
            "delta_Bz_uT": f"{dbz:.4f}",
            "Bmag_uT": f"{Bm:.4f}",
            "sample_id": SAMPLE_ID,
            "magnet_id": MAGNET_ID,
            "note": note,
        }
        csv_writer.writerow(row)
        samples.append(
            {
                "t_rel_s": t_rel,
                "d_actual_mm": d_actual,
                "F_N": F_N,
                "Bmag_uT": Bm,
                "Bx_uT": bx,
                "By_uT": by,
                "Bz_uT": bz,
                "delta_Bx_uT": dbx,
                "delta_By_uT": dby,
                "delta_Bz_uT": dbz,
                "mark10_pos_mm": pos,
            }
        )

        if t_rel >= next_print:
            print(
                f"      t={t_rel:5.1f} s  F={F_N*1000:+8.1f} mN  "
                f"d={d_actual:.3f} mm  |B|={Bm:8.1f} uT"
            )
            next_print += ROW_PRINT_EVERY_S

    summary = summarize_samples(samples)
    print(
        f"    summary(head {SUMMARY_WINDOW_S:.0f}s): "
        f"F={summary['F_N']*1000:+.1f} mN, "
        f"d={summary['d_mm']:.3f} mm, |B|={summary['Bmag_uT']:.1f} uT, "
        f"n={summary['n']}"
    )
    log.write(
        f"[trial {trial} state {spec.state_index}] summary "
        f"F={summary['F_N']:.6f} d={summary['d_mm']:.4f} "
        f"Bmag={summary['Bmag_uT']:.4f} n={summary['n']}\n"
    )
    log.flush()
    return summary


def write_summary_row(
    writer,
    *,
    session_id,
    trial,
    spec: BlindStateSpec,
    target_F_N,
    summary,
    acquire_status,
    preload_status,
    note="",
):
    writer.writerow(
        {
            "session_id": session_id,
            "trial": trial,
            "state_index": spec.state_index,
            "pair_id": spec.pair_id,
            "state_label": spec.state_label,
            "path_mode": spec.path_mode,
            "target_label": spec.target_label_int,
            "nominal_F_target_N": f"{spec.nominal_F_N:.5f}",
            "F_target_N": f"{target_F_N:.5f}",
            "F_N": f"{summary['F_N']:.6f}",
            "F_error_N": f"{summary['F_N'] - target_F_N:+.6f}",
            "d_mm": f"{summary['d_mm']:.4f}",
            "mark10_pos_mm": f"{summary['mark10_pos_mm']:.4f}",
            "Bmag_uT": f"{summary['Bmag_uT']:.4f}",
            "delta_Bx_uT": f"{summary['delta_Bx_uT']:.4f}",
            "delta_By_uT": f"{summary['delta_By_uT']:.4f}",
            "delta_Bz_uT": f"{summary['delta_Bz_uT']:.4f}",
            "n": summary["n"],
            "acquire_status": acquire_status,
            "preload_status": preload_status,
            "note": note,
        }
    )


def main():
    OUTPUT_ROOT.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"session_{ts}"
    session_dir = OUTPUT_ROOT / session_id
    session_dir.mkdir(parents=True)
    log_path = session_dir / "run_log.txt"
    summary_path = session_dir / "O_blind_state_summary.csv"

    specs = make_blind_state_specs(BLIND_FORCE_TARGETS)
    est_total_min = (
        N_TRIALS
        * len(BLIND_FORCE_TARGETS)
        * (2 * TARGET_RECORD_S + 2 * PRE_RECORD_SETTLE_S + 120)
        / 60
    )

    print("\n" + "=" * 64)
    print("  Stage O-mini -- local blind-test pilot acquisition")
    print("=" * 64)
    print(f"  session        : {session_id}")
    print(f"  trials         : {N_TRIALS}")
    print(f"  force targets  : {BLIND_FORCE_TARGETS}")
    print(f"  blind states   : {len(specs)} per trial")
    print(
        f"  preload rule   : loading d + {jplus.D_PRELOAD_EXTRA_MM:.2f} mm, "
        f"cap {jplus.D_PRELOAD_MAX_MM:.2f} mm"
    )
    print(f"  D_SOFT_LIMIT   : {jplus.D_SOFT_LIMIT_MM:.2f} mm")
    hard_limit_text = (
        "OFF" if jplus.F_HARD_LIMIT_N is None else f"{jplus.F_HARD_LIMIT_N:.2f} N"
    )
    print(f"  F_HARD_LIMIT   : {hard_limit_text}")
    print(f"  state record   : {TARGET_RECORD_S:.0f} s")
    print(f"  est total      : ~{est_total_min:.1f} min")
    print()
    print("Pre-flight:")
    print("  [ ] This is a NEW held-out O-mini blind pilot, not calibration")
    print("  [ ] Same sample / magnet / MLX geometry as I+ and J+")
    print("  [ ] Mark-10 start position about 7 mm above lower limit")
    print("  [ ] Clear visible gap above the sample at the start position")
    print("  [ ] EasyMESUR Home -> PC Control ACTIVE")
    print("  [ ] Arduino IDE Serial Monitor on UNO CLOSED")
    print("  [ ] QT Py / MLX running circuitpython/code.py")
    print()
    try:
        input("Press Enter to start (Ctrl+C aborts) ... ")
    except KeyboardInterrupt:
        return

    print("\nOpening MLX90393 first ...")
    try:
        mlx_port = MLX_PORT or find_mlx_port()
        mlx_ser = serial.Serial(mlx_port, MLX_BAUD, timeout=0.5)
        if MLX_SOFT_REBOOT_ON_OPEN:
            print("  soft-rebooting QT Py stream ...")
            soft_reboot_mlx(mlx_ser)
        time.sleep(MLX_STARTUP_WAIT_S)
        _, _, n_warmup = require_mlx_sample(
            mlx_ser, 1.0, "MLX warmup before opening motion hardware"
        )
        print(f"  MLX90393 stream on {mlx_port}  (warmup n={n_warmup})\n")
    except Exception as exc:
        sys.exit(f"\nMLX90393 required for Stage O. {exc}")

    print("Opening Mark-10 ...")
    try:
        mark10 = Mark10(
            MARK10_PORT, MARK10_BAUD,
            speed_mm_per_min=MARK10_SPEED_MM_PER_MIN,
        )
    except Mark10Error as exc:
        mlx_ser.close()
        sys.exit(f"\n{exc}")
    print("  Mark-10 ready")

    print("Opening UNO_force ...")
    try:
        force = ForceReader(find_force_port())
        force.live_tare(duration_s=LIVE_TARE_S, pre_settle_s=TARE_PRE_SETTLE_S)
    except Exception as exc:
        mlx_ser.close()
        mark10.close()
        sys.exit(f"\nForce sensor required for Stage O. {exc}")

    print("Capturing B0 (no-contact baseline) ...")
    try:
        (b0x, b0y, b0z), _, n_b0 = require_mlx_sample(
            mlx_ser, 1.5, "B0 capture"
        )
    except MlxNoDataError as exc:
        mlx_ser.close()
        force.close()
        mark10.close()
        sys.exit(f"\n{exc}")
    B0 = (b0x, b0y, b0z)
    print(f"  B0 = ({b0x:+.2f}, {b0y:+.2f}, {b0z:+.2f}) uT  (n={n_b0})")

    trial_start_pos = mark10.position_stable()
    print(f"  trial_start_pos = {trial_start_pos:+.3f} mm")

    log = log_path.open("w", encoding="utf-8")
    log.write(f"# Stage O blind session {ts}\n")
    log.write(f"# BLIND_FORCE_TARGETS={BLIND_FORCE_TARGETS}\n")
    log.write(
        f"# D_PRELOAD_EXTRA_MM={jplus.D_PRELOAD_EXTRA_MM}, "
        f"D_PRELOAD_MAX_MM={jplus.D_PRELOAD_MAX_MM}, "
        f"D_SOFT_LIMIT_MM={jplus.D_SOFT_LIMIT_MM}\n"
    )
    log.write(f"# live_tare_N={force.live_tare_N:.5f}\n")
    log.write(f"# B0={B0}\n")
    log.write(f"# trial_start_pos={trial_start_pos:.4f}\n")
    log.flush()

    summary_file = summary_path.open("w", newline="", encoding="utf-8")
    summary_writer = csv.DictWriter(summary_file, fieldnames=summary_fieldnames())
    summary_writer.writeheader()

    try:
        for trial in range(1, N_TRIALS + 1):
            print("\n" + "=" * 64)
            print(f"  TRIAL {trial}/{N_TRIALS}")
            print("=" * 64)

            csv_path = session_dir / blind_csv_name(trial)
            with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=blind_fieldnames())
                writer.writeheader()

                for pair_i, (target_label_int, target_F) in enumerate(
                    BLIND_FORCE_TARGETS, start=1
                ):
                    loading_spec = specs[(pair_i - 1) * 2]
                    unloading_spec = specs[(pair_i - 1) * 2 + 1]

                    print("\n" + "-" * 64)
                    print(f"  BLIND TARGET {target_label_int}: reset path")
                    print("-" * 64)

                    print(
                        f"\n  PHASE R: retracting to start "
                        f"({trial_start_pos:+.3f} mm)"
                    )
                    try:
                        back_pos = jplus.reset_to_trial_start_if_needed(
                            mark10, trial_start_pos
                        )
                    except Mark10Error as exc:
                        print(f"  ! retract error before target {target_label_int}: {exc}")
                        break

                    time.sleep(INTER_TARGET_SETTLE_S)
                    contact_pos = find_contact(
                        mark10, force, f"{trial} blind {target_label_int}", log
                    )
                    if contact_pos is None:
                        print(f"  ! contact not found, skipping target {target_label_int}")
                        continue

                    contact_depth = abs(contact_pos - trial_start_pos)
                    planned_depth = contact_depth + jplus.D_PRELOAD_MAX_MM
                    print(
                        f"  contact depth from start = {contact_depth:.2f} mm; "
                        f"max planned travel from start <= {planned_depth:.2f} mm"
                    )

                    print(
                        f"\n  LOADING BLIND TARGET {target_label_int}: "
                        f"F={target_F:.3f} N"
                    )
                    ok, status, pos, d_actual, F_now, n_iter = (
                        jplus.acquire_force_target(
                            mark10,
                            force,
                            contact_pos,
                            target_F,
                            log,
                            trial=trial,
                            pair_label=str(target_label_int),
                            state_label=loading_spec.state_label,
                        )
                    )
                    print(
                        f"    acquire loading: F={F_now:+.3f} N, "
                        f"d={d_actual:.3f} mm, {status}, it={n_iter:02d}"
                    )
                    if not ok:
                        log.write(
                            f"[trial {trial} target {target_label_int}] "
                            f"loading incomplete status={status}\n"
                        )
                        log.flush()
                        continue

                    loading = collect_blind_state(
                        mark10=mark10,
                        force=force,
                        mlx_ser=mlx_ser,
                        contact_pos=contact_pos,
                        B0=B0,
                        session_id=session_id,
                        trial=trial,
                        spec=loading_spec,
                        target_F_N=target_F,
                        d_preload_mm=float("nan"),
                        record_s=TARGET_RECORD_S,
                        csv_writer=writer,
                        log=log,
                    )
                    write_summary_row(
                        summary_writer,
                        session_id=session_id,
                        trial=trial,
                        spec=loading_spec,
                        target_F_N=target_F,
                        summary=loading,
                        acquire_status=status,
                        preload_status="not_started",
                    )
                    summary_file.flush()
                    csv_file.flush()

                    match_target_F = loading["F_N"]
                    preload_d = jplus.compute_preload_depth(loading["d_mm"])
                    if not has_planned_preload_split(loading["d_mm"]):
                        print(
                            "\n  ! loading depth is too close to preload cap; "
                            "skipping unloading blind state for this target"
                        )
                        log.write(
                            f"[trial {trial} target {target_label_int}] "
                            f"loading_d={loading['d_mm']:.4f} leaves no usable "
                            "preload split; unloading skipped\n"
                        )
                        log.flush()
                        continue

                    force_cap = jplus.preload_force_cap(match_target_F)
                    print(
                        f"\n  PRELOAD PATH STEP: move to d={preload_d:.3f} mm "
                        f"(cap F={force_cap:.3f} N, not scored as blind point)"
                    )
                    ok, preload_status, pos, preload_actual_d, preload_F = (
                        jplus.move_to_preload_depth(
                            mark10, force, contact_pos, preload_d, force_cap
                        )
                    )
                    print(
                        f"    preload: F={preload_F:+.3f} N, "
                        f"d={preload_actual_d:.3f} mm, {preload_status}"
                    )
                    if not ok:
                        log.write(
                            f"[trial {trial} target {target_label_int}] "
                            f"preload incomplete status={preload_status}\n"
                        )
                        log.flush()
                        continue
                    if preload_status == "force_cap_stop" and not (
                        jplus.is_usable_preload_stop(
                            loading["d_mm"], preload_actual_d
                        )
                    ):
                        log.write(
                            f"[trial {trial} target {target_label_int}] "
                            "preload force cap too early; unloading skipped\n"
                        )
                        log.flush()
                        continue

                    print(
                        f"\n  UNLOADING BLIND TARGET {target_label_int}: "
                        f"return to matched F={match_target_F:.3f} N"
                    )
                    ok, status, pos, d_actual, F_now, n_iter = (
                        jplus.acquire_force_target(
                            mark10,
                            force,
                            contact_pos,
                            match_target_F,
                            log,
                            trial=trial,
                            pair_label=str(target_label_int),
                            state_label=unloading_spec.state_label,
                        )
                    )
                    print(
                        f"    acquire unloading: F={F_now:+.3f} N, "
                        f"d={d_actual:.3f} mm, {status}, it={n_iter:02d}"
                    )
                    if not ok:
                        log.write(
                            f"[trial {trial} target {target_label_int}] "
                            f"unloading incomplete status={status}\n"
                        )
                        log.flush()
                        continue

                    unloading = collect_blind_state(
                        mark10=mark10,
                        force=force,
                        mlx_ser=mlx_ser,
                        contact_pos=contact_pos,
                        B0=B0,
                        session_id=session_id,
                        trial=trial,
                        spec=unloading_spec,
                        target_F_N=match_target_F,
                        d_preload_mm=preload_actual_d,
                        record_s=TARGET_RECORD_S,
                        csv_writer=writer,
                        log=log,
                        note="target_F_matched_to_loading_head_summary",
                    )
                    write_summary_row(
                        summary_writer,
                        session_id=session_id,
                        trial=trial,
                        spec=unloading_spec,
                        target_F_N=match_target_F,
                        summary=unloading,
                        acquire_status=status,
                        preload_status=preload_status,
                        note="target_F_matched_to_loading_head_summary",
                    )
                    summary_file.flush()
                    csv_file.flush()

                    print(
                        f"\n  PHASE C: retracting to start "
                        f"({trial_start_pos:+.3f} mm)"
                    )
                    try:
                        back_pos = jplus.reset_to_trial_start_if_needed(
                            mark10, trial_start_pos
                        )
                    except Mark10Error as exc:
                        print(f"  ! retract error: {exc}")
                        break

                    time.sleep(INTER_TARGET_REST_S)

            if trial < N_TRIALS:
                print(f"\n  resting {INTER_TRIAL_REST_S:.0f} s for recovery ...")
                time.sleep(INTER_TRIAL_REST_S)

    except KeyboardInterrupt:
        print("\n\nUser abort. Will retract.")
    except Exception as exc:
        print(f"\n\n! unexpected error: {exc}")
        log.write(f"\nERROR: {exc}\n")
        raise
    finally:
        try:
            jplus.reset_to_trial_start_if_needed(mark10, trial_start_pos)
        except Exception:
            pass
        try:
            summary_file.close()
        except Exception:
            pass
        try:
            log.close()
        except Exception:
            pass
        try:
            mlx_ser.close()
        except Exception:
            pass
        try:
            force.close()
        except Exception:
            pass
        try:
            mark10.close()
        except Exception:
            pass

    print(f"\n=== Stage O blind test done. Files in: {session_dir}")
    for p in sorted(session_dir.glob("O_blind*.csv")):
        print(f"  {p.name}")
    print(f"  {summary_path.name}")
    print(f"  {log_path.name}")
    print("\nNext analysis command:")
    print(
        "  python .\\blind_test_analysis.py "
        "--train-session session_20260601_160931 "
        "--train-session session_20260602_103531 "
        f"--blind-session {session_id}"
    )


if __name__ == "__main__":
    main()
