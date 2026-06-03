"""Measure the noise floor of the fixed MLX90393 firmware.

Usage:
    python stage1_noise.py             record 60 s using the firmware on the board
    python stage1_noise.py --duration 120
    python stage1_noise.py --summary

This script no longer edits circuitpython/code.py or switches presets. The
board firmware is intentionally fixed to:

    OSR_1 + FILTER_1 + RESOLUTION_18

If the fixed setting needs to change, edit circuitpython/code.py and copy it to
the CIRCUITPY drive.
"""

import argparse
import csv
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import serial

from mlx_serial import find_mlx_port


BAUD = 115200
DEFAULT_DURATION_S = 60.0
CONFIG_NAME = "fixed_fast"

HERE = Path(__file__).parent
OUTPUT_DIR = HERE / "stage1_data"
SUMMARY_CSV = OUTPUT_DIR / "summary.csv"


def collect(port, duration_s):
    ser = serial.Serial(port, BAUD, timeout=0.5)
    time.sleep(1.0)
    ser.reset_input_buffer()

    ts, bx, by, bz = [], [], [], []
    print(f"  recording {duration_s:.0f}s with current board firmware")
    print("  keep the sensor still")
    t0 = time.time()
    while time.time() - t0 < duration_s:
        line = ser.readline().decode(errors="ignore").strip()
        if not line:
            continue
        if line.startswith("MLX90393") or line.startswith("t_ms"):
            print(f"  {line}")
            continue
        if line.startswith("read_failed"):
            continue
        parts = line.split(",")
        if len(parts) != 4:
            continue
        try:
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
    return {
        "mean": float(np.mean(x)),
        "sigma_raw": float(np.std(x, ddof=1)),
        "sigma_detrend": float(np.std(detrended, ddof=1)),
        "drift": float(slope),
        "p2p": float(x.max() - x.min()),
    }


def run(duration_s, port=None):
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    port = port or find_mlx_port()

    print(f"\n=== MLX90393 noise floor: {CONFIG_NAME} ===")
    print(f"  port: {port}")
    ts, bx, by, bz = collect(port, duration_s)
    n = len(ts)
    if n < 10:
        sys.exit(f"only {n} samples collected; check the MLX serial stream")
    rate = (n - 1) / (ts[-1] - ts[0])
    print(f"  -> {n} samples in {ts[-1]-ts[0]:.1f}s = {rate:.1f} Hz\n")

    results = {
        "Bx": axis_stats(bx, ts),
        "By": axis_stats(by, ts),
        "Bz": axis_stats(bz, ts),
    }

    print(
        f"  {'axis':>4}  {'mean (uT)':>12}  {'sigma_raw':>10}  "
        f"{'sigma_detrend':>14}  {'drift uT/s':>12}  {'p2p':>8}"
    )
    for axis, stats in results.items():
        print(
            f"  {axis:>4}  {stats['mean']:>+12.3f}  "
            f"{stats['sigma_raw']:>10.4f}  "
            f"{stats['sigma_detrend']:>14.4f}  "
            f"{stats['drift']:>+12.5f}  {stats['p2p']:>8.3f}"
        )

    raw_file = OUTPUT_DIR / f"{CONFIG_NAME}_{timestamp}_raw.csv"
    np.savetxt(
        raw_file,
        np.column_stack([ts, bx, by, bz]),
        delimiter=",",
        header="t_s,Bx_uT,By_uT,Bz_uT",
        comments="",
    )
    print(f"\n  raw -> stage1_data/{raw_file.name}")

    first = not SUMMARY_CSV.exists()
    with SUMMARY_CSV.open("a", newline="") as f:
        writer = csv.writer(f)
        if first:
            writer.writerow(
                [
                    "timestamp",
                    "config",
                    "rate_Hz",
                    "n",
                    "axis",
                    "mean_uT",
                    "sigma_raw_uT",
                    "sigma_detrend_uT",
                    "drift_uT_per_s",
                    "p2p_uT",
                ]
            )
        for axis, stats in results.items():
            writer.writerow(
                [
                    timestamp,
                    CONFIG_NAME,
                    f"{rate:.2f}",
                    n,
                    axis,
                    f"{stats['mean']:.4f}",
                    f"{stats['sigma_raw']:.4f}",
                    f"{stats['sigma_detrend']:.4f}",
                    f"{stats['drift']:.5f}",
                    f"{stats['p2p']:.4f}",
                ]
            )
    print("  summary -> stage1_data/summary.csv")


def print_summary():
    if not SUMMARY_CSV.exists():
        sys.exit("no summary yet; run a measurement first")
    rows = list(csv.DictReader(SUMMARY_CSV.open()))
    latest = {}
    for row in rows:
        config = row.get("config") or row.get("preset") or ""
        latest[(config, row["axis"])] = row

    print("\n=== MLX90393 noise floor summary (latest per config/axis) ===\n")
    print(
        f"  {'config':<12} {'rate Hz':>8}  {'axis':>4} "
        f"{'mean uT':>10} {'sigma_raw':>10} {'sigma_detrend':>14}"
    )
    for config in sorted({key[0] for key in latest}):
        for axis in ("Bx", "By", "Bz"):
            row = latest.get((config, axis))
            if row is None:
                continue
            print(
                f"  {config:<12} {float(row['rate_Hz']):>8.1f}  {axis:>4} "
                f"{float(row['mean_uT']):>+10.2f} "
                f"{float(row['sigma_raw_uT']):>10.3f} "
                f"{float(row['sigma_detrend_uT']):>14.3f}"
            )
        print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--duration", type=float, default=DEFAULT_DURATION_S)
    parser.add_argument("--port", default=None)
    args = parser.parse_args()

    if args.summary:
        print_summary()
    else:
        run(args.duration, args.port)


if __name__ == "__main__":
    main()
