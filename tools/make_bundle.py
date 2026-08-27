# -*- coding: utf-8 -*-
"""
make_bundle.py — LV_ESP32
Arma el ZIP distribuible para los alumnos.

El repositorio de Git guarda FUENTES. Este script produce el PAQUETE: una
carpeta que ya trae Python, PyQt5, arduino-cli y el core de Arduino adentro,
para que el alumno la descomprima y funcione SIN internet y SIN instalar nada.

    Config\\python\\python.exe tools\\make_bundle.py
    Config\\python\\python.exe tools\\make_bundle.py --boards esp32_devkit,esp32_devkit_espnow
    Config\\python\\python.exe tools\\make_bundle.py --no-core     (paquete liviano)

Antes de correrlo, en TU maquina tiene que estar todo listo:
    1) Config\\python\\python.exe -m pip install PyQt5
    2) abrir lv_gui.bat -> Instalar dependencias  (para cada tarjeta que incluyas)

El resultado queda en  dist\\LV_ESP32_Portable_<fecha>.zip
"""

import argparse
import os
import shutil
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lv_core as core                                            # noqa: E402

DIST = os.path.join(core.REPO, "dist")

# Lo que NUNCA entra al paquete
EXCLUDE_DIRS = {
    "_legacy", ".git", ".github", "dist", "__pycache__",
    "build",                       # compilaciones locales
    "downloads",                   # cache de descargas de arduino-cli
}
EXCLUDE_EXT = {".pyc", ".lvlps", ".vip", ".zip"}
EXCLUDE_FILES = {".gitignore", "make_bundle.py"}


def human(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return "%.1f %s" % (n, u)
        n /= 1024.0
    return "%.1f TB" % n


def dir_size(path):
    t = 0
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            try:
                t += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return t


def check(board_keys, want_core):
    """Verifica que el paquete vaya a servir de verdad. Aqui es donde se
    detecta que falta algo, no en la maquina del alumno."""
    problems = []

    # PyQt5 dentro del Python del repo, no en el Python del sistema
    sp = os.path.join(core.REPO, "Config", "python", "Lib", "site-packages")
    if not (os.path.isdir(os.path.join(sp, "PyQt5")) or
            os.path.isdir(os.path.join(sp, "PySide6"))):
        problems.append("Falta PyQt5 en Config\\python\\Lib\\site-packages\\\n"
                        "   ->  Config\\python\\python.exe -m pip install PyQt5")

    if not os.path.isfile(os.path.join(core.CLI_HOME, core.EXE_NAME)):
        problems.append("Falta arduino-cli en Config\\arduino-cli\\\n"
                        "   ->  abre tools\\lv_gui.bat y presiona Instalar dependencias")

    if not core.sketch_ok():
        problems.append("Falta firmware\\firmware.ino")

    if want_core:
        for b in board_keys:
            if not core.core_installed(b):
                problems.append("Falta el core %s (para %s)\n"
                                "   ->  Instalar dependencias con esa tarjeta seleccionada"
                                % (core.BOARDS[b]["core"], b))
        have = core.libs_installed()
        need = set()
        for b in board_keys:
            need.update(core.board_libs(b))
        for lib in sorted(need):
            if lib not in have:
                problems.append("Falta la libreria '%s'" % lib)

    return problems


def build(board_keys, want_core, stamp):
    os.makedirs(DIST, exist_ok=True)
    name = "LV_ESP32_Portable_%s" % stamp
    zpath = os.path.join(DIST, name + ".zip")

    skip_dirs = set(EXCLUDE_DIRS)
    if not want_core:
        skip_dirs.add("data")      # el core de Arduino vive en arduino-cli/data

    n, total = 0, 0
    print("Empaquetando en %s ..." % zpath)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, dirs, files in os.walk(core.REPO):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for f in files:
                if f in EXCLUDE_FILES:
                    continue
                if os.path.splitext(f)[1].lower() in EXCLUDE_EXT:
                    continue
                full = os.path.join(root, f)
                rel = os.path.relpath(full, core.REPO)
                if rel.split(os.sep)[0] == "dist":
                    continue
                try:
                    total += os.path.getsize(full)
                    z.write(full, os.path.join(name, rel))
                    n += 1
                    if n % 500 == 0:
                        print("   %d archivos..." % n)
                except OSError as e:
                    print("   (omitido %s: %s)" % (rel, e))

    print()
    print("Archivos      : %d" % n)
    print("Sin comprimir : %s" % human(total))
    print("ZIP           : %s" % human(os.path.getsize(zpath)))
    print("Salida        : %s" % zpath)
    return zpath


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boards", default="esp32_devkit,esp32_devkit_espnow",
                    help="tarjetas que debe soportar el paquete, separadas por coma")
    ap.add_argument("--no-core", action="store_true",
                    help="no incluir el core de Arduino (paquete liviano, "
                         "el alumno necesitara internet una vez)")
    ap.add_argument("--stamp", default="v3",
                    help="sufijo del nombre del zip")
    ap.add_argument("--force", action="store_true",
                    help="empaquetar aunque falten cosas")
    a = ap.parse_args()

    boards = [b.strip() for b in a.boards.split(",") if b.strip()]
    for b in boards:
        if b not in core.BOARDS:
            print("Tarjeta desconocida: %s" % b)
            print("Disponibles: %s" % ", ".join(core.BOARDS))
            sys.exit(2)

    want_core = not a.no_core

    print("=" * 68)
    print("LV_ESP32 — armar paquete portable")
    print("=" * 68)
    print("Repositorio : %s" % core.REPO)
    print("Tarjetas    : %s" % ", ".join(boards))
    print("Core Arduino: %s" % ("incluido (funciona sin internet)"
                                if want_core else "NO incluido"))
    print()

    problems = check(boards, want_core)
    if problems:
        print("PROBLEMAS:")
        for p in problems:
            print(" - " + p)
        print()
        if not a.force:
            print("Corrige eso y vuelve a intentar (o usa --force).")
            sys.exit(1)
        print("--force: se empaqueta de todos modos.\n")

    if want_core:
        d = os.path.join(core.CLI_HOME, "data")
        if os.path.isdir(d):
            print("Tamano del core instalado: %s (comprime bastante)\n" % human(dir_size(d)))

    zpath = build(boards, want_core, a.stamp)

    print()
    print("Para el alumno:")
    print("  1. Descomprimir el ZIP donde quiera")
    print("  2. Abrir tools\\lv_gui.bat")
    print("  3. Cargar firmware")
    print("  No necesita internet, ni Python, ni Arduino IDE, ni permisos de admin.")
    print()
    print("Subelo a GitHub Releases, no al repositorio: %s" % os.path.basename(zpath))


if __name__ == "__main__":
    main()
