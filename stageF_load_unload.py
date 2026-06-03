"""Stage F -- load-unload hysteresis curve, plateau mode.

For a soft magnetic sample whose F_max and d_max have been established
by Stage D / Stage E, this script sweeps the compression depth d from
0 -> d_max -> 0 in equal steps, recording F + B at every plateau, with
a phase tag of either "loading" (descending sweep) or "unloading"
(ascending sweep).

The main question Stage F answers: do the loading and unloading B-F
curves overlap, or is there a hysteresis loop? Overlap means the soft-
magnetic sample is mechanically + magnetically reversible. A loop means
there is path/state-dependent behaviour (viscoelastic / magnetic
remnant) that any single-valued model B = f(F) cannot capture.

Per trial:
  PHASE A: find contact (same logic as Stage E)
  PHASE B-down: visit d = 0, 0.1*d_max, ..., 1.0*d_max  (phase=loading)
  PHASE B-up:   visit d = 1.0*d_max, ..., 0.0          (phase=unloading)
  PHASE C: retract to trial start position
           wait INTER_TRIAL_REST_S for sample recovery

Tag convention: phase="loading" for descending, phase="unloading" for
ascending. Both d=d_max and d=0 are measured on both branches. This makes the
loop endpoints measured rather than visually inferred, which is important if
we want to discuss the loop shape rather than only branch separation.
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
MARK10_SPEED_MM_PER_MIN = 200.0   # downward firmware-capped to ~25 mm/min

# --- MLX90393 ---
MLX_PORT = None                   # None -> auto-detect
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
# d_max: reduced from Stage E's 4.48 because today's sample reaches
# F_HARD_LIMIT (2.5 N) around d=4.0 mm. At d=3.5 mm we measured ~1.5 N
# in Stage E trial 2, leaving ~1 N headroom for both directions.
D_MAX_MM = 3.5
N_D_POINTS = 11                   # 0, 0.1*d_max, ..., 1.0*d_max

# --- Contact detection (Phase A) ---
APPROACH_STEP_MM = 0.2
APPROACH_SETTLE_S = 2.0
APPROACH_SAMPLE_S = 0.5
APPROACH_MAX_DESCENT_MM = 15.0
F_CONTACT_N = 0.025

# --- Plateau measurement (Phase B) ---
PLATEAU_SETTLE_S = 1.0
PLATEAU_RECORD_S = 2.0
PLATEAU_MLX_S = 1.5

# --- Safety ---
F_HARD_LIMIT_N = 2.5

# --- Recovery ---
INTER_TRIAL_REST_S = 10.0

# --- Tare ---
LIVE_TARE_S = 2.0
TARE_PRE_SETTLE_S = 3.0

# --- Output ---
HERE = Path(__file__).parent
OUTPUT_ROOT = HERE / "decouple_data"

# --- Derived ---
D_DOWN = [round(i * D_MAX_MM / (N_D_POINTS - 1), 4)
          for i in range(N_D_POINTS)]
# Unloading: measure d_max again before ascending. The duplicate d_max point is
# not wasted: it is the actual start of the unloading branch and lets plots show
# a measured loop corner rather than an inferred connector.
D_UP = list(reversed(D_DOWN))


# ============================================================================
# Helpers
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
    ser.write(b"\x03")  # Ctrl-C: stop running code / enter REPL
    ser.flush()
    time.sleep(MLX_REBOOT_BREAK_S)
    ser.write(b"\x04")  # Ctrl-D: soft reboot and rerun code.py
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
# Phase B: sweep
# ============================================================================

def sweep_one_direction(mark10, force, mlx_ser, contact_pos, B0,
                        csv_writer, trial_idx, phase, d_sequence, log):
    """Step through `d_sequence`, record F + B at each plateau."""
    print(f"\n  PHASE B {phase.upper()} (trial {trial_idx}): "
          f"{len(d_sequence)} d-points")
    for k, d in enumerate(d_sequence, 1):
        target_pos = contact_pos - d

        try:
            actual_pos = mark10.move_to(target_pos)
        except Mark10Error as exc:
            print(f"    ! Mark-10 error at d={d}: {exc}")
            return False

        time.sleep(PLATEAU_SETTLE_S)
        F_m, F_s, F_n = force.sample_average(PLATEAU_RECORD_S)
        try:
            (mbx, mby, mbz), (sbx, sby, sbz), n_mlx = require_mlx_sample(
                mlx_ser, PLATEAU_MLX_S,
                f"trial {trial_idx} {phase} d={d:.3f}", log=log)
        except MlxNoDataError as exc:
            print("    !! MLX stream has no valid B samples; aborting trial.")
            for line in str(exc).splitlines():
                print(f"       {line}")
            return False

        d_actual = contact_pos - actual_pos
        b_mag = bmag(mbx, mby, mbz)
        dbx = mbx - B0[0] if B0 else float("nan")
        dby = mby - B0[1] if B0 else float("nan")
        dbz = mbz - B0[2] if B0 else float("nan")

        over_limit = abs(F_m) >= F_HARD_LIMIT_N

        print(f"    [{phase[:4]}] d_tgt={d:5.3f}  d_act={d_actual:5.3f} mm   "
              f"F = {F_m*1000:+8.2f} +/- {F_s*1000:5.2f} mN   "
              f"|B| = {b_mag:.0f} uT   nB={n_mlx}")

        csv_writer(
            f"{trial_idx},{phase},{k},{d:.4f},{d_actual:.4f},{actual_pos:.4f},"
            f"{F_m:.5f},{F_s:.5f},{F_n},{n_mlx},"
            f"{mbx:.4f},{mby:.4f},{mbz:.4f},"
            f"{sbx:.4f},{sby:.4f},{sbz:.4f},"
            f"{dbx:.4f},{dby:.4f},{dbz:.4f},{b_mag:.4f}\n"
        )
        log.write(f"[trial {trial_idx} {phase} d={d:.3f}] "
                  f"pos={actual_pos:.3f} F={F_m:.4f}+-{F_s:.4f} "
                  f"nB={n_mlx} Bx={mbx:.2f} By={mby:.2f} Bz={mbz:.2f}\n")
        log.flush()

        if over_limit:
            print(f"    !! d={d:.3f}: F = {F_m:+.3f} N exceeded HARD_LIMIT "
                  f"({F_HARD_LIMIT_N} N), aborting trial after recording point")
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

    per_point_s = (PLATEAU_SETTLE_S + PLATEAU_RECORD_S + PLATEAU_MLX_S
                   + D_MAX_MM / 25.0 * 60.0 / N_D_POINTS)
    n_points_per_trial = N_D_POINTS + len(D_UP)
    est_per_trial_min = (
        (APPROACH_MAX_DESCENT_MM / APPROACH_STEP_MM) *
        (APPROACH_SETTLE_S + APPROACH_SAMPLE_S + 1.0) / 60.0
        + n_points_per_trial * per_point_s / 60.0
        + INTER_TRIAL_REST_S / 60.0
    )

    print("\n" + "=" * 60)
    print("  Stage F -- load-unload hysteresis (plateau mode)")
    print("=" * 60)
    print(f"  session         : {session_dir.name}")
    print(f"  trials          : {N_TRIALS}")
    print(f"  loading d       : {D_DOWN}")
    print(f"  unloading d     : {D_UP}")
    print(f"  d_max           : {D_MAX_MM:.2f} mm  "
          f"(reduced from Stage E's 4.48 for full sweep headroom)")
    print(f"  plateau hold    : {PLATEAU_SETTLE_S + PLATEAU_RECORD_S:.1f} s")
    print(f"  F_HARD_LIMIT    : {F_HARD_LIMIT_N:.2f} N")
    print(f"  points per trial: {n_points_per_trial}")
    print(f"  est per trial   : ~{est_per_trial_min:.1f} min  "
          f"(total ~{N_TRIALS * est_per_trial_min:.0f} min)")
    print()
    print("Pre-flight:")
    print("  [ ] Sample (bag + magnet) on MLX, same setup as Stage E")
    print("  [ ] Mark-10 at start position (3-5 mm air gap above bag)")
    print("  [ ] EasyMESUR Home -> PC Control ACTIVE")
    print("  [ ] Arduino IDE Serial Monitor on UNO CLOSED")
    print("  [ ] Pre-cycle already done (or recent Stage E settled the sample)")
    print("  [ ] Physical lower limit switch still in place")
    print()
    try:
        input("Press Enter to start (Ctrl+C aborts) ... ")
    except KeyboardInterrupt:
        return

    # --- Open hardware ---
    # Open MLX first and keep COM6 open while Mark-10/UNO initialize. On the
    # QT Py M0, leaving the script printing with no host attached can make
    # USB-CDC go silent; holding the port open avoids that failure mode.
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
        sys.exit(f"\nMLX90393 required for Stage F. {exc}")

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
        sys.exit(f"\nForce sensor required for Stage F. {exc}")

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
    log.write(f"# Stage F session {ts}\n")
    log.write(f"# D_MAX_MM={D_MAX_MM}, N_D_POINTS={N_D_POINTS}, "
              f"N_TRIALS={N_TRIALS}\n")
    log.write(f"# D_DOWN={D_DOWN}\n")
    log.write(f"# D_UP={D_UP}\n")
    log.write(f"# live_tare_N={force.live_tare_N:.5f}\n")
    log.write(f"# B0={B0}\n")
    log.write(f"# trial_start_pos={trial_start_pos:.4f}\n")
    log.flush()

    csv_header = ("trial,phase,step,d_target_mm,d_actual_mm,mark10_pos_mm,"
                  "F_mean_N,F_std_N,F_n_samples,B_n_samples,"
                  "mean_Bx_uT,mean_By_uT,mean_Bz_uT,"
                  "sigma_Bx_uT,sigma_By_uT,sigma_Bz_uT,"
                  "delta_Bx_uT,delta_By_uT,delta_Bz_uT,Bmag_uT\n")

    try:
        for trial in range(1, N_TRIALS + 1):
            print("\n" + "=" * 60)
            print(f"  TRIAL {trial}/{N_TRIALS}")
            print("=" * 60)

            csv_path = session_dir / f"F_load_unload_rep{trial}.csv"
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

                # Loading sweep (d = 0 -> d_max)
                ok = sweep_one_direction(
                    mark10, force, mlx_ser, contact_pos, B0,
                    csv_writer, trial, "loading", D_DOWN, log)
                if not ok:
                    print(f"  ! loading sweep aborted, skipping unloading")
                    continue

                # Unloading sweep (d = d_max -> 0). The repeated d_max point
                # is intentional: it is the measured start of unloading.
                ok = sweep_one_direction(
                    mark10, force, mlx_ser, contact_pos, B0,
                    csv_writer, trial, "unloading", D_UP, log)
                if not ok:
                    print(f"  ! unloading sweep aborted, trial {trial} "
                          "incomplete")
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

    print(f"\n=== Stage F done. Files in: {session_dir}")
    for trial in range(1, N_TRIALS + 1):
        p = session_dir / f"F_load_unload_rep{trial}.csv"
        if p.exists():
            print(f"  {p.name}")
    print(f"  {log_path.name}")
    print("\nNext: plot loading vs unloading B-F curves to inspect hysteresis loop.")


if __name__ == "__main__":
    main()
