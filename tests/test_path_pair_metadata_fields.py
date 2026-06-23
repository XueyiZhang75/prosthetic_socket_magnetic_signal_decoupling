import unittest

from apmd_same_d_different_f_path_pair import (
    metadata_fieldnames as same_d_path_metadata_fieldnames,
)
from apmd_same_f_different_d_path_pair import (
    metadata_fieldnames as same_f_path_metadata_fieldnames,
)


class PathPairMetadataFieldTests(unittest.TestCase):
    def test_same_d_path_pair_metadata_fields_include_stamp_head_traceability(self):
        names = set(same_d_path_metadata_fieldnames())

        self.assertTrue(
            {
                "sample_id",
                "magnet_id",
                "head_id",
                "force_calibration_id",
                "displacement_zero_id",
            }.issubset(names)
        )

    def test_same_f_path_pair_metadata_fields_include_stamp_head_traceability(self):
        names = set(same_f_path_metadata_fieldnames())

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
