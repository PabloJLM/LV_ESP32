import os
import sys

import core
import hub.cal as cal_mod
import hub.lang as hlang
from hub.calwin import CalWin
from hub.calwin import CalOhm
from hub.calwin import CalDiv
from hub.dev import DEFAULT_VREF, Device, SimDevice, VREF
from hub.lang import LANGS, T
from hub.ui import (
    QApplication, QFrame, QHBoxLayout, QIcon, QLabel, QPushButton, QSS, QSize, QTimer,
    QToolButton, QVBoxLayout, QWidget, Qt, Runner, combo, group, make_icon)

from hub.instrumentos.bode import Bode
from hub.instrumentos.digital import DigIn, DigOut
from hub.instrumentos.dmm import DMM
from hub.instrumentos.fgen import FGen
from hub.instrumentos.scope import Scope
from hub.instrumentos.vps import VPS


TOOLS = [
    ("dmm",    "DMM",     T("Multímetro digital"),          DMM,    ("ai",)),
    ("scope",  "Scope",   T("Osciloscopio"),                Scope,  ("ai",)),
    ("fgen",   "FGEN",    T("Generador de funciones"),      FGen,   ("out",)),
    ("vps",    "VPS",     T("Fuente variable"),             VPS,    ("out",)),
    ("bode",   "Bode",    T("Analizador de Bode"),          Bode,   ("out", "ai2")),
    ("digin",  "DigIn",   T("Lector digital"),              DigIn,  ("di",)),
    ("digout", "DigOut",  T("Escritor digital"),            DigOut, ("do",)),
    ("cal",    "Cal",     T("Calibración"),                 CalWin, ("ai",)),
    ("calohm", "CalΩ",    T("Calibrar óhmetro"),            CalOhm, ("ai",)),
    ("caldiv", "CalV",    T("Calibrar divisor (sonda)"),    CalDiv, ("ai",)),
]


HUB_QSS = QSS + """
QToolButton#tile   { background:transparent; color:#1a1a1a; border:2px solid transparent;
                     padding:6px 6px; font-size:12px; font-weight:bold; }
QToolButton#tile:hover   { background:#ececec;
                     border-color:#ffffff #707070 #707070 #ffffff; }
QToolButton#tile:pressed { background:#b8e6b8;
                     border-color:#707070 #ffffff #ffffff #707070; }
QToolButton#tile:disabled { color:#8a8a8a; }
QFrame#strip       { background:#e4e4e4; border:2px solid;
                     border-color:#ffffff #8a8a8a #8a8a8a #ffffff; }
"""


class Hub(QWidget):
    def __init__(self, port=None, sim=False, tool=None):
        QWidget.__init__(self)
        self.dev = Device()
        self.cal = cal_mod.Calibration()
        self.wins = {}
        self.connector = None
        self.setObjectName("panel")
        self.setStyleSheet(HUB_QSS)
        self.setWindowTitle("LV_ESP32 Instrument Launcher")
        self.setWindowIcon(QIcon(make_icon("scope", 64)))

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 8, 0, 8)
        root.setSpacing(8)

        g, f = group(T("Dispositivo"))
        self.cb_port = combo([])
        self.btn_scan = QPushButton(T("Actualizar"))
        self.btn_conn = QPushButton(T("Conectar"))
        self.btn_conn.setObjectName("run")
        self.btn_conn.setStyleSheet("min-width:110px;")
        self.cb_lang = combo(LANGS)
        self.cb_lang.setCurrentIndex(self.cb_lang.findData(hlang.LANG))
        self.lb_dev = QLabel(T("Sin conexión"))
        self.lb_dev.setObjectName("board")
        self.lb_cnt = QLabel("")
        self.lb_cnt.setObjectName("hint")
        f.addWidget(QLabel(T("Puerto")), 0, 0)
        f.addWidget(self.cb_port, 0, 1)
        f.addWidget(self.btn_scan, 0, 2)
        f.addWidget(self.btn_conn, 0, 3)
        f.addWidget(QLabel(T("Idioma")), 0, 4)
        f.addWidget(self.cb_lang, 0, 5)
        f.addWidget(QLabel(T("Tarjeta")), 1, 0)
        f.addWidget(self.lb_dev, 1, 1, 1, 5)
        f.addWidget(self.lb_cnt, 2, 1, 1, 5)
        f.setColumnStretch(1, 1)
        w = QHBoxLayout()
        w.setContentsMargins(8, 0, 8, 0)
        w.addWidget(g)
        root.addLayout(w)

        strip = QFrame()
        strip.setObjectName("strip")
        sl = QHBoxLayout(strip)
        sl.setContentsMargins(6, 6, 6, 6)
        sl.setSpacing(2)
        self.tiles = {}
        for key, short, name, cls, needs in TOOLS:
            tb = QToolButton()
            tb.setObjectName("tile")
            tb.setIcon(QIcon(make_icon(key, 64)))
            tb.setIconSize(QSize(44, 44))
            tb.setText(short)
            tb.setToolTip(name)
            tb.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            tb.setMinimumWidth(74)
            tb.clicked.connect(lambda _c=False, k=key: self.open_tool(k))
            sl.addWidget(tb)
            self.tiles[key] = (tb, needs)
        w = QHBoxLayout()
        w.setContentsMargins(8, 0, 8, 0)
        w.addWidget(strip)
        root.addLayout(w)

        self.lb_status = QLabel(T("Elige el puerto y presiona Conectar. Sin tarjeta, usa "
                                  "Simulador."))
        self.lb_status.setObjectName("status")
        self.lb_status.setWordWrap(True)
        w = QHBoxLayout()
        w.setContentsMargins(8, 0, 8, 0)
        w.addWidget(self.lb_status)
        root.addLayout(w)

        self.btn_scan.clicked.connect(lambda: self.scan())
        self.btn_conn.clicked.connect(self.toggle)
        self.cb_lang.currentIndexChanged.connect(self.set_lang)
        self.scan(port)
        self._tiles()
        if sim:
            i = self.cb_port.findData("SIM")
            self.cb_port.setCurrentIndex(i)
        if port or sim:
            QTimer.singleShot(100, self.toggle)
        self._autotool = tool

    def scan(self, prefer=None):
        old = prefer or self.cb_port.currentData()
        self.cb_port.clear()
        for p in core.list_ports():
            self.cb_port.addItem(p["port"] + ("  -  " + p["label"] if p["label"] else ""),
                                 p["port"])
        self.cb_port.addItem(T("Simulador (sin tarjeta)"), "SIM")
        if old:
            i = self.cb_port.findData(old)
            if i < 0 and prefer:
                self.cb_port.insertItem(0, prefer, prefer)
                i = 0
            self.cb_port.setCurrentIndex(max(0, i))

    def set_status(self, text, kind=""):
        self.lb_status.setText(text)
        self.lb_status.setProperty("kind", kind)
        self.lb_status.style().unpolish(self.lb_status)
        self.lb_status.style().polish(self.lb_status)

    def toggle(self):
        if self.dev.connected:
            self.disconnect_dev()
            return
        port = self.cb_port.currentData()
        if not port:
            self.set_status(T("No hay puerto seleccionado."), "err")
            return
        dev = SimDevice() if port == "SIM" else Device()
        dev.cal = self.cal
        self.btn_conn.setEnabled(False)
        self.cb_port.setEnabled(False)
        self.set_status(T("Conectando con %s (unos 2 s)...") % port, "")

        def job(r):
            dev.open(port)
            r.post(dev)

        self.connector = Runner(job)
        self.connector.posted.connect(self._connected)
        self.connector.failed.connect(self._conn_failed)
        self.connector.start()

    def _connected(self, dev):
        self.dev = dev
        self.btn_conn.setEnabled(True)
        self.btn_conn.setText(T("Desconectar"))
        self.btn_conn.setObjectName("stop")
        self.btn_conn.setStyle(self.btn_conn.style())
        self.lb_dev.setText(dev.describe())
        self.lb_cnt.setText(dev.counts())
        self.setWindowTitle("LV_ESP32 Instrument Launcher - " + dev.board_name)
        self.set_status(T("Conectado. Abre un instrumento."), "ok")
        self._tiles()
        for w in list(self.wins.values()):
            w.device_changed()
        if self._autotool:
            self.open_tool(self._autotool)
            self._autotool = None

    def _conn_failed(self, msg):
        self.btn_conn.setEnabled(True)
        self.cb_port.setEnabled(True)
        self.set_status(msg, "err")

    def disconnect_dev(self):
        for w in list(self.wins.values()):
            w.stop_wait()
        self.dev.close()
        self.dev = Device()
        for w in list(self.wins.values()):
            w.device_changed()
        self.btn_conn.setText(T("Conectar"))
        self.btn_conn.setObjectName("run")
        self.btn_conn.setStyle(self.btn_conn.style())
        self.cb_port.setEnabled(True)
        self.lb_dev.setText(T("Sin conexión"))
        self.lb_cnt.setText("")
        self.setWindowTitle("LV_ESP32 Instrument Launcher")
        self.set_status(T("Desconectado."), "")
        self._tiles()

    def set_lang(self, _i):
        lang = self.cb_lang.currentData()
        if lang == hlang.LANG:
            return
        hlang.save(lang)
        args = [os.path.dirname(os.path.abspath(__file__)), "--lang", lang]
        if self.dev.connected:
            args += ["--sim"] if self.dev.simulated else ["--port", self.dev.port]
        for w in list(self.wins.values()):
            w.close()
        self.dev.close()
        import subprocess
        subprocess.Popen([sys.executable] + args)
        QApplication.quit()

    def _ok_for(self, needs):
        d = self.dev
        if not d.connected:
            return False, T("Conecta una tarjeta")
        for n in needs:
            if n == "ai" and d.n["ai"] < 1:
                return False, T("La tarjeta no tiene entradas analógicas")
            if n == "ai2" and d.n["ai"] < 2:
                return False, T("Necesita 2 entradas analógicas")
            if n == "out" and not d.outputs():
                return False, T("La tarjeta no tiene DAC ni PWM")
            if n in ("di", "do") and d.n[n] < 1:
                return False, T("La tarjeta no tiene %s") % n.upper()
        return True, ""

    def _tiles(self):
        for key, short, name, cls, needs in TOOLS:
            tb = self.tiles[key][0]
            ok, why = self._ok_for(needs)
            tb.setEnabled(ok)
            tb.setToolTip(name if ok else "%s - %s" % (name, why))

    def open_tool(self, key):
        if key in self.wins:
            w = self.wins[key]
            w.showNormal()
            w.raise_()
            w.activateWindow()
            return
        cls = [t[3] for t in TOOLS if t[0] == key][0]
        w = cls(self)
        w._key = key
        w.setWindowIcon(QIcon(make_icon(key, 64)))
        self.wins[key] = w
        w.show()

    def cal_changed(self):
        d = self.dev
        if d.connected and not d.simulated:
            d.vref = self.cal.vref(d.board, VREF.get(d.board, DEFAULT_VREF))
        for w in list(self.wins.values()):
            w.device_changed()

    def forget(self, w):
        k = getattr(w, "_key", None)
        if k in self.wins and self.wins[k] is w:
            del self.wins[k]

    def closeEvent(self, e):
        for w in list(self.wins.values()):
            w.close()
        self.dev.close()
        e.accept()
