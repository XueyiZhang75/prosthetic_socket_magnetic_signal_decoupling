"""Stage 1 noise floor measurement protocol.

Usage:
    python stage1_noise.py <preset>           run one preset
    python stage1_noise.py --summary           print accumulated summary table

<preset> ∈ {low_noise, balanced, fast, fastest}

For each preset, the script:
    1. Rewrites circuitpython/code.py to set PRESET = <preset>
    2. Copies code.py to /Volumes/CIRCUITPY/ (triggers board reload)
    3. Soft-reboots CircuitPython via Ctrl-D over the serial port
    4. Waits 5s for warm-up
    5. Records 60s of magnetic data
    6. Computes mean, sigma_raw, sigma_detrend, drift, p2p for each axis
    7. Saves raw CSV to stage1_data/<preset>_<timestamp>_raw.csv
    8. Appends a row to stage1_data/summary.csv
"""

import glob
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import serial


def find_port():
    candidates = sorted(glob.glob("/dev/cu.usbmodem*"))
    if not candidates:
        sys.exit("no /dev/cu.usbmodem* device found — is the board plugged in?")
    return candidates[0]


PORT = find_port()
BAUD = 115200
WARMUP_S = 5.0
DURATION_S = 60.0

HERE = Path(__file__).parent
CODE_PY_LOCAL = HERE / "circuitpython" / "code.py"
CODE_PY_BOARD = Path("/Volumes/CIRCUITPY/code.py")
OUTPUT_DIR = HERE / "stage1_data"
SUMMARY_CSV = OUTPUT_DIR / "summary.csv"

VALID_PRESETS = ["low_noise", "balanced", "fast", "fastest"]


def set_preset(preset):
    text = CODE_PY_LOCAL.read_text()
    new_text, n = re.subn(
        r'^PRESET = ".*"$', f'PRESET = "{preset}"', text, count=1, flags=re.MULTILINE
    )
    if n == 0:
        raise RuntimeError("could not find PRESET line in code.py")
    CODE_PY_LOCAL.write_text(new_text)
    shutil.copy(CODE_PY_LOCAL, CODE_PY_BOARD)


def collect(duration_s):
    ser = serial.Serial(PORT, BAUD, timeout=0.5)
    time.sleep(1)
    ser.reset_input_buffer()
    ser.write(b"\x04")  # Ctrl-D = CircuitPython soft reboot
    print(f"  reboot sent, warming up {WARMUP_S:.0f}s...")
    time.sleep(WARMUP_S)
    ser.reset_input_buffer()

    ts, bx, by, bz = [], [], [], []
    print(f"  recording {duration_s:.0f}s — DO NOT TOUCH THE SENSOR")
    t0 = time.time()
    while time.time() - t0 < duration_s:
        line = ser.readline().decode(errors="ignore").strip()
        if not line:
            continue
        if line.startswith("MLX90393") or line.startswith("t_ms"):
            continue
        parts = line.split(",")
        if len(parts) != 4:
            continue
        try:
            # device prints integers in milli-µT to skip costly float formatting on SAMD21
            ts.append(int(parts[0]) / 1000.0)
            bx.append(int(parts[1]) / 1000.0)
            by.append(int(parts[2]) / 1000.0)
            bz.append(int(parts[3]) / 1000.0)
        except ValueError:
            continue
    ser.close()
    return np.array(ts), np.array(bx), np.array(by), np.array(bz)


def axis_stats(x, t):
    slope, intercept = np.polyfit(t, x, 1)
    detrended = x - (slope * t + intercept)
    return dict(
        mean=float(np.mean(x)),
        sigma_raw=float(np.std(x, ddof=1)),
        sigma_detrend=float(np.std(detrended, ddof=1)),
        drift=float(slope),
        p2p=float(x.max() - x.min()),
    )


def run_one(preset):
    if preset not in VALID_PRESETS:
        sys.exit(f"preset must be one of {VALID_PRESETS}")
    if not CODE_PY_BOARD.parent.exists():
        sys.exit("CIRCUITPY drive not mounted — is the board plugged in?")

    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n=== Stage 1 noise floor: preset={preset} ===")
    set_preset(preset)
    print(f"  PRESET=\"{preset}\" written to code.py and synced to CIRCUITPY")

    ts, bx, by, bz = collect(DURATION_S)
    n = len(ts)
    if n < 10:
        sys.exit(f"only {n} samples collected — something is wrong")
    rate = (n - 1) / (ts[-1] - ts[0])
    print(f"  → {n} samples in {ts[-1]-ts[0]:.1f}s = {rate:.1f} Hz\n")

    results = {"Bx": axis_stats(bx, ts), "By": axis_stats(by, ts), "Bz": axis_stats(bz, ts)}

    print(f"  {'axis':>4}  {'mean (µT)':>12}  {'σ_raw':>9}  {'σ_detrend':>11}  {'drift µT/s':>12}  {'p2p':>8}")
    for axis, s in results.items():
        print(f"  {axis:>4}  {s['mean']:>+12.3f}  {s['sigma_raw']:>9.4f}  "
              f"{s['sigma_detrend']:>11.4f}  {s['drift']:>+12.5f}  {s['p2p']:>8.3f}")

    raw_file = OUTPUT_DIR / f"{preset}_{timestamp}_raw.csv"
    np.savetxt(
        raw_file,
        np.column_stack([ts, bx, by, bz]),
        delimiter=",",
        header="t_s,Bx_uT,By_uT,Bz_uT",
        comments="",
    )
    print(f"\n  raw   → stage1_data/{raw_file.name}")

    first = not SUMMARY_CSV.exists()
    with open(SUMMARY_CSV, "a") as f:
        if first:
            f.write("timestamp,preset,rate_Hz,n,axis,mean_uT,sigma_raw_uT,"
                    "sigma_detrend_uT,drift_uT_per_s,p2p_uT\n")
        for axis, s in results.items():
            f.write(f"{timestamp},{preset},{rate:.2f},{n},{axis},"
                    f"{s['mean']:.4f},{s['sigma_raw']:.4f},{s['sigma_detrend']:.4f},"
                    f"{s['drift']:.5f},{s['p2p']:.4f}\n")
    print(f"  summary → stage1_data/summary.csv (appended 3 rows)")


def print_summary():
    if not SUMMARY_CSV.exists():
        sys.exit("no summary yet — run a preset first")
    import csv
    rows = list(csv.DictReader(SUMMARY_CSV.open()))
    latest = {}
    for r in rows:
        latest[(r["preset"], r["axis"])] = r

    print(f"\n=== Stage 1 noise floor summary (latest per preset/axis) ===\n")
    print(f"  {'preset':<10} {'rate Hz':>8}  {'axis':>4} "
          f"{'mean µT':>10} {'σ_raw':>8} {'σ_detrend':>11} {'drift µT/s':>12}")
    for preset in VALID_PRESETS:
        for axis in ("Bx", "By", "Bz"):
            r = latest.get((preset, axis))
            if r is None:
                continue
            print(f"  {preset:<10} {float(r['rate_Hz']):>8.1f}  {axis:>4} "
                  f"{float(r['mean_uT']):>+10.2f} {float(r['sigma_raw_uT']):>8.3f} "
                  f"{float(r['sigma_detrend_uT']):>11.3f} {float(r['drift_uT_per_s']):>+12.4f}")
        print()


def main():
    if len(sys.argv) != 2:
        sys.exit(f"Usage:\n  python stage1_noise.py <preset>   # preset ∈ {VALID_PRESETS}\n"
                 f"  python stage1_noise.py --summary")
    arg = sys.argv[1]
    if arg == "--summary":
        print_summary()
    else:
        run_one(arg)


if __name__ == "__main__":
    main()
