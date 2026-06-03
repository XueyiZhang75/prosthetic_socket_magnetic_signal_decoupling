import time
import board
import busio
import adafruit_mlx90393

# Fixed MLX90393 sampling configuration for all experiments.
#
# Measured on QT Py M0 + MLX90393 via USB-CDC:
#   OSR_1 + FILTER_1: about 80-96 Hz
#   single-sample sigma: about 2.9, 2.9, 4.2 uT for Bx, By, Bz
#
# Do not use OSR_0 + FILTER_0: earlier runs showed a large DC bias.
MLX_OSR = adafruit_mlx90393.OSR_1
MLX_FILTER = adafruit_mlx90393.FILTER_1

i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
try:
    sensor = adafruit_mlx90393.MLX90393(i2c, gain=adafruit_mlx90393.GAIN_1X)
except ValueError:
    sensor = adafruit_mlx90393.MLX90393(i2c, gain=adafruit_mlx90393.GAIN_1X, address=0x18)

sensor.oversampling = MLX_OSR
sensor.filter = MLX_FILTER
# RESOLUTION_18 gives 4x wider dynamic range than RESOLUTION_16.
# LSB coarsens from about 0.15 uT to about 0.6 uT. Required because the
# magnet pushed By past the RESOLUTION_16 wrap during Stage E compression
# (observed 2026-05-26). Quantization floor is still below signal scale.
sensor.resolution_x = adafruit_mlx90393.RESOLUTION_18
sensor.resolution_y = adafruit_mlx90393.RESOLUTION_18
sensor.resolution_z = adafruit_mlx90393.RESOLUTION_18

print(f"MLX90393 ready, fixed=fast, OSR={MLX_OSR}, FILTER={MLX_FILTER}, RES=18")
print("t_ms,Bx_milliuT,By_milliuT,Bz_milliuT")

t0 = time.monotonic()
while True:
    try:
        bx, by, bz = sensor.magnetic
    except OSError:
        print("read_failed")
        continue
    t_ms = int((time.monotonic() - t0) * 1000)
    # Integer-only output: float formatting is costly on SAMD21.
    # Host scripts divide by 1000 to recover uT.
    print(f"{t_ms},{int(bx*1000)},{int(by*1000)},{int(bz*1000)}")
