"""Stage H -- pseudo force-control B-F curve, plateau mode.

This is a signal-test version of Stage H. Instead of relying on EasyMESUR's
optional Load Target / Load Hold feature, Python closes a slow feedback loop:

  1. Find contact exactly as in Stage E/F.
  2. For each target force F_target, nudge the Mark-10 position up/down.
  3. Stop once the measured force is within tolerance.
  4. Hold the plateau and record F, B, and actual displacement d.

The question Stage H answers: does the B-F curve measured under force-targeted
plateaus resemble the B-F curve measured under displacement control? If yes,
the B-F relation is not only an artifact of prescribed d. If not, path,
viscoelastic state, and q/d history are major parts of the decoupling problem.

This script is intentionally conservative for the temporary fixture:
  - F_TARGET_MAX_N = 0.90 N, matching the temporary fixture's observed range.
  - D_SOFT_LIMIT_MM = 3.60 mm, close to the successful Stage F range.
  - Feedback moves are small (down to 0.02 mm), plateau based, and always
    force-limited.
"""

import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

import serial

from mark10_control import Mark10, Mark10Error
from force_serial import find_force_port, ForceReader
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
MLX_DEBUG_PREVIEW_S = 1.0
MLX_DEBUG_MAX_LINES = 8
MLX_SAMPLE_RETRIES = 2
MLX_RETRY_WAIT_S = 0.5

# --- Trials ---
N_TRIALS = 3
# The temporary fixture in session_20260527_095040 reached only ~0.92 N
# before the conservative displacement limit. Use 0.90 N for the next
# signal-test run so every force target is physically reachable.
F_TARGET_MAX_N = 0.90
N_F_POINTS = 10

# --- Contact detection (Phase A) ---
APPROACH_STEP_MM = 0.2
APPROACH_SETTLE_S = 2.0
APPROACH_SAMPLE_S = 0.5
APPROACH_MAX_DESCENT_MM = 15.0
F_CONTACT_N = 0.025

# --- Pseudo force-control loop (Phase B) ---
FORCE_TOL_N = 0.020
FORCE_TOL_FRAC = 0.015
CONTROL_SETTLE_S = 0.45
CONTROL_SAMPLE_S = 0.35
MAX_CONTROL_ITERS = 50
CONTACT_RELIEF_MM = 0.20
D_SOFT_LIMIT_MM = 3.60
CONTROL_MOVE_TOL_MM = 0.015
MIN_NUDGE_MM = 0.02
MAX_NUDGE_MM = 0.20

# --- Plateau measurement after the target is reached ---
PLATEAU_SETTLE_S = 1.0
PLATEAU_RECORD_S = 2.0
PLATEAU_MLX_S = 1.5

# --- Safety ---
F_HARD_LIMIT_N = 2.50

# --- Recovery ---
INTER_TRIAL_REST_S = 10.0

# --- Tare ---
LIVE_TARE_S = 2.0
TARE_PRE_SETTLE_S = 3.0

# --- Output ---
HERE = Path(__file__).parent
OUTPUT_ROOT = HERE / "decouple_data"

# --- Derived ---
F_TARGETS = [round(i * F_TARGET_MAX_N / (N_F_POINTS - 1), 4)
             for i in range(N_F_POINTS)]


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
    """Read MLX for `duration_s`; return (mean, std, n) for Bx/By/Bz."""
    if ser is None:
        nan = float("nan")
        return ((nan, nan, nan), (nan, nan, nan), 0)
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


def preview_mlx_lines(ser, duration_s=MLX_DEBUG_PREVIEW_S,
                      max_lines=MLX_DEBUG_MAX_LINES):
    """Collect a few raw MLX serial lines for diagnostics."""
    if ser is None:
        return []
    ser.reset_input_buffer()
    lines = []
    t_end = time.time() + duration_s
    while time.time() < t_end and len(lines) < max_lines:
        line = ser.readline().decode(errors="ignore").strip()
        if line:
            lines.append(line[:160])
    return lines


def soft_reboot_mlx(ser):
    """Ask CircuitPython to reload code.py so the MLX stream starts fresh."""
    time.sleep(MLX_REBOOT_OPEN_SETTLE_S)
    ser.write(b"\x03")
    ser.flush()
    time.sleep(MLX_REBOOT_BREAK_S)
    ser.write(b"\x04")
    ser.flush()


def require_mlx_sample(ser, duration_s, context, log=None):
    """Sample MLX and fail loudly if no valid B rows were captured."""
    preview = []
    max_attempts = MLX_SAMPLE_RETRIES + 1
    for attempt in range(1, max_attempts + 1):
        means, stds, n = quick_mlx_sample(ser, duration_s)
        if n > 0:
            if attempt > 1 and log is not None:
                log.write(f"[MLX] {context} recovered on attempt "
                          f"{attempt}/{max_attempts}\n")
                log.flush()
            return means, stds, n

        preview = preview_mlx_lines(ser)
        if attempt < max_attempts:
            if not preview and MLX_SOFT_REBOOT_ON_EMPTY:
                if log is not None:
                    log.write(f"[MLX] {context} saw no raw serial lines; "
                              "soft-rebooting QT Py before retry\n")
                    log.flush()
                soft_reboot_mlx(ser)
                time.sleep(MLX_STARTUP_WAIT_S)
            else:
                time.sleep(MLX_RETRY_WAIT_S)

    msg = [
        f"{context}: 0 valid MLX90393 CSV samples after "
        f"{max_attempts} attempts ({duration_s:.1f} s each).",
        "Expected rows like: t_ms,Bx_milliuT,By_milliuT,Bz_milliuT",
    ]
    if preview:
        msg.append("Raw serial lines seen after the failed sample:")
        msg.extend(f"  {line!r}" for line in preview)
    else:
        msg.append("No raw serial lines were seen after the failed sample.")
    msg.extend([
        "Check that the QT Py is running circuitpython/code.py,",
        "that no other serial reader has the MLX port,",
        "and that the MLX breakout/I2C wiring is still connected.",
    ])
    text = "\n".join(msg)
    if log is not None:
        log.write(f"\nMLX ERROR: {text}\n")
        log.flush()
    raise MlxNoDataError(text)


def bmag(bx, by, bz):
    try:
        return (bx ** 2 + by ** 2 + bz ** 2) ** 0.5
    except TypeError:
        return float("nan")


# ============================================================================
# Phase A: find contact
# ============================================================================

def find_contact(mark10, force, trial_idx, log):
    print(f"\n  PHASE A (trial {trial_idx}): find contact")
    start_pos = mark10.position_stable()
    step = 0

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

        if abs(F_m) >= F_HARD_LIMIT_N:
            print(f"    !! F = {F_m:+.3f} N exceeded HARD_LIMIT")
            return None

        if abs(F_m) >= F_CONTACT_N:
            actual_pos = mark10.position_stable()
            descent_actual = abs(actual_pos - start_pos)
            print(f"    contact at descent = {descent_actual:.3f} mm   "
                  f"F = {F_m*1000:+.2f} mN  (step {step+1})")
            log.write(f"[trial {trial_idx}] contact_pos={actual_pos:.4f} "
                      f"F={F_m:.4f}\n")
            log.flush()
            return actual_pos

        step += 1


# ============================================================================
# Phase B: pseudo force target loop
# ============================================================================

def force_tolerance(target_N):
    return max(FORCE_TOL_N, abs(target_N) * FORCE_TOL_FRAC)


def choose_step_mm(error_N, sign_reversed):
    """Conservative force-feedback position step size."""
    ae = abs(error_N)
    if ae > 0.40:
        step = 0.20
    elif ae > 0.25:
        step = 0.16
    elif ae > 0.12:
        step = 0.10
    elif ae > 0.06:
        step = 0.06
    elif ae > 0.03:
        step = 0.03
    else:
        step = 0.02
    if sign_reversed:
        step *= 0.5
    return max(MIN_NUDGE_MM, min(MAX_NUDGE_MM, step))


def approach_force_target(mark10, force, contact_pos, target_F_N,
                          trial_idx, step_idx, log):
    """Move until measured force is close to target_F_N.

    Returns (reached, status, pos, d_actual, F_m, F_s, F_n, n_iter).
    """
    lower_pos = contact_pos - D_SOFT_LIMIT_MM
    upper_pos = contact_pos + CONTACT_RELIEF_MM
    prev_error = None

    pos = mark10.position_stable()
    for i in range(1, MAX_CONTROL_ITERS + 1):
        time.sleep(CONTROL_SETTLE_S)
        F_m, F_s, F_n = force.sample_average(CONTROL_SAMPLE_S)
        pos = mark10.position_stable()
        d_actual = contact_pos - pos
        error = target_F_N - F_m
        tol = force_tolerance(target_F_N)

        log.write(f"[trial {trial_idx} target {step_idx}] iter={i} "
                  f"targetF={target_F_N:.4f} F={F_m:.4f} "
                  f"err={error:.4f} d={d_actual:.4f} pos={pos:.4f}\n")
        log.flush()

        if abs(F_m) >= F_HARD_LIMIT_N:
            return (False, "hard_limit", pos, d_actual, F_m, F_s, F_n, i)

        if abs(error) <= tol:
            return (True, "reached", pos, d_actual, F_m, F_s, F_n, i)

        if error > 0 and d_actual >= D_SOFT_LIMIT_MM:
            return (False, "d_soft_limit", pos, d_actual, F_m, F_s, F_n, i)

        sign_reversed = (
            prev_error is not None
            and (error > 0) != (prev_error > 0)
        )
        step_mm = choose_step_mm(error, sign_reversed)
        prev_error = error

        if error > 0:
            next_pos = pos - step_mm
        else:
            next_pos = pos + step_mm

        next_pos = min(max(next_pos, lower_pos), upper_pos)

        try:
            pos = mark10.move_to(next_pos, tolerance_mm=CONTROL_MOVE_TOL_MM)
        except Mark10Error as exc:
            log.write(f"[trial {trial_idx} target {step_idx}] "
                      f"Mark10 error: {exc}\n")
            log.flush()
            return (False, f"mark10_error:{exc}", pos, d_actual,
                    F_m, F_s, F_n, i)

    return (False, "max_iters", pos, contact_pos - pos,
            F_m, F_s, F_n, MAX_CONTROL_ITERS)


def measure_force_targets(mark10, force, mlx_ser, contact_pos, B0,
                          csv_writer, trial_idx, log):
    print(f"\n  PHASE B FORCE TARGETS (trial {trial_idx}): "
          f"{len(F_TARGETS)} F-points")

    for k, F_tgt in enumerate(F_TARGETS, 1):
        reached, status, pos, d_control, F_ctrl, F_ctrl_s, F_ctrl_n, n_iter = (
            approach_force_target(
                mark10, force, contact_pos, F_tgt, trial_idx, k, log
            )
        )

        time.sleep(PLATEAU_SETTLE_S)
        F_m, F_s, F_n = force.sample_average(PLATEAU_RECORD_S)
        try:
            (mbx, mby, mbz), (sbx, sby, sbz), n_mlx = require_mlx_sample(
                mlx_ser, PLATEAU_MLX_S,
                f"trial {trial_idx} F_target={F_tgt:.3f}", log=log)
        except MlxNoDataError as exc:
            print("    !! MLX stream has no valid B samples; aborting trial.")
            for line in str(exc).splitlines():
                print(f"       {line}")
            return False

        try:
            actual_pos = mark10.position_stable()
        except Mark10Error:
            actual_pos = pos
        d_actual = contact_pos - actual_pos
        b_mag = bmag(mbx, mby, mbz)
        dbx = mbx - B0[0] if B0 else float("nan")
        dby = mby - B0[1] if B0 else float("nan")
        dbz = mbz - B0[2] if B0 else float("nan")
        F_err = F_m - F_tgt
        final_reached = abs(F_err) <= force_tolerance(F_tgt)
        final_status = status
        if final_reached and not reached:
            final_status = "reached_after_plateau"
        elif reached and not final_reached:
            final_status = "drifted_after_reach"
        over_limit = abs(F_m) >= F_HARD_LIMIT_N

        print(f"    F_tgt={F_tgt:5.3f} N  F_act={F_m:+7.3f} N "
              f"(err={F_err*1000:+6.1f} mN, {final_status}, it={n_iter:02d})  "
              f"d={d_actual:5.3f} mm   |B|={b_mag:.0f} uT   nB={n_mlx}")

        csv_writer(
            f"{trial_idx},force_loading,{k},{F_tgt:.5f},{F_m:.5f},"
            f"{F_err:.5f},{F_s:.5f},{F_n},{n_mlx},"
            f"{actual_pos:.4f},{d_actual:.4f},{int(final_reached)},"
            f"{final_status},{n_iter},"
            f"{mbx:.4f},{mby:.4f},{mbz:.4f},"
            f"{sbx:.4f},{sby:.4f},{sbz:.4f},"
            f"{dbx:.4f},{dby:.4f},{dbz:.4f},{b_mag:.4f}\n"
        )
        log.write(f"[trial {trial_idx} F_target={F_tgt:.3f}] "
                  f"status={final_status} reached={final_reached} it={n_iter} "
                  f"F={F_m:.4f} err={F_err:.4f} d={d_actual:.4f} "
                  f"Bmag={b_mag:.2f}\n")
        log.flush()

        if over_limit:
            print(f"    !! F = {F_m:+.3f} N exceeded HARD_LIMIT "
                  f"({F_HARD_LIMIT_N} N), aborting trial after recording point")
            return False

        if status in ("hard_limit", "d_soft_limit") or status.startswith(
            "mark10_error:"
        ):
            print(f"    !! force target loop stopped by {status}; "
                  "aborting remaining targets for this trial")
            return False

    return True


# ============================================================================
# Main
# ============================================================================

def main():
    OUTPUT_ROOT.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = OUTPUT_ROOT / f"session_{ts}"
    session_dir.mkdir(parents=True)
    log_path = session_dir / "run_log.txt"

    est_per_target_s = 18.0
    est_per_trial_min = (
        (APPROACH_MAX_DESCENT_MM / APPROACH_STEP_MM) *
        (APPROACH_SETTLE_S + APPROACH_SAMPLE_S + 1.0) / 60.0
        + len(F_TARGETS) * est_per_target_s / 60.0
        + INTER_TRIAL_REST_S / 60.0
    )

    print("\n" + "=" * 60)
    print("  Stage H -- pseudo force-control B-F curve (plateau mode)")
    print("=" * 60)
    print(f"  session          : {session_dir.name}")
    print(f"  trials           : {N_TRIALS}")
    print(f"  F targets        : {F_TARGETS} N")
    print(f"  F_target_max     : {F_TARGET_MAX_N:.2f} N")
    print(f"  D_SOFT_LIMIT     : {D_SOFT_LIMIT_MM:.2f} mm")
    print(f"  F_HARD_LIMIT     : {F_HARD_LIMIT_N:.2f} N")
    print(f"  force tolerance  : max({FORCE_TOL_N*1000:.0f} mN, "
          f"{FORCE_TOL_FRAC*100:.1f}% target)")
    print(f"  est per trial    : ~{est_per_trial_min:.1f} min  "
          f"(total ~{N_TRIALS * est_per_trial_min:.0f} min)")
    print()
    print("Pre-flight:")
    print("  [ ] Sample (bag + magnet) on MLX, same setup as Stage F")
    print("  [ ] Mark-10 at start position (3-5 mm air gap above bag)")
    print("  [ ] EasyMESUR Home -> PC Control ACTIVE")
    print("  [ ] Arduino IDE Serial Monitor on UNO CLOSED")
    print("  [ ] QT Py / MLX already running circuitpython/code.py")
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
        sys.exit(f"\nMLX90393 required for Stage H. {exc}")

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
    except Exception as exc:
        mlx_ser.close()
        mark10.close()
        sys.exit(f"\nForce sensor required for Stage H. {exc}")

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
    log.write(f"# Stage H session {ts}\n")
    log.write(f"# F_TARGETS={F_TARGETS}\n")
    log.write(f"# F_TARGET_MAX_N={F_TARGET_MAX_N}, "
              f"D_SOFT_LIMIT_MM={D_SOFT_LIMIT_MM}\n")
    log.write(f"# live_tare_N={force.live_tare_N:.5f}\n")
    log.write(f"# B0={B0}\n")
    log.write(f"# trial_start_pos={trial_start_pos:.4f}\n")
    log.flush()

    csv_header = (
        "trial,phase,step,F_target_N,F_mean_N,F_error_N,F_std_N,"
        "F_n_samples,B_n_samples,mark10_pos_mm,d_actual_mm,"
        "target_reached,status,control_iters,"
        "mean_Bx_uT,mean_By_uT,mean_Bz_uT,"
        "sigma_Bx_uT,sigma_By_uT,sigma_Bz_uT,"
        "delta_Bx_uT,delta_By_uT,delta_Bz_uT,Bmag_uT\n"
    )

    try:
        for trial in range(1, N_TRIALS + 1):
            print("\n" + "=" * 60)
            print(f"  TRIAL {trial}/{N_TRIALS}")
            print("=" * 60)

            csv_path = session_dir / f"H_force_control_rep{trial}.csv"
            f_csv = open(csv_path, "w", encoding="utf-8")
            f_csv.write(csv_header)
            f_csv.flush()
            csv_writer = lambda row: (f_csv.write(row), f_csv.flush())

            try:
                contact_pos = find_contact(mark10, force, trial, log)
                if contact_pos is None:
                    print(f"  ! contact not found, aborting trial {trial}")
                    f_csv.close()
                    continue

                ok = measure_force_targets(
                    mark10, force, mlx_ser, contact_pos, B0,
                    csv_writer, trial, log)
                if not ok:
                    print(f"  ! force-control sweep incomplete for trial {trial}")
            finally:
                f_csv.close()

            print(f"\n  PHASE C: retracting to start ({trial_start_pos:+.3f} mm)")
            try:
                back_pos = mark10.move_to(trial_start_pos)
                print(f"    back at {back_pos:+.3f} mm")
            except Mark10Error as exc:
                print(f"  ! retract error: {exc}")

            if trial < N_TRIALS:
                print(f"\n  resting {INTER_TRIAL_REST_S:.0f} s for sample "
                      "recovery ...")
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

    print(f"\n=== Stage H done. Files in: {session_dir}")
    for trial in range(1, N_TRIALS + 1):
        p = session_dir / f"H_force_control_rep{trial}.csv"
        if p.exists():
            print(f"  {p.name}")
    print(f"  {log_path.name}")
    print("\nNext: plot force-control B-F and compare with Stage E/F.")


if __name__ == "__main__":
    main()
