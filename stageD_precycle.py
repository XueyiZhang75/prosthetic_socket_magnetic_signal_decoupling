"""stageD_precycle.py -- Pre-cycle a fresh soft-magnetic sample.

Performs N_CYCLES uninstrumented compression-release cycles to "exercise"
the soft bag/magnet system so subsequent measurement runs (Stage E onwards)
have repeatable F vs d behaviour.

Why this matters: when a soft (silicone / cloth) magnetic composite is
compressed for the first time, the magnet particles redistribute, the
binder relaxes, and the bag's internal geometry settles. The first few
F vs d curves look quite different from the 10th onwards. Cycling 10-20
times first lets the sample reach a steady-state configuration.

No data files are saved. Force is monitored only for safety (panic stop
on overload). After this script, run Stage E for the real loading curve.

Pre-flight:
    - EasyMESUR touchscreen: Home -> PC Control ACTIVE
    - Force sensor + UNO ready (Arduino IDE Serial Monitor closed)
    - Bag on MLX, magnet inside, dry-run + Stage D already done
    - Mark-10 manually positioned at the SAME start position as Stage D
      (3-5 mm above bag top, dry-run confirmed)
    - Mark-10 PHYSICAL lower limit still set conservatively low
"""

import sys
import time

from mark10_control import Mark10, Mark10Error
from force_serial import find_force_port, ForceReader

# ============================================================================
# CONFIG
# ============================================================================

# --- Mark-10 ---
MARK10_PORT = "COM5"
MARK10_BAUD = 9600
MARK10_SPEED_MM_PER_MIN = 200.0   # downward firmware-capped to ~25 mm/min

# --- Cycle depth ---
# Total Mark-10 descent (from current start position) at the deepest point
# of each cycle. Read this from your Stage D run as:
#     CYCLE_DEPTH_MM = contact_descent + desired_compression
# E.g., Stage D found contact at descent 4.59 mm and probed up to 4.98 mm
# compression. A safe pre-cycle goes a bit shallower (say 3-4 mm compression),
# so CYCLE_DEPTH_MM = 4.59 + 3.5 = ~8.0 mm.
CYCLE_DEPTH_MM = 8.0

# --- Cycle timing ---
N_CYCLES = 15                     # 10-20 is typical for fresh soft samples
DEEP_HOLD_S = 1.5                 # Hold at bottom (let sample creep)
TOP_HOLD_S = 1.0                  # Pause at top (let sample recover)

# --- Safety ---
F_HARD_LIMIT_N = 2.5              # Panic stop if |F| exceeds this anywhere
F_PRE_CHECK_S = 0.5               # Force averaging before each descent
F_BOTTOM_CHECK_S = 1.0            # Force averaging at the deepest point
LIVE_TARE_S = 2.0


# ============================================================================
# Main
# ============================================================================

def main():
    est_cycle_s = (CYCLE_DEPTH_MM / 25.0 * 60.0      # descend at 25 mm/min
                   + DEEP_HOLD_S
                   + CYCLE_DEPTH_MM / 200.0 * 60.0   # retract at 200 mm/min
                   + TOP_HOLD_S
                   + F_PRE_CHECK_S + F_BOTTOM_CHECK_S)
    est_total_min = N_CYCLES * est_cycle_s / 60.0

    print("\n" + "=" * 60)
    print("  Stage D PRE-CYCLE")
    print("=" * 60)
    print(f"  cycles            : {N_CYCLES}")
    print(f"  depth per cycle   : {CYCLE_DEPTH_MM:.2f} mm below start")
    print(f"  hold at bottom    : {DEEP_HOLD_S:.1f} s")
    print(f"  hold at top       : {TOP_HOLD_S:.1f} s")
    print(f"  F panic threshold : {F_HARD_LIMIT_N:.2f} N")
    print(f"  est. total time   : ~{est_total_min:.1f} min")
    print()
    print("Pre-flight checklist:")
    print("  [ ] Bag on MLX, magnet inside (same setup as Stage D)")
    print("  [ ] Mark-10 manually at start position (3-5 mm above bag)")
    print("  [ ] EasyMESUR Home -> PC Control ACTIVE")
    print("  [ ] Arduino IDE Serial Monitor on UNO CLOSED")
    print("  [ ] Mark-10 physical lower limit switch still in place")
    print()
    try:
        input("Press Enter to start (Ctrl+C aborts) ... ")
    except KeyboardInterrupt:
        print("\nAborted before start.")
        return

    # --- Open hardware ---
    print("\nOpening Mark-10 ...")
    try:
        mark10 = Mark10(MARK10_PORT, MARK10_BAUD,
                        speed_mm_per_min=MARK10_SPEED_MM_PER_MIN)
    except Mark10Error as exc:
        sys.exit(f"\n{exc}")
    print("  Mark-10 ready")

    print("Opening UNO_force ...")
    try:
        force = ForceReader(find_force_port())
        force.live_tare(duration_s=LIVE_TARE_S)
    except Exception as exc:
        mark10.close()
        sys.exit(f"\nForce sensor required for pre-cycle (safety monitor). {exc}")

    start_pos = mark10.position()
    bottom_pos = start_pos - CYCLE_DEPTH_MM

    print(f"\n  start_pos  = {start_pos:+.3f} mm")
    print(f"  bottom_pos = {bottom_pos:+.3f} mm  (descent = {CYCLE_DEPTH_MM:.2f} mm)")

    cycle_count = 0
    t_session = time.time()
    abort_msg = "completed normally"

    try:
        for i in range(1, N_CYCLES + 1):
            t_cycle = time.time()
            print(f"\n[cycle {i:2d}/{N_CYCLES}]")

            # Safety check before moving
            F_pre, _, _ = force.sample_average(F_PRE_CHECK_S)
            if abs(F_pre) > F_HARD_LIMIT_N:
                abort_msg = (f"pre-check F = {F_pre:+.3f} N exceeded "
                             f"F_HARD_LIMIT ({F_HARD_LIMIT_N})")
                print(f"  !! {abort_msg}")
                break

            # Descend
            print(f"  descending to {bottom_pos:+.3f} mm ...",
                  end="", flush=True)
            try:
                mark10.move_to(bottom_pos)
            except Mark10Error as exc:
                abort_msg = f"Mark-10 descent error: {exc}"
                print(f"\n  !! {abort_msg}")
                print(f"     likely hit physical limit -- check setup")
                break
            actual_bot = mark10.position()
            print(f" arrived at {actual_bot:+.3f} mm")

            # Hold + force read at bottom
            time.sleep(0.3)   # short pre-sample settle
            F_bot, F_std, _ = force.sample_average(F_BOTTOM_CHECK_S)
            print(f"  bottom F = {F_bot:+.3f} N (+/- {F_std*1000:.1f} mN)")

            if abs(F_bot) > F_HARD_LIMIT_N:
                abort_msg = (f"bottom F = {F_bot:+.3f} N exceeded "
                             f"F_HARD_LIMIT ({F_HARD_LIMIT_N})")
                print(f"  !! {abort_msg}")
                # Try to retract before bailing
                try:
                    mark10.move_to(start_pos)
                except Exception:
                    pass
                break

            # Rest of the deep hold
            remaining = DEEP_HOLD_S - F_BOTTOM_CHECK_S - 0.3
            if remaining > 0:
                time.sleep(remaining)

            # Retract
            print(f"  retracting to {start_pos:+.3f} mm ...",
                  end="", flush=True)
            try:
                mark10.move_to(start_pos)
            except Mark10Error as exc:
                abort_msg = f"Mark-10 retract error: {exc}"
                print(f"\n  !! {abort_msg}")
                break
            actual_top = mark10.position()
            print(f" arrived at {actual_top:+.3f} mm")

            # Pause at top so the sample can rebound
            time.sleep(TOP_HOLD_S)

            cycle_count += 1
            elapsed = time.time() - t_session
            print(f"  cycle done in {time.time() - t_cycle:.1f}s, "
                  f"total elapsed {elapsed:.0f}s, "
                  f"ETA {(N_CYCLES - i) * est_cycle_s:.0f}s")

    except KeyboardInterrupt:
        abort_msg = "user Ctrl+C"
        print("\n\nUser abort. Will retract to start.")

    finally:
        # Always try to retract
        print("\nRetracting to start position ...")
        try:
            mark10.move_to(start_pos)
            final_pos = mark10.position()
            print(f"  back at {final_pos:+.3f} mm")
        except Exception as exc:
            print(f"  ! could not retract: {exc}")
        force.close()
        mark10.close()

    total_min = (time.time() - t_session) / 60.0
    print("\n" + "=" * 60)
    print(f"  Pre-cycle finished: {cycle_count}/{N_CYCLES} cycles completed")
    print(f"  Reason             : {abort_msg}")
    print(f"  Total time         : {total_min:.1f} min")
    print("=" * 60)
    if cycle_count >= 10:
        print("\n  Sample is pre-cycled. Proceed to Stage E (or Stage B baseline).")
    else:
        print(f"\n  ! Only {cycle_count} cycles done. Investigate cause before "
              "Stage E (results may not be repeatable).")


if __name__ == "__main__":
    main()
