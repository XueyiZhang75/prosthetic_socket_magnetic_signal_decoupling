from pathlib import Path
import tempfile
import unittest
from pathlib import Path

import pandas as pd

import apmd_stage5_build_model_dataset as builder


class Stage5DenseLoopDatasetTests(unittest.TestCase):
    def test_dense_loop_training_summaries_include_all_accepted_sessions(self):
        expected_sessions = {
            "session_20260615_112044",
            "session_20260615_143640",
            "session_20260618_092135",
            "session_20260618_135532",
            "session_20260622_112307",
            "session_20260622_132503",
            "session_20260622_143801",
            "session_20260622_151834",
            "session_20260622_162129",
            "session_20260623_152502",
            "session_20260623_162301",
            "session_20260623_172014",
            "session_20260623_182650",
            "session_20260623_200232",
        }

        configured_sessions = {path.parent.name for path in builder.DENSE_LOOP_SUMMARIES}

        self.assertEqual(configured_sessions, expected_sessions)

    def test_dense_loop_summary_rows_are_mapped_to_model_states(self):
        rows = [
            {
                "session_id": "session_test",
                "cycle": 1,
                "state_index": 1,
                "branch": "loading",
                "state_label": "loading_d_300",
                "path_mode": "loading_branch",
                "phase": "loading_dense",
                "d_target_mm": 3.0,
                "d_preload_mm": 3.8,
                "record_s": 15.0,
                "summary_window_s": 5.0,
                "n": 112,
                "d_median_mm": 2.98,
                "F_median_N": 6.49,
                "Bmag_median_uT": 9788.3,
                "Bx_median_uT": -572.2,
                "By_median_uT": 6199.9,
                "Bz_median_uT": 7553.3,
                "delta_Bx_median_uT": -95.8,
                "delta_By_median_uT": 3002.1,
                "delta_Bz_median_uT": 5044.5,
            },
            {
                "session_id": "session_test",
                "cycle": 1,
                "state_index": 15,
                "branch": "unloading",
                "state_label": "unloading_d_300",
                "path_mode": "unloading_branch",
                "phase": "unloading_dense",
                "d_target_mm": 3.0,
                "d_preload_mm": 3.8,
                "record_s": 15.0,
                "summary_window_s": 5.0,
                "n": 113,
                "d_median_mm": 3.0,
                "F_median_N": 4.81,
                "Bmag_median_uT": 10125.1,
                "Bx_median_uT": -570.1,
                "By_median_uT": 6440.2,
                "Bz_median_uT": 7790.4,
                "delta_Bx_median_uT": -93.7,
                "delta_By_median_uT": 3242.4,
                "delta_Bz_median_uT": 5281.5,
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "local_minor_loop_dense_5p1B_state_summary.csv"
            pd.DataFrame(rows).to_csv(path, index=False)

            states = builder._dense_loop_state_rows(path)

        self.assertEqual(len(states), 2)
        self.assertEqual(states[0]["experiment"], "5.1B local minor-loop dense sampling")
        self.assertEqual(states[0]["path_family"], "local_minor_loop_dense")
        self.assertEqual(states[0]["trial"], 1)
        self.assertEqual(states[0]["cycle_index"], 1)
        self.assertEqual(states[0]["state_index"], 1)
        self.assertEqual(states[0]["path_label"], "direct_loading")
        self.assertEqual(states[1]["path_label"], "return_unloading")
        self.assertAlmostEqual(states[0]["F_N"], 6.49)
        self.assertAlmostEqual(states[0]["d_mm"], 2.98)
        self.assertAlmostEqual(states[1]["delta_By_from_B0_uT"], 3242.4)
        self.assertEqual(states[0]["state_n_samples"], 112)

    def test_dense_loop_rows_can_be_filtered_to_accepted_cycles(self):
        rows = [
            {
                "session_id": "session_test_L",
                "cycle": 1,
                "state_index": 1,
                "branch": "loading",
                "state_label": "loading_d_240",
                "path_mode": "loading_branch",
                "phase": "loading_dense",
                "d_target_mm": 2.4,
                "d_preload_mm": 3.2,
                "record_s": 15.0,
                "summary_window_s": 5.0,
                "n": 112,
                "d_median_mm": 2.39,
                "F_median_N": 4.49,
                "Bmag_median_uT": 7500.0,
                "Bx_median_uT": -1.0,
                "By_median_uT": 2.0,
                "Bz_median_uT": 3.0,
            },
            {
                "session_id": "session_test_L",
                "cycle": 2,
                "state_index": 1,
                "branch": "loading",
                "state_label": "loading_d_240",
                "path_mode": "loading_branch",
                "phase": "loading_dense",
                "d_target_mm": 2.4,
                "d_preload_mm": 3.2,
                "record_s": 15.0,
                "summary_window_s": 5.0,
                "n": 112,
                "d_median_mm": 2.39,
                "F_median_N": 4.49,
                "Bmag_median_uT": 7500.0,
                "Bx_median_uT": -1.0,
                "By_median_uT": 2.0,
                "Bz_median_uT": 3.0,
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "local_minor_loop_dense_5p1B_L_state_summary.csv"
            pd.DataFrame(rows).to_csv(path, index=False)

            states = builder._dense_loop_state_rows(path, accepted_cycles={1})

        self.assertEqual(len(states), 1)
        self.assertEqual(states[0]["cycle_index"], 1)
        self.assertEqual(states[0]["experiment"], "5.1B-L Block L local minor-loop dense sampling")

    def test_dense_loop_rows_can_be_mapped_to_upper_work_zone(self):
        rows = [
            {
                "session_id": "session_test_H",
                "cycle": 1,
                "state_index": 1,
                "branch": "loading",
                "state_label": "loading_d_400",
                "path_mode": "loading_branch",
                "phase": "loading_dense",
                "d_target_mm": 4.0,
                "d_preload_mm": 4.2,
                "record_s": 15.0,
                "summary_window_s": 5.0,
                "n": 112,
                "d_median_mm": 3.89,
                "F_median_N": 18.0,
                "Bmag_median_uT": 9000.0,
                "Bx_median_uT": -1.0,
                "By_median_uT": 2.0,
                "Bz_median_uT": 3.0,
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "local_minor_loop_dense_5p1B_H_state_summary.csv"
            pd.DataFrame(rows).to_csv(path, index=False)

            states = builder._dense_loop_state_rows(path, accepted_cycles={1})

        self.assertEqual(len(states), 1)
        self.assertEqual(states[0]["experiment"], "5.1B-H upper work-zone local minor-loop dense sampling")
        self.assertEqual(states[0]["d_target_mm"], 4.0)


if __name__ == "__main__":
    unittest.main()
