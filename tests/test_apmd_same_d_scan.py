import unittest

import apmd_same_d_different_f_path_pair as base


class ApmdSameDDifferentFScanTests(unittest.TestCase):
    def setUp(self):
        names = [
            "D_TARGETS_MM",
            "D_PRELOAD_BY_TARGET_MM",
            "D_PRELOAD_MM",
            "N_TRIALS",
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

    def test_scan_plan_is_target_major(self):
        import apmd_same_d_different_f_scan as scan

        scan.apply_scan_block("A")
        plan = list(scan.iter_scan_plan())

        expected_targets = [2.40, 2.60, 2.80]
        expected = []
        for target in expected_targets:
            preload = round(target + 0.30, 2)
            expected.extend((target, preload, trial) for trial in (1, 2, 3))

        self.assertEqual(len(plan), 9)
        self.assertEqual(
            [(p["target_d_mm"], p["preload_d_mm"], p["trial"]) for p in plan],
            expected,
        )

    def test_block_b_scan_plan_is_target_major(self):
        import apmd_same_d_different_f_scan as scan

        scan.apply_scan_block("B")
        plan = list(scan.iter_scan_plan())

        expected_targets = [3.00, 3.20, 3.40, 3.60]
        expected = []
        for target in expected_targets:
            preload = round(target + 0.30, 2)
            expected.extend((target, preload, trial) for trial in (1, 2, 3))

        self.assertEqual(len(plan), 12)
        self.assertEqual(
            [(p["target_d_mm"], p["preload_d_mm"], p["trial"]) for p in plan],
            expected,
        )

    def test_block_l_scan_plan_uses_fixed_lower_zone_preload(self):
        import apmd_same_d_different_f_scan as scan

        scan.apply_scan_block("L")
        plan = list(scan.iter_scan_plan())

        expected_targets = [2.40, 2.60, 2.80, 3.00]
        expected = []
        for target in expected_targets:
            expected.extend((target, 3.20, trial) for trial in (1, 2, 3))

        self.assertEqual(len(plan), 12)
        self.assertEqual(
            [(p["target_d_mm"], p["preload_d_mm"], p["trial"]) for p in plan],
            expected,
        )

    def test_block_l300_scan_plan_only_runs_d_3p0_supplement(self):
        import apmd_same_d_different_f_scan as scan

        scan.apply_scan_block("L300")
        plan = list(scan.iter_scan_plan())

        expected = [(3.00, 3.20, trial) for trial in (1, 2, 3)]

        self.assertEqual(len(plan), 3)
        self.assertEqual(
            [(p["target_d_mm"], p["preload_d_mm"], p["trial"]) for p in plan],
            expected,
        )

    def test_block_s_scan_plan_uses_fixed_shallow_zone_preload(self):
        import apmd_same_d_different_f_scan as scan

        scan.apply_scan_block("S")
        plan = list(scan.iter_scan_plan())

        expected_targets = [1.80, 2.00, 2.20, 2.40]
        expected = []
        for target in expected_targets:
            expected.extend((target, 2.60, trial) for trial in (1, 2, 3))

        self.assertEqual(len(plan), 12)
        self.assertEqual(
            [(p["target_d_mm"], p["preload_d_mm"], p["trial"]) for p in plan],
            expected,
        )

    def test_block_s_single_target_supplements_use_fixed_shallow_zone_preload(self):
        import apmd_same_d_different_f_scan as scan

        cases = [
            ("S180", 1.80),
            ("S200", 2.00),
            ("S220", 2.20),
            ("S240", 2.40),
        ]

        for block, target in cases:
            with self.subTest(block=block):
                scan.apply_scan_block(block)
                plan = list(scan.iter_scan_plan())

                expected = [(target, 2.60, trial) for trial in (1, 2, 3)]

                self.assertEqual(len(plan), 3)
                self.assertEqual(
                    [(p["target_d_mm"], p["preload_d_mm"], p["trial"]) for p in plan],
                    expected,
                )

    def test_block_h_scan_plan_uses_fixed_upper_zone_preload(self):
        import apmd_same_d_different_f_scan as scan

        scan.apply_scan_block("H")
        plan = list(scan.iter_scan_plan())

        expected_targets = [3.40, 3.60, 3.80, 4.00]
        expected = []
        for target in expected_targets:
            expected.extend((target, 4.20, trial) for trial in (1, 2, 3))

        self.assertEqual(len(plan), 12)
        self.assertEqual(
            [(p["target_d_mm"], p["preload_d_mm"], p["trial"]) for p in plan],
            expected,
        )

    def test_configures_base_for_experiment_3_1A(self):
        import apmd_same_d_different_f_scan as scan

        scan.apply_scan_block("A")
        scan.configure_base_protocol()

        self.assertEqual(base.D_TARGETS_MM, [2.40, 2.60, 2.80])
        self.assertEqual(
            base.D_PRELOAD_BY_TARGET_MM,
            {
                2.40: 2.70,
                2.60: 2.90,
                2.80: 3.10,
            },
        )
        self.assertEqual(base.SUMMARY_FILENAME, "same_d_different_f_scan_A_pair_summary.csv")
        self.assertEqual(base.STATE_FILE_PREFIX, "same_d_different_f_scan_A")
        self.assertEqual(base.CSV_PRINT_GLOB, "same_d_different_f_scan_A*.csv")
        self.assertIsNone(base.F_HARD_LIMIT_N)
        self.assertEqual(base.FORMAL_EXPERIMENT_KEY, "实验 3.1A")

    def test_configures_base_for_experiment_3_1B(self):
        import apmd_same_d_different_f_scan as scan

        scan.apply_scan_block("B")
        scan.configure_base_protocol()

        self.assertEqual(base.D_TARGETS_MM, [3.00, 3.20, 3.40, 3.60])
        self.assertEqual(
            base.D_PRELOAD_BY_TARGET_MM,
            {
                3.00: 3.30,
                3.20: 3.50,
                3.40: 3.70,
                3.60: 3.90,
            },
        )
        self.assertEqual(base.SUMMARY_FILENAME, "same_d_different_f_scan_B_pair_summary.csv")
        self.assertEqual(base.STATE_FILE_PREFIX, "same_d_different_f_scan_B")
        self.assertEqual(base.CSV_PRINT_GLOB, "same_d_different_f_scan_B*.csv")
        self.assertIsNone(base.F_HARD_LIMIT_N)
        self.assertEqual(base.FORMAL_EXPERIMENT_KEY, "实验 3.1B")

    def test_configures_base_for_block_l_same_d_sensitivity(self):
        import apmd_same_d_different_f_scan as scan

        scan.apply_scan_block("L")
        scan.configure_base_protocol()

        self.assertEqual(base.D_TARGETS_MM, [2.40, 2.60, 2.80, 3.00])
        self.assertEqual(
            base.D_PRELOAD_BY_TARGET_MM,
            {
                2.40: 3.20,
                2.60: 3.20,
                2.80: 3.20,
                3.00: 3.20,
            },
        )
        self.assertEqual(
            base.SUMMARY_FILENAME,
            "block_L_same_d_local_sensitivity_pair_summary.csv",
        )
        self.assertEqual(base.STATE_FILE_PREFIX, "block_L_same_d_local_sensitivity")
        self.assertEqual(base.CSV_PRINT_GLOB, "block_L_same_d_local_sensitivity*.csv")
        self.assertIsNone(base.F_HARD_LIMIT_N)
        self.assertEqual(base.FORMAL_EXPERIMENT_KEY, "Block L same-d local sensitivity")

    def test_configures_base_for_shallow_same_d_sensitivity(self):
        import apmd_same_d_different_f_scan as scan

        scan.apply_scan_block("S")
        scan.configure_base_protocol()

        self.assertEqual(base.D_TARGETS_MM, [1.80, 2.00, 2.20, 2.40])
        self.assertEqual(
            base.D_PRELOAD_BY_TARGET_MM,
            {
                1.80: 2.60,
                2.00: 2.60,
                2.20: 2.60,
                2.40: 2.60,
            },
        )
        self.assertEqual(
            base.SUMMARY_FILENAME,
            "shallow_same_d_local_sensitivity_pair_summary.csv",
        )
        self.assertEqual(base.STATE_FILE_PREFIX, "shallow_same_d_local_sensitivity")
        self.assertEqual(base.CSV_PRINT_GLOB, "shallow_same_d_local_sensitivity*.csv")
        self.assertIsNone(base.F_HARD_LIMIT_N)
        self.assertEqual(
            base.FORMAL_EXPERIMENT_KEY,
            "Shallow work-zone same-d local sensitivity",
        )

    def test_configures_base_for_upper_same_d_sensitivity(self):
        import apmd_same_d_different_f_scan as scan

        scan.apply_scan_block("H")
        scan.configure_base_protocol()

        self.assertEqual(base.D_TARGETS_MM, [3.40, 3.60, 3.80, 4.00])
        self.assertEqual(
            base.D_PRELOAD_BY_TARGET_MM,
            {
                3.40: 4.20,
                3.60: 4.20,
                3.80: 4.20,
                4.00: 4.20,
            },
        )
        self.assertEqual(
            base.SUMMARY_FILENAME,
            "upper_same_d_local_sensitivity_pair_summary.csv",
        )
        self.assertEqual(base.STATE_FILE_PREFIX, "upper_same_d_local_sensitivity")
        self.assertEqual(base.CSV_PRINT_GLOB, "upper_same_d_local_sensitivity*.csv")
        self.assertIsNone(base.F_HARD_LIMIT_N)
        self.assertEqual(
            base.FORMAL_EXPERIMENT_KEY,
            "Upper work-zone same-d local sensitivity",
        )

    def test_complete_formal_matrix_registers_as_formal(self):
        import apmd_same_d_different_f_scan as scan

        status, note = scan._scan_registry_status(
            pair_summary_count=9,
            expected_pair_count=9,
        )

        self.assertEqual(status, "formal")
        self.assertEqual(note, "")


if __name__ == "__main__":
    unittest.main()
