"""APMD Stage 6.1: local held-out dense-loop validation acquisition.

This script reuses the stable Stage 5.1B displacement-control dense-loop
implementation, but shifts the target-displacement grid to interleaved
held-out points:

    training grid: 3.00, 3.10, 3.20, 3.30, 3.40, 3.50, 3.60 mm
    held-out grid: 3.05, 3.15, 3.25, 3.35, 3.45, 3.55 mm

The resulting session should be evaluated as held-out validation data and not
added to the Stage 5 training dataset before model testing.
"""

from __future__ import annotations

import sys

import apmd_local_minor_loop_dense_sampling as dense
import apmd_same_d_different_f_path_pair as base


D_GRID_MM = [3.05, 3.15, 3.25, 3.35, 3.45, 3.55]
PRELOAD_D_MM = 3.80
N_CYCLES = 3

STATE_RECORD_S = 15.0
PRELOAD_RECORD_S = 30.0
SUMMARY_WINDOW_S = 5.0
PRE_RECORD_SETTLE_S = 3.0
INTER_STATE_SETTLE_S = 1.0
INTER_CYCLE_REST_S = 120.0

SUMMARY_FILENAME = "local_heldout_dense_loop_6p1_state_summary.csv"
STATE_FILE_PREFIX = "local_heldout_dense_loop_6p1"
FIGURE_FILENAME = "local_heldout_dense_loop_6p1.png"
CSV_PRINT_GLOB = f"{STATE_FILE_PREFIX}*.csv"

WORK_ZONE_BLOCK = "M"

WORK_ZONE_CONFIGS = {
    "M": {
        "d_grid_mm": [3.05, 3.15, 3.25, 3.35, 3.45, 3.55],
        "preload_d_mm": 3.80,
        "summary_filename": "local_heldout_dense_loop_6p1_state_summary.csv",
        "state_file_prefix": "local_heldout_dense_loop_6p1",
        "figure_filename": "local_heldout_dense_loop_6p1.png",
        "stage_label": "local_heldout_dense_loop_6p1",
        "formal_experiment_key": "\u9a8c\u8bc1 6.1",
        "protocol_suffix": "Block M",
    },
    "L": {
        "d_grid_mm": [2.45, 2.55, 2.65, 2.75, 2.85, 2.95],
        "preload_d_mm": 3.20,
        "summary_filename": "local_heldout_dense_loop_6p1_L_state_summary.csv",
        "state_file_prefix": "local_heldout_dense_loop_6p1_L",
        "figure_filename": "local_heldout_dense_loop_6p1_L.png",
        "stage_label": "local_heldout_dense_loop_6p1_L",
        "formal_experiment_key": "\u9a8c\u8bc1 6.1-L",
        "protocol_suffix": "Block L",
    },
}


def parse_work_zone_arg(argv=None) -> str:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return "M"
    if len(args) != 1:
        raise SystemExit("Usage: python .\\apmd_stage6_local_heldout_dense_loop.py [M|L]")
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
        "APMD Stage 6.1 -- local held-out dense-loop validation "
        f"({cfg['protocol_suffix']})"
    )
    base.PROTOCOL_SHORT_NAME = f"APMD local held-out dense-loop 6.1 {WORK_ZONE_BLOCK}"
    base.STAGE_LABEL = cfg["stage_label"]
    base.LOG_HEADER = f"APMD Stage 6.1 {WORK_ZONE_BLOCK} local held-out dense-loop session"

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
        f"Stage 6.1-{WORK_ZONE_BLOCK}: local held-out dense-loop validation, not training data"
    )
    base.NEXT_MESSAGE = (
        "Next: run Stage 6 held-out model prediction before adding this "
        "session to any training dataset."
    )
    base.FORMAL_EXPERIMENT_KEY = cfg["formal_experiment_key"]


def configure_dense_module() -> None:
    dense.D_GRID_MM = list(D_GRID_MM)
    dense.PRELOAD_D_MM = PRELOAD_D_MM
    dense.N_CYCLES = N_CYCLES

    dense.STATE_RECORD_S = STATE_RECORD_S
    dense.PRELOAD_RECORD_S = PRELOAD_RECORD_S
    dense.SUMMARY_WINDOW_S = SUMMARY_WINDOW_S
    dense.PRE_RECORD_SETTLE_S = PRE_RECORD_SETTLE_S
    dense.INTER_STATE_SETTLE_S = INTER_STATE_SETTLE_S
    dense.INTER_CYCLE_REST_S = INTER_CYCLE_REST_S

    dense.SUMMARY_FILENAME = SUMMARY_FILENAME
    dense.STATE_FILE_PREFIX = STATE_FILE_PREFIX
    dense.FIGURE_FILENAME = FIGURE_FILENAME
    dense.CSV_PRINT_GLOB = CSV_PRINT_GLOB
    dense.configure_base_protocol = configure_base_protocol


def main(argv=None) -> None:
    apply_work_zone_config(parse_work_zone_arg(argv))
    configure_dense_module()
    dense.main(apply_cli_config=False)


if __name__ == "__main__":
    main()
