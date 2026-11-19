import argparse
import os
import sys

if not __package__:
    sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from hub.lang import LANGS, T
from hub.ui import QApplication, app_icon

from hub.hub import Hub, TOOLS


def main():
    ap = argparse.ArgumentParser(description="LV_ESP32 Instrument Hub")
    ap.add_argument("--port", default=None, help=T("puerto de la tarjeta (COM5, /dev/ttyUSB0...)"))
    ap.add_argument("--sim", action="store_true", help=T("usar el simulador, sin tarjeta"))
    ap.add_argument("--lang", choices=[k for k, _n in LANGS], default=None,
                    help="es / en")
    ap.add_argument("--tool", default=None, choices=[t[0] for t in TOOLS],
                    help=T("abrir directo un instrumento al conectar"))
    a = ap.parse_args()
    app = QApplication(sys.argv)
    app.setApplicationName("LV_ESP32 Instrument Hub")
    app.setStyle("Fusion")
    app.setWindowIcon(app_icon("hub"))
    hub = Hub(a.port, a.sim, a.tool)
    hub.show()
    rc = app.exec_()
    sys.exit(rc)


if __name__ == "__main__":
    main()
