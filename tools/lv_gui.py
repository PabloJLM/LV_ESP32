# -*- coding: utf-8 -*-
"""
lv_gui.py — LV_ESP32
Interfaz grafica que LabVIEW abre para todo lo que NO es instrumentacion:
instalar dependencias y cargar el firmware.

    lv_gui.py                 abre el lanzador con las dos herramientas
    lv_gui.py --tool deps     solo "Instalar dependencias"
    lv_gui.py --tool flash    solo "Cargar firmware"
    lv_gui.py --tool flash --port COM5 --board esp32_devkit

Desde LabVIEW (System Exec.vi, "wait until completion" = FALSE):
    "<repo>\\Config\\python\\pythonw.exe" "<repo>\\tools\\lv_gui.py" --tool flash

Funciona con PyQt5 o con PySide6, el que este instalado.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lv_core as core                                            # noqa: E402

# ---------------------------------------------------------------------------
# Qt: PyQt5 o PySide6, indistinto
# ---------------------------------------------------------------------------
try:
    from PyQt5.QtCore import Qt, QThread, pyqtSignal as SignalT
    from PyQt5.QtGui import QFont
    from PyQt5.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
                                 QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
                                 QProgressBar, QPushButton, QVBoxLayout, QWidget)
    QT_NAME = "PyQt5"
except ImportError:
    try:
        from PySide6.QtCore import Qt, QThread, Signal as SignalT
        from PySide6.QtGui import QFont
        from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
                                       QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
                                       QProgressBar, QPushButton, QVBoxLayout, QWidget)
        QT_NAME = "PySide6"
    except ImportError:
        sys.stderr.write(
            "\nFalta la libreria grafica. Instalala en el Python portable:\n\n"
            "    Config\\python\\python.exe -m pip install PyQt5\n\n")
        sys.exit(3)


# ---------------------------------------------------------------------------
# Estilo
# ---------------------------------------------------------------------------
QSS = """
/* Aspecto clasico de Windows: gris de sistema, bordes con relieve, sin
   esquinas redondeadas ni acentos de color. Funcional y sobrio. */
QWidget        { background:#f0f0f0; color:#000000;
                 font-family:"Segoe UI","Tahoma","MS Shell Dlg 2",sans-serif;
                 font-size:12px; }
QLabel#title   { font-size:15px; font-weight:bold; color:#000000; }
QLabel#sub     { color:#333333; }
QLabel#field   { color:#000000; }

QComboBox      { background:#ffffff; border:1px solid #7f9db9;
                 padding:3px 6px; min-height:18px; }
QComboBox:focus{ border:1px solid #3399ff; }
QComboBox QAbstractItemView { background:#ffffff; border:1px solid #7f9db9;
                 selection-background-color:#316ac5; selection-color:#ffffff; }

QLineEdit      { background:#ffffff; border:1px solid #7f9db9; padding:3px 5px; }
QLineEdit:focus{ border:1px solid #3399ff; }
QLineEdit:disabled { background:#f0f0f0; color:#6d6d6d; }

QPushButton    { background:#e1e1e1; border:1px solid #adadad;
                 padding:5px 16px; min-width:80px; }
QPushButton:hover    { background:#e5f1fb; border:1px solid #0078d7; }
QPushButton:pressed  { background:#cce4f7; border:1px solid #005499; }
QPushButton:disabled { background:#f0f0f0; color:#a0a0a0; border:1px solid #d0d0d0; }
QPushButton#ghost    { background:#e1e1e1; }

QProgressBar   { background:#ffffff; border:1px solid #7f9db9;
                 height:16px; text-align:center; color:#000000; }
QProgressBar::chunk { background:#06b025; }

QPlainTextEdit { background:#ffffff; border:1px solid #7f9db9;
                 color:#000000; padding:2px; }
QFrame#sep     { background:#a0a0a0; max-height:1px; border:none; }
"""


# ---------------------------------------------------------------------------
# Hilo de trabajo
# ---------------------------------------------------------------------------
class Worker(QThread):
    line = SignalT(str)
    step = SignalT(int, str)
    done = SignalT(bool, str)

    def __init__(self, fn):
        super().__init__()
        self._fn = fn

    def run(self):
        try:
            ok, msg = self._fn(self.line.emit,
                               lambda p, m: self.step.emit(int(p), m))
            self.done.emit(bool(ok), str(msg))
        except Exception as e:                                    # noqa: BLE001
            self.done.emit(False, "Error inesperado: %s" % e)


# ---------------------------------------------------------------------------
# Base con cabecera, log y barra
# ---------------------------------------------------------------------------
class ToolWindow(QWidget):
    def __init__(self, title, subtitle):
        super().__init__()
        self.worker = None
        self.setStyleSheet(QSS)
        self.setMinimumSize(660, 540)

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(24, 20, 24, 20)
        self.root.setSpacing(14)

        t = QLabel(title);    t.setObjectName("title")
        s = QLabel(subtitle); s.setObjectName("sub");  s.setWordWrap(True)
        self.root.addWidget(t)
        self.root.addWidget(s)

        sep = QFrame(); sep.setObjectName("sep"); sep.setFixedHeight(1)
        self.root.addWidget(sep)

        self.form = QGridLayout()
        self.form.setHorizontalSpacing(12)
        self.form.setVerticalSpacing(10)
        self.root.addLayout(self.form)

        self.bar = QProgressBar(); self.bar.setRange(0, 100); self.bar.setValue(0)
        self.root.addWidget(self.bar)

        self.status = QLabel("Listo para comenzar")
        self.status.setObjectName("sub")
        self.status.setWordWrap(True)
        self.root.addWidget(self.status)

        self.log = QPlainTextEdit(); self.log.setReadOnly(True)
        self.log.setFont(QFont("Consolas" if os.name == "nt" else "Monospace", 9))
        self.root.addWidget(self.log, 1)

    # --- helpers -----------------------------------------------------------
    def add_row(self, r, label, widget, extra=None):
        lab = QLabel(label); lab.setObjectName("field")
        self.form.addWidget(lab, r, 0)
        self.form.addWidget(widget, r, 1)
        if extra:
            self.form.addWidget(extra, r, 2)
        self.form.setColumnStretch(1, 1)

    def append(self, txt):
        self.log.appendPlainText(txt)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def on_step(self, pct, msg):
        self.bar.setValue(pct)
        if msg:
            self.status.setText(msg)

    def set_status(self, msg, kind="info"):
        color = {"ok": "#006600", "err": "#a00000", "info": "#333333"}[kind]
        self.status.setStyleSheet("color:%s;" % color)
        self.status.setText(msg)

    def start(self, fn, busy_widgets):
        for w in busy_widgets:
            w.setEnabled(False)
        self.bar.setValue(0)
        self.log.clear()
        self.set_status("Trabajando...", "info")
        self.worker = Worker(fn)
        self.worker.line.connect(self.append)
        self.worker.step.connect(self.on_step)
        self.worker.done.connect(lambda ok, m: self._finish(ok, m, busy_widgets))
        self.worker.start()

    def _finish(self, ok, msg, busy_widgets):
        for w in busy_widgets:
            w.setEnabled(True)
        self.bar.setValue(100 if ok else self.bar.value())
        self.set_status(msg, "ok" if ok else "err")
        self.append("\n=== %s ===" % ("OK" if ok else "ERROR"))
        self.append(msg)


# ---------------------------------------------------------------------------
# Herramienta 1 — dependencias
# ---------------------------------------------------------------------------
class DepsWindow(ToolWindow):
    def __init__(self, board=None):
        super().__init__(
            "Instalar dependencias",
            "Descarga las herramientas de Arduino que necesita el firmware. Se hace "
            "una sola vez y necesita internet.")

        self.cb_board = QComboBox()
        for k, v in core.BOARDS.items():
            self.cb_board.addItem(v["label"], k)
        if board:
            i = self.cb_board.findData(board)
            if i >= 0:
                self.cb_board.setCurrentIndex(i)
        self.add_row(0, "Placa", self.cb_board)

        self.btn_check = QPushButton("Ver estado"); self.btn_check.setObjectName("ghost")
        self.btn_go = QPushButton("Instalar dependencias")
        row = QHBoxLayout(); row.addWidget(self.btn_check); row.addStretch(1); row.addWidget(self.btn_go)
        self.root.insertLayout(4, row)   # justo debajo del formulario

        self.btn_check.clicked.connect(self.check)
        self.btn_go.clicked.connect(self.go)
        self.check()

    def board(self):
        return self.cb_board.currentData()

    def check(self):
        self.log.clear()
        b = self.board()
        st = core.status(b)
        mark = lambda ok: "OK" if ok else "FALTA"

        self.append("Firmware          : %s" % mark(st["sketch"]))
        self.append("Herramientas      : %s" % mark(st["cli"]))
        self.append("Soporte de placa  : %s" % mark(st["core"]))
        for lib, ok in st["libs"].items():
            self.append("%-18s: %s" % (lib[:18], mark(ok)))

        if not st["sketch"]:
            self.set_status("No se encontro el firmware.", "err")
        elif core.all_ready(b):
            self.set_status("Todo listo. Ya puedes cargar el firmware.", "ok")
        else:
            self.set_status("Faltan componentes. Presiona 'Instalar dependencias'.", "info")

    def go(self):
        b = self.board()
        self.start(lambda line, step: core.install_deps(b, line, step),
                   [self.btn_go, self.btn_check, self.cb_board])


# ---------------------------------------------------------------------------
# Herramienta 2 — cargar firmware
# ---------------------------------------------------------------------------
class FlashWindow(ToolWindow):
    def __init__(self, board=None, port=None):
        super().__init__(
            "Cargar firmware",
            "Selecciona la placa y el puerto, y presiona Cargar firmware.")

        self.cb_board = QComboBox()
        for k, v in core.BOARDS.items():
            self.cb_board.addItem(v["label"], k)
        if board:
            i = self.cb_board.findData(board)
            if i >= 0:
                self.cb_board.setCurrentIndex(i)
        self.add_row(0, "Placa", self.cb_board)

        self.cb_port = QComboBox()
        self.btn_rescan = QPushButton("Actualizar"); self.btn_rescan.setObjectName("ghost")
        self.add_row(1, "Puerto", self.cb_port, self.btn_rescan)

        self.btn_go = QPushButton("Cargar firmware")
        row = QHBoxLayout(); row.addStretch(1); row.addWidget(self.btn_go)
        self.root.insertLayout(4, row)   # justo debajo del formulario

        self.btn_rescan.clicked.connect(self.rescan)
        self.btn_go.clicked.connect(self.go)
        self.rescan(preferred=port)

    def board(self):
        return self.cb_board.currentData()

    def rescan(self, checked=False, preferred=None):
        self.cb_port.clear()
        ports = core.list_ports()
        if not ports:
            self.cb_port.addItem("(no hay puertos)", "")
            self.set_status("Conecta la tarjeta por USB y presiona Actualizar.", "err")
            self.btn_go.setEnabled(False)
            return
        for p in ports:
            txt = p["port"] + (("  —  " + p["label"]) if p["label"] else "")
            self.cb_port.addItem(txt, p["port"])
        target = preferred or core.guess_port(self.board(), ports)
        if target:
            i = self.cb_port.findData(target)
            if i >= 0:
                self.cb_port.setCurrentIndex(i)
        self.btn_go.setEnabled(True)
        self.set_status("%d puerto(s) encontrado(s)." % len(ports), "info")

    def go(self):
        b = self.board()
        p = self.cb_port.currentData()
        if not p:
            self.set_status("Selecciona un puerto.", "err")
            return

        self.start(lambda line, step: core.flash_all(b, p, line, step),
                   [self.btn_go, self.btn_rescan, self.cb_board, self.cb_port])


# ---------------------------------------------------------------------------
# Herramienta 3 -- probar el protocolo contra la tarjeta real
# ---------------------------------------------------------------------------
class ProbeWindow(ToolWindow):
    def __init__(self, port=None):
        super().__init__(
            "Probar tarjeta",
            "Manda los comandos del protocolo a la tarjeta y revisa las respuestas.")

        self.cb_port = QComboBox()
        self.btn_rescan = QPushButton("Actualizar"); self.btn_rescan.setObjectName("ghost")
        self.add_row(0, "Puerto", self.cb_port, self.btn_rescan)

        self.ed_dio = QLineEdit("4")
        self.add_row(1, "Pin digital", self.ed_dio)
        self.ed_adc = QLineEdit("34")
        self.add_row(2, "Pin analogico", self.ed_adc)
        self.ed_pwm = QLineEdit("13")
        self.add_row(3, "Pin PWM", self.ed_pwm)
        self.ed_peer = QLineEdit("")
        self.ed_peer.setPlaceholderText("opcional, solo para ESP-NOW")
        self.add_row(4, "Segunda placa", self.ed_peer)

        self.btn_go = QPushButton("Probar")
        row = QHBoxLayout(); row.addStretch(1); row.addWidget(self.btn_go)
        self.root.insertLayout(4, row)   # justo debajo del formulario

        self.btn_rescan.clicked.connect(self.rescan)
        self.btn_go.clicked.connect(self.go)
        self.rescan(preferred=port)

    def rescan(self, checked=False, preferred=None):
        self.cb_port.clear()
        ports = core.list_ports()
        if not ports:
            self.cb_port.addItem("(no hay puertos)", "")
            self.set_status("Conecta la tarjeta por USB y presiona Actualizar.", "err")
            self.btn_go.setEnabled(False)
            return
        for p in ports:
            txt = p["port"] + (("  --  " + p["label"]) if p["label"] else "")
            self.cb_port.addItem(txt, p["port"])
        target = preferred or core.guess_port(DEFAULT_BOARD, ports)
        if target:
            i = self.cb_port.findData(target)
            if i >= 0:
                self.cb_port.setCurrentIndex(i)
        self.btn_go.setEnabled(True)
        self.set_status("%d puerto(s) encontrado(s)." % len(ports), "info")

    def _int_or_none(self, text):
        text = text.strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None

    def go(self):
        p = self.cb_port.currentData()
        if not p:
            self.set_status("Selecciona un puerto.", "err")
            return
        peer = self.ed_peer.text().strip() or None
        dio, adc, pwm = (self._int_or_none(self.ed_dio.text()),
                         self._int_or_none(self.ed_adc.text()),
                         self._int_or_none(self.ed_pwm.text()))

        self.start(lambda line, step: core.run_probe(
                       p, line, step, peer_port=peer, dio=dio, adc=adc, pwm=pwm),
                   [self.btn_go, self.btn_rescan, self.cb_port,
                    self.ed_dio, self.ed_adc, self.ed_pwm, self.ed_peer])


DEFAULT_BOARD = core.DEFAULT_BOARD


# ---------------------------------------------------------------------------
# Lanzador
# ---------------------------------------------------------------------------
class Launcher(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(QSS)
        self.setMinimumSize(460, 260)
        self.kids = []

        v = QVBoxLayout(self)
        v.setContentsMargins(28, 26, 28, 26)
        v.setSpacing(12)

        t = QLabel("LV_ESP32"); t.setObjectName("title")
        s = QLabel("Preparar la tarjeta para usarla desde LabVIEW.")
        s.setObjectName("sub"); s.setWordWrap(True)
        v.addWidget(t); v.addWidget(s)

        sep = QFrame(); sep.setObjectName("sep"); sep.setFixedHeight(1)
        v.addWidget(sep)
        v.addSpacing(6)

        b1 = QPushButton("Instalar dependencias")
        b2 = QPushButton("Cargar firmware")
        for b in (b1, b2):
            b.setMinimumHeight(46)
            v.addWidget(b)
        v.addStretch(1)

        foot = QLabel("Tesla Lab · Universidad Galileo")
        foot.setObjectName("sub"); foot.setAlignment(Qt.AlignCenter)
        v.addWidget(foot)

        b1.clicked.connect(lambda: self.open(DepsWindow()))
        b2.clicked.connect(lambda: self.open(FlashWindow()))

    def open(self, w):
        w.setWindowTitle("LV_ESP32")
        w.show()
        self.kids.append(w)


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool", choices=["deps", "flash", "probe"], default=None)
    ap.add_argument("--board", default=None)
    ap.add_argument("--port", default=None)
    a = ap.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("LV_ESP32")

    if a.tool == "deps":
        w = DepsWindow(a.board)
    elif a.tool == "flash":
        w = FlashWindow(a.board, a.port)
    elif a.tool == "probe":
        w = ProbeWindow(a.port)
    else:
        w = Launcher()

    w.setWindowTitle("LV_ESP32")
    w.show()
    sys.exit(app.exec_() if QT_NAME == "PyQt5" else app.exec())


if __name__ == "__main__":
    main()
