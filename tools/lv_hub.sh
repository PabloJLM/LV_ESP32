#!/usr/bin/env sh
# ===========================================================================
#  lv_hub.sh - LV_ESP32 Instrument Hub (Linux/macOS, equivale a lv_hub.bat)
#  Funciona desde cualquier carpeta: todo se calcula desde la ubicacion del
#  script. La primera vez crea un entorno virtual en <repo>/.venv e instala
#  PyQt5, pyserial y esptool (necesita internet, una sola vez).
#  dfu-util y avrdude se instalan con el sistema: sudo apt install dfu-util avrdude
#
#     tools/lv_hub.sh                 lanzador
#     tools/lv_hub.sh --port /dev/ttyUSB0
#     tools/lv_hub.sh --sim               sin tarjeta
# ===========================================================================
TOOLS="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$TOOLS")"
VENV="$REPO/.venv"

if [ ! -x "$VENV/bin/python" ]; then
    command -v python3 >/dev/null 2>&1 || { echo "ERROR: falta python3 (sudo apt install python3 python3-venv)"; exit 3; }
    echo "Primera ejecucion: creando el entorno en $VENV ..."
    python3 -m venv "$VENV" || { echo "ERROR: no se pudo crear el venv (sudo apt install python3-venv)"; exit 3; }
fi
PY="$VENV/bin/python"

if ! "$PY" -c "import PyQt5, serial, esptool" >/dev/null 2>&1; then
    echo "Instalando PyQt5, pyserial y esptool (una sola vez, necesita internet)..."
    "$PY" -m pip install --disable-pip-version-check PyQt5 pyserial esptool \
        || { echo "ERROR: no se pudieron instalar las dependencias."; exit 4; }
fi

exec "$PY" "$TOOLS/lv_hub.py" "$@"
