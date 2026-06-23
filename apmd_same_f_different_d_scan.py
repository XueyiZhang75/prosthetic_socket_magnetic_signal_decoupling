"""APMD Experiment 3.2: same-F / different-d coarse force-zone scan.

This wrapper keeps the stable Experiment 2.4 same-F path-pair motion logic and
only changes the force-target matrix and output names for the formal 3.2 scan.
Use:

    python .\apmd_same_f_different_d_scan.py A
    python .\apmd_same_f_different_d_scan.py B
    python .\apmd_same_f_different_d_scan.py C

For lower-risk incremental acquisition, run one force point per session:

    python .\apmd_same_f_different_d_scan.py 150
    python .\apmd_same_f_different_d_scan.py 180

For Block L local same-F sensitivity calibration, run one force point per
session with fixed preload d = 3.20 mm:

    python .\apmd_same_f_different_d_scan.py L300
    python .\apmd_same_f_different_d_scan.py L450
"""

from __future__ import annotations

import sys

import apmd_same_f_different_d_path_pair as base


SCAN_BLOCKS = {
    "A": {
        "targets": [(150, 1.50), (180, 1.80), (250, 2.50)],
        "experiment_key": "实验 3.2A",
        "title": (
            "APMD Experiment 3.2A -- same-F/different-d low-mid force scan"
        ),
        "short_name": "APMD same-F/different-d scan 3.2A",
        "summary_filename": "same_f_different_d_scan_A_pair_summary.csv",
        "csv_prefix": "same_f_different_d_scan_A",
        "figure_filename": "same_f_different_d_scan_A.png",
        "next_message": (
            "Next: run Experiment 3.2B with: "
            "python .\\apmd_same_f_different_d_scan.py B"
        ),
    },
    "B": {
        "targets": [(320, 3.20), (375, 3.75), (430, 4.30)],
        "experiment_key": "实验 3.2B",
        "title": (
            "APMD Experiment 3.2B -- same-F/different-d mid-force scan"
        ),
        "short_name": "APMD same-F/different-d scan 3.2B",
        "summary_filename": "same_f_different_d_scan_B_pair_summary.csv",
        "csv_prefix": "same_f_different_d_scan_B",
        "figure_filename": "same_f_different_d_scan_B.png",
        "next_message": (
            "Next: run Experiment 3.2C with: "
            "python .\\apmd_same_f_different_d_scan.py C"
        ),
    },
    "C": {
        "targets": [(490, 4.90), (550, 5.50)],
        "experiment_key": "实验 3.2C",
        "title": (
            "APMD Experiment 3.2C -- same-F/different-d high-force work-zone scan"
        ),
        "short_name": "APMD same-F/different-d scan 3.2C",
        "summary_filename": "same_f_different_d_scan_C_pair_summary.csv",
        "csv_prefix": "same_f_different_d_scan_C",
        "figure_filename": "same_f_different_d_scan_C.png",
        "next_message": (
            "Next: inspect 3.2A/3.2B/3.2C summaries, then choose the "
            "same-F work zone for dosage testing."
        ),
    },
}

SINGLE_TARGETS = {
    "150": (150, 1.50),
    "180": (180, 1.80),
    "250": (250, 2.50),
    "320": (320, 3.20),
    "375": (375, 3.75),
    "430": (430, 4.30),
    "490": (490, 4.90),
    "550": (550, 5.50),
}

BLOCK_L_SINGLE_TARGETS = {
    "L300": (300, 3.00),
    "L450": (450, 4.50),
    "L600": (600, 6.00),
    "L750": (750, 7.50),
    "L900": (900, 9.00),
}

SCAN_BLOCK = "A"


def single_target_spec(target_key):
    label, force_n = SINGLE_TARGETS[target_key]
    return {
        "targets": [(label, force_n)],
        "experiment_key": f"\u5b9e\u9a8c 3.2-{label}",
        "title": (
            "APMD Experiment 3.2 -- same-F/different-d single force point "
            f"({force_n:.2f} N)"
        ),
        "short_name": (
            "APMD same-F/different-d single force point "
            f"{force_n:.2f} N"
        ),
        "summary_filename": f"same_f_different_d_scan_{label}_pair_summary.csv",
        "csv_prefix": "same_f_different_d_scan",
        "csv_print_glob": f"same_f_different_d_scan_{label}*.csv",
        "figure_filename": f"same_f_different_d_scan_{label}.png",
        "next_message": (
            "Next: inspect this single-point session. If it passes gates, "
            "run the next force point; if not, repeat only this force point."
        ),
    }


def block_l_single_target_spec(target_key):
    label, force_n = BLOCK_L_SINGLE_TARGETS[target_key]
    return {
        "targets": [(label, force_n)],
        "experiment_key": f"Block L same-F local sensitivity F={force_n:.2f} N",
        "title": (
            "APMD Block L -- same-F/different-d local sensitivity "
            f"({force_n:.2f} N, fixed preload d=3.20 mm)"
        ),
        "short_name": (
            "APMD Block L same-F local sensitivity "
            f"{force_n:.2f} N"
        ),
        "summary_filename": f"block_L_same_f_local_sensitivity_{label}_pair_summary.csv",
        "csv_prefix": "block_L_same_f_local_sensitivity",
        "csv_print_glob": f"block_L_same_f_local_sensitivity_{label}*.csv",
        "figure_filename": f"block_L_same_f_local_sensitivity_{label}.png",
        "preload_extra_mm": 0.0,
        "preload_fixed_mm": 3.20,
        "next_message": (
            "Next: inspect this Block L same-F sensitivity point. If it passes "
            "same-F, displacement-split, and magnetic-split gates, run the next "
            "Block L force point; otherwise repeat only this force point."
        ),
    }


def valid_selections():
    numeric_targets = sorted(SINGLE_TARGETS, key=int)
    return sorted(SCAN_BLOCKS) + numeric_targets + sorted(BLOCK_L_SINGLE_TARGETS)


def scan_spec(selection):
    key = str(selection).upper()
    if key in SCAN_BLOCKS:
        return SCAN_BLOCKS[key]
    if key in SINGLE_TARGETS:
        return single_target_spec(key)
    if key in BLOCK_L_SINGLE_TARGETS:
        return block_l_single_target_spec(key)
    valid = ", ".join(valid_selections())
    raise ValueError(f"unknown scan selection {selection!r}; use one of: {valid}")


def apply_scan_block(block_name):
    global SCAN_BLOCK

    key = str(block_name).upper()
    scan_spec(key)
    SCAN_BLOCK = key


def configure_base_protocol():
    spec = scan_spec(SCAN_BLOCK)

    base.PROTOCOL_TITLE = spec["title"]
    base.PROTOCOL_SHORT_NAME = spec["short_name"]
    base.LOG_HEADER = f"{spec['short_name']} session"
    base.FORMAL_EXPERIMENT_KEY = spec["experiment_key"]

    base.N_TRIALS = 3
    base.F_TARGETS = list(spec["targets"])
    base.D_PRELOAD_EXTRA_MM = spec.get("preload_extra_mm", 0.30)
    base.D_PRELOAD_FIXED_MM = spec.get("preload_fixed_mm", None)

    # Experiment 3.2 controls preload by displacement dose: loading d + 0.30 mm.
    # Force during preload is recorded as an outcome, not used as a stop condition.
    base.D_PRELOAD_MAX_MM = None
    base.F_PRELOAD_CAP_EXTRA_N = None
    base.F_PRELOAD_CAP_MAX_N = None

    base.D_SOFT_LIMIT_MM = None
    base.F_HARD_LIMIT_N = None

    base.TARGET_RECORD_S = 45.0
    base.PRELOAD_RECORD_S = 30.0
    base.SUMMARY_WINDOW_S = 10.0
    base.INTER_TRIAL_REST_S = 120.0

    base.SUMMARY_FILENAME = spec["summary_filename"]
    base.CSV_PREFIX = spec["csv_prefix"]
    base.CSV_PRINT_GLOB = spec.get("csv_print_glob", f"{spec['csv_prefix']}*.csv")
    base.FIGURE_FILENAME = spec["figure_filename"]
    base.NEXT_MESSAGE = spec["next_message"]


def parse_scan_block(argv):
    valid = "|".join(valid_selections())
    if not argv:
        return "A"
    if len(argv) != 1:
        raise SystemExit(
            f"Usage: python .\\apmd_same_f_different_d_scan.py [{valid}]"
        )
    block = argv[0].upper()
    if block not in SCAN_BLOCKS and block not in SINGLE_TARGETS and block not in BLOCK_L_SINGLE_TARGETS:
        raise SystemExit(
            f"Usage: python .\\apmd_same_f_different_d_scan.py [{valid}]"
        )
    return block


def main(argv=None):
    block = parse_scan_block(sys.argv[1:] if argv is None else argv)
    apply_scan_block(block)
    configure_base_protocol()
    base.main()


if __name__ == "__main__":
    main()
