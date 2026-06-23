import unittest

import pandas as pd


class DenseLoopCrossSessionValidationTests(unittest.TestCase):
    def test_prepare_dense_states_filters_dense_loop_and_adds_features(self):
        import apmd_stage5_dense_loop_cross_session_validation as validation

        df = pd.DataFrame(
            [
                {
                    "experiment": "5.1B local minor-loop dense sampling",
                    "path_family": "local_minor_loop_dense",
                    "session_id": "session_a",
                    "trial": 1,
                    "pair_id": 1,
                    "cycle_index": 1,
                    "state_index": 1,
                    "path_label": "direct_loading",
                    "F_N": 6.0,
                    "d_mm": 3.0,
                    "Bx_uT": 1.0,
                    "By_uT": 2.0,
                    "Bz_uT": 3.0,
                    "Bmag_uT": 4.0,
                    "delta_Bx_from_B0_uT": 0.1,
                    "delta_By_from_B0_uT": 0.2,
                    "delta_Bz_from_B0_uT": 0.3,
                },
                {
                    "experiment": "3.1 same-d/different-F work-zone scan",
                    "path_family": "same_d_different_F",
                    "session_id": "session_b",
                    "trial": 1,
                    "pair_id": 1,
                    "path_label": "direct_loading",
                    "F_N": 2.0,
                    "d_mm": 2.4,
                    "Bx_uT": 1.0,
                    "By_uT": 2.0,
                    "Bz_uT": 3.0,
                    "Bmag_uT": 4.0,
                    "delta_Bx_from_B0_uT": 0.1,
                    "delta_By_from_B0_uT": 0.2,
                    "delta_Bz_from_B0_uT": 0.3,
                },
            ]
        )

        dense = validation.prepare_dense_states(df)

        self.assertEqual(len(dense), 1)
        self.assertEqual(dense.iloc[0]["session_id"], "session_a")
        self.assertEqual(dense.iloc[0]["is_return"], 0)
        self.assertEqual(dense.iloc[0]["is_preload"], 0)
        self.assertAlmostEqual(dense.iloc[0]["delta_Bvec_from_B0_uT"], (0.1**2 + 0.2**2 + 0.3**2) ** 0.5)

    def test_directional_session_splits_hold_out_one_session_at_a_time(self):
        import apmd_stage5_dense_loop_cross_session_validation as validation

        df = pd.DataFrame(
            {
                "session_id": ["session_a", "session_a", "session_b", "session_b"],
                "F_N": [1.0, 2.0, 3.0, 4.0],
            }
        )

        splits = list(validation.directional_session_splits(df))

        self.assertEqual(len(splits), 2)
        for train_idx, test_idx, train_label, test_label in splits:
            train_sessions = set(df.iloc[train_idx]["session_id"])
            test_sessions = set(df.iloc[test_idx]["session_id"])
            self.assertEqual(len(test_sessions), 1)
            self.assertTrue(test_sessions.isdisjoint(train_sessions))
            self.assertIn("train", train_label)
            self.assertIn(test_label, test_sessions)


if __name__ == "__main__":
    unittest.main()
