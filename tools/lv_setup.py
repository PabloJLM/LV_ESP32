# -*- coding: utf-8 -*-
"""
lv_setup.py — LV_ESP32
Todo por consola, sin interfaz grafica. Es la ruta que siempre funciona.

    Config\\python\\python.exe tools\\lv_setup.py doctor
    Config\\python\\python.exe tools\\lv_setup.py boards
    Config\\python\\python.exe tools\\lv_setup.py ports
    Config\\python\\python.exe tools\\lv_setup.py deps  --board esp32_wrover
    Config\\python\\python.exe tools\\lv_setup.py flash --board esp32_wrover --port COM5

Solo stdlib (pyserial es opcional, para el PING de verificacion).
Codigo de salida 0 si todo bien, distinto de 0 si algo fallo.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lv_core as core                                            # noqa: E402


def line(txt):
    print(txt, flush=True)


def step(pct, msg):
    if msg:
        print("[%3d%%] %s" % (int(pct), msg), flush=True)


def head(t):
    print("\n" + "=" * 66)
    print(t)
    print("=" * 66)


# ---------------------------------------------------------------------------
def cmd_boards(a):
    head("Tarjetas disponibles")
    for k, v in core.BOARDS.items():
        mark = "probada" if v["tested"] else "sin probar"
        print("  %-26s  %s" % (k, v["label"]))
        print("  %-26s  fqbn=%s  flags=%s  [%s]"
              % ("", v["fqbn"], v["flags"] or "-", mark))
    print("\nUsa el nombre de la izquierda en --board")
    return 0


def cmd_ports(a):
    head("Puertos serie")
    ports = core.list_ports()
    if not ports:
        print("  (ninguno)")
        print("\n  Conecta la tarjeta por USB. Si sigue sin salir, faltan los")
        print("  drivers CH340 o CP2102 segun el chip de tu placa.")
        return 2
    for p in ports:
        print("  %-8s  %s" % (p["port"], p["label"] or p["fqbn"] or ""))
    return 0


def cmd_doctor(a):
    head("Diagnostico")
    st = core.status(a.board)
    mark = lambda ok: "OK" if ok else "FALTA"

    print("  repositorio       : %s" % core.REPO)
    print("  sketch            : %-6s %s" % (mark(st["sketch"]), core.sketch_path()))
    print("  arduino-cli %-5s : %s" % (core.ACLI_VER, mark(st["cli"])))
    if st["cli"]:
        print("                      %s" % core.cli_path())
    if st.get("cli_sys"):
        print("  (hay uno en el PATH del sistema, NO se usa a proposito:")
        print("   %s)" % st["cli_sys"])
    print("  tarjeta           : %s" % core.BOARDS[a.board]["label"])
    print("  core %-13s: %s" % (core.BOARDS[a.board]["core"], mark(st["core"])))
    for lib, good in st["libs"].items():
        print("  lib  %-13s: %s" % (lib[:13], mark(good)))

    try:
        import serial                                             # noqa: F401
        print("  pyserial          : OK")
    except ImportError:
        print("  pyserial          : FALTA (solo afecta la verificacion por PING)")

    try:
        import PyQt5                                              # noqa: F401
        print("  PyQt5             : OK (la interfaz grafica puede abrir)")
    except ImportError:
        try:
            import PySide6                                        # noqa: F401
            print("  PySide6           : OK")
        except ImportError:
            print("  PyQt5             : FALTA (no importa si usas solo comandos)")

    print()
    cmd_ports(a)

    if not st["sketch"]:
        print("\n  -> No se encontro el sketch. Estas en la carpeta correcta?")
        return 1
    if core.all_ready(a.board):
        print("\n  Todo listo. Puedes cargar el firmware.")
        return 0
    print("\n  Falta instalar el entorno:")
    print("     tools\\lv_setup.py deps --board %s" % a.board)
    return 1


def cmd_deps(a):
    head("Instalar entorno para: %s" % core.BOARDS[a.board]["label"])
    print("La primera vez descarga arduino-cli (~35 MB) y el core (~1 GB).")
    print("Necesita internet y puede tardar de 5 a 15 minutos.\n")
    ok, msg = core.install_deps(a.board, line, step)
    print("\n" + ("OK: " if ok else "ERROR: ") + msg)
    return 0 if ok else 7


def cmd_flash(a):
    spec = core.BOARDS[a.board]
    head("Cargar firmware: %s" % spec["label"])

    if not core.cli_ready():
        print("Falta arduino-cli. Ejecuta primero:")
        print("   tools\\lv_setup.py deps --board %s" % a.board)
        return 3
    if not core.core_installed(a.board):
        print("Falta el core %s. Ejecuta primero:" % spec["core"])
        print("   tools\\lv_setup.py deps --board %s" % a.board)
        return 3

    port = a.port
    if not port:
        port = core.guess_port(a.board)
        if not port:
            print("No pude determinar el puerto. Usa --port COMx")
            print("Puertos vistos:")
            cmd_ports(a)
            return 2
        print("Puerto detectado: %s\n" % port)

    ok, msg = core.flash_all(a.board, port, line, step, verify=not a.no_verify)
    print("\n" + ("OK: " if ok else "ERROR: ") + msg)
    if ok:
        print("\nSiguiente paso, probar el protocolo contra la tarjeta:")
        print("   tools\\lv_probe.py --port %s" % port)
    return 0 if ok else 5


CMDS = {
    "boards": cmd_boards,
    "ports":  cmd_ports,
    "doctor": cmd_doctor,
    "deps":   cmd_deps,
    "flash":  cmd_flash,
}


def main():
    ap = argparse.ArgumentParser(
        prog="lv_setup.py",
        description="LV_ESP32 — preparar el entorno y cargar firmware, por consola")
    ap.add_argument("comando", choices=sorted(CMDS.keys()))
    ap.add_argument("--board", default=core.DEFAULT_BOARD,
                    help="perfil de tarjeta (ver: lv_setup.py boards)")
    ap.add_argument("--port", default=None, help="puerto serie, ej. COM5")
    ap.add_argument("--no-verify", action="store_true",
                    help="no hacer el PING despues de cargar")
    a = ap.parse_args()

    if a.board not in core.BOARDS:
        print("Tarjeta desconocida: %s" % a.board)
        print("Disponibles: %s" % ", ".join(core.BOARDS))
        return 6

    return CMDS[a.comando](a)


if __name__ == "__main__":
    sys.exit(main())
