from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QLineEdit,
    QSpinBox)

import core
from hub.lang import T

from camilab.bloques import SPECS
from camilab.config import PROJ


def port_list():
    out = [(PROJ, T("(proyecto) - el del archivo .camp")), ("SIM", T("SIM (tarjeta simulada)"))]
    for p in core.list_ports():
        out.append((p["port"], p["port"] + ("  -  " + p["label"] if p["label"] else "")))
    return out


class PropDialog(QDialog):
    def __init__(self, ed, nid, parent=None):
        QDialog.__init__(self, parent)
        self.ed = ed
        self.nid = nid
        n = ed.doc["nodes"][nid]
        s = SPECS[n["type"]]
        self.setWindowTitle(T("Propiedades") + " - " + T(s.label))
        f = QFormLayout(self)
        self.get = {}
        p = n["params"]
        if s.kind in ("ctl", "ind"):
            panel_fields(self, f, n)
        for name, kind, default, label in s.params:
            v = p.get(name, default)
            if kind == "num":
                self.num(f, name, T(label), v)
            elif kind == "bool":
                c = QCheckBox()
                c.setChecked(bool(v))
                f.addRow(T(label), c)
                self.get[name] = c.isChecked
            elif kind == "port":
                c = QComboBox()
                c.setEditable(True)
                for k, t in port_list():
                    c.addItem(t, k)
                i = c.findData(v)
                if i >= 0:
                    c.setCurrentIndex(i)
                else:
                    c.setEditText(v)
                f.addRow(T(label), c)
                self.get[name] = lambda c=c: (c.currentData() if c.currentText() ==
                                              c.itemText(c.currentIndex()) else
                                              c.currentText().strip())
            else:
                e = QLineEdit(str(v))
                f.addRow(T(label), e)
                self.get[name] = e.text
        if s.kind == "struct":
            if n["type"] in ("while", "for"):
                sp = QSpinBox()
                sp.setRange(0, 4)
                sp.setValue(int(p.get("sr", 0)))
                f.addRow(T("Shift registers"), sp)
                self.get["sr"] = sp.value
            else:
                sp = QSpinBox()
                sp.setRange(0, 6)
                sp.setValue(int(p.get("outs", 0)))
                f.addRow(T("Terminales de salida"), sp)
                self.get["outs"] = sp.value
        for name, typ, default, label in s.ins:
            if ed.is_wired(nid, name) or typ not in ("num", "bool", "str"):
                continue
            v = p.get("def_" + name, default)
            if typ == "num":
                self.num(f, "def_" + name, T("Si no se cablea: ") + T(label), v)
            elif typ == "bool":
                c = QCheckBox()
                c.setChecked(bool(v))
                f.addRow(T("Si no se cablea: ") + T(label), c)
                self.get["def_" + name] = c.isChecked
            else:
                e = QLineEdit(str(v))
                f.addRow(T("Si no se cablea: ") + T(label), e)
                self.get["def_" + name] = e.text
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)

    def num(self, f, key, label, v, dec=4):
        sp = QDoubleSpinBox()
        sp.setRange(-1e9, 1e9)
        sp.setDecimals(dec)
        sp.setValue(float(v))
        f.addRow(label, sp)
        self.get[key] = sp.value

    def values(self):
        return {k: g() for k, g in self.get.items()}


def panel_fields(dlg, f, n):
    p = n["params"]
    t = n["type"]
    e = QLineEdit(p.get("label", ""))
    f.addRow(T("Etiqueta"), e)
    dlg.get["label"] = e.text
    if t not in ("ctl_bool", "ctl_stop", "ind_led", "ctl_color", "ctl_ring", "ctl_str",
                 "ind_str", "ind_graph"):
        u = QLineEdit(p.get("units", ""))
        f.addRow(T("Unidades"), u)
        dlg.get["units"] = u.text
    if t in ("ctl_num", "ctl_knob", "ctl_slider", "ind_gauge", "ind_bar"):
        dlg.num(f, "min", T("Mínimo"), p.get("min", 0.0))
        dlg.num(f, "max", T("Máximo"), p.get("max", 10.0))
    if t in ("ctl_num", "ctl_knob", "ctl_slider"):
        dlg.num(f, "value", T("Valor inicial"), p.get("value", 0.0))
    if t == "ctl_ring":
        e2 = QLineEdit(p.get("options", ""))
        f.addRow(T("Opciones (separadas por ;)"), e2)
        dlg.get["options"] = e2.text
    if t in ("ctl_bool",):
        c = QCheckBox()
        c.setChecked(bool(p.get("value", False)))
        f.addRow(T("Valor inicial"), c)
        dlg.get["value"] = c.isChecked
    if t == "ind_chart":
        dlg.num(f, "hist", T("Puntos visibles"), p.get("hist", 200), 0)
    if t in ("ind_num", "ind_gauge", "ind_bar"):
        dlg.num(f, "dec", T("Decimales"), p.get("dec", 3), 0)
