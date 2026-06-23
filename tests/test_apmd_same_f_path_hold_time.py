import unittest

import apmd_same_f_different_d_path_pair as base


class ApmdSameFPathHoldTimeTests(unittest.TestCase):
    def setUp(self):
        names = [
            "F_TARGETS",
            "N_TRIALS",
            "D_PRELOAD_EXTRA_MM",
            "D_PRELOAD_MAX_MM",
            "D_SOFT_LIMIT_MM",
            "F_HARD_LIMIT_N",
            "TARGET_RECORD_S",
            "PRELOAD_RECORD_S",
            "SUMMARY_WINDOW_S",
            "INTER_TRIAL_REST_S",
            "SUMMARY_FILENAME",
            "CSV_PREFIX",
            "CSV_PRINT_GLOB",
            "FIGURE_FILENAME",
            "FORMAL_EXPERIMENT_KEY",
            "F_PRELOAD_CAP_EXTRA_N",
            "F_PRELOAD_CAP_MAX_N",
        ]
        self._snapshot = {name: getattr(base, name) for name in names}
        self.addCleanup(self._restore_base_config)

    def _restore_base_config(self):
        for name, value in self._snapshot.items():
            setattr(base, name, value)

    def test_hold_time_plan_scans_preload_hold_duration(self):
        import apmd_same_f_path_hold_time as hold_time

        plan = list(hold_time.iter_hold_time_plan([5.0, 30.0, 90.0]))

        expected = []
        for hold_s in (5.0, 30.0, 90.0):
            expected.extend((3.75, 0.40, hold_s, trial) for trial in (1, 2, 3))

        self.assertEqual(len(plan), 9)
        self.assertEqual(
            [
                (
                    p["target_F_N"],
                    p["preload_extra_mm"],
                    p["preload_hold_s"],
                    p["trial"],
                )
                for p in plan
            ],
            expected,
        )

    def test_configures_base_for_experiment_3_4B(self):
        import apmd_same_f_path_hold_time as hold_time

        hold_time.configure_base_protocol()

        self.assertEqual(base.F_TARGETS, [(375, 3.75)])
        self.assertEqual(base.N_TRIALS, 3)
        self.assertEqual(base.D_PRELOAD_EXTRA_MM, 0.40)
        self.assertIsNone(base.D_PRELOAD_MAX_MM)
        self.assertIsNone(base.D_SOFT_LIMIT_MM)
        self.assertIsNone(base.F_HARD_LIMIT_N)
        self.assertIsNone(base.F_PRELOAD_CAP_EXTRA_N)
        self.assertIsNone(base.F_PRELOAD_CAP_MAX_N)
        self.assertEqual(base.TARGET_RECORD_S, 45.0)
        self.assertEqual(base.PRELOAD_RECORD_S, 30.0)
        self.assertEqual(base.SUMMARY_WINDOW_S, 10.0)
        self.assertEqual(base.INTER_TRIAL_REST_S, 120.0)
        self.assertEqual(base.SUMMARY_FILENAME, "same_f_path_hold_time_B_pair_summary.csv")
        self.assertEqual(base.CSV_PREFIX, "same_f_path_hold_time_B")
        self.assertEqual(base.CSV_PRINT_GLOB, "same_f_path_hold_time_B*.csv")
        self.assertEqual(base.FIGURE_FILENAME, "same_f_path_hold_time_B.png")
        self.assertEqual(base.FORMAL_EXPERIMENT_KEY, "\u5b9e\u9a8c 3.4B")

    def test_selects_one_hold_time_group_per_run(self):
        import apmd_same_f_path_hold_time as hold_time

        self.assertEqual(hold_time.parse_hold_selection(["005"]), [5.0])
        self.assertEqual(hold_time.parse_hold_selection(["030"]), [30.0])
        self.assertEqual(hold_time.parse_hold_selection(["090"]), [90.0])
        self.assertEqual(hold_time.parse_hold_selection(["B"]), [5.0, 30.0, 90.0])

        plan = list(hold_time.iter_hold_time_plan(hold_time.parse_hold_selection(["030"])))
        self.assertEqual(len(plan), 3)
        self.assertEqual({p["preload_hold_s"] for p in plan}, {30.0})
        self.assertEqual([p["trial"] for p in plan], [1, 2, 3])

    def test_group_specific_output_names(self):
        import apmd_same_f_path_hold_time as hold_time

        hold_time.configure_base_protocol([90.0])

        self.assertEqual(
            base.SUMMARY_FILENAME,
            "same_f_path_hold_time_B_hold090_pair_summary.csv",
        )
        self.assertEqual(base.CSV_PREFIX, "same_f_path_hold_time_B_hold090")
        self.assertEqual(base.CSV_PRINT_GLOB, "same_f_path_hold_time_B_hold090*.csv")
        self.assertEqual(base.FORMAL_EXPERIMENT_KEY, "\u5b9e\u9a8c 3.4B-090")


if __name__ == "__main__":
    unittest.main()
