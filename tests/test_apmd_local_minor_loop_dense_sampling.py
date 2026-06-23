import unittest

import apmd_same_d_different_f_path_pair as base
import apmd_local_minor_loop_dense_sampling as dense


class ApmdLocalMinorLoopDenseSamplingTests(unittest.TestCase):
    def setUp(self):
        names = [
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
        ]
        self._snapshot = {name: getattr(base, name) for name in names}
        dense_names = [
            "WORK_ZONE_BLOCK",
            "D_GRID_MM",
            "PRELOAD_D_MM",
            "SUMMARY_FILENAME",
            "STATE_FILE_PREFIX",
            "CSV_PRINT_GLOB",
            "FIGURE_FILENAME",
        ]
        self._dense_snapshot = {name: getattr(dense, name) for name in dense_names}
        self.addCleanup(self._restore_base_config)

    def _restore_base_config(self):
        for name, value in self._snapshot.items():
            setattr(base, name, value)
        for name, value in self._dense_snapshot.items():
            setattr(dense, name, value)

    def test_loop_state_order_is_loading_preload_unloading(self):
        import apmd_local_minor_loop_dense_sampling as dense

        states = list(dense.iter_loop_states())

        self.assertEqual(len(states), 15)
        self.assertEqual(
            [s["target_d_mm"] for s in states],
            [
                3.00,
                3.10,
                3.20,
                3.30,
                3.40,
                3.50,
                3.60,
                3.80,
                3.60,
                3.50,
                3.40,
                3.30,
                3.20,
                3.10,
                3.00,
            ],
        )
        self.assertEqual([s["branch"] for s in states[:7]], ["loading"] * 7)
        self.assertEqual(states[7]["branch"], "preload")
        self.assertEqual([s["branch"] for s in states[8:]], ["unloading"] * 7)

    def test_configures_base_for_experiment_5_1B(self):
        import apmd_local_minor_loop_dense_sampling as dense

        dense.configure_base_protocol()

        self.assertEqual(
            base.D_TARGETS_MM,
            [3.00, 3.10, 3.20, 3.30, 3.40, 3.50, 3.60],
        )
        self.assertEqual(
            base.D_PRELOAD_BY_TARGET_MM,
            {
                3.00: 3.80,
                3.10: 3.80,
                3.20: 3.80,
                3.30: 3.80,
                3.40: 3.80,
                3.50: 3.80,
                3.60: 3.80,
            },
        )
        self.assertEqual(base.D_PRELOAD_MM, 3.80)
        self.assertEqual(base.N_TRIALS, 5)
        self.assertEqual(base.TARGET_RECORD_S, 15.0)
        self.assertEqual(base.PRELOAD_RECORD_S, 30.0)
        self.assertEqual(base.SUMMARY_WINDOW_S, 5.0)
        self.assertEqual(base.INTER_TRIAL_REST_S, 120.0)
        self.assertEqual(
            base.SUMMARY_FILENAME,
            "local_minor_loop_dense_5p1B_state_summary.csv",
        )
        self.assertEqual(base.STATE_FILE_PREFIX, "local_minor_loop_dense_5p1B")
        self.assertEqual(base.CSV_PRINT_GLOB, "local_minor_loop_dense_5p1B*.csv")
        self.assertEqual(base.FIGURE_FILENAME, "local_minor_loop_dense_5p1B.png")
        self.assertEqual(base.FORMAL_EXPERIMENT_KEY, "\u5b9e\u9a8c 5.1B")
        self.assertIsNone(base.F_HARD_LIMIT_N)

    def test_block_l_configures_lower_work_zone(self):
        import apmd_local_minor_loop_dense_sampling as dense

        dense.apply_work_zone_config("L")
        dense.configure_base_protocol()
        states = list(dense.iter_loop_states())

        expected_grid = [2.40, 2.50, 2.60, 2.70, 2.80, 2.90, 3.00]
        self.assertEqual(dense.D_GRID_MM, expected_grid)
        self.assertEqual(dense.PRELOAD_D_MM, 3.20)
        self.assertEqual(base.D_TARGETS_MM, expected_grid)
        self.assertEqual(base.D_PRELOAD_BY_TARGET_MM, {d: 3.20 for d in expected_grid})
        self.assertEqual(base.D_PRELOAD_MM, 3.20)
        self.assertEqual(base.N_TRIALS, 5)
        self.assertEqual(
            base.SUMMARY_FILENAME,
            "local_minor_loop_dense_5p1B_L_state_summary.csv",
        )
        self.assertEqual(base.STATE_FILE_PREFIX, "local_minor_loop_dense_5p1B_L")
        self.assertEqual(base.CSV_PRINT_GLOB, "local_minor_loop_dense_5p1B_L*.csv")
        self.assertEqual(base.FIGURE_FILENAME, "local_minor_loop_dense_5p1B_L.png")
        self.assertEqual(base.FORMAL_EXPERIMENT_KEY, "\u5b9e\u9a8c 5.1B-L")
        self.assertEqual(
            [s["target_d_mm"] for s in states],
            [
                2.40,
                2.50,
                2.60,
                2.70,
                2.80,
                2.90,
                3.00,
                3.20,
                3.00,
                2.90,
                2.80,
                2.70,
                2.60,
                2.50,
                2.40,
            ],
        )


if __name__ == "__main__":
    unittest.main()
