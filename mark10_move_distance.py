import serial
import time
import re
import sys

PORT = "COM5"
BAUD = 9600                 # must match EasyMESUR: Preferences -> PC Control -> Baud Rate

SPEED_MM_PER_MIN = 500.0    # 0.5 .. 1100 mm/min for F305 (depends on installed options)
MOVE_DISTANCE_MM = 20.0     # absolute travel from current (zeroed) position
DIRECTION = "down"          # "up" or "down"


def parse_number(text):
    if text is None:
        return None
    match = re.search(r"[-+]?\d*\.?\d+", text)
    return float(match.group(0)) if match else None


def speed_command_mm(speed):
    if not (0.5 <= speed <= 1100.0):
        raise ValueError(f"Speed {speed} mm/min out of plausible range 0.5..1100")
    return f"e{speed:06.1f}"


def lower_limit_command_mm(distance):
    if distance < 0:
        return f"g-{abs(distance):06.2f}"
    return f"g{distance:06.2f}"


def upper_limit_command_mm(distance):
    if distance < 0:
        return f"h-{abs(distance):06.2f}"
    return f"h{distance:06.2f}"


def send(cmd, expect_reply=True, read_timeout=0.4):
    ser.timeout = read_timeout
    ser.reset_input_buffer()
    ser.write(cmd.encode("ascii"))
    ser.flush()
    if not expect_reply:
        return ""
    line = ser.readline().decode("ascii", errors="ignore").strip()
    print(f"{cmd!s:>8} -> {line!r}")
    return line


def ensure_pc_control_ready():
    print("Probe communication ...")
    reply = send("p")
    if not reply:
        print("\nNo reply from test frame.")
        print("Checklist:")
        print("  1. EasyMESUR touchscreen: Home -> PC Control must be active.")
        print("  2. USB-B cable plugged into the REAR of the MDU (not the tablet).")
        print(f"  3. COM port = {PORT!r}. Verify in Device Manager.")
        print(f"  4. Baud = {BAUD}. Must match Preferences -> PC Control on the touchscreen.")
        print("  5. Mark-10 USB driver installed on this PC.")
        sys.exit(1)
    print(f"Test frame status: {reply!r}\n")


ser = serial.Serial(
    PORT,
    BAUD,
    bytesize=8,
    parity="N",
    stopbits=1,
    timeout=0.4,
    rtscts=False,
    dsrdtr=False,
    xonxoff=False,
)

try:
    print(f"=== Mark-10 {DIRECTION.upper()} {MOVE_DISTANCE_MM} mm at {SPEED_MM_PER_MIN} mm/min ===")

    ensure_pc_control_ready()

    # Safety stop, switch to manual mode, mm units, zero load + position
    send("s")
    send("i")
    send("m")
    send("z")
    send("R")

    print("\nInitial state:")
    send("p")
    send("n")

    # Travel limit setup (direction-dependent)
    if DIRECTION == "down":
        target_mm = -MOVE_DISTANCE_MM
        limit_cmd = lower_limit_command_mm(target_mm)
        readback_cmd = "w"           # request lower travel limit
        motion_cmd = "d"
    elif DIRECTION == "up":
        target_mm = +MOVE_DISTANCE_MM
        limit_cmd = upper_limit_command_mm(target_mm)
        readback_cmd = "v"           # request upper travel limit
        motion_cmd = "u"
    else:
        raise ValueError(f"DIRECTION must be 'up' or 'down', got {DIRECTION!r}")

    print(f"\nSet travel limit: {limit_cmd}")
    send(limit_cmd)
    send(readback_cmd)               # read back

    # Enter travel limit mode BEFORE setting speed
    print("\nEnter travel limit mode")
    send("l")

    # Programmed speed AFTER entering limit mode
    speed_cmd = speed_command_mm(SPEED_MM_PER_MIN)
    print(f"\nSet programmed speed (after l): {speed_cmd}")
    send(speed_cmd)
    send("o")                        # programmed speed selector (back from `j`)
    send("a")                        # read back

    # Pre-motion sanity
    send("p")
    send("x")

    # Kick off motion
    print(f"\nStart {DIRECTION.upper()} motion")
    send(motion_cmd, expect_reply=False)

    # Timeout based on a very conservative worst-case (10 mm/min), NOT the commanded speed.
    # This way, even if firmware silently caps the actual speed, we still wait long enough
    # for the crosshead to physically reach the lower limit.
    worst_case_speed_mm_per_min = 10.0
    timeout_s = MOVE_DISTANCE_MM / worst_case_speed_mm_per_min * 60.0 * 1.5
    expected_time_s = MOVE_DISTANCE_MM / SPEED_MM_PER_MIN * 60.0
    print(f"Expected (if 200 mm/min honored): {expected_time_s:.1f} s")
    print(f"Worst-case timeout (10 mm/min assumption): {timeout_s:.1f} s\n")

    start = time.time()

    # Safety: if position has gone significantly past target, the hardware limit
    # failed to engage — force-stop immediately to protect the frame and sample.
    overshoot_safety_mm = 2.0

    # Stall detection: if position doesn't change for stall_window_s, abort.
    stall_window_s = 5.0
    stall_min_progress_mm = 0.05
    last_motion_t = time.time()
    last_motion_pos = 0.0

    while True:
        time.sleep(0.2)
        elapsed = time.time() - start

        status = send("p", read_timeout=0.15)
        x_resp = send("x", read_timeout=0.15)
        pos = parse_number(x_resp)

        if pos is not None:
            print(f"  t={elapsed:6.2f}s | pos={pos:8.3f} mm | status={status!r}")
        else:
            print(f"  t={elapsed:6.2f}s | pos=?? (raw={x_resp!r}) | status={status!r}")

        # 1. Hard overshoot safety (means limit mode is NOT enforcing)
        if pos is not None:
            if DIRECTION == "down" and pos < target_mm - overshoot_safety_mm:
                print(f"!! Overshoot: pos={pos:.3f} mm vs target {target_mm} mm. Force stop.")
                send("s")
                break
            if DIRECTION == "up" and pos > target_mm + overshoot_safety_mm:
                print(f"!! Overshoot: pos={pos:.3f} mm vs target {target_mm} mm. Force stop.")
                send("s")
                break

        # 2. Hardware limit engaged: machine stopped on its own at the target.
        #    This is the PRIMARY success path — gives ±0.15 mm hardware position accuracy.
        if elapsed > 1.0 and status.startswith("S"):
            if pos is not None:
                print(f"Hardware limit stopped at pos={pos:.3f} mm "
                      f"(target {target_mm} mm, error {pos - target_mm:+.3f} mm)")
            else:
                print("Hardware limit reports stopped (position unknown).")
            break

        # 3. Stall detection (something is wrong if no progress for several seconds)
        if pos is not None:
            if abs(pos - last_motion_pos) >= stall_min_progress_mm:
                last_motion_pos = pos
                last_motion_t = time.time()
            elif time.time() - last_motion_t > stall_window_s and elapsed > 2.0:
                print(f"No progress for {stall_window_s:.1f} s. Aborting.")
                send("s")
                break

        # 4. Absolute safety timeout
        if elapsed > timeout_s:
            print("Absolute timeout. Stopping for safety.")
            send("s")
            break

    # Report actual average speed (helps see if firmware capped us)
    final_elapsed = time.time() - start
    final_x = send("x")
    final_pos = parse_number(final_x)
    if final_pos is not None and final_elapsed > 0:
        actual_speed_mm_per_min = abs(final_pos) / final_elapsed * 60.0
        print(f"\n>>> Actual average speed: {actual_speed_mm_per_min:.2f} mm/min "
              f"(commanded {SPEED_MM_PER_MIN:.1f} mm/min)")

    print("\nFinal readings:")
    send("p")
    send("n")
    send("a")
    send("w")

except KeyboardInterrupt:
    print("\nInterrupted by user. Sending stop.")
    try:
        ser.write(b"s")
        ser.flush()
    except Exception:
        pass

finally:
    try:
        ser.write(b"s")
        ser.flush()
    except Exception:
        pass
    ser.close()
    print("Done.")