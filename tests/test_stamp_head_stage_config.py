import unittest

import stageI_hold_disp as stage_i
import apmd_same_d_different_f_path_pair as same_d_path_pair
import apmd_fixed_force_passive_creep as fixed_force_passive_creep
import apmd_same_f_different_d_path_pair as same_f_path_pair


class StampHeadStageConfigTests(unittest.TestCase):
    def test_passive_and_path_stages_share_stamp_head_ids(self):
        modules = [stage_i, same_d_path_pair, fixed_force_passive_creep, same_f_path_pair]

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

    def test_same_d_path_pair_is_configured_for_formal_anchor_rerun(self):
        self.assertEqual(stage_i.D_HOLDS, [(280, 2.80)])
        self.assertEqual(same_d_path_pair.D_TARGETS_MM, [2.80])
        self.assertAlmostEqual(same_d_path_pair.preload_depth_for_target(2.80), 3.10)
        self.assertAlmostEqual(same_d_path_pair.TARGET_RECORD_S, 45.0)
        self.assertAlmostEqual(same_d_path_pair.PRELOAD_RECORD_S, 30.0)
        self.assertAlmostEqual(same_d_path_pair.SUMMARY_WINDOW_S, 10.0)
        self.assertAlmostEqual(same_d_path_pair.INTER_TRIAL_REST_S, 120.0)
        self.assertLessEqual(same_d_path_pair.TARGET_POSITION_TOL_MM, 0.02)
        self.assertAlmostEqual(same_d_path_pair.D_MATCH_TOL_MM, 0.020)

    def test_same_f_path_pair_is_configured_for_formal_experiment_2_4(self):
        self.assertEqual(fixed_force_passive_creep.F_HOLDS, [(430, 4.30)])
        self.assertEqual(same_f_path_pair.F_TARGETS, [(180, 1.80)])
        self.assertIsNone(fixed_force_passive_creep.D_SOFT_LIMIT_MM)
        self.assertAlmostEqual(same_f_path_pair.D_SOFT_LIMIT_MM, 4.50)
        self.assertAlmostEqual(same_f_path_pair.D_PRELOAD_MAX_MM, 4.50)
        self.assertAlmostEqual(same_f_path_pair.TARGET_RECORD_S, 45.0)
        self.assertAlmostEqual(same_f_path_pair.PRELOAD_RECORD_S, 30.0)
        self.assertAlmostEqual(same_f_path_pair.SUMMARY_WINDOW_S, 10.0)
        self.assertEqual(same_f_path_pair.SUMMARY_WINDOW_MODE, "tail")
        self.assertAlmostEqual(same_f_path_pair.FORCE_MATCH_TOL_N, 0.050)
        self.assertAlmostEqual(same_f_path_pair.ACQUIRE_MIN_STEP_MM, 0.02)
        self.assertAlmostEqual(same_f_path_pair.ACQUIRE_MAX_STEP_MM, 0.16)
        self.assertAlmostEqual(same_f_path_pair.CONTROL_MOVE_TOL_MM, 0.02)
        self.assertAlmostEqual(same_f_path_pair.ACQUIRE_SAMPLE_S, 0.35)
        self.assertAlmostEqual(same_f_path_pair.DYNAMIC_B_SIGNAL_UT, 100.0)
        self.assertAlmostEqual(same_f_path_pair.INTER_TRIAL_REST_S, 120.0)
        self.assertEqual(fixed_force_passive_creep.ACQUIRE_MAX_ITERS, 100)
        self.assertAlmostEqual(fixed_force_passive_creep.ACQUIRE_MAX_NUDGE_MM, 0.18)
        self.assertAlmostEqual(fixed_force_passive_creep.ACQUIRE_MIN_NUDGE_MM, 0.02)
        self.assertAlmostEqual(fixed_force_passive_creep.choose_acquire_nudge_mm(0.03), 0.04)
        self.assertAlmostEqual(fixed_force_passive_creep.choose_acquire_nudge_mm(0.60), 0.14)
        self.assertAlmostEqual(fixed_force_passive_creep.choose_acquire_nudge_mm(1.20), 0.18)

    def test_fixed_force_hold_uses_fine_nudges_near_target(self):
        self.assertEqual(
            fixed_force_passive_creep.CONTROL_MOVE_TOL_MM,
            fixed_force_passive_creep.MIN_NUDGE_MM,
        )
        self.assertAlmostEqual(fixed_force_passive_creep.choose_hold_nudge_mm(0.04), 0.03)
        self.assertAlmostEqual(fixed_force_passive_creep.choose_hold_nudge_mm(0.06), 0.05)
        self.assertAlmostEqual(fixed_force_passive_creep.choose_hold_nudge_mm(0.12), 0.08)
        self.assertAlmostEqual(fixed_force_passive_creep.choose_hold_nudge_mm(0.30), 0.08)

    def test_fixed_force_passive_creep_is_in_smoke_test_mode(self):
        self.assertEqual(fixed_force_passive_creep.N_TRIALS, 1)

    def test_stage_j_start_reset_skips_downward_trim_from_air_gap(self):
        self.assertFalse(fixed_force_passive_creep.should_reset_to_trial_start(+0.45, 0.0))
        self.assertFalse(fixed_force_passive_creep.should_reset_to_trial_start(+0.00, 0.0))
        self.assertTrue(fixed_force_passive_creep.should_reset_to_trial_start(-2.07, 0.0))
        self.assertFalse(same_f_path_pair.should_reset_to_trial_start(+0.45, 0.0))
        self.assertFalse(same_f_path_pair.should_reset_to_trial_start(+0.00, 0.0))
        self.assertTrue(same_f_path_pair.should_reset_to_trial_start(-2.07, 0.0))

    def test_stage_j_force_jump_gate_requires_no_matching_motion(self):
        self.assertTrue(fixed_force_passive_creep.is_force_jump_without_motion(
            previous_F_N=1.78,
            current_F_N=1.89,
            previous_d_mm=1.40,
            current_d_mm=1.40,
        ))
        self.assertFalse(fixed_force_passive_creep.is_force_jump_without_motion(
            previous_F_N=1.78,
            current_F_N=1.80,
            previous_d_mm=1.40,
            current_d_mm=1.40,
        ))
        self.assertFalse(fixed_force_passive_creep.is_force_jump_without_motion(
            previous_F_N=1.78,
            current_F_N=1.89,
            previous_d_mm=1.40,
            current_d_mm=1.55,
        ))

    def test_all_key_rerun_stages_have_force_hard_limit(self):
        self.assertIsNone(stage_i.F_HARD_LIMIT_N)
        self.assertIsNone(same_d_path_pair.F_HARD_LIMIT_N)
        self.assertIsNone(fixed_force_passive_creep.F_HARD_LIMIT_N)
        self.assertIsNone(same_f_path_pair.F_HARD_LIMIT_N)

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
        self.assertAlmostEqual(fixed_force_passive_creep.PRECONTACT_FORCE_ABORT_N, 0.30)


if __name__ == "__main__":
    unittest.main()
