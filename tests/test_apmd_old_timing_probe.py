import unittest

import apmd_same_d_different_f_path_pair as base


class ApmdOldTimingProbeTests(unittest.TestCase):
    def setUp(self):
        names = [
            "TARGET_RECORD_S",
            "PRELOAD_RECORD_S",
            "SUMMARY_WINDOW_S",
            "INTER_TRIAL_REST_S",
            "SUMMARY_FILENAME",
            "STATE_FILE_PREFIX",
            "CSV_PRINT_GLOB",
            "NEXT_MESSAGE",
            "registry_status_for_pairs",
        ]
        self._snapshot = {name: getattr(base, name) for name in names}
        self.addCleanup(self._restore_base_config)

    def _restore_base_config(self):
        for name, value in self._snapshot.items():
            setattr(base, name, value)

    def test_configures_old_timing_without_formal_registry(self):
        import apmd_same_d_different_f_old_timing_probe as probe

        probe.configure_protocol()

        self.assertEqual(base.TARGET_RECORD_S, 30.0)
        self.assertEqual(base.PRELOAD_RECORD_S, 15.0)
        self.assertEqual(base.SUMMARY_WINDOW_S, 8.0)
        self.assertEqual(base.INTER_TRIAL_REST_S, 60.0)
        self.assertEqual(
            base.SUMMARY_FILENAME,
            "same_d_different_f_old_timing_pair_summary.csv",
        )
        self.assertEqual(base.STATE_FILE_PREFIX, "same_d_different_f_old_timing")

        status, note = base.registry_status_for_pairs(3, 3, 3)
        self.assertEqual(status, "")
        self.assertIn("old-timing diagnostic", note)

    def test_plotter_accepts_old_timing_summary(self):
        import plot_apmd_same_d_different_f as plotter

        self.assertIn(
            "same_d_different_f_old_timing_pair_summary.csv",
            plotter.SUMMARY_FILENAMES,
        )


if __name__ == "__main__":
    unittest.main()
