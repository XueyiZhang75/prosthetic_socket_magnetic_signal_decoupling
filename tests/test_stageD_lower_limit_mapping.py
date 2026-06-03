import unittest

import stageD_safety_range as stage_d


class StageDLowerLimitMappingConfigTests(unittest.TestCase):
    def test_stage_d_maps_to_physical_lower_limit_without_interactive_steps(self):
        self.assertEqual(stage_d.PROBE_STOP_MODE, "physical_limit")
        self.assertFalse(stage_d.INTERACTIVE_PROBE)
        self.assertFalse(stage_d.VISUAL_CONFIRM_CONTACT)
        self.assertGreaterEqual(stage_d.PROBE_MAX_DEPTH_MM, 10.0)

    def test_force_marker_does_not_stop_physical_limit_mapping(self):
        reason = stage_d.probe_stop_reason(
            F_m=stage_d.PROBE_FORCE_MARKER_N + 0.5,
            b_mag=10000.0,
            d_compr=1.0,
            hit_physical_limit=False,
        )

        self.assertIsNone(reason)

    def test_physical_lower_limit_stops_mapping(self):
        reason = stage_d.probe_stop_reason(
            F_m=1.0,
            b_mag=10000.0,
            d_compr=2.0,
            hit_physical_limit=True,
        )

        self.assertEqual(reason, "physical_lower_limit")


if __name__ == "__main__":
    unittest.main()
