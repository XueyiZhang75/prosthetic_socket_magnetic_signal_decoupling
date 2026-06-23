import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ApmdNoContactMotionArtifactTests(unittest.TestCase):
    def test_default_replay_path_matches_selected_same_d_path(self):
        import apmd_no_contact_motion_artifact as artifact

        states = artifact.build_motion_sequence(
            target_d_mm=3.40,
            preload_d_mm=3.80,
            replay_contact_depth_mm=1.62,
        )

        self.assertEqual(
            [state.state_label for state in states],
            ["direct_target", "preload_deep", "return_target"],
        )
        self.assertEqual([state.record_s for state in states], [45.0, 30.0, 45.0])
        self.assertEqual([state.path_mode for state in states],
                         ["direct_loading", "preload_loading", "return_unloading"])
        self.assertAlmostEqual(states[0].mark10_pos_mm, -5.02, places=6)
        self.assertAlmostEqual(states[1].mark10_pos_mm, -5.42, places=6)
        self.assertAlmostEqual(states[2].mark10_pos_mm, -5.02, places=6)

    def test_artifact_diagnostic_uses_vector_delta_gate(self):
        import apmd_no_contact_motion_artifact as artifact

        direct = {
            "Bx_uT": 10.0,
            "By_uT": 20.0,
            "Bz_uT": 30.0,
            "Bmag_uT": math.sqrt(10.0 ** 2 + 20.0 ** 2 + 30.0 ** 2),
        }
        returned = {
            "Bx_uT": 13.0,
            "By_uT": 24.0,
            "Bz_uT": 30.0,
            "Bmag_uT": math.sqrt(13.0 ** 2 + 24.0 ** 2 + 30.0 ** 2),
        }

        diag = artifact.artifact_diagnostics(direct, returned, gate_uT=10.0)

        self.assertAlmostEqual(diag["delta_Bvec_uT"], 5.0, places=6)
        self.assertEqual(diag["artifact_ok"], True)
        self.assertEqual(diag["verdict"], "low_motion_artifact")


if __name__ == "__main__":
    unittest.main()
