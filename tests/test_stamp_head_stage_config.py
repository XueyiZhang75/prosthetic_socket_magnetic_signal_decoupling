import unittest

import stageI_hold_disp as stage_i
import stageI_plus_same_d_diff_f as stage_i_plus
import stageJ_hold_force as stage_j
import stageJ_plus_same_f_diff_d as stage_j_plus


class StampHeadStageConfigTests(unittest.TestCase):
    def test_passive_and_path_stages_share_stamp_head_ids(self):
        modules = [stage_i, stage_i_plus, stage_j, stage_j_plus]

        for module in modules:
            self.assertEqual(module.HEAD_ID, "stamp_head_v1")
            self.assertEqual(
                module.FORCE_CALIBRATION_ID,
                "force_calibration_20260602_190856",
            )
            self.assertEqual(
                module.DISPLACEMENT_ZERO_ID,
                "stageD_session_20260602_201421",
            )

    def test_stage_i_plus_is_configured_for_shallow_calibration_expansion(self):
        self.assertEqual(stage_i.D_HOLDS, [(160, 1.60)])
        self.assertEqual(stage_i_plus.D_TARGETS_MM, [1.40])
        self.assertAlmostEqual(stage_i_plus.preload_depth_for_target(1.40), 1.70)
        self.assertLessEqual(stage_i_plus.TARGET_POSITION_TOL_MM, 0.02)

    def test_stage_j_plus_is_configured_for_force_target_expansion(self):
        self.assertEqual(stage_j.F_HOLDS, [(180, 1.80)])
        self.assertEqual(stage_j_plus.F_TARGETS, [(170, 1.70), (190, 1.90)])
        self.assertAlmostEqual(stage_j.D_SOFT_LIMIT_MM, 2.20)
        self.assertAlmostEqual(stage_j_plus.D_SOFT_LIMIT_MM, 2.20)
        self.assertAlmostEqual(stage_j_plus.D_PRELOAD_MAX_MM, 2.00)

    def test_stage_j_is_in_formal_three_trial_mode(self):
        self.assertEqual(stage_j.N_TRIALS, 3)

    def test_stage_j_start_reset_skips_downward_trim_from_air_gap(self):
        self.assertFalse(stage_j.should_reset_to_trial_start(+0.45, 0.0))
        self.assertFalse(stage_j.should_reset_to_trial_start(+0.00, 0.0))
        self.assertTrue(stage_j.should_reset_to_trial_start(-2.07, 0.0))
        self.assertFalse(stage_j_plus.should_reset_to_trial_start(+0.45, 0.0))
        self.assertFalse(stage_j_plus.should_reset_to_trial_start(+0.00, 0.0))
        self.assertTrue(stage_j_plus.should_reset_to_trial_start(-2.07, 0.0))

    def test_stage_j_force_jump_gate_requires_no_matching_motion(self):
        self.assertTrue(stage_j.is_force_jump_without_motion(
            previous_F_N=1.78,
            current_F_N=1.89,
            previous_d_mm=1.40,
            current_d_mm=1.40,
        ))
        self.assertFalse(stage_j.is_force_jump_without_motion(
            previous_F_N=1.78,
            current_F_N=1.80,
            previous_d_mm=1.40,
            current_d_mm=1.40,
        ))
        self.assertFalse(stage_j.is_force_jump_without_motion(
            previous_F_N=1.78,
            current_F_N=1.89,
            previous_d_mm=1.40,
            current_d_mm=1.55,
        ))

    def test_all_key_rerun_stages_have_force_hard_limit(self):
        self.assertAlmostEqual(stage_i.F_HARD_LIMIT_N, 5.0)
        self.assertAlmostEqual(stage_i_plus.F_HARD_LIMIT_N, 5.0)
        self.assertAlmostEqual(stage_j.F_HARD_LIMIT_N, 5.0)
        self.assertAlmostEqual(stage_j_plus.F_HARD_LIMIT_N, 5.0)

    def test_live_tare_sanity_rejects_preloaded_start(self):
        class DummyForce:
            live_tare_N = -1.3523

        with self.assertRaisesRegex(RuntimeError, "already touching"):
            stage_i.assert_no_contact_live_tare(DummyForce(), "test")

    def test_live_tare_sanity_accepts_no_contact_start(self):
        class DummyForce:
            live_tare_N = -2.9145

        stage_i.assert_no_contact_live_tare(DummyForce(), "test")

    def test_precontact_abort_threshold_catches_large_initial_force(self):
        self.assertAlmostEqual(stage_i.PRECONTACT_FORCE_ABORT_N, 0.30)
        self.assertAlmostEqual(stage_j.PRECONTACT_FORCE_ABORT_N, 0.30)


if __name__ == "__main__":
    unittest.main()
