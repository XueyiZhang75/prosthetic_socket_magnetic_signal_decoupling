"""APMD Experiment 3.1: same-d / different-F coarse work-zone scan.

This script tests whether the current setup still has a strong active path-pair
magnetic response at some displacement work zone. Each target displacement is
run as an independent minor-loop block:

    no-contact B0
    contact search
    direct loading to target d
    deeper preload
    return unloading to target d
    retract to no-contact start
    rest

The target-major order avoids carrying path history from one target d into the
next target d.
"""

from __future__ import annotations

import csv
import math
import statistics
import sys
import time
from datetime import datetime

import apmd_same_d_different_f_path_pair as base


SCAN_BLOCKS = {
    "A": {
        "targets": [2.40, 2.60, 2.80],
        "experiment_key": "实验 3.1A",
        "title": (
            "APMD Experiment 3.1A -- same-d/different-F coarse work-zone scan"
        ),
        "short_name": "APMD same-d/different-F scan 3.1A",
        "summary_filename": "same_d_different_f_scan_A_pair_summary.csv",
        "state_prefix": "same_d_different_f_scan_A",
        "figure_filename": "same_d_different_f_scan_A.png",
        "next_message": "Next: run Experiment 3.1B with: python .\\apmd_same_d_different_f_scan.py B",
    },
    "B": {
        "targets": [3.00, 3.20, 3.40, 3.60],
        "experiment_key": "实验 3.1B",
        "title": (
            "APMD Experiment 3.1B -- same-d/different-F deep work-zone scan"
        ),
        "short_name": "APMD same-d/different-F scan 3.1B",
        "summary_filename": "same_d_different_f_scan_B_pair_summary.csv",
        "state_prefix": "same_d_different_f_scan_B",
        "figure_filename": "same_d_different_f_scan_B.png",
        "next_message": "Next: inspect 3.1A/3.1B summaries, then enter Experiment 3.2.",
    },
    "L": {
        "targets": [2.40, 2.60, 2.80, 3.00],
        "fixed_preload": 3.20,
        "experiment_key": "Block L same-d local sensitivity",
        "title": (
            "APMD Block L -- same-d/different-F local sensitivity calibration"
        ),
        "short_name": "APMD Block L same-d local sensitivity",
        "summary_filename": "block_L_same_d_local_sensitivity_pair_summary.csv",
        "state_prefix": "block_L_same_d_local_sensitivity",
        "figure_filename": "block_L_same_d_local_sensitivity.png",
        "next_message": "Next: inspect Block L same-d sensitivity, then run Block L same-F sensitivity calibration.",
    },
    "L300": {
        "targets": [3.00],
        "fixed_preload": 3.20,
        "experiment_key": "Block L same-d local sensitivity d=3.00 supplement",
        "title": (
            "APMD Block L -- same-d/different-F d=3.00 supplement"
        ),
        "short_name": "APMD Block L same-d d=3.00 supplement",
        "summary_filename": "block_L_same_d_local_sensitivity_pair_summary.csv",
        "state_prefix": "block_L_same_d_local_sensitivity",
        "figure_filename": "block_L_same_d_local_sensitivity.png",
        "next_message": "Next: inspect Block L same-d sensitivity, then run Block L same-F sensitivity calibration.",
    },
    "S": {
        "targets": [1.80, 2.00, 2.20, 2.40],
        "fixed_preload": 2.60,
        "experiment_key": "Shallow work-zone same-d local sensitivity",
        "title": (
            "APMD Shallow work zone -- same-d/different-F local sensitivity calibration"
        ),
        "short_name": "APMD shallow work-zone same-d local sensitivity",
        "summary_filename": "shallow_same_d_local_sensitivity_pair_summary.csv",
        "state_prefix": "shallow_same_d_local_sensitivity",
        "figure_filename": "shallow_same_d_local_sensitivity.png",
        "next_message": "Next: inspect shallow work-zone same-d sensitivity, then rebuild Stage 5/6 model after accepted shallow dense-loop and held-out data are recorded.",
    },
    "S180": {
        "targets": [1.80],
        "fixed_preload": 2.60,
        "experiment_key": "Shallow work-zone same-d local sensitivity d=1.80 supplement",
        "title": (
            "APMD Shallow work zone -- same-d/different-F d=1.80 supplement"
        ),
        "short_name": "APMD shallow work-zone same-d d=1.80 supplement",
        "summary_filename": "shallow_same_d_local_sensitivity_pair_summary.csv",
        "state_prefix": "shallow_same_d_local_sensitivity",
        "figure_filename": "shallow_same_d_local_sensitivity.png",
        "next_message": "Next: inspect shallow work-zone same-d sensitivity, then run the next needed shallow same-d target.",
    },
    "S200": {
        "targets": [2.00],
        "fixed_preload": 2.60,
        "experiment_key": "Shallow work-zone same-d local sensitivity d=2.00 supplement",
        "title": (
            "APMD Shallow work zone -- same-d/different-F d=2.00 supplement"
        ),
        "short_name": "APMD shallow work-zone same-d d=2.00 supplement",
        "summary_filename": "shallow_same_d_local_sensitivity_pair_summary.csv",
        "state_prefix": "shallow_same_d_local_sensitivity",
        "figure_filename": "shallow_same_d_local_sensitivity.png",
        "next_message": "Next: inspect shallow work-zone same-d sensitivity, then run the next needed shallow same-d target.",
    },
    "S220": {
        "targets": [2.20],
        "fixed_preload": 2.60,
        "experiment_key": "Shallow work-zone same-d local sensitivity d=2.20 supplement",
        "title": (
            "APMD Shallow work zone -- same-d/different-F d=2.20 supplement"
        ),
        "short_name": "APMD shallow work-zone same-d d=2.20 supplement",
        "summary_filename": "shallow_same_d_local_sensitivity_pair_summary.csv",
        "state_prefix": "shallow_same_d_local_sensitivity",
        "figure_filename": "shallow_same_d_local_sensitivity.png",
        "next_message": "Next: inspect shallow work-zone same-d sensitivity, then run the next needed shallow same-d target.",
    },
    "S240": {
        "targets": [2.40],
        "fixed_preload": 2.60,
        "experiment_key": "Shallow work-zone same-d local sensitivity d=2.40 supplement",
        "title": (
            "APMD Shallow work zone -- same-d/different-F d=2.40 supplement"
        ),
        "short_name": "APMD shallow work-zone same-d d=2.40 supplement",
        "summary_filename": "shallow_same_d_local_sensitivity_pair_summary.csv",
        "state_prefix": "shallow_same_d_local_sensitivity",
        "figure_filename": "shallow_same_d_local_sensitivity.png",
        "next_message": "Next: inspect shallow work-zone same-d sensitivity, then run the next needed shallow same-d target.",
    },
    "H": {
        "targets": [3.40, 3.60, 3.80, 4.00],
        "fixed_preload": 4.20,
        "experiment_key": "Upper work-zone same-d local sensitivity",
        "title": (
            "APMD Upper work zone -- same-d/different-F local sensitivity calibration"
        ),
        "short_name": "APMD upper work-zone same-d local sensitivity",
        "summary_filename": "upper_same_d_local_sensitivity_pair_summary.csv",
        "state_prefix": "upper_same_d_local_sensitivity",
        "figure_filename": "upper_same_d_local_sensitivity.png",
        "next_message": "Next: inspect upper work-zone same-d sensitivity, then rebuild Stage 5/6 local-ID model after accepted dense-loop and held-out data are recorded.",
    },
}

SCAN_BLOCK = "A"
SCAN_TARGETS_MM = []
SCAN_PRELOAD_BY_TARGET_MM = {}
SCAN_TRIALS = 3

SUMMARY_FILENAME = ""
STATE_FILE_PREFIX = ""
CSV_PRINT_GLOB = ""
SCAN_PROTOCOL_TITLE = ""
SCAN_PROTOCOL_SHORT_NAME = ""
SCAN_LOG_HEADER = ""
SCAN_FORMAL_EXPERIMENT_KEY = ""
SCAN_FIGURE_FILENAME = ""
SCAN_NEXT_MESSAGE = ""


def apply_scan_block(block_name):
    global SCAN_BLOCK, SCAN_TARGETS_MM, SCAN_PRELOAD_BY_TARGET_MM
    global SUMMARY_FILENAME, STATE_FILE_PREFIX, CSV_PRINT_GLOB
    global SCAN_PROTOCOL_TITLE, SCAN_PROTOCOL_SHORT_NAME, SCAN_LOG_HEADER
    global SCAN_FORMAL_EXPERIMENT_KEY, SCAN_FIGURE_FILENAME, SCAN_NEXT_MESSAGE

    key = str(block_name).upper()
    if key not in SCAN_BLOCKS:
        valid = ", ".join(sorted(SCAN_BLOCKS))
        raise ValueError(f"unknown scan block {block_name!r}; use one of: {valid}")

    spec = SCAN_BLOCKS[key]
    targets = [float(v) for v in spec["targets"]]
    SCAN_BLOCK = key
    SCAN_TARGETS_MM = targets
    if "fixed_preload" in spec:
        fixed_preload = round(float(spec["fixed_preload"]), 2)
        SCAN_PRELOAD_BY_TARGET_MM = {
            round(target, 2): fixed_preload for target in targets
        }
    else:
        SCAN_PRELOAD_BY_TARGET_MM = {
            round(target, 2): round(target + 0.30, 2) for target in targets
        }
    SUMMARY_FILENAME = spec["summary_filename"]
    STATE_FILE_PREFIX = spec["state_prefix"]
    CSV_PRINT_GLOB = f"{STATE_FILE_PREFIX}*.csv"
    SCAN_PROTOCOL_TITLE = spec["title"]
    SCAN_PROTOCOL_SHORT_NAME = spec["short_name"]
    SCAN_LOG_HEADER = f"{spec['short_name']} session"
    SCAN_FORMAL_EXPERIMENT_KEY = spec["experiment_key"]
    SCAN_FIGURE_FILENAME = spec["figure_filename"]
    SCAN_NEXT_MESSAGE = spec["next_message"]


def configure_base_protocol():
    base.PROTOCOL_TITLE = SCAN_PROTOCOL_TITLE
    base.PROTOCOL_SHORT_NAME = SCAN_PROTOCOL_SHORT_NAME
    base.STAGE_LABEL = "same_d_diff_f_scan"
    base.LOG_HEADER = SCAN_LOG_HEADER

    base.N_TRIALS = SCAN_TRIALS
    base.D_TARGETS_MM = list(SCAN_TARGETS_MM)
    base.D_PRELOAD_BY_TARGET_MM = dict(SCAN_PRELOAD_BY_TARGET_MM)
    base.D_PRELOAD_MM = SCAN_PRELOAD_BY_TARGET_MM[SCAN_TARGETS_MM[0]]

    base.TARGET_RECORD_S = 45.0
    base.PRELOAD_RECORD_S = 30.0
    base.SUMMARY_WINDOW_S = 10.0
    base.INTER_TRIAL_REST_S = 120.0
    base.F_HARD_LIMIT_N = None

    base.SUMMARY_FILENAME = SUMMARY_FILENAME
    base.STATE_FILE_PREFIX = STATE_FILE_PREFIX
    base.CSV_PRINT_GLOB = CSV_PRINT_GLOB
    base.FIGURE_FILENAME = SCAN_FIGURE_FILENAME
    base.PREFLIGHT_FIRST_LINE = (
        f"This is {SCAN_FORMAL_EXPERIMENT_KEY}: coarse scan of same-d/different-F work zones"
    )
    base.NEXT_MESSAGE = SCAN_NEXT_MESSAGE
    base.FORMAL_EXPERIMENT_KEY = SCAN_FORMAL_EXPERIMENT_KEY


def parse_scan_block(argv):
    valid = "|".join(sorted(SCAN_BLOCKS))
    if not argv:
        return "A"
    if len(argv) != 1:
        raise SystemExit(
            f"Usage: python .\\apmd_same_d_different_f_scan.py [{valid}]"
        )
    block = argv[0].upper()
    if block not in SCAN_BLOCKS:
        raise SystemExit(
            f"Usage: python .\\apmd_same_d_different_f_scan.py [{valid}]"
        )
    return block


apply_scan_block(SCAN_BLOCK)


def iter_scan_plan(targets=None, preload_map=None, trials=None):
    if targets is None:
        targets = SCAN_TARGETS_MM
    if preload_map is None:
        preload_map = SCAN_PRELOAD_BY_TARGET_MM
    if trials is None:
        trials = SCAN_TRIALS
    for pair_id, target_d in enumerate(targets, start=1):
        preload_d = preload_map[round(float(target_d), 2)]
        for trial in range(1, trials + 1):
            yield {
                "pair_id": pair_id,
                "trial": trial,
                "target_d_mm": float(target_d),
                "preload_d_mm": float(preload_d),
            }


def _median(values):
    clean = [v for v in values if not math.isnan(v)]
    if not clean:
        return float("nan")
    return statistics.median(clean)


def _capture_b0(mlx_ser, context):
    (b0x, b0y, b0z), _, n_b0 = base.require_mlx_sample(mlx_ser, 1.5, context)
    return (b0x, b0y, b0z), n_b0


def _fieldnames():
    return [
        "time_s", "session_id", "trial", "repeat_id", "pair_id", "stage",
        "state_label", "phase", "control_mode", "path_mode", "target_label",
        "d_target_mm", "d_preload_mm", "d_actual_mm", "d_mm", "q_mm",
        "d_error_mm", "mark10_pos_mm", "t_rel_s", "F_N",
        "mean_Bx_uT", "mean_By_uT", "mean_Bz_uT",
        "delta_Bx_uT", "delta_By_uT", "delta_Bz_uT", "Bmag_uT",
        *base.metadata_fieldnames(), "note",
    ]


def _summary_fields():
    return [
        "session_id", *base.metadata_fieldnames(), "trial", "pair_id",
        "target_label", "d_target_mm", "d_preload_mm", "d_direct_mm",
        "d_return_mm", "d_diff_mm", "F_direct_N", "F_return_N",
        "delta_F_N", "Bmag_direct_uT", "Bmag_return_uT", "delta_Bmag_uT",
        "delta_Bx_uT", "delta_By_uT", "delta_Bz_uT", "delta_Bvec_uT",
        "slope_Bmag_uT_per_N", "same_d_ok", "force_split_ok",
        "b_signal_ok", "verdict",
    ]


def _print_target_overview(rows):
    if not rows:
        return
    print("\nTarget-d scan overview:")
    for target_d in SCAN_TARGETS_MM:
        subset = [r for r in rows if abs(r["target_d_mm"] - target_d) < 1e-9]
        if not subset:
            continue
        same_d = sum(1 for r in subset if r["same_d_ok"])
        strong = sum(1 for r in subset if r["verdict"] == "strong")
        med_dd = _median([abs(r["d_diff_mm"]) for r in subset])
        med_dF = _median([abs(r["delta_F_N"]) for r in subset])
        med_dB = _median([r["delta_Bvec_uT"] for r in subset])
        ratio = med_dB / med_dF if med_dF > 1e-9 else float("nan")
        print(
            f"  d={target_d:.2f} mm: same-d {same_d}/{SCAN_TRIALS}, "
            f"strong {strong}/{SCAN_TRIALS}, "
            f"median |dd|={med_dd:.3f} mm, "
            f"median |dF|={med_dF*1000:.1f} mN, "
            f"median dBvec={med_dB:.1f} uT, "
            f"dBvec/|dF|={ratio:.1f} uT/N"
        )


def _scan_registry_status(pair_summary_count, expected_pair_count):
    if pair_summary_count == expected_pair_count:
        return "formal", ""
    return "", (
        f"not registered: {pair_summary_count}/{expected_pair_count} "
        "planned scan pairs completed"
    )


def main(argv=None):
    block = parse_scan_block(sys.argv[1:] if argv is None else argv)
    apply_scan_block(block)
    configure_base_protocol()
    base.OUTPUT_ROOT.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"session_{ts}"
    session_dir = base.OUTPUT_ROOT / session_id
    session_dir.mkdir(parents=True)
    log_path = session_dir / "run_log.txt"
    summary_path = session_dir / SUMMARY_FILENAME
    scan_plan = list(iter_scan_plan())
    expected_pair_count = len(scan_plan)
    pair_summary_count = 0
    strong_pair_count = 0
    same_d_pair_count = 0
    summary_rows = []
    run_status = ""
    registry_note = ""

    est_total_min = (
        expected_pair_count
        * (
            2 * base.TARGET_RECORD_S
            + base.PRELOAD_RECORD_S
            + 3 * base.PRE_RECORD_SETTLE_S
            + 3 * base.INTER_STATE_SETTLE_S
            + base.INTER_TRIAL_REST_S
            + 1.5
        )
        / 60
    )

    print("\n" + "=" * 72)
    print(f"  {base.PROTOCOL_TITLE}")
    print("=" * 72)
    print(f"  session        : {session_id}")
    print(f"  targets        : {base.D_TARGETS_MM}")
    print(f"  trials/target  : {base.N_TRIALS}")
    print("  preload plan   : "
          + ", ".join(
              f"{d:.2f}->{base.preload_depth_for_target(d):.2f} mm"
              for d in base.D_TARGETS_MM
          ))
    print(f"  target record  : {base.TARGET_RECORD_S:.0f} s")
    print(f"  preload record : {base.PRELOAD_RECORD_S:.0f} s")
    print(f"  summary window : last {base.SUMMARY_WINDOW_S:.0f} s median")
    print(f"  rest/pair      : {base.INTER_TRIAL_REST_S:.0f} s")
    print(f"  planned pairs  : {expected_pair_count}")
    print(f"  est total      : ~{est_total_min:.1f} min")
    print()
    print("Pre-flight:")
    print("  [ ] Mark-10 start position about 6 mm above lower limit")
    print("  [ ] Clear visible gap above the sample at the start position")
    print("  [ ] Same sample / magnet / MLX geometry for the whole scan")
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
            mlx_ser, 1.0, "MLX warmup before opening motion hardware")
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
            force, "APMD same-d/different-F scan pre-flight")
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
    log.write(
        f"# D_TARGETS_MM={base.D_TARGETS_MM}, "
        f"D_PRELOAD_BY_TARGET_MM={base.D_PRELOAD_BY_TARGET_MM}\n"
    )
    log.write(
        f"# TARGET_RECORD_S={base.TARGET_RECORD_S}, "
        f"PRELOAD_RECORD_S={base.PRELOAD_RECORD_S}, "
        f"N_TRIALS={base.N_TRIALS}\n"
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
    summary_writer = csv.DictWriter(summary_file, fieldnames=_summary_fields())
    summary_writer.writeheader()

    try:
        for index, item in enumerate(scan_plan, start=1):
            trial = item["trial"]
            pair_id = item["pair_id"]
            target_d = item["target_d_mm"]
            preload_d = item["preload_d_mm"]
            label = base.target_label(target_d)

            print("\n" + "=" * 72)
            print(
                f"  SCAN POINT {index}/{expected_pair_count}: "
                f"d={target_d:.2f} mm, preload={preload_d:.2f} mm, "
                f"rep {trial}/{base.N_TRIALS}"
            )
            print("=" * 72)

            print("  Capturing pair-local B0 (no-contact baseline) ...")
            B0, n_b0 = _capture_b0(
                mlx_ser,
                f"B0 capture d={target_d:.2f} rep={trial}",
            )
            print(
                f"    B0 = ({B0[0]:+.2f}, {B0[1]:+.2f}, {B0[2]:+.2f}) "
                f"uT  (n={n_b0})"
            )
            log.write(
                f"[target {target_d:.2f} trial {trial}] B0={B0} n={n_b0}\n"
            )
            log.flush()

            contact_pos = base.find_contact(mark10, force, trial, log)
            if contact_pos is None:
                print(f"  ! contact not found, skipping d={target_d:.2f} rep {trial}")
                continue

            contact_depth = abs(contact_pos - trial_start_pos)
            planned_depth = contact_depth + preload_d
            print(
                f"  contact depth from start = {contact_depth:.2f} mm; "
                f"planned travel from start ~= {planned_depth:.2f} mm"
            )

            csv_path = session_dir / f"{STATE_FILE_PREFIX}_{label}_rep{trial}.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=_fieldnames())
                writer.writeheader()

                direct = base.collect_state(
                    mark10=mark10,
                    force=force,
                    mlx_ser=mlx_ser,
                    contact_pos=contact_pos,
                    B0=B0,
                    session_id=session_id,
                    trial=trial,
                    pair_id=pair_id,
                    target_d_mm=target_d,
                    preload_d_mm=preload_d,
                    state_label="direct_target",
                    path_mode="direct_loading",
                    phase="holding",
                    record_s=base.TARGET_RECORD_S,
                    csv_writer=writer,
                    log=log,
                )
                time.sleep(base.INTER_STATE_SETTLE_S)

                base.collect_state(
                    mark10=mark10,
                    force=force,
                    mlx_ser=mlx_ser,
                    contact_pos=contact_pos,
                    B0=B0,
                    session_id=session_id,
                    trial=trial,
                    pair_id=pair_id,
                    target_d_mm=preload_d,
                    preload_d_mm=preload_d,
                    state_label="preload_deep",
                    path_mode="preload_loading",
                    phase="preload",
                    record_s=base.PRELOAD_RECORD_S,
                    csv_writer=writer,
                    log=log,
                )
                time.sleep(base.INTER_STATE_SETTLE_S)

                returned = base.collect_state(
                    mark10=mark10,
                    force=force,
                    mlx_ser=mlx_ser,
                    contact_pos=contact_pos,
                    B0=B0,
                    session_id=session_id,
                    trial=trial,
                    pair_id=pair_id,
                    target_d_mm=target_d,
                    preload_d_mm=preload_d,
                    state_label="return_target",
                    path_mode="return_unloading",
                    phase="holding",
                    record_s=base.TARGET_RECORD_S,
                    csv_writer=writer,
                    log=log,
                )

            diag = base.pair_diagnostics(direct, returned)
            base.print_pair_diagnostics(diag)
            base.write_pair_summary(
                summary_writer,
                session_id,
                trial,
                pair_id,
                target_d,
                preload_d,
                direct,
                returned,
                diag,
            )
            summary_file.flush()
            pair_summary_count += 1
            if diag["verdict"] == "strong":
                strong_pair_count += 1
            if diag["same_d_ok"]:
                same_d_pair_count += 1
            summary_rows.append({
                "target_d_mm": target_d,
                "d_diff_mm": diag["d_diff_mm"],
                "delta_F_N": diag["delta_F_N"],
                "delta_Bvec_uT": diag["delta_Bvec_uT"],
                "same_d_ok": diag["same_d_ok"],
                "verdict": diag["verdict"],
            })

            log.write(
                f"[target {target_d:.2f} trial {trial}] diagnostic "
                f"dd={diag['d_diff_mm']:+.4f} "
                f"dF={diag['delta_F_N']:+.6f} "
                f"dBmag={diag['delta_Bmag_uT']:+.4f} "
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

            if index < expected_pair_count:
                print(f"\n  resting {base.INTER_TRIAL_REST_S:.0f} s for recovery ...")
                time.sleep(base.INTER_TRIAL_REST_S)

        run_status, registry_note = _scan_registry_status(
            pair_summary_count,
            expected_pair_count,
        )
        if run_status:
            registry_note = (
                f"strong={strong_pair_count}/{expected_pair_count}; "
                f"same_d={same_d_pair_count}/{expected_pair_count}"
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
            f"{pair_summary_count}/{expected_pair_count} scan pairs"
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

    _print_target_overview(summary_rows)

    print(f"\n=== {base.PROTOCOL_SHORT_NAME} done. Files in: {session_dir}")
    for p in sorted(session_dir.glob(CSV_PRINT_GLOB)):
        print(f"  {p.name}")
    print(f"  {log_path.name}")
    if base.NEXT_MESSAGE:
        print(f"\n{base.NEXT_MESSAGE}")


if __name__ == "__main__":
    main()
