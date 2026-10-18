# -*- coding: utf-8 -*-
"""
make_bundle.py — LV_ESP32
Arma el ZIP para los usuarios (se sube a GitHub Releases, no al repo).

Lleva los VIs y la carpeta LV_Firmware\\ (el .exe con las herramientas nativas y
los binarios). No lleva Python, PlatformIO, el codigo de tools\\ ni las fuentes
del firmware: el usuario no compila ni instala nada.

Antes: tools\\build_exe.bat   (arma dist\\LV_Firmware\\)

    python tools\\make_bundle.py
    python tools\\make_bundle.py --stamp v3
"""
import argparse
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lv_core as core                                            # noqa: E402

DIST = os.path.join(core.REPO, "dist")
APP = os.path.join(DIST, "LV_Firmware")

# Carpetas (por nombre) que NUNCA entran
EXCLUDE_DIRS = {"LV_ESP32.wiki", ".git", ".github", "dist", "__pycache__", ".pio"}
# Rutas (desde la raiz del repo) que no entran: son de desarrollo
EXCLUDE_PATHS = ("Config/python", "Config/arduino-cli", "Config/flashtools",
                 "tools", "firmware")
EXCLUDE_EXT = {".pyc", ".lvlps", ".vip", ".zip"}
EXCLUDE_FILES = {".gitignore", "platformio.ini"}

# herramienta nativa por metodo de carga
NEEDS = {
    "esptool":     ["esptool/esptool.exe"],
    "dfu":         ["dfu-util/dfu-util.exe"],
    "avrdude":     ["avrdude/avrdude.exe", "avrdude/avrdude.conf"],
    "stlink_copy": [],
}


def human(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return "%.1f %s" % (n, u)
        n /= 1024.0
    return "%.1f TB" % n


def check(board_keys):
    """Verifica que el paquete vaya a servir de verdad. Aqui es donde se
    detecta que falta algo, no en la maquina del usuario."""
    problems = []
    if not os.path.isfile(os.path.join(APP, "LV_Firmware.exe")):
        problems.append("Falta dist\\LV_Firmware\\LV_Firmware.exe\n"
                        "   ->  corre tools\\build_exe.bat")
        return problems

    for b in board_keys:
        spec = core.BOARDS[b]
        f = os.path.join(APP, "firmware", "bin", spec["bin"])
        if not os.path.isfile(f):
            problems.append("Falta dist\\LV_Firmware\\firmware\\bin\\%s (para %s)\n"
                            "   ->  ver firmware\\COMPILAR.md y vuelve a correr "
                            "tools\\build_exe.bat" % (spec["bin"], b))
        for rel in NEEDS[spec["method"]]:
            t = os.path.join(APP, "Config", "flashtools", *rel.split("/"))
            if not os.path.isfile(t):
                problems.append("Falta dist\\LV_Firmware\\Config\\flashtools\\%s (para %s)\n"
                                "   ->  ver Config\\flashtools\\LEEME.md"
                                % (rel.replace("/", "\\"), b))
    return problems


def _skip_path(rel):
    r = rel.replace(os.sep, "/")
    return any(r == p or r.startswith(p + "/") for p in EXCLUDE_PATHS)


def build(stamp):
    name = "LV_ESP32_%s" % stamp
    zpath = os.path.join(DIST, name + ".zip")
    n, total = 0, 0
    print("Empaquetando en %s ..." % zpath)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        def add(full, arc):
            nonlocal n, total
            try:
                total += os.path.getsize(full)
                z.write(full, arc)
                n += 1
                if n % 500 == 0:
                    print("   %d archivos..." % n)
            except OSError as e:
                print("   (omitido %s: %s)" % (arc, e))

        # 1) los VIs y el resto del repo, sin lo de desarrollo
        for root, dirs, files in os.walk(core.REPO):
            rel_root = os.path.relpath(root, core.REPO)
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not _skip_path(
                os.path.normpath(os.path.join(rel_root, d)))]
            for f in files:
                if f in EXCLUDE_FILES or os.path.splitext(f)[1].lower() in EXCLUDE_EXT:
                    continue
                full = os.path.join(root, f)
                add(full, os.path.join(name, os.path.relpath(full, core.REPO)))

        # 2) el .exe con sus herramientas y binarios
        for root, dirs, files in os.walk(APP):
            for f in files:
                full = os.path.join(root, f)
                add(full, os.path.join(name, "LV_Firmware", os.path.relpath(full, APP)))

    print()
    print("Archivos      : %d" % n)
    print("Sin comprimir : %s" % human(total))
    print("ZIP           : %s" % human(os.path.getsize(zpath)))
    print("Salida        : %s" % zpath)
    return zpath


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boards", default=",".join(core.BOARDS),
                    help="placas cuyo binario y herramienta deben estar, separadas "
                         "por coma (por defecto, todas)")
    ap.add_argument("--stamp", default="v3", help="sufijo del nombre del zip")
    ap.add_argument("--force", action="store_true",
                    help="empaquetar aunque falten cosas")
    a = ap.parse_args()

    boards = [b.strip() for b in a.boards.split(",") if b.strip()]
    for b in boards:
        if b not in core.BOARDS:
            print("Placa desconocida: %s" % b)
            print("Disponibles: %s" % ", ".join(core.BOARDS))
            sys.exit(2)

    print("=" * 68)
    print("LV_ESP32 — armar el ZIP para usuarios")
    print("=" * 68)
    print("Placas : %s" % ", ".join(boards))
    print()

    problems = check(boards)
    if problems:
        print("PROBLEMAS:")
        for p in problems:
            print(" - " + p)
        print()
        if not a.force or not os.path.isdir(APP):
            print("Corrige eso y vuelve a intentar (--force solo salta lo que falte "
                  "dentro de LV_Firmware).")
            sys.exit(1)
        print("--force: se empaqueta de todos modos.\n")

    zpath = build(a.stamp)

    print()
    print("Para el usuario:")
    print("  1. Descomprimir el ZIP donde quiera")
    print("  2. Abrir LV_Firmware\\LV_Firmware.exe  (o desde el VI Firmware.vi)")
    print("  No necesita internet, ni Python, ni PlatformIO, ni permisos de admin.")
    print()
    print("Subelo a GitHub Releases, no al repositorio: %s" % os.path.basename(zpath))


if __name__ == "__main__":
    main()
