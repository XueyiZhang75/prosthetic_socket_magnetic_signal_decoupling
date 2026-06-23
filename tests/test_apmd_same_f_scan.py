import unittest

import apmd_same_f_different_d_path_pair as base


class ApmdSameFDifferentDScanTests(unittest.TestCase):
    def setUp(self):
        names = [
            "F_TARGETS",
            "N_TRIALS",
            "SUMMARY_FILENAME",
            "CSV_PREFIX",
            "CSV_PRINT_GLOB",
            "FIGURE_FILENAME",
            "FORMAL_EXPERIMENT_KEY",
            "D_PRELOAD_EXTRA_MM",
            "D_PRELOAD_FIXED_MM",
            "F_PRELOAD_CAP_EXTRA_N",
            "F_PRELOAD_CAP_MAX_N",
            "D_PRELOAD_MAX_MM",
            "D_SOFT_LIMIT_MM",
            "F_HARD_LIMIT_N",
        ]
        self._snapshot = {name: getattr(base, name) for name in names}
        self.addCleanup(self._restore_base_config)

    def _restore_base_config(self):
        for name, value in self._snapshot.items():
            setattr(base, name, value)

    def test_block_a_configures_low_mid_force_targets(self):
        import apmd_same_f_different_d_scan as scan

        scan.apply_scan_block("A")
        scan.configure_base_protocol()

        self.assertEqual(
            base.F_TARGETS,
            [(150, 1.50), (180, 1.80), (250, 2.50)],
        )
        self.assertEqual(base.SUMMARY_FILENAME, "same_f_different_d_scan_A_pair_summary.csv")
        self.assertEqual(base.CSV_PREFIX, "same_f_different_d_scan_A")
        self.assertEqual(base.CSV_PRINT_GLOB, "same_f_different_d_scan_A*.csv")
        self.assertEqual(base.FORMAL_EXPERIMENT_KEY, "\u5b9e\u9a8c 3.2A")
        self.assertEqual(base.D_PRELOAD_EXTRA_MM, 0.30)
        self.assertIsNone(base.D_PRELOAD_FIXED_MM)
        self.assertIsNone(base.F_PRELOAD_CAP_EXTRA_N)
        self.assertIsNone(base.F_PRELOAD_CAP_MAX_N)
        self.assertIsNone(base.D_PRELOAD_MAX_MM)
        self.assertIsNone(base.D_SOFT_LIMIT_MM)
        self.assertIsNone(base.F_HARD_LIMIT_N)

    def test_block_b_and_c_have_expected_targets(self):
        import apmd_same_f_different_d_scan as scan

        scan.apply_scan_block("B")
        scan.configure_base_protocol()
        self.assertEqual(
            base.F_TARGETS,
            [(320, 3.20), (375, 3.75), (430, 4.30)],
        )
        self.assertEqual(base.FORMAL_EXPERIMENT_KEY, "\u5b9e\u9a8c 3.2B")

        scan.apply_scan_block("C")
        scan.configure_base_protocol()
        self.assertEqual(
            base.F_TARGETS,
            [(490, 4.90), (550, 5.50)],
        )
        self.assertEqual(base.FORMAL_EXPERIMENT_KEY, "\u5b9e\u9a8c 3.2C")

    def test_single_force_target_configures_one_short_session(self):
        import apmd_same_f_different_d_scan as scan

        scan.apply_scan_block("250")
        scan.configure_base_protocol()

        self.assertEqual(base.F_TARGETS, [(250, 2.50)])
        self.assertEqual(base.SUMMARY_FILENAME, "same_f_different_d_scan_250_pair_summary.csv")
        self.assertEqual(base.CSV_PREFIX, "same_f_different_d_scan")
        self.assertEqual(base.CSV_PRINT_GLOB, "same_f_different_d_scan_250*.csv")
        self.assertEqual(base.FORMAL_EXPERIMENT_KEY, "\u5b9e\u9a8c 3.2-250")
        self.assertIn("same-F/different-d single force point", base.PROTOCOL_SHORT_NAME)
        self.assertEqual(base.D_PRELOAD_EXTRA_MM, 0.30)
        self.assertIsNone(base.D_PRELOAD_FIXED_MM)

    def test_single_force_target_continues_after_successful_250_point(self):
        import apmd_same_f_different_d_scan as scan

        scan.apply_scan_block("320")
        scan.configure_base_protocol()

        self.assertEqual(base.F_TARGETS, [(320, 3.20)])
        self.assertEqual(base.SUMMARY_FILENAME, "same_f_different_d_scan_320_pair_summary.csv")
        self.assertEqual(base.CSV_PRINT_GLOB, "same_f_different_d_scan_320*.csv")
        self.assertEqual(base.FORMAL_EXPERIMENT_KEY, "\u5b9e\u9a8c 3.2-320")

    def test_block_l_single_force_target_uses_fixed_preload(self):
        import apmd_same_f_different_d_scan as scan

        scan.apply_scan_block("L450")
        scan.configure_base_protocol()

        self.assertEqual(base.F_TARGETS, [(450, 4.50)])
        self.assertEqual(base.D_PRELOAD_EXTRA_MM, 0.0)
        self.assertEqual(base.D_PRELOAD_FIXED_MM, 3.20)
        self.assertEqual(base.SUMMARY_FILENAME, "block_L_same_f_local_sensitivity_450_pair_summary.csv")
        self.assertEqual(base.CSV_PREFIX, "block_L_same_f_local_sensitivity")
        self.assertEqual(base.CSV_PRINT_GLOB, "block_L_same_f_local_sensitivity_450*.csv")
        self.assertEqual(base.FIGURE_FILENAME, "block_L_same_f_local_sensitivity_450.png")
        self.assertEqual(base.FORMAL_EXPERIMENT_KEY, "Block L same-F local sensitivity F=4.50 N")
        self.assertIn("Block L", base.PROTOCOL_SHORT_NAME)

    def test_preload_force_cap_can_be_disabled(self):
        base.F_PRELOAD_CAP_EXTRA_N = None
        base.F_PRELOAD_CAP_MAX_N = None

        self.assertIsNone(base.preload_force_cap(5.50))

    def test_preload_move_ignores_force_when_force_cap_is_off(self):
        class FakeMark10:
            def __init__(self):
                self.pos = -3.000
                self.moves = []

            def position_stable(self):
                return self.pos

            def move_to(self, target, tolerance_mm=0.02, **kwargs):
                self.moves.append((target, tolerance_mm))
                self.pos = target
                return self.pos

        class HighForce:
            def sample_average(self, duration_s):
                return 99.0, 0.001, 10

        ok, status, pos, current_d, force_n = base.move_to_preload_depth(
            FakeMark10(),
            HighForce(),
            contact_pos=-1.000,
            preload_d_mm=2.300,
            force_cap_N=None,
        )

        self.assertTrue(ok)
        self.assertEqual(status, "reached")
        self.assertAlmostEqual(current_d, 2.300)
        self.assertAlmostEqual(force_n, 99.0)


if __name__ == "__main__":
    unittest.main()
