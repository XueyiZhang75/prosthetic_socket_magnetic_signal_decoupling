import sys
import time
from collections import deque

import serial
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from mlx_serial import find_mlx_port

PORT = find_mlx_port()
BAUD = 115200
WINDOW_S = 10.0          # 显示窗口长度 (秒)
SHOW_MAGNITUDE = False   # True 时额外画 |B|

ser = serial.Serial(PORT, BAUD, timeout=0.05)
time.sleep(1)
ser.reset_input_buffer()

t_buf, bx_buf, by_buf, bz_buf = deque(), deque(), deque(), deque()
t0 = time.time()

fig, ax = plt.subplots(figsize=(10, 5))
(line_x,) = ax.plot([], [], label="Bx", color="tab:red")
(line_y,) = ax.plot([], [], label="By", color="tab:green")
(line_z,) = ax.plot([], [], label="Bz", color="tab:blue")
extra_lines = []
if SHOW_MAGNITUDE:
    (line_m,) = ax.plot([], [], label="|B|", color="black", linestyle="--", alpha=0.6)
    extra_lines.append(line_m)

ax.set_xlabel("time (s)")
ax.set_ylabel("B (µT)")
ax.legend(loc="upper left")
ax.grid(True, alpha=0.3)
ax.set_title(f"MLX90393 live  ({PORT})")


def drain_serial():
    while ser.in_waiting:
        raw = ser.readline().decode(errors="ignore").strip()
        if not raw or raw.startswith("MLX90393") or raw.startswith("t_ms"):
            continue
        parts = raw.split(",")
        if len(parts) != 4:
            continue
        try:
            bx, by, bz = float(parts[1]), float(parts[2]), float(parts[3])
        except ValueError:
            continue
        t = time.time() - t0
        t_buf.append(t)
        bx_buf.append(bx)
        by_buf.append(by)
        bz_buf.append(bz)
        while t_buf and t - t_buf[0] > WINDOW_S:
            t_buf.popleft()
            bx_buf.popleft()
            by_buf.popleft()
            bz_buf.popleft()


def update(_):
    drain_serial()
    if not t_buf:
        return (line_x, line_y, line_z, *extra_lines)
    t_now = t_buf[-1]
    line_x.set_data(t_buf, bx_buf)
    line_y.set_data(t_buf, by_buf)
    line_z.set_data(t_buf, bz_buf)
    all_y = list(bx_buf) + list(by_buf) + list(bz_buf)
    if SHOW_MAGNITUDE:
        mag = [(x * x + y * y + z * z) ** 0.5 for x, y, z in zip(bx_buf, by_buf, bz_buf)]
        extra_lines[0].set_data(t_buf, mag)
        all_y += mag
    ax.set_xlim(max(0, t_now - WINDOW_S), t_now + 0.2)
    margin = max(1.0, 0.1 * (max(all_y) - min(all_y)))
    ax.set_ylim(min(all_y) - margin, max(all_y) + margin)
    return (line_x, line_y, line_z, *extra_lines)


ani = FuncAnimation(fig, update, interval=50, blit=False, cache_frame_data=False)
try:
    plt.tight_layout()
    plt.show()
finally:
    ser.close()
