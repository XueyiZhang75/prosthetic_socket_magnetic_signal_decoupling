import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


def _fake_rows():
    rows = []
    for d in (2.4, 2.6, 2.8, 3.0, 3.2, 3.4, 3.6):
        for trial in (1, 2, 3):
            rows.append(
                {
                    "d_target_mm": d,
                    "trial": trial,
                    "d_diff_mm": 0.0 if trial == 2 else 0.02,
                    "F_direct_N": d * 2.0 + trial * 0.01,
                    "F_return_N": d * 1.6 + trial * 0.01,
                    "delta_F_N": -(d * 0.2 + trial * 0.001),
                    "delta_Bvec_uT": d * 50.0 + trial,
                    "delta_Bx_uT": trial * 0.5,
                    "delta_By_uT": d * 40.0 + trial,
                    "delta_Bz_uT": d * 8.0 + trial,
                }
            )
    return rows


class CompleteFigurePanelTests(unittest.TestCase):
    def test_complete_figure_panel_c_is_magnetic_efficiency(self):
        import plot_apmd_same_d_different_f_scan as plotter

        captured = {}

        def capture_save(fig, _output_dirs, _filename):
            captured["fig"] = fig
            return []

        with TemporaryDirectory() as tmp_dir:
            with patch.object(plotter, "save_figure", side_effect=capture_save):
                plotter.plot_complete_workzone_figure(_fake_rows(), [Path(tmp_dir)])

        fig = captured["fig"]
        self.assertEqual(
            fig.axes[2].get_title(loc="left"),
            "Magnetic signal normalized by force split",
        )
        self.assertEqual(fig.axes[2].get_ylabel(), "Delta Bvec / |Delta F| (uT/N)")
        self.assertIn("c", [text.get_text() for text in fig.axes[2].texts])


if __name__ == "__main__":
    unittest.main()
