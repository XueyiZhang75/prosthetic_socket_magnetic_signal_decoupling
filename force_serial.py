"""Cross-platform reader for the Arduino UNO + HX711 + DYLY-103 force chain.

Mirrors `mlx_serial.py` (same usage pattern), but for the force-sensor side:
the UNO is running `uno_force.ino`, which streams one CSV row per HX711
sample at ~10 Hz over USB CDC:

    t_ms , raw , scaled_N

`scaled_N` is already in Newtons IF the .ino has been calibrated (i.e.,
`TARE_OFFSET` and `CALIBRATION_FACTOR` are filled in). On top of the .ino's
static TARE_OFFSET this module supports a software "live tare" called once
at the start of each experiment to absorb any zero-drift (typical ~5-10 mN
between calibration and use, due to thermal/mechanical settling).

Typical usage in an experiment script:

    from force_serial import find_force_port, ForceReader

    with ForceReader(find_force_port()) as force:
        force.live_tare(duration_s=2.0)              # zero out static drift
        for q in q_sequence:
            mark10.move_to(q)
            time.sleep(2.0)
            F_mean, F_std, n = force.sample_average(2.0)
            print(f"q={q} F={F_mean:.4f} +/- {F_std*1000:.2f} mN")
"""

import statistics
import sys
import time

import serial
import serial.tools.list_ports


BAUD = 115200

# Physical sanity limit: any single sample whose |scaled_N| exceeds this is
# discarded as a HX711 read glitch / bit error / serial corruption. The
# DYLY-103 saturates around ~49 N, so 100 N is comfortably impossible.
SANITY_LIMIT_N = 100.0

# Banner the .ino prints once on boot. We use this to disambiguate the UNO
# from other USB-serial devices on the system (e.g. the QT Py for MLX90393).
_BANNER_TOKEN = "UNO_force ready"

# Heuristic keywords for the UNO / CH340 USB-serial chip. Used as a first
# pass before banner-probing — fast on systems where only one match exists.
_UNO_KEYWORDS = (
    "ch340", "ch9102", "wch", "arduino", "uno", "usb-serial ch",
)

# Keywords that strongly suggest the device is NOT the UNO (e.g. QT Py).
_MLX_KEYWORDS = ("adafruit", "qt py", "qtpy", "samd", "circuitpython", "usbmodem")


# ----------------------------------------------------------------------------
# Port finding
# ----------------------------------------------------------------------------
def _describe(p):
    return " ".join(filter(None, [
        p.device, p.description, p.manufacturer, p.product, p.interface,
    ])).lower()


def _probe_banner(device, timeout_s=2.5):
    """Open `device`, read for up to `timeout_s`, return True iff the UNO_force
    banner shows up. Closes the port on the way out."""
    try:
        ser = serial.Serial(device, BAUD, timeout=0.4)
    except (serial.SerialException, PermissionError, OSError):
        return False
    try:
        time.sleep(2.2)  # UNO resets when port opens; banner needs ~2 s
        t_end = time.time() + timeout_s
        while time.time() < t_end:
            line = ser.readline().decode(errors="ignore")
            if _BANNER_TOKEN in line:
                return True
    finally:
        try:
            ser.close()
        except Exception:
            pass
    return False


def find_force_port(prefer=None, interactive=True):
    """Locate the Arduino UNO + HX711 + DYLY-103 chain.

    Strategy:
      1. If `prefer` is given, return it directly (no probing).
      2. Keyword match on USB description (fast, works in 95% of setups).
      3. If multiple matches or ambiguous, banner-probe each candidate
         (open + listen for "UNO_force ready").
      4. Fall back to interactive prompt if nothing matched.
    """
    if prefer:
        return prefer

    ports = list(serial.tools.list_ports.comports())
    if not ports:
        sys.exit("No serial ports found. Is the UNO plugged in?")

    # Filter out MLX-style ports up front to avoid grabbing the QT Py.
    candidates = []
    for p in ports:
        desc = _describe(p)
        if any(k in desc for k in _MLX_KEYWORDS):
            continue
        candidates.append(p)

    # 2) keyword first pass
    keyword_hits = [
        p for p in candidates if any(k in _describe(p) for k in _UNO_KEYWORDS)
    ]
    if len(keyword_hits) == 1:
        p = keyword_hits[0]
        print(f"  auto-detected UNO_force on {p.device}  ({p.description})")
        return p.device

    # 3) banner probe the remaining candidates (or all of them if keyword pass
    #    was empty / ambiguous)
    probe_set = keyword_hits if keyword_hits else candidates
    for p in probe_set:
        print(f"  probing {p.device} for UNO_force banner ...", end="",
              flush=True)
        if _probe_banner(p.device):
            print(" hit.")
            return p.device
        print(" no.")

    # 4) interactive fallback
    print("\nCould not identify UNO_force port. Available ports:",
          file=sys.stderr)
    for i, p in enumerate(ports):
        print(f"  [{i}] {p.device:10s}  {p.description}", file=sys.stderr)
    if not (interactive and sys.stdin.isatty()):
        sys.exit("UNO_force port not found (non-interactive).")

    while True:
        choice = input("Pick port index or full COM name: ").strip()
        if choice.upper().startswith("COM") or choice.startswith("/"):
            return choice
        try:
            return ports[int(choice)].device
        except (ValueError, IndexError):
            print("  invalid; try again", file=sys.stderr)


# ----------------------------------------------------------------------------
# ForceReader
# ----------------------------------------------------------------------------
class ForceReader:
    """One-line reader for the UNO_force serial stream.

    State:
      live_tare_N : float   software zero offset applied on top of the .ino's
                            static TARE_OFFSET. Set by call to live_tare().
                            All "tared" outputs subtract this.

    The .ino streams `t_ms, raw, scaled_N` once per HX711 sample. This class
    parses each line, ignores boot banner / header, and exposes:

      read_one()          ->  (t_ms, raw, scaled_N_raw) for the next valid row
                              or None on timeout. scaled_N_raw is what the .ino
                              put on the wire, BEFORE the live_tare correction.

      live_tare(dur_s)    ->  read dur_s seconds, average scaled_N_raw, store
                              as live_tare_N. Prints noise stats.

      drain(dur_s)        ->  consume the serial stream for dur_s (mechanical
                              settle), discarding samples.

      sample_average(dur_s)
                          ->  collect dur_s of samples, return
                              (mean_N_tared, std_N, n_samples).

      read_force_N()      ->  return the most recent tared force reading,
                              draining the input buffer first so it is the
                              very latest.
    """

    def __init__(self, port, baud=BAUD, ready_timeout_s=5.0, max_open_retries=5):
        self.port = port
        self.ser = self._open_with_retry(port, baud, max_open_retries)
        # Opening the UNO triggers a hardware reset.
        time.sleep(2.2)
        self.ser.reset_input_buffer()
        self._wait_for_banner(ready_timeout_s)
        self.live_tare_N = 0.0
        self.last_live_tare_stats = None

    @staticmethod
    def _open_with_retry(port, baud, max_retries):
        """Open the UNO serial port, retrying with a friendly hint if it's busy.

        Same pattern as force_calibration.py: the typical cause is Arduino
        IDE's Serial Monitor still holding the port, or a CH340 driver in a
        stuck state after a previous crash. Give the user a chance to fix it
        instead of dying immediately.
        """
        for attempt in range(1, max_retries + 1):
            try:
                return serial.Serial(port, baud, timeout=0.5)
            except (serial.SerialException, PermissionError, OSError) as exc:
                msg = str(exc)
                is_busy = (
                    "PermissionError" in msg or "Access is denied" in msg
                    or "Cannot configure port" in msg
                    or "FileNotFoundError" in msg
                )
                if attempt == 1 and is_busy:
                    print(f"\n  ! cannot open {port}: looks like another program "
                          "is holding the port.")
                    print("    Most common cause: Arduino IDE's Serial Monitor "
                          "or Plotter is open.")
                    print("    Close it (or the whole Arduino IDE), then come "
                          "back here.\n")
                elif attempt == 1:
                    print(f"\n  ! cannot open {port}: {exc}\n")
                if attempt < max_retries:
                    try:
                        input(f"  press Enter to retry (attempt {attempt + 1}/"
                              f"{max_retries}), or Ctrl+C to abort ... ")
                    except KeyboardInterrupt:
                        raise
                else:
                    raise

    # ------------------------------------------------------------------- io

    def _wait_for_banner(self, timeout_s):
        t_end = time.time() + timeout_s
        while time.time() < t_end:
            line = self.ser.readline().decode(errors="ignore").strip()
            if _BANNER_TOKEN in line:
                return
            if line.startswith("t_ms") or "," in line:
                return
        print("  ! warning: no UNO_force banner seen — wrong board?")

    @staticmethod
    def _parse_line(line):
        """Parse `t_ms,raw,scaled_N`. Return (t_ms, raw, scaled_N) or None."""
        if not line or line.startswith("#") or line.startswith("t_ms"):
            return None
        parts = line.split(",")
        if len(parts) != 3:
            return None
        try:
            return (int(parts[0]), int(parts[1]), float(parts[2]))
        except ValueError:
            return None

    def read_one(self):
        """Read one valid sample row (blocks up to the serial timeout)."""
        line = self.ser.readline().decode(errors="ignore").strip()
        return self._parse_line(line)

    # ------------------------------------------------------------- functions

    def drain(self, duration_s):
        """Read & discard for `duration_s`. Returns sample count drained."""
        n = 0
        t_end = time.time() + duration_s
        while time.time() < t_end:
            if self.read_one() is not None:
                n += 1
        self.ser.reset_input_buffer()
        return n

    def live_tare(self, duration_s=2.0, pre_settle_s=3.0, verbose=True):
        """Median-based live tare with outlier diagnostics.

        Pre-drains the stream for `pre_settle_s` first so any mechanical
        ringing from a recent move has time to die down. Then samples
        scaled_N for `duration_s` and uses the MEDIAN as the tare value
        (robust to a handful of HX711 read glitches).

        Prints diagnostic info so the user can see if the underlying data
        is clean: mean vs median (close => clean), std vs scaled-MAD
        (similar => clean), and min/max (tight spread => clean).
        """
        if pre_settle_s > 0:
            if verbose:
                print(f"  live-tare: pre-settling {pre_settle_s:.1f} s "
                      "(do not touch the sensor) ...", end="", flush=True)
            t_end = time.time() + pre_settle_s
            self.ser.reset_input_buffer()
            while time.time() < t_end:
                self.read_one()
            if verbose:
                print(" done.")

        if verbose:
            print(f"  live-tare: sampling {duration_s:.1f} s ...",
                  end="", flush=True)
        self.ser.reset_input_buffer()
        samples = []
        t_end = time.time() + duration_s
        while time.time() < t_end:
            r = self.read_one()
            if r is not None:
                samples.append(r[2])
        if not samples:
            raise RuntimeError("live_tare got no samples — UNO not streaming?")

        # Hard sanity: discard physically impossible HX711 glitches
        n_raw = len(samples)
        samples = [s for s in samples if abs(s) < SANITY_LIMIT_N]
        n_drop = n_raw - len(samples)
        if not samples:
            raise RuntimeError(
                f"live_tare: all {n_raw} samples beyond +/-{SANITY_LIMIT_N} N — "
                "HX711 wiring issue?"
            )

        # Robust statistics
        median_N = statistics.median(samples)
        deviations = [abs(s - median_N) for s in samples]
        mad = statistics.median(deviations)
        std_robust_N = 1.4826 * mad   # MAD scaled to estimate Gaussian std

        # Conventional statistics (for comparison)
        mean_N = statistics.mean(samples)
        std_N = statistics.stdev(samples) if len(samples) > 1 else 0.0
        sample_range_N = max(samples) - min(samples)

        self.live_tare_N = median_N
        self.last_live_tare_stats = {
            "median_N": median_N,
            "mean_N": mean_N,
            "robust_std_N": std_robust_N,
            "sample_std_N": std_N,
            "min_N": min(samples),
            "max_N": max(samples),
            "range_N": sample_range_N,
            "n": len(samples),
            "n_dropped": n_drop,
        }

        if verbose:
            print(" done.")
            extra = f", dropped {n_drop} outlier(s)" if n_drop else ""
            print(f"  live_tare_N (median) = {median_N*1000:+8.2f} mN")
            print(f"    mean              = {mean_N*1000:+8.2f} mN")
            print(f"    robust std (MAD)  = {std_robust_N*1000:8.2f} mN")
            print(f"    sample std        = {std_N*1000:8.2f} mN")
            print(f"    range [min, max]  = [{min(samples)*1000:+.1f}, "
                  f"{max(samples)*1000:+.1f}] mN")
            print(f"    n = {len(samples)}{extra}")
            # Diagnostic warning
            if std_N > 5 * std_robust_N and len(samples) > 5:
                print(f"    !! sample std >> robust std --> outliers present, "
                      "but median tare is unaffected")
            if std_robust_N * 1000 > 50:
                print(f"    !! robust noise > 50 mN: mechanical setup is "
                      "still oscillating. Consider waiting longer before "
                      "running, or check for loose wires / dangling cables.")
        return median_N, std_robust_N, len(samples)

    def sample_average(self, duration_s):
        """Collect `duration_s` of samples, return (median_N, robust_std_N, n)
        AFTER subtracting the live tare. Returns median (not mean) because a
        single HX711 read glitch can otherwise spoof a 'contact' event in
        downstream logic. robust_std_N is MAD-based, ~1 sigma for Gaussian
        data but not skewed by outliers."""
        self.ser.reset_input_buffer()
        raw_samples = []
        t_end = time.time() + duration_s
        while time.time() < t_end:
            r = self.read_one()
            if r is not None:
                raw_samples.append(r[2])

        # Hard sanity filter (physical impossibility)
        good = [s - self.live_tare_N for s in raw_samples
                if abs(s) < SANITY_LIMIT_N]
        if not good:
            return 0.0, 0.0, 0

        median_N = statistics.median(good)
        deviations = [abs(g - median_N) for g in good]
        mad = statistics.median(deviations)
        std_robust_N = 1.4826 * mad
        return median_N, std_robust_N, len(good)

    def read_force_N(self):
        """Drain any backlog, return the very latest tared force reading."""
        latest = None
        # Read everything that has accumulated, keeping only the last.
        while self.ser.in_waiting:
            line = self.ser.readline().decode(errors="ignore").strip()
            r = self._parse_line(line)
            if r is not None:
                latest = r
        if latest is None:
            # Buffer was empty (no backlog) — wait for one fresh sample.
            latest = self.read_one()
        if latest is None:
            raise RuntimeError("no force sample available")
        return latest[2] - self.live_tare_N

    # --------------------------------------------------------------- lifetime

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ----------------------------------------------------------------------------
# Standalone self-test
# ----------------------------------------------------------------------------
def _self_test(port=None):
    """Open the UNO_force port, do a live-tare, then print live readings.

    Useful as a sanity check: `python force_serial.py [COM7]` will stream
    tared force readings until you Ctrl+C.
    """
    port = port or find_force_port()
    print(f"\n=== UNO_force self-test on {port} ===")
    with ForceReader(port) as force:
        force.live_tare(duration_s=2.0)
        print("\nstreaming tared force every ~0.5 s, Ctrl+C to stop:")
        try:
            while True:
                F = force.read_force_N()
                print(f"  F = {F*1000:+8.2f} mN   ({F:+.5f} N)")
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nstopped.")


if __name__ == "__main__":
    cli_port = sys.argv[1] if len(sys.argv) > 1 else None
    _self_test(cli_port)
