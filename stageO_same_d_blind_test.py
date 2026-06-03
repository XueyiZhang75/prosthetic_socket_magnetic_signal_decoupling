"""Stage O-mini v2b -- same-d / different-F held-out blind acquisition.

This script reuses the validated Stage I+ path protocol:

    direct loading to target d
    preload deeper
    unload back to the same target d

The difference is experimental role and output naming. These rows are written
as O/blind states, so they can be evaluated as held-out data instead of being
accidentally used as calibration.
"""

from __future__ import annotations

import stageI_plus_same_d_diff_f as iplus


HELDOUT_D_TARGETS_MM = [1.50]
HELDOUT_D_PRELOAD_BY_TARGET_MM = {
    1.50: 1.80,
}


def configure_protocol() -> None:
    iplus.PROTOCOL_TITLE = (
        "Stage O-mini v2b -- same-d / different-F held-out blind probe"
    )
    iplus.PROTOCOL_SHORT_NAME = "Stage O-mini v2b"
    iplus.STAGE_LABEL = "O_blind"
    iplus.LOG_HEADER = "Stage O-mini v2b same-d held-out session"
    iplus.SUMMARY_FILENAME = "O_blind_same_d_pair_summary.csv"
    iplus.STATE_FILE_PREFIX = "O_blind_same_d"
    iplus.CSV_PRINT_GLOB = "O_blind*.csv"
    iplus.PREFLIGHT_FIRST_LINE = (
        "This is a NEW same-d held-out O-mini blind pilot, not calibration"
    )
    iplus.NEXT_MESSAGE = ""

    iplus.N_TRIALS = 1
    iplus.D_TARGETS_MM = list(HELDOUT_D_TARGETS_MM)
    iplus.D_PRELOAD_BY_TARGET_MM = dict(HELDOUT_D_PRELOAD_BY_TARGET_MM)
    iplus.D_PRELOAD_MM = 1.80

    iplus.TARGET_RECORD_S = 20.0
    iplus.PRELOAD_RECORD_S = 10.0
    iplus.SUMMARY_WINDOW_S = 5.0


def main() -> None:
    configure_protocol()
    iplus.main()


if __name__ == "__main__":
    main()
