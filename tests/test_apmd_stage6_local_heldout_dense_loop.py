import unittest

import apmd_local_minor_loop_dense_sampling as dense
import apmd_same_d_different_f_path_pair as base
import apmd_stage6_local_heldout_dense_loop as heldout


class ApmdStage6LocalHeldoutDenseLoopTests(unittest.TestCase):
    def setUp(self):
        base_names = [
            "PROTOCOL_TITLE",
            "PROTOCOL_SHORT_NAME",
            "STAGE_LABEL",
            "LOG_HEADER",
            "D_TARGETS_MM",
            "D_PRELOAD_BY_TARGET_MM",
            "D_PRELOAD_MM",
            "N_TRIALS",
            "TARGET_RECORD_S",
            "PRELOAD_RECORD_S",
            "SUMMARY_WINDOW_S",
            "PRE_RECORD_SETTLE_S",
            "INTER_STATE_SETTLE_S",
            "INTER_TRIAL_REST_S",
            "SUMMARY_FILENAME",
            "STATE_FILE_PREFIX",
            "CSV_PRINT_GLOB",
            "FIGURE_FILENAME",
            "FORMAL_EXPERIMENT_KEY",
            "F_HARD_LIMIT_N",
            "NEXT_MESSAGE",
        ]
        dense_names = [
            "D_GRID_MM",
            "PRELOAD_D_MM",
            "N_CYCLES",
            "STATE_RECORD_S",
            "PRELOAD_RECORD_S",
            "SUMMARY_WINDOW_S",
            "PRE_RECORD_SETTLE_S",
            "INTER_STATE_SETTLE_S",
            "INTER_CYCLE_REST_S",
            "SUMMARY_FILENAME",
            "STATE_FILE_PREFIX",
            "CSV_PRINT_GLOB",
            "FIGURE_FILENAME",
            "configure_base_protocol",
        ]
        heldout_names = [
            "WORK_ZONE_BLOCK",
            "D_GRID_MM",
            "PRELOAD_D_MM",
            "SUMMARY_FILENAME",
            "STATE_FILE_PREFIX",
            "CSV_PRINT_GLOB",
            "FIGURE_FILENAME",
        ]
        self._base_snapshot = {name: getattr(base, name) for name in base_names}
        self._dense_snapshot = {name: getattr(dense, name) for name in dense_names}
        self._heldout_snapshot = {name: getattr(heldout, name) for name in heldout_names}
        self.addCleanup(self._restore)

    def _restore(self):
        for name, value in self._base_snapshot.items():
            setattr(base, name, value)
        for name, value in self._dense_snapshot.items():
            setattr(dense, name, value)
        for name, value in self._heldout_snapshot.items():
            setattr(heldout, name, value)

    def test_stage6_configures_interleaved_heldout_grid(self):
        import apmd_stage6_local_heldout_dense_loop as heldout

        heldout.configure_dense_module()
        dense.configure_base_protocol()

        expected_grid = [3.05, 3.15, 3.25, 3.35, 3.45, 3.55]
        self.assertEqual(dense.D_GRID_MM, expected_grid)
        self.assertEqual(base.D_TARGETS_MM, expected_grid)
        self.assertEqual(base.D_PRELOAD_BY_TARGET_MM, {d: 3.80 for d in expected_grid})
        self.assertEqual(base.D_PRELOAD_MM, 3.80)
        self.assertEqual(base.N_TRIALS, 3)
        self.assertEqual(base.TARGET_RECORD_S, 15.0)
        self.assertEqual(base.PRELOAD_RECORD_S, 30.0)
        self.assertEqual(base.SUMMARY_WINDOW_S, 5.0)
        self.assertEqual(base.INTER_TRIAL_REST_S, 120.0)
        self.assertEqual(
            base.SUMMARY_FILENAME,
            "local_heldout_dense_loop_6p1_state_summary.csv",
        )
        self.assertEqual(base.STATE_FILE_PREFIX, "local_heldout_dense_loop_6p1")
        self.assertEqual(base.CSV_PRINT_GLOB, "local_heldout_dense_loop_6p1*.csv")
        self.assertEqual(base.FIGURE_FILENAME, "local_heldout_dense_loop_6p1.png")
        self.assertEqual(base.FORMAL_EXPERIMENT_KEY, "\u9a8c\u8bc1 6.1")

    def test_stage6_loop_state_order_is_loading_preload_unloading(self):
        import apmd_stage6_local_heldout_dense_loop as heldout

        heldout.configure_dense_module()
        states = list(dense.iter_loop_states())

        self.assertEqual(len(states), 13)
        self.assertEqual(
            [s["target_d_mm"] for s in states],
            [
                3.05,
                3.15,
                3.25,
                3.35,
                3.45,
                3.55,
                3.80,
                3.55,
                3.45,
                3.35,
                3.25,
                3.15,
                3.05,
            ],
        )
        self.assertEqual([s["branch"] for s in states[:6]], ["loading"] * 6)
        self.assertEqual(states[6]["branch"], "preload")
        self.assertEqual([s["branch"] for s in states[7:]], ["unloading"] * 6)

    def test_stage6_block_l_configures_lower_interleaved_heldout_grid(self):
        import apmd_stage6_local_heldout_dense_loop as heldout

        heldout.apply_work_zone_config("L")
        heldout.configure_dense_module()
        dense.configure_base_protocol()
        states = list(dense.iter_loop_states())

        expected_grid = [2.45, 2.55, 2.65, 2.75, 2.85, 2.95]
        self.assertEqual(dense.D_GRID_MM, expected_grid)
        self.assertEqual(dense.PRELOAD_D_MM, 3.20)
        self.assertEqual(base.D_TARGETS_MM, expected_grid)
        self.assertEqual(base.D_PRELOAD_BY_TARGET_MM, {d: 3.20 for d in expected_grid})
        self.assertEqual(base.D_PRELOAD_MM, 3.20)
        self.assertEqual(base.N_TRIALS, 3)
        self.assertEqual(
            base.SUMMARY_FILENAME,
            "local_heldout_dense_loop_6p1_L_state_summary.csv",
        )
        self.assertEqual(base.STATE_FILE_PREFIX, "local_heldout_dense_loop_6p1_L")
        self.assertEqual(base.CSV_PRINT_GLOB, "local_heldout_dense_loop_6p1_L*.csv")
        self.assertEqual(base.FIGURE_FILENAME, "local_heldout_dense_loop_6p1_L.png")
        self.assertEqual(base.FORMAL_EXPERIMENT_KEY, "\u9a8c\u8bc1 6.1-L")
        self.assertEqual(
            [s["target_d_mm"] for s in states],
            [
                2.45,
                2.55,
                2.65,
                2.75,
                2.85,
                2.95,
                3.20,
                2.95,
                2.85,
                2.75,
                2.65,
                2.55,
                2.45,
            ],
        )

    def test_stage6_block_s_configures_shallow_interleaved_heldout_grid(self):
        import apmd_stage6_local_heldout_dense_loop as heldout

        heldout.apply_work_zone_config("S")
        heldout.configure_dense_module()
        dense.configure_base_protocol()
        states = list(dense.iter_loop_states())

        expected_grid = [1.85, 1.95, 2.05, 2.15, 2.25, 2.35]
        self.assertEqual(dense.D_GRID_MM, expected_grid)
        self.assertEqual(dense.PRELOAD_D_MM, 2.60)
        self.assertEqual(base.D_TARGETS_MM, expected_grid)
        self.assertEqual(base.D_PRELOAD_BY_TARGET_MM, {d: 2.60 for d in expected_grid})
        self.assertEqual(base.D_PRELOAD_MM, 2.60)
        self.assertEqual(base.N_TRIALS, 3)
        self.assertEqual(base.TARGET_RECORD_S, 15.0)
        self.assertEqual(base.PRELOAD_RECORD_S, 30.0)
        self.assertEqual(base.SUMMARY_WINDOW_S, 5.0)
        self.assertEqual(
            base.SUMMARY_FILENAME,
            "local_heldout_dense_loop_6p1_S_state_summary.csv",
        )
        self.assertEqual(base.STATE_FILE_PREFIX, "local_heldout_dense_loop_6p1_S")
        self.assertEqual(base.CSV_PRINT_GLOB, "local_heldout_dense_loop_6p1_S*.csv")
        self.assertEqual(base.FIGURE_FILENAME, "local_heldout_dense_loop_6p1_S.png")
        self.assertEqual(base.FORMAL_EXPERIMENT_KEY, "\u9a8c\u8bc1 6.1-S")
        self.assertEqual(
            [s["target_d_mm"] for s in states],
            [
                1.85,
                1.95,
                2.05,
                2.15,
                2.25,
                2.35,
                2.60,
                2.35,
                2.25,
                2.15,
                2.05,
                1.95,
                1.85,
            ],
        )

    def test_stage6_block_h_configures_upper_interleaved_heldout_grid(self):
        import apmd_stage6_local_heldout_dense_loop as heldout

        heldout.apply_work_zone_config("H")
        heldout.configure_dense_module()
        dense.configure_base_protocol()
        states = list(dense.iter_loop_states())

        expected_grid = [3.45, 3.55, 3.65, 3.75, 3.85, 3.95]
        self.assertEqual(dense.D_GRID_MM, expected_grid)
        self.assertEqual(dense.PRELOAD_D_MM, 4.20)
        self.assertEqual(base.D_TARGETS_MM, expected_grid)
        self.assertEqual(base.D_PRELOAD_BY_TARGET_MM, {d: 4.20 for d in expected_grid})
        self.assertEqual(base.D_PRELOAD_MM, 4.20)
        self.assertEqual(base.N_TRIALS, 3)
        self.assertEqual(base.TARGET_RECORD_S, 15.0)
        self.assertEqual(base.PRELOAD_RECORD_S, 30.0)
        self.assertEqual(base.SUMMARY_WINDOW_S, 5.0)
        self.assertEqual(
            base.SUMMARY_FILENAME,
            "local_heldout_dense_loop_6p1_H_state_summary.csv",
        )
        self.assertEqual(base.STATE_FILE_PREFIX, "local_heldout_dense_loop_6p1_H")
        self.assertEqual(base.CSV_PRINT_GLOB, "local_heldout_dense_loop_6p1_H*.csv")
        self.assertEqual(base.FIGURE_FILENAME, "local_heldout_dense_loop_6p1_H.png")
        self.assertEqual(base.FORMAL_EXPERIMENT_KEY, "\u9a8c\u8bc1 6.1-H")
        self.assertEqual(
            [s["target_d_mm"] for s in states],
            [
                3.45,
                3.55,
                3.65,
                3.75,
                3.85,
                3.95,
                4.20,
                3.95,
                3.85,
                3.75,
                3.65,
                3.55,
                3.45,
            ],
        )


if __name__ == "__main__":
    unittest.main()
