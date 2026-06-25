import unittest
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class Stage6LocalIdentifiabilityModelTests(unittest.TestCase):
    def test_error_bar_plot_uses_only_ridge_models_for_like_for_like_comparison(self):
        import apmd_stage6_compare_local_identifiability_models as stage6

        self.assertEqual(
            stage6.error_bar_model_order(),
            [
                "plain_magnetic_ridge",
                "lim_style_branch_ridge",
                "apmd_path_memory_ridge",
                "apmd_local_identifiability_ridge",
            ],
        )

    def test_fit_grid_includes_plain_baseline_as_first_column(self):
        import plot_apmd_stage6_model_fit_grid as fit_grid

        model_names = [model_name for model_name, *_ in fit_grid.MODELS]

        self.assertEqual(
            model_names,
            [
                "plain_magnetic_ridge",
                "lim_style_branch_ridge",
                "apmd_path_memory_ridge",
                "apmd_local_identifiability_ridge",
            ],
        )
        self.assertIn("2x4", fit_grid.OUT_PNG.name)
        self.assertIn("2x4", fit_grid.OUT_PDF.name)

    def test_stage6_mlp_specs_match_ridge_feature_families_without_rf_or_cnn(self):
        import apmd_stage6_compare_local_identifiability_models as stage6
        import apmd_stage6_neural_model_check as neural

        ridge_models = stage6.error_bar_model_order()
        expected_mlp_models = [name.replace("_ridge", "_mlp") for name in ridge_models]
        mlp_models = [name for name, *_ in neural.mlp_model_specs()]

        self.assertEqual(mlp_models, expected_mlp_models)
        self.assertTrue(all(name.endswith("_mlp") for name in mlp_models))
        self.assertFalse(any("random_forest" in name or "cnn" in name for name in mlp_models))
        self.assertEqual(neural.OUT_METRICS.name, "apmd_stage6_mlp_model_metrics.csv")

    def test_stage6_mlp_fit_grid_uses_four_mlp_models(self):
        import apmd_stage6_neural_model_check as neural
        import plot_apmd_stage6_mlp_fit_grid as fit_grid

        expected_models = [name for name, *_ in neural.mlp_model_specs()]
        actual_models = [model_name for model_name, *_ in fit_grid.MODELS]

        self.assertEqual(actual_models, expected_models)
        self.assertIn("2x4", fit_grid.OUT_PNG.name)
        self.assertIn("2x4", fit_grid.OUT_PDF.name)

    def test_add_local_identifiability_features_projects_delta_b_onto_local_axes(self):
        import apmd_stage6_compare_local_identifiability_models as stage6

        states = pd.DataFrame(
            [
                {
                    "F_N": 4.8,
                    "d_mm": 3.32,
                    "delta_Bx_from_B0_uT": 10.0,
                    "delta_By_from_B0_uT": 5.0,
                    "delta_Bz_from_B0_uT": 0.0,
                }
            ]
        )
        jf = pd.DataFrame(
            [
                {
                    "target_d_mm": 3.0,
                    "jF_x_uT_per_N": 0.0,
                    "jF_y_uT_per_N": 100.0,
                    "jF_z_uT_per_N": 0.0,
                },
                {
                    "target_d_mm": 3.4,
                    "jF_x_uT_per_N": 2.0,
                    "jF_y_uT_per_N": 0.0,
                    "jF_z_uT_per_N": 0.0,
                },
            ]
        )
        jd = pd.DataFrame(
            [
                {
                    "target_F_N": 1.5,
                    "jd_x_uT_per_mm": 100.0,
                    "jd_y_uT_per_mm": 0.0,
                    "jd_z_uT_per_mm": 0.0,
                },
                {
                    "target_F_N": 4.9,
                    "jd_x_uT_per_mm": 0.0,
                    "jd_y_uT_per_mm": 4.0,
                    "jd_z_uT_per_mm": 0.0,
                },
            ]
        )

        enriched = stage6.add_local_identifiability_features(states, jf, jd)

        self.assertEqual(enriched.iloc[0]["local_jF_target_d_mm"], 3.4)
        self.assertEqual(enriched.iloc[0]["local_jd_target_F_N"], 4.9)
        self.assertEqual(enriched.iloc[0]["local_zone_id"], "d340_F490")
        self.assertAlmostEqual(enriched.iloc[0]["local_p_F_uT"], 10.0)
        self.assertAlmostEqual(enriched.iloc[0]["local_p_d_uT"], 5.0)
        self.assertAlmostEqual(enriched.iloc[0]["local_residual_uT"], 0.0)
        self.assertAlmostEqual(enriched.iloc[0]["local_angle_deg"], 90.0)

    def test_add_local_identifiability_features_prefers_block_l_jf_for_block_l_states(self):
        import apmd_stage6_compare_local_identifiability_models as stage6

        states = pd.DataFrame(
            [
                {
                    "F_N": 4.0,
                    "d_mm": 2.8,
                    "source_state_csv": "decouple_data/session_x/local_minor_loop_dense_5p1B_L_state_summary.csv",
                    "experiment": "5.1B-L Block L local minor-loop dense sampling",
                    "delta_Bx_from_B0_uT": 0.0,
                    "delta_By_from_B0_uT": 12.0,
                    "delta_Bz_from_B0_uT": 0.0,
                }
            ]
        )
        jf = pd.DataFrame(
            [
                {
                    "target_d_mm": 2.8,
                    "work_zone_id": "Stage3_BlockM",
                    "jF_x_uT_per_N": 1.0,
                    "jF_y_uT_per_N": 0.0,
                    "jF_z_uT_per_N": 0.0,
                },
                {
                    "target_d_mm": 2.8,
                    "work_zone_id": "Block_L",
                    "jF_x_uT_per_N": 0.0,
                    "jF_y_uT_per_N": 2.0,
                    "jF_z_uT_per_N": 0.0,
                },
            ]
        )
        jd = pd.DataFrame(
            [
                {
                    "target_F_N": 4.3,
                    "jd_x_uT_per_mm": 1.0,
                    "jd_y_uT_per_mm": 0.0,
                    "jd_z_uT_per_mm": 0.0,
                }
            ]
        )

        enriched = stage6.add_local_identifiability_features(states, jf, jd)

        self.assertEqual(enriched.iloc[0]["local_jF_source_zone"], "Block_L")
        self.assertEqual(enriched.iloc[0]["local_zone_id"], "Block_L_d280_F430")
        self.assertAlmostEqual(enriched.iloc[0]["local_p_F_uT"], 12.0)

    def test_add_local_identifiability_features_prefers_upper_jf_for_upper_states(self):
        import apmd_stage6_compare_local_identifiability_models as stage6

        states = pd.DataFrame(
            [
                {
                    "F_N": 17.0,
                    "d_mm": 3.89,
                    "source_state_csv": "decouple_data/session_x/local_minor_loop_dense_5p1B_H_state_summary.csv",
                    "experiment": "5.1B-H upper work-zone local minor-loop dense sampling",
                    "delta_Bx_from_B0_uT": 0.0,
                    "delta_By_from_B0_uT": 0.0,
                    "delta_Bz_from_B0_uT": 15.0,
                }
            ]
        )
        jf = pd.DataFrame(
            [
                {
                    "target_d_mm": 3.8,
                    "work_zone_id": "Stage3_BlockM",
                    "jF_x_uT_per_N": 1.0,
                    "jF_y_uT_per_N": 0.0,
                    "jF_z_uT_per_N": 0.0,
                },
                {
                    "target_d_mm": 3.8,
                    "work_zone_id": "Block_H",
                    "jF_x_uT_per_N": 0.0,
                    "jF_y_uT_per_N": 0.0,
                    "jF_z_uT_per_N": 3.0,
                },
            ]
        )
        jd = pd.DataFrame(
            [
                {
                    "target_F_N": 4.9,
                    "jd_x_uT_per_mm": 1.0,
                    "jd_y_uT_per_mm": 0.0,
                    "jd_z_uT_per_mm": 0.0,
                }
            ]
        )

        enriched = stage6.add_local_identifiability_features(states, jf, jd)

        self.assertEqual(enriched.iloc[0]["local_jF_source_zone"], "Block_H")
        self.assertEqual(enriched.iloc[0]["local_zone_id"], "Block_H_d380_F490")
        self.assertAlmostEqual(enriched.iloc[0]["local_p_F_uT"], 15.0)


if __name__ == "__main__":
    unittest.main()
