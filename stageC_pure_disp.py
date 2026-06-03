"""Stage C — pure-displacement calibration B(q), F ≈ 0.

Magnet (on the Mark-10 column) is moved relative to the fixed MLX90393 to set a
known vertical air gap q. No contact, so F ≈ 0. This yields B = g(q), the
physical basis for the Jacobian column j_q in the APMD decoupling model.

Protocol (plateau / point-by-point):
    For each q in the sequence:
        1. Jog the Mark-10 so the gap reads the target q on its screen.
        2. Press Enter. The script SETTLES for SETTLE_S (drains buffer, lets the
           fixture relax), then RECORDS for RECORD_S. Stats use the last
           TAIL_FRAC of the window.
        3. Optionally type the actual q if it differs from the target.

Sweep: down (far→near) then up (near→far) to expose any hysteresis.

Output: decouple_data/session_<ts>/
    C_q<q>_<dir>_raw.csv   raw Bx/By/Bz samples (full window)
    C_summary.csv          one row per q-point: mean ± σ, ΔB = B − B0, |B|
    C_B_vs_q.png           B(q) and ΔB(q) plots
"""

import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import serial

from mlx_serial import find_mlx_port as find_port

BAUD = 115200
SETTLE_S = 5.0          # silent settle after Enter
RECORD_S = 20.0         # raw recording window
TAIL_FRAC = 0.5         # stats taken from the last TAIL_FRAC of the window

# Baseline B0 from Stage B.3 (magnet mounted, not contacting), session_20260518_173029.
# ΔB = B − B0. Re-measure B0 if the magnet / start geometry changes.
B0 = (281.435, -1168.864, -3466.130)

# q sampling sequence (mm): 60–140 mm, integer 2 mm step → 41 gaps.
# Far range keeps the magnet in the clean far-field dipole regime, away from
# the near-field non-monotonic (magic-angle) behaviour.
# down = far→near (140→60), up = near→far (60→140).
Q_DOWN = [float(q) for q in range(140, 58, -2)]   # 140, 138, …, 60
Q_UP = list(reversed(Q_DOWN))                      # 60, 62, …, 140

HERE = Path(__file__).parent
OUTPUT_ROOT = HERE / "decouple_data"
def record(ser, settle_s, dur_s):
    """Drain ser for settle_s, then capture dur_s of mag samples (Bx,By,Bz)."""
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
    print(" done")
    return np.array(bx), np.array(by), np.array(bz)


def tail_stats(arr, frac):
    """mean, std (ddof=1) over the last `frac` of arr."""
    tail = arr[int(len(arr) * (1 - frac)):]
    return float(np.mean(tail)), float(np.std(tail, ddof=1)), len(tail)


def plot_summary(summary_path, png_path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not available, skipping plot")
        return
    import csv
    rows = list(csv.DictReader(summary_path.open()))
    if not rows:
        return
    q = np.array([float(r["q_mm"]) for r in rows])
    dn = np.array([r["direction"] == "down" for r in rows])
    up = ~dn
    cols = ["Bx", "By", "Bz"]
    colors = ["tab:red", "tab:green", "tab:blue"]

    fig, axes = plt.subplots(3, 2, figsize=(13, 11), sharex=True)
    for i, (name, color) in enumerate(zip(cols, colors)):
        m = np.array([float(r[f"mean_{name}_uT"]) for r in rows])
        s = np.array([float(r[f"sigma_{name}_uT"]) for r in rows])
        d = np.array([float(r[f"delta_{name}_uT"]) for r in rows])
        for ax, y, ylab in ((axes[i, 0], m, f"{name} (µT)"),
                            (axes[i, 1], d, f"Δ{name} = {name}−B0 (µT)")):
            if dn.any():
                ax.errorbar(q[dn], y[dn], yerr=s[dn], fmt="o-", color=color,
                            label="down", capsize=2, markersize=4)
            if up.any():
                ax.errorbar(q[up], y[up], yerr=s[up], fmt="s--", color=color,
                            alpha=0.55, label="up", capsize=2, markersize=4)
            ax.set_ylabel(ylab); ax.grid(True, alpha=0.3); ax.legend(fontsize=8)
    axes[-1, 0].set_xlabel("gap q (mm)")
    axes[-1, 1].set_xlabel("gap q (mm)")
    axes[0, 0].set_title("Stage C: raw B vs gap q")
    axes[0, 1].set_title("Stage C: ΔB = B − B0 vs gap q")
    fig.tight_layout()
    fig.savefig(png_path, dpi=120)
    print(f"  plot → {png_path}")


def main():
    OUTPUT_ROOT.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = OUTPUT_ROOT / f"session_{ts}"
    session_dir.mkdir(parents=True)
    summary_file = session_dir / "C_summary.csv"

    sequence = [(q, "down") for q in Q_DOWN] + [(q, "up") for q in Q_UP]

    print("\n=== Stage C: pure displacement B(q), F ≈ 0 ===")
    print(f"  session : {session_dir.name}")
    print(f"  points  : {len(sequence)}  ({len(Q_DOWN)} down + {len(Q_UP)} up)")
    print(f"  timing  : {SETTLE_S:.0f}s settle + {RECORD_S:.0f}s record, "
          f"stats from last {int(RECORD_S*TAIL_FRAC)}s")
    print(f"  B0      : {B0} µT  (Stage B.3)\n")
    print("Pre-flight checklist:")
    print("  [ ] code.py preset = low_noise")
    print("  [ ] magnet/sample on Mark-10, NOT contacting the sensor (air gap)")
    print("  [ ] Mark-10 force ≈ 0 N (no contact load)")
    print("  [ ] other serial readers (Serial Studio / teleplot) closed")
    print(f"  [ ] Mark-10 at q = {Q_DOWN[0]:.1f} mm (first 'down' point)\n")
    input("Press Enter when ready to start session... ")

    port = find_port()
    print(f"\nusing serial port: {port}\n")
    ser = serial.Serial(port, BAUD, timeout=0.5)
    time.sleep(1)

    with open(summary_file, "w") as f:
        f.write("q_mm,q_target_mm,direction,n_tail,"
                "mean_Bx_uT,sigma_Bx_uT,mean_By_uT,sigma_By_uT,"
                "mean_Bz_uT,sigma_Bz_uT,"
                "delta_Bx_uT,delta_By_uT,delta_Bz_uT,Bmag_uT\n")

        for i, (q_target, direction) in enumerate(sequence, 1):
            print(f"\n[{i:3d}/{len(sequence)}] {direction:<4} target q = {q_target} mm")
            print(f"   1) jog Mark-10 so the gap reads {q_target} mm")
            try:
                ans = input("   2) press Enter to record "
                            "(or type actual q in mm, Ctrl+C aborts): ").strip()
            except KeyboardInterrupt:
                print("\n\n  session aborted by user — data so far is saved")
                break
            q = float(ans) if ans else q_target

            ser.reset_input_buffer()
            bx, by, bz = record(ser, SETTLE_S, RECORD_S)
            n = len(bx)
            if n < 10:
                print(f"   ! only {n} samples — skipping")
                continue

            mbx, sbx, nt = tail_stats(bx, TAIL_FRAC)
            mby, sby, _ = tail_stats(by, TAIL_FRAC)
            mbz, sbz, _ = tail_stats(bz, TAIL_FRAC)
            dbx, dby, dbz = mbx - B0[0], mby - B0[1], mbz - B0[2]
            bmag = (mbx**2 + mby**2 + mbz**2) ** 0.5
            print(f"     Bx={mbx:+9.2f}±{sbx:5.2f}  "
                  f"By={mby:+9.2f}±{sby:5.2f}  Bz={mbz:+9.2f}±{sbz:5.2f} µT")
            print(f"     ΔB=({dbx:+.1f},{dby:+.1f},{dbz:+.1f})  |B|={bmag:.1f} µT  "
                  f"(stats from last {nt}/{n})")

            f.write(f"{q},{q_target},{direction},{nt},"
                    f"{mbx:.4f},{sbx:.4f},{mby:.4f},{sby:.4f},"
                    f"{mbz:.4f},{sbz:.4f},"
                    f"{dbx:.4f},{dby:.4f},{dbz:.4f},{bmag:.4f}\n")
            f.flush()

            np.savetxt(session_dir / f"C_q{q}_{direction}_raw.csv",
                       np.column_stack([bx, by, bz]),
                       delimiter=",", header="Bx_uT,By_uT,Bz_uT", comments="")

    ser.close()
    print(f"\n=== Stage C session done. Summary: {summary_file} ===")
    plot_summary(summary_file, session_dir / "C_B_vs_q.png")


if __name__ == "__main__":
    main()
