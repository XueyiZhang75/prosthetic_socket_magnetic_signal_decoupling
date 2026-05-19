import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# 自动读取当前文件夹里最新的 mlx90393_*.csv 文件
csv_files = sorted(Path(".").glob("mlx90393_*.csv"), key=lambda p: p.stat().st_mtime)

if not csv_files:
    raise FileNotFoundError("No mlx90393_*.csv file found in current folder.")

filename = csv_files[-1]
print(f"Reading file: {filename}")

# 读取 CSV
df = pd.read_csv(filename)

# 清理列名，避免隐藏空格
df.columns = [c.strip() for c in df.columns]

# 转换数据类型
for col in ["t_ms", "Bx", "By", "Bz"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=["t_ms", "Bx", "By", "Bz"])

# 用 Arduino 时间生成相对时间，单位：秒
df["t_s"] = (df["t_ms"] - df["t_ms"].iloc[0]) / 1000.0

# 计算三轴磁场合量
df["B_mag"] = (df["Bx"]**2 + df["By"]**2 + df["Bz"]**2) ** 0.5

# 打印基本信息
print(df.head())
print("\nData summary:")
print(df[["Bx", "By", "Bz", "B_mag"]].describe())

# 画 Bx, By, Bz
plt.figure(figsize=(10, 5))
plt.plot(df["t_s"], df["Bx"], label="Bx")
plt.plot(df["t_s"], df["By"], label="By")
plt.plot(df["t_s"], df["Bz"], label="Bz")
plt.xlabel("Time (s)")
plt.ylabel("Magnetic field")
plt.title("MLX90393 Magnetic Field vs Time")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("mlx90393_Bxyz_vs_time.png", dpi=300)
plt.show()

# 画磁场合量
plt.figure(figsize=(10, 5))
plt.plot(df["t_s"], df["B_mag"], label="|B|")
plt.xlabel("Time (s)")
plt.ylabel("Magnetic field magnitude")
plt.title("MLX90393 Magnetic Field Magnitude vs Time")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("mlx90393_Bmag_vs_time.png", dpi=300)
plt.show()