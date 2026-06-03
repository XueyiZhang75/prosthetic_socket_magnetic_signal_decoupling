"""Diagnose QT Py CircuitPython boot output.

Opens the MLX serial port, sends Ctrl-C + Ctrl-D to trigger a soft reload,
and prints everything the board emits for 5 seconds. Use this when code.py
appears to be silently failing — the AttributeError / ImportError traceback
will show up right after the soft-reboot banner.
"""

import time
import serial

from mlx_serial import find_mlx_port

PORT = find_mlx_port()
print(f"Opening {PORT} at 115200 ...")
ser = serial.Serial(PORT, 115200, timeout=0.2)
time.sleep(0.5)

# Ctrl-C breaks any running loop; Ctrl-D in REPL = soft reboot
print("Sending Ctrl-C + Ctrl-D (soft reboot) ...\n")
ser.write(b"\x03")
time.sleep(0.2)
ser.write(b"\x04")

end = time.time() + 5.0
buf = b""
while time.time() < end:
    chunk = ser.read(4096)
    if chunk:
        buf += chunk
        try:
            print(chunk.decode("utf-8", errors="replace"), end="", flush=True)
        except Exception:
            pass

ser.close()
print("\n\n--- end of 5 s capture ---")
if not buf:
    print("(nothing received — board may be unresponsive; try unplugging/replugging the QT Py)")
