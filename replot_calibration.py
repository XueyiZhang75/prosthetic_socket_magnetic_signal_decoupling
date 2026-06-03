"""Re-plot a calibration CSV using the current plot_fit style.

Use case: you ran force_calibration.py earlier, but now you've updated the
plot style (or just want a different filename). This reads any
force_calibration_*.csv that the calibration script produced and
regenerates the PNG.

Usage:
    python replot_calibration.py force_calibration_20260525_101932.csv
    python replot_calibration.py force_calibration_20260525_101932.csv out.png

If you don't pass a CSV path, it picks the most recent one in this folder.
"""

import csv
import re
import sys
from pathlib import Path

from force_calibration import plot_fit


HERE = Path(__file__).parent


def parse_csv(csv_path):
    """Read a force-calibration CSV and return (tare_offset, k, points).

    points = [(mass_g, mean_raw, std_raw, force_N), ...]   (same shape that
    plot_fit() expects).
    """
    tare_offset = None
    k = None
    points = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        # First parse the # header lines, then the data rows
        for row in reader:
            if not row:
                continue
            first = row[0].strip()
            # Metadata lines start with "#"
            if first.startswith("#"):
                line = ",".join(row)               # rejoin in case "=" had commas
                m = re.search(r"TARE_OFFSET\s*=\s*([-+]?\d+)", line)
                if m:
                    tare_offset = int(m.group(1))
                m = re.search(r"CALIBRATION_FACTOR\s*=\s*([-+]?\d*\.?\d+)", line)
                if m:
                    k = float(m.group(1))
                continue
            # Column header row
            if first == "mass_g":
                continue
            # Data row: mass_g, F_N, mean_raw, std_raw, delta_raw
            try:
                mass_g = float(row[0])
                force_n = float(row[1])
                mean_raw = float(row[2])
                std_raw = float(row[3])
            except (ValueError, IndexError):
                continue
            points.append((mass_g, mean_raw, std_raw, force_n))

    if tare_offset is None or k is None:
        raise ValueError(
            f"could not find TARE_OFFSET / CALIBRATION_FACTOR in {csv_path} "
            "(is this a force_calibration_*.csv file?)"
        )
    if not points:
        raise ValueError(f"no data rows found in {csv_path}")
    return tare_offset, k, points


def find_latest_csv():
    cands = sorted(HERE.glob("force_calibration_*.csv"))
    if not cands:
        sys.exit("  no force_calibration_*.csv found in this folder")
    return cands[-1]


def main():
    if len(sys.argv) >= 2:
        csv_path = Path(sys.argv[1])
        if not csv_path.is_absolute():
            csv_path = HERE / csv_path
    else:
        csv_path = find_latest_csv()
        print(f"  no CSV given, using latest: {csv_path.name}")

    if not csv_path.exists():
        sys.exit(f"  CSV not found: {csv_path}")

    if len(sys.argv) >= 3:
        png_path = Path(sys.argv[2])
        if not png_path.is_absolute():
            png_path = HERE / png_path
    else:
        png_path = csv_path.with_suffix(".png")

    print(f"reading  : {csv_path}")
    tare_offset, k, points = parse_csv(csv_path)
    print(f"  TARE_OFFSET        = {tare_offset}")
    print(f"  CALIBRATION_FACTOR = {k}")
    print(f"  n points           = {len(points)}")
    for p in points:
        mass_g, mean_raw, std_raw, force_n = p
        print(f"    m={mass_g:7.1f} g    F={force_n:.4f} N    "
              f"raw={mean_raw:.1f} +/- {std_raw:.1f}")

    print(f"writing  : {png_path}")
    plot_fit(points, tare_offset, k, png_path)
    print("done.")


if __name__ == "__main__":
    main()
