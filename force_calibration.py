"""force_calibration.py -- standalone calibration of the HX711 + DYLY-103 chain.

Walks you through three phases:

  1. TARE          — read the no-load baseline of the HX711 raw counts.
                     This becomes TARE_OFFSET in uno_force.ino.

  2. KNOWN MASSES  — place 3+ known masses on (or hang from) the load cell.
                     For each one, type the mass in grams; the script averages
                     a few seconds of raw counts and pairs them with the
                     expected force F = m * g.

  3. LINEAR FIT    — fits a straight line  raw - TARE_OFFSET = K * F_N
                     (forced through the tare). K becomes CALIBRATION_FACTOR.

At the end it prints the two C++ constants for you to paste into
uno_force.ino, then save+re-Upload from Arduino IDE. After that the
`scaled_N` column in the serial stream is real Newtons.

Run with no Serial Monitor and no other Python script holding the UNO port.

  python force_calibration.py            # auto-detect Arduino COM port
  python force_calibration.py COM7       # or specify the port explicitly
"""

import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

import serial
import serial.tools.list_ports

BAUD = 115200
GRAVITY = 9.80665                # m/s^2
TARE_SAMPLES = 40                # ~4 s at 10 Hz
POINT_SAMPLES = 40
READY_TIMEOUT_S = 5.0            # how long to wait for the UNO banner


# ----------------------------------------------------------------------------
# Port finding
# ----------------------------------------------------------------------------
def find_uno_port(prefer=None):
    if prefer:
        return prefer
    ports = list(serial.tools.list_ports.comports())
    # Arduino UNO (genuine = ATmega16U2), or CH340/CH9102 clones
    keywords = ("arduino", "uno", "ch340", "ch9102", "wch", "usb-serial ch")
    for p in ports:
        haystack = " ".join(filter(None, [
            p.description, p.manufacturer, p.product, p.interface,
        ])).lower()
        if any(k in haystack for k in keywords):
            print(f"  auto-detected Arduino on {p.device}  ({p.description})")
            return p.device

    print("\nCould not auto-detect Arduino UNO. Available ports:")
    for i, p in enumerate(ports):
        print(f"  [{i}] {p.device:8s}  {p.description}")
    while True:
        choice = input("Pick port index or full COM name: ").strip()
        if not choice:
            continue
        if choice.upper().startswith("COM") or choice.startswith("/"):
            return choice
        try:
            return ports[int(choice)].device
        except (ValueError, IndexError):
            print("  invalid; try again")


# ----------------------------------------------------------------------------
# Serial helpers
# ----------------------------------------------------------------------------
def open_serial(port, max_retries=5):
    """Open the UNO serial port, retrying with a friendly hint if it's busy."""
    for attempt in range(1, max_retries + 1):
        try:
            ser = serial.Serial(port, BAUD, timeout=2)
            # Opening the UNO triggers a hardware reset; firmware needs ~2 s
            # to come up and print its banner.
            time.sleep(2.2)
            ser.reset_input_buffer()
            return ser
        except (serial.SerialException, PermissionError, OSError) as exc:
            msg = str(exc)
            is_busy = (
                "PermissionError" in msg or "Access is denied" in msg
                or "Cannot configure port" in msg or "FileNotFoundError" in msg
            )
            if attempt == 1 and is_busy:
                print(f"\n  ! cannot open {port}: looks like something else is "
                      "holding the port.")
                print("    Most common cause: Arduino IDE's Serial Monitor "
                      "or Serial Plotter is open.")
                print("    Close the Serial Monitor tab (the X on its tab) or "
                      "close the whole Arduino IDE, then come back here.\n")
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


def wait_for_banner(ser):
    """Read until we see the UNO_force banner, or time out."""
    t_end = time.time() + READY_TIMEOUT_S
    while time.time() < t_end:
        line = ser.readline().decode(errors="ignore").strip()
        if "UNO_force ready" in line:
            return True
        # Keep going if we just got header / data; we still know things are OK
        if line.startswith("t_ms") or "," in line:
            return True
    return False


def read_raw_samples(ser, n_samples, label=""):
    """Collect n valid raw integers from the t_ms,raw,scaled_N stream."""
    raw_vals = []
    print(f"  sampling {label}", end="", flush=True)
    while len(raw_vals) < n_samples:
        line = ser.readline().decode(errors="ignore").strip()
        if not line:
            continue
        if line.startswith("#") or line.startswith("t_ms"):
            continue
        parts = line.split(",")
        if len(parts) != 3:
            continue
        try:
            raw_vals.append(int(parts[1]))
        except ValueError:
            continue
        if len(raw_vals) % 5 == 0:
            print(".", end="", flush=True)
    print(f" done ({len(raw_vals)} samples)")
    return raw_vals


def stats(xs):
    """mean, std (ddof=1), min, max."""
    return (
        statistics.mean(xs),
        statistics.stdev(xs) if len(xs) > 1 else 0.0,
        min(xs),
        max(xs),
    )


# ----------------------------------------------------------------------------
# Linear regression: y = K * x, forced through origin (since we already tared)
# ----------------------------------------------------------------------------
def fit_through_origin(xs, ys):
    """Least-squares slope K minimizing sum((K*x - y)^2). Also return R^2."""
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_xx = sum(x * x for x in xs)
    if sum_xx == 0:
        raise ValueError("all x values are zero")
    k = sum_xy / sum_xx
    mean_y = sum(ys) / len(ys)
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    ss_res = sum((y - k * x) ** 2 for x, y in zip(xs, ys))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return k, r2


# ----------------------------------------------------------------------------
# Plot (optional)
# ----------------------------------------------------------------------------
def plot_fit(points, tare_offset, k, png_path):
    """Publication-style calibration plot.

    Top panel: linear fit, measured points with +/-2σ error bars from each
    point's raw-counts std, secondary x-axis in grams, fit-quality summary
    box (R², slope, resolution, max residual, n).

    Bottom panel (multi-point only): residual from the fit, on counts (left
    y) and mN (right y) — the diagnostic for linearity.

    Single-point case degrades gracefully to a single panel with no residuals.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not available, skipping plot")
        return

    forces = [p[3] for p in points]
    deltas = [p[1] - tare_offset for p in points]
    stds = [p[2] for p in points]
    yerr = [2.0 * s for s in stds]
    n_points = len(points)
    if n_points == 0:
        return

    # ----------------------------------------------------------------- layout
    if n_points >= 2:
        fig, (ax_main, ax_res) = plt.subplots(
            2, 1, figsize=(8.5, 7.5),
            gridspec_kw={"height_ratios": [3, 1], "hspace": 0.10},
            sharex=True,
        )
    else:
        fig, ax_main = plt.subplots(figsize=(8.5, 5.5))
        ax_res = None

    pt_color = "#d62728"
    fit_color = "#1f77b4"

    # ------------------------------------------------------------ main panel
    f_max = max(forces) * 1.10 if max(forces) > 0 else 1.0
    ax_main.plot(
        [0.0, f_max], [0.0, k * f_max],
        "-", color=fit_color, linewidth=1.8, alpha=0.85,
        label=fr"linear fit:  $\Delta$raw = {k:,.2f} $\cdot$ F",
        zorder=1,
    )
    ax_main.errorbar(
        forces, deltas, yerr=yerr,
        fmt="o", color=pt_color, markersize=8,
        markeredgecolor="white", markeredgewidth=1.5,
        ecolor=pt_color, elinewidth=1.5, capsize=5,
        label=r"measured  ($\pm 2\sigma$)", zorder=3,
    )
    ax_main.plot([0], [0], "+", color="black", markersize=12,
                 markeredgewidth=1.5, zorder=2)
    ax_main.axhline(0, color="black", linewidth=0.5, alpha=0.4, zorder=0)
    ax_main.axvline(0, color="black", linewidth=0.5, alpha=0.4, zorder=0)
    ax_main.grid(True, alpha=0.25, linestyle="--", linewidth=0.5)
    ax_main.set_xlim(0, f_max)
    ax_main.set_ylabel("raw $-$ TARE_OFFSET   (counts)", fontsize=11)
    ax_main.set_title("HX711 + DYLY-103 force-sensor calibration",
                      fontsize=13, pad=14, weight="bold")
    ax_main.legend(loc="lower right", fontsize=10, framealpha=0.95)

    # Fit-quality annotation box
    if n_points >= 2:
        mean_d = sum(deltas) / len(deltas)
        ss_tot = sum((d - mean_d) ** 2 for d in deltas)
        ss_res = sum((d - k * f) ** 2 for f, d in zip(forces, deltas))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
        max_abs_res = max(abs(d - k * f) for f, d in zip(forces, deltas))
        max_abs_res_mN = max_abs_res / abs(k) * 1000.0
        ann = (f"R²         = {r2:.6f}\n"
               f"slope      = {k:,.1f} counts/N\n"
               f"resolution = {1000.0 / abs(k):.4f} mN/count\n"
               f"max |res|  = {max_abs_res:.1f} counts  ({max_abs_res_mN:.2f} mN)\n"
               f"n          = {n_points} points")
    else:
        ann = (f"slope      = {k:,.1f} counts/N\n"
               f"resolution = {1000.0 / abs(k):.4f} mN/count\n"
               f"(single-point — R² not computable)")
    ax_main.text(
        0.025, 0.97, ann, transform=ax_main.transAxes,
        verticalalignment="top", fontsize=9.5, family="monospace",
        bbox=dict(boxstyle="round,pad=0.5",
                  facecolor="white", edgecolor="#bbbbbb", alpha=0.95),
    )

    # Secondary x-axis (grams)
    sec = ax_main.secondary_xaxis(
        "top",
        functions=(lambda f: f * 1000.0 / 9.80665,
                   lambda m: m * 9.80665 / 1000.0),
    )
    sec.set_xlabel("equivalent mass   (g)", fontsize=10)
    sec.tick_params(labelsize=9)

    # ------------------------------------------------------------ residuals
    if ax_res is not None:
        residuals = [d - k * f for f, d in zip(forces, deltas)]
        ax_res.errorbar(
            forces, residuals, yerr=yerr,
            fmt="o", color=pt_color, markersize=6,
            markeredgecolor="white", markeredgewidth=1.0,
            ecolor=pt_color, elinewidth=1.0, capsize=4,
        )
        ax_res.axhline(0, color=fit_color, linewidth=1.0, alpha=0.8)
        ax_res.grid(True, alpha=0.25, linestyle="--", linewidth=0.5)
        ax_res.set_xlabel("applied force F   (N)", fontsize=11)
        ax_res.set_ylabel("residual\n(counts)", fontsize=10)

        # Right axis in mN
        sec_y = ax_res.secondary_yaxis(
            "right",
            functions=(lambda c: c * 1000.0 / abs(k),
                       lambda m: m * abs(k) / 1000.0),
        )
        sec_y.set_ylabel("residual\n(mN)", fontsize=10)
        sec_y.tick_params(labelsize=9)
    else:
        ax_main.set_xlabel("applied force F   (N)", fontsize=11)

    fig.savefig(png_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  plot -> {png_path}")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    cli_port = sys.argv[1] if len(sys.argv) > 1 else None

    print("=" * 64)
    print("  HX711 + DYLY-103 force-sensor calibration")
    print("=" * 64)
    print()
    print("Before starting, make sure:")
    print("  [ ] uno_force.ino has been Uploaded to the UNO")
    print("  [ ] Arduino IDE Serial Monitor is CLOSED")
    print("  [ ] No other Python script is using the UNO COM port")
    print("  [ ] Load cell/head assembly is loaded along the same local")
    print("      sensing direction used in the experiment.")
    print("      If the stamp head points downward in the rig, it is OK to")
    print("      flip the whole assembly so weights can sit on the stamp face;")
    print("      after reinstalling, run live_tare and confirm contact is positive.")
    print()

    port = find_uno_port(cli_port)
    print(f"\nOpening {port} @ {BAUD} ...")
    try:
        ser = open_serial(port)
    except serial.SerialException as exc:
        sys.exit(f"  could not open {port}: {exc}")

    if not wait_for_banner(ser):
        print("  ! no UNO_force banner seen. Continuing anyway, but check that "
              "the right .ino is on the board.")

    # ------------------------------------------------------------------- TARE
    print("\nSTEP 1 -- TARE (no-load baseline)")
    print("  Remove any load. Don't touch the sensor. Let it sit ~5 s")
    print("  to stabilise (thermal/mechanical settling).")
    input("  Press Enter to start tare ... ")
    tare_raw = read_raw_samples(ser, TARE_SAMPLES, label="tare ")
    t_mean, t_std, t_min, t_max = stats(tare_raw)
    tare_offset = round(t_mean)
    print(f"  TARE_OFFSET = {tare_offset}")
    print(f"  noise: std = {t_std:.1f} counts, peak-peak = {t_max - t_min} counts")
    if t_std > 1000:
        print("  ! tare noise is unusually high. Check wiring, vibration, or "
              "make sure nothing is touching the cell.")

    # ----------------------------------------------------------- KNOWN MASSES
    print("\nSTEP 2 -- KNOWN MASSES")
    print("  Apply masses one at a time. For each, type the mass in grams,")
    print("  press Enter, place the mass, then press Enter again to sample.")
    print("  Use 3-5 masses spread across your expected range")
    print("  (e.g., 100 g, 500 g, 1000 g, 2000 g, 4000 g for a 5 kg cell).")
    print("  Press Enter on an empty mass prompt to finish.\n")

    points = []  # list of (mass_g, mean_raw, std_raw, F_N)
    while True:
        prompt = f"  point {len(points) + 1} -- mass in grams (Enter to finish): "
        ans = input(prompt).strip()
        if not ans:
            break
        try:
            mass_g = float(ans)
        except ValueError:
            print("    not a number, try again")
            continue
        if mass_g <= 0:
            print("    mass must be > 0")
            continue
        input(f"    place {mass_g:.1f} g on the cell, then press Enter ... ")
        ser.reset_input_buffer()
        raw_vals = read_raw_samples(ser, POINT_SAMPLES, label=f"{mass_g:g}g ")
        r_mean, r_std, r_min, r_max = stats(raw_vals)
        force_n = mass_g * GRAVITY / 1000.0
        delta = r_mean - tare_offset
        print(f"    mean raw = {r_mean:.1f}   std = {r_std:.1f}   "
              f"delta = {delta:+.1f}   F = {force_n:.4f} N")
        points.append((mass_g, r_mean, r_std, force_n))

    ser.close()

    if len(points) < 1:
        sys.exit("\n  no mass points entered. Aborting.")

    # --------------------------------------------------------------------- FIT
    forces = [p[3] for p in points]
    deltas = [p[1] - tare_offset for p in points]

    if len(points) == 1:
        # Single-point: slope is just delta/F, no R^2 meaningful.
        k = deltas[0] / forces[0]
        r2 = float("nan")
        print("\n  WARNING: only 1 mass point. Trusting the DYLY-103 0.03% "
              "linearity spec, but you cannot verify linearity from one point. "
              "Add 2-3 more points later if you can.")
    else:
        k, r2 = fit_through_origin(forces, deltas)

    print()
    print("=" * 64)
    print(f"  TARE_OFFSET        = {tare_offset}")
    print(f"  CALIBRATION_FACTOR = {k:.4f}   (counts per Newton)")
    if len(points) >= 2:
        print(f"  R^2                = {r2:.6f}   ({len(points)} points)")
    else:
        print(f"  R^2                = n/a (single-point calibration)")
    print(f"  resolution         ~ {1.0 / abs(k) * 1000:.3f} mN per count")
    print("=" * 64)
    print()
    print("Edit uno_force.ino lines 34-35 to:")
    print(f"  const long  TARE_OFFSET        = {tare_offset};")
    print(f"  const float CALIBRATION_FACTOR = {k:.4f};")
    print()
    print("Then re-Verify and Upload from Arduino IDE. The `scaled_N` column")
    print("in the serial stream will then be real Newtons.")

    # ----------------------------------------------------------------- saving
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    here = Path(__file__).parent
    log_path = here / f"force_calibration_{ts}.csv"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("# HX711 + DYLY-103 calibration\n")
        f.write(f"# timestamp: {datetime.now().isoformat(timespec='seconds')}\n")
        f.write(f"# port: {port}\n")
        f.write(f"# TARE_OFFSET = {tare_offset}\n")
        f.write(f"# tare_std_counts = {t_std:.2f}\n")
        f.write(f"# CALIBRATION_FACTOR = {k:.4f}\n")
        f.write(f"# R2 = {r2:.6f}\n")
        f.write("mass_g,F_N,mean_raw,std_raw,delta_raw\n")
        for mass_g, mean_raw, std_raw, force_n in points:
            f.write(f"{mass_g},{force_n:.4f},{mean_raw:.1f},"
                    f"{std_raw:.1f},{mean_raw - tare_offset:+.1f}\n")
    print(f"Log written: {log_path}")

    plot_fit(points, tare_offset, k, here / f"force_calibration_{ts}.png")


if __name__ == "__main__":
    main()
