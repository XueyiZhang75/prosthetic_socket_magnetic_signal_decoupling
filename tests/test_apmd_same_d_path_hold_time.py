import unittest

import apmd_same_d_different_f_path_pair as base


class ApmdSameDPathHoldTimeTests(unittest.TestCase):
    def setUp(self):
        names = [
            "D_TARGETS_MM",
            "D_PRELOAD_BY_TARGET_MM",
            "D_PRELOAD_MM",
            "N_TRIALS",
            "TARGET_RECORD_S",
            "PRELOAD_RECORD_S",
            "SUMMARY_WINDOW_S",
            "INTER_TRIAL_REST_S",
            "SUMMARY_FILENAME",
            "STATE_FILE_PREFIX",
            "CSV_PRINT_GLOB",
            "FIGURE_FILENAME",
            "FORMAL_EXPERIMENT_KEY",
            "F_HARD_LIMIT_N",
        ]
        self._snapshot = {name: getattr(base, name) for name in names}
        self.addCleanup(self._restore_base_config)

    def _restore_base_config(self):
        for name, value in self._snapshot.items():
            setattr(base, name, value)

    def test_hold_time_plan_is_hold_time_major(self):
        import apmd_same_d_path_hold_time as hold_time

        plan = list(hold_time.iter_hold_time_plan())

        expected = []
        for hold_s in (5.0, 30.0, 90.0):
            expected.extend((3.40, 3.80, hold_s, trial) for trial in (1, 2, 3))

        self.assertEqual(len(plan), 9)
        self.assertEqual(
            [
                (
                    p["target_d_mm"],
                    p["preload_d_mm"],
                    p["preload_hold_s"],
                    p["trial"],
                )
                for p in plan
            ],
            expected,
        )

    def test_configures_base_for_experiment_3_3B(self):
        import apmd_same_d_path_hold_time as hold_time

        hold_time.configure_base_protocol()

        self.assertEqual(base.D_TARGETS_MM, [3.40])
        self.assertEqual(base.D_PRELOAD_BY_TARGET_MM, {3.40: 3.80})
        self.assertEqual(base.D_PRELOAD_MM, 3.80)
        self.assertEqual(base.N_TRIALS, 3)
        self.assertEqual(base.TARGET_RECORD_S, 45.0)
        self.assertEqual(base.PRELOAD_RECORD_S, 30.0)
        self.assertEqual(base.SUMMARY_WINDOW_S, 10.0)
        self.assertEqual(base.INTER_TRIAL_REST_S, 120.0)
        self.assertEqual(base.SUMMARY_FILENAME, "same_d_path_hold_time_B_pair_summary.csv")
        self.assertEqual(base.STATE_FILE_PREFIX, "same_d_path_hold_time_B")
        self.assertEqual(base.CSV_PRINT_GLOB, "same_d_path_hold_time_B*.csv")
        self.assertEqual(base.FIGURE_FILENAME, "same_d_path_hold_time_B.png")
        self.assertEqual(base.FORMAL_EXPERIMENT_KEY, "\u5b9e\u9a8c 3.3B")
        self.assertIsNone(base.F_HARD_LIMIT_N)


if __name__ == "__main__":
    unittest.main()
