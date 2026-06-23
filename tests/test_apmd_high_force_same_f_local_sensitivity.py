import unittest

import apmd_same_f_different_d_path_pair as base


class ApmdHighForceSameFLocalSensitivityTests(unittest.TestCase):
    def setUp(self):
        names = [
            "PROTOCOL_TITLE",
            "PROTOCOL_SHORT_NAME",
            "LOG_HEADER",
            "F_TARGETS",
            "N_TRIALS",
            "D_PRELOAD_EXTRA_MM",
            "D_PRELOAD_FIXED_MM",
            "D_PRELOAD_MAX_MM",
            "F_PRELOAD_CAP_EXTRA_N",
            "F_PRELOAD_CAP_MAX_N",
            "D_SOFT_LIMIT_MM",
            "F_HARD_LIMIT_N",
            "TARGET_RECORD_S",
            "PRELOAD_RECORD_S",
            "SUMMARY_WINDOW_S",
            "INTER_TRIAL_REST_S",
            "FORCE_MATCH_TOL_N",
            "MIN_D_SPLIT_MM",
            "DYNAMIC_B_SIGNAL_UT",
            "SUMMARY_FILENAME",
            "CSV_PREFIX",
            "CSV_PRINT_GLOB",
            "FIGURE_FILENAME",
            "FORMAL_EXPERIMENT_KEY",
            "NEXT_MESSAGE",
        ]
        self._snapshot = {name: getattr(base, name) for name in names}
        self.addCleanup(self._restore_base_config)

    def _restore_base_config(self):
        for name, value in self._snapshot.items():
            setattr(base, name, value)

    def test_high_force_plan_uses_fixed_preload_depth(self):
        import apmd_high_force_same_f_local_sensitivity as script

        self.assertEqual(
            script.F_TARGETS_HIGH_FORCE,
            [(800, 8.00), (1000, 10.00), (1200, 12.00)],
        )
        self.assertEqual(script.FIXED_PRELOAD_D_MM, 3.80)

        script.configure_base_protocol()

        self.assertEqual(base.F_TARGETS, script.F_TARGETS_HIGH_FORCE)
        self.assertEqual(base.N_TRIALS, 3)
        self.assertEqual(base.D_PRELOAD_FIXED_MM, 3.80)
        self.assertEqual(base.D_PRELOAD_MAX_MM, None)
        self.assertEqual(base.D_SOFT_LIMIT_MM, None)
        self.assertEqual(base.F_HARD_LIMIT_N, None)
        self.assertEqual(base.FORCE_MATCH_TOL_N, 0.050)
        self.assertEqual(base.MIN_D_SPLIT_MM, 0.10)
        self.assertEqual(base.DYNAMIC_B_SIGNAL_UT, 100.0)
        self.assertEqual(
            base.SUMMARY_FILENAME,
            "high_force_same_f_local_sensitivity_pair_summary.csv",
        )
        self.assertEqual(base.CSV_PREFIX, "high_force_same_f_local_sensitivity")
        self.assertEqual(
            base.CSV_PRINT_GLOB,
            "high_force_same_f_local_sensitivity*.csv",
        )
        self.assertEqual(base.FORMAL_EXPERIMENT_KEY, "\u5b9e\u9a8c 6.4A")

    def test_fixed_preload_depth_overrides_extra_depth_rule(self):
        base.D_PRELOAD_FIXED_MM = 3.80
        base.D_PRELOAD_EXTRA_MM = 0.30
        base.D_PRELOAD_MAX_MM = None

        self.assertEqual(base.compute_preload_depth(3.20), 3.80)
        self.assertEqual(base.compute_preload_depth(3.60), 3.80)


if __name__ == "__main__":
    unittest.main()
