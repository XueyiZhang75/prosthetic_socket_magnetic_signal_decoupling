"""APMD Experiment 3.3A: same-d path-dose preload-depth scan.

This script reuses the stable same-d / different-F path-pair logic from
Experiment 2.2/3.1. The only change is the experimental matrix:

    fixed target d = 3.40 mm
    preload d = 3.60, 3.70, 3.80 mm
    3 usable path-pairs per preload depth

Each path-pair follows:

    no-contact B0
    contact search
    direct loading to target d
    deeper preload
    return unloading to the same target d
    retract to no-contact start
    rest
"""

from __future__ import annotations

import csv
import sys
import time
from datetime import datetime

import apmd_same_d_different_f_path_pair as base
import apmd_same_d_different_f_scan as scan_helpers


TARGET_D_MM = 3.40
PRELOAD_D_MM = [3.60, 3.70, 3.80]
TRIALS_PER_PRELOAD = 3

SUMMARY_FILENAME = "same_d_path_dosage_A_pair_summary.csv"
STATE_FILE_PREFIX = "same_d_path_dosage_A"
FIGURE_FILENAME = "same_d_path_dosage_A.png"
CSV_PRINT_GLOB = f"{STATE_FILE_PREFIX}*.csv"


def configure_base_protocol() -> None:
    base.PROTOCOL_TITLE = (
        "APMD Experiment 3.3A -- same-d path-dose preload-depth scan"
    )
    base.PROTOCOL_SHORT_NAME = "APMD same-d path-dose 3.3A"
    base.STAGE_LABEL = "same_d_path_dosage_A"
    base.LOG_HEADER = "APMD same-d path-dose 3.3A session"

    base.N_TRIALS = TRIALS_PER_PRELOAD
    base.D_TARGETS_MM = [TARGET_D_MM]
    base.D_PRELOAD_BY_TARGET_MM = {TARGET_D_MM: PRELOAD_D_MM[0]}
    base.D_PRELOAD_MM = PRELOAD_D_MM[0]

    base.TARGET_RECORD_S = 45.0
    base.PRELOAD_RECORD_S = 30.0
    base.SUMMARY_WINDOW_S = 10.0
    base.INTER_TRIAL_REST_S = 120.0
    base.F_HARD_LIMIT_N = None

    base.SUMMARY_FILENAME = SUMMARY_FILENAME
    base.STATE_FILE_PREFIX = STATE_FILE_PREFIX
    base.CSV_PRINT_GLOB = CSV_PRINT_GLOB
    base.FIGURE_FILENAME = FIGURE_FILENAME
    base.PREFLIGHT_FIRST_LINE = (
        "Experiment 3.3A: same target d, varied preload depth"
    )
    base.NEXT_MESSAGE = (
        "Next: plot 3.3A preload-depth response, then run 3.3B hold-time scan."
    )
    base.FORMAL_EXPERIMENT_KEY = "实验 3.3A"


def iter_dose_plan():
    for condition_id, preload_d in enumerate(PRELOAD_D_MM, start=1):
        for trial in range(1, TRIALS_PER_PRELOAD + 1):
            yield {
                "condition_id": condition_id,
                "trial": trial,
                "pair_id": condition_id,
                "target_d_mm": TARGET_D_MM,
                "preload_d_mm": preload_d,
                "preload_extra_mm": preload_d - TARGET_D_MM,
                "condition_label": f"preload_{int(round(preload_d * 100)):03d}",
            }


def print_dose_overview(rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    print("\nPreload-depth dose overview:")
    for preload_d in PRELOAD_D_MM:
        subset = [r for r in rows if abs(r["preload_d_mm"] - preload_d) < 1e-9]
        if not subset:
            continue
        same_d = sum(1 for r in subset if r["same_d_ok"])
        strong = sum(1 for r in subset if r["verdict"] == "strong")
        med_dd = scan_helpers._median([abs(r["d_diff_mm"]) for r in subset])
        med_dF = scan_helpers._median([abs(r["delta_F_N"]) for r in subset])
        med_dB = scan_helpers._median([r["delta_Bvec_uT"] for r in subset])
        ratio = med_dB / med_dF if med_dF > 1e-9 else float("nan")
        print(
            f"  preload={preload_d:.2f} mm (+{preload_d - TARGET_D_MM:.2f}): "
            f"same-d {same_d}/{TRIALS_PER_PRELOAD}, "
            f"strong {strong}/{TRIALS_PER_PRELOAD}, "
            f"median |dd|={med_dd:.3f} mm, "
            f"median |dF|={med_dF * 1000:.1f} mN, "
            f"median dBvec={med_dB:.1f} uT, "
            f"dBvec/|dF|={ratio:.1f} uT/N"
        )


def parse_block_arg() -> None:
    if len(sys.argv) <= 1:
        return
    if len(sys.argv) == 2 and sys.argv[1].upper() == "A":
        return
    raise SystemExit("Usage: python .\\apmd_same_d_path_dosage.py [A]")


def main() -> None:
    parse_block_arg()
    configure_base_protocol()
    base.OUTPUT_ROOT.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"session_{ts}"
    session_dir = base.OUTPUT_ROOT / session_id
    session_dir.mkdir(parents=True)
    log_path = session_dir / "run_log.txt"
    summary_path = session_dir / SUMMARY_FILENAME

    dose_plan = list(iter_dose_plan())
    expected_pair_count = len(dose_plan)
    pair_summary_count = 0
    strong_pair_count = 0
    same_d_pair_count = 0
    summary_rows: list[dict[str, object]] = []
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
    print(f"  target d       : {TARGET_D_MM:.2f} mm")
    print("  preload d      : " + ", ".join(f"{v:.2f} mm" for v in PRELOAD_D_MM))
    print(f"  trials/preload : {TRIALS_PER_PRELOAD}")
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
            force, "APMD same-d path-dose 3.3A pre-flight"
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
    log.write(f"# TARGET_D_MM={TARGET_D_MM}, PRELOAD_D_MM={PRELOAD_D_MM}\n")
    log.write(
        f"# TARGET_RECORD_S={base.TARGET_RECORD_S}, "
        f"PRELOAD_RECORD_S={base.PRELOAD_RECORD_S}, "
        f"TRIALS_PER_PRELOAD={TRIALS_PER_PRELOAD}\n"
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
    summary_writer = csv.DictWriter(
        summary_file, fieldnames=scan_helpers._summary_fields()
    )
    summary_writer.writeheader()

    try:
        for index, item in enumerate(dose_plan, start=1):
            trial = item["trial"]
            pair_id = item["pair_id"]
            target_d = item["target_d_mm"]
            preload_d = item["preload_d_mm"]
            condition_label = item["condition_label"]
            target_label = base.target_label(target_d)
            preload_label = int(round(preload_d * 100))

            print("\n" + "=" * 72)
            print(
                f"  DOSE POINT {index}/{expected_pair_count}: "
                f"d={target_d:.2f} mm, preload={preload_d:.2f} mm "
                f"(+{preload_d - target_d:.2f}), rep {trial}/{TRIALS_PER_PRELOAD}"
            )
            print("=" * 72)

            print("  Capturing pair-local B0 (no-contact baseline) ...")
            B0, n_b0 = scan_helpers._capture_b0(
                mlx_ser,
                f"B0 capture preload={preload_d:.2f} rep={trial}",
            )
            print(
                f"    B0 = ({B0[0]:+.2f}, {B0[1]:+.2f}, {B0[2]:+.2f}) "
                f"uT  (n={n_b0})"
            )
            log.write(
                f"[preload {preload_d:.2f} trial {trial}] B0={B0} n={n_b0}\n"
            )
            log.flush()

            contact_pos = base.find_contact(mark10, force, trial, log)
            if contact_pos is None:
                print(
                    f"  ! contact not found, skipping preload={preload_d:.2f} rep {trial}"
                )
                continue

            contact_depth = abs(contact_pos - trial_start_pos)
            planned_depth = contact_depth + preload_d
            print(
                f"  contact depth from start = {contact_depth:.2f} mm; "
                f"planned travel from start ~= {planned_depth:.2f} mm"
            )

            csv_path = (
                session_dir
                / f"{STATE_FILE_PREFIX}_{target_label}_pre{preload_label:03d}_rep{trial}.csv"
            )
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=scan_helpers._fieldnames())
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
            summary_rows.append(
                {
                    "condition_label": condition_label,
                    "target_d_mm": target_d,
                    "preload_d_mm": preload_d,
                    "d_diff_mm": diag["d_diff_mm"],
                    "delta_F_N": diag["delta_F_N"],
                    "delta_Bvec_uT": diag["delta_Bvec_uT"],
                    "same_d_ok": diag["same_d_ok"],
                    "verdict": diag["verdict"],
                }
            )

            log.write(
                f"[preload {preload_d:.2f} trial {trial}] diagnostic "
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

        if pair_summary_count == expected_pair_count:
            run_status = "formal"
            registry_note = (
                f"3.3A preload-depth dose complete; "
                f"strong={strong_pair_count}/{expected_pair_count}; "
                f"same_d={same_d_pair_count}/{expected_pair_count}"
            )
        else:
            registry_note = (
                f"not registered: {pair_summary_count}/{expected_pair_count} "
                "planned dose pairs completed"
            )
            print(f"\n  formal registry skipped: {registry_note}")
            log.write(f"# formal registry skipped: {registry_note}\n")
            log.flush()

    except KeyboardInterrupt:
        print("\n\nUser abort. Will retract.")
        run_status = ""
        registry_note = (
            f"not registered: user abort after "
            f"{pair_summary_count}/{expected_pair_count} dose pairs"
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

    print_dose_overview(summary_rows)

    print(f"\n=== {base.PROTOCOL_SHORT_NAME} done. Files in: {session_dir}")
    for p in sorted(session_dir.glob(CSV_PRINT_GLOB)):
        print(f"  {p.name}")
    print(f"  {summary_path.name}")
    print(f"  {log_path.name}")
    if base.NEXT_MESSAGE:
        print(f"\n{base.NEXT_MESSAGE}")


if __name__ == "__main__":
    main()
