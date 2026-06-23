"""APMD Stage 7.1 -- no-contact motion artifact control.

This control replays the selected same-d active path-pair motion without
letting the stamp head touch the sample. The goal is to test whether Mark-10
motion, wiring, serial timing, or environmental drift alone can create a
return-direct magnetic split comparable to the contact APMD signal.

Default replay path:
    nominal target d = 3.40 mm
    nominal preload d = 3.80 mm
    direct target -> preload -> return target

The script does not search contact. Instead it replays the absolute Mark-10
positions implied by the selected contact experiments using a fixed estimated
contact depth from the no-contact start. The sample/head must be arranged so
the replay motion remains truly no-contact.
"""

from __future__ import annotations

import csv
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import serial

from apmd_session_registry import SessionRecord, register_session
from force_serial import ForceReader, find_force_port
from mark10_control import Mark10, Mark10Error
from mlx_serial import find_mlx_port
from stageI_hold_disp import (
    MlxNoDataError,
    assert_no_contact_live_tare,
    bmag,
    read_force_one,
    read_mlx_one,
    require_mlx_sample,
    soft_reboot_mlx,
)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# ============================================================================
# CONFIG
# ============================================================================

MARK10_PORT = "COM5"
MARK10_BAUD = 9600
MARK10_SPEED_MM_PER_MIN = 200.0
TARGET_POSITION_TOL_MM = 0.020

MLX_PORT = None
MLX_BAUD = 115200
MLX_STARTUP_WAIT_S = 2.0
MLX_SOFT_REBOOT_ON_OPEN = False

N_TRIALS = 3
TARGET_D_MM = 3.40
PRELOAD_D_MM = 3.80
REPLAY_CONTACT_DEPTH_MM = 1.62

TARGET_RECORD_S = 45.0
PRELOAD_RECORD_S = 30.0
PRE_RECORD_SETTLE_S = 5.0
SUMMARY_WINDOW_S = 10.0
ROW_PRINT_EVERY_S = 5.0
INTER_STATE_SETTLE_S = 3.0
INTER_TRIAL_REST_S = 120.0

LIVE_TARE_S = 2.0
TARE_PRE_SETTLE_S = 3.0
NO_CONTACT_FORCE_ABORT_N = 0.100

ARTIFACT_GATE_UT = 10.0
B0_DRIFT_GATE_UT = 10.0

SAMPLE_ID = ""
MAGNET_ID = ""
HEAD_ID = "stamp_head_v1"
FORCE_CALIBRATION_ID = "force_calibration_20260602_190856"
DISPLACEMENT_ZERO_ID = "stageD_session_20260602_201421"

HERE = Path(__file__).parent
OUTPUT_ROOT = HERE / "decouple_data"
FORMAL_DESIGN_PATH = HERE / "APMD_FORMAL_EXPERIMENT_DESIGN.md"

PROTOCOL_TITLE = "APMD -- no-contact motion artifact control"
STAGE_LABEL = "no_contact_motion_artifact"
SUMMARY_FILENAME = "no_contact_motion_artifact_pair_summary.csv"
B0_SUMMARY_FILENAME = "no_contact_motion_artifact_B0_summary.csv"
STATE_FILE_PREFIX = "no_contact_motion_artifact"
FIGURE_FILENAME = "no_contact_motion_artifact.png"
FORMAL_EXPERIMENT_KEY = "7.1"


@dataclass(frozen=True)
class MotionState:
    state_label: str
    path_mode: str
    phase: str
    nominal_d_mm: float
    preload_d_mm: float
    record_s: float
    mark10_pos_mm: float


def metadata_fieldnames() -> list[str]:
    return [
        "sample_id",
        "magnet_id",
        "head_id",
        "force_calibration_id",
        "displacement_zero_id",
    ]


def metadata_values() -> dict[str, str]:
    return {
        "sample_id": SAMPLE_ID,
        "magnet_id": MAGNET_ID,
        "head_id": HEAD_ID,
        "force_calibration_id": FORCE_CALIBRATION_ID,
        "displacement_zero_id": DISPLACEMENT_ZERO_ID,
    }


def vector_norm3(x: float, y: float, z: float) -> float:
    return (x * x + y * y + z * z) ** 0.5


def median_or_nan(values):
    clean = [v for v in values if v == v]
    return statistics.median(clean) if clean else float("nan")


def target_label(d_mm: float) -> str:
    return f"{int(round(d_mm * 100)):03d}"


def build_motion_sequence(
    *,
    target_d_mm: float = TARGET_D_MM,
    preload_d_mm: float = PRELOAD_D_MM,
    replay_contact_depth_mm: float = REPLAY_CONTACT_DEPTH_MM,
) -> list[MotionState]:
    """Return replay states as positions relative to the current no-contact start."""
    direct_pos = -(replay_contact_depth_mm + target_d_mm)
    preload_pos = -(replay_contact_depth_mm + preload_d_mm)
    return [
        MotionState(
            state_label="direct_target",
            path_mode="direct_loading",
            phase="no_contact_replay",
            nominal_d_mm=target_d_mm,
            preload_d_mm=preload_d_mm,
            record_s=TARGET_RECORD_S,
            mark10_pos_mm=direct_pos,
        ),
        MotionState(
            state_label="preload_deep",
            path_mode="preload_loading",
            phase="no_contact_replay",
            nominal_d_mm=preload_d_mm,
            preload_d_mm=preload_d_mm,
            record_s=PRELOAD_RECORD_S,
            mark10_pos_mm=preload_pos,
        ),
        MotionState(
            state_label="return_target",
            path_mode="return_unloading",
            phase="no_contact_replay",
            nominal_d_mm=target_d_mm,
            preload_d_mm=preload_d_mm,
            record_s=TARGET_RECORD_S,
            mark10_pos_mm=direct_pos,
        ),
    ]


def summarize_samples(samples: list[dict], window_s: float = SUMMARY_WINDOW_S) -> dict:
    if not samples:
        nan = float("nan")
        return {
            "n": 0,
            "F_N": nan,
            "Bmag_uT": nan,
            "Bx_uT": nan,
            "By_uT": nan,
            "Bz_uT": nan,
            "mark10_pos_mm": nan,
            "motion_depth_from_start_mm": nan,
        }
    t_max = max(s["t_rel_s"] for s in samples)
    tail = [s for s in samples if s["t_rel_s"] >= t_max - window_s]
    if not tail:
        tail = samples
    return {
        "n": len(tail),
        "F_N": median_or_nan([s["F_N"] for s in tail]),
        "Bmag_uT": median_or_nan([s["Bmag_uT"] for s in tail]),
        "Bx_uT": median_or_nan([s["Bx_uT"] for s in tail]),
        "By_uT": median_or_nan([s["By_uT"] for s in tail]),
        "Bz_uT": median_or_nan([s["Bz_uT"] for s in tail]),
        "mark10_pos_mm": median_or_nan([s["mark10_pos_mm"] for s in tail]),
        "motion_depth_from_start_mm": median_or_nan(
            [s["motion_depth_from_start_mm"] for s in tail]
        ),
    }


def artifact_diagnostics(direct: dict, returned: dict, gate_uT: float = ARTIFACT_GATE_UT) -> dict:
    dBx = returned["Bx_uT"] - direct["Bx_uT"]
    dBy = returned["By_uT"] - direct["By_uT"]
    dBz = returned["Bz_uT"] - direct["Bz_uT"]
    dBmag = returned["Bmag_uT"] - direct["Bmag_uT"]
    dBvec = vector_norm3(dBx, dBy, dBz)
    artifact_ok = dBvec <= gate_uT
    return {
        "delta_Bmag_uT": dBmag,
        "delta_Bx_uT": dBx,
        "delta_By_uT": dBy,
        "delta_Bz_uT": dBz,
        "delta_Bvec_uT": dBvec,
        "artifact_ok": artifact_ok,
        "verdict": "low_motion_artifact" if artifact_ok else "motion_artifact_detected",
    }


def capture_b0(mlx_ser, context: str, log=None) -> tuple[tuple[float, float, float], int]:
    (bx, by, bz), _, n = require_mlx_sample(mlx_ser, 1.5, context, log=log)
    return (bx, by, bz), n


def b0_drift_diagnostics(b0_start: tuple[float, float, float],
                         b0_end: tuple[float, float, float]) -> dict:
    dBx = b0_end[0] - b0_start[0]
    dBy = b0_end[1] - b0_start[1]
    dBz = b0_end[2] - b0_start[2]
    dBvec = vector_norm3(dBx, dBy, dBz)
    return {
        "delta_Bx_uT": dBx,
        "delta_By_uT": dBy,
        "delta_Bz_uT": dBz,
        "delta_Bvec_uT": dBvec,
        "drift_ok": dBvec <= B0_DRIFT_GATE_UT,
    }


def record_no_contact_state(
    *,
    mark10,
    force,
    mlx_ser,
    B0,
    session_id: str,
    trial: int,
    pair_id: int,
    state: MotionState,
    trial_start_pos: float,
    csv_writer,
    log,
) -> dict:
    target_pos = trial_start_pos + state.mark10_pos_mm
    print(
        f"\n  {state.state_label}: replay nominal d={state.nominal_d_mm:.3f} mm "
        f"pos={target_pos:+.3f} mm, record {state.record_s:.0f} s"
    )
    actual_pos = mark10.move_to(target_pos, tolerance_mm=TARGET_POSITION_TOL_MM)
    motion_depth = trial_start_pos - actual_pos

    time.sleep(PRE_RECORD_SETTLE_S)
    force.ser.reset_input_buffer()
    mlx_ser.reset_input_buffer()

    log.write(
        f"[trial {trial} {state.state_label}] start "
        f"nominal_d={state.nominal_d_mm:.4f} pos={actual_pos:.4f} "
        f"motion_depth={motion_depth:.4f}\n"
    )
    log.flush()

    t0 = time.perf_counter()
    next_print = 0.0
    samples = []
    while True:
        t_rel = time.perf_counter() - t0
        if t_rel >= state.record_s:
            break

        F_N = read_force_one(force, timeout_s=1.0)
        B = read_mlx_one(mlx_ser, timeout_s=1.0)
        if F_N is None or B is None:
            continue
        if abs(F_N) > NO_CONTACT_FORCE_ABORT_N:
            raise RuntimeError(
                f"No-contact control detected contact load: F={F_N:+.3f} N "
                f"> {NO_CONTACT_FORCE_ABORT_N:.3f} N. Stop and restore no-contact geometry."
            )

        bx, by, bz = B
        Bm = bmag(bx, by, bz)
        dbx, dby, dbz = bx - B0[0], by - B0[1], bz - B0[2]
        row = {
            "time_s": f"{time.time():.6f}",
            "session_id": session_id,
            "trial": trial,
            "repeat_id": trial,
            "pair_id": pair_id,
            "stage": STAGE_LABEL,
            "state_label": state.state_label,
            "phase": state.phase,
            "control_mode": "no_contact_motion_replay",
            "path_mode": state.path_mode,
            "target_label": target_label(TARGET_D_MM),
            "nominal_d_mm": f"{state.nominal_d_mm:.4f}",
            "nominal_preload_d_mm": f"{state.preload_d_mm:.4f}",
            "motion_depth_from_start_mm": f"{motion_depth:.4f}",
            "mark10_pos_mm": f"{actual_pos:.4f}",
            "t_rel_s": f"{t_rel:.4f}",
            "F_N": f"{F_N:.6f}",
            "mean_Bx_uT": f"{bx:.4f}",
            "mean_By_uT": f"{by:.4f}",
            "mean_Bz_uT": f"{bz:.4f}",
            "delta_Bx_uT": f"{dbx:.4f}",
            "delta_By_uT": f"{dby:.4f}",
            "delta_Bz_uT": f"{dbz:.4f}",
            "Bmag_uT": f"{Bm:.4f}",
            **metadata_values(),
            "note": "no_contact",
        }
        csv_writer.writerow(row)
        samples.append({
            "t_rel_s": t_rel,
            "F_N": F_N,
            "Bx_uT": bx,
            "By_uT": by,
            "Bz_uT": bz,
            "Bmag_uT": Bm,
            "mark10_pos_mm": actual_pos,
            "motion_depth_from_start_mm": motion_depth,
        })

        if t_rel >= next_print:
            print(
                f"      t={t_rel:5.1f} s  F={F_N*1000:+7.1f} mN  "
                f"|B|={Bm:8.1f} uT"
            )
            next_print += ROW_PRINT_EVERY_S

    summary = summarize_samples(samples)
    print(
        f"    summary(last {SUMMARY_WINDOW_S:.0f}s): "
        f"F={summary['F_N']*1000:+.1f} mN, "
        f"|B|={summary['Bmag_uT']:.1f} uT, n={summary['n']}"
    )
    log.write(
        f"[trial {trial} {state.state_label}] summary "
        f"n={summary['n']} F={summary['F_N']:.6f} "
        f"Bmag={summary['Bmag_uT']:.4f}\n"
    )
    log.flush()
    return summary


def write_trial_summary(writer, session_id: str, trial: int, direct: dict,
                        returned: dict, diag: dict):
    writer.writerow({
        "session_id": session_id,
        **metadata_values(),
        "trial": trial,
        "pair_id": 1,
        "target_label": target_label(TARGET_D_MM),
        "nominal_d_target_mm": f"{TARGET_D_MM:.4f}",
        "nominal_d_preload_mm": f"{PRELOAD_D_MM:.4f}",
        "direct_motion_depth_mm": f"{direct['motion_depth_from_start_mm']:.4f}",
        "return_motion_depth_mm": f"{returned['motion_depth_from_start_mm']:.4f}",
        "F_direct_N": f"{direct['F_N']:.6f}",
        "F_return_N": f"{returned['F_N']:.6f}",
        "Bmag_direct_uT": f"{direct['Bmag_uT']:.4f}",
        "Bmag_return_uT": f"{returned['Bmag_uT']:.4f}",
        "delta_Bmag_uT": f"{diag['delta_Bmag_uT']:+.4f}",
        "delta_Bx_uT": f"{diag['delta_Bx_uT']:+.4f}",
        "delta_By_uT": f"{diag['delta_By_uT']:+.4f}",
        "delta_Bz_uT": f"{diag['delta_Bz_uT']:+.4f}",
        "delta_Bvec_uT": f"{diag['delta_Bvec_uT']:.4f}",
        "artifact_gate_uT": f"{ARTIFACT_GATE_UT:.1f}",
        "artifact_ok": int(diag["artifact_ok"]),
        "verdict": diag["verdict"],
    })


def plot_summary(summary_path: Path, b0_path: Path, png_path: Path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not available, skipping plot")
        return

    rows = list(csv.DictReader(summary_path.open(encoding="utf-8")))
    if not rows:
        return

    trials = [int(r["trial"]) for r in rows]
    dBvec = [float(r["delta_Bvec_uT"]) for r in rows]
    dBy = [float(r["delta_By_uT"]) for r in rows]
    dBz = [float(r["delta_Bz_uT"]) for r in rows]
    dBx = [float(r["delta_Bx_uT"]) for r in rows]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    ax = axes[0]
    ax.bar(trials, dBvec, color="#222222", width=0.55)
    ax.axhline(ARTIFACT_GATE_UT, color="#b83b3b", linestyle="--", linewidth=1.2,
               label=f"{ARTIFACT_GATE_UT:.0f} uT gate")
    ax.set_xlabel("trial")
    ax.set_ylabel("return - direct ΔBvec (uT)")
    ax.set_title("No-contact motion artifact")
    ax.set_xticks(trials)
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)

    ax = axes[1]
    x = range(len(trials))
    width = 0.24
    ax.bar([i - width for i in x], dBx, width=width, color="#222222", label="dBx")
    ax.bar(x, dBy, width=width, color="#c23b3b", label="dBy")
    ax.bar([i + width for i in x], dBz, width=width, color="#1f77b4", label="dBz")
    ax.axhline(0, color="#888888", linewidth=1.0)
    ax.set_xticks(list(x))
    ax.set_xticklabels([str(t) for t in trials])
    ax.set_xlabel("trial")
    ax.set_ylabel("return - direct component (uT)")
    ax.set_title("Component-level artifact check")
    ax.legend(frameon=False, ncols=3)
    ax.grid(axis="y", alpha=0.25)

    if b0_path.exists():
        b0_rows = list(csv.DictReader(b0_path.open(encoding="utf-8")))
        if b0_rows:
            drift = float(b0_rows[0]["delta_Bvec_uT"])
            fig.suptitle(f"B0 drift = {drift:.1f} uT", y=1.02, fontsize=11)

    fig.tight_layout()
    fig.savefig(png_path, dpi=200)
    print(f"  plot -> {png_path}")


def fail_before_trial(session_id: str, log_path: Path, ts: str, note) -> None:
    text = str(note)
    print(f"\n{text}")
    log_path.write_text(
        f"# APMD no-contact motion artifact failed before acquisition {ts}\n"
        f"# status=failed_preflight\n# note={text}\n",
        encoding="utf-8",
    )
    raise SystemExit(1)


def main() -> None:
    OUTPUT_ROOT.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"session_{ts}"
    session_dir = OUTPUT_ROOT / session_id
    session_dir.mkdir(parents=True, exist_ok=False)
    log_path = session_dir / "run_log.txt"
    summary_path = session_dir / SUMMARY_FILENAME
    b0_path = session_dir / B0_SUMMARY_FILENAME
    png_path = session_dir / FIGURE_FILENAME

    sequence = build_motion_sequence()
    est_total_s = N_TRIALS * (
        sum(s.record_s for s in sequence)
        + len(sequence) * (PRE_RECORD_SETTLE_S + INTER_STATE_SETTLE_S)
        + INTER_TRIAL_REST_S
    )

    print("\n" + "=" * 64)
    print(f"  {PROTOCOL_TITLE}")
    print("=" * 64)
    print(f"  session        : {session_id}")
    print(f"  trials         : {N_TRIALS}")
    print(f"  replay path    : d={TARGET_D_MM:.2f} -> {PRELOAD_D_MM:.2f} -> {TARGET_D_MM:.2f} mm")
    print(f"  replay positions from start: {[f'{s.mark10_pos_mm:+.3f}' for s in sequence]} mm")
    print(f"  no-contact gate: ΔBvec <= {ARTIFACT_GATE_UT:.1f} uT")
    print(f"  est total      : ~{est_total_s / 60:.1f} min")

    print("\nPre-flight:")
    print("  [ ] This is a NO-CONTACT artifact control, not a contact experiment")
    print("  [ ] Mark-10 start position about 6 mm above lower limit")
    print("  [ ] Stamp head will replay the selected path but must NOT touch sample")
    print("  [ ] Sample/magnet/MLX geometry kept as close as possible to formal APMD setup")
    print("  [ ] EasyMESUR Home -> PC Control ACTIVE")
    print("  [ ] Arduino IDE Serial Monitor on UNO CLOSED")
    print("  [ ] QT Py / MLX running circuitpython/code.py")
    print("  [ ] Observe first replay move and abort if any contact is visible")
    print()
    try:
        input("Press Enter to start (Ctrl+C aborts) ... ")
    except KeyboardInterrupt:
        return

    print("\nOpening MLX90393 first ...")
    try:
        mlx_port = MLX_PORT or find_mlx_port()
        mlx_ser = serial.Serial(mlx_port, MLX_BAUD, timeout=0.5)
        if MLX_SOFT_REBOOT_ON_OPEN:
            print("  soft-rebooting QT Py stream ...")
            soft_reboot_mlx(mlx_ser)
        time.sleep(MLX_STARTUP_WAIT_S)
        _, _, n_warmup = require_mlx_sample(
            mlx_ser, 1.0, "MLX warmup before no-contact artifact control")
        print(f"  MLX90393 stream on {mlx_port}  (warmup n={n_warmup})")
    except Exception as exc:
        fail_before_trial(session_id, log_path, ts, exc)

    print("\nOpening Mark-10 ...")
    try:
        mark10 = Mark10(MARK10_PORT, MARK10_BAUD,
                        speed_mm_per_min=MARK10_SPEED_MM_PER_MIN)
    except Mark10Error as exc:
        mlx_ser.close()
        fail_before_trial(session_id, log_path, ts, exc)
    print("  Mark-10 ready")

    print("Opening UNO_force ...")
    try:
        force = ForceReader(find_force_port())
        force.live_tare(duration_s=LIVE_TARE_S, pre_settle_s=TARE_PRE_SETTLE_S)
        assert_no_contact_live_tare(force, "APMD no-contact artifact pre-flight")
    except Exception as exc:
        mlx_ser.close()
        mark10.close()
        fail_before_trial(session_id, log_path, ts, exc)

    log = log_path.open("w", encoding="utf-8")
    log.write(f"# APMD no-contact motion artifact control {ts}\n")
    log.write(
        f"# target_d={TARGET_D_MM:.4f}, preload_d={PRELOAD_D_MM:.4f}, "
        f"replay_contact_depth={REPLAY_CONTACT_DEPTH_MM:.4f}\n"
    )
    log.write(f"# replay_relative_positions={[s.mark10_pos_mm for s in sequence]}\n")
    log.write(f"# live_tare_N={force.live_tare_N:.5f}\n")
    log.flush()

    print("Capturing B0_start ...")
    try:
        B0_start, n_b0_start = capture_b0(mlx_ser, "B0_start capture", log=log)
    except MlxNoDataError as exc:
        mlx_ser.close()
        force.close()
        mark10.close()
        fail_before_trial(session_id, log_path, ts, exc)
    print(
        f"  B0_start = ({B0_start[0]:+.2f}, {B0_start[1]:+.2f}, "
        f"{B0_start[2]:+.2f}) uT (n={n_b0_start})"
    )
    log.write(f"# B0_start={B0_start}\n")
    log.flush()

    trial_start_pos = mark10.position_stable()
    print(f"  trial_start_pos = {trial_start_pos:+.3f} mm")
    log.write(f"# trial_start_pos={trial_start_pos:.4f}\n")
    log.flush()

    raw_fields = [
        "time_s", "session_id", "trial", "repeat_id", "pair_id", "stage",
        "state_label", "phase", "control_mode", "path_mode", "target_label",
        "nominal_d_mm", "nominal_preload_d_mm", "motion_depth_from_start_mm",
        "mark10_pos_mm", "t_rel_s", "F_N",
        "mean_Bx_uT", "mean_By_uT", "mean_Bz_uT",
        "delta_Bx_uT", "delta_By_uT", "delta_Bz_uT", "Bmag_uT",
        *metadata_fieldnames(), "note",
    ]
    summary_fields = [
        "session_id", *metadata_fieldnames(), "trial", "pair_id",
        "target_label", "nominal_d_target_mm", "nominal_d_preload_mm",
        "direct_motion_depth_mm", "return_motion_depth_mm",
        "F_direct_N", "F_return_N",
        "Bmag_direct_uT", "Bmag_return_uT", "delta_Bmag_uT",
        "delta_Bx_uT", "delta_By_uT", "delta_Bz_uT", "delta_Bvec_uT",
        "artifact_gate_uT", "artifact_ok", "verdict",
    ]

    artifact_ok_count = 0
    summary_file = summary_path.open("w", newline="", encoding="utf-8")
    summary_writer = csv.DictWriter(summary_file, fieldnames=summary_fields)
    summary_writer.writeheader()

    try:
        for trial in range(1, N_TRIALS + 1):
            print("\n" + "=" * 64)
            print(f"  TRIAL {trial}/{N_TRIALS}")
            print("=" * 64)
            csv_path = session_dir / f"{STATE_FILE_PREFIX}_{target_label(TARGET_D_MM)}_rep{trial}.csv"
            state_summaries = {}
            with csv_path.open("w", newline="", encoding="utf-8") as raw_file:
                writer = csv.DictWriter(raw_file, fieldnames=raw_fields)
                writer.writeheader()
                for state in sequence:
                    state_summaries[state.state_label] = record_no_contact_state(
                        mark10=mark10,
                        force=force,
                        mlx_ser=mlx_ser,
                        B0=B0_start,
                        session_id=session_id,
                        trial=trial,
                        pair_id=1,
                        state=state,
                        trial_start_pos=trial_start_pos,
                        csv_writer=writer,
                        log=log,
                    )
                    time.sleep(INTER_STATE_SETTLE_S)

            diag = artifact_diagnostics(
                state_summaries["direct_target"],
                state_summaries["return_target"],
            )
            write_trial_summary(
                summary_writer,
                session_id,
                trial,
                state_summaries["direct_target"],
                state_summaries["return_target"],
                diag,
            )
            summary_file.flush()
            artifact_ok_count += int(diag["artifact_ok"])
            print(
                "\n    no-contact diagnostic: "
                f"ΔBvec={diag['delta_Bvec_uT']:.2f} uT, "
                f"verdict={diag['verdict']}"
            )
            log.write(
                f"[trial {trial}] no-contact diagnostic "
                f"dBvec={diag['delta_Bvec_uT']:.4f} "
                f"verdict={diag['verdict']}\n"
            )
            log.flush()

            print(f"\n  PHASE R: retracting to start ({trial_start_pos:+.3f} mm)")
            try:
                back_pos = mark10.move_to(trial_start_pos)
                print(f"    back at {back_pos:+.3f} mm")
            except Mark10Error as exc:
                print(f"  ! retract error: {exc}")

            if trial < N_TRIALS:
                print(f"\n  resting {INTER_TRIAL_REST_S:.0f} s ...")
                time.sleep(INTER_TRIAL_REST_S)

        print("\nCapturing B0_end ...")
        B0_end, n_b0_end = capture_b0(mlx_ser, "B0_end capture", log=log)
        b0_diag = b0_drift_diagnostics(B0_start, B0_end)
        with b0_path.open("w", newline="", encoding="utf-8") as b0_file:
            writer = csv.DictWriter(
                b0_file,
                fieldnames=[
                    "session_id", "B0_start_Bx_uT", "B0_start_By_uT", "B0_start_Bz_uT",
                    "B0_end_Bx_uT", "B0_end_By_uT", "B0_end_Bz_uT",
                    "n_b0_start", "n_b0_end", "delta_Bx_uT", "delta_By_uT",
                    "delta_Bz_uT", "delta_Bvec_uT", "drift_gate_uT", "drift_ok",
                ],
            )
            writer.writeheader()
            writer.writerow({
                "session_id": session_id,
                "B0_start_Bx_uT": f"{B0_start[0]:.4f}",
                "B0_start_By_uT": f"{B0_start[1]:.4f}",
                "B0_start_Bz_uT": f"{B0_start[2]:.4f}",
                "B0_end_Bx_uT": f"{B0_end[0]:.4f}",
                "B0_end_By_uT": f"{B0_end[1]:.4f}",
                "B0_end_Bz_uT": f"{B0_end[2]:.4f}",
                "n_b0_start": n_b0_start,
                "n_b0_end": n_b0_end,
                "delta_Bx_uT": f"{b0_diag['delta_Bx_uT']:+.4f}",
                "delta_By_uT": f"{b0_diag['delta_By_uT']:+.4f}",
                "delta_Bz_uT": f"{b0_diag['delta_Bz_uT']:+.4f}",
                "delta_Bvec_uT": f"{b0_diag['delta_Bvec_uT']:.4f}",
                "drift_gate_uT": f"{B0_DRIFT_GATE_UT:.1f}",
                "drift_ok": int(b0_diag["drift_ok"]),
            })
        print(
            f"  B0_end = ({B0_end[0]:+.2f}, {B0_end[1]:+.2f}, "
            f"{B0_end[2]:+.2f}) uT (n={n_b0_end})"
        )
        print(
            f"  B0 drift ΔBvec={b0_diag['delta_Bvec_uT']:.2f} uT, "
            f"drift_ok={b0_diag['drift_ok']}"
        )
        log.write(
            f"# B0_end={B0_end}\n"
            f"# B0_drift_dBvec={b0_diag['delta_Bvec_uT']:.4f} "
            f"drift_ok={b0_diag['drift_ok']}\n"
        )
        log.flush()

        plot_summary(summary_path, b0_path, png_path)

        run_ok = artifact_ok_count == N_TRIALS and b0_diag["drift_ok"]
        if run_ok:
            changed = register_session(
                FORMAL_DESIGN_PATH,
                FORMAL_EXPERIMENT_KEY,
                SessionRecord(
                    session_id=session_id,
                    status="formal",
                    summary_filename=SUMMARY_FILENAME,
                    figure_filename=FIGURE_FILENAME,
                    note=(
                        f"no-contact replay passed {artifact_ok_count}/{N_TRIALS}; "
                        f"B0 drift {b0_diag['delta_Bvec_uT']:.1f} uT"
                    ),
                ),
            )
            print(
                f"  formal registry {'updated' if changed else 'already contained this session'}"
            )
        else:
            print(
                "  formal registry skipped: no-contact artifact or B0 drift gate failed"
            )

    except KeyboardInterrupt:
        print("\n\nUser abort. Will retract.")
        try:
            mark10.move_to(trial_start_pos)
        except Exception:
            pass
    finally:
        summary_file.close()
        log.close()
        try:
            force.close()
        except Exception:
            pass
        try:
            mark10.close()
        except Exception:
            pass
        try:
            mlx_ser.close()
        except Exception:
            pass

    print("\n=== APMD no-contact motion artifact control done. Files in:", session_dir)
    for path in sorted(session_dir.glob("no_contact_motion_artifact*")):
        print(" ", path.name)
    print("\nNext: inspect no_contact_motion_artifact_pair_summary.csv")


if __name__ == "__main__":
    main()
