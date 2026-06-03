import math
import tempfile
import unittest
from pathlib import Path

from identifiability_analysis import (
    PairColumnEstimate,
    assess_safety_consistency,
    estimate_pair_column,
    fit_local_jacobian,
    jacobian_metrics,
    local_jacobian_windows,
    pair_column_angle_check,
    parse_stage_d_summary,
)


class IdentifiabilityAnalysisTests(unittest.TestCase):
    def test_jacobian_metrics_detects_independent_columns(self):
        metrics = jacobian_metrics((3.0, 0.0, 0.0), (0.0, 4.0, 0.0))

        self.assertAlmostEqual(metrics.cosine_abs, 0.0)
        self.assertAlmostEqual(metrics.angle_deg, 90.0)
        self.assertAlmostEqual(metrics.min_singular, 3.0)
        self.assertAlmostEqual(metrics.condition_number, 4.0 / 3.0)
        self.assertEqual(metrics.verdict, "good")

    def test_jacobian_metrics_flags_nearly_collinear_columns(self):
        metrics = jacobian_metrics((1.0, 0.0, 0.0), (2.0, 0.01, 0.0))

        self.assertGreater(metrics.cosine_abs, 0.99)
        self.assertLess(metrics.angle_deg, 5.0)
        self.assertEqual(metrics.verdict, "ill-conditioned")

    def test_fit_local_jacobian_recovers_known_linear_model(self):
        rows = []
        for force in (-1.0, 0.0, 1.0):
            for disp in (-0.5, 0.5):
                rows.append(
                    {
                        "F_N": force,
                        "d_mm": disp,
                        "delta_Bx_uT": 10.0 + 2.0 * force - 3.0 * disp,
                        "delta_By_uT": -5.0 + 4.0 * force + 1.0 * disp,
                        "delta_Bz_uT": 1.0 - 1.0 * force + 2.0 * disp,
                    }
                )

        fit = fit_local_jacobian(rows, state_cols=("F_N", "d_mm"))

        self.assertEqual(fit.n_samples, 6)
        self.assertAlmostEqual(fit.j_force[0], 2.0)
        self.assertAlmostEqual(fit.j_force[1], 4.0)
        self.assertAlmostEqual(fit.j_force[2], -1.0)
        self.assertAlmostEqual(fit.j_displacement[0], -3.0)
        self.assertAlmostEqual(fit.j_displacement[1], 1.0)
        self.assertAlmostEqual(fit.j_displacement[2], 2.0)
        self.assertLess(fit.rmse_uT, 1e-9)

    def test_parse_stage_d_summary_and_flag_e_overrun(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary_path = Path(tmp) / "D_summary.txt"
            summary_path.write_text(
                "\n".join(
                    [
                        "Stage D safety-range summary",
                        "session: 20260525_191114",
                        "F_max observed in probe : +1.4324 N",
                        "d_max observed in probe : +4.9800 mm",
                        "verdict                 : OK",
                        "  F_max = 1.146 N    (= 0.8 * observed peak)",
                        "  d_max = 4.482 mm   (= 0.9 * observed peak)",
                    ]
                ),
                encoding="utf-8",
            )

            summary = parse_stage_d_summary(summary_path)
            check = assess_safety_consistency(
                summary,
                observed_force_max=3.0547,
                observed_displacement_max=4.29,
            )

        self.assertTrue(math.isclose(summary.recommended_force_n, 1.146))
        self.assertEqual(check.verdict, "fail")
        self.assertIn("exceeds recommended F_max", check.messages[0])

    def test_local_jacobian_windows_fit_multiple_work_points(self):
        rows = []
        for center_d in (1.0, 3.0):
            for force in (-0.2, 0.2):
                for disp_offset in (-0.1, 0.1):
                    disp = center_d + disp_offset
                    rows.append(
                        {
                            "F_N": force,
                            "d_mm": disp,
                            "delta_Bx_uT": 2.0 * force + 1.0 * disp,
                            "delta_By_uT": -1.0 * force + 3.0 * disp,
                            "delta_Bz_uT": 0.5 * force - 2.0 * disp,
                        }
                    )

        windows = local_jacobian_windows(
            rows,
            centers=(1.0, 3.0),
            half_width_mm=0.25,
            min_samples=4,
        )

        self.assertEqual(len(windows), 2)
        self.assertTrue(all(w.fit.n_samples == 4 for w in windows))
        self.assertAlmostEqual(windows[0].fit.j_force[0], 2.0)
        self.assertAlmostEqual(windows[1].fit.j_displacement[1], 3.0)

    def test_estimate_pair_column_uses_component_medians(self):
        rows = [
            {
                "delta_F_N": "-0.5",
                "delta_Bx_uT": "10",
                "delta_By_uT": "-20",
                "delta_Bz_uT": "40",
                "same_d_ok": "1",
                "force_split_ok": "1",
                "b_signal_ok": "1",
                "verdict": "strong",
            },
            {
                "delta_F_N": "-0.25",
                "delta_Bx_uT": "5",
                "delta_By_uT": "-12.5",
                "delta_Bz_uT": "25",
                "same_d_ok": "1",
                "force_split_ok": "1",
                "b_signal_ok": "1",
                "verdict": "strong",
            },
        ]

        estimate = estimate_pair_column(
            rows,
            stage_name="I+",
            denominator_col="delta_F_N",
            required_flags=("same_d_ok", "force_split_ok", "b_signal_ok"),
            output_unit="uT/N",
        )

        self.assertEqual(estimate.n_total, 2)
        self.assertEqual(estimate.n_usable, 2)
        self.assertAlmostEqual(estimate.vector[0], -20.0)
        self.assertAlmostEqual(estimate.vector[1], 45.0)
        self.assertAlmostEqual(estimate.vector[2], -90.0)

    def test_pair_column_angle_check_passes_independent_pair_evidence(self):
        force = PairColumnEstimate(
            stage_name="I+",
            n_total=3,
            n_usable=3,
            vector=(30.0, -90.0, 270.0),
            median_signal_uT=140.0,
            median_denominator=0.48,
            denominator_label="delta_F_N",
            output_unit="uT/N",
        )
        displacement = PairColumnEstimate(
            stage_name="J+",
            n_total=6,
            n_usable=4,
            vector=(-550.0, 3300.0, 540.0),
            median_signal_uT=820.0,
            median_denominator=0.24,
            denominator_label="delta_d_mm",
            output_unit="uT/mm",
        )

        check = pair_column_angle_check(force, displacement)

        self.assertEqual(check.verdict, "pass")
        self.assertIn("angle", check.messages[0])


if __name__ == "__main__":
    unittest.main()
