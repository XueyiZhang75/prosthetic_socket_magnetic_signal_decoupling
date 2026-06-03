"""Stage C (automated) -- pure displacement calibration B(q), F ~ 0.

Replaces the manual `stageC_pure_disp.py`. Mark-10 PC Control positions the
crosshead at each q target; MLX90393 records the magnetic field at each
plateau. The force sensor (UNO + HX711 + DYLY-103) is also opened, live-
tared at session start, and sampled at each plateau as a sanity-check that
F really stays ~ 0 throughout the sweep (no accidental contact, no drift).
If the force sensor is not connected, that side is skipped automatically.

This is also the reference template for all later three-stream stages
(E/F/G/H/I/J/L): Mark-10 motion + MLX field + UNO_force, all timestamped
on the PC clock.

Protocol (matches EXPERIMENT_PLAN.md section "Stage C"):
    - q sweep: 140 -> 60 mm down (far->near), then 60 -> 140 mm up (near->far)
    - At each q point: SETTLE_S seconds idle, then RECORD_S seconds of MLX data
    - Stats from the last TAIL_FRAC of the recording window
    - Then FORCE_SAMPLE_S seconds of force averaging (F should be ~ 0)
    - Magnet on Mark-10 column, sensor fixed below, no contact -> F ~ 0

Coordinate convention:
    The user manually positions the magnet at q = Q_START_MM before launching.
    The script issues `z` to zero the Mark-10 position counter, then every q
    target maps to a Mark-10 absolute position:

        mark10_target_mm = q_target - Q_START_MM

    Moving the Mark-10 DOWN (negative position) brings the magnet closer to
    the sensor, so q decreases. Moving UP increases q.

Speed note:
    Downward motion is firmware-capped at ~25 mm/min on F305 fw 1.00.25.
    Upward motion runs at the programmed speed (~200 mm/min). Position
    accuracy is unaffected. The full sweep takes ~35-40 min unattended.

Outputs (under decouple_data/session_<ts>/):
    C_summary.csv               one row per q-point, includes F_mean_N
    C_q<q>_<dir>_raw.csv        raw Bx/By/Bz samples per point
    run_log.txt                 timestamped per-step log (incl. live_tare_N)
    C_B_vs_q.png                auto-generated plot
"""

import csv
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import serial

from mark10_control import Mark10, Mark10Error
from mlx_serial import find_mlx_port
from force_serial import find_force_port, ForceReader

# ============================================================================
# CONFIG
# ============================================================================

# --- Mark-10 ---
MARK10_PORT = "COM5"
MARK10_BAUD = 9600
MARK10_SPEED_MM_PER_MIN = 200.0   # downward is firmware-capped to ~25 mm/min anyway

# --- MLX90393 ---
MLX_PORT = None                   # None -> auto-detect via list_ports
MLX_BAUD = 115200

# --- Force sensor (optional sanity-check; F is supposed to be ~0 in Stage C) ---
FORCE_ENABLED = True              # set False to skip the force-side entirely
FORCE_PORT = None                 # None -> auto-detect
FORCE_TARE_S = 2.0                # live-tare duration at session start
FORCE_SAMPLE_S = 2.0              # per-plateau force averaging window
FORCE_NONZERO_WARN_N = 0.050      # warn if |F| exceeds this on any plateau

# --- Q sweep (mm) ---
Q_START_MM = 140.0                # where the user MANUALLY positions before start
Q_DOWN = [float(q) for q in range(140, 58, -2)]   # 140, 138, ..., 60  (41 pts)
Q_UP = list(reversed(Q_DOWN))                      # 60, 62, ..., 140

# --- Per-point timing ---
SETTLE_S = 5.0
RECORD_S = 20.0
TAIL_FRAC = 0.5

# --- Baseline B0 from Stage B.3 (re-measure if magnet / geometry changes) ---
B0 = (281.435, -1168.864, -3466.130)

# --- Output ---
HERE = Path(__file__).parent
OUTPUT_ROOT = HERE / "decouple_data"


# ============================================================================
# MLX90393 helpers
# ============================================================================

def record_mlx(ser, settle_s, dur_s):
    """Drain `settle_s` of serial, then capture `dur_s` of (Bx,By,Bz) in uT.

    The QT Py firmware streams `t_ms,Bx,By,Bz` in milli-uT integers (Stage 1
    protocol). We divide each by 1000 to get uT.
    """
    print(f"   settling {settle_s:.0f}s ...", end="", flush=True)
    t_end = time.time() + settle_s
    while time.time() < t_end:
        ser.readline()
    ser.reset_input_buffer()

    print(f" recording {dur_s:.0f}s ...", end="", flush=True)
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
    tail = arr[int(len(arr) * (1 - frac)):]
    return float(np.mean(tail)), float(np.std(tail, ddof=1)), len(tail)


# ============================================================================
# Plotting (same layout as the manual stageC_pure_disp.py)
# ============================================================================

def plot_summary(summary_path, png_path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not available, skipping plot")
        return
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
        for ax, y, ylab in (
            (axes[i, 0], m, f"{name} (uT)"),
            (axes[i, 1], d, f"D{name} = {name} - B0 (uT)"),
        ):
            if dn.any():
                ax.errorbar(q[dn], y[dn], yerr=s[dn], fmt="o-", color=color,
                            label="down", capsize=2, markersize=4)
            if up.any():
                ax.errorbar(q[up], y[up], yerr=s[up], fmt="s--", color=color,
                            alpha=0.55, label="up", capsize=2, markersize=4)
            ax.set_ylabel(ylab)
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=8)
    axes[-1, 0].set_xlabel("gap q (mm)")
    axes[-1, 1].set_xlabel("gap q (mm)")
    axes[0, 0].set_title("Stage C: raw B vs gap q")
    axes[0, 1].set_title("Stage C: DB = B - B0 vs gap q")
    fig.tight_layout()
    fig.savefig(png_path, dpi=120)
    print(f"  plot -> {png_path}")


# ============================================================================
# Main
# ============================================================================

def main():
    OUTPUT_ROOT.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = OUTPUT_ROOT / f"session_{ts}"
    session_dir.mkdir(parents=True)
    summary_file = session_dir / "C_summary.csv"
    log_file = session_dir / "run_log.txt"

    sequence = [(q, "down") for q in Q_DOWN] + [(q, "up") for q in Q_UP]
    n_pts = len(sequence)
    # Rough time estimate: down motion ~25 mm/min, up motion ~200 mm/min
    total_down_mm = abs(Q_DOWN[0] - Q_DOWN[-1])
    total_up_mm = abs(Q_UP[-1] - Q_UP[0])
    move_s = total_down_mm / 25.0 * 60.0 + total_up_mm / 200.0 * 60.0
    record_s = n_pts * (SETTLE_S + RECORD_S)
    est_total_s = move_s + record_s

    print("\n=== Stage C (automated): pure displacement B(q), F ~ 0 ===")
    print(f"  session    : {session_dir.name}")
    print(f"  points     : {n_pts}  ({len(Q_DOWN)} down + {len(Q_UP)} up)")
    print(f"  per-point  : {SETTLE_S:.0f}s settle + {RECORD_S:.0f}s record")
    print(f"  q range    : {Q_DOWN[0]:.1f} -> {Q_DOWN[-1]:.1f} -> {Q_UP[-1]:.1f} mm "
          f"(step {abs(Q_DOWN[1]-Q_DOWN[0]):.1f} mm)")
    print(f"  B0         : {B0} uT")
    print(f"  est. total : ~{est_total_s/60:.1f} min "
          f"(motion {move_s/60:.1f} + record {record_s/60:.1f})\n")

    print("Pre-flight checklist:")
    print("  [ ] EasyMESUR touchscreen: Home -> PC Control ACTIVE")
    print(f"  [ ] Magnet on Mark-10 crosshead, sensor below, q = {Q_START_MM} mm NOW")
    print("  [ ] Mark-10 force ~ 0 N (no contact load)")
    print("  [ ] code.py preset = low_noise on the QT Py")
    print("  [ ] No other serial reader (Serial Studio / teleplot) on the MLX port")
    if FORCE_ENABLED:
        print("  [ ] uno_force.ino on UNO with calibrated TARE_OFFSET / CALIBRATION_FACTOR")
        print("  [ ] Arduino IDE Serial Monitor on UNO CLOSED")
    print(f"  [ ] Mark-10 has >= {abs(Q_DOWN[0]-Q_DOWN[-1])+2:.0f} mm of physical "
          "downward clearance")
    try:
        input("\nPress Enter to start (Ctrl+C to abort) ... ")
    except KeyboardInterrupt:
        print("\nAborted before start.")
        return

    # --- Mark-10 ---
    print("\nOpening Mark-10 ...")
    try:
        mark10 = Mark10(MARK10_PORT, MARK10_BAUD,
                        speed_mm_per_min=MARK10_SPEED_MM_PER_MIN)
    except Mark10Error as exc:
        sys.exit(f"\n{exc}")
    print(f"  Mark-10 ready, zeroed at q = {Q_START_MM} mm "
          f"(position counter = {mark10.position():.3f} mm)")

    # --- MLX90393 ---
    mlx_port = MLX_PORT or find_mlx_port()
    print(f"Opening MLX90393 on {mlx_port} ...")
    mlx_ser = serial.Serial(mlx_port, MLX_BAUD, timeout=0.5)
    time.sleep(1.0)
    print("  MLX90393 stream connected")

    # --- Force sensor (optional) ---
    force = None
    if FORCE_ENABLED:
        try:
            f_port = FORCE_PORT or find_force_port()
            print(f"Opening UNO_force on {f_port} ...")
            force = ForceReader(f_port)
            force.live_tare(duration_s=FORCE_TARE_S)
        except Exception as exc:
            print(f"  ! force sensor unavailable: {exc}")
            print("  ! continuing without force sanity-check (F columns will be NaN)\n")
            force = None
    else:
        print("Force sensor disabled (FORCE_ENABLED=False).\n")

    print()

    def q_to_mark10(q):
        return q - Q_START_MM

    log = log_file.open("w", encoding="utf-8")
    log.write(f"# Stage C automated session {ts}\n")
    log.write(f"# Q_START_MM={Q_START_MM} mm\n")
    log.write(f"# MARK10_SPEED_MM_PER_MIN={MARK10_SPEED_MM_PER_MIN}\n")
    log.write(f"# SETTLE_S={SETTLE_S}, RECORD_S={RECORD_S}, TAIL_FRAC={TAIL_FRAC}\n")
    log.write(f"# B0={B0}\n")
    log.write(f"# FORCE_ENABLED={FORCE_ENABLED} (live_tare_N="
              f"{force.live_tare_N if force else 'n/a'})\n")
    log.write("# columns: i, direction, q_target_mm, mark10_target_mm, "
              "mark10_pos_mm, q_actual_mm, n_samples, mean_Bx, mean_By, mean_Bz, "
              "F_mean_N, F_std_N\n")
    log.flush()

    t_session_start = time.time()
    n_done = 0

    try:
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(
                "q_mm,q_target_mm,direction,mark10_pos_mm,n_tail,"
                "mean_Bx_uT,sigma_Bx_uT,mean_By_uT,sigma_By_uT,"
                "mean_Bz_uT,sigma_Bz_uT,"
                "delta_Bx_uT,delta_By_uT,delta_Bz_uT,Bmag_uT,"
                "F_mean_N,F_std_N,F_n_samples\n"
            )

            for i, (q_target, direction) in enumerate(sequence, 1):
                t_step = time.time()
                m10_target = q_to_mark10(q_target)
                print(f"\n[{i:3d}/{n_pts}] {direction:<4} q={q_target:6.1f} mm "
                      f"  Mark10 target = {m10_target:+7.2f} mm")

                # --- move ---
                t_move = time.time()
                print("   moving Mark-10 ...", end=" ", flush=True)
                try:
                    pos = mark10.move_to(m10_target)
                except Mark10Error as exc:
                    print(f"\n  Mark-10 error: {exc}")
                    log.write(f"[{i}] MARK10_ERROR: {exc}\n")
                    log.flush()
                    break
                q_actual = Q_START_MM + pos
                print(f"arrived pos={pos:+.3f} mm  q={q_actual:.3f} mm  "
                      f"({time.time()-t_move:.1f}s)")

                # --- record ---
                bx, by, bz = record_mlx(mlx_ser, SETTLE_S, RECORD_S)
                n = len(bx)
                if n < 10:
                    msg = f"   ! only {n} MLX samples - skipping"
                    print(msg)
                    log.write(f"[{i}] SKIP: {msg}\n")
                    log.flush()
                    continue

                mbx, sbx, nt = tail_stats(bx, TAIL_FRAC)
                mby, sby, _ = tail_stats(by, TAIL_FRAC)
                mbz, sbz, _ = tail_stats(bz, TAIL_FRAC)
                dbx, dby, dbz = mbx - B0[0], mby - B0[1], mbz - B0[2]
                bmag = (mbx ** 2 + mby ** 2 + mbz ** 2) ** 0.5

                print(f"     Bx={mbx:+9.2f}+-{sbx:5.2f}   "
                      f"By={mby:+9.2f}+-{sby:5.2f}   "
                      f"Bz={mbz:+9.2f}+-{sbz:5.2f} uT")
                print(f"     DB=({dbx:+.1f},{dby:+.1f},{dbz:+.1f})  "
                      f"|B|={bmag:.1f} uT  "
                      f"(tail {nt}/{n})  step {time.time()-t_step:.1f}s")

                # --- force sanity-check ---
                if force is not None:
                    F_mean, F_std, F_n = force.sample_average(FORCE_SAMPLE_S)
                    f_warn = (" [!! NON-ZERO]"
                              if abs(F_mean) > FORCE_NONZERO_WARN_N else "")
                    print(f"     F = {F_mean*1000:+7.2f} +/- {F_std*1000:5.2f} mN  "
                          f"(n={F_n}){f_warn}")
                else:
                    F_mean, F_std, F_n = float("nan"), float("nan"), 0

                f.write(
                    f"{q_actual:.3f},{q_target},{direction},{pos:.3f},{nt},"
                    f"{mbx:.4f},{sbx:.4f},{mby:.4f},{sby:.4f},"
                    f"{mbz:.4f},{sbz:.4f},"
                    f"{dbx:.4f},{dby:.4f},{dbz:.4f},{bmag:.4f},"
                    f"{F_mean:.5f},{F_std:.5f},{F_n}\n"
                )
                f.flush()

                raw_path = session_dir / f"C_q{q_target}_{direction}_raw.csv"
                np.savetxt(
                    raw_path,
                    np.column_stack([bx, by, bz]),
                    delimiter=",",
                    header="Bx_uT,By_uT,Bz_uT",
                    comments="",
                )

                log.write(
                    f"[{i}] {direction} q_tgt={q_target} m10_tgt={m10_target:.3f} "
                    f"m10_pos={pos:.3f} q_act={q_actual:.3f} n={n} "
                    f"Bx={mbx:.2f} By={mby:.2f} Bz={mbz:.2f} "
                    f"F={F_mean:.5f} F_std={F_std:.5f}\n"
                )
                log.flush()

                n_done += 1
                # progress estimate
                elapsed = time.time() - t_session_start
                remaining_pts = n_pts - i
                if n_done > 0:
                    avg_step = elapsed / n_done
                    eta_s = remaining_pts * avg_step
                    print(f"     elapsed {elapsed/60:.1f} min, "
                          f"ETA ~{eta_s/60:.1f} min")

    except KeyboardInterrupt:
        print("\n\n   session aborted by user -- data so far is saved")
        log.write("\nABORTED: KeyboardInterrupt\n")
    except Exception as exc:
        print(f"\n\n   session aborted by error: {exc}")
        log.write(f"\nERROR: {exc}\n")
        raise
    finally:
        log.close()
        mark10.close()
        mlx_ser.close()
        if force is not None:
            force.close()
        print(f"\n=== Stage C done.  Summary: {summary_file} ===")
        plot_summary(summary_file, session_dir / "C_B_vs_q.png")


if __name__ == "__main__":
    main()
