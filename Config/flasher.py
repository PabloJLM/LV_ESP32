import sys
import subprocess
import os

# ---------------- CONFIG ----------------
BAUD = "921600"

# ---------------- VALIDACIÓN ----------------
if len(sys.argv) < 2:
    print("USO: flasher.py COMx")
    sys.exit(1)

PORT = sys.argv[1]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = os.path.join(BASE_DIR, "python", "python.exe")
FW_DIR = os.path.join(BASE_DIR, "firmware", "esp32")

# ---------------- UTIL ----------------
def run(cmd):
    print(">>", " ".join(cmd))
    p = subprocess.run(cmd, capture_output=True, text=True)
    print(p.stdout)
    if p.returncode != 0:
        print(p.stderr)
        sys.exit(p.returncode)

# ---------------- DETECTAR CHIP ----------------
print("Detectando ESP32...")

detect = subprocess.run(
    [PYTHON, "-m", "esptool", "--port", PORT, "chip_id"],
    capture_output=True,
    text=True
)

out = detect.stdout.upper()
print(out)

if "ESP32" not in out:
    print("ERROR: No se detectó un ESP32 compatible")
    sys.exit(2)

print("ESP32 detectado correctamente")

# ---------------- VALIDAR BIN ----------------
for f in ["bootloader.bin", "partitions.bin", "firmware.bin"]:
    if not os.path.exists(os.path.join(FW_DIR, f)):
        print(f"ERROR: Falta {f} en {FW_DIR}")
        sys.exit(3)

# ---------------- BORRAR FLASH ----------------
print("Borrando flash...")
run([
    PYTHON, "-m", "esptool",
    "--port", PORT,
    "--baud", BAUD,
    "erase_flash"
])

# ---------------- PROGRAMAR ----------------
print("Programando firmware...")

run([
    PYTHON, "-m", "esptool",
    "--port", PORT,
    "--baud", BAUD,
    "write_flash", "-z",
    "0x1000", os.path.join(FW_DIR, "bootloader.bin"),
    "0x8000", os.path.join(FW_DIR, "partitions.bin"),
    "0x10000", os.path.join(FW_DIR, "firmware.bin")
])

print("OK: Firmware cargado correctamente")
sys.exit(0)