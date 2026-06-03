"""Read raw MLX serial for 3 seconds and dump every line verbatim.

Use to verify what the QT Py is actually outputting, including any startup
banner that may not match Stage E's expected format.
"""

import time
import serial
from mlx_serial import find_mlx_port

port = find_mlx_port()
print(f"Opening {port} ...")
ser = serial.Serial(port, 115200, timeout=0.3)
time.sleep(1.0)
ser.reset_input_buffer()

print("--- raw lines for 3 s ---")
end = time.time() + 3.0
n = 0
while time.time() < end:
    line = ser.readline().decode(errors="ignore").strip()
    if not line:
        continue
    n += 1
    parts = line.split(",")
    print(f"  [{n:3d}] len={len(parts):2d}  {line!r}")
ser.close()
print(f"--- done, {n} non-empty lines ---")
