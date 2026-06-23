import tempfile
import unittest
from pathlib import Path

from apmd_session_registry import SessionRecord, register_session


class ApmdSessionRegistryTests(unittest.TestCase):
    def test_replaces_tbd_with_first_formal_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            design = Path(tmp) / "APMD_FORMAL_EXPERIMENT_DESIGN.md"
            design.write_text(
                "\n".join(
                    [
                        "| 实验 | 采集脚本 | 作图/分析脚本 | 当前可用 session | formal rerun session |",
                        "|---|---|---|---|---|",
                        "| 实验 2.2 近似同位移/异力主动路径对实验 | `apmd_same_d_different_f_path_pair.py` | `plot_apmd_same_d_different_f.py` | legacy evidence | **next formal anchor:** TBD after running renamed script |",
                    ]
                ),
                encoding="utf-8",
            )

            changed = register_session(
                design,
                "实验 2.2",
                SessionRecord(
                    session_id="session_20260608_120000",
                    status="formal",
                    summary_filename="same_d_different_f_pair_summary.csv",
                    figure_filename="same_d_different_f_path_pair.png",
                ),
            )

            self.assertTrue(changed)
            text = design.read_text(encoding="utf-8")
            self.assertIn("formal: `session_20260608_120000`", text)
            self.assertIn("summary=`same_d_different_f_pair_summary.csv`", text)
            self.assertIn("figure=`same_d_different_f_path_pair.png`", text)
            self.assertNotIn("TBD after running renamed script", text)

    def test_appends_new_session_and_keeps_existing_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            design = Path(tmp) / "APMD_FORMAL_EXPERIMENT_DESIGN.md"
            design.write_text(
                "\n".join(
                    [
                        "| 实验 | 采集脚本 | 作图/分析脚本 | 当前可用 session | formal rerun session |",
                        "|---|---|---|---|---|",
                        "| 实验 2.2 近似同位移/异力主动路径对实验 | `apmd_same_d_different_f_path_pair.py` | `plot_apmd_same_d_different_f.py` | legacy evidence | formal: `session_20260608_120000`; summary=`same_d_different_f_pair_summary.csv`; figure=`same_d_different_f_path_pair.png` |",
                    ]
                ),
                encoding="utf-8",
            )

            changed = register_session(
                design,
                "实验 2.2",
                SessionRecord(
                    session_id="session_20260608_130000",
                    status="partial",
                    summary_filename="same_d_different_f_pair_summary.csv",
                    figure_filename="same_d_different_f_path_pair.png",
                    note="2/3 pairs",
                ),
            )

            self.assertTrue(changed)
            text = design.read_text(encoding="utf-8")
            self.assertIn("formal: `session_20260608_120000`", text)
            self.assertIn("<br>partial: `session_20260608_130000`", text)
            self.assertIn("note=2/3 pairs", text)

    def test_does_not_duplicate_existing_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            design = Path(tmp) / "APMD_FORMAL_EXPERIMENT_DESIGN.md"
            design.write_text(
                "\n".join(
                    [
                        "| 实验 | 采集脚本 | 作图/分析脚本 | 当前可用 session | formal rerun session |",
                        "|---|---|---|---|---|",
                        "| 实验 2.2 近似同位移/异力主动路径对实验 | `apmd_same_d_different_f_path_pair.py` | `plot_apmd_same_d_different_f.py` | legacy evidence | formal: `session_20260608_120000`; summary=`same_d_different_f_pair_summary.csv`; figure=`same_d_different_f_path_pair.png` |",
                    ]
                ),
                encoding="utf-8",
            )

            changed = register_session(
                design,
                "实验 2.2",
                SessionRecord(
                    session_id="session_20260608_120000",
                    status="formal",
                    summary_filename="same_d_different_f_pair_summary.csv",
                    figure_filename="same_d_different_f_path_pair.png",
                ),
            )

            self.assertFalse(changed)
            text = design.read_text(encoding="utf-8")
            self.assertEqual(text.count("session_20260608_120000"), 1)

    def test_updates_stage_session_record_column(self):
        with tempfile.TemporaryDirectory() as tmp:
            design = Path(tmp) / "APMD_FORMAL_EXPERIMENT_DESIGN.md"
            design.write_text(
                "\n".join(
                    [
                        "| 实验 | 采集脚本 | 作图/分析脚本 | session 记录 | 脚本状态 |",
                        "|---|---|---|---|---|",
                        "| 实验 3.1 近似同位移/异力路径对粗扫描 | `apmd_same_d_different_f_scan.py` | planned | TBD | ready |",
                    ]
                ),
                encoding="utf-8",
            )

            changed = register_session(
                design,
                "实验 3.1",
                SessionRecord(
                    session_id="session_20260608_140000",
                    status="formal",
                    summary_filename="same_d_different_f_scan_pair_summary.csv",
                    note="strong=2/9; same_d=8/9",
                ),
            )

            self.assertTrue(changed)
            text = design.read_text(encoding="utf-8")
            self.assertIn("formal: `session_20260608_140000`", text)
            self.assertIn("summary=`same_d_different_f_scan_pair_summary.csv`", text)
            self.assertIn("note=strong=2/9; same_d=8/9", text)
            self.assertNotIn("| TBD |", text)


if __name__ == "__main__":
    unittest.main()
