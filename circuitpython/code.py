import time
import board
import busio
import adafruit_mlx90393

# === sampling preset: change this one line to retune rate vs noise ===
# measured on QT Py M0 + MLX90393 via USB-CDC (Stage 1, 2026-05-12):
#   "low_noise" : 14.6 Hz, σ=(0.39, 0.42, 0.60) µT for (Bx,By,Bz)   <- static calibration
#   "balanced"  : 51.8 Hz, σ=(1.12, 1.13, 1.69) µT                  <- general purpose
#   "fast"      : 80.4 Hz, σ=(2.84, 2.85, 4.20) µT                  <- dynamic experiments
#   "fastest"   : 81.9 Hz, σ=(5.1,  5.1,  7.5)  µT  ⚠️ DO NOT USE
#                ↑ FILTER_0 leaves a ~500 µT differential bias in the mean;
#                  rate is the same as "fast" anyway (USB-CDC bottleneck).
PRESET = "low_noise"

PRESETS = {
    "low_noise": (adafruit_mlx90393.OSR_3, adafruit_mlx90393.FILTER_5),
    "balanced":  (adafruit_mlx90393.OSR_2, adafruit_mlx90393.FILTER_3),
    "fast":      (adafruit_mlx90393.OSR_1, adafruit_mlx90393.FILTER_1),
    "fastest":   (adafruit_mlx90393.OSR_0, adafruit_mlx90393.FILTER_0),
}
osr, flt = PRESETS[PRESET]

i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
try:
    sensor = adafruit_mlx90393.MLX90393(i2c, gain=adafruit_mlx90393.GAIN_1X)
except ValueError:
    sensor = adafruit_mlx90393.MLX90393(i2c, gain=adafruit_mlx90393.GAIN_1X, address=0x18)

sensor.oversampling = osr
sensor.filter = flt

print(f"MLX90393 ready, preset={PRESET}, OSR={osr}, FILTER={flt}")
print("t_ms,Bx_milliuT,By_milliuT,Bz_milliuT")

t0 = time.monotonic()
while True:
    try:
        bx, by, bz = sensor.magnetic
    except OSError:
        print("read_failed")
        continue
    t_ms = int((time.monotonic() - t0) * 1000)
    # integer-only: float .3f formatting is the dominant cost on SAMD21. host divides by 1000.
    print(f"{t_ms},{int(bx*1000)},{int(by*1000)},{int(bz*1000)}")
