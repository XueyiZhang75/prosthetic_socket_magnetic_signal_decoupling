import unittest

import apmd_same_f_different_d_path_pair as base


class ApmdSameFPathDosageTests(unittest.TestCase):
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

    def test_dosage_plan_scans_preload_extra_depth(self):
        import apmd_same_f_path_dosage as dosage

        plan = list(dosage.iter_dose_plan([0.20, 0.30, 0.40]))

        expected = []
        for extra in (0.20, 0.30, 0.40):
            expected.extend((3.75, extra, trial) for trial in (1, 2, 3))

        self.assertEqual(len(plan), 9)
        self.assertEqual(
            [
                (
                    p["target_F_N"],
                    p["preload_extra_mm"],
                    p["trial"],
                )
                for p in plan
            ],
            expected,
        )

    def test_configures_base_for_experiment_3_4A(self):
        import apmd_same_f_path_dosage as dosage

        dosage.configure_base_protocol()

        self.assertEqual(base.F_TARGETS, [(375, 3.75)])
        self.assertEqual(base.N_TRIALS, 3)
        self.assertEqual(base.D_PRELOAD_EXTRA_MM, 0.20)
        self.assertIsNone(base.D_PRELOAD_MAX_MM)
        self.assertIsNone(base.D_SOFT_LIMIT_MM)
        self.assertIsNone(base.F_HARD_LIMIT_N)
        self.assertIsNone(base.F_PRELOAD_CAP_EXTRA_N)
        self.assertIsNone(base.F_PRELOAD_CAP_MAX_N)
        self.assertEqual(base.TARGET_RECORD_S, 45.0)
        self.assertEqual(base.PRELOAD_RECORD_S, 30.0)
        self.assertEqual(base.SUMMARY_WINDOW_S, 10.0)
        self.assertEqual(base.INTER_TRIAL_REST_S, 120.0)
        self.assertEqual(base.SUMMARY_FILENAME, "same_f_path_dosage_A_pair_summary.csv")
        self.assertEqual(base.CSV_PREFIX, "same_f_path_dosage_A")
        self.assertEqual(base.CSV_PRINT_GLOB, "same_f_path_dosage_A*.csv")
        self.assertEqual(base.FIGURE_FILENAME, "same_f_path_dosage_A.png")
        self.assertEqual(base.FORMAL_EXPERIMENT_KEY, "\u5b9e\u9a8c 3.4A")

    def test_selects_one_preload_extra_group_per_run(self):
        import apmd_same_f_path_dosage as dosage

        self.assertEqual(dosage.parse_dose_selection(["020"]), [0.20])
        self.assertEqual(dosage.parse_dose_selection(["A30"]), [0.30])
        self.assertEqual(dosage.parse_dose_selection(["040"]), [0.40])

        plan = list(dosage.iter_dose_plan(dosage.parse_dose_selection(["030"])))
        self.assertEqual(len(plan), 3)
        self.assertEqual({p["preload_extra_mm"] for p in plan}, {0.30})
        self.assertEqual([p["trial"] for p in plan], [1, 2, 3])

    def test_group_specific_output_names(self):
        import apmd_same_f_path_dosage as dosage

        dosage.configure_base_protocol([0.40])

        self.assertEqual(
            base.SUMMARY_FILENAME,
            "same_f_path_dosage_A_extra040_pair_summary.csv",
        )
        self.assertEqual(base.CSV_PREFIX, "same_f_path_dosage_A_extra040")
        self.assertEqual(base.CSV_PRINT_GLOB, "same_f_path_dosage_A_extra040*.csv")
        self.assertEqual(base.FORMAL_EXPERIMENT_KEY, "\u5b9e\u9a8c 3.4A-040")


if __name__ == "__main__":
    unittest.main()
