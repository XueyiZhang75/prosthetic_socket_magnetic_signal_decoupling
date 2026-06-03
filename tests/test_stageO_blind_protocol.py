import fnmatch
import unittest

from blind_test_analysis import STATE_FILE_PATTERNS
from stageO_same_d_blind_test import (
    HELDOUT_D_PRELOAD_BY_TARGET_MM,
    HELDOUT_D_TARGETS_MM,
)
from stageO_blind_test import (
    BLIND_FORCE_TARGETS,
    blind_csv_name,
    blind_fieldnames,
    has_planned_preload_split,
    make_blind_state_specs,
    summarize_samples,
)


class StageOBlindProtocolTests(unittest.TestCase):
    def test_blind_csv_name_is_consumed_by_analysis_script(self):
        name = blind_csv_name(trial=2)

        self.assertEqual(name, "O_blind_states_rep2.csv")
        self.assertTrue(
            any(fnmatch.fnmatch(name, pattern) for pattern in STATE_FILE_PATTERNS)
        )

    def test_same_d_heldout_csv_name_is_consumed_by_analysis_script(self):
        name = "O_blind_same_d_150_rep1.csv"

        self.assertTrue(
            any(fnmatch.fnmatch(name, pattern) for pattern in STATE_FILE_PATTERNS)
        )

    def test_same_d_heldout_uses_interpolation_displacement(self):
        self.assertEqual(HELDOUT_D_TARGETS_MM, [1.50])
        self.assertAlmostEqual(HELDOUT_D_PRELOAD_BY_TARGET_MM[1.50], 1.80)

    def test_make_blind_state_specs_creates_nonmonotonic_two_path_points(self):
        specs = make_blind_state_specs([(205, 2.05), (175, 1.75)])

        self.assertEqual(len(specs), 4)
        self.assertEqual([s.state_index for s in specs], [1, 2, 3, 4])
        self.assertEqual(
            [s.state_label for s in specs],
            [
                "blind_01_loading",
                "blind_02_unloading",
                "blind_03_loading",
                "blind_04_unloading",
            ],
        )
        self.assertEqual([s.path_mode for s in specs], [
            "direct_loading",
            "return_unloading",
            "direct_loading",
            "return_unloading",
        ])
        self.assertEqual([s.pair_id for s in specs], [1, 1, 2, 2])

    def test_default_targets_stay_inside_observed_useful_window(self):
        target_forces = [target for _, target in BLIND_FORCE_TARGETS]

        self.assertEqual(target_forces, [1.75, 1.85])
        self.assertLessEqual(max(target_forces), 1.90)
        self.assertGreaterEqual(min(target_forces), 1.70)

    def test_has_planned_preload_split_rejects_states_near_preload_cap(self):
        self.assertTrue(has_planned_preload_split(1.70))
        self.assertFalse(has_planned_preload_split(1.89))

    def test_fieldnames_include_blind_analysis_contract(self):
        names = set(blind_fieldnames())

        required = {
            "time_s",
            "session_id",
            "trial",
            "repeat_id",
            "pair_id",
            "stage",
            "state_label",
            "phase",
            "control_mode",
            "target",
            "actual",
            "F_target_N",
            "F_N",
            "d_actual_mm",
            "d_mm",
            "t_rel_s",
            "delta_Bx_uT",
            "delta_By_uT",
            "delta_Bz_uT",
            "Bmag_uT",
        }
        self.assertTrue(required.issubset(names))

    def test_summarize_samples_uses_head_window(self):
        samples = [
            {
                "t_rel_s": 0.0,
                "d_actual_mm": 4.5,
                "F_N": 2.00,
                "Bmag_uT": 100.0,
                "Bx_uT": 1.0,
                "By_uT": 2.0,
                "Bz_uT": 3.0,
                "delta_Bx_uT": 4.0,
                "delta_By_uT": 5.0,
                "delta_Bz_uT": 6.0,
            },
            {
                "t_rel_s": 1.0,
                "d_actual_mm": 4.5,
                "F_N": 2.20,
                "Bmag_uT": 120.0,
                "Bx_uT": 1.0,
                "By_uT": 2.0,
                "Bz_uT": 3.0,
                "delta_Bx_uT": 4.0,
                "delta_By_uT": 5.0,
                "delta_Bz_uT": 6.0,
            },
            {
                "t_rel_s": 7.0,
                "d_actual_mm": 4.5,
                "F_N": 1.70,
                "Bmag_uT": 200.0,
                "Bx_uT": 10.0,
                "By_uT": 20.0,
                "Bz_uT": 30.0,
                "delta_Bx_uT": 40.0,
                "delta_By_uT": 50.0,
                "delta_Bz_uT": 60.0,
            },
        ]

        summary = summarize_samples(samples, window_s=2.0)

        self.assertAlmostEqual(summary["F_N"], 2.10)
        self.assertAlmostEqual(summary["Bmag_uT"], 110.0)
        self.assertEqual(summary["n"], 2)


if __name__ == "__main__":
    unittest.main()
