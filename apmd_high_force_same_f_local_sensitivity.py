"""APMD Experiment 6.4A: high-force same-F local sensitivity supplement.

This wrapper reuses the stable same-F/different-d path-pair protocol and only
changes the force targets plus preload rule.  The purpose is to estimate the
local j_d direction in the high-force range actually visited by the Stage 5/6
local dense-loop data.

Recommended low-risk acquisition:

    python .\apmd_high_force_same_f_local_sensitivity.py 800
    python .\apmd_high_force_same_f_local_sensitivity.py 1000
    python .\apmd_high_force_same_f_local_sensitivity.py 1200

For a single longer session:

    python .\apmd_high_force_same_f_local_sensitivity.py
"""

from __future__ import annotations

import sys

import apmd_same_f_different_d_path_pair as base


F_TARGETS_HIGH_FORCE = [(800, 8.00), (1000, 10.00), (1200, 12.00)]
OPTIONAL_TARGETS = [(600, 6.00), (1400, 14.00)]
FIXED_PRELOAD_D_MM = 3.80

SINGLE_TARGETS = {
    str(label): (label, force_n)
    for label, force_n in F_TARGETS_HIGH_FORCE + OPTIONAL_TARGETS
}

TARGET_SELECTION = "ALL"


def selected_targets(selection):
    key = str(selection).upper()
    if key in ("ALL", "A"):
        return list(F_TARGETS_HIGH_FORCE)
    if key in SINGLE_TARGETS:
        return [SINGLE_TARGETS[key]]
    valid = ["ALL"] + sorted(SINGLE_TARGETS, key=int)
    raise ValueError(f"unknown target selection {selection!r}; use one of: {valid}")


def apply_target_selection(selection):
    global TARGET_SELECTION

    selected_targets(selection)
    TARGET_SELECTION = str(selection).upper()


def configure_base_protocol():
    targets = selected_targets(TARGET_SELECTION)
    if len(targets) == 1:
        label, force_n = targets[0]
        suffix = f"_{label}"
        title_suffix = f" single point {force_n:.2f} N"
        next_message = (
            "Next: inspect this high-force same-F local sensitivity session. "
            "If it passes gates, run the next force point."
        )
    else:
        suffix = ""
        title_suffix = " target set 8/10/12 N"
        next_message = (
            "Next: inspect the 8/10/12 N summaries, then rebuild Stage 4/6 "
            "local-ID features if all three force points are accepted."
        )

    base.PROTOCOL_TITLE = (
        "APMD -- high-force same-F local sensitivity supplement"
        f"({title_suffix})"
    )
    base.PROTOCOL_SHORT_NAME = (
        "APMD high-force same-F local sensitivity"
        f"{title_suffix}"
    )
    base.LOG_HEADER = "APMD high-force same-F local sensitivity session"
    base.FORMAL_EXPERIMENT_KEY = "\u5b9e\u9a8c 6.4A"

    base.N_TRIALS = 3
    base.F_TARGETS = targets

    base.D_PRELOAD_EXTRA_MM = 0.0
    base.D_PRELOAD_FIXED_MM = FIXED_PRELOAD_D_MM
    base.D_PRELOAD_MAX_MM = None
    base.F_PRELOAD_CAP_EXTRA_N = None
    base.F_PRELOAD_CAP_MAX_N = None

    base.D_SOFT_LIMIT_MM = None
    base.F_HARD_LIMIT_N = None

    base.TARGET_RECORD_S = 45.0
    base.PRELOAD_RECORD_S = 30.0
    base.SUMMARY_WINDOW_S = 10.0
    base.INTER_TRIAL_REST_S = 120.0

    base.FORCE_MATCH_TOL_N = 0.050
    base.MIN_D_SPLIT_MM = 0.10
    base.DYNAMIC_B_SIGNAL_UT = 100.0

    base.SUMMARY_FILENAME = (
        f"high_force_same_f_local_sensitivity{suffix}_pair_summary.csv"
    )
    base.CSV_PREFIX = "high_force_same_f_local_sensitivity"
    base.CSV_PRINT_GLOB = f"high_force_same_f_local_sensitivity{suffix}*.csv"
    base.FIGURE_FILENAME = f"high_force_same_f_local_sensitivity{suffix}.png"
    base.NEXT_MESSAGE = next_message


def parse_target_selection(argv):
    valid = "|".join(["ALL"] + sorted(SINGLE_TARGETS, key=int))
    if not argv:
        return "ALL"
    if len(argv) != 1:
        raise SystemExit(
            "Usage: python .\\apmd_high_force_same_f_local_sensitivity.py "
            f"[{valid}]"
        )
    key = argv[0].upper()
    if key != "ALL" and key not in SINGLE_TARGETS:
        raise SystemExit(
            "Usage: python .\\apmd_high_force_same_f_local_sensitivity.py "
            f"[{valid}]"
        )
    return key


def main(argv=None):
    selection = parse_target_selection(sys.argv[1:] if argv is None else argv)
    apply_target_selection(selection)
    configure_base_protocol()
    base.main()


if __name__ == "__main__":
    main()
