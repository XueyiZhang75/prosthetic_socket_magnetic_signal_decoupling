import serial
import time

PORT = "COM5"
BAUD = 9600

def try_command(ser, cmd, suffix_name, suffix):
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    payload = (cmd + suffix).encode("ascii")
    print(f"Sending {repr(cmd + suffix)} [{suffix_name}]")

    ser.write(payload)
    ser.flush()
    time.sleep(1.0)

    data = ser.read_all().decode("ascii", errors="ignore")
    print(f"Response: {repr(data)}")
    return data

print(f"Opening {PORT} at {BAUD} baud...")

ser = serial.Serial(
    PORT,
    BAUD,
    bytesize=8,
    parity="N",
    stopbits=1,
    timeout=2,
    rtscts=False,
    dsrdtr=False,
    xonxoff=False
)

time.sleep(1.0)

print("Port opened.")
print("Testing Mark-10 commands...\n")

for cmd in ["p", "n", "x", "?"]:
    print("=" * 40)
    print(f"Command: {cmd}")

    try_command(ser, cmd, "no terminator", "")
    try_command(ser, cmd, "CR", "\r")
    try_command(ser, cmd, "CRLF", "\r\n")

ser.close()
print("\nDone.")