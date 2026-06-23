"""Stage O-mini v2b -- same-d / different-F held-out blind acquisition.

This script reuses the validated APMD same-d / different-F path protocol:

    direct loading to target d
    preload deeper
    unload back to the same target d

The difference is experimental role and output naming. These rows are written
as O/blind states, so they can be evaluated as held-out data instead of being
accidentally used as calibration.
"""

from __future__ import annotations

import apmd_same_d_different_f_path_pair as same_d_path


HELDOUT_D_TARGETS_MM = [1.50]
HELDOUT_D_PRELOAD_BY_TARGET_MM = {
    1.50: 1.80,
}


def configure_protocol() -> None:
    same_d_path.PROTOCOL_TITLE = (
        "Stage O-mini v2b -- same-d / different-F held-out blind probe"
    )
    same_d_path.PROTOCOL_SHORT_NAME = "Stage O-mini v2b"
    same_d_path.STAGE_LABEL = "O_blind"
    same_d_path.LOG_HEADER = "Stage O-mini v2b same-d held-out session"
    same_d_path.SUMMARY_FILENAME = "O_blind_same_d_pair_summary.csv"
    same_d_path.STATE_FILE_PREFIX = "O_blind_same_d"
    same_d_path.CSV_PRINT_GLOB = "O_blind*.csv"
    same_d_path.PREFLIGHT_FIRST_LINE = (
        "This is a NEW same-d held-out O-mini blind pilot, not calibration"
    )
    same_d_path.NEXT_MESSAGE = ""

    same_d_path.N_TRIALS = 1
    same_d_path.D_TARGETS_MM = list(HELDOUT_D_TARGETS_MM)
    same_d_path.D_PRELOAD_BY_TARGET_MM = dict(HELDOUT_D_PRELOAD_BY_TARGET_MM)
    same_d_path.D_PRELOAD_MM = 1.80

    same_d_path.TARGET_RECORD_S = 20.0
    same_d_path.PRELOAD_RECORD_S = 10.0
    same_d_path.SUMMARY_WINDOW_S = 5.0


def main() -> None:
    configure_protocol()
    same_d_path.main()


if __name__ == "__main__":
    main()
