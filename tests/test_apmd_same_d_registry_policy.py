import unittest

from apmd_same_d_different_f_path_pair import pair_diagnostics, registry_status_for_pairs


class ApmdSameDRegistryPolicyTests(unittest.TestCase):
    def test_same_d_gate_accepts_boundary_float_roundoff(self):
        direct = {
            "d_mm": 1.58,
            "F_N": 2.10,
            "Bmag_uT": 100.0,
            "delta_Bx_uT": 0.0,
            "delta_By_uT": 0.0,
            "delta_Bz_uT": 0.0,
        }
        returned = {
            "d_mm": 1.60,
            "F_N": 1.60,
            "Bmag_uT": 150.0,
            "delta_Bx_uT": 0.0,
            "delta_By_uT": 60.0,
            "delta_Bz_uT": 0.0,
        }

        diag = pair_diagnostics(direct, returned)

        self.assertTrue(diag["same_d_ok"])

    def test_registers_only_complete_all_strong_pairs(self):
        status, note = registry_status_for_pairs(
            pair_summary_count=3,
            usable_pair_count=3,
            expected_pair_count=3,
        )

        self.assertEqual(status, "formal")
        self.assertEqual(note, "")

    def test_does_not_register_partial_or_failed_pairs(self):
        cases = [
            (0, 0, 3),
            (2, 2, 3),
            (3, 2, 3),
            (3, 0, 3),
        ]

        for pair_count, usable_count, expected_count in cases:
            with self.subTest(pair_count=pair_count, usable_count=usable_count):
                status, note = registry_status_for_pairs(
                    pair_summary_count=pair_count,
                    usable_pair_count=usable_count,
                    expected_pair_count=expected_count,
                )
                self.assertEqual(status, "")
                self.assertIn("not registered", note)


if __name__ == "__main__":
    unittest.main()
