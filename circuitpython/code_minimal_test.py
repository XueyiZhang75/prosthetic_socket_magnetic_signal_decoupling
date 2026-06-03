"""Minimal MLX90393 test for debugging.

Copy this to CIRCUITPY/code.py as a sanity check when the main code.py
appears silent. Prints once per second so you can verify USB-CDC alone works,
then enumerates the adafruit_mlx90393 attributes to find what RESOLUTION /
RES constants and resolution_* properties actually exist in your library.
"""

import time
import board
import busio
import adafruit_mlx90393

print("=== MLX90393 minimal boot test ===")
print(f"adafruit_mlx90393 module loaded OK")

# List all RES / RESOLUTION constants
res_attrs = [a for a in dir(adafruit_mlx90393)
             if "RES" in a.upper()]
print(f"Resolution-like constants: {res_attrs}")

i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
try:
    sensor = adafruit_mlx90393.MLX90393(i2c)
    print("Sensor opened at default address")
except Exception as e:
    print(f"Default address failed ({e}), trying 0x18")
    sensor = adafruit_mlx90393.MLX90393(i2c, address=0x18)
    print("Sensor opened at 0x18")

# Inspect resolution-related properties / methods on the sensor instance
sensor_res_attrs = [a for a in dir(sensor)
                    if "resol" in a.lower() or "res_" in a.lower()]
print(f"Sensor resolution attributes: {sensor_res_attrs}")

print("\n=== streaming Bx,By,Bz once per second (Ctrl-C to stop) ===")
while True:
    try:
        bx, by, bz = sensor.magnetic
        print(f"Bx={bx:8.1f}  By={by:8.1f}  Bz={bz:8.1f}  uT")
    except Exception as e:
        print(f"read failed: {e}")
    time.sleep(1.0)
