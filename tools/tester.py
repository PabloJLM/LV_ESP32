import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as W


def run_line(wire, line):
    parts = line.strip().split()
    if not parts:
        raise ValueError("vacio")
    name = parts[0].lower()
    if name == "hex":
        try:
            frame = bytes(int(x, 16) for x in parts[1:])
        except ValueError:
            raise ValueError("hex: bytes en hexadecimal, p. ej.  hex 01 00 01")
        if not frame:
            raise ValueError("hex: faltan bytes")
        return wire.txrx(frame, W.raw_reply_kind(frame))
    if name == "lcd":
        a = parts[1:]
        if len(a) >= 4 and a[0].lower().startswith("0x"):
            addr, col, row, txt = int(a[0], 16), int(a[1]), int(a[2]), " ".join(a[3:])
        elif len(a) >= 3:
            addr, col, row, txt = 0x27, int(a[0]), int(a[1]), " ".join(a[2:])
        else:
            raise ValueError("lcd [0x27] col fila texto")
        return wire.cmd("lcd", (addr, col, row), txt)
    if name == "wsave":
        if len(parts) < 2:
            raise ValueError("wsave ssid [clave]")
        return wire.cmd("wsave", (), parts[1], parts[2] if len(parts) > 2 else "")
    if name == "ftpsave":
        if len(parts) != 3:
            raise ValueError("ftpsave usuario clave")
        return wire.cmd("ftpsave", (), parts[1], parts[2])
    if name in W.SIMPLE:
        try:
            args = [int(x, 0) for x in parts[1:]]
        except ValueError:
            raise ValueError("los argumentos de %s son enteros" % name)
        return wire.cmd(name, args)
    raise ValueError("comando desconocido: %s" % name)


def fmt_hex(b):
    return " ".join("%02X" % x for x in b) if b else "(nada)"


def describe(line, res):
    ok, msg = res.verdict()
    return ("%s\n   TX %s\n   RX %s   %r\n   -> %s   (%.0f ms)"
            % (line, fmt_hex(res.tx), fmt_hex(res.rx), res.text, msg, res.ms)), ok


def cli(a):
    w = W.Wire(a.port, timeout=a.timeout, boot_delay=a.boot)
    bad = 0
    try:
        ident = w.identity()
        print("Identidad:", ident["raw"] if ident else "SIN RESPUESTA")
        for line in a.cmd:
            try:
                txt, ok = describe(line, run_line(w, line))
            except ValueError as e:
                txt, ok = "%s\n   -> %s" % (line, e), False
            print(txt)
            bad += 0 if ok else 1
    finally:
        w.close()
    return 1 if bad else 0


ROWS = [
    ("Salida digital (DO)", "do", [("canal", 0, 255), ("valor", 1, 1)], "Enviar"),
    ("Entrada digital (DI)", "di", [("canal", 0, 255)], "Leer"),
    ("Entrada analogica (AI)", "ai", [("canal", 0, 255)], "Leer"),
    ("Salida analogica / DAC (AO)", "ao", [("canal", 0, 255), ("valor", 128, 255)], "Enviar"),
    ("PWM", "pwm", [("canal", 0, 255), ("duty", 128, 255)], "Enviar"),
    ("Servo", "servo", [("canal", 0, 255), ("angulo", 90, 180)], "Enviar"),
    ("NeoPixel: toda la tira", "neo", [("r", 255, 255), ("g", 0, 255), ("b", 0, 255)], "Enviar"),
    ("NeoPixel: un pixel", "neopx",
     [("pixel", 0, 255), ("r", 0, 255), ("g", 255, 255), ("b", 0, 255)], "Enviar"),
    ("NeoPixel: pin de la tira", "neoopt", [("opcion", 0, 255)], "Enviar"),
]
LIMITS = {"do": "do", "di": "di", "ai": "ai", "ao": "ao", "pwm": "pwm", "servo": "servo",
          "neoopt": "neo"}
ONLINE = [("Conectar", "wconn"), ("Estado", "wstat"), ("Desconectar", "wdisc"),
          ("FTP on", "ftp 1"), ("FTP off", "ftp 0")]


def gui(a):
    from hub.ui import (QSS, QApplication, QComboBox, QFileDialog, QGroupBox, QHBoxLayout,
                        QLabel, QLineEdit, QPlainTextEdit, QPushButton, QScrollArea, QTimer,
                        QVBoxLayout, QWidget, Qt, app_icon, ispin, set_status)

    class Win(QWidget):
        def __init__(self):
            super().__init__()
            self.setObjectName("panel")
            self.setStyleSheet(QSS)
            self.setWindowTitle("LV_ESP32 · Probador de comandos")
            self.resize(1020, 700)
            self.wire = None
            self.hist, self.hpos = [], 0
            self.spins = {}

            self.port = QComboBox()
            self.port.setEditable(True)
            self.port.setMinimumWidth(180)
            self.bcon = self.button("Conectar", self.toggle)
            self.bcon.setObjectName("run")
            self.info = QLabel("sin conexion")
            self.info.setObjectName("status")
            top = self.hbox(QLabel("Puerto"), self.port, self.button("Actualizar", self.refresh),
                            self.bcon)
            top.addWidget(self.info, 1)

            self.panel = QVBoxLayout()
            for title, name, fields, btn in ROWS:
                self.spins[name] = [ispin(0, hi, val) for _l, val, hi in fields]
                ws = []
                for (lbl, _v, _h), sp in zip(fields, self.spins[name]):
                    ws += [QLabel(lbl), sp]
                ws.append(self.button(btn, lambda _c=False, n=name: self.send(
                    "%s %s" % (n, " ".join(str(x.value()) for x in self.spins[n])))))
                self.box(title, ws)

            self.l_addr = QLineEdit("0x27")
            self.l_addr.setMaximumWidth(60)
            self.l_col, self.l_row = ispin(0, 15, 0), ispin(0, 1, 0)
            self.l_txt = QLineEdit("Hola")
            self.l_txt.setMaxLength(16)
            self.box("LCD I2C", [QLabel("addr"), self.l_addr, QLabel("col"), self.l_col,
                                 QLabel("fila"), self.l_row, self.l_txt,
                                 self.button("Enviar", self.do_lcd)], stretch=False)
            self.box("Generales", [self.button("Ping", lambda: self.send("ping")),
                                   self.button("Identidad", lambda: self.send("id"))])

            self.w_ssid, self.w_pass = self.edit("SSID"), self.edit("clave", True)
            self.f_user, self.f_pass = self.edit("usuario FTP"), self.edit("clave FTP", True)
            self.gonl = QGroupBox("WiFi / FTP  (solo variantes ONLINE)")
            v = QVBoxLayout(self.gonl)
            v.addLayout(self.hbox(self.w_ssid, self.w_pass,
                                  self.button("Guardar WiFi", self.do_wsave)))
            v.addLayout(self.hbox(self.f_user, self.f_pass,
                                  self.button("Guardar FTP", self.do_fsave)))
            v.addLayout(self.hbox(*[self.button(t, lambda _c=False, c=c: self.send(c))
                                    for t, c in ONLINE]))
            self.panel.addWidget(self.gonl)
            self.panel.addStretch(1)
            inner = QWidget()
            inner.setObjectName("panel")
            inner.setLayout(self.panel)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(inner)
            scroll.setMinimumWidth(450)

            self.log = QPlainTextEdit()
            self.log.setReadOnly(True)
            self.cmd = QLineEdit()
            self.cmd.setPlaceholderText(
                "comando:  do 0 1  |  ai 2  |  neo 255 0 0  |  hex 01 00 01   (Enter)")
            self.cmd.returnPressed.connect(self.on_enter)
            self.cmd.installEventFilter(self)
            foot = self.hbox(self.button("Limpiar", self.log.clear),
                             self.button("Guardar registro...", self.save_log))
            foot.addStretch(1)
            right = QVBoxLayout()
            right.addWidget(self.log, 1)
            right.addWidget(self.cmd)
            right.addLayout(foot)

            mid = QHBoxLayout()
            mid.addWidget(scroll)
            mid.addLayout(right, 1)
            root = QVBoxLayout(self)
            root.addLayout(top)
            root.addLayout(mid, 1)

            self.set_enabled(False)
            self.refresh()
            if a.port:
                self.port.setEditText(a.port)
                QTimer.singleShot(100, self.toggle)

        def button(self, text, slot):
            b = QPushButton(text)
            b.clicked.connect(slot)
            return b

        def edit(self, placeholder, secret=False):
            e = QLineEdit()
            e.setPlaceholderText(placeholder)
            if secret:
                e.setEchoMode(QLineEdit.Password)
            return e

        def hbox(self, *widgets):
            h = QHBoxLayout()
            for w in widgets:
                h.addWidget(w)
            return h

        def box(self, title, widgets, stretch=True):
            g = QGroupBox(title)
            h = self.hbox(*widgets)
            if stretch:
                h.addStretch(1)
            g.setLayout(h)
            self.panel.addWidget(g)

        def set_enabled(self, on):
            for i in range(self.panel.count()):
                w = self.panel.itemAt(i).widget()
                if w:
                    w.setEnabled(on)
            self.cmd.setEnabled(on)

        def refresh(self):
            cur = self.port.currentText()
            self.port.clear()
            self.port.addItems([p["port"] for p in W.list_ports()])
            if cur:
                self.port.setEditText(cur)

        def say(self, text, kind=""):
            set_status(self.info, text, kind)

        def toggle(self):
            if self.wire:
                self.wire.close()
                self.wire = None
                self.bcon.setText("Conectar")
                self.say("sin conexion")
                self.set_enabled(False)
                return
            self.say("abriendo... (la placa se reinicia)")
            QApplication.processEvents()
            try:
                self.wire = W.Wire(self.port.currentText().strip(), timeout=a.timeout,
                                   boot_delay=a.boot)
                ident = self.wire.identity()
            except Exception as e:
                self.wire = None
                self.say("error: %s" % e, "err")
                return
            self.bcon.setText("Desconectar")
            self.set_enabled(True)
            if not ident:
                self.say("conectado, pero la placa no contesta (firmware v3 cargado?)", "err")
                return
            if "board" not in ident:
                self.say("respuesta rara: %s" % ident.get("raw"), "err")
                return
            n = ident["n"]
            self.say("%s · %s · v%s · DI%s DO%s AI%s AO%s PWM%s SV%s NEO%s" % (
                ident["board"], ident["variant"], ident["version"], n["di"], n["do"],
                n["ai"], n["ao"], n["pwm"], n["servo"], n["neo"]), "ok")
            self.gonl.setEnabled(ident["online"])
            for name, key in LIMITS.items():
                if n.get(key) is not None:
                    self.spins[name][0].setMaximum(max(n[key] - 1, 0))
            self.log_add("Identidad: %s" % ident["raw"], "#555")

        def log_add(self, txt, color):
            esc = (txt.replace("&", "&amp;").replace("<", "&lt;")
                      .replace("\n", "<br>").replace(" ", "&nbsp;"))
            self.log.appendHtml('<span style="color:%s">%s</span>' % (color, esc))

        def send(self, line):
            if not self.wire:
                return
            try:
                txt, ok = describe(line, run_line(self.wire, line))
            except ValueError as e:
                txt, ok = "%s\n   -> %s" % (line, e), False
            except Exception as e:
                txt, ok = "%s\n   -> error de puerto: %s" % (line, e), False
            self.log_add(txt, "#1a7f37" if ok else "#c62828")

        def on_enter(self):
            line = self.cmd.text().strip()
            if not line:
                return
            self.hist.append(line)
            self.hpos = len(self.hist)
            self.cmd.clear()
            self.send(line)

        def eventFilter(self, obj, ev):
            if obj is self.cmd and ev.type() == ev.KeyPress and self.hist \
                    and ev.key() in (Qt.Key_Up, Qt.Key_Down):
                step = -1 if ev.key() == Qt.Key_Up else 1
                self.hpos = min(len(self.hist), max(0, self.hpos + step))
                self.cmd.setText(self.hist[self.hpos] if self.hpos < len(self.hist) else "")
                return True
            return super().eventFilter(obj, ev)

        def do_lcd(self):
            self.send("lcd %s %d %d %s" % (self.l_addr.text() or "0x27", self.l_col.value(),
                                           self.l_row.value(), self.l_txt.text()))

        def do_wsave(self):
            if self.w_ssid.text():
                self.send("wsave %s %s" % (self.w_ssid.text(), self.w_pass.text()))

        def do_fsave(self):
            if self.f_user.text() and self.f_pass.text():
                self.send("ftpsave %s %s" % (self.f_user.text(), self.f_pass.text()))

        def save_log(self):
            fn, _ = QFileDialog.getSaveFileName(self, "Guardar registro", "probador.txt",
                                                "Texto (*.txt)")
            if fn:
                with open(fn, "w", encoding="utf-8") as f:
                    f.write(self.log.toPlainText())

        def closeEvent(self, ev):
            if self.wire:
                self.wire.close()
            super().closeEvent(ev)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setWindowIcon(app_icon("tester"))
    w = Win()
    w.show()
    return app.exec_()


def main():
    ap = argparse.ArgumentParser(description="Probador de comandos LV_ESP32 v3")
    ap.add_argument("--port")
    ap.add_argument("--cmd", action="append", help="ejecuta el comando y sale (repetible)")
    ap.add_argument("--timeout", type=float, default=1.0, help="timeout de lectura (s), como VISA")
    ap.add_argument("--boot", type=float, default=2.0, help="espera tras abrir el puerto (s)")
    a = ap.parse_args()
    if a.cmd:
        if not a.port:
            ap.error("--cmd necesita --port")
        return cli(a)
    return gui(a)


if __name__ == "__main__":
    sys.exit(main())
