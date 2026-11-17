import json
import os

from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
    QTextBrowser, QVBoxLayout, QWidget)

import core
from hub.dev import BOARD_NAMES, DEFAULT_VREF, PINS, VREF
from hub.lang import T

from camilab.documento import save_json
from camilab.config import APP, EXT_PROJ, EXT_VI, app_icon
from camilab.menus import add_actions
from camilab.simulador import FakeSerial


class IdentThread(QThread):
    done = pyqtSignal(object, str)

    def __init__(self, port):
        QThread.__init__(self)
        self.port = port

    def run(self):
        try:
            if self.port.upper() == "SIM":
                w = core.Wire(transport=FakeSerial(), timeout=0.5)
            else:
                w = core.Wire(self.port, timeout=1.0)
            d = w.identity()
            w.close()
            if not d or "n" not in d:
                raise ValueError(T("La tarjeta no responde."))
            self.done.emit(d, "")
        except Exception as e:
            self.done.emit(None, str(e))


def board_html(d):
    b = d["board"]
    vref = VREF.get(b, DEFAULT_VREF)
    n = d["n"]
    pins = PINS.get(b, {})
    rows = []
    for k, name in (("ai", T("Entradas analógicas (AI)")), ("di", T("Entradas digitales (DI)")),
                    ("do", T("Salidas digitales (DO)")), ("ao", T("Salidas analógicas (AO, DAC)")),
                    ("pwm", "PWM")):
        cnt = n.get(k) or 0
        if not cnt:
            rows.append("<tr><td><b>%s</b></td><td>-</td></tr>" % name)
            continue
        lst = ", ".join("%s%d = %s" % (k.upper(), i, pins.get(k, [])[i] if i < len(pins.get(k, []))
                                       else "?") for i in range(cnt))
        rows.append("<tr><td><b>%s</b></td><td>%s</td></tr>" % (name, lst))
    return ("<h3>%s</h3><p>%s %s · Vref <b>%.1f V</b></p>"
            "<p>%s</p><table cellspacing=4>%s</table>") % (
        T(BOARD_NAMES.get(b, b)), T("Firmware"), "%s %s" % (d["variant"], d["version"]), vref,
        T("El ADC convierte de 0 a %.1f V en 0 a 4095 cuentas: cada cuenta vale %.2f mV. "
          "El DAC y el PWM son de 8 bits: 256 pasos de %.1f mV.") % (
            vref, vref / 4095 * 1000, vref / 255 * 1000),
        "".join(rows))


class ProjectWindow(QMainWindow):
    def __init__(self, app, path=None):
        QMainWindow.__init__(self)
        self.app = app
        self.path = path
        self.data = {"camilab_project": 1, "name": T("Mi proyecto"), "port": "SIM",
                     "instruments": [], "notes": ""}
        if path:
            with open(path, encoding="utf-8") as f:
                self.data.update(json.load(f))
        self.setWindowIcon(app_icon(True))
        self.resize(820, 640)
        w = QWidget()
        w.setObjectName("panel")
        self.setCentralWidget(w)
        lay = QVBoxLayout(w)
        g = QGroupBox(T("Proyecto"))
        f = QFormLayout(g)
        self.ed_name = QLineEdit(self.data["name"])
        f.addRow(T("Nombre"), self.ed_name)
        lay.addWidget(g)
        g = QGroupBox(T("Tarjeta"))
        v = QVBoxLayout(g)
        hl = QHBoxLayout()
        self.cb_port = QComboBox()
        self.cb_port.setEditable(True)
        b1 = QPushButton(T("Actualizar"))
        b2 = QPushButton(T("Probar conexión"))
        hl.addWidget(QLabel(T("Puerto")))
        hl.addWidget(self.cb_port, 1)
        hl.addWidget(b1)
        hl.addWidget(b2)
        v.addLayout(hl)
        v.addWidget(QLabel(T("Los bloques 'Abrir puerto' con puerto (proyecto) usan este.")))
        self.info = QTextBrowser()
        self.info.setMinimumHeight(150)
        self.info.setHtml(T("Presiona 'Probar conexión' para ver la tarjeta, su Vref y el pin "
                            "de cada canal."))
        v.addWidget(self.info)
        lay.addWidget(g)
        g = QGroupBox(T("Instrumentos (.cami)"))
        hl = QHBoxLayout(g)
        self.lst = QListWidget()
        hl.addWidget(self.lst, 1)
        bv = QVBoxLayout()
        for txt, fn in ((T("Nuevo"), self.new_vi), (T("Agregar existente..."), self.add_existing),
                        (T("Abrir"), self.open_sel), (T("Quitar de la lista"), self.remove_sel)):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            bv.addWidget(b)
        bv.addStretch(1)
        hl.addLayout(bv)
        lay.addWidget(g, 1)
        g = QGroupBox(T("Notas"))
        vl = QVBoxLayout(g)
        self.notes = QPlainTextEdit(self.data.get("notes", ""))
        self.notes.setMaximumHeight(90)
        vl.addWidget(self.notes)
        lay.addWidget(g)
        mb = self.menuBar()
        m = mb.addMenu(T("Archivo"))
        add_actions(m, [(T("Guardar proyecto"), "Ctrl+S", self.save),
                        (T("Guardar proyecto como..."), "Ctrl+Shift+S", self.save_as)])
        m.addAction(T("Inicio de CamiLab")).triggered.connect(self.app.show_home)
        m.addAction(T("Cerrar")).triggered.connect(self.close)
        b1.clicked.connect(self.scan)
        b2.clicked.connect(self.probe)
        self.lst.itemDoubleClicked.connect(lambda _i: self.open_sel())
        self.ed_name.textChanged.connect(self.touch)
        self.notes.textChanged.connect(self.touch)
        self.cb_port.currentTextChanged.connect(self.touch)
        self.scan()
        self.refresh_list()
        self.dirty = False
        self.title()

    def name(self):
        return self.ed_name.text() or T("Proyecto")

    def folder(self):
        return os.path.dirname(self.path) if self.path else os.path.expanduser("~")

    def port(self):
        d = self.cb_port.currentData()
        txt = self.cb_port.currentText().strip()
        if d and self.cb_port.itemText(self.cb_port.currentIndex()) == txt:
            return d
        return txt or "SIM"

    def touch(self, *_a):
        self.dirty = True
        self.title()

    def title(self):
        self.setWindowTitle("%s%s - %s" % (os.path.basename(self.path) if self.path else
                                           self.name() + EXT_PROJ, " *" if self.dirty else "", APP))

    def scan(self):
        cur = self.data.get("port", "SIM")
        self.cb_port.blockSignals(True)
        self.cb_port.clear()
        self.cb_port.addItem(T("SIM (tarjeta simulada)"), "SIM")
        for p in core.list_ports():
            self.cb_port.addItem(p["port"] + ("  -  " + p["label"] if p["label"] else ""), p["port"])
        i = self.cb_port.findData(cur)
        if i >= 0:
            self.cb_port.setCurrentIndex(i)
        else:
            self.cb_port.setEditText(cur)
        self.cb_port.blockSignals(False)

    def probe(self):
        self.info.setHtml(T("Conectando con %s (unos 2 s)...") % self.port())
        self.th = IdentThread(self.port())
        self.th.done.connect(self.probed)
        self.th.start()

    def probed(self, d, err):
        if d is None:
            self.info.setHtml("<p style='color:#a01010'><b>%s</b></p>" % err)
        else:
            self.info.setHtml(board_html(d))

    def abs_paths(self):
        base = self.folder()
        return [os.path.normpath(os.path.join(base, p)) for p in self.data["instruments"]]

    def refresh_list(self):
        self.lst.clear()
        for rel, ab in zip(self.data["instruments"], self.abs_paths()):
            it = QListWidgetItem(rel + ("" if os.path.isfile(ab) else "   " + T("(no existe)")))
            it.setData(Qt.UserRole, ab)
            self.lst.addItem(it)

    def add_instrument(self, path):
        base = self.folder()
        try:
            rel = os.path.relpath(path, base)
        except ValueError:
            rel = path
        if rel not in self.data["instruments"]:
            self.data["instruments"].append(rel)
            self.refresh_list()
            self.touch()

    def new_vi(self):
        if not self.path:
            QMessageBox.information(self, APP, T("Guarda primero el proyecto."))
            if not self.save_as():
                return
        self.app.new_vi(project=self)

    def add_existing(self):
        paths, _f = QFileDialog.getOpenFileNames(self, T("Agregar instrumentos"), self.folder(),
                                                 T("Instrumento CamiLab") + " (*%s)" % EXT_VI)
        for p in paths:
            self.add_instrument(p)

    def open_sel(self):
        it = self.lst.currentItem()
        if it:
            self.app.open_path(it.data(Qt.UserRole), project=self)

    def remove_sel(self):
        r = self.lst.currentRow()
        if r >= 0:
            del self.data["instruments"][r]
            self.refresh_list()
            self.touch()

    def collect(self):
        self.data["name"] = self.ed_name.text()
        self.data["port"] = self.port()
        self.data["notes"] = self.notes.toPlainText()
        return self.data

    def save(self):
        if not self.path:
            return self.save_as()
        try:
            save_json(self.collect(), self.path)
        except OSError as e:
            QMessageBox.warning(self, APP, T("No se pudo guardar: %s") % e)
            return False
        self.dirty = False
        self.title()
        return True

    def save_as(self):
        old = self.abs_paths()
        p, _f = QFileDialog.getSaveFileName(self, T("Guardar proyecto"),
                                            os.path.join(self.folder(), self.name() + EXT_PROJ),
                                            T("Proyecto CamiLab") + " (*%s)" % EXT_PROJ)
        if not p:
            return False
        if not p.lower().endswith(EXT_PROJ):
            p += EXT_PROJ
        self.path = p
        self.data["instruments"] = []
        for ab in old:
            self.add_instrument(ab)
        return self.save()

    def closeEvent(self, e):
        if self.dirty:
            r = QMessageBox.question(self, APP, T("¿Guardar los cambios de %s?") % self.name(),
                                     QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if r == QMessageBox.Cancel or (r == QMessageBox.Save and not self.save()):
                e.ignore()
                return
        self.app.forget(self)
        e.accept()
