import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lv_core as core

try:
    from PyQt5.QtCore import Qt, QThread, pyqtSignal as SignalT
    from PyQt5.QtGui import QFont, QTextCursor
    from PyQt5.QtWidgets import (QApplication, QComboBox, QFileDialog, QFrame,
                                 QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                                 QPlainTextEdit, QProgressBar, QPushButton,
                                 QVBoxLayout, QWidget)
    QT_NAME = "PyQt5"
except ImportError:
    try:
        from PySide6.QtCore import Qt, QThread, Signal as SignalT
        from PySide6.QtGui import QFont, QTextCursor
        from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QFrame,
                                       QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                                       QPlainTextEdit, QProgressBar, QPushButton,
                                       QVBoxLayout, QWidget)
        QT_NAME = "PySide6"
    except ImportError:
        sys.stderr.write(
            "\nFalta la libreria grafica. Instalala en el Python portable:\n\n"
            "    %s -m pip install PyQt5\n\n" % sys.executable)
        sys.exit(3)


QSS = """
/* Paleta tipo LabVIEW: blanco, amarillos calidos y amarillo oscuro.
   Sin esquinas redondeadas; relieve sobrio. */
QWidget        { background:#fffdf0; color:#2b2100;
                 font-family:"Segoe UI","Tahoma","MS Shell Dlg 2",sans-serif;
                 font-size:12px; }
QLabel#title   { font-size:15px; font-weight:bold; color:#6b5200;
                 background:#ffe27a; border-bottom:2px solid #b38600;
                 padding:6px 8px; }
QLabel#sub     { color:#5a4600; }
QLabel#field   { color:#2b2100; }

QComboBox      { background:#ffffff; border:1px solid #b38600;
                 padding:3px 6px; min-height:18px; }
QComboBox:focus{ border:1px solid #8a6a00; background:#fffbe0; }
QComboBox QAbstractItemView { background:#ffffff; border:1px solid #b38600;
                 selection-background-color:#b38600; selection-color:#ffffff; }

QLineEdit      { background:#ffffff; border:1px solid #b38600; padding:3px 5px; }
QLineEdit:focus{ border:1px solid #8a6a00; background:#fffbe0; }
QLineEdit:disabled { background:#f3efd8; color:#8c8466; }

QPushButton    { background:#f7c92b; border:1px solid #8a6a00;
                 padding:5px 16px; min-width:80px; color:#2b2100; }
QPushButton:hover    { background:#ffdc5e; border:1px solid #6b5200; }
QPushButton:pressed  { background:#d9a900; border:1px solid #6b5200; }
QPushButton:disabled { background:#f3efd8; color:#a39a78; border:1px solid #d6cda6; }
QPushButton#ghost    { background:#fff3c2; }

QProgressBar   { background:#ffffff; border:1px solid #b38600;
                 height:16px; text-align:center; color:#2b2100; }
QProgressBar::chunk { background:#e0a800; }

QPlainTextEdit { background:#ffffff; border:1px solid #b38600;
                 color:#2b2100; padding:2px; }
QFrame#sep     { background:#b38600; max-height:1px; border:none; }
"""


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
        except Exception as e:
            self.done.emit(False, "Error inesperado: %s" % e)


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

    def add_row(self, r, label, widget, extra=None):
        lab = QLabel(label); lab.setObjectName("field")
        self.form.addWidget(lab, r, 0)
        self.form.addWidget(widget, r, 1)
        if extra:
            self.form.addWidget(extra, r, 2)
        self.form.setColumnStretch(1, 1)

    def append(self, txt):
        if txt.startswith("\r"):
            c = self.log.textCursor()
            c.movePosition(QTextCursor.End)
            c.select(QTextCursor.LineUnderCursor)
            c.insertText(txt[1:])
        else:
            self.log.appendPlainText(txt)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def on_step(self, pct, msg):
        self.bar.setValue(pct)
        if msg:
            self.status.setText(msg)

    def set_status(self, msg, kind="info"):
        color = {"ok": "#006600", "err": "#a00000", "info": "#5a4600"}[kind]
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

        self.ed_file = QLineEdit()
        self.btn_file = QPushButton("Examinar..."); self.btn_file.setObjectName("ghost")
        self.add_row(2, "Archivo", self.ed_file, self.btn_file)

        self.btn_go = QPushButton("Cargar firmware")
        row = QHBoxLayout(); row.addStretch(1); row.addWidget(self.btn_go)
        self.root.insertLayout(4, row)

        self.btn_rescan.clicked.connect(self.rescan)
        self.btn_go.clicked.connect(self.go)
        self.btn_file.clicked.connect(self.pick_file)
        self.cb_board.currentIndexChanged.connect(lambda _i: self._on_board())
        self.ed_file.textChanged.connect(lambda _t: self._apply_board())
        self.ed_file.setText(core.display_path(core.bin_path(self.board())))
        self.rescan(preferred=port)

    def board(self):
        return self.cb_board.currentData()

    def _needs_port(self):
        return core.BOARDS[self.board()].get("needs_port", True)

    def _file_ok(self):
        return os.path.isfile(core.resolve_path(self.ed_file.text()))

    def _on_board(self):
        self.ed_file.setText(core.display_path(core.bin_path(self.board())))
        self._apply_board()

    def pick_file(self):
        start = core.resolve_path(self.ed_file.text()) or core.BIN_DIR
        path, _flt = QFileDialog.getOpenFileName(
            self, "Elegir el archivo de firmware", start,
            "Firmware (*.bin *.hex);;Todos los archivos (*)")
        if path:
            self.ed_file.setText(core.display_path(os.path.normpath(path)))

    def _apply_board(self):
        has = bool(self.cb_port.currentData())
        self.btn_go.setEnabled(has or not self._needs_port())
        if not self._file_ok():
            self.set_status("No existe el archivo de firmware. Usa Examinar... "
                            "o compilalo (%s)." % os.path.join("firmware", "COMPILAR.md"),
                            "err")
        elif core.BOARDS[self.board()].get("note"):
            self.set_status(core.BOARDS[self.board()]["note"], "info")
        elif not self._needs_port():
            self.set_status("Esta placa se carga sin usar el puerto serie: el "
                            "puerto es opcional, se busca solo al terminar.", "info")

    def rescan(self, checked=False, preferred=None):
        self.cb_port.clear()
        ports = core.list_ports()
        if not ports:
            self.cb_port.addItem("(no hay puertos)", "")
            if self._needs_port():
                self.set_status("Conecta la tarjeta por USB y presiona Actualizar.", "err")
            self._apply_board()
            return
        for p in ports:
            txt = p["port"] + (("  —  " + p["label"]) if p["label"] else "")
            self.cb_port.addItem(txt, p["port"])
        target = preferred or core.guess_port(self.board(), ports)
        if target:
            i = self.cb_port.findData(target)
            if i >= 0:
                self.cb_port.setCurrentIndex(i)
        self._apply_board()
        if self._needs_port() and self._file_ok():
            self.set_status("%d puerto(s) encontrado(s)." % len(ports), "info")

    def go(self):
        b = self.board()
        p = self.cb_port.currentData()
        if not p and self._needs_port():
            self.set_status("Selecciona un puerto.", "err")
            return
        p = p or ""

        f = self.ed_file.text().strip() or None
        self.start(lambda line, step: core.flash_all(b, p, line, step, bin_file=f),
                   [self.btn_go, self.btn_rescan, self.btn_file, self.cb_board,
                    self.cb_port, self.ed_file])


class ProbeWindow(ToolWindow):
    def __init__(self, port=None):
        super().__init__(
            "Probar tarjeta",
            "Manda los comandos del protocolo a la tarjeta y revisa las respuestas.")

        self.cb_port = QComboBox()
        self.btn_rescan = QPushButton("Actualizar"); self.btn_rescan.setObjectName("ghost")
        self.add_row(0, "Puerto", self.cb_port, self.btn_rescan)

        self.ed_dio = QLineEdit("0")
        self.add_row(1, "Canal DO", self.ed_dio)
        self.ed_adc = QLineEdit("0")
        self.add_row(2, "Canal AI", self.ed_adc)
        self.ed_pwm = QLineEdit("0")
        self.add_row(3, "Canal PWM", self.ed_pwm)
        self.ed_peer = QLineEdit("")
        self.ed_peer.hide()

        self.btn_go = QPushButton("Probar")
        row = QHBoxLayout(); row.addStretch(1); row.addWidget(self.btn_go)
        self.root.insertLayout(4, row)

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


class OnlineWindow(ToolWindow):
    def __init__(self, port=None):
        super().__init__(
            "WiFi y FTP",
            "Conecta el ESP32 (firmware '... + WiFi/FTP') a tu red y publica la "
            "SD por FTP. Cierra los VIs de LabVIEW que tengan el puerto abierto: "
            "solo una aplicacion puede usarlo a la vez.")
        self.link = None

        self.cb_port = QComboBox()
        self.btn_rescan = QPushButton("Actualizar"); self.btn_rescan.setObjectName("ghost")
        self.add_row(0, "Puerto", self.cb_port, self.btn_rescan)

        self.ed_ssid = QLineEdit()
        self.ed_ssid.setPlaceholderText("nombre de la red WiFi (2.4 GHz)")
        self.add_row(1, "Red WiFi", self.ed_ssid)
        self.ed_wpass = QLineEdit(); self.ed_wpass.setEchoMode(QLineEdit.Password)
        self.add_row(2, "Clave WiFi", self.ed_wpass)
        self.ed_user = QLineEdit("lv")
        self.add_row(3, "Usuario FTP", self.ed_user)
        self.ed_fpass = QLineEdit(); self.ed_fpass.setEchoMode(QLineEdit.Password)
        self.add_row(4, "Clave FTP", self.ed_fpass)

        self.btn_conn  = QPushButton("Conectar WiFi")
        self.btn_disc  = QPushButton("Desconectar"); self.btn_disc.setObjectName("ghost")
        self.btn_fon   = QPushButton("Iniciar FTP")
        self.btn_foff  = QPushButton("Detener FTP"); self.btn_foff.setObjectName("ghost")
        self.btn_stat  = QPushButton("Estado");      self.btn_stat.setObjectName("ghost")
        row = QHBoxLayout()
        for b in (self.btn_stat, self.btn_disc, self.btn_foff):
            row.addWidget(b)
        row.addStretch(1)
        row.addWidget(self.btn_conn)
        row.addWidget(self.btn_fon)
        self.root.insertLayout(4, row)

        self._busy = [self.btn_conn, self.btn_disc, self.btn_fon, self.btn_foff,
                      self.btn_stat, self.btn_rescan, self.cb_port, self.ed_ssid,
                      self.ed_wpass, self.ed_user, self.ed_fpass]

        self.btn_rescan.clicked.connect(self.rescan)
        self.btn_conn.clicked.connect(self.do_connect)
        self.btn_disc.clicked.connect(
            lambda: self.run(lambda lk, ln, st: core.online_disconnect(lk, ln)))
        self.btn_fon.clicked.connect(self.do_ftp_on)
        self.btn_foff.clicked.connect(
            lambda: self.run(lambda lk, ln, st: core.online_ftp_stop(lk, ln)))
        self.btn_stat.clicked.connect(
            lambda: self.run(lambda lk, ln, st: core.online_status(lk, ln)))
        self.rescan(preferred=port)

    def _close(self):
        if self.link is not None:
            self.link.close()
            self.link = None

    def closeEvent(self, ev):
        self._close()
        ev.accept()

    def rescan(self, checked=False, preferred=None):
        self._close()
        self.cb_port.clear()
        ports = core.list_ports()
        if not ports:
            self.cb_port.addItem("(no hay puertos)", "")
            self.set_status("Conecta la tarjeta por USB y presiona Actualizar.", "err")
            for b in (self.btn_conn, self.btn_disc, self.btn_fon, self.btn_foff, self.btn_stat):
                b.setEnabled(False)
            return
        for p in ports:
            txt = p["port"] + (("  --  " + p["label"]) if p["label"] else "")
            self.cb_port.addItem(txt, p["port"])
        target = preferred or core.guess_port("esp32_wrover_online", ports)
        if target:
            i = self.cb_port.findData(target)
            if i >= 0:
                self.cb_port.setCurrentIndex(i)
        for b in (self.btn_conn, self.btn_disc, self.btn_fon, self.btn_foff, self.btn_stat):
            b.setEnabled(True)
        self.set_status("%d puerto(s) encontrado(s)." % len(ports), "info")

    def _with_link(self, port, fn, line, step):
        try:
            if self.link is None or self.link.port != port:
                self._close()
                step(5, "Abriendo %s (la tarjeta se reinicia, ~2 s)..." % port)
                self.link = core.LvLink(port)
            return fn(self.link, line, step)
        except Exception as e:
            self._close()
            return False, ("No se pudo usar %s: %s  (¿otro programa o un VI "
                           "tiene el puerto abierto?)" % (port, e))

    def run(self, fn):
        port = self.cb_port.currentData()
        if not port:
            self.set_status("Selecciona un puerto.", "err")
            return
        self.start(lambda line, step: self._with_link(port, fn, line, step), self._busy)

    def do_connect(self):
        ssid, pw = self.ed_ssid.text(), self.ed_wpass.text()
        if not ssid:
            self.set_status("Escribe el nombre de la red WiFi.", "err")
            return
        self.run(lambda lk, ln, st: core.online_connect(lk, ssid, pw, ln, st))

    def do_ftp_on(self):
        user, pw = self.ed_user.text(), self.ed_fpass.text()
        if not user or not pw:
            self.set_status("Escribe usuario y clave del FTP.", "err")
            return
        self.run(lambda lk, ln, st: core.online_ftp_start(lk, user, pw, ln))


class Launcher(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(QSS)
        self.setMinimumSize(460, 280)
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

        b2 = QPushButton("Cargar firmware")
        b3 = QPushButton("WiFi y FTP (solo variante ONLINE)")
        for b in (b2, b3):
            b.setMinimumHeight(46)
            v.addWidget(b)
        v.addStretch(1)

        foot = QLabel("Tesla Lab · Universidad Galileo")
        foot.setObjectName("sub"); foot.setAlignment(Qt.AlignCenter)
        v.addWidget(foot)

        b2.clicked.connect(lambda: self.open(FlashWindow()))
        b3.clicked.connect(lambda: self.open(OnlineWindow()))

    def open(self, w):
        w.setWindowTitle("LV_ESP32")
        w.show()
        self.kids.append(w)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool", choices=["flash", "probe", "online"], default=None)
    ap.add_argument("--board", default=None)
    ap.add_argument("--port", default=None)
    a = ap.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("LV_ESP32")

    if a.tool == "flash":
        w = FlashWindow(a.board, a.port)
    elif a.tool == "probe":
        w = ProbeWindow(a.port)
    elif a.tool == "online":
        w = OnlineWindow(a.port)
    else:
        w = Launcher()

    w.setWindowTitle("LV_ESP32")
    w.show()
    sys.exit(app.exec_() if QT_NAME == "PyQt5" else app.exec())


if __name__ == "__main__":
    main()
