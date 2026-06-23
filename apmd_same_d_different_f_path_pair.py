"""APMD same-d / different-F active path-pair acquisition.

Purpose:
  Passive fixed-displacement holds showed clear force relaxation but weak
  magnetic response at fixed d. This protocol creates a stronger
  near-matched-displacement / different-force comparison using controlled
  path history:

      direct loading to target d
      preload deeper
      unload back to the same target d

  If the two target-d states have a measurable force split and a measurable
  magnetic split, they provide stronger evidence for the local force column

      j_F = dB / dF | d

  than passive relaxation alone.
"""

import csv
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

import serial

from apmd_session_registry import SessionRecord, register_session
from force_serial import ForceReader, find_force_port
from mark10_control import Mark10, Mark10Error
from mlx_serial import find_mlx_port
from stageI_hold_disp import (
    MlxNoDataError,
    assert_no_contact_live_tare,
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

# --- APMD same-d / different-F active path-pair settings ---
N_TRIALS = 3
D_TARGETS_MM = [2.80]
D_PRELOAD_BY_TARGET_MM = {
    2.80: 3.10,
}
D_PRELOAD_MM = 3.10

TARGET_RECORD_S = 45.0
PRELOAD_RECORD_S = 30.0
PRE_RECORD_SETTLE_S = 5.0
STREAM_DISCARD_S = 1.0
SUMMARY_WINDOW_S = 10.0
ROW_PRINT_EVERY_S = 5.0

# --- Decision thresholds for live diagnostics only ---
D_MATCH_TOL_MM = 0.020
FLOAT_COMPARE_EPS = 1e-9
TARGET_POSITION_TOL_MM = 0.02
MIN_FORCE_SPLIT_N = 0.20
DYNAMIC_B_SIGNAL_UT = 50.0

# --- Safety ---
F_HARD_LIMIT_N = None

# --- Tare ---
LIVE_TARE_S = 2.0
TARE_PRE_SETTLE_S = 3.0

# --- Recovery ---
INTER_STATE_SETTLE_S = 3.0
INTER_TRIAL_REST_S = 120.0

# --- Metadata ---
SAMPLE_ID = ""
MAGNET_ID = ""
HEAD_ID = "stamp_head_v1"
FORCE_CALIBRATION_ID = "force_calibration_20260602_190856"
DISPLACEMENT_ZERO_ID = "stageD_session_20260602_201421"

# --- Output ---
HERE = Path(__file__).parent
OUTPUT_ROOT = HERE / "decouple_data"
FORMAL_DESIGN_PATH = HERE / "APMD_FORMAL_EXPERIMENT_DESIGN.md"

# --- Protocol identity / output naming ---
PROTOCOL_TITLE = (
    "APMD -- near-matched-displacement / different-force active path-pair test"
)
PROTOCOL_SHORT_NAME = "APMD same-d/different-F"
STAGE_LABEL = "same_d_diff_f"
LOG_HEADER = "APMD same-d/different-F active path-pair session"
SUMMARY_FILENAME = "same_d_different_f_pair_summary.csv"
STATE_FILE_PREFIX = "same_d_different_f"
CSV_PRINT_GLOB = "same_d_different_f*.csv"
FIGURE_FILENAME = "same_d_different_f_path_pair.png"
PREFLIGHT_FIRST_LINE = (
    "Same sample / magnet / MLX geometry as the passive fixed-d contrast"
)
NEXT_MESSAGE = "Next: python .\\plot_apmd_same_d_different_f.py"
FORMAL_EXPERIMENT_KEY = "实验 2.2"


def metadata_fieldnames():
    return [
        "sample_id",
        "magnet_id",
        "head_id",
        "force_calibration_id",
        "displacement_zero_id",
    ]


def metadata_values():
    return {
        "sample_id": SAMPLE_ID,
        "magnet_id": MAGNET_ID,
        "head_id": HEAD_ID,
        "force_calibration_id": FORCE_CALIBRATION_ID,
        "displacement_zero_id": DISPLACEMENT_ZERO_ID,
    }


def median_or_nan(values):
    clean = [v for v in values if v == v]
    return statistics.median(clean) if clean else float("nan")


def vector_norm3(x, y, z):
    return (x * x + y * y + z * z) ** 0.5


def target_label(d_mm):
    return f"{int(round(d_mm * 100)):03d}"


def preload_depth_for_target(target_d_mm):
    key = round(float(target_d_mm), 2)
    if key in D_PRELOAD_BY_TARGET_MM:
        return D_PRELOAD_BY_TARGET_MM[key]
    return float(D_PRELOAD_MM)


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
        }

    t_max = max(s["t_rel_s"] for s in samples)
    tail = [s for s in samples if s["t_rel_s"] >= t_max - window_s]
    if not tail:
        tail = samples

    return {
        "n": len(tail),
        "d_mm": median_or_nan([s["d_actual_mm"] for s in tail]),
        "F_N": median_or_nan([s["F_N"] for s in tail]),
        "Bmag_uT": median_or_nan([s["Bmag_uT"] for s in tail]),
        "Bx_uT": median_or_nan([s["mean_Bx_uT"] for s in tail]),
        "By_uT": median_or_nan([s["mean_By_uT"] for s in tail]),
        "Bz_uT": median_or_nan([s["mean_Bz_uT"] for s in tail]),
        "delta_Bx_uT": median_or_nan([s["delta_Bx_uT"] for s in tail]),
        "delta_By_uT": median_or_nan([s["delta_By_uT"] for s in tail]),
        "delta_Bz_uT": median_or_nan([s["delta_Bz_uT"] for s in tail]),
    }


def flush_streams(force, mlx_ser):
    force.ser.reset_input_buffer()
    mlx_ser.reset_input_buffer()
    if STREAM_DISCARD_S > 0:
        force.drain(STREAM_DISCARD_S)
        quick_mlx_sample(mlx_ser, STREAM_DISCARD_S)
        force.ser.reset_input_buffer()
        mlx_ser.reset_input_buffer()


def collect_state(
    *,
    mark10,
    force,
    mlx_ser,
    contact_pos,
    B0,
    session_id,
    trial,
    pair_id,
    target_d_mm,
    preload_d_mm,
    state_label,
    path_mode,
    phase,
    record_s,
    csv_writer,
    log,
):
    """Move to one displacement state and record paired F/B samples."""
    target_pos = contact_pos - target_d_mm
    print(
        f"\n  {state_label}: move to d={target_d_mm:.3f} mm "
        f"({path_mode}), record {record_s:.0f} s"
    )
    actual_pos = mark10.move_to(target_pos, tolerance_mm=TARGET_POSITION_TOL_MM)
    d_actual = contact_pos - actual_pos

    time.sleep(PRE_RECORD_SETTLE_S)
    flush_streams(force, mlx_ser)

    print(f"    d_actual={d_actual:.3f} mm")
    log.write(
        f"[trial {trial} pair {pair_id} {state_label}] start "
        f"d_target={target_d_mm:.4f} d_actual={d_actual:.4f} "
        f"pos={actual_pos:.4f}\n"
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
        if F_HARD_LIMIT_N is not None and abs(F_N) >= F_HARD_LIMIT_N:
            raise RuntimeError(
                f"{PROTOCOL_SHORT_NAME} hard force limit exceeded: "
                f"F={F_N:+.3f} N "
                f">= {F_HARD_LIMIT_N:.3f} N"
            )

        bx, by, bz = B
        Bm = bmag(bx, by, bz)
        dbx, dby, dbz = bx - B0[0], by - B0[1], bz - B0[2]
        row = {
            "time_s": f"{time.time():.6f}",
            "session_id": session_id,
            "trial": trial,
            "repeat_id": trial,
            "pair_id": pair_id,
            "stage": STAGE_LABEL,
            "state_label": state_label,
            "phase": phase,
            "control_mode": "disp_path_hold",
            "path_mode": path_mode,
            "target_label": target_label(target_d_mm),
            "d_target_mm": f"{target_d_mm:.4f}",
            "d_preload_mm": f"{preload_d_mm:.4f}",
            "d_actual_mm": f"{d_actual:.4f}",
            "d_mm": f"{d_actual:.4f}",
            "q_mm": "",
            "d_error_mm": f"{d_actual - target_d_mm:+.4f}",
            "mark10_pos_mm": f"{actual_pos:.4f}",
            "t_rel_s": f"{t_rel:.4f}",
            "F_N": f"{F_N:.6f}",
            "mean_Bx_uT": f"{bx:.4f}",
            "mean_By_uT": f"{by:.4f}",
            "mean_Bz_uT": f"{bz:.4f}",
            "delta_Bx_uT": f"{dbx:.4f}",
            "delta_By_uT": f"{dby:.4f}",
            "delta_Bz_uT": f"{dbz:.4f}",
            "Bmag_uT": f"{Bm:.4f}",
            **metadata_values(),
            "note": "",
        }
        csv_writer.writerow(row)
        samples.append(
            {
                "t_rel_s": t_rel,
                "d_actual_mm": d_actual,
                "F_N": F_N,
                "mean_Bx_uT": bx,
                "mean_By_uT": by,
                "mean_Bz_uT": bz,
                "delta_Bx_uT": dbx,
                "delta_By_uT": dby,
                "delta_Bz_uT": dbz,
                "Bmag_uT": Bm,
            }
        )

        if t_rel >= next_print:
            print(
                f"      t={t_rel:5.1f} s  F={F_N*1000:+8.1f} mN  "
                f"|B|={Bm:8.1f} uT"
            )
            next_print += ROW_PRINT_EVERY_S

    summary = summarize_samples(samples)
    print(
        f"    summary(last {SUMMARY_WINDOW_S:.0f}s): "
        f"F={summary['F_N']*1000:+.1f} mN, "
        f"|B|={summary['Bmag_uT']:.1f} uT, "
        f"n={summary['n']}"
    )
    log.write(
        f"[trial {trial} pair {pair_id} {state_label}] summary "
        f"n={summary['n']} d={summary['d_mm']:.4f} "
        f"F={summary['F_N']:.6f} Bmag={summary['Bmag_uT']:.4f}\n"
    )
    log.flush()
    return summary


def pair_diagnostics(direct, returned):
    d_diff = returned["d_mm"] - direct["d_mm"]
    dF = returned["F_N"] - direct["F_N"]
    dBmag = returned["Bmag_uT"] - direct["Bmag_uT"]
    dBx = returned["delta_Bx_uT"] - direct["delta_Bx_uT"]
    dBy = returned["delta_By_uT"] - direct["delta_By_uT"]
    dBz = returned["delta_Bz_uT"] - direct["delta_Bz_uT"]
    dBvec = vector_norm3(dBx, dBy, dBz)
    slope_mag = dBmag / dF if abs(dF) > 1e-9 else float("nan")

    same_d_ok = abs(d_diff) <= D_MATCH_TOL_MM + FLOAT_COMPARE_EPS
    force_ok = abs(dF) >= MIN_FORCE_SPLIT_N
    b_ok = dBvec >= DYNAMIC_B_SIGNAL_UT
    if same_d_ok and force_ok and b_ok:
        verdict = "strong"
    elif same_d_ok and force_ok:
        verdict = "force_split_only"
    elif same_d_ok:
        verdict = "weak_force_split"
    else:
        verdict = "bad_d_match"

    return {
        "d_diff_mm": d_diff,
        "delta_F_N": dF,
        "delta_Bmag_uT": dBmag,
        "delta_Bx_uT": dBx,
        "delta_By_uT": dBy,
        "delta_Bz_uT": dBz,
        "delta_Bvec_uT": dBvec,
        "slope_Bmag_uT_per_N": slope_mag,
        "same_d_ok": same_d_ok,
        "force_split_ok": force_ok,
        "b_signal_ok": b_ok,
        "verdict": verdict,
    }


def write_pair_summary(writer, session_id, trial, pair_id, target_d, preload_d,
                       direct, returned, diag):
    writer.writerow({
        "session_id": session_id,
        **metadata_values(),
        "trial": trial,
        "pair_id": pair_id,
        "target_label": target_label(target_d),
        "d_target_mm": f"{target_d:.4f}",
        "d_preload_mm": f"{preload_d:.4f}",
        "d_direct_mm": f"{direct['d_mm']:.4f}",
        "d_return_mm": f"{returned['d_mm']:.4f}",
        "d_diff_mm": f"{diag['d_diff_mm']:+.4f}",
        "F_direct_N": f"{direct['F_N']:.6f}",
        "F_return_N": f"{returned['F_N']:.6f}",
        "delta_F_N": f"{diag['delta_F_N']:+.6f}",
        "Bmag_direct_uT": f"{direct['Bmag_uT']:.4f}",
        "Bmag_return_uT": f"{returned['Bmag_uT']:.4f}",
        "delta_Bmag_uT": f"{diag['delta_Bmag_uT']:+.4f}",
        "delta_Bx_uT": f"{diag['delta_Bx_uT']:+.4f}",
        "delta_By_uT": f"{diag['delta_By_uT']:+.4f}",
        "delta_Bz_uT": f"{diag['delta_Bz_uT']:+.4f}",
        "delta_Bvec_uT": f"{diag['delta_Bvec_uT']:.4f}",
        "slope_Bmag_uT_per_N": f"{diag['slope_Bmag_uT_per_N']:.4f}",
        "same_d_ok": int(diag["same_d_ok"]),
        "force_split_ok": int(diag["force_split_ok"]),
        "b_signal_ok": int(diag["b_signal_ok"]),
        "verdict": diag["verdict"],
    })


def print_pair_diagnostics(diag):
    print("\n    pair diagnostic: return - direct")
    print(f"      delta d     = {diag['d_diff_mm']:+.3f} mm")
    print(f"      delta F     = {diag['delta_F_N']*1000:+.1f} mN")
    print(f"      delta |B|   = {diag['delta_Bmag_uT']:+.1f} uT")
    print(f"      |delta B3|  = {diag['delta_Bvec_uT']:.1f} uT")
    print(f"      d|B|/dF     = {diag['slope_Bmag_uT_per_N']:+.1f} uT/N")
    print(f"      verdict     = {diag['verdict']}")


def register_formal_design_session(session_id, status, note=""):
    if not FORMAL_DESIGN_PATH.exists():
        print(f"  ! formal design registry skipped: missing {FORMAL_DESIGN_PATH.name}")
        return
    changed = register_session(
        FORMAL_DESIGN_PATH,
        FORMAL_EXPERIMENT_KEY,
        SessionRecord(
            session_id=session_id,
            status=status,
            summary_filename=SUMMARY_FILENAME,
            figure_filename=FIGURE_FILENAME,
            note=note,
        ),
    )
    if changed:
        print(
            f"  registry -> {FORMAL_DESIGN_PATH.name} "
            f"({FORMAL_EXPERIMENT_KEY}, {status})"
        )
    else:
        print(
            f"  registry already contains {session_id} "
            f"({FORMAL_EXPERIMENT_KEY})"
        )


def registry_note_from_error(exc, limit=120):
    text = " ".join(str(exc).split())
    return text.replace("|", "/")[:limit]


def record_preflight_failure(session_id, log_path, ts, status, note):
    try:
        with log_path.open("a", encoding="utf-8") as log:
            if log.tell() == 0:
                log.write(f"# {LOG_HEADER} {ts}\n")
                log.write(f"# session_id={session_id}\n")
            log.write(f"# status={status}\n")
            log.write(f"ERROR: {note}\n")
    except Exception as exc:
        print(f"  ! pre-flight run_log write failed: {exc}")


def fail_before_trial(session_id, log_path, ts, message, status="error"):
    note = registry_note_from_error(message)
    record_preflight_failure(session_id, log_path, ts, status, note)
    sys.exit(f"\n{message}")


def registry_status_for_pairs(pair_summary_count, usable_pair_count, expected_pair_count):
    if pair_summary_count == expected_pair_count and usable_pair_count == expected_pair_count:
        return "formal", ""
    return (
        "",
        (
            f"not registered: {usable_pair_count}/{expected_pair_count} usable "
            f"strong pairs, {pair_summary_count}/{expected_pair_count} total pairs"
        ),
    )


def main():
    OUTPUT_ROOT.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"session_{ts}"
    session_dir = OUTPUT_ROOT / session_id
    session_dir.mkdir(parents=True)
    log_path = session_dir / "run_log.txt"
    summary_path = session_dir / SUMMARY_FILENAME
    expected_pair_count = N_TRIALS * len(D_TARGETS_MM)
    pair_summary_count = 0
    usable_pair_count = 0
    run_status = ""
    registry_note = ""

    est_total_min = (
        N_TRIALS
        * len(D_TARGETS_MM)
        * (2 * TARGET_RECORD_S + PRELOAD_RECORD_S
           + 3 * PRE_RECORD_SETTLE_S + 3 * INTER_STATE_SETTLE_S
           + INTER_TRIAL_REST_S)
        / 60
    )

    print("\n" + "=" * 64)
    print(f"  {PROTOCOL_TITLE}")
    print("=" * 64)
    print(f"  session        : {session_id}")
    print(f"  trials         : {N_TRIALS}")
    print(f"  target d       : {D_TARGETS_MM}")
    print("  preload plan   : "
          + ", ".join(
              f"{d:.2f}->{preload_depth_for_target(d):.2f} mm"
              for d in D_TARGETS_MM
          ))
    print(f"  target record  : {TARGET_RECORD_S:.0f} s")
    print(f"  preload record : {PRELOAD_RECORD_S:.0f} s")
    print(f"  inter-trial rest: {INTER_TRIAL_REST_S:.0f} s")
    print(f"  est total      : ~{est_total_min:.1f} min")
    print()
    print("Pre-flight:")
    print(f"  [ ] {PREFLIGHT_FIRST_LINE}")
    print("  [ ] Mark-10 start position about 6 mm above lower limit")
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
            mlx_ser, 1.0, "MLX warmup before opening motion hardware")
        print(f"  MLX90393 stream on {mlx_port}  (warmup n={n_warmup})\n")
    except Exception as exc:
        fail_before_trial(
            session_id,
            log_path,
            ts,
            f"MLX90393 required for {PROTOCOL_SHORT_NAME}. {exc}",
        )

    print("Opening Mark-10 ...")
    try:
        mark10 = Mark10(MARK10_PORT, MARK10_BAUD,
                        speed_mm_per_min=MARK10_SPEED_MM_PER_MIN)
    except Mark10Error as exc:
        mlx_ser.close()
        fail_before_trial(session_id, log_path, ts, exc)
    print("  Mark-10 ready")

    print("Opening UNO_force ...")
    try:
        force = ForceReader(find_force_port())
        force.live_tare(duration_s=LIVE_TARE_S,
                        pre_settle_s=TARE_PRE_SETTLE_S)
        assert_no_contact_live_tare(force, "APMD same-d/different-F pre-flight")
    except Exception as exc:
        mlx_ser.close()
        mark10.close()
        fail_before_trial(
            session_id,
            log_path,
            ts,
            f"Force sensor required for {PROTOCOL_SHORT_NAME}. {exc}",
        )

    print("Capturing B0 (no-contact baseline) ...")
    try:
        (b0x, b0y, b0z), _, n_b0 = require_mlx_sample(
            mlx_ser, 1.5, "B0 capture")
    except MlxNoDataError as exc:
        mlx_ser.close()
        force.close()
        mark10.close()
        fail_before_trial(session_id, log_path, ts, exc)
    B0 = (b0x, b0y, b0z)
    print(f"  B0 = ({b0x:+.2f}, {b0y:+.2f}, {b0z:+.2f}) uT  (n={n_b0})")

    trial_start_pos = mark10.position_stable()
    print(f"  trial_start_pos = {trial_start_pos:+.3f} mm")

    log = log_path.open("w", encoding="utf-8")
    log.write(f"# {LOG_HEADER} {ts}\n")
    log.write(
        f"# D_TARGETS_MM={D_TARGETS_MM}, "
        f"D_PRELOAD_BY_TARGET_MM={D_PRELOAD_BY_TARGET_MM}, "
        f"D_PRELOAD_MM={D_PRELOAD_MM}\n"
    )
    log.write(
        f"# TARGET_RECORD_S={TARGET_RECORD_S}, "
        f"PRELOAD_RECORD_S={PRELOAD_RECORD_S}, N_TRIALS={N_TRIALS}\n"
    )
    log.write(f"# live_tare_N={force.live_tare_N:.5f}\n")
    log.write(f"# B0={B0}\n")
    log.write(
        f"# head_id={HEAD_ID}, sample_id={SAMPLE_ID}, magnet_id={MAGNET_ID}, "
        f"force_calibration_id={FORCE_CALIBRATION_ID}, "
        f"displacement_zero_id={DISPLACEMENT_ZERO_ID}\n"
    )
    log.write(f"# trial_start_pos={trial_start_pos:.4f}\n")
    log.flush()

    fieldnames = [
        "time_s", "session_id", "trial", "repeat_id", "pair_id", "stage",
        "state_label", "phase", "control_mode", "path_mode", "target_label",
        "d_target_mm", "d_preload_mm", "d_actual_mm", "d_mm", "q_mm",
        "d_error_mm", "mark10_pos_mm", "t_rel_s", "F_N",
        "mean_Bx_uT", "mean_By_uT", "mean_Bz_uT",
        "delta_Bx_uT", "delta_By_uT", "delta_Bz_uT", "Bmag_uT",
        *metadata_fieldnames(), "note",
    ]
    summary_fields = [
        "session_id", *metadata_fieldnames(), "trial", "pair_id", "target_label",
        "d_target_mm", "d_preload_mm", "d_direct_mm", "d_return_mm",
        "d_diff_mm", "F_direct_N", "F_return_N", "delta_F_N",
        "Bmag_direct_uT", "Bmag_return_uT", "delta_Bmag_uT",
        "delta_Bx_uT", "delta_By_uT", "delta_Bz_uT", "delta_Bvec_uT",
        "slope_Bmag_uT_per_N", "same_d_ok", "force_split_ok",
        "b_signal_ok", "verdict",
    ]

    summary_file = summary_path.open("w", newline="", encoding="utf-8")
    summary_writer = csv.DictWriter(summary_file, fieldnames=summary_fields)
    summary_writer.writeheader()

    try:
        for trial in range(1, N_TRIALS + 1):
            print("\n" + "=" * 64)
            print(f"  TRIAL {trial}/{N_TRIALS}")
            print("=" * 64)

            contact_pos = find_contact(mark10, force, trial, log)
            if contact_pos is None:
                print(f"  ! contact not found, aborting trial {trial}")
                continue

            contact_depth = abs(contact_pos - trial_start_pos)
            max_preload = max(preload_depth_for_target(d) for d in D_TARGETS_MM)
            planned_depth = contact_depth + max_preload
            print(
                f"  contact depth from start = {contact_depth:.2f} mm; "
                f"max planned travel from start ~= {planned_depth:.2f} mm"
            )

            for pair_id, target_d in enumerate(D_TARGETS_MM, start=1):
                preload_d = preload_depth_for_target(target_d)
                label = target_label(target_d)
                csv_path = session_dir / f"{STATE_FILE_PREFIX}_{label}_rep{trial}.csv"
                with csv_path.open("w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()

                    direct = collect_state(
                        mark10=mark10,
                        force=force,
                        mlx_ser=mlx_ser,
                        contact_pos=contact_pos,
                        B0=B0,
                        session_id=session_id,
                        trial=trial,
                        pair_id=pair_id,
                        target_d_mm=target_d,
                        preload_d_mm=preload_d,
                        state_label="direct_target",
                        path_mode="direct_loading",
                        phase="holding",
                        record_s=TARGET_RECORD_S,
                        csv_writer=writer,
                        log=log,
                    )
                    time.sleep(INTER_STATE_SETTLE_S)

                    collect_state(
                        mark10=mark10,
                        force=force,
                        mlx_ser=mlx_ser,
                        contact_pos=contact_pos,
                        B0=B0,
                        session_id=session_id,
                        trial=trial,
                        pair_id=pair_id,
                        target_d_mm=preload_d,
                        preload_d_mm=preload_d,
                        state_label="preload_deep",
                        path_mode="preload_loading",
                        phase="preload",
                        record_s=PRELOAD_RECORD_S,
                        csv_writer=writer,
                        log=log,
                    )
                    time.sleep(INTER_STATE_SETTLE_S)

                    returned = collect_state(
                        mark10=mark10,
                        force=force,
                        mlx_ser=mlx_ser,
                        contact_pos=contact_pos,
                        B0=B0,
                        session_id=session_id,
                        trial=trial,
                        pair_id=pair_id,
                        target_d_mm=target_d,
                        preload_d_mm=preload_d,
                        state_label="return_target",
                        path_mode="return_unloading",
                        phase="holding",
                        record_s=TARGET_RECORD_S,
                        csv_writer=writer,
                        log=log,
                    )

                diag = pair_diagnostics(direct, returned)
                print_pair_diagnostics(diag)
                write_pair_summary(
                    summary_writer,
                    session_id,
                    trial,
                    pair_id,
                    target_d,
                    preload_d,
                    direct,
                    returned,
                    diag,
                )
                pair_summary_count += 1
                if diag["verdict"] == "strong":
                    usable_pair_count += 1
                summary_file.flush()
                log.write(
                    f"[trial {trial} pair {pair_id}] diagnostic "
                    f"dd={diag['d_diff_mm']:+.4f} "
                    f"dF={diag['delta_F_N']:+.6f} "
                    f"dBmag={diag['delta_Bmag_uT']:+.4f} "
                    f"dBvec={diag['delta_Bvec_uT']:.4f} "
                    f"verdict={diag['verdict']}\n"
                )
                log.flush()

            print(f"\n  PHASE C: retracting to start ({trial_start_pos:+.3f} mm)")
            try:
                back_pos = mark10.move_to(trial_start_pos)
                print(f"    back at {back_pos:+.3f} mm")
            except Mark10Error as exc:
                print(f"  ! retract error: {exc}")

            if trial < N_TRIALS:
                print(f"\n  resting {INTER_TRIAL_REST_S:.0f} s for recovery ...")
                time.sleep(INTER_TRIAL_REST_S)

        run_status, registry_note = registry_status_for_pairs(
            pair_summary_count,
            usable_pair_count,
            expected_pair_count,
        )
        if not run_status:
            print(f"\n  formal registry skipped: {registry_note}")
            log.write(f"# formal registry skipped: {registry_note}\n")
            log.flush()

    except KeyboardInterrupt:
        print("\n\nUser abort. Will retract.")
        run_status = ""
        registry_note = f"not registered: user abort after {pair_summary_count}/{expected_pair_count} pairs"
    except Exception as exc:
        print(f"\n\n! unexpected error: {exc}")
        log.write(f"\nERROR: {exc}\n")
        run_status = ""
        registry_note = f"not registered: {registry_note_from_error(exc)}"
        raise
    finally:
        try:
            mark10.move_to(trial_start_pos)
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
        mark10.close()
        if run_status:
            try:
                register_formal_design_session(session_id, run_status, registry_note)
            except Exception as exc:
                print(f"  ! formal design registry update failed: {exc}")

    print(f"\n=== {PROTOCOL_SHORT_NAME} done. Files in: {session_dir}")
    for p in sorted(session_dir.glob(CSV_PRINT_GLOB)):
        print(f"  {p.name}")
    print(f"  {log_path.name}")
    if NEXT_MESSAGE:
        print(f"\n{NEXT_MESSAGE}")


if __name__ == "__main__":
    main()
