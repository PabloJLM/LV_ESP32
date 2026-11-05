#!/usr/bin/env sh
# ===========================================================================
#  lv_tester.sh - LV_ESP32 v3  (equivalente en Linux/macOS de lv_tester.bat)
#  Probador de comandos (botones + linea de comandos). Usa el mismo protocolo
#  que los VIs de LabVIEW. Cierra los VIs que tengan el puerto abierto.
#  Comparte el entorno <repo>/.venv con lv_gui.sh.
#
#     tools/lv_tester.sh                        elige el puerto en la ventana
#     tools/lv_tester.sh --port /dev/ttyUSB0    conecta solo
# ===========================================================================
TOOLS="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$TOOLS")"
VENV="$REPO/.venv"

# Un venv sin pip (p. ej. creado sin python3-venv) queda roto: se descarta.
if [ -x "$VENV/bin/python" ] && ! "$VENV/bin/python" -m pip --version >/dev/null 2>&1; then
    echo "El entorno $VENV esta incompleto (sin pip); recreandolo ..."
    rm -rf "$VENV"
fi

if [ ! -x "$VENV/bin/python" ]; then
    command -v python3 >/dev/null 2>&1 || { echo "ERROR: falta python3 (sudo apt install python3 python3-venv)"; exit 3; }
    echo "Primera ejecucion: creando el entorno en $VENV ..."
    python3 -m venv "$VENV" || { rm -rf "$VENV"; echo "ERROR: no se pudo crear el venv (sudo apt install python3-venv)"; exit 3; }
fi
PY="$VENV/bin/python"

if ! "$PY" -c "import PyQt5, serial" >/dev/null 2>&1; then
    echo "Instalando PyQt5 y pyserial (una sola vez, necesita internet)..."
    "$PY" -m pip install --disable-pip-version-check PyQt5 pyserial esptool \
        || { echo "ERROR: no se pudieron instalar las dependencias."; exit 4; }
fi

exec "$PY" "$TOOLS/lv_tester.py" "$@"
