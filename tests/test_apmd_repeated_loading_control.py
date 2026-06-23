import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ApmdRepeatedLoadingControlTests(unittest.TestCase):
    def test_default_cycle_plan_repeats_loading_without_preload(self):
        import apmd_repeated_loading_control as control

        cycles = control.build_cycle_plan(target_d_mm=3.40, cycles=5)

        self.assertEqual([cycle.cycle for cycle in cycles], [1, 2, 3, 4, 5])
        self.assertEqual([cycle.state_label for cycle in cycles], ["loading_target"] * 5)
        self.assertEqual([cycle.path_mode for cycle in cycles], ["repeat_loading"] * 5)
        self.assertEqual([cycle.target_d_mm for cycle in cycles], [3.40] * 5)
        self.assertEqual([cycle.preload_d_mm for cycle in cycles], [3.40] * 5)
        self.assertEqual([cycle.record_s for cycle in cycles], [45.0] * 5)

    def test_cycle_to_reference_diagnostics_use_vector_delta_gate(self):
        import apmd_repeated_loading_control as control

        reference = {
            "F_N": 6.0,
            "d_mm": 3.40,
            "Bmag_uT": math.sqrt(100.0 ** 2 + 200.0 ** 2 + 300.0 ** 2),
            "delta_Bx_uT": 100.0,
            "delta_By_uT": 200.0,
            "delta_Bz_uT": 300.0,
        }
        current = {
            "F_N": 6.1,
            "d_mm": 3.40,
            "Bmag_uT": math.sqrt(106.0 ** 2 + 208.0 ** 2 + 300.0 ** 2),
            "delta_Bx_uT": 106.0,
            "delta_By_uT": 208.0,
            "delta_Bz_uT": 300.0,
        }

        diag = control.cycle_to_reference_diagnostics(
            reference, current, gate_uT=10.0
        )

        self.assertAlmostEqual(diag["delta_Bvec_uT"], 10.0, places=6)
        self.assertEqual(diag["control_ok"], True)
        self.assertEqual(diag["verdict"], "repeat_loading_low_memory")

    def test_registry_status_requires_all_cycles_and_low_control_delta(self):
        import apmd_repeated_loading_control as control

        status, note = control.registry_status_for_control(
            acquired_cycles=5,
            expected_cycles=5,
            max_delta_Bvec_uT=42.0,
            gate_uT=50.0,
        )

        self.assertEqual(status, "formal")
        self.assertIn("passed 5/5", note)

        status, note = control.registry_status_for_control(
            acquired_cycles=5,
            expected_cycles=5,
            max_delta_Bvec_uT=75.0,
            gate_uT=50.0,
        )

        self.assertEqual(status, "")
        self.assertIn("not registered", note)

    def test_fixed_contact_policy_uses_same_absolute_target_position(self):
        import apmd_repeated_loading_control as control

        cycles = control.build_cycle_plan(target_d_mm=3.40, cycles=5)
        positions = control.fixed_contact_target_positions(
            contact_pos_mm=-1.690,
            cycles=cycles,
        )

        self.assertEqual(len(positions), 5)
        self.assertTrue(all(pos == positions[0] for pos in positions))
        self.assertAlmostEqual(positions[0], -5.090, places=6)


if __name__ == "__main__":
    unittest.main()
