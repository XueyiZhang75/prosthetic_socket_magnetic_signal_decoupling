"""Absolute minimum CircuitPython sanity check.

No sensor, no I2C, no third-party library — just prints once per second.
If THIS doesn't show up over serial, the USB-CDC console itself is broken
(boot.py mis-configured, OOM, wrong COM port, or driver issue).
"""

import time

i = 0
while True:
    print(f"hello {i}")
    i += 1
    time.sleep(1)
