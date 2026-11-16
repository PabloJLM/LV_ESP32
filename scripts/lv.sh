#!/usr/bin/env sh
# Lanzador para Linux/macOS.  Uso:  scripts/lv.sh <hub|camilab|flasher|tester|probe> [argumentos]
# Crea y usa el entorno <repo>/.venv (PyQt5, pyserial, esptool) la primera vez.
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$HERE")"
TOOLS="$REPO/tools"
VENV="$REPO/.venv"

TOOL="$1"
[ -n "$TOOL" ] && shift
case "$TOOL" in
    hub)     TARGET="$TOOLS/hub" ;;
    camilab) TARGET="$TOOLS/camilab" ;;
    flasher) TARGET="$TOOLS/flasher.py" ;;
    tester)  TARGET="$TOOLS/tester.py" ;;
    probe)   TARGET="$TOOLS/flasher.py"; set -- --tool probe "$@" ;;
    *) echo "Uso: scripts/lv.sh <hub|camilab|flasher|tester|probe> [argumentos]"; exit 2 ;;
esac

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

if ! "$PY" -c "import PyQt5, serial, esptool" >/dev/null 2>&1; then
    echo "Instalando PyQt5, pyserial y esptool (una sola vez, necesita internet)..."
    "$PY" -m pip install --disable-pip-version-check PyQt5 pyserial esptool \
        || { echo "ERROR: no se pudieron instalar las dependencias."; exit 4; }
fi

exec "$PY" "$TARGET" "$@"
