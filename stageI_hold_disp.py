"""Stage I -- fixed-displacement hold for estimating j_F.

Signal-test version for the temporary fixture.

Purpose:
  Hold d approximately constant and observe whether force relaxation is
  accompanied by magnetic-field relaxation. This probes the local sensitivity

      j_F = dB / dF | d

  because d is held fixed while F changes due to viscoelastic relaxation.

Protocol:
  1. Open MLX first and keep COM6 attached.
  2. Live-tare force sensor.
  3. Capture no-contact B0.
  4. Find contact point using the same force-change-point logic as Stage D.
  5. Move to the stamp-head D-map-derived hold depth.
  6. Hold each displacement for HOLD_S and record a time series of F and B.

This is not a final material-characterization script. It is designed to answer:
"Can we observe useful force relaxation and B relaxation at fixed d?"
"""

import csv
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

import serial

from mark10_control import Mark10, Mark10Error
from force_serial import find_force_port, ForceReader, SANITY_LIMIT_N
from mlx_serial import find_mlx_port


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
MLX_SOFT_REBOOT_ON_EMPTY = True
MLX_REBOOT_OPEN_SETTLE_S = 0.5
MLX_REBOOT_BREAK_S = 0.2
MLX_SAMPLE_RETRIES = 2
MLX_RETRY_WAIT_S = 0.5

# --- Stage I hold settings ---
N_TRIALS = 3
D_HOLDS = [(280, 2.80)]
HOLD_S = 120.0
HOLD_PRE_SETTLE_S = 5.0
HOLD_STREAM_DISCARD_S = 1.0
ROW_PRINT_EVERY_S = 5.0

# --- Contact detection ---
APPROACH_STEP_MM = 0.1
APPROACH_SETTLE_S = 2.0
APPROACH_SAMPLE_S = 0.5
APPROACH_MAX_DESCENT_MM = 15.0
F_CONTACT_N = 0.080
CONTACT_BASELINE_WINDOW = 5
CONTACT_BASELINE_MIN_STEPS = 3
CONTACT_STEP_DELTA_N = 0.015
CONTACT_SLOPE_N_PER_MM = 0.12
PRECONTACT_FORCE_ABORT_N = 0.30

# --- Safety ---
F_HARD_LIMIT_N = None

# --- No-contact sanity ---
EXPECTED_NO_CONTACT_LIVE_TARE_N = -2.90
NO_CONTACT_LIVE_TARE_TOL_N = 0.60

# --- Tare ---
LIVE_TARE_S = 2.0
TARE_PRE_SETTLE_S = 3.0

# --- Recovery ---
INTER_HOLD_SETTLE_S = 3.0
INTER_TRIAL_REST_S = 60.0

# --- Output ---
HERE = Path(__file__).parent
OUTPUT_ROOT = HERE / "decouple_data"

# --- Metadata ---
SAMPLE_ID = ""
MAGNET_ID = ""
HEAD_ID = "stamp_head_v1"
FORCE_CALIBRATION_ID = "force_calibration_20260602_190856"
DISPLACEMENT_ZERO_ID = "stageD_session_20260602_201421"


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


def assert_no_contact_live_tare(force, context):
    """Abort if software tare was likely taken while already compressed."""
    delta = force.live_tare_N - EXPECTED_NO_CONTACT_LIVE_TARE_N
    if abs(delta) <= NO_CONTACT_LIVE_TARE_TOL_N:
        return
    raise RuntimeError(
        f"{context}: live_tare_N={force.live_tare_N:+.4f} N differs from "
        f"expected no-contact baseline {EXPECTED_NO_CONTACT_LIVE_TARE_N:+.4f} N "
        f"by {delta:+.4f} N. The stamp head is likely already touching or "
        "preloaded. Retract to a true no-contact start position, then rerun."
    )


# ============================================================================
# MLX helpers
# ============================================================================

class MlxNoDataError(RuntimeError):
    """Raised when the MLX serial stream is open but has no valid data rows."""


def parse_mlx_line(line):
    """Parse one QT Py MLX CSV row; return (Bx, By, Bz) in uT or None."""
    if not line or line.startswith("MLX90393") or line.startswith("t_ms"):
        return None
    parts = line.split(",")
    if len(parts) != 4:
        return None
    try:
        return (int(parts[1]) / 1000.0,
                int(parts[2]) / 1000.0,
                int(parts[3]) / 1000.0)
    except ValueError:
        return None


def quick_mlx_sample(ser, duration_s):
    """Read MLX for duration_s; return (mean, std, n) for Bx/By/Bz."""
    ser.reset_input_buffer()
    bx, by, bz = [], [], []
    t_end = time.time() + duration_s
    while time.time() < t_end:
        line = ser.readline().decode(errors="ignore").strip()
        parsed = parse_mlx_line(line)
        if parsed is None:
            continue
        x, y, z = parsed
        bx.append(x)
        by.append(y)
        bz.append(z)
    if not bx:
        nan = float("nan")
        return ((nan, nan, nan), (nan, nan, nan), 0)
    means = (statistics.mean(bx), statistics.mean(by), statistics.mean(bz))
    stds = (
        statistics.stdev(bx) if len(bx) > 1 else 0.0,
        statistics.stdev(by) if len(by) > 1 else 0.0,
        statistics.stdev(bz) if len(bz) > 1 else 0.0,
    )
    return means, stds, len(bx)


def soft_reboot_mlx(ser):
    """Ask CircuitPython to reload code.py so the MLX stream starts fresh."""
    time.sleep(MLX_REBOOT_OPEN_SETTLE_S)
    ser.write(b"\x03")
    ser.flush()
    time.sleep(MLX_REBOOT_BREAK_S)
    ser.write(b"\x04")
    ser.flush()


def preview_mlx_lines(ser, duration_s=1.0, max_lines=8):
    ser.reset_input_buffer()
    lines = []
    t_end = time.time() + duration_s
    while time.time() < t_end and len(lines) < max_lines:
        line = ser.readline().decode(errors="ignore").strip()
        if line:
            lines.append(line[:160])
    return lines


def require_mlx_sample(ser, duration_s, context, log=None):
    max_attempts = MLX_SAMPLE_RETRIES + 1
    preview = []
    for attempt in range(1, max_attempts + 1):
        means, stds, n = quick_mlx_sample(ser, duration_s)
        if n > 0:
            return means, stds, n

        preview = preview_mlx_lines(ser)
        if attempt < max_attempts:
            if not preview and MLX_SOFT_REBOOT_ON_EMPTY:
                if log is not None:
                    log.write(f"[MLX] {context}: empty stream; soft reboot\n")
                    log.flush()
                soft_reboot_mlx(ser)
                time.sleep(MLX_STARTUP_WAIT_S)
            else:
                time.sleep(MLX_RETRY_WAIT_S)

    msg = [
        f"{context}: 0 valid MLX90393 CSV samples after "
        f"{max_attempts} attempts.",
        "Expected rows like: t_ms,Bx_milliuT,By_milliuT,Bz_milliuT",
    ]
    if preview:
        msg.append("Raw serial lines seen:")
        msg.extend(f"  {line!r}" for line in preview)
    else:
        msg.append("No raw serial lines were seen.")
    text = "\n".join(msg)
    if log is not None:
        log.write(f"\nMLX ERROR: {text}\n")
        log.flush()
    raise MlxNoDataError(text)


def read_mlx_one(ser, timeout_s=1.0):
    """Read one valid MLX row."""
    t_end = time.time() + timeout_s
    while time.time() < t_end:
        line = ser.readline().decode(errors="ignore").strip()
        parsed = parse_mlx_line(line)
        if parsed is not None:
            return parsed
    return None


def bmag(bx, by, bz):
    return (bx ** 2 + by ** 2 + bz ** 2) ** 0.5


# ============================================================================
# Force helpers
# ============================================================================

def read_force_one(force, timeout_s=1.0):
    """Read one valid tared force sample from ForceReader."""
    t_end = time.time() + timeout_s
    while time.time() < t_end:
        r = force.read_one()
        if r is None:
            continue
        raw_N = r[2]
        if abs(raw_N) >= SANITY_LIMIT_N:
            continue
        return raw_N - force.live_tare_N
    return None


# ============================================================================
# Motion helpers
# ============================================================================

def find_contact(mark10, force, trial_idx, log):
    print(f"\n  PHASE A (trial {trial_idx}): find contact by force change point")
    start_pos = mark10.position_stable()
    step = 0
    approach_history = []

    while True:
        target_pos = start_pos - (step + 1) * APPROACH_STEP_MM
        descent = abs(target_pos - start_pos)
        if descent > APPROACH_MAX_DESCENT_MM:
            print(f"    ! no contact within {APPROACH_MAX_DESCENT_MM:.1f} mm")
            return None

        try:
            mark10.move_to(target_pos)
        except Mark10Error as exc:
            print(f"    ! Mark-10 error during approach: {exc}")
            return None

        time.sleep(APPROACH_SETTLE_S)
        F_m, F_s, F_n = force.sample_average(APPROACH_SAMPLE_S)
        actual_pos = mark10.position_stable()
        descent_actual = abs(actual_pos - start_pos)

        baseline_vals = [
            row[1] for row in approach_history[-CONTACT_BASELINE_WINDOW:]
        ]
        baseline_N = statistics.median(baseline_vals) if baseline_vals else 0.0
        delta_from_baseline_N = F_m - baseline_N
        if approach_history:
            prev_descent, prev_F = approach_history[-1]
            step_delta_N = F_m - prev_F
            step_delta_mm = max(descent_actual - prev_descent, 1e-9)
            slope_N_per_mm = step_delta_N / step_delta_mm
        else:
            step_delta_N = float("nan")
            slope_N_per_mm = float("nan")

        has_enough_baseline = (
            len(approach_history) >= CONTACT_BASELINE_MIN_STEPS
        )
        is_change_point = (
            has_enough_baseline
            and delta_from_baseline_N >= F_CONTACT_N
            and step_delta_N >= CONTACT_STEP_DELTA_N
            and slope_N_per_mm >= CONTACT_SLOPE_N_PER_MM
        )

        if not has_enough_baseline and F_m >= PRECONTACT_FORCE_ABORT_N:
            print(
                f"    !! F={F_m:+.3f} N before baseline was established. "
                "Start position is likely already touching/preloaded."
            )
            log.write(
                f"[trial {trial_idx}] precontact_abort pos={actual_pos:.4f} "
                f"F={F_m:.4f}\n"
            )
            log.flush()
            return None

        print(f"    step {step+1:>3d} descent={descent_actual:5.2f} mm "
              f"F={F_m*1000:+7.2f} +/- {F_s*1000:5.2f} mN "
              f"dF_base={delta_from_baseline_N*1000:+7.2f} mN "
              f"dF_step={step_delta_N*1000:+7.2f} mN "
              f"slope={slope_N_per_mm:+.3f} N/mm")

        if F_HARD_LIMIT_N is not None and abs(F_m) >= F_HARD_LIMIT_N:
            print(f"    !! F = {F_m:+.3f} N exceeded HARD_LIMIT")
            return None

        if is_change_point:
            print(f"    contact change point at descent = {descent_actual:.3f} mm   "
                  f"F = {F_m*1000:+.2f} mN  (step {step+1})")
            log.write(f"[trial {trial_idx}] contact_pos={actual_pos:.4f} "
                      f"F={F_m:.4f} baseline={baseline_N:.4f} "
                      f"dF_base={delta_from_baseline_N:.4f} "
                      f"dF_step={step_delta_N:.4f} "
                      f"slope={slope_N_per_mm:.4f}\n")
            log.flush()
            return actual_pos

        approach_history.append((descent_actual, F_m))
        step += 1


def collect_hold(mark10, force, mlx_ser, contact_pos, B0, trial, hold_label,
                 d_target, csv_writer, log):
    """Move to d_target and collect fixed-d time series."""
    target_pos = contact_pos - d_target
    print(f"\n  HOLD {hold_label:02d}%: move to d={d_target:.3f} mm")
    actual_pos = mark10.move_to(target_pos)
    d_actual = contact_pos - actual_pos
    time.sleep(HOLD_PRE_SETTLE_S)

    print(f"    holding d_actual={d_actual:.3f} mm for {HOLD_S:.0f} s ...")
    log.write(f"[trial {trial} hold {hold_label}] start "
              f"d_target={d_target:.4f} d_actual={d_actual:.4f} "
              f"pos={actual_pos:.4f}\n")
    log.flush()

    force.ser.reset_input_buffer()
    mlx_ser.reset_input_buffer()
    if HOLD_STREAM_DISCARD_S > 0:
        force.drain(HOLD_STREAM_DISCARD_S)
        quick_mlx_sample(mlx_ser, HOLD_STREAM_DISCARD_S)
        force.ser.reset_input_buffer()
        mlx_ser.reset_input_buffer()
    t0 = time.perf_counter()
    next_print = 0.0
    n_rows = 0
    F_first = F_last = None
    B_first = B_last = None

    while True:
        t_rel = time.perf_counter() - t0
        if t_rel >= HOLD_S:
            break

        F_N = read_force_one(force, timeout_s=1.0)
        B = read_mlx_one(mlx_ser, timeout_s=1.0)
        if F_N is None or B is None:
            continue
        bx, by, bz = B
        Bm = bmag(bx, by, bz)
        dbx, dby, dbz = bx - B0[0], by - B0[1], bz - B0[2]

        if F_first is None:
            F_first = F_N
            B_first = Bm
        F_last = F_N
        B_last = Bm
        n_rows += 1

        csv_writer.writerow({
            "trial": trial,
            "hold_label": hold_label,
            "phase": "holding",
            "control_mode": "disp_hold",
            **metadata_values(),
            "d_target_mm": f"{d_target:.4f}",
            "d_actual_mm": f"{d_actual:.4f}",
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
        })

        if F_HARD_LIMIT_N is not None and abs(F_N) >= F_HARD_LIMIT_N:
            print(f"    !! F={F_N:+.3f} N exceeded HARD_LIMIT; aborting hold")
            log.write(f"[trial {trial} hold {hold_label}] hard limit "
                      f"F={F_N:.4f}\n")
            log.flush()
            return False

        if t_rel >= next_print:
            print(f"      t={t_rel:5.1f} s  F={F_N*1000:+8.1f} mN  "
                  f"|B|={Bm:7.0f} uT")
            next_print += ROW_PRINT_EVERY_S

    try:
        final_pos = mark10.position_stable()
    except Mark10Error:
        final_pos = actual_pos
    final_d = contact_pos - final_pos

    if F_first is not None:
        print(f"    done: n={n_rows}, ΔF={(F_last-F_first)*1000:+.1f} mN, "
              f"Δ|B|={B_last-B_first:+.1f} uT, "
              f"d_end={final_d:.3f} mm")
        log.write(f"[trial {trial} hold {hold_label}] done n={n_rows} "
                  f"d_end={final_d:.4f} d_drift={final_d-d_actual:+.4f} "
                  f"dF={F_last-F_first:+.6f} dB={B_last-B_first:+.4f}\n")
    else:
        print("    ! no paired F/B rows collected")
        log.write(f"[trial {trial} hold {hold_label}] no rows\n")
    log.flush()
    return n_rows > 0


# ============================================================================
# Main
# ============================================================================

def main():
    OUTPUT_ROOT.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = OUTPUT_ROOT / f"session_{ts}"
    session_dir.mkdir(parents=True)
    log_path = session_dir / "run_log.txt"

    est_total_min = (
        N_TRIALS * (len(D_HOLDS) * (HOLD_S + INTER_HOLD_SETTLE_S) + 90) / 60
    )

    print("\n" + "=" * 60)
    print("  Stage I -- fixed-displacement hold (j_F probe)")
    print("=" * 60)
    print(f"  session        : {session_dir.name}")
    print(f"  trials         : {N_TRIALS}")
    print(f"  hold depths    : {[(lab, d) for lab, d in D_HOLDS]}")
    print(f"  hold duration  : {HOLD_S:.0f} s per depth")
    hard_limit_text = "OFF" if F_HARD_LIMIT_N is None else f"{F_HARD_LIMIT_N:.2f} N"
    print(f"  F_HARD_LIMIT   : {hard_limit_text}")
    print(f"  est total      : ~{est_total_min:.1f} min")
    print()
    print("Pre-flight:")
    print("  [ ] Sample (bag + magnet) on MLX, same setup as Stage H")
    print("  [ ] Mark-10 at start position about 6 mm above lower limit")
    print("  [ ] Clear visible gap above the sample at the start position")
    print("  [ ] EasyMESUR Home -> PC Control ACTIVE")
    print("  [ ] Arduino IDE Serial Monitor on UNO CLOSED")
    print("  [ ] QT Py / MLX running circuitpython/code.py")
    print("  [ ] Physical lower limit switch still in place")
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
        sys.exit(f"\nMLX90393 required for Stage I. {exc}")

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
        assert_no_contact_live_tare(force, "Stage I pre-flight")
    except Exception as exc:
        mlx_ser.close()
        mark10.close()
        sys.exit(f"\nForce sensor required for Stage I. {exc}")

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
    log.write(f"# Stage I session {ts}\n")
    log.write(f"# metadata={metadata_values()}\n")
    log.write(f"# D_HOLDS={D_HOLDS}, HOLD_S={HOLD_S}, "
              f"N_TRIALS={N_TRIALS}\n")
    log.write(f"# live_tare_N={force.live_tare_N:.5f}\n")
    log.write(f"# B0={B0}\n")
    log.write(f"# trial_start_pos={trial_start_pos:.4f}\n")
    log.flush()

    fieldnames = [
        "trial", "hold_label", "phase", "control_mode",
        *metadata_fieldnames(),
        "d_target_mm", "d_actual_mm", "mark10_pos_mm", "t_rel_s",
        "F_N", "mean_Bx_uT", "mean_By_uT", "mean_Bz_uT",
        "delta_Bx_uT", "delta_By_uT", "delta_Bz_uT", "Bmag_uT",
    ]

    try:
        for trial in range(1, N_TRIALS + 1):
            print("\n" + "=" * 60)
            print(f"  TRIAL {trial}/{N_TRIALS}")
            print("=" * 60)

            contact_pos = find_contact(mark10, force, trial, log)
            if contact_pos is None:
                print(f"  ! contact not found, aborting trial {trial}")
                continue

            for hold_label, d_target in D_HOLDS:
                csv_path = session_dir / (
                    f"I_hold_disp_{hold_label}_rep{trial}.csv"
                )
                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    ok = collect_hold(
                        mark10, force, mlx_ser, contact_pos, B0,
                        trial, hold_label, d_target, writer, log)
                if not ok:
                    print(f"  ! hold {hold_label}% incomplete")
                    break
                time.sleep(INTER_HOLD_SETTLE_S)

            print(f"\n  PHASE C: retracting to start ({trial_start_pos:+.3f} mm)")
            try:
                back_pos = mark10.move_to(trial_start_pos)
                print(f"    back at {back_pos:+.3f} mm")
            except Mark10Error as exc:
                print(f"  ! retract error: {exc}")

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
            mark10.move_to(trial_start_pos)
        except Exception:
            pass
        log.close()
        try:
            mlx_ser.close()
        except Exception:
            pass
        force.close()
        mark10.close()

    print(f"\n=== Stage I done. Files in: {session_dir}")
    for p in sorted(session_dir.glob("I_hold_disp_*.csv")):
        print(f"  {p.name}")
    print(f"  {log_path.name}")
    print("\nNext: plot F(t), B(t), and dB/dF for each fixed-d hold.")


if __name__ == "__main__":
    main()
