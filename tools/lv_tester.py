import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lv_wire as W


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
    raise ValueError("comando desconocido: %s   (ver la ayuda del archivo)" % name)


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


def gui(a):
    from PyQt5 import QtCore, QtWidgets, QtGui
    try:
        from serial.tools import list_ports
    except Exception:
        list_ports = None

    class Win(QtWidgets.QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("LV_ESP32 · Probador de comandos")
            self.resize(1020, 700)
            self.wire = None
            self.ident = None
            self.hist, self.hpos = [], 0
            self.spins = {}
            root = QtWidgets.QVBoxLayout(self)

            top = QtWidgets.QHBoxLayout()
            self.port = QtWidgets.QComboBox()
            self.port.setEditable(True)
            self.port.setMinimumWidth(180)
            bref = QtWidgets.QPushButton("Actualizar")
            bref.clicked.connect(self.refresh)
            self.bcon = QtWidgets.QPushButton("Conectar")
            self.bcon.clicked.connect(self.toggle)
            self.info = QtWidgets.QLabel("sin conexion")
            top.addWidget(QtWidgets.QLabel("Puerto:"))
            top.addWidget(self.port)
            top.addWidget(bref)
            top.addWidget(self.bcon)
            top.addWidget(self.info, 1)
            root.addLayout(top)

            mid = QtWidgets.QHBoxLayout()
            root.addLayout(mid, 1)
            self.panel = QtWidgets.QVBoxLayout()
            pw = QtWidgets.QWidget()
            pw.setLayout(self.panel)
            sc = QtWidgets.QScrollArea()
            sc.setWidgetResizable(True)
            sc.setWidget(pw)
            sc.setMinimumWidth(430)
            mid.addWidget(sc, 0)

            self.rowspec("Salida digital (DO)", "do", [("canal", 0, 0, 255), ("valor", 1, 0, 1)], "Enviar")
            self.rowspec("Entrada digital (DI)", "di", [("canal", 0, 0, 255)], "Leer")
            self.rowspec("Entrada analogica (AI)", "ai", [("canal", 0, 0, 255)], "Leer")
            self.rowspec("Salida analogica / DAC (AO)", "ao", [("canal", 0, 0, 255), ("valor", 128, 0, 255)], "Enviar")
            self.rowspec("PWM", "pwm", [("canal", 0, 0, 255), ("duty", 128, 0, 255)], "Enviar")
            self.rowspec("Servo", "servo", [("canal", 0, 0, 255), ("angulo", 90, 0, 180)], "Enviar")
            self.rowspec("NeoPixel: toda la tira", "neo", [("r", 255, 0, 255), ("g", 0, 0, 255), ("b", 0, 0, 255)], "Enviar")
            self.rowspec("NeoPixel: un pixel", "neopx", [("pixel", 0, 0, 255), ("r", 0, 0, 255), ("g", 255, 0, 255), ("b", 0, 0, 255)], "Enviar")
            self.rowspec("NeoPixel: pin de la tira", "neoopt", [("opcion", 0, 0, 255)], "Enviar")

            g = QtWidgets.QGroupBox("LCD I2C")
            h = QtWidgets.QHBoxLayout(g)
            self.l_addr = QtWidgets.QLineEdit("0x27"); self.l_addr.setMaximumWidth(60)
            self.l_col = QtWidgets.QSpinBox(); self.l_col.setRange(0, 15)
            self.l_row = QtWidgets.QSpinBox(); self.l_row.setRange(0, 1)
            self.l_txt = QtWidgets.QLineEdit("Hola"); self.l_txt.setMaxLength(16)
            b = QtWidgets.QPushButton("Enviar"); b.clicked.connect(self.do_lcd)
            for wd in (QtWidgets.QLabel("addr"), self.l_addr, QtWidgets.QLabel("col"), self.l_col,
                       QtWidgets.QLabel("fila"), self.l_row, self.l_txt, b):
                h.addWidget(wd)
            self.panel.addWidget(g)

            g = QtWidgets.QGroupBox("Generales")
            h = QtWidgets.QHBoxLayout(g)
            for txt, cmd in (("Ping", "ping"), ("Identidad", "id")):
                b = QtWidgets.QPushButton(txt)
                b.clicked.connect(lambda _=False, c=cmd: self.send(c))
                h.addWidget(b)
            self.panel.addWidget(g)

            self.gonl = QtWidgets.QGroupBox("WiFi / FTP  (solo variantes ONLINE)")
            v = QtWidgets.QVBoxLayout(self.gonl)
            h = QtWidgets.QHBoxLayout()
            self.w_ssid = QtWidgets.QLineEdit(); self.w_ssid.setPlaceholderText("SSID")
            self.w_pass = QtWidgets.QLineEdit(); self.w_pass.setPlaceholderText("clave")
            self.w_pass.setEchoMode(QtWidgets.QLineEdit.Password)
            b = QtWidgets.QPushButton("Guardar WiFi"); b.clicked.connect(self.do_wsave)
            for wd in (self.w_ssid, self.w_pass, b):
                h.addWidget(wd)
            v.addLayout(h)
            h = QtWidgets.QHBoxLayout()
            self.f_user = QtWidgets.QLineEdit(); self.f_user.setPlaceholderText("usuario FTP")
            self.f_pass = QtWidgets.QLineEdit(); self.f_pass.setPlaceholderText("clave FTP")
            self.f_pass.setEchoMode(QtWidgets.QLineEdit.Password)
            b = QtWidgets.QPushButton("Guardar FTP"); b.clicked.connect(self.do_fsave)
            for wd in (self.f_user, self.f_pass, b):
                h.addWidget(wd)
            v.addLayout(h)
            h = QtWidgets.QHBoxLayout()
            for txt, cmd in (("Conectar", "wconn"), ("Estado", "wstat"), ("Desconectar", "wdisc"),
                             ("FTP on", "ftp 1"), ("FTP off", "ftp 0")):
                b = QtWidgets.QPushButton(txt)
                b.clicked.connect(lambda _=False, c=cmd: self.send(c))
                h.addWidget(b)
            v.addLayout(h)
            self.panel.addWidget(self.gonl)
            self.panel.addStretch(1)

            right = QtWidgets.QVBoxLayout()
            mid.addLayout(right, 1)
            self.log = QtWidgets.QPlainTextEdit()
            self.log.setReadOnly(True)
            f = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
            self.log.setFont(f)
            right.addWidget(self.log, 1)
            self.cmd = QtWidgets.QLineEdit()
            self.cmd.setPlaceholderText("comando:  do 0 1  |  ai 2  |  neo 255 0 0  |  hex 01 00 01   (Enter)")
            self.cmd.returnPressed.connect(self.on_enter)
            self.cmd.installEventFilter(self)
            right.addWidget(self.cmd)
            hb = QtWidgets.QHBoxLayout()
            bc = QtWidgets.QPushButton("Limpiar"); bc.clicked.connect(self.log.clear)
            bs = QtWidgets.QPushButton("Guardar registro..."); bs.clicked.connect(self.save_log)
            hb.addWidget(bc); hb.addWidget(bs); hb.addStretch(1)
            right.addLayout(hb)

            self.set_enabled(False)
            self.refresh()
            if a.port:
                self.port.setEditText(a.port)
                QtCore.QTimer.singleShot(100, self.toggle)

        def rowspec(self, title, name, fields, btn):
            g = QtWidgets.QGroupBox(title)
            h = QtWidgets.QHBoxLayout(g)
            sp = []
            for lbl, default, lo, hi in fields:
                h.addWidget(QtWidgets.QLabel(lbl))
                s = QtWidgets.QSpinBox()
                s.setRange(lo, hi)
                s.setValue(default)
                h.addWidget(s)
                sp.append(s)
            b = QtWidgets.QPushButton(btn)
            b.clicked.connect(lambda _=False, n=name, ss=sp: self.send(
                "%s %s" % (n, " ".join(str(x.value()) for x in ss))))
            h.addWidget(b)
            h.addStretch(1)
            self.panel.addWidget(g)
            self.spins[name] = sp

        def set_enabled(self, on):
            for i in range(self.panel.count()):
                it = self.panel.itemAt(i).widget()
                if it:
                    it.setEnabled(on)
            self.cmd.setEnabled(on)

        def refresh(self):
            cur = self.port.currentText()
            self.port.clear()
            if list_ports:
                for p in list_ports.comports():
                    self.port.addItem(p.device)
            if cur:
                self.port.setEditText(cur)

        def toggle(self):
            if self.wire:
                self.wire.close()
                self.wire = None
                self.bcon.setText("Conectar")
                self.info.setText("sin conexion")
                self.set_enabled(False)
                return
            self.info.setText("abriendo... (la placa se reinicia)")
            QtWidgets.QApplication.processEvents()
            try:
                self.wire = W.Wire(self.port.currentText().strip(), timeout=a.timeout, boot_delay=a.boot)
                self.ident = self.wire.identity()
            except Exception as e:
                self.wire = None
                self.info.setText("error: %s" % e)
                return
            self.bcon.setText("Desconectar")
            self.set_enabled(True)
            if not self.ident:
                self.info.setText("conectado, pero la placa NO contesta a 0xEF (firmware v3 cargado?)")
                return
            if "board" not in self.ident:
                self.info.setText("respuesta rara: %s" % self.ident.get("raw"))
                return
            n = self.ident["n"]
            self.info.setText("%s · %s · v%s · DI%s DO%s AI%s AO%s PWM%s SV%s NEO%s" % (
                self.ident["board"], self.ident["variant"], self.ident["version"],
                n["di"], n["do"], n["ai"], n["ao"], n["pwm"], n["servo"], n["neo"]))
            self.gonl.setEnabled(self.ident["online"])
            lim = {"do": "do", "di": "di", "ai": "ai", "ao": "ao", "pwm": "pwm", "servo": "servo", "neoopt": "neo"}
            for name, key in lim.items():
                cnt = n.get(key)
                if cnt is not None:
                    self.spins[name][0].setMaximum(max(cnt - 1, 0))
            self.log_add("Identidad: %s" % self.ident["raw"], "#555")

        def log_add(self, txt, color=None):
            if color:
                esc = (txt.replace("&", "&amp;").replace("<", "&lt;")
                          .replace("\n", "<br>").replace(" ", "&nbsp;"))
                self.log.appendHtml('<span style="color:%s">%s</span>' % (color, esc))
            else:
                self.log.appendPlainText(txt)

        def send(self, line):
            if not self.wire:
                return
            try:
                res = run_line(self.wire, line)
                txt, ok = describe(line, res)
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
            if obj is self.cmd and ev.type() == QtCore.QEvent.KeyPress and self.hist:
                if ev.key() == QtCore.Qt.Key_Up:
                    self.hpos = max(0, self.hpos - 1)
                    self.cmd.setText(self.hist[self.hpos])
                    return True
                if ev.key() == QtCore.Qt.Key_Down:
                    self.hpos = min(len(self.hist), self.hpos + 1)
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
            fn, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Guardar registro", "probador.txt", "Texto (*.txt)")
            if fn:
                with open(fn, "w", encoding="utf-8") as f:
                    f.write(self.log.toPlainText())

        def closeEvent(self, ev):
            if self.wire:
                self.wire.close()
            super().closeEvent(ev)

    app = QtWidgets.QApplication(sys.argv)
    w = Win()
    w.show()
    if a.shot:
        QtCore.QTimer.singleShot(a.shot_ms, lambda: (w.grab().save(a.shot), app.quit()))
    return app.exec_()


def main():
    ap = argparse.ArgumentParser(description="Probador de comandos LV_ESP32 v3")
    ap.add_argument("--port")
    ap.add_argument("--cmd", action="append", help="ejecuta el comando y sale (repetible)")
    ap.add_argument("--timeout", type=float, default=1.0, help="timeout de lectura (s), como VISA")
    ap.add_argument("--boot", type=float, default=2.0, help="espera tras abrir el puerto (s)")
    ap.add_argument("--shot", help=argparse.SUPPRESS)
    ap.add_argument("--shot-ms", type=int, default=800, help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.cmd:
        if not a.port:
            ap.error("--cmd necesita --port")
        return cli(a)
    return gui(a)


if __name__ == "__main__":
    sys.exit(main())
