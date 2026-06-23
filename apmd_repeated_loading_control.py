"""APMD Experiment 7.2: repeated-loading branch control.

This control repeats the same loading-to-target branch without a deeper preload:

    contact search
    load to selected target d
    record target state
    retract to no-contact start
    rest

If repeated loading alone produces only a small cycle-to-cycle magnetic change,
then the large same-d active-path signal is not explained by ordinary repeated
loading or setup cycling. It supports the conclusion that the deeper-preload
path is the necessary active excitation.
"""

from __future__ import annotations

import csv
import math
import sys
import time
from dataclasses import dataclass
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import apmd_same_d_different_f_path_pair as base
from apmd_session_registry import SessionRecord, register_session


TARGET_D_MM = 3.40
CYCLES = 5
TARGET_RECORD_S = 45.0
SUMMARY_WINDOW_S = 10.0
INTER_CYCLE_REST_S = 120.0
CONTROL_B_GATE_UT = 50.0

SUMMARY_FILENAME = "repeated_loading_control_summary.csv"
STATE_FILE_PREFIX = "repeated_loading_control"
FIGURE_FILENAME = "repeated_loading_control.png"
CSV_PRINT_GLOB = f"{STATE_FILE_PREFIX}*.csv"
FORMAL_EXPERIMENT_KEY = "7.2"

COLOR_BLACK = "#222222"
COLOR_RED = "#c43d3d"
COLOR_BLUE = "#1f77b4"
COLOR_GRAY = "#7a7a7a"


@dataclass(frozen=True)
class LoadingCycle:
    cycle: int
    state_label: str
    path_mode: str
    target_d_mm: float
    preload_d_mm: float
    record_s: float


def configure_base_protocol() -> None:
    base.PROTOCOL_TITLE = "APMD Experiment 7.2 -- repeated-loading branch control"
    base.PROTOCOL_SHORT_NAME = "APMD repeated-loading control 7.2"
    base.STAGE_LABEL = "repeated_loading_control"
    base.LOG_HEADER = "APMD repeated-loading branch control session"

    base.N_TRIALS = CYCLES
    base.D_TARGETS_MM = [TARGET_D_MM]
    base.D_PRELOAD_BY_TARGET_MM = {TARGET_D_MM: TARGET_D_MM}
    base.D_PRELOAD_MM = TARGET_D_MM

    base.TARGET_RECORD_S = TARGET_RECORD_S
    base.PRELOAD_RECORD_S = 0.0
    base.SUMMARY_WINDOW_S = SUMMARY_WINDOW_S
    base.INTER_TRIAL_REST_S = INTER_CYCLE_REST_S
    base.F_HARD_LIMIT_N = None

    base.SUMMARY_FILENAME = SUMMARY_FILENAME
    base.STATE_FILE_PREFIX = STATE_FILE_PREFIX
    base.CSV_PRINT_GLOB = CSV_PRINT_GLOB
    base.FIGURE_FILENAME = FIGURE_FILENAME
    base.PREFLIGHT_FIRST_LINE = (
        "Experiment 7.2: repeated loading to target d, no deeper preload"
    )
    base.NEXT_MESSAGE = "Next: run Stage 7.3 cross-day repeatability if needed."
    base.FORMAL_EXPERIMENT_KEY = FORMAL_EXPERIMENT_KEY


def build_cycle_plan(
    *, target_d_mm: float = TARGET_D_MM, cycles: int = CYCLES
) -> list[LoadingCycle]:
    return [
        LoadingCycle(
            cycle=i,
            state_label="loading_target",
            path_mode="repeat_loading",
            target_d_mm=float(target_d_mm),
            preload_d_mm=float(target_d_mm),
            record_s=TARGET_RECORD_S,
        )
        for i in range(1, cycles + 1)
    ]


def fixed_contact_target_positions(
    *, contact_pos_mm: float, cycles: list[LoadingCycle]
) -> list[float]:
    """Absolute Mark-10 targets when all cycles share one contact reference."""
    return [float(contact_pos_mm) - cycle.target_d_mm for cycle in cycles]


def cycle_to_reference_diagnostics(
    reference: dict,
    current: dict,
    *,
    gate_uT: float = CONTROL_B_GATE_UT,
) -> dict:
    dF = current["F_N"] - reference["F_N"]
    dd = current["d_mm"] - reference["d_mm"]
    dBmag = current["Bmag_uT"] - reference["Bmag_uT"]
    dBx = current["delta_Bx_uT"] - reference["delta_Bx_uT"]
    dBy = current["delta_By_uT"] - reference["delta_By_uT"]
    dBz = current["delta_Bz_uT"] - reference["delta_Bz_uT"]
    dBvec = base.vector_norm3(dBx, dBy, dBz)
    control_ok = dBvec <= gate_uT + 1e-9
    return {
        "delta_F_vs_cycle1_N": dF,
        "delta_d_vs_cycle1_mm": dd,
        "delta_Bmag_vs_cycle1_uT": dBmag,
        "delta_Bx_vs_cycle1_uT": dBx,
        "delta_By_vs_cycle1_uT": dBy,
        "delta_Bz_vs_cycle1_uT": dBz,
        "delta_Bvec_uT": dBvec,
        "control_ok": control_ok,
        "verdict": (
            "repeat_loading_low_memory"
            if control_ok
            else "repeat_loading_memory_detected"
        ),
    }


def registry_status_for_control(
    *,
    acquired_cycles: int,
    expected_cycles: int,
    max_delta_Bvec_uT: float,
    gate_uT: float = CONTROL_B_GATE_UT,
) -> tuple[str, str]:
    if acquired_cycles != expected_cycles:
        return (
            "",
            (
                f"not registered: {acquired_cycles}/{expected_cycles} "
                "loading cycles acquired"
            ),
        )
    if max_delta_Bvec_uT <= gate_uT + 1e-9:
        return (
            "formal",
            (
                f"repeated-loading control passed {acquired_cycles}/{expected_cycles}; "
                f"max cycle-to-cycle ΔBvec {max_delta_Bvec_uT:.1f} uT"
            ),
        )
    return (
        "",
        (
            f"not registered: repeated loading exceeded control gate "
            f"({max_delta_Bvec_uT:.1f} uT > {gate_uT:.1f} uT)"
        ),
    )


def summary_fieldnames() -> list[str]:
    return [
        "session_id",
        *base.metadata_fieldnames(),
        "cycle",
        "target_label",
        "target_d_mm",
        "d_mm",
        "F_N",
        "Bmag_uT",
        "delta_Bx_uT",
        "delta_By_uT",
        "delta_Bz_uT",
        "n_tail",
        "reference_cycle",
        "delta_F_vs_cycle1_N",
        "delta_d_vs_cycle1_mm",
        "delta_Bmag_vs_cycle1_uT",
        "delta_Bx_vs_cycle1_uT",
        "delta_By_vs_cycle1_uT",
        "delta_Bz_vs_cycle1_uT",
        "delta_Bvec_uT",
        "control_gate_uT",
        "control_ok",
        "verdict",
    ]


def raw_fieldnames() -> list[str]:
    return [
        "time_s",
        "session_id",
        "trial",
        "repeat_id",
        "pair_id",
        "stage",
        "state_label",
        "phase",
        "control_mode",
        "path_mode",
        "target_label",
        "d_target_mm",
        "d_preload_mm",
        "d_actual_mm",
        "d_mm",
        "q_mm",
        "d_error_mm",
        "mark10_pos_mm",
        "t_rel_s",
        "F_N",
        "mean_Bx_uT",
        "mean_By_uT",
        "mean_Bz_uT",
        "delta_Bx_uT",
        "delta_By_uT",
        "delta_Bz_uT",
        "Bmag_uT",
        *base.metadata_fieldnames(),
        "note",
    ]


def write_cycle_summary(writer, session_id: str, cycle: LoadingCycle,
                        summary: dict, diag: dict) -> None:
    writer.writerow(
        {
            "session_id": session_id,
            **base.metadata_values(),
            "cycle": cycle.cycle,
            "target_label": base.target_label(cycle.target_d_mm),
            "target_d_mm": f"{cycle.target_d_mm:.4f}",
            "d_mm": f"{summary['d_mm']:.4f}",
            "F_N": f"{summary['F_N']:.6f}",
            "Bmag_uT": f"{summary['Bmag_uT']:.4f}",
            "delta_Bx_uT": f"{summary['delta_Bx_uT']:.4f}",
            "delta_By_uT": f"{summary['delta_By_uT']:.4f}",
            "delta_Bz_uT": f"{summary['delta_Bz_uT']:.4f}",
            "n_tail": summary["n"],
            "reference_cycle": 1,
            "delta_F_vs_cycle1_N": f"{diag['delta_F_vs_cycle1_N']:+.6f}",
            "delta_d_vs_cycle1_mm": f"{diag['delta_d_vs_cycle1_mm']:+.4f}",
            "delta_Bmag_vs_cycle1_uT": f"{diag['delta_Bmag_vs_cycle1_uT']:+.4f}",
            "delta_Bx_vs_cycle1_uT": f"{diag['delta_Bx_vs_cycle1_uT']:+.4f}",
            "delta_By_vs_cycle1_uT": f"{diag['delta_By_vs_cycle1_uT']:+.4f}",
            "delta_Bz_vs_cycle1_uT": f"{diag['delta_Bz_vs_cycle1_uT']:+.4f}",
            "delta_Bvec_uT": f"{diag['delta_Bvec_uT']:.4f}",
            "control_gate_uT": f"{CONTROL_B_GATE_UT:.1f}",
            "control_ok": int(diag["control_ok"]),
            "verdict": diag["verdict"],
        }
    )


def plot_control_summary(rows: list[dict], png_path) -> None:
    if not rows:
        return
    cycles = [int(r["cycle"]) for r in rows]
    forces = [float(r["F_N"]) for r in rows]
    dBvec = [float(r["delta_Bvec_uT"]) for r in rows]
    dBx = [float(r["delta_Bx_vs_cycle1_uT"]) for r in rows]
    dBy = [float(r["delta_By_vs_cycle1_uT"]) for r in rows]
    dBz = [float(r["delta_Bz_vs_cycle1_uT"]) for r in rows]

    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.8), dpi=220)
    fig.suptitle(
        "Experiment 7.2: repeated loading control without deeper preload",
        fontsize=13,
        fontweight="bold",
        x=0.02,
        ha="left",
    )

    ax = axes[0]
    ax.plot(cycles, forces, color=COLOR_BLACK, marker="o", lw=1.4)
    ax.set_title("Target-state force repeatability", fontsize=10)
    ax.set_xlabel("loading cycle")
    ax.set_ylabel("F at target d (N)")
    ax.grid(True, axis="y", color="#e7e7e7", lw=0.8)

    ax = axes[1]
    ax.bar(cycles, dBvec, color=COLOR_BLACK, width=0.58)
    ax.axhline(CONTROL_B_GATE_UT, color=COLOR_RED, ls="--", lw=1.2)
    ax.text(
        cycles[-1] + 0.05,
        CONTROL_B_GATE_UT,
        f"{CONTROL_B_GATE_UT:.0f} uT gate",
        color=COLOR_RED,
        va="bottom",
        fontsize=8,
    )
    ax.set_title("Cycle-to-cycle magnetic change", fontsize=10)
    ax.set_xlabel("loading cycle")
    ax.set_ylabel("ΔBvec vs cycle 1 (uT)")
    ax.grid(True, axis="y", color="#e7e7e7", lw=0.8)

    ax = axes[2]
    width = 0.22
    xs = [c - width for c in cycles]
    ax.bar(xs, dBx, width=width, color=COLOR_BLACK, label="dBx")
    ax.bar(cycles, dBy, width=width, color=COLOR_RED, label="dBy")
    ax.bar([c + width for c in cycles], dBz, width=width, color=COLOR_BLUE, label="dBz")
    ax.axhline(0, color=COLOR_GRAY, lw=0.9)
    ax.set_title("Component-level repeated-loading drift", fontsize=10)
    ax.set_xlabel("loading cycle")
    ax.set_ylabel("component vs cycle 1 (uT)")
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper left")
    ax.grid(True, axis="y", color="#e7e7e7", lw=0.8)

    for ax in axes:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.tight_layout(rect=[0, 0, 1, 0.88])
    fig.savefig(png_path, bbox_inches="tight")
    plt.close(fig)


def register_formal_design_session(session_id: str, status: str, note: str = "") -> None:
    if not base.FORMAL_DESIGN_PATH.exists():
        print(f"  ! formal design registry skipped: missing {base.FORMAL_DESIGN_PATH.name}")
        return
    changed = register_session(
        base.FORMAL_DESIGN_PATH,
        FORMAL_EXPERIMENT_KEY,
        SessionRecord(
            session_id=session_id,
            status=status,
            summary_filename=SUMMARY_FILENAME,
            figure_filename=FIGURE_FILENAME,
            note=note,
        ),
    )
    if changed:
        print(
            f"  registry -> {base.FORMAL_DESIGN_PATH.name} "
            f"({FORMAL_EXPERIMENT_KEY}, {status})"
        )
    else:
        print(
            f"  registry already contains {session_id} "
            f"({FORMAL_EXPERIMENT_KEY})"
        )


def parse_args() -> None:
    if len(sys.argv) <= 1:
        return
    if len(sys.argv) == 2 and sys.argv[1] == "340":
        return
    raise SystemExit("Usage: python .\\apmd_repeated_loading_control.py [340]")


def main() -> None:
    parse_args()
    configure_base_protocol()
    base.OUTPUT_ROOT.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"session_{ts}"
    session_dir = base.OUTPUT_ROOT / session_id
    session_dir.mkdir(parents=True)
    log_path = session_dir / "run_log.txt"
    summary_path = session_dir / SUMMARY_FILENAME
    png_path = session_dir / FIGURE_FILENAME

    cycle_plan = build_cycle_plan()
    expected_cycles = len(cycle_plan)
    acquired_cycles = 0
    cycle_summaries: list[tuple[LoadingCycle, dict, dict]] = []
    run_status = ""
    registry_note = ""

    est_total_min = (
        expected_cycles
        * (
            base.TARGET_RECORD_S
            + base.PRE_RECORD_SETTLE_S
            + base.INTER_TRIAL_REST_S
            + 1.5
        )
        / 60
    )

    print("\n" + "=" * 72)
    print(f"  {base.PROTOCOL_TITLE}")
    print("=" * 72)
    print(f"  session        : {session_id}")
    print(f"  target d       : {TARGET_D_MM:.2f} mm")
    print(f"  cycles         : {expected_cycles}")
    print("  deeper preload : OFF")
    print(f"  target record  : {base.TARGET_RECORD_S:.0f} s")
    print(f"  summary window : last {base.SUMMARY_WINDOW_S:.0f} s median")
    print(f"  rest/cycle     : {base.INTER_TRIAL_REST_S:.0f} s")
    print(f"  control gate   : cycle-to-cycle ΔBvec <= {CONTROL_B_GATE_UT:.0f} uT")
    print(f"  est total      : ~{est_total_min:.1f} min")
    print()
    print("Pre-flight:")
    print("  [ ] Same sample / magnet / MLX geometry as selected active path sessions")
    print("  [ ] Mark-10 start position about 6 mm above lower limit")
    print("  [ ] Clear visible gap above the sample at the start position")
    print("  [ ] EasyMESUR Home -> PC Control ACTIVE")
    print("  [ ] Arduino IDE Serial Monitor on UNO CLOSED")
    print("  [ ] QT Py / MLX running circuitpython/code.py")
    print()
    try:
        input("Press Enter to start (Ctrl+C aborts) ... ")
    except KeyboardInterrupt:
        return

    print("\nOpening MLX90393 first ...")
    try:
        mlx_port = base.MLX_PORT or base.find_mlx_port()
        mlx_ser = base.serial.Serial(mlx_port, base.MLX_BAUD, timeout=0.5)
        if base.MLX_SOFT_REBOOT_ON_OPEN:
            print("  soft-rebooting QT Py stream ...")
            base.soft_reboot_mlx(mlx_ser)
        time.sleep(base.MLX_STARTUP_WAIT_S)
        _, _, n_warmup = base.require_mlx_sample(
            mlx_ser, 1.0, "MLX warmup before opening motion hardware"
        )
        print(f"  MLX90393 stream on {mlx_port}  (warmup n={n_warmup})\n")
    except Exception as exc:
        base.fail_before_trial(
            session_id,
            log_path,
            ts,
            f"MLX90393 required for {base.PROTOCOL_SHORT_NAME}. {exc}",
        )

    print("Opening Mark-10 ...")
    try:
        mark10 = base.Mark10(
            base.MARK10_PORT,
            base.MARK10_BAUD,
            speed_mm_per_min=base.MARK10_SPEED_MM_PER_MIN,
        )
    except base.Mark10Error as exc:
        mlx_ser.close()
        base.fail_before_trial(session_id, log_path, ts, exc)
    print("  Mark-10 ready")

    print("Opening UNO_force ...")
    try:
        force = base.ForceReader(base.find_force_port())
        force.live_tare(
            duration_s=base.LIVE_TARE_S,
            pre_settle_s=base.TARE_PRE_SETTLE_S,
        )
        base.assert_no_contact_live_tare(force, "APMD repeated-loading 7.2 pre-flight")
    except Exception as exc:
        mlx_ser.close()
        mark10.close()
        base.fail_before_trial(
            session_id,
            log_path,
            ts,
            f"Force sensor required for {base.PROTOCOL_SHORT_NAME}. {exc}",
        )

    print("Capturing B0 (no-contact baseline) ...")
    try:
        (b0x, b0y, b0z), _, n_b0 = base.require_mlx_sample(
            mlx_ser, 1.5, "B0 capture"
        )
    except base.MlxNoDataError as exc:
        mlx_ser.close()
        force.close()
        mark10.close()
        base.fail_before_trial(session_id, log_path, ts, exc)
    B0 = (b0x, b0y, b0z)
    print(f"  B0 = ({b0x:+.2f}, {b0y:+.2f}, {b0z:+.2f}) uT  (n={n_b0})")

    trial_start_pos = mark10.position_stable()
    print(f"  trial_start_pos = {trial_start_pos:+.3f} mm")

    log = log_path.open("w", encoding="utf-8")
    log.write(f"# {base.LOG_HEADER} {ts}\n")
    log.write(f"# TARGET_D_MM={TARGET_D_MM}, CYCLES={CYCLES}\n")
    log.write(
        f"# TARGET_RECORD_S={base.TARGET_RECORD_S}, "
        f"SUMMARY_WINDOW_S={base.SUMMARY_WINDOW_S}, "
        f"INTER_CYCLE_REST_S={base.INTER_TRIAL_REST_S}\n"
    )
    log.write(f"# live_tare_N={force.live_tare_N:.5f}\n")
    log.write(f"# B0={B0}\n")
    log.write(
        f"# head_id={base.HEAD_ID}, sample_id={base.SAMPLE_ID}, "
        f"magnet_id={base.MAGNET_ID}, "
        f"force_calibration_id={base.FORCE_CALIBRATION_ID}, "
        f"displacement_zero_id={base.DISPLACEMENT_ZERO_ID}\n"
    )
    log.write(f"# trial_start_pos={trial_start_pos:.4f}\n")
    log.flush()

    summary_file = summary_path.open("w", newline="", encoding="utf-8")
    summary_writer = csv.DictWriter(summary_file, fieldnames=summary_fieldnames())
    summary_writer.writeheader()

    try:
        print("\n" + "=" * 72)
        print("  CONTACT REFERENCE FOR ALL REPEATED-LOADING CYCLES")
        print("=" * 72)
        contact_pos = base.find_contact(mark10, force, 1, log)
        if contact_pos is None:
            print("  ! contact not found; no cycles acquired")
            contact_positions = []
        else:
            contact_depth = abs(contact_pos - trial_start_pos)
            target_positions = fixed_contact_target_positions(
                contact_pos_mm=contact_pos,
                cycles=cycle_plan,
            )
            contact_positions = [contact_pos]
            print(
                f"  fixed contact_pos = {contact_pos:+.3f} mm; "
                f"contact depth from start = {contact_depth:.2f} mm"
            )
            print(
                f"  fixed absolute target pos = {target_positions[0]:+.3f} mm "
                f"for every loading cycle"
            )
            log.write(
                f"[fixed contact reference] contact_pos={contact_pos:.4f} "
                f"target_pos={target_positions[0]:.4f}\n"
            )
            log.flush()

        reference_summary = None
        for cycle in cycle_plan:
            if not contact_positions:
                break
            print("\n" + "=" * 72)
            print(f"  LOADING CYCLE {cycle.cycle}/{expected_cycles}")
            print("=" * 72)

            contact_depth = abs(contact_pos - trial_start_pos)
            planned_depth = contact_depth + cycle.target_d_mm
            print(
                f"  contact depth from start = {contact_depth:.2f} mm; "
                f"planned travel from start ~= {planned_depth:.2f} mm"
            )

            csv_path = (
                session_dir
                / f"{STATE_FILE_PREFIX}_{base.target_label(cycle.target_d_mm)}_cycle{cycle.cycle}.csv"
            )
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=raw_fieldnames())
                writer.writeheader()

                summary = base.collect_state(
                    mark10=mark10,
                    force=force,
                    mlx_ser=mlx_ser,
                    contact_pos=contact_pos,
                    B0=B0,
                    session_id=session_id,
                    trial=cycle.cycle,
                    pair_id=1,
                    target_d_mm=cycle.target_d_mm,
                    preload_d_mm=cycle.preload_d_mm,
                    state_label=cycle.state_label,
                    path_mode=cycle.path_mode,
                    phase="loading_hold",
                    record_s=cycle.record_s,
                    csv_writer=writer,
                    log=log,
                )

            if reference_summary is None:
                reference_summary = summary
            diag = cycle_to_reference_diagnostics(reference_summary, summary)
            cycle_summaries.append((cycle, summary, diag))
            write_cycle_summary(summary_writer, session_id, cycle, summary, diag)
            summary_file.flush()
            acquired_cycles += 1

            print("\n    repeated-loading diagnostic: cycle - cycle 1")
            print(f"      delta F     = {diag['delta_F_vs_cycle1_N']*1000:+.1f} mN")
            print(f"      delta d     = {diag['delta_d_vs_cycle1_mm']:+.3f} mm")
            print(f"      delta |B|   = {diag['delta_Bmag_vs_cycle1_uT']:+.1f} uT")
            print(f"      |delta B3|  = {diag['delta_Bvec_uT']:.1f} uT")
            print(f"      verdict     = {diag['verdict']}")

            log.write(
                f"[cycle {cycle.cycle}] diagnostic "
                f"dF={diag['delta_F_vs_cycle1_N']:+.6f} "
                f"dd={diag['delta_d_vs_cycle1_mm']:+.4f} "
                f"dBvec={diag['delta_Bvec_uT']:.4f} "
                f"verdict={diag['verdict']}\n"
            )
            log.flush()

            print(f"\n  PHASE C: retracting to start ({trial_start_pos:+.3f} mm)")
            try:
                back_pos = mark10.move_to(trial_start_pos)
                print(f"    back at {back_pos:+.3f} mm")
            except base.Mark10Error as exc:
                print(f"  ! retract error: {exc}")

            if cycle.cycle < expected_cycles:
                print(f"\n  resting {base.INTER_TRIAL_REST_S:.0f} s for recovery ...")
                time.sleep(base.INTER_TRIAL_REST_S)

        rows_for_plot = []
        for cycle, summary, diag in cycle_summaries:
            rows_for_plot.append(
                {
                    "cycle": cycle.cycle,
                    "F_N": summary["F_N"],
                    "delta_Bvec_uT": diag["delta_Bvec_uT"],
                    "delta_Bx_vs_cycle1_uT": diag["delta_Bx_vs_cycle1_uT"],
                    "delta_By_vs_cycle1_uT": diag["delta_By_vs_cycle1_uT"],
                    "delta_Bz_vs_cycle1_uT": diag["delta_Bz_vs_cycle1_uT"],
                }
            )
        plot_control_summary(rows_for_plot, png_path)
        print(f"\n  figure saved: {png_path.name}")

        max_dB = max((diag["delta_Bvec_uT"] for _, _, diag in cycle_summaries), default=float("nan"))
        run_status, registry_note = registry_status_for_control(
            acquired_cycles=acquired_cycles,
            expected_cycles=expected_cycles,
            max_delta_Bvec_uT=max_dB,
        )
        if not run_status:
            print(f"\n  formal registry skipped: {registry_note}")
            log.write(f"# formal registry skipped: {registry_note}\n")
            log.flush()

    except KeyboardInterrupt:
        print("\n\nUser abort. Will retract.")
        run_status = ""
        registry_note = (
            f"not registered: user abort after {acquired_cycles}/{expected_cycles} cycles"
        )
    except Exception as exc:
        print(f"\n\n! unexpected error: {exc}")
        log.write(f"\nERROR: {exc}\n")
        run_status = ""
        registry_note = f"not registered: {base.registry_note_from_error(exc)}"
        raise
    finally:
        try:
            mark10.move_to(trial_start_pos)
        except Exception:
            pass
        try:
            summary_file.close()
        except Exception:
            pass
        try:
            log.close()
        except Exception:
            pass
        try:
            mlx_ser.close()
        except Exception:
            pass
        try:
            force.close()
        except Exception:
            pass
        mark10.close()
        if run_status:
            try:
                register_formal_design_session(session_id, run_status, registry_note)
            except Exception as exc:
                print(f"  ! formal design registry update failed: {exc}")

    print(f"\n=== {base.PROTOCOL_SHORT_NAME} done. Files in: {session_dir}")
    for p in sorted(session_dir.glob(CSV_PRINT_GLOB)):
        print(f"  {p.name}")
    print(f"  {summary_path.name}")
    print(f"  {FIGURE_FILENAME}")
    print(f"  {log_path.name}")
    if base.NEXT_MESSAGE:
        print(f"\n{base.NEXT_MESSAGE}")


if __name__ == "__main__":
    main()
