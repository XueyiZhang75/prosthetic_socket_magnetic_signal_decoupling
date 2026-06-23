"""APMD Experiment 3.4B: same-F path-dose preload holding-time scan.

This script reuses the stable same-F / different-d path-pair logic from
Experiment 3.4A. The only change is the experimental matrix:

    fixed target F = 3.75 N
    fixed preload extra depth = +0.40 mm
    preload hold = 5, 30, or 90 s
    3 usable path-pairs per preload holding time

Run one hold-time group at a time:

    python .\apmd_same_f_path_hold_time.py 005
    python .\apmd_same_f_path_hold_time.py 030
    python .\apmd_same_f_path_hold_time.py 090

Full-matrix mode is also available:

    python .\apmd_same_f_path_hold_time.py B

Each path-pair follows:

    no-contact B0
    contact search
    loading path to target F
    deeper preload by +0.40 mm
    hold preload for selected time
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
import apmd_same_f_path_dosage as dose_helpers


TARGET_F_LABEL = 375
TARGET_F_N = 3.75
PRELOAD_EXTRA_MM = 0.40
PRELOAD_HOLD_TIMES_S = [5.0, 30.0, 90.0]
TRIALS_PER_HOLD_TIME = 3

SUMMARY_FILENAME = "same_f_path_hold_time_B_pair_summary.csv"
STATE_FILE_PREFIX = "same_f_path_hold_time_B"
FIGURE_FILENAME = "same_f_path_hold_time_B.png"
CSV_PRINT_GLOB = f"{STATE_FILE_PREFIX}*.csv"


def hold_time_label(hold_s: float) -> str:
    return f"{int(round(hold_s)):03d}"


def output_suffix(selected_hold_times: list[float]) -> str:
    if len(selected_hold_times) == 1:
        return f"_hold{hold_time_label(selected_hold_times[0])}"
    return ""


def make_summary_filename(selected_hold_times: list[float]) -> str:
    return f"{STATE_FILE_PREFIX}{output_suffix(selected_hold_times)}_pair_summary.csv"


def make_csv_prefix(selected_hold_times: list[float]) -> str:
    return f"{STATE_FILE_PREFIX}{output_suffix(selected_hold_times)}"


def parse_hold_selection(argv: list[str]) -> list[float]:
    usage = (
        "Usage: python .\\apmd_same_f_path_hold_time.py 005|030|090|B|ALL\n"
        "       one numeric run = one preload-hold group = 3 planned pairs"
    )
    if len(argv) == 0:
        return list(PRELOAD_HOLD_TIMES_S)
    if len(argv) != 1:
        raise SystemExit(usage)
    token = argv[0].strip().upper().replace("S", "")
    aliases = {
        "B": list(PRELOAD_HOLD_TIMES_S),
        "ALL": list(PRELOAD_HOLD_TIMES_S),
        "005": [5.0],
        "05": [5.0],
        "5": [5.0],
        "030": [30.0],
        "30": [30.0],
        "090": [90.0],
        "90": [90.0],
    }
    if token not in aliases:
        raise SystemExit(usage)
    return aliases[token]


def configure_base_protocol(selected_hold_times: list[float] | None = None) -> None:
    if selected_hold_times is None:
        selected_hold_times = PRELOAD_HOLD_TIMES_S
    csv_prefix = make_csv_prefix(selected_hold_times)
    summary_filename = make_summary_filename(selected_hold_times)

    base.PROTOCOL_TITLE = (
        "APMD Experiment 3.4B -- same-F path-dose preload holding-time scan"
    )
    base.PROTOCOL_SHORT_NAME = "APMD same-F path-dose 3.4B"
    base.LOG_HEADER = "APMD same-F path-dose 3.4B session"

    base.N_TRIALS = TRIALS_PER_HOLD_TIME
    base.F_TARGETS = [(TARGET_F_LABEL, TARGET_F_N)]
    base.D_PRELOAD_EXTRA_MM = PRELOAD_EXTRA_MM

    # Experiment 3.4B controls preload by the same displacement dose chosen
    # in 3.4A, then varies only how long that preload state is held.
    base.D_PRELOAD_MAX_MM = None
    base.F_PRELOAD_CAP_EXTRA_N = None
    base.F_PRELOAD_CAP_MAX_N = None
    base.D_SOFT_LIMIT_MM = None
    base.F_HARD_LIMIT_N = None

    base.TARGET_RECORD_S = 45.0
    base.PRELOAD_RECORD_S = (
        selected_hold_times[0] if len(selected_hold_times) == 1 else 30.0
    )
    base.SUMMARY_WINDOW_S = 10.0
    base.SUMMARY_WINDOW_MODE = "tail"
    base.INTER_TRIAL_REST_S = 120.0

    base.SUMMARY_FILENAME = summary_filename
    base.CSV_PREFIX = csv_prefix
    base.CSV_PRINT_GLOB = f"{csv_prefix}*.csv"
    base.FIGURE_FILENAME = FIGURE_FILENAME
    if len(selected_hold_times) == 1:
        base.FORMAL_EXPERIMENT_KEY = (
            f"\u5b9e\u9a8c 3.4B-{hold_time_label(selected_hold_times[0])}"
        )
    else:
        base.FORMAL_EXPERIMENT_KEY = "\u5b9e\u9a8c 3.4B"

    if selected_hold_times == [5.0]:
        base.NEXT_MESSAGE = "Next: run 30 s group with python .\\apmd_same_f_path_hold_time.py 030."
    elif selected_hold_times == [30.0]:
        base.NEXT_MESSAGE = "Next: run 90 s group with python .\\apmd_same_f_path_hold_time.py 090."
    else:
        base.NEXT_MESSAGE = (
            "Next: plot 3.4B preload hold-time response, then move to 3.5 "
            "recovery-time scan."
        )


def iter_hold_time_plan(selected_hold_times: list[float]):
    for condition_id, hold_s in enumerate(selected_hold_times, start=1):
        for trial in range(1, TRIALS_PER_HOLD_TIME + 1):
            yield {
                "condition_id": condition_id,
                "trial": trial,
                "pair_id": condition_id,
                "target_F_label": TARGET_F_LABEL,
                "target_F_N": TARGET_F_N,
                "preload_extra_mm": PRELOAD_EXTRA_MM,
                "preload_hold_s": hold_s,
                "condition_label": f"hold_{hold_time_label(hold_s)}s",
            }


def summary_fields():
    fields = list(dose_helpers.summary_fields())
    insert_at = fields.index("d_preload_extra_mm") + 1
    fields.insert(insert_at, "preload_hold_s")
    return fields


def write_hold_summary(
    writer,
    session_id,
    trial,
    pair_id,
    target_F,
    preload_hold_s,
    loading,
    unloading,
    diag,
):
    writer.writerow(
        {
            "session_id": session_id,
            **base.metadata_values(),
            "trial": trial,
            "pair_id": pair_id,
            "target_label": TARGET_F_LABEL,
            "F_target_N": f"{target_F:.5f}",
            "F_match_target_N": f"{loading.get('F_match_target_N', loading['F_N']):.6f}",
            "d_preload_mm": f"{loading.get('d_preload_mm', float('nan')):.4f}",
            "d_preload_extra_mm": f"{PRELOAD_EXTRA_MM:.4f}",
            "preload_hold_s": f"{preload_hold_s:.1f}",
            "F_loading_N": f"{loading['F_N']:.6f}",
            "F_unloading_N": f"{unloading['F_N']:.6f}",
            "delta_F_N": f"{diag['delta_F_N']:+.6f}",
            "d_loading_mm": f"{loading['d_mm']:.4f}",
            "d_unloading_mm": f"{unloading['d_mm']:.4f}",
            "delta_d_mm": f"{diag['delta_d_mm']:+.4f}",
            "Bmag_loading_uT": f"{loading['Bmag_uT']:.4f}",
            "Bmag_unloading_uT": f"{unloading['Bmag_uT']:.4f}",
            "delta_Bmag_uT": f"{diag['delta_Bmag_uT']:+.4f}",
            "delta_Bx_uT": f"{diag['delta_Bx_uT']:+.4f}",
            "delta_By_uT": f"{diag['delta_By_uT']:+.4f}",
            "delta_Bz_uT": f"{diag['delta_Bz_uT']:+.4f}",
            "delta_Bvec_uT": f"{diag['delta_Bvec_uT']:.4f}",
            "slope_Bmag_uT_per_mm": f"{diag['slope_Bmag_uT_per_mm']:.4f}",
            "same_F_ok": int(diag["same_F_ok"]),
            "disp_split_ok": int(diag["disp_split_ok"]),
            "b_signal_ok": int(diag["b_signal_ok"]),
            "verdict": diag["verdict"],
        }
    )


def print_hold_time_overview(rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    print("\nPreload holding-time overview:")
    for hold_s in sorted({r["preload_hold_s"] for r in rows}):
        subset = [r for r in rows if abs(r["preload_hold_s"] - hold_s) < 1e-9]
        if not subset:
            continue
        same_f = sum(1 for r in subset if r["same_F_ok"])
        strong = sum(1 for r in subset if r["verdict"] == "strong")
        med_dF = base.median_or_nan([abs(r["delta_F_N"]) for r in subset])
        med_dd = base.median_or_nan([abs(r["delta_d_mm"]) for r in subset])
        med_dB = base.median_or_nan([r["delta_Bvec_uT"] for r in subset])
        ratio = med_dB / med_dd if med_dd > 1e-9 else float("nan")
        print(
            f"  hold={hold_s:.0f} s: "
            f"same-F {same_f}/{TRIALS_PER_HOLD_TIME}, "
            f"strong {strong}/{TRIALS_PER_HOLD_TIME}, "
            f"median |dF|={med_dF * 1000:.1f} mN, "
            f"median |dd|={med_dd:.3f} mm, "
            f"median dBvec={med_dB:.1f} uT, "
            f"dBvec/|dd|={ratio:.1f} uT/mm"
        )


def main() -> None:
    selected_hold_times = parse_hold_selection(sys.argv[1:])
    configure_base_protocol(selected_hold_times)
    base.OUTPUT_ROOT.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"session_{ts}"
    session_dir = base.OUTPUT_ROOT / session_id
    session_dir.mkdir(parents=True)
    log_path = session_dir / "run_log.txt"
    summary_path = session_dir / base.SUMMARY_FILENAME

    hold_plan = list(iter_hold_time_plan(selected_hold_times))
    expected_pair_count = len(hold_plan)
    pair_summary_count = 0
    strong_pair_count = 0
    same_f_pair_count = 0
    summary_rows: list[dict[str, object]] = []
    run_status = ""
    registry_note = ""

    est_total_min = (
        sum(
            2 * base.TARGET_RECORD_S
            + item["preload_hold_s"]
            + 3 * base.PRE_RECORD_SETTLE_S
            + base.INTER_TRIAL_REST_S
            + 1.5
            for item in hold_plan
        )
        / 60
    )

    print("\n" + "=" * 72)
    print(f"  {base.PROTOCOL_TITLE}")
    print("=" * 72)
    print(f"  session        : {session_id}")
    print(f"  target F       : {TARGET_F_N:.2f} N")
    print(f"  preload extra  : +{PRELOAD_EXTRA_MM:.2f} mm")
    print("  preload hold  : " + ", ".join(f"{v:.0f} s" for v in selected_hold_times))
    print(f"  trials/hold    : {TRIALS_PER_HOLD_TIME}")
    print(f"  target record  : {base.TARGET_RECORD_S:.0f} s")
    print(f"  summary window : last {base.SUMMARY_WINDOW_S:.0f} s median")
    print(f"  rest/pair      : {base.INTER_TRIAL_REST_S:.0f} s")
    print(f"  planned pairs  : {expected_pair_count}")
    print("  D_SOFT_LIMIT   : OFF")
    print("  F_HARD_LIMIT   : OFF")
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
            force, "APMD same-F path-dose 3.4B pre-flight"
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
    log.write(
        f"# TARGET_F_N={TARGET_F_N}, PRELOAD_EXTRA_MM={PRELOAD_EXTRA_MM}, "
        f"PRELOAD_HOLD_TIMES_S={selected_hold_times}, "
        f"TARGET_RECORD_S={base.TARGET_RECORD_S}, "
        f"TRIALS_PER_HOLD_TIME={TRIALS_PER_HOLD_TIME}\n"
    )
    log.write(
        f"# D_SOFT_LIMIT_MM={base.D_SOFT_LIMIT_MM}, "
        f"F_HARD_LIMIT_N={base.F_HARD_LIMIT_N}\n"
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
    summary_writer = csv.DictWriter(summary_file, fieldnames=summary_fields())
    summary_writer.writeheader()

    try:
        for index, item in enumerate(hold_plan, start=1):
            trial = item["trial"]
            pair_id = item["pair_id"]
            target_F = item["target_F_N"]
            target_label = item["target_F_label"]
            preload_hold_s = item["preload_hold_s"]
            hold_label = int(round(preload_hold_s))
            base.PRELOAD_RECORD_S = preload_hold_s

            print("\n" + "=" * 72)
            print(
                f"  HOLD-TIME POINT {index}/{expected_pair_count}: "
                f"F={target_F:.2f} N, preload extra=+{PRELOAD_EXTRA_MM:.2f} mm, "
                f"hold={preload_hold_s:.0f} s, "
                f"rep {trial}/{TRIALS_PER_HOLD_TIME}"
            )
            print("=" * 72)

            print(f"\n  PHASE R: retracting to start ({trial_start_pos:+.3f} mm)")
            try:
                base.reset_to_trial_start_if_needed(mark10, trial_start_pos)
            except base.Mark10Error as exc:
                print(f"  ! retract error before hold-time point: {exc}")
                continue
            time.sleep(base.INTER_PAIR_SETTLE_S)

            print("  Capturing pair-local B0 (no-contact baseline) ...")
            try:
                B0, _, n_b0 = base.require_mlx_sample(
                    mlx_ser,
                    1.5,
                    f"B0 capture hold={preload_hold_s:.0f}s rep={trial}",
                )
            except base.MlxNoDataError as exc:
                print(f"  ! B0 capture failed: {exc}")
                continue
            print(
                f"    B0 = ({B0[0]:+.2f}, {B0[1]:+.2f}, {B0[2]:+.2f}) "
                f"uT  (n={n_b0})"
            )
            log.write(
                f"[hold {preload_hold_s:.0f}s trial {trial}] B0={B0} n={n_b0}\n"
            )
            log.flush()

            contact_pos = base.find_contact(
                mark10, force, f"{trial} hold {hold_label:03d}", log
            )
            if contact_pos is None:
                print(
                    f"  ! contact not found, skipping hold={preload_hold_s:.0f}s rep {trial}"
                )
                continue

            contact_depth = abs(contact_pos - trial_start_pos)
            print(
                f"  contact depth from start = {contact_depth:.2f} mm; "
                "max planned travel from start = not software-capped"
            )

            csv_path = (
                session_dir
                / f"{base.CSV_PREFIX}_{target_label}_hold{hold_label:03d}_rep{trial}.csv"
            )
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=dose_helpers.fieldnames())
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
                print(f"  ! hold-time pair incomplete: {status}")
                log.write(
                    f"[hold {preload_hold_s:.0f}s trial {trial}] "
                    f"incomplete status={status}\n"
                )
                log.flush()
            else:
                diag = base.pair_diagnostics(loading, unloading)
                base.print_pair_diagnostics(diag)
                write_hold_summary(
                    summary_writer,
                    session_id,
                    trial,
                    pair_id,
                    target_F,
                    preload_hold_s,
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
                        "preload_hold_s": preload_hold_s,
                        "delta_F_N": diag["delta_F_N"],
                        "delta_d_mm": diag["delta_d_mm"],
                        "delta_Bvec_uT": diag["delta_Bvec_uT"],
                        "same_F_ok": diag["same_F_ok"],
                        "verdict": diag["verdict"],
                    }
                )
                log.write(
                    f"[hold {preload_hold_s:.0f}s trial {trial}] diagnostic "
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
                f"3.4B preload holding-time dose complete; "
                f"strong={strong_pair_count}/{expected_pair_count}; "
                f"same_F={same_f_pair_count}/{expected_pair_count}"
            )
        else:
            registry_note = (
                f"not registered: {pair_summary_count}/{expected_pair_count} "
                "planned hold-time pairs completed"
            )
            print(f"\n  formal registry skipped: {registry_note}")
            log.write(f"# formal registry skipped: {registry_note}\n")
            log.flush()

    except KeyboardInterrupt:
        print("\n\nUser abort. Will retract.")
        run_status = ""
        registry_note = (
            f"not registered: user abort after "
            f"{pair_summary_count}/{expected_pair_count} hold-time pairs"
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

    print_hold_time_overview(summary_rows)

    print(f"\n=== {base.PROTOCOL_SHORT_NAME} done. Files in: {session_dir}")
    for p in sorted(session_dir.glob(base.CSV_PRINT_GLOB)):
        print(f"  {p.name}")
    print(f"  {summary_path.name}")
    print(f"  {log_path.name}")
    if base.NEXT_MESSAGE:
        print(f"\n{base.NEXT_MESSAGE}")


if __name__ == "__main__":
    main()
