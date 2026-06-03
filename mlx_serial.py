"""Cross-platform serial-port helper for the QT Py / MLX90393 stream.

Replaces the Mac-only `/dev/cu.usbmodem*` glob used in the original Stage 1/2/B/C
scripts. Works on Windows (COMx), macOS (/dev/cu.usbmodem*), and Linux
(/dev/ttyACM*) by enumerating ports through pyserial and matching common
USB-CDC keywords (QT Py / Adafruit / SAMD / CircuitPython / USB Serial Device).

Usage:
    from mlx_serial import find_mlx_port
    port = find_mlx_port()           # auto-detect, fall back to interactive
    port = find_mlx_port(prefer="COM7")   # if you already know it, skip search
"""

import sys

import serial.tools.list_ports

_KEYWORDS = (
    "adafruit",
    "qt py",
    "qtpy",
    "samd",
    "circuitpython",
    "usb serial",       # generic Windows description for CDC devices
    "usbmodem",         # macOS-style device-name fragment
    "ttyacm",           # Linux-style device-name fragment
)


def _describe(p):
    return " ".join(filter(None, [
        p.device, p.description, p.manufacturer, p.product, p.interface,
    ])).lower()


def find_mlx_port(prefer=None, interactive=True):
    """Return the COM/tty device path for the MLX90393 / QT Py board.

    Args:
        prefer: if given, return this string directly (e.g. "COM7"). Use when
            you already know the port and want to skip the scan.
        interactive: if auto-detect fails and stdin is a TTY, prompt the user
            to pick from the list. If False, raise SystemExit instead.

    Returns:
        str: the serial-port device string (e.g. "COM7", "/dev/cu.usbmodem...").
    """
    if prefer:
        return prefer

    ports = list(serial.tools.list_ports.comports())

    # First pass: keyword match in description/manufacturer/device name
    for p in ports:
        if any(k in _describe(p) for k in _KEYWORDS):
            return p.device

    # Nothing matched. Show what we did see, then either prompt or bail.
    if not ports:
        sys.exit(
            "No serial ports found at all. Is the QT Py plugged in and "
            "recognised by the OS? On Windows: check Device Manager."
        )

    print("Could not auto-detect MLX90393 / QT Py. Available ports:",
          file=sys.stderr)
    for i, p in enumerate(ports):
        print(f"  [{i}] {p.device:10s}  {p.description}", file=sys.stderr)

    if not (interactive and sys.stdin.isatty()):
        sys.exit("MLX90393 port not found (non-interactive).")

    while True:
        choice = input("Pick port index or full device name: ").strip()
        if not choice:
            continue
        if choice.upper().startswith("COM") or choice.startswith("/"):
            return choice
        try:
            return ports[int(choice)].device
        except (ValueError, IndexError):
            print("  invalid; try again", file=sys.stderr)
