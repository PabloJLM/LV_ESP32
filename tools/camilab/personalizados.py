import glob
import json
import os

from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QApplication, QComboBox, QDialog, QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QListWidget, QMessageBox, QPushButton, QTableWidget, QVBoxLayout, QWidget)

from hub.lang import T

from camilab import bloques
from camilab.bloques import CATS, CH, SES, SPECS, boolean, check_ack, need_ses, num, spec

DIR = os.path.join(os.path.expanduser("~"), "CamiLab", "bloques")
CAT = "Personalizados"
IN_TYPES = (("num", "Número (1 byte)"), ("str", "Texto"))
REPLIES = (("ack", "Confirmación (AA / XX)"), ("dig", "Digital (A0 / A1)"),
           ("int", "Número (línea)"), ("line", "Texto (línea)"))
OUT = {"ack": ("ok", "bool", "ok"), "dig": ("v", "bool", "valor"),
       "int": ("v", "num", "valor"), "line": ("v", "str", "texto")}
ERRORS = []


def parse_cmd(t):
    v = int(str(t).strip(), 0)
    if not 0 <= v <= 255:
        raise ValueError(T("El comando debe estar entre 0x00 y 0xFF."))
    return v


def frame(code, ins, inp):
    out = bytearray([code])
    for name, typ in ins:
        v = inp.get(name)
        if typ == "str":
            b = str("" if v is None else v).encode("latin-1", "replace")[:255]
            out.append(len(b))
            out += b
        else:
            out.append(int(max(0, min(255, round(num(v))))))
    return bytes(out)


def make_fn(label, code, ins, rep):
    def fn(ctx, node, inp):
        w = need_ses(inp["ses"])
        r = w.txrx(frame(code, ins, inp), "ack" if rep in ("ack", "dig") else "line")
        ctx.log(label, r)
        if rep == "ack":
            return {"ses": w, "ok": r.rx[:2] == b"AA"}
        if rep == "dig":
            if r.rx[:2] != b"A0" and r.rx[:2] != b"A1":
                check_ack(r)
            return {"ses": w, "v": r.rx[1:2] == b"1"}
        txt = r.rx.decode("latin-1", "replace").strip()
        if not txt:
            raise ValueError(T("Sin respuesta de la tarjeta (timeout)."))
        if rep == "int":
            return {"ses": w, "v": float(int(txt))}
        return {"ses": w, "v": txt}
    return fn


def add_json(path, d):
    tid = "usr_" + os.path.splitext(os.path.basename(path))[0]
    label = d["nombre"].strip()
    code = parse_cmd(d["cmd"])
    ins = [(n.strip(), t) for n, t in d.get("entradas", [])]
    rep = d.get("respuesta", "ack")
    if rep not in OUT or not label or any(not n or t not in ("num", "str") for n, t in ins):
        raise ValueError(T("Definición incompleta."))
    pins = [SES] + [(n, t, "" if t == "str" else 0.0, n) for n, t in ins]
    spec(tid, CAT, label, pins, [("ses", "ses", "sesión"), OUT[rep]],
         make_fn(label, code, ins, rep), kind="io", sym=d.get("sym") or label[:4].upper(),
         doc=d.get("doc") or "0x%02X" % code)


def add_py(path):
    g = {"spec": spec, "CAT": CAT, "SES": SES, "CH": CH, "num": num, "boolean": boolean,
         "need_ses": need_ses, "check_ack": check_ack, "T": T, "bloques": bloques}
    with open(path, encoding="utf-8") as f:
        exec(compile(f.read(), path, "exec"), g)


def load():
    for tid in [k for k, s in SPECS.items() if s.cat == CAT]:
        del SPECS[tid]
    if CAT in CATS:
        CATS.remove(CAT)
    del ERRORS[:]
    for path in sorted(glob.glob(os.path.join(DIR, "*.json"))):
        try:
            with open(path, encoding="utf-8") as f:
                add_json(path, json.load(f))
        except Exception as e:
            ERRORS.append("%s: %s" % (os.path.basename(path), e))
    for path in sorted(glob.glob(os.path.join(DIR, "*.py"))):
        try:
            add_py(path)
        except Exception as e:
            ERRORS.append("%s: %s" % (os.path.basename(path), e))


def refresh():
    load()
    from camilab.diagrama import Palette
    for w in QApplication.allWidgets():
        if isinstance(w, Palette):
            w.fill()


class BlocksDialog(QDialog):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setWindowTitle(T("Bloques personalizados"))
        self.resize(640, 380)
        self.lst = QListWidget()
        self.lst.currentRowChanged.connect(self.pick)
        self.name = QLineEdit()
        self.cmd = QLineEdit()
        self.cmd.setPlaceholderText("0x20")
        self.rep = QComboBox()
        for k, t in REPLIES:
            self.rep.addItem(T(t), k)
        self.tab = QTableWidget(0, 2)
        self.tab.setHorizontalHeaderLabels([T("Entrada"), T("Tipo")])
        self.tab.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tab.verticalHeader().hide()
        plus, minus = QPushButton("+"), QPushButton("-")
        plus.clicked.connect(lambda: self.add_row("", "num"))
        minus.clicked.connect(lambda: self.tab.removeRow(self.tab.rowCount() - 1))
        pm = QHBoxLayout()
        pm.addWidget(plus)
        pm.addWidget(minus)
        pm.addStretch(1)
        form = QFormLayout()
        form.addRow(T("Nombre"), self.name)
        form.addRow(T("Comando"), self.cmd)
        form.addRow(T("Respuesta"), self.rep)
        right = QVBoxLayout()
        right.addLayout(form)
        right.addWidget(self.tab, 1)
        right.addLayout(pm)
        rw = QWidget()
        rw.setLayout(right)
        top = QHBoxLayout()
        top.addWidget(self.lst, 1)
        top.addWidget(rw, 2)
        bts = QHBoxLayout()
        for t, fn in ((T("Nuevo"), self.new), (T("Guardar"), self.save),
                      (T("Eliminar"), self.delete), (T("Abrir carpeta"), self.folder)):
            b = QPushButton(t)
            b.clicked.connect(fn)
            bts.addWidget(b)
        bts.addStretch(1)
        self.err = QLabel()
        self.err.setWordWrap(True)
        self.err.setStyleSheet("color:#d03030")
        lay = QVBoxLayout(self)
        lay.addLayout(top, 1)
        lay.addWidget(self.err)
        lay.addLayout(bts)
        self.files = []
        self.reload_list()

    def add_row(self, n, t):
        r = self.tab.rowCount()
        self.tab.insertRow(r)
        self.tab.setCellWidget(r, 0, QLineEdit(n))
        c = QComboBox()
        for k, txt in IN_TYPES:
            c.addItem(T(txt), k)
        c.setCurrentIndex(max(0, c.findData(t)))
        self.tab.setCellWidget(r, 1, c)

    def reload_list(self, keep=None):
        self.files = sorted(glob.glob(os.path.join(DIR, "*.json")))
        self.lst.blockSignals(True)
        self.lst.clear()
        for p in self.files:
            try:
                with open(p, encoding="utf-8") as f:
                    self.lst.addItem(json.load(f).get("nombre", os.path.basename(p)))
            except (OSError, ValueError):
                self.lst.addItem(os.path.basename(p))
        self.lst.blockSignals(False)
        self.err.setText("\n".join(ERRORS))
        if keep in self.files:
            self.lst.setCurrentRow(self.files.index(keep))
        else:
            self.new()

    def pick(self, i):
        if not 0 <= i < len(self.files):
            return
        try:
            with open(self.files[i], encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError) as e:
            self.err.setText(str(e))
            return
        self.name.setText(d.get("nombre", ""))
        c = d.get("cmd", 0)
        self.cmd.setText("0x%02X" % c if isinstance(c, int) else str(c))
        self.rep.setCurrentIndex(max(0, self.rep.findData(d.get("respuesta", "ack"))))
        self.tab.setRowCount(0)
        for n, t in d.get("entradas", []):
            self.add_row(n, t)

    def new(self):
        self.lst.clearSelection()
        self.lst.setCurrentRow(-1)
        self.name.clear()
        self.cmd.clear()
        self.rep.setCurrentIndex(0)
        self.tab.setRowCount(0)

    def current(self):
        i = self.lst.currentRow()
        return self.files[i] if 0 <= i < len(self.files) else None

    def save(self):
        ins = [[self.tab.cellWidget(r, 0).text().strip(), self.tab.cellWidget(r, 1).currentData()]
               for r in range(self.tab.rowCount())]
        d = {"nombre": self.name.text().strip(), "cmd": self.cmd.text().strip(),
             "entradas": ins, "respuesta": self.rep.currentData()}
        try:
            d["cmd"] = parse_cmd(d["cmd"])
            if not d["nombre"] or any(not n for n, _t in ins):
                raise ValueError(T("Definición incompleta."))
        except ValueError as e:
            QMessageBox.warning(self, T("Bloques personalizados"), str(e))
            return
        path = self.current()
        if path is None:
            stem = "".join(ch if ch.isalnum() else "_" for ch in d["nombre"].lower()) or "bloque"
            path = os.path.join(DIR, stem + ".json")
            k = 2
            while os.path.exists(path):
                path = os.path.join(DIR, "%s_%d.json" % (stem, k))
                k += 1
        os.makedirs(DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        refresh()
        self.reload_list(path)

    def delete(self):
        path = self.current()
        if path is None:
            return
        if QMessageBox.question(self, T("Bloques personalizados"),
                                T("¿Eliminar este bloque?")) != QMessageBox.Yes:
            return
        os.remove(path)
        refresh()
        self.reload_list()

    def folder(self):
        os.makedirs(DIR, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(DIR))


def show(parent):
    BlocksDialog(parent).exec_()

