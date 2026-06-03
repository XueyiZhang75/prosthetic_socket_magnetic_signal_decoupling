"""Stage D -- Contact point + safety-range identification.

Determines the contact point (d=0 by definition) and a conservative
F_max / d_max for the soft magnetic sample, by carefully descending the
Mark-10 crosshead in small steps while monitoring force in real time.

Three phases:
    PHASE A (approach)
        Descend in APPROACH_STEP_MM steps until the force signal shows a
        clear change point: positive force rise above the no-contact rolling
        baseline and a significant step-to-step dF/dd slope. The operator then
        confirms visual contact before d=0 is accepted.
        The Mark-10 position at that moment becomes the contact reference;
        compression depth d_mm is measured from there.

    PHASE B (probe / mapping)
        Step further down in PROBE_STEP_MM increments, holding for
        PROBE_HOLD_S at each step to sample F (and optionally B). Stop
        when ANY of these conditions trip:
            - physical lower limit is reached (normal stop for this setup)
            - depth reaches PROBE_MAX_DEPTH_MM (software backstop)
            - |F| exceeds F_HARD_LIMIT_N      (panic stop)
            - |B| exceeds MLX_SATURATION_UT   (MLX saturating, optional)
            - Ctrl+C                          (interactive abort)

    PHASE C (retract)
        Move crosshead back up to the original start position.

Outputs (under decouple_data/session_<ts>/):
    D_safety_range.csv     one row per step (phase, mark10_pos, d, F, B...)
    D_summary.txt          contact point + recommended F_max, d_max
    run_log.txt            timestamped detailed log

Pre-flight:
    - EasyMESUR touchscreen: Home -> PC Control ACTIVE
    - Force sensor live-tared with the FINAL clamp + fixture installed
    - Magnet/sample positioned so contact will happen between the start
      position and the configured physical lower-limit position
    - Physical Mark-10 lower limit switch set to the maximum safe compression
      for this sample/head setup (not to a destructive hard stop)
"""

import csv
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
MARK10_SPEED_MM_PER_MIN = 200.0   # downward is firmware-capped to ~25 mm/min

# --- MLX90393 (optional) ---
MLX_ENABLED = True
MLX_PORT = None                   # None -> auto-detect
MLX_BAUD = 115200
MLX_SATURATION_UT = 28000         # |B| above which we assume saturation risk

# --- Force / safety ---
F_CONTACT_N = 0.080              # Required rise from no-contact baseline
CONTACT_BASELINE_WINDOW = 5      # Rolling no-contact points for baseline
CONTACT_BASELINE_MIN_STEPS = 3   # Need this many no-contact points first
CONTACT_STEP_DELTA_N = 0.015     # Required force jump from previous step
CONTACT_SLOPE_N_PER_MM = 0.12    # Required local dF/dd during approach
F_HARD_LIMIT_N = 8.0             # Emergency stop; lower limit is the planned endpoint
VISUAL_CONFIRM_CONTACT = False   # Accept algorithmic change point automatically

# --- Phase A: approach ---
APPROACH_STEP_MM = 0.1
APPROACH_SETTLE_S = 5           # Settle after each step (mech ringing)
APPROACH_SAMPLE_S = 1           # Force averaging per step
APPROACH_MAX_DESCENT_MM = 15.0    # Give up if no contact within this much

# --- Phase B: lower-limit F-d-B mapping ---
PROBE_STEP_MM = 0.1
PROBE_HOLD_S = 2.0                # Total per-step time: 30% settle + 70% sample
PROBE_STOP_MODE = "physical_limit"
PROBE_FORCE_MARKER_N = 2.2        # Report when crossed; does not stop mapping
PROBE_MAX_DEPTH_MM = 12.0         # Software backstop if lower limit is not reached
LOWER_LIMIT_POSITION_TOL_MM = 0.08
INTERACTIVE_PROBE = False         # Automatic mapping after contact is found

# --- Output ---
HERE = Path(__file__).parent
OUTPUT_ROOT = HERE / "decouple_data"


# ============================================================================
# Helpers
# ============================================================================

def quick_mlx_sample(ser, duration_s=0.5):
    """Read MLX for a short window; return (mean_Bx, mean_By, mean_Bz, n) in uT."""
    if ser is None:
        return float("nan"), float("nan"), float("nan"), 0
    ser.reset_input_buffer()
    bx, by, bz = [], [], []
    t_end = time.time() + duration_s
    while time.time() < t_end:
        line = ser.readline().decode(errors="ignore").strip()
        if not line or line.startswith("MLX90393") or line.startswith("t_ms"):
            continue
        parts = line.split(",")
        if len(parts) != 4:
            continue
        try:
            bx.append(int(parts[1]) / 1000.0)
            by.append(int(parts[2]) / 1000.0)
            bz.append(int(parts[3]) / 1000.0)
        except ValueError:
            continue
    if not bx:
        return float("nan"), float("nan"), float("nan"), 0
    return (statistics.mean(bx), statistics.mean(by), statistics.mean(bz),
            len(bx))


def bmag(bx, by, bz):
    try:
        return (bx ** 2 + by ** 2 + bz ** 2) ** 0.5
    except TypeError:
        return float("nan")


def probe_stop_reason(F_m, b_mag, d_compr, hit_physical_limit):
    """Return the probe stop reason for the current sample, or None."""
    if abs(F_m) >= F_HARD_LIMIT_N:
        return "F_hard_limit"
    if hit_physical_limit:
        return "physical_lower_limit"
    if b_mag == b_mag and b_mag > MLX_SATURATION_UT:
        return "B_saturation"
    if (
        PROBE_STOP_MODE == "force_target"
        and PROBE_FORCE_MARKER_N is not None
        and abs(F_m) >= PROBE_FORCE_MARKER_N
    ):
        return "F_target_reached"
    if d_compr >= PROBE_MAX_DEPTH_MM:
        if PROBE_STOP_MODE == "physical_limit":
            return "depth_backstop"
        return "depth_limit"
    return None


def fmt_row(phase, step, m10_pos, d_compr, F_m, F_s, F_n,
            mbx, mby, mbz, b_mag, note):
    return (f"{phase},{step},{m10_pos:.4f},{d_compr:.4f},"
            f"{F_m:.5f},{F_s:.5f},{F_n},"
            f"{mbx:.4f},{mby:.4f},{mbz:.4f},{b_mag:.4f},"
            f"{note}\n")


# ============================================================================
# Phase A: approach
# ============================================================================

def phase_a_approach(mark10, force, mlx_ser, csv_writer, log):
    """Step down until a force change point and visual contact agree.

    Returns:
        (contact_pos_mm, F_at_contact_N, data_rows)
        contact_pos_mm = None if no contact within APPROACH_MAX_DESCENT_MM
    """
    print("\n" + "=" * 60)
    print("PHASE A: APPROACH UNTIL CONTACT")
    print("=" * 60)
    print(f"  step size      : {APPROACH_STEP_MM:.2f} mm")
    print(f"  max descent    : {APPROACH_MAX_DESCENT_MM:.1f} mm")
    print(f"  dF baseline thr: {F_CONTACT_N * 1000:.0f} mN")
    print(f"  dF step thr    : {CONTACT_STEP_DELTA_N * 1000:.0f} mN")
    print(f"  dF/dd slope thr: {CONTACT_SLOPE_N_PER_MM:.2f} N/mm")
    print(f"  F hard limit   : {F_HARD_LIMIT_N:.1f} N")
    print()
    input("  Press Enter to begin approach (Ctrl+C aborts) ... ")

    start_pos = mark10.position()
    contact_pos = None
    F_at_contact = float("nan")
    step = 0
    approach_history = []  # list of (descent_mm, F_mean_N), no-contact points

    try:
        while True:
            target_pos = start_pos - (step + 1) * APPROACH_STEP_MM
            descent = abs(target_pos - start_pos)
            if descent > APPROACH_MAX_DESCENT_MM:
                print(f"\n  ! No contact within {APPROACH_MAX_DESCENT_MM:.1f} mm.")
                print(f"    Stopping. Move sample closer and re-run.")
                return None, float("nan"), step

            # Move (treat Mark-10 errors as "hit physical limit / no contact")
            try:
                mark10.move_to(target_pos)
            except Mark10Error as exc:
                print(f"\n  ! Mark-10 stopped before reaching target ({exc}).")
                print(f"    Likely hit the physical lower limit switch "
                      f"after descent {abs(start_pos - target_pos):.2f} mm.")
                print(f"    Treating as 'no contact found within physical range'.")
                return None, float("nan"), step
            time.sleep(APPROACH_SETTLE_S)

            # Sample force
            F_m, F_s, F_n = force.sample_average(APPROACH_SAMPLE_S)

            # Sample MLX briefly (optional)
            mbx, mby, mbz, _ = quick_mlx_sample(mlx_ser, 0.3) if mlx_ser else \
                (float("nan"),) * 3 + (0,)
            b_mag = bmag(mbx, mby, mbz)

            actual_pos = mark10.position()
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

            print(f"  step {step+1:>3d}  descent = {descent_actual:5.2f} mm  "
                  f"F = {F_m * 1000:+7.2f} +/- {F_s * 1000:5.2f} mN  "
                  f"dF_base = {delta_from_baseline_N * 1000:+7.2f} mN  "
                  f"dF_step = {step_delta_N * 1000:+7.2f} mN  "
                  f"slope = {slope_N_per_mm:+.3f} N/mm" +
                  (f"  |B| = {b_mag:.0f} uT" if mlx_ser else ""))

            note = (
                f"baseline_N={baseline_N:.5f};"
                f"dF_base_N={delta_from_baseline_N:.5f};"
                f"dF_step_N={step_delta_N:.5f};"
                f"slope_N_per_mm={slope_N_per_mm:.5f};"
                f"change_point={is_change_point}"
            )
            csv_writer(fmt_row("approach", step + 1, actual_pos,
                               float("nan"),  # d_compr undefined until contact
                               F_m, F_s, F_n, mbx, mby, mbz, b_mag, note))

            # Panic check
            if abs(F_m) >= F_HARD_LIMIT_N:
                print(f"\n  !! PANIC: |F| ({F_m:.3f} N) exceeded F_HARD_LIMIT "
                      f"({F_HARD_LIMIT_N:.1f} N). Stopping.")
                return None, F_m, step + 1

            # Contact candidate. Compression sign was checked after reinstall:
            # positive force means the stamp head is pressing the sample.
            if is_change_point:
                if VISUAL_CONFIRM_CONTACT:
                    print(f"\n  ? CONTACT CHANGE-POINT CANDIDATE")
                    print(f"      F        = {F_m:+.4f} N")
                    print(f"      baseline = {baseline_N:+.4f} N")
                    print(f"      dF_base  = {delta_from_baseline_N:+.4f} N")
                    print(f"      dF_step  = {step_delta_N:+.4f} N")
                    print(f"      slope    = {slope_N_per_mm:+.3f} N/mm")
                    print(f"      descent  = {descent_actual:.2f} mm")
                    ans = input("    Is there NO visible gap and is the stamp "
                                "face touching level? [Enter] yes, "
                                "'n' continue approach, 'q' abort: ") \
                        .strip().lower()
                    if ans == "q":
                        print("  ! user abort at contact confirmation")
                        log.write(f"CONTACT_CANDIDATE_ABORT step={step+1} "
                                  f"pos={actual_pos:.4f} F={F_m:.4f} "
                                  f"dF_base={delta_from_baseline_N:.4f} "
                                  f"slope={slope_N_per_mm:.4f}\n")
                        log.flush()
                        return None, float("nan"), step + 1
                    if ans == "n":
                        print("    continuing approach; candidate rejected "
                              "by visual check.")
                        log.write(f"CONTACT_CANDIDATE_REJECTED step={step+1} "
                                  f"pos={actual_pos:.4f} F={F_m:.4f} "
                                  f"dF_base={delta_from_baseline_N:.4f} "
                                  f"slope={slope_N_per_mm:.4f}\n")
                        log.flush()
                        approach_history.append((descent_actual, F_m))
                        step += 1
                        continue
                else:
                    print(f"\n  *** AUTO CONTACT CHANGE-POINT")
                    print(f"      F        = {F_m:+.4f} N")
                    print(f"      baseline = {baseline_N:+.4f} N")
                    print(f"      dF_base  = {delta_from_baseline_N:+.4f} N")
                    print(f"      dF_step  = {step_delta_N:+.4f} N")
                    print(f"      slope    = {slope_N_per_mm:+.3f} N/mm")
                    print(f"      descent  = {descent_actual:.2f} mm")

                contact_pos = actual_pos
                F_at_contact = F_m
                print(f"\n  *** CONTACT at Mark-10 pos = {actual_pos:+.3f} mm "
                      f"(descent {descent_actual:.2f} mm from start)")
                print(f"      F at contact = {F_m:+.4f} N")
                log.write(f"CONTACT step={step+1} pos={actual_pos:.4f} "
                          f"F={F_m:.4f} baseline={baseline_N:.4f} "
                          f"dF_base={delta_from_baseline_N:.4f} "
                          f"dF_step={step_delta_N:.4f} "
                          f"slope={slope_N_per_mm:.4f}\n")
                log.flush()
                return contact_pos, F_at_contact, step + 1

            approach_history.append((descent_actual, F_m))
            step += 1

    except KeyboardInterrupt:
        print("\n  ! user abort during approach")
        return None, float("nan"), step


# ============================================================================
# Phase B: probe
# ============================================================================

def phase_b_probe(mark10, force, mlx_ser, contact_pos, csv_writer, log):
    """Step deeper than contact, recording F (and B) at each step.

    Returns:
        (F_max_observed, d_max_observed_mm, abort_reason)
    """
    print("\n" + "=" * 60)
    print("PHASE B: LOWER-LIMIT F-d-B MAPPING")
    print("=" * 60)
    print(f"  step size      : {PROBE_STEP_MM:.2f} mm")
    print(f"  hold per step  : {PROBE_HOLD_S:.1f} s "
          f"({PROBE_HOLD_S * 0.3:.1f} settle + {PROBE_HOLD_S * 0.7:.1f} sample)")
    print(f"  stop mode      : {PROBE_STOP_MODE}")
    print(f"  force marker   : {PROBE_FORCE_MARKER_N:.1f} N (report only)")
    print(f"  depth backstop : {PROBE_MAX_DEPTH_MM:.1f} mm from contact")
    print(f"  F hard limit   : {F_HARD_LIMIT_N:.1f} N")
    print(f"  interactive    : {INTERACTIVE_PROBE}")
    print()

    if INTERACTIVE_PROBE:
        ans = input("  Phase A found contact. Start Phase B? "
                    "[Enter] yes, 'q' abort: ").strip().lower()
        if ans == "q":
            return float("nan"), 0.0, "user_abort_before_probe"
    else:
        print("  automatic mapping begins now; Ctrl+C aborts.")

    F_max_obs = 0.0
    d_max_obs = 0.0
    abort_reason = "normal_done"
    force_marker_reported = False

    try:
        for step in range(1, int(PROBE_MAX_DEPTH_MM / PROBE_STEP_MM) + 1):
            target_pos = contact_pos - step * PROBE_STEP_MM

            # Move
            hit_physical_limit = False
            move_note = ""
            try:
                mark10.move_to(target_pos)
            except Mark10Error as exc:
                hit_physical_limit = True
                move_note = f"physical_lower_limit_or_motion_stop: {exc}"
                print("\n  ! Mark-10 stopped before reaching the requested "
                      "probe target.")
                print("    Treating this as the configured physical lower "
                      "limit / maximum safe compression for this setup.")
            time.sleep(PROBE_HOLD_S * 0.3)

            # Sample force during the rest of the hold
            F_m, F_s, F_n = force.sample_average(PROBE_HOLD_S * 0.7)

            # Sample MLX during the same period (rough — sequential, not parallel)
            mbx, mby, mbz, _ = quick_mlx_sample(mlx_ser, 0.5) if mlx_ser else \
                (float("nan"), float("nan"), float("nan"), 0)
            b_mag = bmag(mbx, mby, mbz)

            actual_pos = mark10.position()
            d_compr = contact_pos - actual_pos
            target_shortfall_mm = actual_pos - target_pos
            if target_shortfall_mm > LOWER_LIMIT_POSITION_TOL_MM:
                hit_physical_limit = True
                shortfall_note = (
                    f"target_shortfall_mm={target_shortfall_mm:.4f};"
                    "physical_lower_limit_inferred"
                )
                move_note = f"{move_note};{shortfall_note}" if move_note else \
                    shortfall_note

            F_max_obs = max(F_max_obs, abs(F_m))
            d_max_obs = max(d_max_obs, d_compr)

            mlx_str = f"  |B| = {b_mag:.0f} uT" if mlx_ser else ""
            print(f"\n  step {step:>3d}  d = {d_compr:+5.3f} mm  "
                  f"F = {F_m:+7.4f} +/- {F_s * 1000:5.2f} mN" +
                  f"  target_shortfall = {target_shortfall_mm:+.3f} mm" +
                  mlx_str)

            csv_writer(fmt_row("probe", step, actual_pos, d_compr,
                               F_m, F_s, F_n, mbx, mby, mbz, b_mag,
                               move_note))

            if (
                not force_marker_reported
                and PROBE_FORCE_MARKER_N is not None
                and abs(F_m) >= PROBE_FORCE_MARKER_N
            ):
                print(f"  crossed force marker ({PROBE_FORCE_MARKER_N:.1f} N); "
                      "continuing toward lower limit.")
                log.write(f"FORCE_MARKER step={step} d={d_compr:.4f} "
                          f"F={F_m:.4f}\n")
                log.flush()
                force_marker_reported = True

            stop_reason = probe_stop_reason(
                F_m=F_m,
                b_mag=b_mag,
                d_compr=d_compr,
                hit_physical_limit=hit_physical_limit,
            )
            if stop_reason is not None:
                abort_reason = stop_reason
                if stop_reason == "F_hard_limit":
                    print(f"  !! PANIC: |F| exceeded F_HARD_LIMIT")
                elif stop_reason == "physical_lower_limit":
                    print("  reached physical lower limit / maximum safe "
                          "compression endpoint")
                elif stop_reason == "B_saturation":
                    print(f"  ! |B| approaching saturation ({b_mag:.0f} > "
                          f"{MLX_SATURATION_UT:.0f} uT)")
                elif stop_reason == "F_target_reached":
                    print(f"  reached force marker ({PROBE_FORCE_MARKER_N:.1f} N)")
                elif stop_reason == "depth_backstop":
                    print(f"  reached software depth backstop "
                          f"({PROBE_MAX_DEPTH_MM:.1f} mm)")
                else:
                    print(f"  stopping probe: {stop_reason}")
                break

            # Interactive confirmation between steps
            if INTERACTIVE_PROBE:
                ans = input("    next step? [Enter] yes, 'q' stop here: ") \
                    .strip().lower()
                if ans == "q":
                    abort_reason = "user_stop"
                    break

    except KeyboardInterrupt:
        print("\n  ! user abort during probe")
        abort_reason = "user_keyboard_interrupt"

    return F_max_obs, d_max_obs, abort_reason


# ============================================================================
# Main
# ============================================================================

def main():
    OUTPUT_ROOT.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = OUTPUT_ROOT / f"session_{ts}"
    session_dir.mkdir(parents=True)
    csv_path = session_dir / "D_safety_range.csv"
    summary_path = session_dir / "D_summary.txt"
    log_path = session_dir / "run_log.txt"

    print("\n=== Stage D: contact point + safety range ===")
    print(f"  session   : {session_dir.name}")
    print(f"  outputs   : {csv_path.name}, {summary_path.name}\n")
    print("Pre-flight checklist:")
    print("  [ ] EasyMESUR touchscreen: Home -> PC Control ACTIVE")
    print("  [ ] uno_force.ino uploaded with calibrated constants")
    print("  [ ] Arduino IDE Serial Monitor on UNO CLOSED")
    print("  [ ] Force sensor mounted in FINAL experimental orientation")
    print("  [ ] Sample placed under crosshead, with magnet on crosshead")
    print(f"  [ ] Start position is above the sample; contact should occur "
          f"within {APPROACH_MAX_DESCENT_MM:.0f} mm")
    print("  [ ] Mark-10 PHYSICAL lower limit is set to the maximum safe "
          "compression/depth, not a destructive hard stop")
    print()
    try:
        input("Press Enter to start ... ")
    except KeyboardInterrupt:
        print("\nAborted before start.")
        return

    # --- Mark-10 ---
    print("\nOpening Mark-10 ...")
    try:
        mark10 = Mark10(MARK10_PORT, MARK10_BAUD,
                        speed_mm_per_min=MARK10_SPEED_MM_PER_MIN)
    except Mark10Error as exc:
        sys.exit(f"\n{exc}")
    print(f"  Mark-10 ready, zero set at current position")

    # --- Force ---
    print("Opening UNO_force ...")
    try:
        force = ForceReader(find_force_port())
        force.live_tare(duration_s=2.0)
    except Exception as exc:
        mark10.close()
        sys.exit(f"\nForce sensor required for Stage D. {exc}")

    # --- MLX (optional) ---
    mlx_ser = None
    if MLX_ENABLED:
        try:
            mlx_port = MLX_PORT or find_mlx_port()
            print(f"Opening MLX90393 on {mlx_port} ...")
            mlx_ser = serial.Serial(mlx_port, MLX_BAUD, timeout=0.5)
            time.sleep(1.0)
            print("  MLX90393 stream connected\n")
        except Exception as exc:
            print(f"  ! MLX unavailable: {exc}")
            print("  ! Continuing without MLX saturation check\n")
            mlx_ser = None

    # --- Open output files ---
    f_csv = open(csv_path, "w", encoding="utf-8")
    f_csv.write("phase,step,mark10_pos_mm,d_compression_mm,"
                "F_mean_N,F_std_N,F_n_samples,"
                "mean_Bx_uT,mean_By_uT,mean_Bz_uT,Bmag_uT,note\n")
    f_csv.flush()
    csv_writer = lambda row: (f_csv.write(row), f_csv.flush())

    log = open(log_path, "w", encoding="utf-8")
    log.write(f"# Stage D session {ts}\n")
    log.write(f"# live_tare_N = {force.live_tare_N:.5f}\n")
    log.write(f"# APPROACH_STEP_MM={APPROACH_STEP_MM}, F_CONTACT_N={F_CONTACT_N}, "
              f"F_HARD_LIMIT_N={F_HARD_LIMIT_N}\n")
    log.write(f"# CONTACT_BASELINE_WINDOW={CONTACT_BASELINE_WINDOW}, "
              f"CONTACT_BASELINE_MIN_STEPS={CONTACT_BASELINE_MIN_STEPS}, "
              f"CONTACT_STEP_DELTA_N={CONTACT_STEP_DELTA_N}, "
              f"CONTACT_SLOPE_N_PER_MM={CONTACT_SLOPE_N_PER_MM}\n")
    log.write(f"# PROBE_STEP_MM={PROBE_STEP_MM}, "
              f"PROBE_STOP_MODE={PROBE_STOP_MODE}, "
              f"PROBE_FORCE_MARKER_N={PROBE_FORCE_MARKER_N}, "
              f"PROBE_MAX_DEPTH_MM={PROBE_MAX_DEPTH_MM}, "
              f"LOWER_LIMIT_POSITION_TOL_MM={LOWER_LIMIT_POSITION_TOL_MM}\n")
    log.flush()

    start_pos = mark10.position()
    contact_pos = None
    F_at_contact = float("nan")
    F_max_obs = 0.0
    d_max_obs = 0.0
    abort_reason = "no_contact"

    try:
        # --- Phase A ---
        contact_pos, F_at_contact, a_steps = phase_a_approach(
            mark10, force, mlx_ser, csv_writer, log)

        # --- Phase B (only if contact found) ---
        if contact_pos is not None:
            F_max_obs, d_max_obs, abort_reason = phase_b_probe(
                mark10, force, mlx_ser, contact_pos, csv_writer, log)
        else:
            print("\nSkipping Phase B because no contact was found.")
            abort_reason = "no_contact"

    finally:
        # --- Phase C: always retract to start ---
        print("\n" + "=" * 60)
        print("PHASE C: RETRACT TO START")
        print("=" * 60)
        try:
            mark10.move_to(start_pos)
            final_pos = mark10.position()
            print(f"  back at Mark-10 pos = {final_pos:+.3f} mm "
                  f"(started at {start_pos:+.3f})")
        except Exception as exc:
            print(f"  ! retract failed: {exc}")

        # --- Close ---
        f_csv.close()
        log.write(f"\nfinal: contact={contact_pos} F_at_contact={F_at_contact} "
                  f"F_max_obs={F_max_obs} d_max_obs={d_max_obs} "
                  f"abort_reason={abort_reason}\n")
        log.close()
        if mlx_ser is not None:
            mlx_ser.close()
        force.close()
        mark10.close()

    # --- Summary ---
    if contact_pos is None:
        rec_F_max = float("nan")
        rec_d_max = float("nan")
        verdict = "INCOMPLETE: no contact found, no safety range determined."
    else:
        rec_F_max = round(0.8 * F_max_obs, 3)
        rec_d_max = round(0.9 * d_max_obs, 3)
        verdict = "OK" if abort_reason in ("F_target_reached", "depth_limit",
                                            "depth_backstop",
                                            "physical_lower_limit",
                                            "normal_done") else \
                  "PARTIAL (review log)"

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"Stage D safety-range summary\n")
        f.write(f"session: {ts}\n\n")
        f.write(f"start Mark-10 position  : {start_pos:+.4f} mm\n")
        f.write(f"contact Mark-10 position: ")
        f.write(f"{contact_pos:+.4f} mm\n" if contact_pos is not None
                else "(not found)\n")
        f.write(f"contact F               : {F_at_contact:+.4f} N\n\n")
        f.write(f"F_max observed in probe : {F_max_obs:+.4f} N\n")
        f.write(f"d_max observed in probe : {d_max_obs:+.4f} mm\n\n")
        f.write(f"abort_reason            : {abort_reason}\n")
        f.write(f"verdict                 : {verdict}\n\n")
        f.write(f"RECOMMENDED for later stages (conservative):\n")
        f.write(f"  F_max = {rec_F_max} N    (= 0.8 * observed peak)\n")
        f.write(f"  d_max = {rec_d_max} mm   (= 0.9 * observed peak)\n")

    print(f"\n=== Stage D done.  Outputs:\n"
          f"  {csv_path}\n  {summary_path}\n  {log_path}")
    if contact_pos is not None:
        print(f"\n  contact F          = {F_at_contact:+.4f} N")
        print(f"  observed F_max     = {F_max_obs:+.4f} N")
        print(f"  observed d_max     = {d_max_obs:+.4f} mm")
        print(f"  RECOMMENDED F_max  = {rec_F_max} N")
        print(f"  RECOMMENDED d_max  = {rec_d_max} mm")
        print(f"  abort reason       = {abort_reason}")
    else:
        print("\n  no contact found within APPROACH_MAX_DESCENT_MM.\n  "
              "Re-position sample closer and re-run.")


if __name__ == "__main__":
    main()
