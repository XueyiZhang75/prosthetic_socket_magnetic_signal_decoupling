import math
import io
import unittest

from apmd_same_f_different_d_path_pair import (
    compute_preload_depth,
    is_usable_preload_stop,
    move_to_preload_depth,
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
            "delta_Bx_uT": 180.0,
            "delta_By_uT": 60.0,
            "delta_Bz_uT": 120.0,
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
            vector_norm3(80.0, 110.0, 100.0),
        )
        self.assertAlmostEqual(diag["slope_Bmag_uT_per_mm"], 250.0)

    def test_pair_diagnostics_accepts_displayed_0100mm_displacement_split(self):
        loading = {
            "F_N": 3.750,
            "d_mm": 2.340,
            "Bmag_uT": 8800.0,
            "delta_Bx_uT": 0.0,
            "delta_By_uT": 0.0,
            "delta_Bz_uT": 0.0,
        }
        unloading = {
            "F_N": 3.735,
            "d_mm": 2.4399999999999995,
            "Bmag_uT": 9100.0,
            "delta_Bx_uT": 5.0,
            "delta_By_uT": 220.0,
            "delta_Bz_uT": 210.0,
        }

        diag = pair_diagnostics(loading, unloading)

        self.assertAlmostEqual(diag["delta_d_mm"], 0.100, places=3)
        self.assertTrue(diag["same_F_ok"])
        self.assertTrue(diag["disp_split_ok"])
        self.assertTrue(diag["b_signal_ok"])
        self.assertEqual(diag["verdict"], "strong")

    def test_pair_diagnostics_rejects_0090mm_displacement_split(self):
        loading = {
            "F_N": 3.750,
            "d_mm": 2.340,
            "Bmag_uT": 8800.0,
            "delta_Bx_uT": 0.0,
            "delta_By_uT": 0.0,
            "delta_Bz_uT": 0.0,
        }
        unloading = {
            "F_N": 3.735,
            "d_mm": 2.430,
            "Bmag_uT": 9100.0,
            "delta_Bx_uT": 5.0,
            "delta_By_uT": 220.0,
            "delta_Bz_uT": 210.0,
        }

        diag = pair_diagnostics(loading, unloading)

        self.assertAlmostEqual(diag["delta_d_mm"], 0.090, places=3)
        self.assertTrue(diag["same_F_ok"])
        self.assertFalse(diag["disp_split_ok"])
        self.assertTrue(diag["b_signal_ok"])
        self.assertEqual(diag["verdict"], "weak_disp_split")

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

    def test_pair_diagnostics_rejects_force_error_above_formal_gate(self):
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

        self.assertFalse(diag["same_F_ok"])
        self.assertTrue(diag["disp_split_ok"])
        self.assertTrue(diag["b_signal_ok"])
        self.assertEqual(diag["verdict"], "bad_F_match")

    def test_summarize_samples_uses_tail_window_for_formal_state(self):
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

        self.assertAlmostEqual(summary["F_N"], 2.00)
        self.assertAlmostEqual(summary["Bmag_uT"], 200.0)

    def test_compute_preload_depth_uses_relative_depth_with_formal_cap(self):
        self.assertAlmostEqual(compute_preload_depth(1.60), 1.90)
        self.assertAlmostEqual(compute_preload_depth(1.75), 2.05)
        self.assertAlmostEqual(compute_preload_depth(4.30), 4.50)

    def test_preload_force_cap_matches_original_stage_j_plus_logic(self):
        self.assertAlmostEqual(preload_force_cap(1.70), 2.70)
        self.assertAlmostEqual(preload_force_cap(2.80), 3.20)

    def test_acquire_uses_coarse_steps_far_from_target_and_fine_steps_near_target(self):
        from apmd_same_f_different_d_path_pair import choose_acquire_step_mm

        self.assertAlmostEqual(choose_acquire_step_mm(1.60), 0.16)
        self.assertAlmostEqual(choose_acquire_step_mm(0.50), 0.12)
        self.assertAlmostEqual(choose_acquire_step_mm(0.04), 0.02)

    def test_acquire_accepts_either_side_inside_formal_force_gate(self):
        from apmd_same_f_different_d_path_pair import force_entry_ok

        self.assertTrue(force_entry_ok(+0.045, 0.050, "loading_target"))
        self.assertTrue(force_entry_ok(-0.045, 0.050, "unloading_target"))
        self.assertFalse(force_entry_ok(+0.055, 0.050, "loading_target"))

    def test_acquire_accepts_narrow_target_after_stage_j_plus_step(self):
        import apmd_same_f_different_d_path_pair as protocol

        class FakeMark10:
            def __init__(self):
                self.pos = -3.75
                self.moves = []

            def position_stable(self):
                return self.pos

            def move_to(self, target, tolerance_mm=0.02):
                self.moves.append((target, tolerance_mm))
                self.pos = round(target, 4)
                return self.pos

        class ForceSequence:
            def __init__(self):
                self.values = [2.10, 2.54]
                self.last = self.values[-1]

            def sample_average(self, duration_s):
                if self.values:
                    self.last = self.values.pop(0)
                return self.last, 0.001, 10

        old_settings = {
            "ACQUIRE_SETTLE_S": protocol.ACQUIRE_SETTLE_S,
            "ACQUIRE_SAMPLE_S": protocol.ACQUIRE_SAMPLE_S,
            "ACQUIRE_MAX_ITERS": protocol.ACQUIRE_MAX_ITERS,
            "D_SOFT_LIMIT_MM": protocol.D_SOFT_LIMIT_MM,
            "F_HARD_LIMIT_N": protocol.F_HARD_LIMIT_N,
        }
        try:
            protocol.ACQUIRE_SETTLE_S = 0.0
            protocol.ACQUIRE_SAMPLE_S = 0.0
            protocol.ACQUIRE_MAX_ITERS = 5
            protocol.D_SOFT_LIMIT_MM = None
            protocol.F_HARD_LIMIT_N = None

            ok, status, pos, d_actual, force_n, it = protocol.acquire_force_target(
                FakeMark10(),
                ForceSequence(),
                contact_pos=-1.59,
                target_F_N=2.50,
                log=io.StringIO(),
                trial=1,
                pair_label="250",
                state_label="unloading_target",
            )
        finally:
            for name, value in old_settings.items():
                setattr(protocol, name, value)

        self.assertTrue(ok)
        self.assertEqual(status, "reached")
        self.assertEqual(it, 2)
        self.assertAlmostEqual(force_n, 2.54)
        self.assertAlmostEqual(pos, -3.83)

    def test_acquire_refines_wide_bracket_before_accepting_state(self):
        import apmd_same_f_different_d_path_pair as protocol

        class FakeMark10:
            def __init__(self):
                self.pos = -4.21
                self.moves = []

            def position_stable(self):
                return self.pos

            def move_to(self, target, tolerance_mm=0.02):
                self.moves.append((target, tolerance_mm))
                self.pos = round(target, 4)
                return self.pos

        class ForceSequence:
            def __init__(self):
                self.values = [4.19, 2.74, 3.12]
                self.last = self.values[-1]

            def sample_average(self, duration_s):
                if self.values:
                    self.last = self.values.pop(0)
                return self.last, 0.001, 10

        old_settings = {
            "ACQUIRE_SETTLE_S": protocol.ACQUIRE_SETTLE_S,
            "ACQUIRE_SAMPLE_S": protocol.ACQUIRE_SAMPLE_S,
            "ACQUIRE_MAX_ITERS": protocol.ACQUIRE_MAX_ITERS,
            "D_SOFT_LIMIT_MM": protocol.D_SOFT_LIMIT_MM,
            "F_HARD_LIMIT_N": protocol.F_HARD_LIMIT_N,
        }
        try:
            protocol.ACQUIRE_SETTLE_S = 0.0
            protocol.ACQUIRE_SAMPLE_S = 0.0
            protocol.ACQUIRE_MAX_ITERS = 5
            protocol.D_SOFT_LIMIT_MM = None
            protocol.F_HARD_LIMIT_N = None

            ok, status, pos, d_actual, force_n, it = protocol.acquire_force_target(
                FakeMark10(),
                ForceSequence(),
                contact_pos=-1.69,
                target_F_N=3.11,
                log=io.StringIO(),
                trial=1,
                pair_label="320",
                state_label="unloading_target",
            )
        finally:
            for name, value in old_settings.items():
                setattr(protocol, name, value)

        self.assertTrue(ok)
        self.assertEqual(status, "reached")
        self.assertEqual(it, 3)
        self.assertAlmostEqual(force_n, 3.12)
        self.assertAlmostEqual(pos, -4.13)

    def test_acquire_rejects_position_above_contact_relief_bounds(self):
        import apmd_same_f_different_d_path_pair as protocol

        class FakeMark10:
            def __init__(self):
                self.pos = -3.790

            def position_stable(self):
                return self.pos

            def move_to(self, target, tolerance_mm=0.02):
                # Simulate the observed failure mode: the command should move
                # near -3.65 mm, but the next stable read is far above contact.
                self.pos = 0.124
                return target

        class ForceSequence:
            def __init__(self):
                self.values = [2.4065, 1.6920]

            def sample_average(self, duration_s):
                value = self.values.pop(0)
                return value, 0.001, 10

        old_settings = {
            "ACQUIRE_SETTLE_S": protocol.ACQUIRE_SETTLE_S,
            "ACQUIRE_SAMPLE_S": protocol.ACQUIRE_SAMPLE_S,
            "ACQUIRE_MAX_ITERS": protocol.ACQUIRE_MAX_ITERS,
            "D_SOFT_LIMIT_MM": protocol.D_SOFT_LIMIT_MM,
            "F_HARD_LIMIT_N": protocol.F_HARD_LIMIT_N,
        }
        try:
            protocol.ACQUIRE_SETTLE_S = 0.0
            protocol.ACQUIRE_SAMPLE_S = 0.0
            protocol.ACQUIRE_MAX_ITERS = 5
            protocol.D_SOFT_LIMIT_MM = None
            protocol.F_HARD_LIMIT_N = None

            ok, status, pos, d_actual, force_n, it = protocol.acquire_force_target(
                FakeMark10(),
                ForceSequence(),
                contact_pos=-1.790,
                target_F_N=1.7322,
                log=io.StringIO(),
                trial=3,
                pair_label="180",
                state_label="unloading",
            )
        finally:
            for name, value in old_settings.items():
                setattr(protocol, name, value)

        self.assertFalse(ok)
        self.assertEqual(status, "position_out_of_bounds")
        self.assertAlmostEqual(pos, 0.124)
        self.assertLess(d_actual, 0.0)

    def test_preload_move_uses_original_stage_j_plus_step_and_tolerance(self):
        class FakeMark10:
            def __init__(self):
                self.pos = -3.240
                self.moves = []

            def position_stable(self):
                return self.pos

            def move_to(self, target, tolerance_mm=0.02, **kwargs):
                self.moves.append((target, tolerance_mm))
                self.pos = target
                return self.pos

        class StableForce:
            def sample_average(self, duration_s):
                return 1.75, 0.001, 10

        mark10 = FakeMark10()
        ok, status, pos, current_d, force_n = move_to_preload_depth(
            mark10,
            StableForce(),
            contact_pos=-1.500,
            preload_d_mm=2.040,
            force_cap_N=2.70,
        )

        self.assertTrue(ok)
        self.assertEqual(status, "reached")
        self.assertEqual(len(mark10.moves), 3)
        self.assertTrue(all(tol == 0.02 for _, tol in mark10.moves))
        self.assertAlmostEqual(mark10.moves[0][0], -3.340)
        self.assertAlmostEqual(mark10.moves[-1][0], -3.540)
        self.assertAlmostEqual(pos, -3.540)
        self.assertAlmostEqual(current_d, 2.040)
        self.assertAlmostEqual(force_n, 1.75)

    def test_preload_move_accepts_final_depth_inside_motion_tolerance(self):
        class FakeMark10:
            def __init__(self):
                self.pos = -3.610
                self.moves = []

            def position_stable(self):
                return self.pos

            def move_to(self, target, tolerance_mm=0.02, **kwargs):
                self.moves.append((target, tolerance_mm))
                self.pos = target
                return self.pos

        class StableForce:
            def sample_average(self, duration_s):
                return 2.30, 0.001, 10

        mark10 = FakeMark10()
        ok, status, pos, current_d, force_n = move_to_preload_depth(
            mark10,
            StableForce(),
            contact_pos=-1.590,
            preload_d_mm=2.040,
            force_cap_N=None,
        )

        self.assertTrue(ok)
        self.assertEqual(status, "reached")
        self.assertEqual(mark10.moves, [])
        self.assertAlmostEqual(current_d, 2.020)
        self.assertAlmostEqual(force_n, 2.30)

    def test_force_cap_stop_is_usable_if_displacement_split_is_large(self):
        self.assertTrue(is_usable_preload_stop(3.75, 4.23))
        self.assertFalse(is_usable_preload_stop(3.75, 3.82))

    def test_vector_norm3(self):
        self.assertTrue(math.isclose(vector_norm3(3.0, 4.0, 12.0), 13.0))


if __name__ == "__main__":
    unittest.main()
