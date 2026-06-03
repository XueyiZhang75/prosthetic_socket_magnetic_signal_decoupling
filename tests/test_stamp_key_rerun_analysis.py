import csv
import tempfile
import unittest
from pathlib import Path

from stamp_key_rerun_analysis import analyze_pair_sessions, render_report


class StampKeyRerunAnalysisTests(unittest.TestCase):
    def _write_csv(self, path: Path, fieldnames, rows):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_analyzes_specified_iplus_and_jplus_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_csv(
                root / "session_i" / "Iplus_pair_summary.csv",
                [
                    "delta_F_N",
                    "delta_Bx_uT",
                    "delta_By_uT",
                    "delta_Bz_uT",
                    "delta_Bvec_uT",
                    "same_d_ok",
                    "force_split_ok",
                    "b_signal_ok",
                ],
                [
                    {
                        "delta_F_N": "0.50",
                        "delta_Bx_uT": "50",
                        "delta_By_uT": "0",
                        "delta_Bz_uT": "0",
                        "delta_Bvec_uT": "50",
                        "same_d_ok": "1",
                        "force_split_ok": "1",
                        "b_signal_ok": "1",
                    },
                    {
                        "delta_F_N": "0.40",
                        "delta_Bx_uT": "40",
                        "delta_By_uT": "0",
                        "delta_Bz_uT": "0",
                        "delta_Bvec_uT": "40",
                        "same_d_ok": "1",
                        "force_split_ok": "1",
                        "b_signal_ok": "1",
                    },
                ],
            )
            self._write_csv(
                root / "session_j" / "Jplus_pair_summary.csv",
                [
                    "delta_d_mm",
                    "delta_Bx_uT",
                    "delta_By_uT",
                    "delta_Bz_uT",
                    "delta_Bvec_uT",
                    "same_F_ok",
                    "disp_split_ok",
                    "b_signal_ok",
                ],
                [
                    {
                        "delta_d_mm": "0.25",
                        "delta_Bx_uT": "0",
                        "delta_By_uT": "250",
                        "delta_Bz_uT": "0",
                        "delta_Bvec_uT": "250",
                        "same_F_ok": "1",
                        "disp_split_ok": "1",
                        "b_signal_ok": "1",
                    },
                    {
                        "delta_d_mm": "0.20",
                        "delta_Bx_uT": "0",
                        "delta_By_uT": "200",
                        "delta_Bz_uT": "0",
                        "delta_Bvec_uT": "200",
                        "same_F_ok": "1",
                        "disp_split_ok": "1",
                        "b_signal_ok": "1",
                    },
                    {
                        "delta_d_mm": "0.30",
                        "delta_Bx_uT": "0",
                        "delta_By_uT": "300",
                        "delta_Bz_uT": "0",
                        "delta_Bvec_uT": "300",
                        "same_F_ok": "1",
                        "disp_split_ok": "1",
                        "b_signal_ok": "1",
                    },
                ],
            )

            result = analyze_pair_sessions(root, "session_i", "session_j")

            self.assertEqual(result.force.n_usable, 2)
            self.assertEqual(result.displacement.n_usable, 3)
            self.assertAlmostEqual(result.metrics.angle_deg, 90.0)
            self.assertEqual(result.verdict, "PASS")

            report = render_report(result)
            self.assertIn("session_i", report)
            self.assertIn("session_j", report)
            self.assertIn("Pair-column angle", report)


if __name__ == "__main__":
    unittest.main()
