"""APMD Experiment 5.1B: local minor-loop dense model dataset.

This acquisition is for model training, not another path-pair gate test.  It
uses stable displacement-control logic from the same-d/different-F scripts and
records a dense local hysteresis loop:

    loading:   3.0 -> 3.1 -> 3.2 -> 3.3 -> 3.4 -> 3.5 -> 3.6 mm
    preload:   3.8 mm
    unloading: 3.6 -> 3.5 -> 3.4 -> 3.3 -> 3.2 -> 3.1 -> 3.0 mm

Each cycle creates one raw state CSV plus a session-level state summary table.
The intermediate 3.1/3.3/3.5 mm points are included to make the local model
dataset continuous enough for interpolation inside the selected work zone.
"""

from __future__ import annotations

import csv
import sys
import time
from datetime import datetime

import apmd_same_d_different_f_path_pair as base
import apmd_same_d_different_f_scan as scan_helpers


D_GRID_MM = [3.00, 3.10, 3.20, 3.30, 3.40, 3.50, 3.60]
PRELOAD_D_MM = 3.80
N_CYCLES = 5

STATE_RECORD_S = 15.0
PRELOAD_RECORD_S = 30.0
SUMMARY_WINDOW_S = 5.0
PRE_RECORD_SETTLE_S = 3.0
INTER_STATE_SETTLE_S = 1.0
INTER_CYCLE_REST_S = 120.0

SUMMARY_FILENAME = "local_minor_loop_dense_5p1B_state_summary.csv"
STATE_FILE_PREFIX = "local_minor_loop_dense_5p1B"
FIGURE_FILENAME = "local_minor_loop_dense_5p1B.png"
CSV_PRINT_GLOB = f"{STATE_FILE_PREFIX}*.csv"

WORK_ZONE_BLOCK = "M"

WORK_ZONE_CONFIGS = {
    "M": {
        "d_grid_mm": [3.00, 3.10, 3.20, 3.30, 3.40, 3.50, 3.60],
        "preload_d_mm": 3.80,
        "summary_filename": "local_minor_loop_dense_5p1B_state_summary.csv",
        "state_file_prefix": "local_minor_loop_dense_5p1B",
        "figure_filename": "local_minor_loop_dense_5p1B.png",
        "stage_label": "local_minor_loop_5p1B",
        "formal_experiment_key": "\u5b9e\u9a8c 5.1B",
        "protocol_suffix": "Block M",
    },
    "L": {
        "d_grid_mm": [2.40, 2.50, 2.60, 2.70, 2.80, 2.90, 3.00],
        "preload_d_mm": 3.20,
        "summary_filename": "local_minor_loop_dense_5p1B_L_state_summary.csv",
        "state_file_prefix": "local_minor_loop_dense_5p1B_L",
        "figure_filename": "local_minor_loop_dense_5p1B_L.png",
        "stage_label": "local_minor_loop_5p1B_L",
        "formal_experiment_key": "\u5b9e\u9a8c 5.1B-L",
        "protocol_suffix": "Block L",
    },
}


def parse_work_zone_arg(argv=None) -> str:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return "M"
    if len(args) != 1:
        raise SystemExit("Usage: python .\\apmd_local_minor_loop_dense_sampling.py [M|L]")
    block = args[0].upper()
    if block not in WORK_ZONE_CONFIGS:
        raise SystemExit("Unknown work-zone block. Use M or L.")
    return block


def apply_work_zone_config(block: str) -> None:
    global WORK_ZONE_BLOCK
    global D_GRID_MM, PRELOAD_D_MM, SUMMARY_FILENAME
    global STATE_FILE_PREFIX, FIGURE_FILENAME, CSV_PRINT_GLOB

    block = block.upper()
    if block not in WORK_ZONE_CONFIGS:
        raise ValueError(f"Unknown work-zone block: {block}")

    cfg = WORK_ZONE_CONFIGS[block]
    WORK_ZONE_BLOCK = block
    D_GRID_MM = list(cfg["d_grid_mm"])
    PRELOAD_D_MM = cfg["preload_d_mm"]
    SUMMARY_FILENAME = cfg["summary_filename"]
    STATE_FILE_PREFIX = cfg["state_file_prefix"]
    FIGURE_FILENAME = cfg["figure_filename"]
    CSV_PRINT_GLOB = f"{STATE_FILE_PREFIX}*.csv"


def configure_base_protocol() -> None:
    cfg = WORK_ZONE_CONFIGS[WORK_ZONE_BLOCK]
    base.PROTOCOL_TITLE = (
        "APMD Experiment 5.1B -- local minor-loop dense model dataset "
        f"({cfg['protocol_suffix']})"
    )
    base.PROTOCOL_SHORT_NAME = f"APMD local minor-loop 5.1B {WORK_ZONE_BLOCK}"
    base.STAGE_LABEL = cfg["stage_label"]
    base.LOG_HEADER = f"APMD local minor-loop 5.1B {WORK_ZONE_BLOCK} session"

    base.N_TRIALS = N_CYCLES
    base.D_TARGETS_MM = list(D_GRID_MM)
    base.D_PRELOAD_BY_TARGET_MM = {d: PRELOAD_D_MM for d in D_GRID_MM}
    base.D_PRELOAD_MM = PRELOAD_D_MM

    base.TARGET_RECORD_S = STATE_RECORD_S
    base.PRELOAD_RECORD_S = PRELOAD_RECORD_S
    base.SUMMARY_WINDOW_S = SUMMARY_WINDOW_S
    base.PRE_RECORD_SETTLE_S = PRE_RECORD_SETTLE_S
    base.INTER_STATE_SETTLE_S = INTER_STATE_SETTLE_S
    base.INTER_TRIAL_REST_S = INTER_CYCLE_REST_S
    base.ROW_PRINT_EVERY_S = 5.0
    base.F_HARD_LIMIT_N = None

    base.SUMMARY_FILENAME = SUMMARY_FILENAME
    base.STATE_FILE_PREFIX = STATE_FILE_PREFIX
    base.CSV_PRINT_GLOB = CSV_PRINT_GLOB
    base.FIGURE_FILENAME = FIGURE_FILENAME
    base.PREFLIGHT_FIRST_LINE = (
        f"Experiment 5.1B-{WORK_ZONE_BLOCK}: local dense minor-loop model dataset"
    )
    base.NEXT_MESSAGE = (
        "Next: run Stage 5 dataset builder and retrain local model."
    )
    base.FORMAL_EXPERIMENT_KEY = cfg["formal_experiment_key"]


def iter_loop_states():
    state_index = 1
    for d_mm in D_GRID_MM:
        yield {
            "state_index": state_index,
            "branch": "loading",
            "state_label": f"loading_d_{base.target_label(d_mm)}",
            "path_mode": "loading_branch",
            "phase": "loading_dense",
            "target_d_mm": d_mm,
            "record_s": STATE_RECORD_S,
        }
        state_index += 1

    yield {
        "state_index": state_index,
        "branch": "preload",
        "state_label": f"preload_d_{base.target_label(PRELOAD_D_MM)}",
        "path_mode": "preload_loading",
        "phase": "preload_dense",
        "target_d_mm": PRELOAD_D_MM,
        "record_s": PRELOAD_RECORD_S,
    }
    state_index += 1

    for d_mm in reversed(D_GRID_MM):
        yield {
            "state_index": state_index,
            "branch": "unloading",
            "state_label": f"unloading_d_{base.target_label(d_mm)}",
            "path_mode": "return_unloading",
            "phase": "unloading_dense",
            "target_d_mm": d_mm,
            "record_s": STATE_RECORD_S,
        }
        state_index += 1


def state_summary_fields():
    return [
        "session_id",
        *base.metadata_fieldnames(),
        "cycle",
        "state_index",
        "branch",
        "state_label",
        "path_mode",
        "phase",
        "d_target_mm",
        "d_preload_mm",
        "record_s",
        "summary_window_s",
        "n",
        "d_median_mm",
        "F_median_N",
        "Bmag_median_uT",
        "Bx_median_uT",
        "By_median_uT",
        "Bz_median_uT",
        "delta_Bx_median_uT",
        "delta_By_median_uT",
        "delta_Bz_median_uT",
    ]


def write_state_summary(writer, session_id, cycle, state, summary):
    writer.writerow(
        {
            "session_id": session_id,
            **base.metadata_values(),
            "cycle": cycle,
            "state_index": state["state_index"],
            "branch": state["branch"],
            "state_label": state["state_label"],
            "path_mode": state["path_mode"],
            "phase": state["phase"],
            "d_target_mm": f"{state['target_d_mm']:.4f}",
            "d_preload_mm": f"{PRELOAD_D_MM:.4f}",
            "record_s": f"{state['record_s']:.1f}",
            "summary_window_s": f"{SUMMARY_WINDOW_S:.1f}",
            "n": summary["n"],
            "d_median_mm": f"{summary['d_mm']:.4f}",
            "F_median_N": f"{summary['F_N']:.6f}",
            "Bmag_median_uT": f"{summary['Bmag_uT']:.4f}",
            "Bx_median_uT": f"{summary['Bx_uT']:.4f}",
            "By_median_uT": f"{summary['By_uT']:.4f}",
            "Bz_median_uT": f"{summary['Bz_uT']:.4f}",
            "delta_Bx_median_uT": f"{summary['delta_Bx_uT']:.4f}",
            "delta_By_median_uT": f"{summary['delta_By_uT']:.4f}",
            "delta_Bz_median_uT": f"{summary['delta_Bz_uT']:.4f}",
        }
    )


def registry_status(completed_states: int, expected_states: int):
    if completed_states == expected_states:
        return "formal", ""
    return "", (
        f"not registered: {completed_states}/{expected_states} "
        "planned dense-loop states completed"
    )


def main(argv=None, apply_cli_config: bool = True) -> None:
    if apply_cli_config:
        apply_work_zone_config(parse_work_zone_arg(argv))
    configure_base_protocol()
    base.OUTPUT_ROOT.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"session_{ts}"
    session_dir = base.OUTPUT_ROOT / session_id
    session_dir.mkdir(parents=True)
    log_path = session_dir / "run_log.txt"
    summary_path = session_dir / SUMMARY_FILENAME

    loop_states = list(iter_loop_states())
    expected_states = N_CYCLES * len(loop_states)
    completed_states = 0
    run_status = ""
    registry_note = ""

    cycle_active_s = sum(s["record_s"] for s in loop_states)
    est_total_min = (
        N_CYCLES
        * (
            cycle_active_s
            + len(loop_states) * base.PRE_RECORD_SETTLE_S
            + (len(loop_states) - 1) * base.INTER_STATE_SETTLE_S
            + base.INTER_TRIAL_REST_S
            + 1.5
        )
        / 60
    )

    print("\n" + "=" * 72)
    print(f"  {base.PROTOCOL_TITLE}")
    print("=" * 72)
    print(f"  session        : {session_id}")
    print(f"  d grid         : {D_GRID_MM}")
    print(f"  preload d      : {PRELOAD_D_MM:.2f} mm")
    print(f"  cycles         : {N_CYCLES}")
    print(f"  state record   : {STATE_RECORD_S:.0f} s")
    print(f"  preload record : {PRELOAD_RECORD_S:.0f} s")
    print(f"  summary window : last {SUMMARY_WINDOW_S:.0f} s median")
    print(f"  rest/cycle     : {INTER_CYCLE_REST_S:.0f} s")
    print(f"  planned states : {expected_states}")
    print(f"  est total      : ~{est_total_min:.1f} min")
    print()
    print("Pre-flight:")
    print("  [ ] Mark-10 start position about 6 mm above lower limit")
    print("  [ ] Clear visible gap above the sample at the start position")
    print("  [ ] Same sample / magnet / MLX geometry for the whole dense-loop run")
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
        base.assert_no_contact_live_tare(
            force, "APMD local minor-loop 5.1B pre-flight"
        )
    except Exception as exc:
        mlx_ser.close()
        mark10.close()
        base.fail_before_trial(
            session_id,
            log_path,
            ts,
            f"Force sensor required for {base.PROTOCOL_SHORT_NAME}. {exc}",
        )

    trial_start_pos = mark10.position_stable()
    print(f"  trial_start_pos = {trial_start_pos:+.3f} mm")

    log = log_path.open("w", encoding="utf-8")
    log.write(f"# {base.LOG_HEADER} {ts}\n")
    log.write(f"# D_GRID_MM={D_GRID_MM}, PRELOAD_D_MM={PRELOAD_D_MM}\n")
    log.write(
        f"# STATE_RECORD_S={STATE_RECORD_S}, "
        f"PRELOAD_RECORD_S={PRELOAD_RECORD_S}, "
        f"N_CYCLES={N_CYCLES}\n"
    )
    log.write(f"# live_tare_N={force.live_tare_N:.5f}\n")
    log.write(
        f"# head_id={base.HEAD_ID}, sample_id={base.SAMPLE_ID}, "
        f"magnet_id={base.MAGNET_ID}, "
        f"force_calibration_id={base.FORCE_CALIBRATION_ID}, "
        f"displacement_zero_id={base.DISPLACEMENT_ZERO_ID}\n"
    )
    log.write(f"# trial_start_pos={trial_start_pos:.4f}\n")
    log.flush()

    summary_file = summary_path.open("w", newline="", encoding="utf-8")
    summary_writer = csv.DictWriter(summary_file, fieldnames=state_summary_fields())
    summary_writer.writeheader()

    try:
        for cycle in range(1, N_CYCLES + 1):
            print("\n" + "=" * 72)
            print(f"  LOCAL MINOR LOOP CYCLE {cycle}/{N_CYCLES}")
            print("=" * 72)

            print("  Capturing cycle-local B0 (no-contact baseline) ...")
            B0, n_b0 = scan_helpers._capture_b0(
                mlx_ser, f"B0 capture 5.1B cycle={cycle}"
            )
            print(
                f"    B0 = ({B0[0]:+.2f}, {B0[1]:+.2f}, {B0[2]:+.2f}) "
                f"uT  (n={n_b0})"
            )
            log.write(f"[cycle {cycle}] B0={B0} n={n_b0}\n")
            log.flush()

            contact_pos = base.find_contact(mark10, force, cycle, log)
            if contact_pos is None:
                print(f"  ! contact not found, skipping cycle {cycle}")
                continue

            contact_depth = abs(contact_pos - trial_start_pos)
            planned_depth = contact_depth + PRELOAD_D_MM
            print(
                f"  contact depth from start = {contact_depth:.2f} mm; "
                f"max planned travel from start ~= {planned_depth:.2f} mm"
            )

            csv_path = session_dir / f"{STATE_FILE_PREFIX}_cycle{cycle}.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=scan_helpers._fieldnames())
                writer.writeheader()

                for i, state in enumerate(loop_states, start=1):
                    print(
                        f"\n  STATE {i}/{len(loop_states)} "
                        f"({state['branch']}): d={state['target_d_mm']:.2f} mm"
                    )
                    summary = base.collect_state(
                        mark10=mark10,
                        force=force,
                        mlx_ser=mlx_ser,
                        contact_pos=contact_pos,
                        B0=B0,
                        session_id=session_id,
                        trial=cycle,
                        pair_id=cycle,
                        target_d_mm=state["target_d_mm"],
                        preload_d_mm=PRELOAD_D_MM,
                        state_label=state["state_label"],
                        path_mode=state["path_mode"],
                        phase=state["phase"],
                        record_s=state["record_s"],
                        csv_writer=writer,
                        log=log,
                    )
                    write_state_summary(
                        summary_writer, session_id, cycle, state, summary
                    )
                    summary_file.flush()
                    completed_states += 1

                    log.write(
                        f"[cycle {cycle} state {state['state_index']}] "
                        f"{state['state_label']} d={summary['d_mm']:.4f} "
                        f"F={summary['F_N']:.6f} "
                        f"Bmag={summary['Bmag_uT']:.4f}\n"
                    )
                    log.flush()
                    if i < len(loop_states):
                        time.sleep(base.INTER_STATE_SETTLE_S)

            print(f"\n  PHASE C: retracting to start ({trial_start_pos:+.3f} mm)")
            try:
                back_pos = mark10.move_to(trial_start_pos)
                print(f"    back at {back_pos:+.3f} mm")
            except base.Mark10Error as exc:
                print(f"  ! retract error: {exc}")

            if cycle < N_CYCLES:
                print(f"\n  resting {base.INTER_TRIAL_REST_S:.0f} s for recovery ...")
                time.sleep(base.INTER_TRIAL_REST_S)

        run_status, registry_note = registry_status(completed_states, expected_states)
        if run_status:
            registry_note = (
                f"cycles={N_CYCLES}; states={completed_states}/{expected_states}; "
                f"d_grid={D_GRID_MM}; preload={PRELOAD_D_MM:.2f} mm"
            )
        else:
            print(f"\n  formal registry skipped: {registry_note}")
            log.write(f"# formal registry skipped: {registry_note}\n")
            log.flush()

    except KeyboardInterrupt:
        print("\n\nUser abort. Will retract.")
        run_status = ""
        registry_note = (
            f"not registered: user abort after "
            f"{completed_states}/{expected_states} dense-loop states"
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
                base.register_formal_design_session(
                    session_id,
                    run_status,
                    registry_note,
                )
            except Exception as exc:
                print(f"  ! formal design registry update failed: {exc}")

    print(f"\nDense-loop state overview: {completed_states}/{expected_states} states")
    print(f"\n=== {base.PROTOCOL_SHORT_NAME} done. Files in: {session_dir}")
    for p in sorted(session_dir.glob(CSV_PRINT_GLOB)):
        print(f"  {p.name}")
    print(f"  {SUMMARY_FILENAME}")
    print(f"  {log_path.name}")
    if base.NEXT_MESSAGE:
        print(f"\n{base.NEXT_MESSAGE}")


if __name__ == "__main__":
    main()
