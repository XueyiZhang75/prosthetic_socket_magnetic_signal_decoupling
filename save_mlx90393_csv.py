import serial
import csv
import glob
import sys
import time
from datetime import datetime


def find_port():
    candidates = sorted(glob.glob("/dev/cu.usbmodem*"))
    if not candidates:
        sys.exit("no /dev/cu.usbmodem* device found — is the board plugged in?")
    return candidates[0]


PORT = find_port()
BAUD = 115200

filename = "mlx90393_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv"

print(f"Opening serial port: {PORT}")
print(f"Saving to: {filename}")
print("Press Ctrl+C to stop recording.\n")

ser = serial.Serial(PORT, BAUD, timeout=2)
time.sleep(2)
ser.reset_input_buffer()

with open(filename, "w", newline="") as f:
    writer = csv.writer(f)

    # 统一表头：如果没有 status，就留空
    writer.writerow(["pc_time_s", "t_ms", "status", "Bx", "By", "Bz"])

    count = 0

    try:
        while True:
            line = ser.readline().decode("utf-8", errors="ignore").strip()

            if not line:
                continue

            # 跳过说明文字和表头
            if "MLX90393" in line or "read_failed" in line or line.startswith("t_ms"):
                print(line)
                continue

            parts = [p.strip() for p in line.split(",")]

            # 情况 1：Adafruit 代码输出 4 列：t_ms,Bx_uT,By_uT,Bz_uT
            if len(parts) == 4:
                try:
                    t_ms = int(parts[0])
                    status = ""
                    bx = float(parts[1])
                    by = float(parts[2])
                    bz = float(parts[3])
                except ValueError:
                    print("Skipped:", line)
                    continue

            # 情况 2：raw I2C 代码输出 5 列：t_ms,status,Bx_raw,By_raw,Bz_raw
            elif len(parts) == 5:
                try:
                    t_ms = int(parts[0])
                    status = parts[1]
                    bx = float(parts[2])
                    by = float(parts[3])
                    bz = float(parts[4])
                except ValueError:
                    print("Skipped:", line)
                    continue

            else:
                print("Skipped:", line)
                continue

            pc_time_s = time.time()
            writer.writerow([pc_time_s, t_ms, status, bx, by, bz])
            f.flush()

            count += 1
            print(f"{count}: t={t_ms}, status={status}, Bx={bx}, By={by}, Bz={bz}")

    except KeyboardInterrupt:
        print("\nRecording stopped.")

ser.close()
print(f"Saved {count} rows to {filename}")