"""Stage B — signal health check + baseline acquisition (B.1–B.4).

Each sub-step records a fixed window from the MLX90393 (QT Py, low_noise preset
assumed already deployed by Stage B.0) and writes a raw CSV plus an appended row
to B_baseline_summary.csv.

Usage (run one step per call so the operator can rearrange the magnet between):
    python stageB_baseline.py b1                    # creates a new session dir
    python stageB_baseline.py b2 --session <dir>
    python stageB_baseline.py b3 --session <dir>
    python stageB_baseline.py b4 --session <dir>

The b1 call prints `SESSION=<path>`; pass that path to b2/b3/b4 so all four land
in the same decouple_data/session_<ts>/ folder.

Steps:
    b1  signal health   40 s  — operator moves the magnet by hand during the
                                window; large peak-to-peak confirms B responds.
    b2  no magnet        60 s — magnet sample removed / far away.
    b3  magnet no-contact 60 s — magnet mounted, not contacting → defines B0.
    b4  stage motion     60 s — Mark-10 driven up/down (no contact) during window.
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import serial

from mlx_serial import find_mlx_port as find_port

BAUD = 115200
SETTLE_S = 3.0

HERE = Path(__file__).parent
OUTPUT_ROOT = HERE / "decouple_data"

STEPS = {
    "b1": dict(dur=40.0, fname="B1_signal_health.csv",
               label="signal health (move the magnet by hand NOW)"),
    "b2": dict(dur=60.0, fname="baseline_no_magnet.csv",
               label="no-magnet background"),
    "b3": dict(dur=60.0, fname="baseline_magnet_no_contact.csv",
               label="magnet mounted, NOT contacting -> defines B0"),
    "b4": dict(dur=60.0, fname="baseline_stage_motion.csv",
               label="Mark-10 moving up/down, NO contact"),
}


def record(ser, settle_s, dur_s, live=False):
    """Drain ser for settle_s, then capture dur_s of samples (t_s, Bx, By, Bz)."""
    print(f"  settling {settle_s:.0f}s ...", flush=True)
    t_end = time.time() + settle_s
    while time.time() < t_end:
        ser.readline()
    ser.reset_input_buffer()

    print(f"  recording {dur_s:.0f}s ...", flush=True)
    ts, bx, by, bz = [], [], [], []
    t0 = time.time()
    next_live = t0 + 2.0
    while time.time() - t0 < dur_s:
        line = ser.readline().decode(errors="ignore").strip()
        if not line or line.startswith("MLX90393") or line.startswith("t_ms"):
            continue
        parts = line.split(",")
        if len(parts) != 4:
            continue
        try:
            t = time.time() - t0
            x, y, z = (int(parts[1]) / 1000.0,
                       int(parts[2]) / 1000.0,
                       int(parts[3]) / 1000.0)
        except ValueError:
            continue
        ts.append(t); bx.append(x); by.append(y); bz.append(z)
        if live and time.time() >= next_live:
            mag = (x * x + y * y + z * z) ** 0.5
            print(f"    t={t:5.1f}s  B=({x:+8.1f},{y:+8.1f},{z:+8.1f})  |B|={mag:7.1f} uT")
            next_live += 2.0
    print("  done")
    return (np.array(ts), np.array(bx), np.array(by), np.array(bz))


def axis_stats(x, t):
    slope, intercept = np.polyfit(t, x, 1)
    detr = x - (slope * t + intercept)
    return dict(mean=float(np.mean(x)), sigma=float(np.std(x, ddof=1)),
                sigma_detrend=float(np.std(detr, ddof=1)),
                drift=float(slope), p2p=float(x.max() - x.min()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=STEPS.keys())
    ap.add_argument("--session", default=None,
                    help="existing session dir (omit on b1 to create a new one)")
    args = ap.parse_args()
    step = args.step
    cfg = STEPS[step]

    if args.session:
        session_dir = Path(args.session)
        session_dir.mkdir(parents=True, exist_ok=True)
    else:
        OUTPUT_ROOT.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = OUTPUT_ROOT / f"session_{ts}"
        session_dir.mkdir(parents=True)

    print(f"\n=== Stage B / {step.upper()} : {cfg['label']} ===")
    print(f"  session : {session_dir}")
    print(f"  window  : {SETTLE_S:.0f}s settle + {cfg['dur']:.0f}s record (low_noise)\n")

    port = find_port()
    ser = serial.Serial(port, BAUD, timeout=0.5)
    time.sleep(1)
    print(f"  port    : {port}")

    t, bx, by, bz = record(ser, SETTLE_S, cfg["dur"], live=(step == "b1"))
    ser.close()

    n = len(t)
    if n < 10:
        sys.exit(f"only {n} samples — check the serial link")
    rate = (n - 1) / (t[-1] - t[0])
    res = {"Bx": axis_stats(bx, t), "By": axis_stats(by, t), "Bz": axis_stats(bz, t)}

    print(f"\n  -> {n} samples, {rate:.1f} Hz")
    print(f"  {'axis':>4} {'mean uT':>10} {'sigma':>8} {'drift uT/s':>12} {'p2p uT':>9}")
    for a, s in res.items():
        print(f"  {a:>4} {s['mean']:>+10.2f} {s['sigma']:>8.3f} "
              f"{s['drift']:>+12.5f} {s['p2p']:>9.2f}")
    mag = float(np.mean(np.sqrt(bx**2 + by**2 + bz**2)))
    print(f"  |B| mean = {mag:.2f} uT")
    if step == "b3":
        print(f"\n  >>> B0 = ({res['Bx']['mean']:+.3f}, {res['By']['mean']:+.3f}, "
              f"{res['Bz']['mean']:+.3f}) uT  <<<  (use for dB = B - B0)")

    raw = session_dir / cfg["fname"]
    np.savetxt(raw, np.column_stack([t, bx, by, bz]), delimiter=",",
               header="t_s,Bx_uT,By_uT,Bz_uT", comments="")
    print(f"\n  raw -> {raw}")

    summ = session_dir / "B_baseline_summary.csv"
    first = not summ.exists()
    with open(summ, "a") as f:
        if first:
            f.write("step,timestamp,n,rate_Hz,axis,mean_uT,sigma_uT,"
                    "sigma_detrend_uT,drift_uT_per_s,p2p_uT\n")
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        for a, s in res.items():
            f.write(f"{step},{now},{n},{rate:.2f},{a},{s['mean']:.4f},"
                    f"{s['sigma']:.4f},{s['sigma_detrend']:.4f},"
                    f"{s['drift']:.5f},{s['p2p']:.4f}\n")
    print(f"  summary -> {summ}")
    print(f"\nSESSION={session_dir}")


if __name__ == "__main__":
    main()
