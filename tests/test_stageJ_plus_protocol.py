import math
import unittest

from stageJ_plus_same_f_diff_d import (
    compute_preload_depth,
    is_usable_preload_stop,
    pair_diagnostics,
    preload_force_cap,
    summarize_samples,
    vector_norm3,
)


class StageJPlusProtocolTests(unittest.TestCase):
    def test_pair_diagnostics_flags_same_force_different_displacement(self):
        loading = {
            "F_N": 2.000,
            "d_mm": 4.30,
            "Bmag_uT": 10000.0,
            "delta_Bx_uT": 100.0,
            "delta_By_uT": -50.0,
            "delta_Bz_uT": 20.0,
        }
        unloading = {
            "F_N": 2.035,
            "d_mm": 4.62,
            "Bmag_uT": 10080.0,
            "delta_Bx_uT": 120.0,
            "delta_By_uT": -10.0,
            "delta_Bz_uT": 70.0,
        }

        diag = pair_diagnostics(loading, unloading)

        self.assertTrue(diag["same_F_ok"])
        self.assertTrue(diag["disp_split_ok"])
        self.assertTrue(diag["b_signal_ok"])
        self.assertEqual(diag["verdict"], "strong")
        self.assertAlmostEqual(diag["delta_F_N"], 0.035)
        self.assertAlmostEqual(diag["delta_d_mm"], 0.32)
        self.assertAlmostEqual(
            diag["delta_Bvec_uT"],
            vector_norm3(20.0, 40.0, 50.0),
        )
        self.assertAlmostEqual(diag["slope_Bmag_uT_per_mm"], 250.0)

    def test_pair_diagnostics_rejects_bad_force_match(self):
        loading = {
            "F_N": 1.80,
            "d_mm": 4.20,
            "Bmag_uT": 9000.0,
            "delta_Bx_uT": 0.0,
            "delta_By_uT": 0.0,
            "delta_Bz_uT": 0.0,
        }
        unloading = {
            "F_N": 2.05,
            "d_mm": 4.70,
            "Bmag_uT": 9100.0,
            "delta_Bx_uT": 30.0,
            "delta_By_uT": 40.0,
            "delta_Bz_uT": 50.0,
        }

        diag = pair_diagnostics(loading, unloading)

        self.assertFalse(diag["same_F_ok"])
        self.assertTrue(diag["disp_split_ok"])
        self.assertEqual(diag["verdict"], "bad_F_match")

    def test_pair_diagnostics_accepts_mark10_quantized_force_match(self):
        loading = {
            "F_N": 2.1287,
            "d_mm": 4.40,
            "Bmag_uT": 12855.8,
            "delta_Bx_uT": 0.0,
            "delta_By_uT": 0.0,
            "delta_Bz_uT": 0.0,
        }
        unloading = {
            "F_N": 2.2227,
            "d_mm": 4.70,
            "Bmag_uT": 13529.8,
            "delta_Bx_uT": -150.9,
            "delta_By_uT": 665.9,
            "delta_Bz_uT": -338.8,
        }

        diag = pair_diagnostics(loading, unloading)

        self.assertTrue(diag["same_F_ok"])
        self.assertTrue(diag["disp_split_ok"])
        self.assertTrue(diag["b_signal_ok"])
        self.assertEqual(diag["verdict"], "strong")

    def test_summarize_samples_uses_head_window_for_jplus_state(self):
        samples = [
            {
                "t_rel_s": 0.0,
                "d_actual_mm": 4.4,
                "F_N": 2.20,
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
                "d_actual_mm": 4.4,
                "F_N": 2.18,
                "Bmag_uT": 110.0,
                "Bx_uT": 1.0,
                "By_uT": 2.0,
                "Bz_uT": 3.0,
                "delta_Bx_uT": 4.0,
                "delta_By_uT": 5.0,
                "delta_Bz_uT": 6.0,
            },
            {
                "t_rel_s": 8.0,
                "d_actual_mm": 4.4,
                "F_N": 2.00,
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

        self.assertAlmostEqual(summary["F_N"], 2.19)
        self.assertAlmostEqual(summary["Bmag_uT"], 105.0)

    def test_compute_preload_depth_uses_relative_depth_and_cap(self):
        self.assertAlmostEqual(compute_preload_depth(1.60), 1.90)
        self.assertAlmostEqual(compute_preload_depth(1.75), 2.00)
        self.assertAlmostEqual(compute_preload_depth(2.10), 2.00)

    def test_preload_force_cap_limits_interpretation_window(self):
        self.assertAlmostEqual(preload_force_cap(1.70), 2.70)
        self.assertAlmostEqual(preload_force_cap(2.80), 3.20)

    def test_force_cap_stop_is_usable_if_displacement_split_is_large(self):
        self.assertTrue(is_usable_preload_stop(3.75, 4.23))
        self.assertFalse(is_usable_preload_stop(3.75, 3.82))

    def test_vector_norm3(self):
        self.assertTrue(math.isclose(vector_norm3(3.0, 4.0, 12.0), 13.0))


if __name__ == "__main__":
    unittest.main()
