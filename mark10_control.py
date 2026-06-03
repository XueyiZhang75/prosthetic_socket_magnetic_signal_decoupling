"""Mark-10 Series F test frame controller (PC Control mode).

Driver for absolute positioning over the legacy NexygenTM-style ASCII protocol
described in §10.2 of the EasyMESUR user guide. Reusable across all stages that
need automated Mark-10 motion (Stage C/E/F/G/H/I/J/K/L).

Pre-conditions for the test frame:
  - EasyMESUR touchscreen: Home -> PC Control active
  - USB-B cable on the rear of the MDU (NOT the touchpanel USB-C)
  - Mark-10 USB driver installed on this PC
  - Baud rate in EasyMESUR Preferences -> PC Control matches `baud` here

Known firmware quirk (verified on F305 fw 1.00.25, EasyMESUR 2.5.0):
  The downward `d` command is capped at ~25 mm/min regardless of the programmed
  speed. Upward `u` honours the programmed speed (~91% of commanded, the rest is
  accel/decel ramp). Position accuracy is unaffected: hardware limit stops the
  crosshead at exactly the target with sub-mm error in both directions.
"""

import re
import statistics
import time

import serial


class Mark10Error(RuntimeError):
    pass


class Mark10:
    def __init__(self, port, baud=9600, speed_mm_per_min=200.0, verbose=False):
        if not (0.5 <= speed_mm_per_min <= 1100.0):
            raise ValueError(
                f"speed {speed_mm_per_min} mm/min outside 0.5..1100 range"
            )
        self.port = port
        self.baud = baud
        self.speed = speed_mm_per_min
        self.verbose = verbose
        self.ser = serial.Serial(
            port, baud, bytesize=8, parity="N", stopbits=1, timeout=0.4
        )
        self._probe()
        # canonical pre-flight: stop, mm units, manual mode, zero pos + load
        self._cmd("s")
        self._cmd("i")
        self._cmd("m")
        self._cmd("z")
        self._cmd("R")
        self._assert_speed()

    # --------------------------------------------------------------- serial

    def _cmd(self, cmd, expect_reply=True, read_timeout=0.4):
        self.ser.timeout = read_timeout
        self.ser.reset_input_buffer()
        self.ser.write(cmd.encode("ascii"))
        self.ser.flush()
        if not expect_reply:
            return ""
        line = self.ser.readline().decode("ascii", errors="ignore").strip()
        if self.verbose:
            print(f"  [mark10] {cmd!r} -> {line!r}")
        return line

    def _probe(self, max_retries=5):
        """Send a status query; retry with a friendly hint if no reply.

        Most common failure: EasyMESUR auto-exited PC Control mode after the
        previous Python session disconnected. User just needs to go back to
        Home -> PC Control on the touchscreen and press Enter to retry.
        """
        for attempt in range(1, max_retries + 1):
            reply = self._cmd("p")
            if reply:
                return
            if attempt == 1:
                print("\n  ! Mark-10 did not reply on probe.")
                print("    Most common cause: EasyMESUR is NOT in PC Control "
                      "mode right now.")
                print("    Look at the Mark-10 touchscreen:")
                print("      - If it shows Home screen / Manual Control, "
                      "tap Home -> PC Control.")
                print("      - If the screen is off, check Mark-10 power "
                      "and USB.")
                print(f"    (port {self.port!r}, baud {self.baud})")
            if attempt < max_retries:
                try:
                    input(f"\n  press Enter to retry (attempt {attempt + 1}/"
                          f"{max_retries}), or Ctrl+C to abort ... ")
                except KeyboardInterrupt:
                    raise
            else:
                raise Mark10Error(
                    "Mark-10 still not responding after retries. Check the "
                    "touchscreen and USB cable, then re-run."
                )

    def _assert_speed(self):
        # Set programmed speed AND select it. Legacy quirk: re-assert before
        # every motion command, otherwise the selector can be silently reset.
        self._cmd(f"e{self.speed:06.1f}")
        self._cmd("o")

    # --------------------------------------------------------------- helpers

    @staticmethod
    def _limit_cmd(letter, value):
        """Build a `g` (lower) or `h` (upper) travel-limit command in mm format.

        Manual:  g/h-XXX.XX  (negative if applicable, 3-digit zero-padded int,
        2 decimals).  Negative form is 7 chars after the letter; positive 6.
        """
        if value < 0:
            return f"{letter}-{abs(value):06.2f}"
        return f"{letter}{value:06.2f}"

    # --------------------------------------------------------------- queries

    def _position_once(self):
        """Return one raw crosshead position read in mm."""
        last = ""
        for _ in range(3):
            last = self._cmd("x")
            m = re.search(r"[-+]?\d*\.?\d+", last)
            if m:
                return float(m.group(0))
            time.sleep(0.05)
        raise Mark10Error(f"position query failed (last reply {last!r})")

    def position(self):
        """Return current crosshead position in mm (relative to last `z`)."""
        return self._position_once()

    def position_stable(self, samples=5, spread_mm=0.2):
        """Return a median position after rejecting one-off serial glitches."""
        vals = []
        for _ in range(samples):
            vals.append(self._position_once())
            time.sleep(0.03)

        med = statistics.median(vals)
        close = [v for v in vals if abs(v - med) <= spread_mm]
        if len(close) >= max(2, min(3, samples)):
            return statistics.median(close)

        vals_sorted = sorted(vals)
        best_pair = min(
            zip(vals_sorted, vals_sorted[1:]),
            key=lambda p: abs(p[1] - p[0]),
        )
        if abs(best_pair[1] - best_pair[0]) <= spread_mm:
            return statistics.median(best_pair)

        raise Mark10Error(
            "unstable position replies: "
            + ", ".join(f"{v:+.3f}" for v in vals)
        )

    def status(self):
        """Return the raw status string from `p` (e.g. 'S L', 'D L', 'S L DL')."""
        return self._cmd("p")

    # --------------------------------------------------------------- actions

    def zero_position(self):
        self._cmd("z")

    def stop(self):
        self._cmd("s")

    def move_to(
        self,
        target_mm,
        tolerance_mm=0.05,
        max_wait_s=600.0,
        stall_window_s=8.0,
        opposite_limit_margin_mm=5.0,
    ):
        """Move to absolute position `target_mm` (mm relative to the last `z`).

        Blocks until the hardware travel limit stops the crosshead at the
        target. Both `g` (lower) and `h` (upper) limits are set every call:
        the one in the direction of motion is set to `target_mm`, the other
        is set permissively (current ± `opposite_limit_margin_mm`) so it does
        not block the move.

        Upward moves are two-stage: a fast segment at the programmed speed
        up to (target − SLOW_BAND_MM), then a slow segment at SLOW_SPEED_MM
        to the final target. The slow segment avoids the 0.2–0.3 mm
        overshoot observed in Stage F (single-stage upward at 200 mm/min
        + 0.3 s polling → motor travels ~1 mm per poll before stop arrives).
        Downward moves are single-stage because the firmware `g` limit
        physically stops the crosshead with sub-mm precision.

        Returns the actual final position (read from `x`).
        Raises Mark10Error on stall or timeout.
        """
        current = self.position_stable()
        delta = target_mm - current
        if abs(delta) < tolerance_mm:
            return current

        if delta < 0:
            # Downward: single segment, firmware g-limit is precise.
            return self._run_segment(
                target_mm, current, "d",
                speed_mm_per_min=self.speed,
                tolerance_mm=tolerance_mm,
                poll_s=0.3,
                max_wait_s=max_wait_s,
                stall_window_s=stall_window_s,
                opposite_limit_margin_mm=opposite_limit_margin_mm,
            )

        # Upward: two-stage to avoid Python-polling overshoot.
        SLOW_BAND_MM = 0.5
        SLOW_SPEED_MM_PER_MIN = 25.0
        slow_speed = min(self.speed, SLOW_SPEED_MM_PER_MIN)

        if delta > SLOW_BAND_MM:
            intermediate = target_mm - SLOW_BAND_MM
            self._run_segment(
                intermediate, current, "u",
                speed_mm_per_min=self.speed,
                tolerance_mm=0.15,            # loose: precision comes in slow stage
                poll_s=0.3,
                max_wait_s=max_wait_s,
                stall_window_s=stall_window_s,
                opposite_limit_margin_mm=opposite_limit_margin_mm,
                final_check_mm=1.0,
            )

        # Slow finishing segment (also the only segment if delta <= SLOW_BAND_MM).
        current2 = self.position_stable()
        return self._run_segment(
            target_mm, current2, "u",
            speed_mm_per_min=slow_speed,
            tolerance_mm=tolerance_mm,        # tight (default 0.05)
            poll_s=0.1,                       # poll fast so 25 mm/min ≈ 0.04 mm overshoot
            max_wait_s=max_wait_s,
            stall_window_s=stall_window_s,
            opposite_limit_margin_mm=opposite_limit_margin_mm,
        )

    def _run_segment(
        self,
        target_mm, start_pos, motion,
        speed_mm_per_min,
        tolerance_mm,
        poll_s,
        max_wait_s,
        stall_window_s,
        opposite_limit_margin_mm,
        final_check_mm=0.5,
    ):
        """Drive one motion segment to `target_mm`. `motion` is 'u' or 'd'.

        For 'd' the firmware `g` limit physically stops the crosshead, and we
        wait for "stop + position-stable". For 'u' we Python-poll position
        and send `s` once `pos >= target − tolerance_mm`.
        """
        delta_sign = -1 if motion == "d" else +1

        if motion == "d":
            self._cmd(self._limit_cmd("g", target_mm))
            self._cmd(self._limit_cmd("h",
                                      start_pos + opposite_limit_margin_mm))
        else:
            # h not reliably honored on fresh upward moves; keep it as a far
            # safety ceiling and rely on Python polling instead.
            self._cmd(self._limit_cmd("h", target_mm + 5.0))
            self._cmd(self._limit_cmd("g",
                                      start_pos - opposite_limit_margin_mm))

        self._cmd("l")
        # Set speed for THIS segment (may differ from self.speed for the
        # upward slow-finish stage).
        self._cmd(f"e{speed_mm_per_min:06.1f}")
        self._cmd("o")
        self._cmd(motion, expect_reply=False)

        start = time.time()
        last_progress_t = start
        last_pos = start_pos
        overshoot_safety_mm = 2.0
        pos_sanity_mm = 5.0

        while True:
            time.sleep(poll_s)
            elapsed = time.time() - start
            st = self.status()
            pos = self.position()

            # Cross-contaminated position read sanity check.
            if abs(pos - last_pos) > pos_sanity_mm and elapsed > 0.5:
                time.sleep(0.05)
                pos_retry = self.position()
                if abs(pos_retry - last_pos) <= pos_sanity_mm:
                    pos = pos_retry
                else:
                    self.stop()
                    try:
                        pos_stable = self.position_stable(samples=5,
                                                          spread_mm=0.2)
                    except Mark10Error:
                        pos_stable = pos_retry
                    raise Mark10Error(
                        "implausible position jump: "
                        f"last={last_pos:.3f} mm, "
                        f"read={pos:.3f}/{pos_retry:.3f}/"
                        f"{pos_stable:.3f} mm, "
                        f"target={target_mm:.3f} mm"
                    )

            # Upward: explicit Python stop when we reach target.
            if delta_sign > 0 and pos >= target_mm - tolerance_mm:
                self.stop()
                time.sleep(0.1)
                try:
                    final_pos = self.position_stable(samples=5,
                                                     spread_mm=0.2)
                except Mark10Error:
                    final_pos = pos
                if abs(final_pos - target_mm) > final_check_mm:
                    raise Mark10Error(
                        f"bad final position: pos={final_pos:.3f} mm, "
                        f"target={target_mm:.3f} mm"
                    )
                return final_pos

            # Hard overshoot safety.
            if (delta_sign < 0 and pos < target_mm - overshoot_safety_mm) or (
                delta_sign > 0 and pos > target_mm + overshoot_safety_mm
            ):
                self.stop()
                raise Mark10Error(
                    f"overshoot: pos={pos:.3f} mm, target={target_mm:.3f} mm"
                )

            # Hardware limit / stop detection (mainly for downward).
            st_upper = st.upper()
            limit_matches_direction = (
                (delta_sign < 0 and "DL" in st_upper) or
                (delta_sign > 0 and "UL" in st_upper)
            )
            plain_stopped = (
                st_upper.startswith("S")
                and "DL" not in st_upper
                and "UL" not in st_upper
            )

            if elapsed > 1.0 and (limit_matches_direction or plain_stopped):
                time.sleep(0.15)
                pos_a = self.position()
                time.sleep(0.15)
                pos_b = self.position()
                position_stable = (
                    abs(pos_b - pos_a) < 0.1
                    and abs(pos_a - pos) < 0.1
                )
                if position_stable:
                    try:
                        return self.position_stable(samples=5, spread_mm=0.2)
                    except Mark10Error:
                        return pos_b
                last_pos = pos_b
                last_progress_t = time.time()

            # Stall detection.
            if abs(pos - last_pos) >= 0.05:
                last_pos = pos
                last_progress_t = time.time()
            elif time.time() - last_progress_t > stall_window_s and elapsed > 3.0:
                self.stop()
                raise Mark10Error(
                    f"stalled at pos={pos:.3f} mm, target={target_mm:.3f} mm"
                )

            # Absolute timeout.
            if elapsed > max_wait_s:
                self.stop()
                raise Mark10Error(
                    f"timeout: pos={pos:.3f} mm, target={target_mm:.3f} mm"
                )

    # --------------------------------------------------------------- lifecycle

    def close(self):
        try:
            self._cmd("s")
        except Exception:
            pass
        try:
            self.ser.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ============================================================================
# Standalone self-test
# ============================================================================
# Running this file directly (`python mark10_control.py`) probes the Mark-10
# WITHOUT moving the crosshead. Use it before running a real experiment to
# confirm:
#   - the COM port is right
#   - the baud rate matches EasyMESUR Preferences -> PC Control
#   - the touchscreen is actually in PC Control mode
#   - position/load readback work

def _self_test(port="COM5", baud=9600):
    print(f"=== Mark-10 self-test on {port} @ {baud} ===")
    try:
        m = Mark10(port, baud)
    except Mark10Error as exc:
        print(f"\nFAILED to open Mark-10:\n{exc}")
        return 1
    try:
        print(f"  status   : {m.status()!r}")
        print(f"  position : {m.position():+.3f} mm   (relative to current zero)")
        print(f"  programmed speed setting (e/o asserted in __init__): "
              f"{m.speed:.1f} mm/min")
        print("  no motion was commanded.")
        print("\nMark-10 is reachable and PC Control is active. OK.")
        return 0
    finally:
        m.close()


if __name__ == "__main__":
    import sys
    cli_port = sys.argv[1] if len(sys.argv) > 1 else "COM5"
    raise SystemExit(_self_test(cli_port))
