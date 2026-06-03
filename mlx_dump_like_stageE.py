"""Replicate Stage E's MLX serial open + read pattern exactly.

Opens with timeout=0.5 (Stage E's value), sleeps 1.0 s (Stage E's value),
then reads for 1.5 s and prints every line. If the first lines we get are
"MLX90393 ready..." / "t_ms,..." that means the serial open reset the board.
"""

import time
import serial
from mlx_serial import find_mlx_port

port = find_mlx_port()
print(f"Opening {port} with timeout=0.5 (Stage E pattern) ...")
ser = serial.Serial(port, 115200, timeout=0.5)
print(f"  DTR is held: {ser.dtr}  RTS: {ser.rts}")

print("sleep 1.0 s ...")
time.sleep(1.0)

print("reset_input_buffer + read 1.5 s ...")
ser.reset_input_buffer()
end = time.time() + 1.5
n = 0
while time.time() < end:
    line = ser.readline().decode(errors="ignore").strip()
    if not line:
        print("  (empty / timeout)")
        continue
    n += 1
    print(f"  [{n}] {line!r}")
ser.close()
print(f"\n--- got {n} non-empty lines in 1.5 s ---")
