"""Diagnostic same-d / different-F acquisition using the old timing settings.

This is a probe, not a formal APMD registration run. It reuses the current
same-d/different-F acquisition logic while restoring the timing used by the
strong 2026-06-02 path-pair session:

    target record  = 30 s
    preload record = 15 s
    summary window = 8 s
    trial rest     = 60 s

Use this to test whether the weaker 2026-06-08 magnetic split is caused by
the newer longer timing, without changing the formal protocol script.
"""

import apmd_same_d_different_f_path_pair as base


def _diagnostic_registry_status_for_pairs(
    pair_summary_count, usable_pair_count, expected_pair_count
):
    return "", "not registered: old-timing diagnostic probe"


def configure_protocol():
    base.PROTOCOL_TITLE = (
        "APMD diagnostic -- same-d/different-F old-timing path-pair probe"
    )
    base.PROTOCOL_SHORT_NAME = "APMD same-d/different-F old-timing diagnostic"
    base.STAGE_LABEL = "same_d_diff_f_old_timing_probe"
    base.LOG_HEADER = "APMD same-d/different-F old-timing diagnostic session"

    base.TARGET_RECORD_S = 30.0
    base.PRELOAD_RECORD_S = 15.0
    base.SUMMARY_WINDOW_S = 8.0
    base.INTER_TRIAL_REST_S = 60.0

    base.SUMMARY_FILENAME = "same_d_different_f_old_timing_pair_summary.csv"
    base.STATE_FILE_PREFIX = "same_d_different_f_old_timing"
    base.CSV_PRINT_GLOB = "same_d_different_f_old_timing*.csv"
    base.FIGURE_FILENAME = "same_d_different_f_old_timing_path_pair.png"
    base.NEXT_MESSAGE = "Next: inspect the old-timing diagnostic summary."
    base.registry_status_for_pairs = _diagnostic_registry_status_for_pairs


def main():
    configure_protocol()
    base.main()


if __name__ == "__main__":
    main()
