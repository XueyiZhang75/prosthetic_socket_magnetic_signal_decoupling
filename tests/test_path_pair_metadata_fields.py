import unittest

from stageI_plus_same_d_diff_f import metadata_fieldnames as iplus_metadata_fieldnames
from stageJ_plus_same_f_diff_d import metadata_fieldnames as jplus_metadata_fieldnames


class PathPairMetadataFieldTests(unittest.TestCase):
    def test_iplus_metadata_fields_include_stamp_head_traceability(self):
        names = set(iplus_metadata_fieldnames())

        self.assertTrue(
            {
                "sample_id",
                "magnet_id",
                "head_id",
                "force_calibration_id",
                "displacement_zero_id",
            }.issubset(names)
        )

    def test_jplus_metadata_fields_include_stamp_head_traceability(self):
        names = set(jplus_metadata_fieldnames())

        self.assertTrue(
            {
                "sample_id",
                "magnet_id",
                "head_id",
                "force_calibration_id",
                "displacement_zero_id",
            }.issubset(names)
        )


if __name__ == "__main__":
    unittest.main()
