"""Stage J+ -- same-force, different-displacement path probe.

Purpose:
  The active fixed-force Stage J hold was not stable enough on the soft
  sample. Stage J+ creates a cleaner pairwise comparison:

      loading path:   acquire target F and record B,d
      preload deeper: establish a different path/internal material state
      unloading path: reacquire the same target F and record B,d

  If the two target-force states match in F but differ in d and B, they
  provide direct evidence for the displacement column

      j_d = dB / dd | F

  This is a path-pair probe, not a final force-control characterization.
"""

import csv
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

import serial

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

# --- Stage J+ path settings ---
N_TRIALS = 3
F_TARGETS = [(170, 1.70), (190, 1.90)]
D_PRELOAD_EXTRA_MM = 0.30
D_PRELOAD_MAX_MM = 2.00
D_SOFT_LIMIT_MM = 2.20
CONTACT_RELIEF_MM = 0.20
START_RESET_TOL_MM = 0.02

TARGET_RECORD_S = 20.0
PRELOAD_RECORD_S = 8.0
PRE_RECORD_SETTLE_S = 3.0
STREAM_DISCARD_S = 1.0
SUMMARY_WINDOW_S = 5.0
SUMMARY_WINDOW_MODE = "head"
ROW_PRINT_EVERY_S = 5.0

# --- Target acquisition ---
FORCE_MATCH_TOL_N = 0.100
FORCE_MATCH_TOL_FRAC = 0.050
ACQUIRE_MAX_ITERS = 90
ACQUIRE_SETTLE_S = 0.45
ACQUIRE_SAMPLE_S = 0.35
ACQUIRE_MIN_STEP_MM = 0.02
ACQUIRE_MAX_STEP_MM = 0.16
CONTROL_MOVE_TOL_MM = 0.02
PRELOAD_STEP_MM = 0.10
PRELOAD_CHECK_SETTLE_S = 0.25
PRELOAD_CHECK_SAMPLE_S = 0.25
F_PRELOAD_CAP_EXTRA_N = 1.00
F_PRELOAD_CAP_MAX_N = 3.20

# --- Live diagnostics only ---
MIN_D_SPLIT_MM = 0.10
MIN_PRELOAD_SPLIT_MM = 0.20
DYNAMIC_B_SIGNAL_UT = 12.5

# --- Safety ---
F_HARD_LIMIT_N = 5.0

# --- Tare ---
LIVE_TARE_S = 2.0
TARE_PRE_SETTLE_S = 3.0

# --- Recovery ---
INTER_PAIR_SETTLE_S = 5.0
INTER_PAIR_REST_S = 20.0
INTER_TRIAL_REST_S = 60.0

# --- Metadata ---
SAMPLE_ID = ""
MAGNET_ID = ""
HEAD_ID = "stamp_head_v1"
FORCE_CALIBRATION_ID = "force_calibration_20260602_190856"
DISPLACEMENT_ZERO_ID = "stageD_session_20260602_201421"

# --- Output ---
HERE = Path(__file__).parent
OUTPUT_ROOT = HERE / "decouple_data"


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


def should_reset_to_trial_start(current_pos, trial_start_pos):
    return current_pos < trial_start_pos - START_RESET_TOL_MM


def reset_to_trial_start_if_needed(mark10, trial_start_pos):
    current_pos = mark10.position_stable()
    if not should_reset_to_trial_start(current_pos, trial_start_pos):
        print(f"    already at/above start ({current_pos:+.3f} mm); "
              "skip downward trim")
        return current_pos
    back_pos = mark10.move_to(trial_start_pos)
    print(f"    back at {back_pos:+.3f} mm")
    return back_pos


def force_label(force_N):
    return f"{int(round(force_N * 100)):03d}"


def force_tolerance(target_N):
    return max(FORCE_MATCH_TOL_N, abs(target_N) * FORCE_MATCH_TOL_FRAC)


def compute_preload_depth(loading_d_mm):
    return min(loading_d_mm + D_PRELOAD_EXTRA_MM, D_PRELOAD_MAX_MM)


def preload_force_cap(match_target_N):
    return min(match_target_N + F_PRELOAD_CAP_EXTRA_N, F_PRELOAD_CAP_MAX_N)


def is_usable_preload_stop(loading_d_mm, preload_d_mm):
    return abs(preload_d_mm - loading_d_mm) >= MIN_PRELOAD_SPLIT_MM


def choose_acquire_step_mm(error_N):
    ae = abs(error_N)
    if ae > 0.80:
        step = 0.16
    elif ae > 0.40:
        step = 0.12
    elif ae > 0.15:
        step = 0.08
    elif ae > 0.06:
        step = 0.04
    else:
        step = 0.02
    return max(ACQUIRE_MIN_STEP_MM, min(ACQUIRE_MAX_STEP_MM, step))


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

    if SUMMARY_WINDOW_MODE == "head":
        t_min = min(s["t_rel_s"] for s in samples)
        window = [s for s in samples if s["t_rel_s"] <= t_min + window_s]
    else:
        t_max = max(s["t_rel_s"] for s in samples)
        window = [s for s in samples if s["t_rel_s"] >= t_max - window_s]
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
    }


def flush_streams(force, mlx_ser):
    force.ser.reset_input_buffer()
    mlx_ser.reset_input_buffer()
    if STREAM_DISCARD_S > 0:
        force.drain(STREAM_DISCARD_S)
        quick_mlx_sample(mlx_ser, STREAM_DISCARD_S)
        force.ser.reset_input_buffer()
        mlx_ser.reset_input_buffer()


def acquire_force_target(
    mark10,
    force,
    contact_pos,
    target_F_N,
    log,
    *,
    trial,
    pair_label,
    state_label,
):
    """Move in small 0.02-mm-compatible steps until F is near target_F_N."""
    lower_pos = contact_pos - D_SOFT_LIMIT_MM
    upper_pos = contact_pos + CONTACT_RELIEF_MM
    pos = mark10.position_stable()
    tol = force_tolerance(target_F_N)
    previous = None

    for i in range(1, ACQUIRE_MAX_ITERS + 1):
        time.sleep(ACQUIRE_SETTLE_S)
        F_m, F_s, F_n = force.sample_average(ACQUIRE_SAMPLE_S)
        pos = mark10.position_stable()
        d_actual = contact_pos - pos
        err = target_F_N - F_m

        log.write(
            f"[trial {trial} pair {pair_label} {state_label} acquire] "
            f"iter={i} targetF={target_F_N:.4f} F={F_m:.4f} "
            f"err={err:.4f} d={d_actual:.4f} pos={pos:.4f}\n"
        )
        log.flush()

        if F_HARD_LIMIT_N is not None and abs(F_m) >= F_HARD_LIMIT_N:
            return False, "hard_limit", pos, d_actual, F_m, i
        if abs(err) <= tol:
            return True, "reached", pos, d_actual, F_m, i
        if previous is not None and err * previous["err"] < 0:
            best = (
                {"pos": pos, "d": d_actual, "F": F_m, "err": err}
                if abs(err) <= abs(previous["err"])
                else previous
            )
            if abs(best["pos"] - pos) > CONTROL_MOVE_TOL_MM:
                try:
                    pos = mark10.move_to(
                        best["pos"], tolerance_mm=CONTROL_MOVE_TOL_MM)
                except Mark10Error as exc:
                    return (
                        False,
                        f"mark10_error:{exc}",
                        pos,
                        d_actual,
                        F_m,
                        i,
                    )
            return True, "bracketed_best", best["pos"], best["d"], best["F"], i
        if err > 0 and d_actual >= D_SOFT_LIMIT_MM:
            return False, "d_soft_limit", pos, d_actual, F_m, i

        previous = {"pos": pos, "d": d_actual, "F": F_m, "err": err}
        step = choose_acquire_step_mm(err)
        next_pos = pos - step if err > 0 else pos + step
        next_pos = min(max(next_pos, lower_pos), upper_pos)
        try:
            pos = mark10.move_to(next_pos, tolerance_mm=CONTROL_MOVE_TOL_MM)
        except Mark10Error as exc:
            return False, f"mark10_error:{exc}", pos, d_actual, F_m, i

    return False, "max_iters", pos, contact_pos - pos, F_m, ACQUIRE_MAX_ITERS


def collect_current_state(
    *,
    mark10,
    force,
    mlx_ser,
    contact_pos,
    B0,
    session_id,
    trial,
    pair_id,
    target_F_N,
    d_preload_mm,
    state_label,
    path_mode,
    phase,
    record_s,
    csv_writer,
    log,
):
    print(
        f"\n  {state_label}: record {record_s:.0f} s at current position "
        f"({path_mode})"
    )
    time.sleep(PRE_RECORD_SETTLE_S)
    flush_streams(force, mlx_ser)

    pos = mark10.position_stable()
    d_actual = contact_pos - pos
    print(f"    d_actual={d_actual:.3f} mm")
    log.write(
        f"[trial {trial} pair {pair_id} {state_label}] start "
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
        F_error = F_N - target_F_N
        row = {
            "time_s": f"{time.time():.6f}",
            "session_id": session_id,
            "trial": trial,
            "repeat_id": trial,
            "pair_id": pair_id,
            "stage": "Jplus",
            "state_label": state_label,
            "phase": phase,
            "control_mode": "same_force_path_pair",
            "path_mode": path_mode,
            "target_label": force_label(target_F_N),
            "target": f"{target_F_N:.5f}",
            "actual": f"{F_N:.6f}",
            "F_target_N": f"{target_F_N:.5f}",
            "F_N": f"{F_N:.6f}",
            "F_error_N": f"{F_error:+.6f}",
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
            **metadata_values(),
            "note": "",
        }
        csv_writer.writerow(row)
        samples.append(
            {
                "t_rel_s": t_rel,
                "d_actual_mm": d_actual,
                "F_N": F_N,
                "Bx_uT": bx,
                "By_uT": by,
                "Bz_uT": bz,
                "delta_Bx_uT": dbx,
                "delta_By_uT": dby,
                "delta_Bz_uT": dbz,
                "Bmag_uT": Bm,
            }
        )

        if t_rel >= next_print:
            print(
                f"      t={t_rel:5.1f} s  F={F_N*1000:+8.1f} mN  "
                f"d={d_actual:5.3f} mm  |B|={Bm:8.1f} uT"
            )
            next_print += ROW_PRINT_EVERY_S

    summary = summarize_samples(samples)
    print(
        f"    summary({SUMMARY_WINDOW_MODE} {SUMMARY_WINDOW_S:.0f}s): "
        f"F={summary['F_N']*1000:+.1f} mN, "
        f"d={summary['d_mm']:.3f} mm, "
        f"|B|={summary['Bmag_uT']:.1f} uT, n={summary['n']}"
    )
    log.write(
        f"[trial {trial} pair {pair_id} {state_label}] summary "
        f"n={summary['n']} F={summary['F_N']:.6f} "
        f"d={summary['d_mm']:.4f} Bmag={summary['Bmag_uT']:.4f}\n"
    )
    log.flush()
    return summary


def pair_diagnostics(loading, unloading):
    dF = unloading["F_N"] - loading["F_N"]
    dd = unloading["d_mm"] - loading["d_mm"]
    dBmag = unloading["Bmag_uT"] - loading["Bmag_uT"]
    dBx = unloading["delta_Bx_uT"] - loading["delta_Bx_uT"]
    dBy = unloading["delta_By_uT"] - loading["delta_By_uT"]
    dBz = unloading["delta_Bz_uT"] - loading["delta_Bz_uT"]
    dBvec = vector_norm3(dBx, dBy, dBz)
    slope_mag = dBmag / dd if abs(dd) > 1e-9 else float("nan")

    same_F_ok = abs(dF) <= FORCE_MATCH_TOL_N
    disp_ok = abs(dd) >= MIN_D_SPLIT_MM
    b_ok = dBvec >= DYNAMIC_B_SIGNAL_UT
    if same_F_ok and disp_ok and b_ok:
        verdict = "strong"
    elif same_F_ok and disp_ok:
        verdict = "disp_split_only"
    elif same_F_ok:
        verdict = "weak_disp_split"
    else:
        verdict = "bad_F_match"

    return {
        "delta_F_N": dF,
        "delta_d_mm": dd,
        "delta_Bmag_uT": dBmag,
        "delta_Bx_uT": dBx,
        "delta_By_uT": dBy,
        "delta_Bz_uT": dBz,
        "delta_Bvec_uT": dBvec,
        "slope_Bmag_uT_per_mm": slope_mag,
        "same_F_ok": same_F_ok,
        "disp_split_ok": disp_ok,
        "b_signal_ok": b_ok,
        "verdict": verdict,
    }


def write_pair_summary(
    writer,
    session_id,
    trial,
    pair_id,
    target_F,
    loading,
    unloading,
    diag,
):
    writer.writerow({
        "session_id": session_id,
        **metadata_values(),
        "trial": trial,
        "pair_id": pair_id,
        "target_label": force_label(target_F),
        "F_target_N": f"{target_F:.5f}",
        "F_match_target_N": f"{loading.get('F_match_target_N', loading['F_N']):.6f}",
        "d_preload_mm": f"{loading.get('d_preload_mm', float('nan')):.4f}",
        "d_preload_extra_mm": f"{D_PRELOAD_EXTRA_MM:.4f}",
        "F_loading_N": f"{loading['F_N']:.6f}",
        "F_unloading_N": f"{unloading['F_N']:.6f}",
        "delta_F_N": f"{diag['delta_F_N']:+.6f}",
        "d_loading_mm": f"{loading['d_mm']:.4f}",
        "d_unloading_mm": f"{unloading['d_mm']:.4f}",
        "delta_d_mm": f"{diag['delta_d_mm']:+.4f}",
        "Bmag_loading_uT": f"{loading['Bmag_uT']:.4f}",
        "Bmag_unloading_uT": f"{unloading['Bmag_uT']:.4f}",
        "delta_Bmag_uT": f"{diag['delta_Bmag_uT']:+.4f}",
        "delta_Bx_uT": f"{diag['delta_Bx_uT']:+.4f}",
        "delta_By_uT": f"{diag['delta_By_uT']:+.4f}",
        "delta_Bz_uT": f"{diag['delta_Bz_uT']:+.4f}",
        "delta_Bvec_uT": f"{diag['delta_Bvec_uT']:.4f}",
        "slope_Bmag_uT_per_mm": f"{diag['slope_Bmag_uT_per_mm']:.4f}",
        "same_F_ok": int(diag["same_F_ok"]),
        "disp_split_ok": int(diag["disp_split_ok"]),
        "b_signal_ok": int(diag["b_signal_ok"]),
        "verdict": diag["verdict"],
    })


def print_pair_diagnostics(diag):
    print("\n    pair diagnostic: unloading - loading")
    print(f"      delta F     = {diag['delta_F_N']*1000:+.1f} mN")
    print(f"      delta d     = {diag['delta_d_mm']:+.3f} mm")
    print(f"      delta |B|   = {diag['delta_Bmag_uT']:+.1f} uT")
    print(f"      |delta B3|  = {diag['delta_Bvec_uT']:.1f} uT")
    print(f"      d|B|/dd     = {diag['slope_Bmag_uT_per_mm']:+.1f} uT/mm")
    print(f"      verdict     = {diag['verdict']}")


def move_to_preload_depth(mark10, force, contact_pos, preload_d_mm, force_cap_N):
    """Move deeper in small steps, stopping if preload force leaves window."""
    pos = mark10.position_stable()
    current_d = contact_pos - pos

    while current_d < preload_d_mm - CONTROL_MOVE_TOL_MM:
        next_d = min(current_d + PRELOAD_STEP_MM, preload_d_mm)
        try:
            pos = mark10.move_to(
                contact_pos - next_d, tolerance_mm=CONTROL_MOVE_TOL_MM)
        except Mark10Error as exc:
            return False, f"mark10_error:{exc}", pos, current_d, float("nan")

        current_d = contact_pos - pos
        time.sleep(PRELOAD_CHECK_SETTLE_S)
        F_m, F_s, F_n = force.sample_average(PRELOAD_CHECK_SAMPLE_S)
        if F_m >= force_cap_N:
            return True, "force_cap_stop", pos, current_d, F_m

    F_m, F_s, F_n = force.sample_average(PRELOAD_CHECK_SAMPLE_S)
    return True, "reached", pos, current_d, F_m


def run_pair(
    *,
    mark10,
    force,
    mlx_ser,
    contact_pos,
    B0,
    session_id,
    trial,
    pair_id,
    target_F,
    csv_writer,
    log,
):
    pair_label = force_label(target_F)

    print(f"\n  LOADING TARGET {pair_label}: F={target_F:.3f} N")
    ok, status, pos, d_actual, F_now, n_iter = acquire_force_target(
        mark10,
        force,
        contact_pos,
        target_F,
        log,
        trial=trial,
        pair_label=pair_label,
        state_label="loading_target",
    )
    print(
        f"    acquire loading: F={F_now:+.3f} N, d={d_actual:.3f} mm, "
        f"{status}, it={n_iter:02d}"
    )
    if not ok:
        return None, None, f"loading_{status}"

    loading = collect_current_state(
        mark10=mark10,
        force=force,
        mlx_ser=mlx_ser,
        contact_pos=contact_pos,
        B0=B0,
        session_id=session_id,
        trial=trial,
        pair_id=pair_id,
        target_F_N=target_F,
        d_preload_mm=float("nan"),
        state_label="loading_target",
        path_mode="direct_loading",
        phase="holding",
        record_s=TARGET_RECORD_S,
        csv_writer=csv_writer,
        log=log,
    )

    match_target_F = loading["F_N"]
    preload_d = compute_preload_depth(loading["d_mm"])
    force_cap = preload_force_cap(match_target_F)
    print(
        f"\n  PRELOAD: move to d={preload_d:.3f} mm "
        f"(loading d + {D_PRELOAD_EXTRA_MM:.2f}, cap F={force_cap:.3f} N)"
    )
    ok, status, pos, preload_actual_d, preload_F = (
        move_to_preload_depth(
            mark10, force, contact_pos, preload_d, force_cap)
    )
    print(
        f"    preload: F={preload_F:+.3f} N, d={preload_actual_d:.3f} mm, "
        f"{status}"
    )
    if not ok:
        return loading, None, f"preload_{status}"
    if status == "force_cap_stop" and not is_usable_preload_stop(
        loading["d_mm"], preload_actual_d
    ):
        return loading, None, "preload_force_cap_too_early"
    loading["F_match_target_N"] = match_target_F
    loading["d_preload_mm"] = preload_actual_d

    collect_current_state(
        mark10=mark10,
        force=force,
        mlx_ser=mlx_ser,
        contact_pos=contact_pos,
        B0=B0,
        session_id=session_id,
        trial=trial,
        pair_id=pair_id,
        target_F_N=target_F,
        d_preload_mm=preload_actual_d,
        state_label="preload_deep",
        path_mode="preload_loading",
        phase="preload",
        record_s=PRELOAD_RECORD_S,
        csv_writer=csv_writer,
        log=log,
    )

    print(
        f"\n  UNLOADING TARGET {pair_label}: "
        f"return to matched F={match_target_F:.3f} N"
    )
    ok, status, pos, d_actual, F_now, n_iter = acquire_force_target(
        mark10,
        force,
        contact_pos,
        match_target_F,
        log,
        trial=trial,
        pair_label=pair_label,
        state_label="unloading_target",
    )
    print(
        f"    acquire unloading: F={F_now:+.3f} N, d={d_actual:.3f} mm, "
        f"{status}, it={n_iter:02d}"
    )
    if not ok:
        return loading, None, f"unloading_{status}"

    unloading = collect_current_state(
        mark10=mark10,
        force=force,
        mlx_ser=mlx_ser,
        contact_pos=contact_pos,
        B0=B0,
        session_id=session_id,
        trial=trial,
        pair_id=pair_id,
        target_F_N=match_target_F,
        d_preload_mm=preload_d,
        state_label="unloading_target",
        path_mode="return_unloading",
        phase="holding",
        record_s=TARGET_RECORD_S,
        csv_writer=csv_writer,
        log=log,
    )
    unloading["F_match_target_N"] = match_target_F
    unloading["d_preload_mm"] = preload_actual_d

    return loading, unloading, "ok"


def main():
    OUTPUT_ROOT.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"session_{ts}"
    session_dir = OUTPUT_ROOT / session_id
    session_dir.mkdir(parents=True)
    log_path = session_dir / "run_log.txt"
    summary_path = session_dir / "Jplus_pair_summary.csv"

    est_total_min = (
        N_TRIALS
        * len(F_TARGETS)
        * (2 * TARGET_RECORD_S + PRELOAD_RECORD_S
           + 3 * PRE_RECORD_SETTLE_S + 90)
        / 60
    )

    print("\n" + "=" * 64)
    print("  Stage J+ -- same-F / different-d path probe")
    print("=" * 64)
    print(f"  session        : {session_id}")
    print(f"  trials         : {N_TRIALS}")
    print(f"  force targets  : {[(lab, f) for lab, f in F_TARGETS]}")
    print(
        f"  preload d      : loading d + {D_PRELOAD_EXTRA_MM:.2f} mm, "
        f"cap {D_PRELOAD_MAX_MM:.2f} mm"
    )
    print(f"  D_SOFT_LIMIT   : {D_SOFT_LIMIT_MM:.2f} mm")
    hard_limit_text = "OFF" if F_HARD_LIMIT_N is None else f"{F_HARD_LIMIT_N:.2f} N"
    print(f"  F_HARD_LIMIT   : {hard_limit_text}")
    print(f"  target record  : {TARGET_RECORD_S:.0f} s")
    print(f"  est total      : ~{est_total_min:.1f} min")
    print()
    print("Pre-flight:")
    print("  [ ] Same sample / magnet / MLX geometry as Stage I+")
    print("  [ ] Mark-10 start position still about 10 mm above lower limit")
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
        sys.exit(f"\nMLX90393 required for Stage J+. {exc}")

    print("Opening Mark-10 ...")
    try:
        mark10 = Mark10(MARK10_PORT, MARK10_BAUD,
                        speed_mm_per_min=MARK10_SPEED_MM_PER_MIN)
    except Mark10Error as exc:
        mlx_ser.close()
        sys.exit(f"\n{exc}")
    print("  Mark-10 ready")

    print("Opening UNO_force ...")
    try:
        force = ForceReader(find_force_port())
        force.live_tare(duration_s=LIVE_TARE_S,
                        pre_settle_s=TARE_PRE_SETTLE_S)
        assert_no_contact_live_tare(force, "Stage J+ pre-flight")
    except Exception as exc:
        mlx_ser.close()
        mark10.close()
        sys.exit(f"\nForce sensor required for Stage J+. {exc}")

    print("Capturing B0 (no-contact baseline) ...")
    try:
        (b0x, b0y, b0z), _, n_b0 = require_mlx_sample(
            mlx_ser, 1.5, "B0 capture")
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
    log.write(f"# Stage J+ session {ts}\n")
    log.write(
        f"# F_TARGETS={F_TARGETS}, "
        f"D_PRELOAD_EXTRA_MM={D_PRELOAD_EXTRA_MM}, "
        f"D_PRELOAD_MAX_MM={D_PRELOAD_MAX_MM}, "
        f"N_TRIALS={N_TRIALS}\n"
    )
    log.write(f"# D_SOFT_LIMIT_MM={D_SOFT_LIMIT_MM}, "
              f"F_HARD_LIMIT_N={F_HARD_LIMIT_N}\n")
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
        "target", "actual", "F_target_N", "F_N", "F_error_N",
        "d_preload_mm", "d_actual_mm", "d_mm", "q_mm", "mark10_pos_mm",
        "t_rel_s", "Bx_uT", "By_uT", "Bz_uT",
        "mean_Bx_uT", "mean_By_uT", "mean_Bz_uT",
        "delta_Bx_uT", "delta_By_uT", "delta_Bz_uT", "Bmag_uT",
        *metadata_fieldnames(), "note",
    ]
    summary_fields = [
        "session_id", *metadata_fieldnames(), "trial", "pair_id",
        "target_label", "F_target_N",
        "F_match_target_N", "d_preload_mm", "d_preload_extra_mm",
        "F_loading_N", "F_unloading_N", "delta_F_N", "d_loading_mm",
        "d_unloading_mm", "delta_d_mm",
        "Bmag_loading_uT", "Bmag_unloading_uT", "delta_Bmag_uT",
        "delta_Bx_uT", "delta_By_uT", "delta_Bz_uT", "delta_Bvec_uT",
        "slope_Bmag_uT_per_mm", "same_F_ok", "disp_split_ok",
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

            for pair_id, (target_label_int, target_F) in enumerate(
                F_TARGETS, start=1
            ):
                print("\n" + "-" * 64)
                print(f"  FORCE PAIR {target_label_int}: reset path")
                print("-" * 64)

                print(f"\n  PHASE R: retracting to start ({trial_start_pos:+.3f} mm)")
                try:
                    reset_to_trial_start_if_needed(mark10, trial_start_pos)
                except Mark10Error as exc:
                    print(f"  ! retract error before pair {target_label_int}: {exc}")
                    break

                time.sleep(INTER_PAIR_SETTLE_S)

                contact_pos = find_contact(
                    mark10, force, f"{trial} pair {target_label_int}", log)
                if contact_pos is None:
                    print(f"  ! contact not found, skipping pair {target_label_int}")
                    continue

                contact_depth = abs(contact_pos - trial_start_pos)
                planned_depth = contact_depth + D_PRELOAD_MAX_MM
                print(
                    f"  contact depth from start = {contact_depth:.2f} mm; "
                    f"max planned travel from start <= {planned_depth:.2f} mm"
                )

                csv_path = session_dir / (
                    f"Jplus_same_F_{target_label_int}_rep{trial}.csv"
                )
                with csv_path.open("w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    loading, unloading, status = run_pair(
                        mark10=mark10,
                        force=force,
                        mlx_ser=mlx_ser,
                        contact_pos=contact_pos,
                        B0=B0,
                        session_id=session_id,
                        trial=trial,
                        pair_id=pair_id,
                        target_F=target_F,
                        csv_writer=writer,
                        log=log,
                    )

                if status != "ok":
                    print(f"  ! pair {target_label_int} incomplete: {status}")
                    log.write(
                        f"[trial {trial} pair {target_label_int}] "
                        f"incomplete status={status}\n"
                    )
                    log.flush()
                else:
                    diag = pair_diagnostics(loading, unloading)
                    print_pair_diagnostics(diag)
                    write_pair_summary(
                        summary_writer,
                        session_id,
                        trial,
                        pair_id,
                        target_F,
                        loading,
                        unloading,
                        diag,
                    )
                    summary_file.flush()
                    log.write(
                        f"[trial {trial} pair {target_label_int}] diagnostic "
                        f"dF={diag['delta_F_N']:+.6f} "
                        f"dd={diag['delta_d_mm']:+.4f} "
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
                    break

                time.sleep(INTER_PAIR_REST_S)

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
            reset_to_trial_start_if_needed(mark10, trial_start_pos)
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

    print(f"\n=== Stage J+ done. Files in: {session_dir}")
    for p in sorted(session_dir.glob("Jplus_*.csv")):
        print(f"  {p.name}")
    print(f"  {log_path.name}")
    print("\nNext: python .\\plot_stage_J_plus.py")


if __name__ == "__main__":
    main()
