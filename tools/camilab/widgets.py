import math
import os

from PyQt5.QtCore import pyqtSignal, QBuffer, QByteArray, QIODevice, QMimeData, QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QDrag, QFont, QImage, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QColorDialog, QComboBox, QDial, QDoubleSpinBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMenu, QMessageBox, QPushButton, QSizePolicy, QSlider, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget)

from hub.lang import T
from hub.ui import C_CH, Led, Plot

import base64
from camilab.config import APP, fill_ports, port_value, PROJ, style_plot, TH


PMIME = "application/x-camipanel"
MMIME = "application/x-camimove"


def nice_range(lo, hi, n=5):
    if hi - lo < 1e-9:
        hi, lo = hi + 0.5, lo - 0.5
    raw = (hi - lo) / float(n)
    e = 10 ** math.floor(math.log10(raw))
    st = next(m * e for m in (1, 2, 5, 10) if raw <= m * e)
    lo = math.floor(lo / st) * st
    hi = math.ceil(hi / st) * st
    return lo, hi, max(1, int(round((hi - lo) / st)))


def img_to_b64(path, maxpx=900):
    im = QImage(path)
    if im.isNull():
        return None
    if max(im.width(), im.height()) > maxpx:
        im = im.scaled(maxpx, maxpx, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.WriteOnly)
    im.save(buf, "PNG")
    return base64.b64encode(bytes(ba)).decode("ascii")


def b64_to_pix(data):
    pm = QPixmap()
    if data:
        pm.loadFromData(base64.b64decode(data), "PNG")
    return pm


def pick_image(parent):
    path, _f = QFileDialog.getOpenFileName(parent, T("Elegir imagen"), os.path.expanduser("~"),
                                           T("Imágenes") + " (*.png *.jpg *.jpeg *.bmp *.gif)")
    if not path:
        return None
    data = img_to_b64(path)
    if data is None:
        QMessageBox.warning(parent, APP, T("No se pudo leer la imagen."))
    return data


def fmt(v, dec=3):
    if isinstance(v, bool):
        return "T" if v else "F"
    if isinstance(v, (int, float)):
        if v != v:
            return "NaN"
        return "%.*f" % (int(dec), v)
    if isinstance(v, (list, tuple)):
        return "[%d]" % len(v)
    return str(v)


REPS = (("double", "Double"), ("int", "Entero (I32)"), ("byte", "Byte (U8)"))
LIMITS = {"int": (-2147483648, 2147483647), "byte": (0, 255)}


def as_rep(v, rep):
    """Pasa un número a la representación elegida. Entero y byte redondean y se limitan."""
    v = float(v)
    if rep not in LIMITS:
        return v
    lo, hi = LIMITS[rep]
    return int(max(lo, min(hi, round(v))))


def num_text(v, rep="double"):
    return "%d" % v if rep in LIMITS else "%g" % v


class ArrayBox(QWidget):
    """Una columna con los elementos de un arreglo. Editable (control) o solo lectura."""
    changed = pyqtSignal()

    def __init__(self, typ, rep, editable):
        QWidget.__init__(self)
        self.typ, self.rep, self.editable = typ, rep, editable
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        self.tab = QTableWidget(0, 1)
        self.tab.horizontalHeader().setVisible(False)
        self.tab.horizontalHeader().setStretchLastSection(True)
        self.tab.setMinimumHeight(70)
        v.addWidget(self.tab, 1)
        if editable:
            h = QHBoxLayout()
            for text, tip, fn in (("+", T("Agregar elemento"), self.add),
                                  ("-", T("Quitar el último"), self.remove)):
                b = QPushButton(text)
                b.setToolTip(tip)
                b.clicked.connect(fn)
                h.addWidget(b)
            v.addLayout(h)
            self.tab.itemChanged.connect(lambda _i: self.changed.emit())
        else:
            self.tab.setEditTriggers(QTableWidget.NoEditTriggers)

    def item(self, x):
        if self.typ == "bool":
            it = QTableWidgetItem("T" if x else "F")
            if self.editable:
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                it.setCheckState(Qt.Checked if x else Qt.Unchecked)
                it.setText("")
            return it
        if self.typ == "num":
            try:
                return QTableWidgetItem(num_text(as_rep(x, self.rep), self.rep))
            except (TypeError, ValueError):
                return QTableWidgetItem(str(x))
        return QTableWidgetItem(str(x))

    def set_values(self, vals):
        self.tab.blockSignals(True)
        self.tab.setRowCount(len(vals))
        for i, x in enumerate(vals):
            self.tab.setItem(i, 0, self.item(x))
        self.tab.blockSignals(False)

    def values(self):
        out = []
        for i in range(self.tab.rowCount()):
            it = self.tab.item(i, 0)
            if self.typ == "bool":
                out.append(it.checkState() == Qt.Checked)
            elif self.typ == "num":
                try:
                    out.append(as_rep(it.text().replace(",", "."), self.rep))
                except ValueError:
                    out.append(0)
            else:
                out.append(it.text())
        return out

    def add(self):
        self.set_values(self.values() + [{"num": 0, "bool": False, "str": ""}[self.typ]])
        self.changed.emit()

    def remove(self):
        self.set_values(self.values()[:-1])
        self.changed.emit()


class ImageBox(QLabel):
    def __init__(self, data=None):
        QLabel.__init__(self)
        self.pm = b64_to_pix(data)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(20, 20)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

    def resizeEvent(self, e):
        if not self.pm.isNull():
            self.setPixmap(self.pm.scaled(self.size(), Qt.KeepAspectRatio,
                                          Qt.SmoothTransformation))
        QLabel.resizeEvent(self, e)


class Meter(QWidget):
    def __init__(self, p, w, h):
        QWidget.__init__(self)
        self.p = p
        self.v = None
        self.setMinimumSize(w, h)

    def put(self, v):
        self.v = v
        self.update()

    def limits(self):
        return float(self.p.get("min", 0)), float(self.p.get("max", 10))

    def number(self):
        v = self.v
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) and v == v else None

    def readout(self, v):
        txt = fmt(v, self.p.get("dec", 2)) if v is not None else "---"
        return txt + " " + self.p.get("units", "")


class Gauge(Meter):
    def __init__(self, p):
        Meter.__init__(self, p, 90, 80)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        lo, hi = self.limits()
        s = max(40.0, min(self.width() - 10, (self.height() - 14) / 0.86))
        R = QRectF((self.width() - s) / 2, 6, s, s)
        p.setPen(QPen(TH["lo"], 2))
        p.setBrush(TH["input"])
        p.drawPie(R, -45 * 16, 270 * 16)
        c = R.center()
        r = s / 2
        f = QFont()
        f.setPixelSize(max(8, int(s / 14)))
        p.setFont(f)
        for k in range(11):
            a = math.radians(225 - 27 * k)
            x0, y0 = c.x() + math.cos(a) * r * 0.82, c.y() - math.sin(a) * r * 0.82
            x1, y1 = c.x() + math.cos(a) * r * 0.95, c.y() - math.sin(a) * r * 0.95
            p.setPen(QPen(TH["text"], 2 if k % 5 == 0 else 1))
            p.drawLine(QPointF(x0, y0), QPointF(x1, y1))
            if k % 5 == 0:
                tx, ty = c.x() + math.cos(a) * r * 0.66, c.y() - math.sin(a) * r * 0.66
                p.drawText(QRectF(tx - 30, ty - 8, 60, 16), Qt.AlignCenter,
                           "%g" % round(lo + (hi - lo) * k / 10.0, 3))
        v = self.number()
        if v is not None:
            fr = max(0.0, min(1.0, (v - lo) / ((hi - lo) or 1e-12)))
            a = math.radians(225 - 270 * fr)
            p.setPen(QPen(TH["alert"], 3, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(c, QPointF(c.x() + math.cos(a) * r * 0.8, c.y() - math.sin(a) * r * 0.8))
        p.setBrush(TH["text"])
        p.setPen(Qt.NoPen)
        p.drawEllipse(c, 5, 5)
        f.setPixelSize(max(10, int(s / 9)))
        f.setBold(True)
        p.setFont(f)
        p.setPen(TH["accent"])
        p.drawText(QRectF(R.left(), c.y() + r * 0.5, R.width(), r * 0.36), Qt.AlignCenter,
                   self.readout(v))


class Bar(Meter):
    def __init__(self, p):
        Meter.__init__(self, p, 60, 80)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        lo, hi = self.limits()
        H = self.height() - 30
        bw = min(26, self.width() / 3)
        x = self.width() / 2 - bw / 2 - 14
        R = QRectF(x, 6, bw, H)
        p.setPen(QPen(TH["lo"], 2))
        p.setBrush(TH["screen"])
        p.drawRect(R)
        v = self.number()
        if v is not None:
            fr = max(0.0, min(1.0, (v - lo) / ((hi - lo) or 1e-12)))
            p.fillRect(QRectF(R.left() + 2, R.bottom() - 2 - (H - 4) * fr, bw - 4, (H - 4) * fr),
                       TH["signal"])
        f = QFont()
        f.setPixelSize(10)
        p.setFont(f)
        p.setPen(TH["text"])
        for k in range(6):
            y = R.bottom() - H * k / 5.0
            p.drawLine(QPointF(R.right() + 2, y), QPointF(R.right() + 7, y))
            p.drawText(QRectF(R.right() + 9, y - 7, 60, 14), Qt.AlignLeft | Qt.AlignVCenter,
                       "%g" % round(lo + (hi - lo) * k / 5.0, 3))
        f.setBold(True)
        f.setPixelSize(12)
        p.setFont(f)
        p.setPen(TH["accent"])
        p.drawText(QRectF(0, self.height() - 22, self.width(), 20), Qt.AlignCenter,
                   self.readout(v))


class PItem(QFrame):
    def __init__(self, panel, iid):
        QFrame.__init__(self, panel.grid)
        self.panel = panel
        self.iid = iid
        self.setObjectName("pitem")
        self.hist = []
        self.mhist = []
        self.chart_n = 0
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 6)
        lay.setSpacing(3)
        self.head = QLabel("")
        self.head.setObjectName("phead")
        lay.addWidget(self.head)
        self.body = QWidget()
        self.bl = QVBoxLayout(self.body)
        self.bl.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.body, 1)
        self.build()

    @property
    def node(self):
        return self.panel.doc["nodes"].get(self.iid)

    @property
    def kind(self):
        n = self.node
        return n["type"] if n else "image"

    def build(self):
        while self.bl.count():
            w = self.bl.takeAt(0).widget()
            if w:
                w.setParent(None)
        k = self.kind
        n = self.node
        p = n["params"] if n else {}
        self.head.setText(p.get("label", "") if n else "")
        self.head.setVisible(bool(n))
        self.w = None
        if k == "image":
            self.w = ImageBox(self.panel.doc["panel"]["items"][self.iid].get("data"))
        elif k == "ind_img":
            self.w = ImageBox(p.get("image"))
            self.w.setVisible(False)
        elif k == "ctl_num":
            rep = p.get("rep", "double")
            lo, hi = float(p.get("min", 0)), float(p.get("max", 10))
            if rep in LIMITS:
                lo, hi = max(lo, LIMITS[rep][0]), min(hi, LIMITS[rep][1])
            self.w = QDoubleSpinBox()
            self.w.setRange(lo, hi)
            self.w.setDecimals(0 if rep in LIMITS else int(p.get("dec", 3)))
            self.w.setSingleStep(1 if rep in LIMITS else (hi - lo) / 100.0)
            if p.get("units"):
                self.w.setSuffix(" " + p["units"])
            self.w.setValue(float(p.get("value", 0)))
            self.w.setMinimumHeight(30)
            f = self.w.font()
            f.setPointSize(13)
            self.w.setFont(f)
            self.w.valueChanged.connect(self.changed)
        elif k in ("ctl_knob", "ctl_slider"):
            box = QWidget()
            v = QVBoxLayout(box)
            v.setContentsMargins(0, 0, 0, 0)
            if k == "ctl_knob":
                self.dial = QDial()
                self.dial.setNotchesVisible(True)
                self.dial.setMinimumSize(60, 60)
            else:
                self.dial = QSlider(Qt.Horizontal)
            self.dial.setRange(0, 1000)
            lo, hi = float(p.get("min", 0)), float(p.get("max", 10))
            self.dial.setValue(int(round(1000 * (float(p.get("value", 0)) - lo) / ((hi - lo) or 1))))
            self.val = QLabel("")
            self.val.setObjectName("readout")
            self.val.setAlignment(Qt.AlignCenter)
            v.addWidget(self.dial, 1)
            v.addWidget(self.val)
            self.w = box
            self.dial.valueChanged.connect(self.changed)
        elif k == "ctl_str":
            self.w = QLineEdit(str(p.get("value", "")))
            self.w.textChanged.connect(self.changed)
        elif k == "ctl_port":
            box = QWidget()
            hl = QHBoxLayout(box)
            hl.setContentsMargins(0, 0, 0, 0)
            self.cb = QComboBox()
            self.cb.setEditable(True)
            fill_ports(self.cb, p.get("value", PROJ))
            b = QPushButton(T("Buscar"))
            b.clicked.connect(lambda: (fill_ports(self.cb, port_value(self.cb)), self.changed()))
            hl.addWidget(self.cb, 1)
            hl.addWidget(b)
            self.w = box
            self.cb.currentIndexChanged.connect(self.changed)
            self.cb.editTextChanged.connect(self.changed)
        elif k == "ctl_ring":
            self.w = QComboBox()
            for o in [x.strip() for x in str(p.get("options", "")).split(";") if x.strip()]:
                self.w.addItem(o)
            self.w.setCurrentIndex(int(p.get("value", 0)))
            self.w.currentIndexChanged.connect(self.changed)
        elif k == "ctl_color":
            self.w = QPushButton("")
            self.w.setMinimumHeight(34)
            self.w.clicked.connect(self.pick_color)
        elif k in ("ctl_bool", "ctl_stop"):
            box = QWidget()
            hl = QHBoxLayout(box)
            hl.setContentsMargins(0, 0, 0, 0)
            self.btn = QPushButton("STOP" if k == "ctl_stop" else "OFF")
            self.btn.setCheckable(True)
            self.btn.setMinimumHeight(34)
            if k == "ctl_stop":
                self.btn.setObjectName("stopbtn")
            self.btn.setChecked(bool(p.get("value", False)) and k == "ctl_bool")
            self.led = Led(TH["signal"].name(), 22)
            hl.addWidget(self.btn, 1)
            hl.addWidget(self.led)
            self.w = box
            self.btn.toggled.connect(self.changed)
        elif k == "ind_num":
            self.w = QLabel("---")
            self.w.setObjectName("lcd")
            self.w.setStyleSheet("font-size:%dpx;" % max(18, min(48, 14 * self.span_h())))
            self.w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        elif k == "ind_led":
            box = QWidget()
            hl = QHBoxLayout(box)
            self.led = Led(TH["signal"].name(), 40)
            hl.addStretch(1)
            hl.addWidget(self.led)
            hl.addStretch(1)
            self.w = box
        elif "_arr_" in k:
            self.w = ArrayBox(k.rsplit("_", 1)[1], p.get("rep", "double"), k.startswith("ctl"))
            if k.startswith("ctl"):
                self.w.set_values(p.get("value", []))
                self.w.changed.connect(self.changed)
        elif k == "ind_gauge":
            self.w = Gauge(p)
        elif k == "ind_bar":
            self.w = Bar(p)
        elif k in ("ind_chart", "ind_graph", "ind_xy"):
            self.w = Plot()
            style_plot(self.w)
            self.w.setMinimumSize(120, 90)
            self.w.yfmt = lambda v: "%g" % round(v, 4)
            self.w.xfmt = lambda v: "%g" % round(v, 2)
            self.w.nx, self.w.ny = 5, 5
        elif k == "ind_str":
            self.w = QLabel("")
            self.w.setObjectName("readout")
            self.w.setWordWrap(True)
            self.w.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        if self.w is not None:
            self.bl.addWidget(self.w)
        self.changed()
        self.reset()

    def span_h(self):
        it = self.panel.doc["panel"]["items"].get(self.iid, {})
        return it.get("rs", 1)

    def value(self):
        k = self.kind
        p = self.node["params"] if self.node else {}
        if k == "ctl_num":
            return as_rep(self.w.value(), p.get("rep", "double"))
        if k.startswith("ctl_arr"):
            return self.w.values()
        if k in ("ctl_knob", "ctl_slider"):
            lo, hi = float(p.get("min", 0)), float(p.get("max", 10))
            return lo + (hi - lo) * self.dial.value() / 1000.0
        if k == "ctl_str":
            return self.w.text()
        if k == "ctl_port":
            return port_value(self.cb)
        if k == "ctl_ring":
            return float(max(0, self.w.currentIndex()))
        if k == "ctl_color":
            return list(p.get("value", [255, 0, 0]))
        if k in ("ctl_bool", "ctl_stop"):
            return self.btn.isChecked()
        return None

    def changed(self, *_a):
        k = self.kind
        if not k.startswith("ctl"):
            return
        v = self.value()
        p = self.node["params"]
        if k in ("ctl_knob", "ctl_slider"):
            self.val.setText(fmt(v, p.get("dec", 3)) + " " + p.get("units", ""))
        if k == "ctl_color":
            r, g, b = v
            self.w.setText("R %d  G %d  B %d" % (r, g, b))
            fg = "#000000" if (r * 0.3 + g * 0.59 + b * 0.11) > 128 else "#ffffff"
            self.w.setStyleSheet("QPushButton{background:rgb(%d,%d,%d);color:%s;"
                                 "font-weight:bold;}" % (r, g, b, fg))
        if k == "ctl_bool":
            self.btn.setText("ON" if v else "OFF")
            self.led.set(v)
        if k == "ctl_stop":
            self.led.set(v)
        self.panel.ctl_values[self.iid] = v
        if not self.panel.running and k != "ctl_stop" and p.get("value") != v:
            p["value"] = v
            self.panel.modified()

    def pick_color(self):
        r, g, b = self.node["params"].get("value", [255, 0, 0])
        c = QColorDialog.getColor(QColor(int(r), int(g), int(b)), self, T("Color"))
        if c.isValid():
            self.node["params"]["value"] = [c.red(), c.green(), c.blue()]
            self.changed()

    def reset(self):
        k = self.kind
        self.hist = []
        self.mhist = []
        self.chart_n = 0
        if k == "ind_num":
            self.w.setText("---")
        elif k == "ind_led":
            self.led.set(False)
        elif k == "ind_img":
            self.w.setVisible(False)
        elif k in ("ind_gauge", "ind_bar"):
            self.w.put(None)
        elif k in ("ind_chart", "ind_graph", "ind_xy"):
            self.w.overlay = []
            self.w.xr, self.w.yr = (0, 10), (0, 1)
            self.w.set_traces([])
        elif k == "ind_str":
            self.w.setText("")
        elif k.startswith("ind_arr"):
            self.w.set_values([])
        elif k == "ctl_stop":
            self.btn.setChecked(False)

    def put(self, v):
        k = self.kind
        p = self.node["params"]
        if k == "ind_num":
            rep, dec = p.get("rep", "double"), p.get("dec", 3)
            if rep in LIMITS and isinstance(v, (int, float)) and not isinstance(v, bool):
                v, dec = as_rep(v, rep), 0
            self.w.setText(fmt(v, dec) + (" " + p["units"] if p.get("units") else ""))
        elif k.startswith("ind_arr"):
            self.w.set_values(list(v) if isinstance(v, (list, tuple)) else [v])
        elif k == "ind_led":
            self.led.set(bool(v) if not isinstance(v, (list, tuple)) else any(v))
        elif k == "ind_img":
            self.w.setVisible(bool(v) if not isinstance(v, (list, tuple)) else any(v))
        elif k in ("ind_gauge", "ind_bar"):
            self.w.put(v)
        elif k == "ind_str":
            self.w.setText(fmt(v) if not isinstance(v, str) else v)
        elif k == "ind_graph":
            if isinstance(v, (list, tuple)) and v and all(isinstance(r, (list, tuple)) for r in v):
                rows = [[float(x) for x in r if isinstance(x, (int, float))] for r in v]
                self.draw_multi([(list(range(len(r))), r) for r in rows if r])
                return
            ys = [float(x) for x in (v if isinstance(v, (list, tuple)) else [v])
                  if isinstance(x, (int, float))]
            self.draw(list(range(len(ys))), ys)
        elif k == "ind_xy":
            if isinstance(v, (list, tuple)) and len(v) == 2:
                xs, ys = [list(a) if isinstance(a, (list, tuple)) else [a] for a in v]
                pts = [(float(x), float(y)) for x, y in zip(xs, ys)
                       if isinstance(x, (int, float)) and isinstance(y, (int, float))]
                if pts:
                    self.draw_multi([([a for a, _b in pts], [b for _a, b in pts])], xfit=True)

    def feed(self, vals):
        p = self.node["params"]
        if p.get("multi"):
            self.feed_multi(vals, int(p.get("hist", 200)) or 200)
            return
        for v in vals:
            if isinstance(v, (list, tuple)):
                self.hist.extend(float(x) for x in v if isinstance(x, (int, float)))
            elif isinstance(v, (int, float)):
                self.hist.append(float(v))
        n = int(p.get("hist", 200)) or 200
        self.hist = self.hist[-n:]
        self.chart_n = getattr(self, "chart_n", 0) + len(vals)
        x0 = max(0, self.chart_n - len(self.hist))
        self.draw([x0 + i for i in range(len(self.hist))], self.hist, n)

    def feed_multi(self, vals, n):
        for v in vals:
            row = [float(x) for x in (v if isinstance(v, (list, tuple)) else [v])
                   if isinstance(x, (int, float))]
            if row:
                self.mhist.append(row)
        self.mhist = self.mhist[-n:]
        self.chart_n += len(vals)
        if not self.mhist:
            return
        x0 = max(0, self.chart_n - len(self.mhist))
        k = max(len(r) for r in self.mhist)
        traces = []
        for j in range(k):
            pts = [(x0 + i, r[j]) for i, r in enumerate(self.mhist) if j < len(r)]
            traces.append(([a for a, _b in pts], [b for _a, b in pts]))
        self.draw_multi(traces, span=n)

    def draw_multi(self, traces, span=None, xfit=False):
        pl = self.w
        traces = [(xs, ys) for xs, ys in traces if ys]
        if not traces:
            return
        allx = [x for xs, _ys in traces for x in xs]
        ally = [y for _xs, ys in traces for y in ys]
        lo, hi, ny = nice_range(min(ally), max(ally), 5)
        pl.yr = (lo, hi)
        pl.ny = ny
        if span:
            pl.xr = (traces[0][0][0], traces[0][0][0] + span)
            pl.nx = 5
        elif xfit:
            x0, x1, nx = nice_range(min(allx), max(allx), 5)
            pl.xr, pl.nx = (x0, x1), nx
        else:
            x0, x1, nx = nice_range(0, max(1, max(len(xs) for xs, _ys in traces) - 1), 5)
            pl.xr, pl.nx = (0, x1), nx
        dec = self.node["params"].get("dec", 3)
        pl.overlay = [(C_CH[j % len(C_CH)], fmt(ys[-1], dec)) for j, (_xs, ys) in enumerate(traces)]
        pl.set_traces([(xs, ys, C_CH[j % len(C_CH)]) for j, (xs, ys) in enumerate(traces)])

    def draw(self, xs, ys, span=None):
        pl = self.w
        if not ys:
            return
        lo, hi, ny = nice_range(min(ys), max(ys), 5)
        pl.yr = (lo, hi)
        pl.ny = ny
        if span:
            pl.xr = (xs[0], xs[0] + span)
            pl.nx = 5
        else:
            x0, x1, nx = nice_range(0, max(1, len(ys) - 1), 5)
            pl.xr = (0, x1)
            pl.nx = nx
        pl.overlay = [(TH["signal"], fmt(ys[-1], self.node["params"].get("dec", 3)) + " " +
                       self.node["params"].get("units", ""))]
        pl.set_traces([(xs, ys, TH["signal"])])

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self.panel.running:
            self.drag_start = e.pos()
        QFrame.mousePressEvent(self, e)

    def mouseMoveEvent(self, e):
        if not self.panel.running and getattr(self, "drag_start", None) is not None and \
                (e.pos() - self.drag_start).manhattanLength() > 8:
            self.drag_start = None
            md = QMimeData()
            md.setData(MMIME, self.iid.encode())
            d = QDrag(self)
            d.setMimeData(md)
            d.setPixmap(self.grab().scaled(160, 120, Qt.KeepAspectRatio))
            d.exec_(Qt.MoveAction)
            return
        QFrame.mouseMoveEvent(self, e)

    def mouseDoubleClickEvent(self, e):
        if not self.panel.running:
            self.panel.props(self.iid)

    def contextMenuEvent(self, e):
        if self.panel.running:
            return
        self.panel.item_menu(self.iid, e.globalPos())


class FreeText(QLabel):
    def __init__(self, panel, t):
        QLabel.__init__(self, panel)
        self.panel = panel
        self.t = t
        self.setObjectName("freetext")
        self.setText(t["text"])
        f = self.font()
        f.setPointSize(int(t.get("size", 11)))
        f.setBold(bool(t.get("bold", False)))
        self.setFont(f)
        self.adjustSize()
        self.off = None

    def place(self):
        r = self.panel.rect()
        self.adjustSize()
        self.move(int(self.t["x"] * r.width()), int(self.t["y"] * r.height()))
        self.raise_()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self.panel.running:
            self.off = e.pos()

    def mouseMoveEvent(self, e):
        if self.off is not None:
            p = self.mapToParent(e.pos() - self.off)
            r = self.panel.rect()
            self.move(max(0, min(r.width() - 20, p.x())), max(0, min(r.height() - 10, p.y())))

    def mouseReleaseEvent(self, e):
        if self.off is not None:
            r = self.panel.rect()
            self.t["x"] = self.x() / float(max(1, r.width()))
            self.t["y"] = self.y() / float(max(1, r.height()))
            self.off = None
            self.panel.modified()

    def mouseDoubleClickEvent(self, e):
        if not self.panel.running:
            self.panel.edit_text(self)

    def contextMenuEvent(self, e):
        if self.panel.running:
            return
        m = QMenu()
        a1 = m.addAction(T("Editar texto..."))
        sub = m.addMenu(T("Tamaño de letra"))
        sizes = {}
        for s in (9, 11, 14, 18, 24, 32):
            sizes[sub.addAction("%d pt" % s)] = s
        a2 = m.addAction(T("Negrita"))
        a2.setCheckable(True)
        a2.setChecked(bool(self.t.get("bold")))
        m.addSeparator()
        a3 = m.addAction(T("Eliminar"))
        a = m.exec_(e.globalPos())
        if a == a1:
            self.panel.edit_text(self)
        elif a in sizes:
            self.t["size"] = sizes[a]
            self.panel.rebuild_texts()
        elif a == a2:
            self.t["bold"] = not self.t.get("bold")
            self.panel.rebuild_texts()
        elif a == a3:
            self.panel.doc["panel"]["texts"].remove(self.t)
            self.panel.rebuild_texts()
        self.panel.modified()


class Grid(QWidget):
    GAP = 6

    def __init__(self, panel):
        QWidget.__init__(self)
        self.panel = panel
        self.setAcceptDrops(True)
        self.hover = None
        self.setMinimumSize(300, 200)

    def cell_rect(self, r, c, rs=1, cs=1):
        P = self.panel.doc["panel"]
        W = self.width() - self.GAP
        H = self.height() - self.GAP
        cw = W / float(P["cols"])
        ch = H / float(P["rows"])
        return QRectF(self.GAP + c * cw, self.GAP + r * ch, cs * cw - self.GAP, rs * ch - self.GAP)

    def cell_at(self, pos):
        P = self.panel.doc["panel"]
        cw = (self.width() - self.GAP) / float(P["cols"])
        ch = (self.height() - self.GAP) / float(P["rows"])
        c = int((pos.x() - self.GAP / 2) // cw)
        r = int((pos.y() - self.GAP / 2) // ch)
        if 0 <= r < P["rows"] and 0 <= c < P["cols"]:
            return r, c
        return None

    def layout_items(self):
        for iid, w in self.panel.widgets.items():
            it = self.panel.doc["panel"]["items"][iid]
            w.setGeometry(self.cell_rect(it["r"], it["c"], it["rs"], it["cs"]).toRect())
            w.show()

    def resizeEvent(self, e):
        self.layout_items()

    def paintEvent(self, e):
        if self.panel.running:
            return
        p = QPainter(self)
        P = self.panel.doc["panel"]
        for r in range(P["rows"]):
            for c in range(P["cols"]):
                R = self.cell_rect(r, c)
                hot = self.hover == (r, c)
                p.setPen(QPen(TH["accent"] if hot else TH["text2"], 1.5 if hot else 1,
                              Qt.DashLine))
                p.setBrush(QColor(TH["accent"].red(), TH["accent"].green(), TH["accent"].blue(),
                                  70) if hot else Qt.NoBrush)
                p.drawRect(R)

    def dragEnterEvent(self, e):
        md = e.mimeData()
        if (md.hasFormat(PMIME) or md.hasFormat(MMIME)) and not self.panel.running:
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        self.hover = self.cell_at(e.pos())
        self.update()
        e.acceptProposedAction()

    def dragLeaveEvent(self, e):
        self.hover = None
        self.update()

    def dropEvent(self, e):
        self.hover = None
        self.update()
        cell = self.cell_at(e.pos())
        md = e.mimeData()
        if md.hasFormat(PMIME):
            tid = bytes(md.data(PMIME)).decode()
            if tid == "text":
                self.panel.add_text(self.mapTo(self.panel, e.pos()))
            elif cell:
                self.panel.add_item(tid, cell)
        elif md.hasFormat(MMIME) and cell:
            self.panel.move_item(bytes(md.data(MMIME)).decode(), cell)
        e.acceptProposedAction()


class Banner(QFrame):
    def __init__(self, panel, key):
        QFrame.__init__(self)
        self.panel = panel
        self.key = key
        self.setObjectName("banner")
        hl = QHBoxLayout(self)
        hl.setContentsMargins(10, 4, 10, 4)
        self.img = QLabel()
        self.txt = QLabel()
        self.txt.setObjectName("btitle" if key == "title" else "bfooter")
        self.txt.setWordWrap(True)
        hl.addWidget(self.img)
        hl.addWidget(self.txt, 1)

    def refresh(self):
        d = self.panel.doc["panel"][self.key]
        pm = b64_to_pix(d.get("image"))
        h = 54 if self.key == "title" else 36
        if not pm.isNull():
            self.img.setPixmap(pm.scaledToHeight(h, Qt.SmoothTransformation))
            self.img.show()
        else:
            self.img.hide()
        self.txt.setText(d.get("text", ""))
        on = d.get("on", True) and (bool(d.get("text")) or not pm.isNull())
        self.setVisible(on or (not self.panel.running and self.key == "title"))
        if not d.get("text") and pm.isNull():
            self.txt.setText(T("Título del panel (doble clic para editar)")
                             if self.key == "title" else "")

    def mouseDoubleClickEvent(self, e):
        if not self.panel.running:
            self.panel.config()
