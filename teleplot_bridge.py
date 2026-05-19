"""
teleplot_bridge.py — 把 MLX90393 串口数据转发给 Teleplot 实时显示。

固件不用改：本脚本读取板子的 CSV 输出
    t_ms,Bx_milliuT,By_milliuT,Bz_milliuT        (4 列, code.py 当前格式)
或   t_ms,status,Bx_raw,By_raw,Bz_raw             (5 列, raw I2C 变体)
然后以 Teleplot 的 UDP 遥测格式发到 127.0.0.1:47269。

用法
----
1. 在 VS Code 里装扩展 "Teleplot"（发布者 alexnesnes），装一次即可。
2. 跑本脚本，它会自动打开 Teleplot 面板（macOS，靠 AppleScript 模拟
   命令面板操作）：
       python teleplot_bridge.py
   想同时把数据存成 CSV：
       python teleplot_bridge.py --save
   也可指定串口：
       python teleplot_bridge.py --port /dev/cu.usbmodem101
   不想自动开面板：
       python teleplot_bridge.py --no-open

首次自动打开面板时，macOS 会要求给运行脚本的程序（终端 / VS Code）
"辅助功能 (Accessibility)" 权限：系统设置 > 隐私与安全性 > 辅助功能，
勾上对应的 App。没给权限也不影响数据转发，手动开面板即可。

注意：串口是独占的，跑本脚本时不要同时跑 save_mlx90393_csv.py / live_plot.py。
用 --save 就能一边看一边存。Ctrl+C 停止。
"""
import argparse
import glob
import socket
import subprocess
import sys
import time
from datetime import datetime

import serial

TELEPLOT_ADDR = ("127.0.0.1", 47269)
BAUD = 115200


def find_port():
    candidates = sorted(glob.glob("/dev/cu.usbmodem*"))
    if not candidates:
        sys.exit("no /dev/cu.usbmodem* device found — is the board plugged in?")
    return candidates[0]


def parse_line(line):
    """把一行解析成 (t_ms, status, bx, by, bz)，单位 µT；解析不了返回 None。

    4 列是固件的整数 milli-µT 输出，除以 1000 得 µT。
    5 列是 raw I2C 变体，原样保留（raw counts，不是 µT）。
    """
    parts = [p.strip() for p in line.split(",")]
    try:
        if len(parts) == 4:
            t_ms = int(parts[0])
            status = ""
            bx, by, bz = (int(p) / 1000.0 for p in parts[1:])
        elif len(parts) == 5:
            t_ms = int(parts[0])
            status = parts[1]
            bx, by, bz = (float(p) for p in parts[2:])
        else:
            return None
    except ValueError:
        return None
    return t_ms, status, bx, by, bz


def open_teleplot_panel():
    """在 VS Code 里自动打开 Teleplot 面板（仅 macOS）。

    VS Code 没有从命令行触发扩展命令的接口。早先版本用 AppleScript
    模拟命令面板打字，但中文输入法会拦截字母键导致失败。
    现在改为：keybindings.json 里把 teleplot.start 绑到 Cmd+Ctrl+Alt+T，
    本函数只发这个组合键 —— 带修饰键的快捷键不会被输入法拦截。
    需要给运行脚本的 App 开『辅助功能』权限；失败也不影响数据转发。
    """
    if sys.platform != "darwin":
        print("自动开面板仅支持 macOS；请手动在命令面板运行 'Start teleplot session'。")
        return
    script = '''
    tell application "Visual Studio Code" to activate
    delay 0.6
    tell application "System Events"
        keystroke "t" using {command down, control down, option down}
    end tell
    '''
    try:
        subprocess.run(["osascript", "-e", script],
                       check=True, capture_output=True, timeout=15)
        print("已打开 Teleplot 面板。")
    except Exception as e:
        print(f"自动开面板失败（{e}）；请手动在命令面板运行 'Start teleplot session'。")


def main():
    ap = argparse.ArgumentParser(description="MLX90393 串口 -> Teleplot UDP 桥接")
    ap.add_argument("--port", default=None, help="串口设备 (默认自动查找 /dev/cu.usbmodem*)")
    ap.add_argument("--save", action="store_true", help="同时把数据存成 CSV")
    ap.add_argument("--host", default="127.0.0.1", help="Teleplot 监听地址")
    ap.add_argument("--udp-port", type=int, default=47269, help="Teleplot UDP 端口")
    ap.add_argument("--no-open", action="store_true", help="不自动打开 Teleplot 面板")
    args = ap.parse_args()

    if not args.no_open:
        open_teleplot_panel()
        time.sleep(1.5)  # 等面板的 UDP 监听起来

    port = args.port or find_port()
    teleplot_addr = (args.host, args.udp_port)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ser = serial.Serial(port, BAUD, timeout=1)
    time.sleep(2)
    ser.reset_input_buffer()

    csv_file = None
    csv_writer = None
    if args.save:
        import csv
        fname = "mlx90393_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv"
        csv_file = open(fname, "w", newline="")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["pc_time_s", "t_ms", "status", "Bx", "By", "Bz"])
        print(f"Recording to: {fname}")

    print(f"Serial: {port}  ->  Teleplot UDP {teleplot_addr[0]}:{teleplot_addr[1]}")
    print("Open the Teleplot panel in VS Code. Press Ctrl+C to stop.\n")

    count = 0
    try:
        while True:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            # 板子的说明文字 / 表头 / 错误，原样转发到终端方便排查
            if ("MLX90393" in line or "read_failed" in line
                    or line.startswith("t_ms")):
                print(line)
                continue

            parsed = parse_line(line)
            if parsed is None:
                print("Skipped:", line)
                continue
            t_ms, status, bx, by, bz = parsed
            bmag = (bx * bx + by * by + bz * bz) ** 0.5

            # Teleplot UDP 遥测：name:timestamp_ms:value|g  ，一包多行
            # 时间戳用电脑墙钟 (Unix epoch 毫秒)，X 轴才会显示正确时刻；
            # 板子的相对 t_ms 仍存进 CSV。
            ts = int(time.time() * 1000)
            packet = "\n".join((
                f"Bx:{ts}:{bx:.3f}|g",
                f"By:{ts}:{by:.3f}|g",
                f"Bz:{ts}:{bz:.3f}|g",
                f"Bmag:{ts}:{bmag:.3f}|g",
            ))
            sock.sendto(packet.encode(), teleplot_addr)

            if csv_writer is not None:
                csv_writer.writerow([time.time(), t_ms, status, bx, by, bz])
                csv_file.flush()

            count += 1
            if count % 20 == 0:
                print(f"{count} samples  t={t_ms} ms  "
                      f"Bx={bx:.2f} By={by:.2f} Bz={bz:.2f} µT")
    except KeyboardInterrupt:
        print(f"\nStopped. Forwarded {count} samples.")
    finally:
        ser.close()
        sock.close()
        if csv_file is not None:
            csv_file.close()


if __name__ == "__main__":
    main()
