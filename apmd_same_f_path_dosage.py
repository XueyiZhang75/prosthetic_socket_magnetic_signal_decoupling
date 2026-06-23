"""APMD Experiment 3.4A: same-F path-dose preload-extra-depth scan.

This script reuses the stable same-F / different-d path-pair logic from
Experiment 3.2. The only change is the experimental matrix:

    fixed target F = 3.75 N
    preload extra depth = +0.20, +0.30, or +0.40 mm
    3 usable path-pairs per preload extra depth group

Run one preload-extra group at a time:

    python .\apmd_same_f_path_dosage.py 020
    python .\apmd_same_f_path_dosage.py 030
    python .\apmd_same_f_path_dosage.py 040

Each path-pair follows:

    no-contact B0
    contact search
    loading path to target F
    deeper preload by displacement dose
    unloading path back to matched F
    retract to no-contact start
    rest
"""

from __future__ import annotations

import csv
import sys
import time
from datetime import datetime

import apmd_same_f_different_d_path_pair as base


TARGET_F_LABEL = 375
TARGET_F_N = 3.75
PRELOAD_EXTRA_MM = [0.20, 0.30, 0.40]
TRIALS_PER_EXTRA = 3

SUMMARY_FILENAME = "same_f_path_dosage_A_pair_summary.csv"
STATE_FILE_PREFIX = "same_f_path_dosage_A"
FIGURE_FILENAME = "same_f_path_dosage_A.png"
CSV_PRINT_GLOB = f"{STATE_FILE_PREFIX}*.csv"


def preload_extra_label(extra_mm: float) -> str:
    return f"{int(round(extra_mm * 100)):03d}"


def output_suffix(selected_extras: list[float]) -> str:
    if len(selected_extras) == 1:
        return f"_extra{preload_extra_label(selected_extras[0])}"
    return ""


def make_summary_filename(selected_extras: list[float]) -> str:
    return f"{STATE_FILE_PREFIX}{output_suffix(selected_extras)}_pair_summary.csv"


def make_csv_prefix(selected_extras: list[float]) -> str:
    return f"{STATE_FILE_PREFIX}{output_suffix(selected_extras)}"


def parse_dose_selection(argv: list[str]) -> list[float]:
    usage = (
        "Usage: python .\\apmd_same_f_path_dosage.py 020|030|040\n"
        "       one run = one preload-extra group = 3 planned pairs"
    )
    if len(argv) != 1:
        raise SystemExit(usage)
    token = argv[0].strip().upper().replace("+", "")
    aliases = {
        "020": 0.20, "20": 0.20, "A20": 0.20, "A020": 0.20,
        "0.20": 0.20, ".20": 0.20,
        "030": 0.30, "30": 0.30, "A30": 0.30, "A030": 0.30,
        "0.30": 0.30, ".30": 0.30,
        "040": 0.40, "40": 0.40, "A40": 0.40, "A040": 0.40,
        "0.40": 0.40, ".40": 0.40,
    }
    if token not in aliases:
        raise SystemExit(usage)
    return [aliases[token]]


def configure_base_protocol(selected_extras: list[float] | None = None) -> None:
    if selected_extras is None:
        selected_extras = PRELOAD_EXTRA_MM
    csv_prefix = make_csv_prefix(selected_extras)
    summary_filename = make_summary_filename(selected_extras)

    base.PROTOCOL_TITLE = (
        "APMD Experiment 3.4A -- same-F path-dose preload-extra-depth scan"
    )
    base.PROTOCOL_SHORT_NAME = "APMD same-F path-dose 3.4A"
    base.LOG_HEADER = "APMD same-F path-dose 3.4A session"

    base.N_TRIALS = TRIALS_PER_EXTRA
    base.F_TARGETS = [(TARGET_F_LABEL, TARGET_F_N)]
    base.D_PRELOAD_EXTRA_MM = selected_extras[0]

    # Experiment 3.4A controls preload by displacement dose:
    # loading d + selected extra depth. Force during preload is an outcome.
    base.D_PRELOAD_MAX_MM = None
    base.F_PRELOAD_CAP_EXTRA_N = None
    base.F_PRELOAD_CAP_MAX_N = None
    base.D_SOFT_LIMIT_MM = None
    base.F_HARD_LIMIT_N = None

    base.TARGET_RECORD_S = 45.0
    base.PRELOAD_RECORD_S = 30.0
    base.SUMMARY_WINDOW_S = 10.0
    base.SUMMARY_WINDOW_MODE = "tail"
    base.INTER_TRIAL_REST_S = 120.0

    base.SUMMARY_FILENAME = summary_filename
    base.CSV_PREFIX = csv_prefix
    base.CSV_PRINT_GLOB = f"{csv_prefix}*.csv"
    base.FIGURE_FILENAME = FIGURE_FILENAME
    if len(selected_extras) == 1:
        base.FORMAL_EXPERIMENT_KEY = (
            f"\u5b9e\u9a8c 3.4A-{preload_extra_label(selected_extras[0])}"
        )
    else:
        base.FORMAL_EXPERIMENT_KEY = "\u5b9e\u9a8c 3.4A"
    if selected_extras == [0.20]:
        base.NEXT_MESSAGE = "Next: run +0.30 mm group with python .\\apmd_same_f_path_dosage.py 030."
    elif selected_extras == [0.30]:
        base.NEXT_MESSAGE = "Next: run +0.40 mm group with python .\\apmd_same_f_path_dosage.py 040."
    else:
        base.NEXT_MESSAGE = (
            "Next: inspect 3.4A preload-extra-depth response, then run 3.4B "
            "same-F hold-time scan."
        )


def iter_dose_plan(selected_extras: list[float]):
    for condition_id, extra_mm in enumerate(selected_extras, start=1):
        for trial in range(1, TRIALS_PER_EXTRA + 1):
            yield {
                "condition_id": condition_id,
                "trial": trial,
                "pair_id": condition_id,
                "target_F_label": TARGET_F_LABEL,
                "target_F_N": TARGET_F_N,
                "preload_extra_mm": extra_mm,
                "condition_label": f"extra_{int(round(extra_mm * 100)):03d}",
            }


def fieldnames():
    return [
        "time_s", "session_id", "trial", "repeat_id", "pair_id", "stage",
        "state_label", "phase", "control_mode", "path_mode", "target_label",
        "target", "actual", "F_target_N", "F_N", "F_error_N",
        "d_preload_mm", "d_actual_mm", "d_mm", "q_mm", "mark10_pos_mm",
        "t_rel_s", "Bx_uT", "By_uT", "Bz_uT",
        "mean_Bx_uT", "mean_By_uT", "mean_Bz_uT",
        "delta_Bx_uT", "delta_By_uT", "delta_Bz_uT", "Bmag_uT",
        *base.metadata_fieldnames(), "note",
    ]


def summary_fields():
    return [
        "session_id", *base.metadata_fieldnames(), "trial", "pair_id",
        "target_label", "F_target_N",
        "F_match_target_N", "d_preload_mm", "d_preload_extra_mm",
        "F_loading_N", "F_unloading_N", "delta_F_N", "d_loading_mm",
        "d_unloading_mm", "delta_d_mm",
        "Bmag_loading_uT", "Bmag_unloading_uT", "delta_Bmag_uT",
        "delta_Bx_uT", "delta_By_uT", "delta_Bz_uT", "delta_Bvec_uT",
        "slope_Bmag_uT_per_mm", "same_F_ok", "disp_split_ok",
        "b_signal_ok", "verdict",
    ]


def print_dose_overview(rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    print("\nPreload-extra dose overview:")
    for extra_mm in sorted({r["preload_extra_mm"] for r in rows}):
        subset = [r for r in rows if abs(r["preload_extra_mm"] - extra_mm) < 1e-9]
        if not subset:
            continue
        same_f = sum(1 for r in subset if r["same_F_ok"])
        strong = sum(1 for r in subset if r["verdict"] == "strong")
        med_dF = base.median_or_nan([abs(r["delta_F_N"]) for r in subset])
        med_dd = base.median_or_nan([abs(r["delta_d_mm"]) for r in subset])
        med_dB = base.median_or_nan([r["delta_Bvec_uT"] for r in subset])
        ratio = med_dB / med_dd if med_dd > 1e-9 else float("nan")
        print(
            f"  preload extra=+{extra_mm:.2f} mm: "
            f"same-F {same_f}/{TRIALS_PER_EXTRA}, "
            f"strong {strong}/{TRIALS_PER_EXTRA}, "
            f"median |dF|={med_dF * 1000:.1f} mN, "
            f"median |dd|={med_dd:.3f} mm, "
            f"median dBvec={med_dB:.1f} uT, "
            f"dBvec/|dd|={ratio:.1f} uT/mm"
        )


def main() -> None:
    selected_extras = parse_dose_selection(sys.argv[1:])
    configure_base_protocol(selected_extras)
    base.OUTPUT_ROOT.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"session_{ts}"
    session_dir = base.OUTPUT_ROOT / session_id
    session_dir.mkdir(parents=True)
    log_path = session_dir / "run_log.txt"
    summary_path = session_dir / base.SUMMARY_FILENAME

    dose_plan = list(iter_dose_plan(selected_extras))
    expected_pair_count = len(dose_plan)
    pair_summary_count = 0
    strong_pair_count = 0
    same_f_pair_count = 0
    summary_rows: list[dict[str, object]] = []
    run_status = ""
    registry_note = ""

    est_total_min = (
        expected_pair_count
        * (
            2 * base.TARGET_RECORD_S
            + base.PRELOAD_RECORD_S
            + 3 * base.PRE_RECORD_SETTLE_S
            + base.INTER_TRIAL_REST_S
            + 1.5
        )
        / 60
    )

    print("\n" + "=" * 72)
    print(f"  {base.PROTOCOL_TITLE}")
    print("=" * 72)
    print(f"  session        : {session_id}")
    print(f"  target F       : {TARGET_F_N:.2f} N")
    print("  preload extra  : " + ", ".join(f"+{v:.2f} mm" for v in selected_extras))
    print(f"  trials/extra   : {TRIALS_PER_EXTRA}")
    print(f"  target record  : {base.TARGET_RECORD_S:.0f} s")
    print(f"  preload record : {base.PRELOAD_RECORD_S:.0f} s")
    print(f"  summary window : last {base.SUMMARY_WINDOW_S:.0f} s median")
    print(f"  rest/pair      : {base.INTER_TRIAL_REST_S:.0f} s")
    print(f"  planned pairs  : {expected_pair_count}")
    print(f"  D_SOFT_LIMIT   : OFF")
    print(f"  F_HARD_LIMIT   : OFF")
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
        raise SystemExit(f"\nMLX90393 required for APMD same-F path-dose 3.4A. {exc}")

    print("Opening Mark-10 ...")
    try:
        mark10 = base.Mark10(
            base.MARK10_PORT,
            base.MARK10_BAUD,
            speed_mm_per_min=base.MARK10_SPEED_MM_PER_MIN,
        )
    except base.Mark10Error as exc:
        mlx_ser.close()
        raise SystemExit(f"\n{exc}")
    print("  Mark-10 ready")

    print("Opening UNO_force ...")
    try:
        force = base.ForceReader(base.find_force_port())
        force.live_tare(
            duration_s=base.LIVE_TARE_S,
            pre_settle_s=base.TARE_PRE_SETTLE_S,
        )
        base.assert_no_contact_live_tare(
            force, "APMD same-F path-dose 3.4A pre-flight"
        )
    except Exception as exc:
        mlx_ser.close()
        mark10.close()
        raise SystemExit(f"\nForce sensor required for APMD same-F path-dose 3.4A. {exc}")

    trial_start_pos = mark10.position_stable()
    print(f"  trial_start_pos = {trial_start_pos:+.3f} mm")

    log = log_path.open("w", encoding="utf-8")
    log.write(f"# {base.LOG_HEADER} {ts}\n")
    log.write(
        f"# TARGET_F_N={TARGET_F_N}, PRELOAD_EXTRA_MM={selected_extras}, "
        f"TARGET_RECORD_S={base.TARGET_RECORD_S}, "
        f"PRELOAD_RECORD_S={base.PRELOAD_RECORD_S}, "
        f"TRIALS_PER_EXTRA={TRIALS_PER_EXTRA}\n"
    )
    log.write(f"# D_SOFT_LIMIT_MM={base.D_SOFT_LIMIT_MM}, "
              f"F_HARD_LIMIT_N={base.F_HARD_LIMIT_N}\n")
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
    summary_writer = csv.DictWriter(summary_file, fieldnames=summary_fields())
    summary_writer.writeheader()

    try:
        for index, item in enumerate(dose_plan, start=1):
            trial = item["trial"]
            pair_id = item["pair_id"]
            target_F = item["target_F_N"]
            target_label = item["target_F_label"]
            preload_extra = item["preload_extra_mm"]
            extra_label = int(round(preload_extra * 100))
            base.D_PRELOAD_EXTRA_MM = preload_extra

            print("\n" + "=" * 72)
            print(
                f"  DOSE POINT {index}/{expected_pair_count}: "
                f"F={target_F:.2f} N, preload extra=+{preload_extra:.2f} mm, "
                f"rep {trial}/{TRIALS_PER_EXTRA}"
            )
            print("=" * 72)

            print(f"\n  PHASE R: retracting to start ({trial_start_pos:+.3f} mm)")
            try:
                base.reset_to_trial_start_if_needed(mark10, trial_start_pos)
            except base.Mark10Error as exc:
                print(f"  ! retract error before dose point: {exc}")
                continue
            time.sleep(base.INTER_PAIR_SETTLE_S)

            print("  Capturing pair-local B0 (no-contact baseline) ...")
            try:
                B0, _, n_b0 = base.require_mlx_sample(
                    mlx_ser,
                    1.5,
                    f"B0 capture extra={preload_extra:.2f} rep={trial}",
                )
            except base.MlxNoDataError as exc:
                print(f"  ! B0 capture failed: {exc}")
                continue
            print(
                f"    B0 = ({B0[0]:+.2f}, {B0[1]:+.2f}, {B0[2]:+.2f}) "
                f"uT  (n={n_b0})"
            )
            log.write(
                f"[extra {preload_extra:.2f} trial {trial}] B0={B0} n={n_b0}\n"
            )
            log.flush()

            contact_pos = base.find_contact(
                mark10, force, f"{trial} extra {extra_label:03d}", log
            )
            if contact_pos is None:
                print(
                    f"  ! contact not found, skipping extra=+{preload_extra:.2f} rep {trial}"
                )
                continue

            contact_depth = abs(contact_pos - trial_start_pos)
            print(
                f"  contact depth from start = {contact_depth:.2f} mm; "
                "max planned travel from start = not software-capped"
            )

            csv_path = (
                session_dir
                / f"{base.CSV_PREFIX}_{target_label}_rep{trial}.csv"
            )
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames())
                writer.writeheader()
                loading, unloading, status = base.run_pair(
                    mark10=mark10,
                    force=force,
                    mlx_ser=mlx_ser,
                    contact_pos=contact_pos,
                    B0=B0,
                    session_id=session_id,
                    trial=trial,
                    pair_id=pair_id,
                    target_F=target_F,
                    csv_writer=writer,
                    log=log,
                )

            if status != "ok":
                print(f"  ! dose pair incomplete: {status}")
                log.write(
                    f"[extra {preload_extra:.2f} trial {trial}] "
                    f"incomplete status={status}\n"
                )
                log.flush()
            else:
                diag = base.pair_diagnostics(loading, unloading)
                base.print_pair_diagnostics(diag)
                base.write_pair_summary(
                    summary_writer,
                    session_id,
                    trial,
                    pair_id,
                    target_F,
                    loading,
                    unloading,
                    diag,
                )
                summary_file.flush()
                pair_summary_count += 1
                if diag["verdict"] == "strong":
                    strong_pair_count += 1
                if diag["same_F_ok"]:
                    same_f_pair_count += 1
                summary_rows.append(
                    {
                        "preload_extra_mm": preload_extra,
                        "delta_F_N": diag["delta_F_N"],
                        "delta_d_mm": diag["delta_d_mm"],
                        "delta_Bvec_uT": diag["delta_Bvec_uT"],
                        "same_F_ok": diag["same_F_ok"],
                        "verdict": diag["verdict"],
                    }
                )
                log.write(
                    f"[extra {preload_extra:.2f} trial {trial}] diagnostic "
                    f"dF={diag['delta_F_N']:+.6f} "
                    f"dd={diag['delta_d_mm']:+.4f} "
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
                f"3.4A preload-extra-depth dose complete; "
                f"strong={strong_pair_count}/{expected_pair_count}; "
                f"same_F={same_f_pair_count}/{expected_pair_count}"
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
            base.reset_to_trial_start_if_needed(mark10, trial_start_pos)
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
    for p in sorted(session_dir.glob(base.CSV_PRINT_GLOB)):
        print(f"  {p.name}")
    print(f"  {summary_path.name}")
    print(f"  {log_path.name}")
    if base.NEXT_MESSAGE:
        print(f"\n{base.NEXT_MESSAGE}")


if __name__ == "__main__":
    main()
