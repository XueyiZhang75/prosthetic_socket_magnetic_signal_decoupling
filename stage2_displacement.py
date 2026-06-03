"""Stage 2 — pure displacement experiment (vertical air gap, F ≈ 0).

Protocol:
    Magnet source (bead chain / patch / Halbach / ...) mounted on Mark-10
    column. MLX90393 fixed flat on base plate. Mark-10 sets a known vertical
    gap q between the magnet's bottom face and the sensor's top face.
    No contact, so F ≈ 0.

    For each q in the predefined sequence:
        1. Use Mark-10 to set the target q (Mark-10 step resolution is 0.02 mm)
        2. Press Enter — script silently SETTLES for SETTLE_S, then RECORDS for
           RECORD_S. Stats are computed from the LAST TAIL_FRAC of the window,
           because the first chunk usually still contains fixture relaxation.

Output:
    stage2_data/session_<ts>/
        q<q>mm_<dir>_raw.csv     raw Bx/By/Bz samples (full window) for re-analysis
        summary.csv               one row per q-point: mean ± σ from tail fraction
        B_vs_q.png                auto-generated 3-axis B(q) plot
"""

import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import serial

from mlx_serial import find_mlx_port as find_port

BAUD = 115200
SETTLE_S = 5.0          # silent wait after Enter (drains buffer, lets fixture relax)
RECORD_S = 20.0         # raw recording window after settle
TAIL_FRAC = 0.5         # fraction of window used for stats (last TAIL_FRAC)

# === q sampling sequence (mm) ===
# Mark-10 resolution is 0.02 mm. Uniform 1 mm grid from 40 → 1 mm to densely
# sample the full decay curve (useful for single-bead axial alignment runs where
# dB/dq is non-trivial across the whole range), plus one extra 0.5 mm point at
# the near end where the field still changes steeply.
# Preserve "down" as far→near and "up" as near→far.
Q_DOWN = [float(q) for q in range(40, 0, -1)] + [0.5]   # 40, 39, …, 1, 0.5  (41 pts)
Q_UP = list(reversed(Q_DOWN))


HERE = Path(__file__).parent
OUTPUT_DIR = HERE / "stage2_data"


def record(ser, settle_s, dur_s):
    """Drain ser for settle_s (no storage), then capture dur_s of mag samples.
    Device sends milli-µT integers per Stage-1 protocol; we divide by 1000."""
    print(f"   settling {settle_s:.0f}s …", end="", flush=True)
    t_end = time.time() + settle_s
    while time.time() < t_end:
        ser.readline()
    ser.reset_input_buffer()

    print(f" recording {dur_s:.0f}s …", end="", flush=True)
    bx, by, bz = [], [], []
    t0 = time.time()
    while time.time() - t0 < dur_s:
        line = ser.readline().decode(errors="ignore").strip()
        if not line:
            continue
        if line.startswith("MLX90393") or line.startswith("t_ms"):
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
    print(" done")
    return np.array(bx), np.array(by), np.array(bz)


def tail_stats(arr, frac):
    """mean, std (ddof=1) over the last `frac` of arr."""
    n = len(arr)
    tail = arr[int(n * (1 - frac)):]
    return float(np.mean(tail)), float(np.std(tail, ddof=1)), len(tail)


def plot_summary(summary_path, png_path):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not available, skipping plot")
        return

    import csv
    rows = list(csv.DictReader(summary_path.open()))
    if not rows:
        return

    q   = np.array([float(r["q_mm"]) for r in rows])
    dn  = np.array([r["direction"] == "down" for r in rows])
    up  = ~dn
    mbx = np.array([float(r["mean_Bx_uT"]) for r in rows])
    mby = np.array([float(r["mean_By_uT"]) for r in rows])
    mbz = np.array([float(r["mean_Bz_uT"]) for r in rows])
    sbx = np.array([float(r["sigma_Bx_uT"]) for r in rows])
    sby = np.array([float(r["sigma_By_uT"]) for r in rows])
    sbz = np.array([float(r["sigma_Bz_uT"]) for r in rows])

    fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
    for ax, m, s, name, color in zip(
        axes, [mbx, mby, mbz], [sbx, sby, sbz],
        ["Bx", "By", "Bz"], ["tab:red", "tab:green", "tab:blue"],
    ):
        if dn.any():
            ax.errorbar(q[dn], m[dn], yerr=s[dn], fmt="o-", color=color,
                        label="down (far→near)", capsize=3, markersize=4)
        if up.any():
            ax.errorbar(q[up], m[up], yerr=s[up], fmt="s--", color=color, alpha=0.55,
                        label="up (near→far)", capsize=3, markersize=4)
        ax.set_ylabel(f"{name} (µT)")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best", fontsize=9)
    axes[-1].set_xlabel("gap q (mm)")
    axes[0].set_title(f"Stage 2: B vs vertical gap q  "
                      f"(stats from last {TAIL_FRAC*100:.0f}% of {RECORD_S:.0f}s window)")
    fig.tight_layout()
    fig.savefig(png_path, dpi=120)
    print(f"  plot → {png_path}")


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = OUTPUT_DIR / f"session_{timestamp}"
    session_dir.mkdir()
    summary_file = session_dir / "summary.csv"

    sequence = [(q, "down") for q in Q_DOWN] + [(q, "up") for q in Q_UP]

    print("\n=== Stage 2: pure displacement (vertical gap, F ≈ 0) ===")
    print(f"  session : {session_dir.name}")
    print(f"  points  : {len(sequence)}  ({len(Q_DOWN)} down + {len(Q_UP)} up)")
    print(f"  timing  : {SETTLE_S:.0f}s settle + {RECORD_S:.0f}s record per point "
          f"(stats from last {int(RECORD_S*TAIL_FRAC)}s)")
    print(f"  down q  : {Q_DOWN} mm")
    print(f"  up   q  : {Q_UP} mm\n")
    print("Pre-flight checklist:")
    print("  [ ] Magnet source rigidly mounted on Mark-10 fixture, centered above sensor")
    print("  [ ] MLX90393 fixed flat on base plate, not touching anything")
    print("  [ ] Mark-10 zeroed: q=0 = position where magnet barely touches sensor")
    print("  [ ] Mark-10 force reads ≈ 0 N (no contact load)")
    print(f"  [ ] code.py preset = low_noise (deploy if not)")
    print("  [ ] Serial Studio / other serial readers closed")
    print(f"  [ ] Mark-10 currently at q = {Q_DOWN[0]:.1f} mm (first 'down' point)\n")
    input("Press Enter when ready to start session... ")

    port = find_port()
    print(f"\nusing serial port: {port}\n")
    ser = serial.Serial(port, BAUD, timeout=0.5)
    time.sleep(1)

    with open(summary_file, "w") as f:
        f.write("q_mm,direction,n_tail,mean_Bx_uT,sigma_Bx_uT,"
                "mean_By_uT,sigma_By_uT,mean_Bz_uT,sigma_Bz_uT\n")

        for i, (q, direction) in enumerate(sequence, 1):
            print(f"\n[{i:2d}/{len(sequence)}] {direction:<4}  target q = {q} mm")
            print(f"   1) move Mark-10 to {q} mm")
            try:
                input(f"   2) press Enter (Ctrl+C to abort the session): ")
            except KeyboardInterrupt:
                print("\n\n  session aborted by user — data so far is saved")
                break

            ser.reset_input_buffer()
            bx, by, bz = record(ser, SETTLE_S, RECORD_S)
            n = len(bx)
            if n < 10:
                print(f"   ! only {n} samples — skipping")
                continue

            mbx, sbx, nt = tail_stats(bx, TAIL_FRAC)
            mby, sby, _  = tail_stats(by, TAIL_FRAC)
            mbz, sbz, _  = tail_stats(bz, TAIL_FRAC)
            print(f"     Bx = {mbx:+9.2f} ± {sbx:6.3f} µT")
            print(f"     By = {mby:+9.2f} ± {sby:6.3f} µT")
            print(f"     Bz = {mbz:+9.2f} ± {sbz:6.3f} µT   "
                  f"(stats from last {nt}/{n} samples)")

            f.write(f"{q},{direction},{nt},"
                    f"{mbx:.4f},{sbx:.4f},{mby:.4f},{sby:.4f},{mbz:.4f},{sbz:.4f}\n")
            f.flush()

            np.savetxt(
                session_dir / f"q{q}mm_{direction}_raw.csv",
                np.column_stack([bx, by, bz]),
                delimiter=",",
                header="Bx_uT,By_uT,Bz_uT",
                comments="",
            )

    ser.close()
    print(f"\n=== Session done. Summary: {summary_file} ===")
    plot_summary(summary_file, session_dir / "B_vs_q.png")


if __name__ == "__main__":
    main()
