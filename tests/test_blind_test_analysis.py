import math
import unittest

import numpy as np

from blind_test_analysis import (
    compute_metrics,
    filter_preload_points,
    fit_linear_ridge,
    predict_linear,
    summarize_state_rows,
)


class BlindTestAnalysisTests(unittest.TestCase):
    def test_linear_ridge_recovers_two_output_mapping(self):
        rng = np.random.default_rng(42)
        x = rng.normal(size=(30, 3))
        coef = np.array([[0.20, -0.10], [-0.05, 0.30], [0.40, 0.15]])
        y = x @ coef + np.array([1.5, 4.0])

        model = fit_linear_ridge(x, y, alpha=1e-9)
        pred = predict_linear(model, x)

        self.assertLess(float(np.max(np.abs(pred - y))), 1e-6)

    def test_compute_metrics_reports_mae_rmse_and_max_abs(self):
        metrics = compute_metrics(
            np.array([1.0, 2.0, 4.0]),
            np.array([1.5, 1.5, 5.0]),
        )

        self.assertAlmostEqual(metrics["mae"], 2.0 / 3.0)
        self.assertTrue(math.isclose(metrics["rmse"], math.sqrt(0.5)))
        self.assertAlmostEqual(metrics["max_abs"], 1.0)

    def test_summarize_state_rows_uses_head_window_by_state(self):
        rows = []
        for state, base_f in (("loading_target", 1.0), ("unloading_target", 2.0)):
            for t in (0.0, 1.0, 6.0):
                rows.append(
                    {
                        "state_label": state,
                        "trial": "1",
                        "pair_id": "1",
                        "t_rel_s": str(t),
                        "F_N": str(base_f + t),
                        "d_mm": "4.0",
                        "delta_Bx_uT": "10",
                        "delta_By_uT": "20",
                        "delta_Bz_uT": "30",
                        "Bmag_uT": "100",
                    }
                )

        points = summarize_state_rows(
            rows,
            session="session_test",
            source_file="example.csv",
            stage="blind",
            window_s=2.0,
        )

        self.assertEqual(len(points), 2)
        by_state = {p["state_label"]: p for p in points}
        self.assertAlmostEqual(by_state["loading_target"]["F_N"], 1.5)
        self.assertAlmostEqual(by_state["unloading_target"]["F_N"], 2.5)

    def test_summarize_state_rows_accepts_d_actual_and_missing_bmag(self):
        rows = [
            {
                "state_label": "blind_state",
                "trial": "1",
                "t_rel_s": "0.0",
                "F_N": "2.0",
                "d_mm": "",
                "d_actual_mm": "4.7",
                "delta_Bx_uT": "3",
                "delta_By_uT": "4",
                "delta_Bz_uT": "12",
                "Bmag_uT": "",
            }
        ]

        points = summarize_state_rows(
            rows,
            session="session_test",
            source_file="Blind_state_rep1.csv",
            stage="blind",
        )

        self.assertEqual(len(points), 1)
        self.assertAlmostEqual(points[0]["d_mm"], 4.7)
        self.assertAlmostEqual(points[0]["Bmag_uT"], 13.0)

    def test_filter_preload_points_removes_auxiliary_path_states(self):
        points = [
            {"state_label": "loading_target"},
            {"state_label": "preload_deep"},
            {"state_label": "return_target"},
            {"state_label": "blind_01_loading"},
        ]

        kept = filter_preload_points(points, include_preload=False)

        self.assertEqual(
            [p["state_label"] for p in kept],
            ["loading_target", "return_target", "blind_01_loading"],
        )
        self.assertEqual(
            filter_preload_points(points, include_preload=True),
            points,
        )


if __name__ == "__main__":
    unittest.main()
