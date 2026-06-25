import unittest
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class Stage6PredictLocalHeldoutTests(unittest.TestCase):
    def test_heldout_summaries_include_all_accepted_test_only_sessions(self):
        import apmd_stage6_predict_local_heldout as stage6

        expected_sessions = {
            "session_20260615_160438",
            "session_20260618_161152",
            "session_20260622_173504",
            "session_20260622_180702",
            "session_20260622_185538",
            "session_20260623_201622",
            "session_20260623_204724",
        }

        configured_sessions = {path.parent.name for path in stage6.HELDOUT_SUMMARIES}

        self.assertEqual(configured_sessions, expected_sessions)

    def test_prepare_heldout_states_matches_stage5_state_schema(self):
        import apmd_stage6_predict_local_heldout as stage6

        raw = pd.DataFrame(
            [
                {
                    "session_id": "session_heldout",
                    "cycle": 1,
                    "state_index": 1,
                    "branch": "loading",
                    "state_label": "loading_d_305",
                    "path_mode": "loading_branch",
                    "phase": "loading_dense",
                    "d_target_mm": 3.05,
                    "d_preload_mm": 3.80,
                    "record_s": 15.0,
                    "summary_window_s": 5.0,
                    "n": 113,
                    "d_median_mm": 3.04,
                    "F_median_N": 6.31,
                    "Bmag_median_uT": 9000.0,
                    "Bx_median_uT": -1.0,
                    "By_median_uT": 2.0,
                    "Bz_median_uT": 3.0,
                    "delta_Bx_median_uT": 10.0,
                    "delta_By_median_uT": 20.0,
                    "delta_Bz_median_uT": 30.0,
                },
                {
                    "session_id": "session_heldout",
                    "cycle": 1,
                    "state_index": 7,
                    "branch": "preload",
                    "state_label": "preload_d_380",
                    "path_mode": "preload_loading",
                    "phase": "preload_dense",
                    "d_target_mm": 3.80,
                    "d_preload_mm": 3.80,
                    "record_s": 30.0,
                    "summary_window_s": 5.0,
                    "n": 113,
                    "d_median_mm": 3.79,
                    "F_median_N": 13.2,
                    "Bmag_median_uT": 11000.0,
                    "Bx_median_uT": -2.0,
                    "By_median_uT": 3.0,
                    "Bz_median_uT": 4.0,
                    "delta_Bx_median_uT": 11.0,
                    "delta_By_median_uT": 21.0,
                    "delta_Bz_median_uT": 31.0,
                },
                {
                    "session_id": "session_heldout",
                    "cycle": 1,
                    "state_index": 8,
                    "branch": "unloading",
                    "state_label": "unloading_d_305",
                    "path_mode": "unloading_branch",
                    "phase": "unloading_dense",
                    "d_target_mm": 3.05,
                    "d_preload_mm": 3.80,
                    "record_s": 15.0,
                    "summary_window_s": 5.0,
                    "n": 113,
                    "d_median_mm": 3.02,
                    "F_median_N": 4.2,
                    "Bmag_median_uT": 9300.0,
                    "Bx_median_uT": -3.0,
                    "By_median_uT": 4.0,
                    "Bz_median_uT": 5.0,
                    "delta_Bx_median_uT": 12.0,
                    "delta_By_median_uT": 22.0,
                    "delta_Bz_median_uT": 32.0,
                },
            ]
        )

        states = stage6.prepare_heldout_states(raw)

        self.assertEqual(len(states), 3)
        self.assertTrue((states["path_family"] == "local_minor_loop_dense").all())
        self.assertTrue((states["experiment"] == "6.1 local held-out dense-loop validation").all())
        self.assertEqual(states.iloc[0]["path_label"], "direct_loading")
        self.assertEqual(states.iloc[1]["path_label"], "preload_deep")
        self.assertEqual(states.iloc[2]["path_label"], "return_unloading")
        self.assertAlmostEqual(states.iloc[0]["F_N"], 6.31)
        self.assertAlmostEqual(states.iloc[0]["d_mm"], 3.04)
        self.assertAlmostEqual(states.iloc[0]["preload_extra_mm"], 0.75)
        self.assertAlmostEqual(states.iloc[0]["delta_Bvec_from_B0_uT"], (10.0**2 + 20.0**2 + 30.0**2) ** 0.5)

    def test_select_training_states_excludes_heldout_session(self):
        import apmd_stage6_predict_local_heldout as stage6

        df = pd.DataFrame(
            [
                {
                    "session_id": "session_train",
                    "path_family": "local_minor_loop_dense",
                    "F_N": 1.0,
                    "d_mm": 3.0,
                    "Bx_uT": 1.0,
                    "By_uT": 2.0,
                    "Bz_uT": 3.0,
                    "Bmag_uT": 4.0,
                },
                {
                    "session_id": "session_20260615_160438",
                    "path_family": "local_heldout_dense_loop",
                    "F_N": 2.0,
                    "d_mm": 3.1,
                    "Bx_uT": 1.0,
                    "By_uT": 2.0,
                    "Bz_uT": 3.0,
                    "Bmag_uT": 4.0,
                },
            ]
        )

        train = stage6.select_training_states(df, heldout_session_id="session_20260615_160438")

        self.assertEqual(len(train), 1)
        self.assertEqual(train.iloc[0]["session_id"], "session_train")
        self.assertNotIn("session_20260615_160438", set(train["session_id"]))

    def test_prepare_heldout_states_filters_to_primary_cycles_when_requested(self):
        import apmd_stage6_predict_local_heldout as stage6

        raw = pd.DataFrame(
            [
                {
                    "session_id": "session_block_l_heldout",
                    "cycle": 1,
                    "state_index": 1,
                    "branch": "loading",
                    "state_label": "loading_d_245",
                    "path_mode": "loading_branch",
                    "phase": "loading_dense",
                    "d_target_mm": 2.45,
                    "d_preload_mm": 3.20,
                    "record_s": 15.0,
                    "summary_window_s": 5.0,
                    "n": 113,
                    "d_median_mm": 2.44,
                    "F_median_N": 4.3,
                    "Bmag_median_uT": 8000.0,
                    "Bx_median_uT": -1.0,
                    "By_median_uT": 2.0,
                    "Bz_median_uT": 3.0,
                },
                {
                    "session_id": "session_block_l_heldout",
                    "cycle": 2,
                    "state_index": 1,
                    "branch": "loading",
                    "state_label": "loading_d_245",
                    "path_mode": "loading_branch",
                    "phase": "loading_dense",
                    "d_target_mm": 2.45,
                    "d_preload_mm": 3.20,
                    "record_s": 15.0,
                    "summary_window_s": 5.0,
                    "n": 113,
                    "d_median_mm": 2.44,
                    "F_median_N": 4.3,
                    "Bmag_median_uT": 8000.0,
                    "Bx_median_uT": -1.0,
                    "By_median_uT": 2.0,
                    "Bz_median_uT": 3.0,
                },
            ]
        )

        states = stage6.prepare_heldout_states(
            raw,
            summary_path=ROOT / "decouple_data" / "session_block_l_heldout" / "local_heldout_dense_loop_6p1_L_state_summary.csv",
            accepted_cycles={1},
        )

        self.assertEqual(len(states), 1)
        self.assertEqual(states.iloc[0]["cycle_index"], 1)
        self.assertEqual(states.iloc[0]["experiment"], "6.1-L Block L local held-out dense-loop validation")

    def test_prepare_heldout_states_maps_upper_work_zone(self):
        import apmd_stage6_predict_local_heldout as stage6

        raw = pd.DataFrame(
            [
                {
                    "session_id": "session_upper_heldout",
                    "cycle": 1,
                    "state_index": 1,
                    "branch": "loading",
                    "state_label": "loading_d_395",
                    "path_mode": "loading_branch",
                    "phase": "loading_dense",
                    "d_target_mm": 3.95,
                    "d_preload_mm": 4.20,
                    "record_s": 15.0,
                    "summary_window_s": 5.0,
                    "n": 113,
                    "d_median_mm": 3.89,
                    "F_median_N": 17.5,
                    "Bmag_median_uT": 9000.0,
                    "Bx_median_uT": -1.0,
                    "By_median_uT": 2.0,
                    "Bz_median_uT": 3.0,
                }
            ]
        )

        states = stage6.prepare_heldout_states(
            raw,
            summary_path=ROOT / "decouple_data" / "session_upper_heldout" / "local_heldout_dense_loop_6p1_H_state_summary.csv",
            accepted_cycles={1},
        )

        self.assertEqual(len(states), 1)
        self.assertEqual(states.iloc[0]["experiment"], "6.1-H upper work-zone local held-out dense-loop validation")


if __name__ == "__main__":
    unittest.main()
