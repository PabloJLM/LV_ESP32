import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core

try:
    from hub.ui import (QSS, QApplication, QComboBox, QFileDialog, QHBoxLayout, QLabel,
                        QLineEdit, QPlainTextEdit, QProgressBar, QPushButton, QTextCursor,
                        QThread, QVBoxLayout, QWidget, Signal, fill_ports, group, hint,
                        set_status, app_icon)
except ImportError:
    sys.stderr.write("\nFalta la libreria grafica. Instalala en el Python portable:\n\n"
                     "    %s -m pip install PyQt5\n\n" % sys.executable)
    sys.exit(3)

NO_PORT = "Conecta la tarjeta por USB y presiona Actualizar."


class Worker(QThread):
    line = Signal(str)
    step = Signal(int, str)
    done = Signal(bool, str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            ok, msg = self.fn(self.line.emit, lambda p, m: self.step.emit(int(p), m))
            self.done.emit(bool(ok), str(msg))
        except Exception as e:
            self.done.emit(False, "Error inesperado: %s" % e)


def password():
    ed = QLineEdit()
    ed.setEchoMode(QLineEdit.Password)
    return ed


class ToolWindow(QWidget):
    TITLE = ""
    HINT = ""
    BOARD = core.DEFAULT_BOARD

    def __init__(self, port=None):
        super().__init__()
        self.worker = None
        self.inputs = []
        self.setObjectName("panel")
        self.setStyleSheet(QSS)
        self.setWindowTitle("LV_ESP32")
        self.setMinimumSize(660, 540)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)
        title = QLabel(self.TITLE)
        title.setObjectName("title")
        root.addWidget(title)
        root.addWidget(hint(self.HINT))

        box, self.form = group("")
        self.form.setColumnStretch(1, 1)
        root.addWidget(box)
        self.buttons = QHBoxLayout()
        root.addLayout(self.buttons)

        self.bar = QProgressBar()
        self.status = QLabel("Listo para comenzar")
        self.status.setObjectName("status")
        self.status.setWordWrap(True)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        root.addWidget(self.bar)
        root.addWidget(self.status)
        root.addWidget(self.log, 1)

        self.cb_port = QComboBox()
        self.btn_scan = self.button("Actualizar", lambda: self.scan(), add=False)
        self.build()
        self.scan(port)

    def build(self):
        pass

    def row(self, label, widget, extra=None):
        r = self.form.rowCount()
        self.form.addWidget(QLabel(label), r, 0)
        self.form.addWidget(widget, r, 1)
        if extra:
            self.form.addWidget(extra, r, 2)
        self.inputs.append(widget)
        return widget

    def button(self, text, slot, main=False, add=True):
        b = QPushButton(text)
        if main:
            b.setObjectName("run")
        b.clicked.connect(slot)
        if add:
            self.buttons.addWidget(b)
        self.inputs.append(b)
        return b

    def port(self):
        return self.cb_port.currentData()

    def board(self):
        return self.BOARD

    def needs_port(self):
        return True

    def scan(self, prefer=None):
        ports = core.list_ports()
        fill_ports(self.cb_port, prefer or core.guess_port(self.board(), ports))
        if not ports:
            self.cb_port.addItem("(no hay puertos)", "")
        self.ports_changed(len(ports))

    def ports_changed(self, n):
        for i in range(self.buttons.count()):
            w = self.buttons.itemAt(i).widget()
            if w:
                w.setEnabled(n > 0)
        if n:
            self.say("%d puerto(s) encontrado(s)." % n)
        else:
            self.say(NO_PORT, "err")

    def say(self, text, kind=""):
        set_status(self.status, text, kind)

    def append(self, txt):
        if txt.startswith("\r"):
            c = self.log.textCursor()
            c.movePosition(QTextCursor.End)
            c.select(QTextCursor.LineUnderCursor)
            c.insertText(txt[1:])
        else:
            self.log.appendPlainText(txt)
        sb = self.log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_step(self, pct, msg):
        self.bar.setValue(pct)
        if msg:
            self.status.setText(msg)

    def start(self, fn):
        if self.needs_port() and not self.port():
            self.say("Selecciona un puerto.", "err")
            return
        for w in self.inputs:
            w.setEnabled(False)
        self.bar.setValue(0)
        self.log.clear()
        self.say("Trabajando...")
        self.worker = Worker(fn)
        self.worker.line.connect(self.append)
        self.worker.step.connect(self.on_step)
        self.worker.done.connect(self.finish)
        self.worker.start()

    def finish(self, ok, msg):
        for w in self.inputs:
            w.setEnabled(True)
        if ok:
            self.bar.setValue(100)
        self.say(msg, "ok" if ok else "err")
        self.append("\n=== %s ===" % ("OK" if ok else "ERROR"))
        self.append(msg)


class FlashWindow(ToolWindow):
    TITLE = "Cargar firmware"
    HINT = "Selecciona la placa y el puerto, y presiona Cargar firmware."

    def __init__(self, board=None, port=None):
        self.board0 = board
        super().__init__(port)

    def build(self):
        self.cb_board = QComboBox()
        for k, v in core.BOARDS.items():
            self.cb_board.addItem(v["label"], k)
        self.cb_board.setCurrentIndex(max(0, self.cb_board.findData(self.board0)))
        self.ed_file = QLineEdit(core.display_path(core.bin_path(self.board())))
        self.row("Placa", self.cb_board)
        self.row("Puerto", self.cb_port, self.btn_scan)
        self.row("Archivo", self.ed_file, self.button("Examinar...", self.pick_file, add=False))
        self.buttons.addStretch(1)
        self.btn_go = self.button("Cargar firmware", self.go, main=True)
        self.cb_board.currentIndexChanged.connect(self.board_changed)
        self.ed_file.textChanged.connect(lambda _t: self.check())

    def board(self):
        return self.cb_board.currentData()

    def needs_port(self):
        return core.BOARDS[self.board()].get("needs_port", True)

    def file_ok(self):
        return os.path.isfile(core.resolve_path(self.ed_file.text()))

    def board_changed(self, _i):
        self.ed_file.setText(core.display_path(core.bin_path(self.board())))
        self.check()

    def pick_file(self):
        start = core.resolve_path(self.ed_file.text()) or core.BIN_DIR
        path, _flt = QFileDialog.getOpenFileName(
            self, "Elegir el archivo de firmware", start,
            "Firmware (*.bin *.hex);;Todos los archivos (*)")
        if path:
            self.ed_file.setText(core.display_path(os.path.normpath(path)))

    def check(self):
        note = core.BOARDS[self.board()].get("note")
        self.btn_go.setEnabled(bool(self.port()) or not self.needs_port())
        if not self.file_ok():
            self.say("No existe el archivo de firmware. Usa Examinar... o compilalo (%s)."
                     % os.path.join("firmware", "COMPILAR.md"), "err")
        elif note:
            self.say(note)
        elif not self.needs_port():
            self.say("Esta placa no necesita puerto para cargar.")

    def ports_changed(self, n):
        if self.needs_port():
            if not n:
                self.say(NO_PORT, "err")
            elif self.file_ok():
                self.say("%d puerto(s) encontrado(s)." % n)
        self.check()

    def go(self):
        b, p = self.board(), self.port() or ""
        f = self.ed_file.text().strip() or None
        self.start(lambda line, step: core.flash_all(b, p, line, step, bin_file=f))


class OnlineWindow(ToolWindow):
    TITLE = "WiFi y FTP"
    HINT = ("Conecta el ESP32 (firmware '+ WiFi/FTP') a tu red y publica la SD por FTP. "
            "Cierra los VIs que usen el puerto.")
    BOARD = "esp32_wrover_online"

    def build(self):
        self.link = None
        self.row("Puerto", self.cb_port, self.btn_scan)
        self.ed_ssid = self.row("Red WiFi", QLineEdit())
        self.ed_ssid.setPlaceholderText("nombre de la red WiFi (2.4 GHz)")
        self.ed_wpass = self.row("Clave WiFi", password())
        self.ed_user = self.row("Usuario FTP", QLineEdit("lv"))
        self.ed_fpass = self.row("Clave FTP", password())
        self.button("Estado", lambda: self.run(lambda lk, ln, st: core.online_status(lk, ln)))
        self.button("Desconectar",
                    lambda: self.run(lambda lk, ln, st: core.online_disconnect(lk, ln)))
        self.button("Detener FTP",
                    lambda: self.run(lambda lk, ln, st: core.online_ftp_stop(lk, ln)))
        self.buttons.addStretch(1)
        self.button("Conectar WiFi", self.wifi_on, main=True)
        self.button("Iniciar FTP", self.ftp_on, main=True)

    def close_link(self):
        if self.link is not None:
            self.link.close()
            self.link = None

    def closeEvent(self, ev):
        self.close_link()
        ev.accept()

    def scan(self, prefer=None):
        self.close_link()
        super().scan(prefer)

    def with_link(self, port, fn, line, step):
        try:
            if self.link is None or self.link.port != port:
                self.close_link()
                step(5, "Abriendo %s (unos 2 s)..." % port)
                self.link = core.LvLink(port)
            return fn(self.link, line, step)
        except Exception as e:
            self.close_link()
            return False, ("No se pudo usar %s: %s  (¿otro programa o un VI "
                           "tiene el puerto abierto?)" % (port, e))

    def run(self, fn):
        port = self.port()
        self.start(lambda line, step: self.with_link(port, fn, line, step))

    def wifi_on(self):
        ssid, pw = self.ed_ssid.text(), self.ed_wpass.text()
        if not ssid:
            self.say("Escribe el nombre de la red WiFi.", "err")
            return
        self.run(lambda lk, ln, st: core.online_connect(lk, ssid, pw, ln, st))

    def ftp_on(self):
        user, pw = self.ed_user.text(), self.ed_fpass.text()
        if not user or not pw:
            self.say("Escribe usuario y clave del FTP.", "err")
            return
        self.run(lambda lk, ln, st: core.online_ftp_start(lk, user, pw, ln))


class Launcher(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("panel")
        self.setStyleSheet(QSS)
        self.setWindowTitle("LV_ESP32")
        self.setMinimumSize(420, 240)
        self.kids = []

        v = QVBoxLayout(self)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(10)
        title = QLabel("LV_ESP32")
        title.setObjectName("title")
        v.addWidget(title)
        v.addWidget(hint("Preparar la tarjeta para usarla desde LabVIEW."))
        for text, cls in (("Cargar firmware", FlashWindow),
                          ("WiFi y FTP (solo variante ONLINE)", OnlineWindow)):
            b = QPushButton(text)
            b.setMinimumHeight(40)
            b.clicked.connect(lambda _c=False, cls=cls: self.open(cls()))
            v.addWidget(b)
        v.addStretch(1)
        v.addWidget(hint("Tesla Lab · Universidad Galileo"))

    def open(self, w):
        w.show()
        self.kids.append(w)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool", choices=["flash", "online"], default=None)
    ap.add_argument("--board", default=None)
    ap.add_argument("--port", default=None)
    a = ap.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("LV_ESP32")
    app.setStyle("Fusion")
    app.setWindowIcon(app_icon("flasher"))
    if a.tool == "flash":
        w = FlashWindow(a.board, a.port)
    elif a.tool == "online":
        w = OnlineWindow(a.port)
    else:
        w = Launcher()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
