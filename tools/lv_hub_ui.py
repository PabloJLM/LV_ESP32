import math
import time
import traceback

try:
    from PyQt5.QtCore import Qt, QThread, QRectF, QPointF, QSize, QTimer, pyqtSignal as Signal
    from PyQt5.QtGui import (QColor, QFont, QLinearGradient, QPainter, QPen,
                             QPixmap, QPolygonF, QRadialGradient, QBrush, QIcon)
    from PyQt5.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QComboBox,
                                 QDial, QDoubleSpinBox, QFileDialog, QFrame,
                                 QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                                 QMessageBox, QPushButton, QSizePolicy, QSpinBox,
                                 QToolButton, QVBoxLayout, QWidget)
    QT_NAME = "PyQt5"
except ImportError:
    from PySide6.QtCore import Qt, QThread, QRectF, QPointF, QSize, QTimer, Signal
    from PySide6.QtGui import (QColor, QFont, QLinearGradient, QPainter, QPen,
                               QPixmap, QPolygonF, QRadialGradient, QBrush, QIcon)
    from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QComboBox,
                                   QDial, QDoubleSpinBox, QFileDialog, QFrame,
                                   QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                                   QMessageBox, QPushButton, QSizePolicy, QSpinBox,
                                   QToolButton, QVBoxLayout, QWidget)
    QT_NAME = "PySide6"

from lv_hub_dev import DeviceError
from lv_hub_lang import T

C_CH = [QColor("#00ff40"), QColor("#c8ff28"), QColor("#40c8ff"), QColor("#ff7ad9")]
C_MARK = QColor("#ff9a2e")

QSS = """
QWidget            { color:#1a1a1a; font-size:12px;
                     font-family:"Tahoma","Segoe UI","DejaVu Sans",sans-serif; }
QWidget#panel      { background:#d4d4d4; }
QLabel#status      { color:#303030; padding:2px 4px; }
QLabel#status[kind="err"] { color:#a01010; font-weight:bold; }
QLabel#status[kind="ok"]  { color:#106a10; font-weight:bold; }
QLabel#board       { background:#0a0a0a; color:#00ff40; border:2px solid;
                     border-color:#707070 #ffffff #ffffff #707070;
                     font-family:"Consolas","DejaVu Sans Mono","Courier New",monospace;
                     font-size:13px; font-weight:bold; padding:4px 10px; }

QGroupBox          { background:#e4e4e4; border:2px solid;
                     border-color:#ffffff #8a8a8a #8a8a8a #ffffff;
                     margin-top:18px; padding:8px 6px 6px 6px; }
QGroupBox::title   { subcontrol-origin:margin; subcontrol-position:top left;
                     left:4px; padding:0 2px; color:#1a1a1a; font-weight:bold; }
QGroupBox QLabel#hint, QLabel#hint { color:#4a4a4a; font-size:11px; }

QComboBox, QDoubleSpinBox, QSpinBox {
                     background:#ffffff; color:#111; border:2px solid;
                     border-color:#808080 #f4f4f4 #f4f4f4 #808080;
                     padding:2px 4px; min-height:18px; }
QComboBox QAbstractItemView { background:#ffffff; color:#111;
                     selection-background-color:#1a7a1a; selection-color:#fff; }
QComboBox:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled { color:#888; background:#ececec; }

QPushButton        { background:#dcdcdc; color:#111; border:2px solid;
                     border-color:#ffffff #707070 #707070 #ffffff; padding:4px 12px; }
QPushButton:hover  { background:#e8e8e8; }
QPushButton:pressed, QPushButton:checked {
                     background:#b8e6b8; border-color:#707070 #ffffff #ffffff #707070; }
QPushButton:disabled { color:#999; }
QPushButton#run    { font-weight:bold; color:#0a6a0a; min-width:70px; }
QPushButton#stop   { font-weight:bold; color:#a00000; min-width:70px; }
QPushButton#mode   { min-width:46px; min-height:30px; font-size:14px; font-weight:bold; }

QLabel#lcd         { background:#0a0a0a; color:#00ff40; border:3px solid;
                     border-color:#707070 #ffffff #ffffff #707070;
                     font-family:"Consolas","DejaVu Sans Mono","Courier New",monospace;
                     font-size:46px; font-weight:bold; padding:6px 14px; }
QLabel#lcdsmall    { background:#0a0a0a; color:#7cff9a; border:2px solid;
                     border-color:#707070 #ffffff #ffffff #707070;
                     font-family:"Consolas","DejaVu Sans Mono","Courier New",monospace;
                     font-size:12px; padding:3px 8px; }
QLabel#readout     { background:#0a0a0a; color:#00ff40; border:2px solid;
                     border-color:#707070 #ffffff #ffffff #707070;
                     font-family:"Consolas","DejaVu Sans Mono","Courier New",monospace;
                     font-size:12px; padding:4px 8px; }
QDial              { background:#c8c8c8; }
"""


_PREF = [(1e9, "G"), (1e6, "M"), (1e3, "k"), (1.0, ""), (1e-3, "m"),
         (1e-6, "µ"), (1e-9, "n"), (1e-12, "p")]


def eng(v, unit="", digits=4, sign=False):
    if v is None or isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return "----  " + unit
    a = abs(v)
    for f, p in _PREF:
        if a >= f * 0.9995 or f == 1e-12:
            x = v / f
            break
    if a == 0:
        x, p = 0.0, ""
    dec = max(0, digits - 1 - (int(math.floor(math.log10(abs(x)))) if x else 0))
    s = ("%+.*f" if sign else "%.*f") % (dec, x)
    return "%s %s%s" % (s, p, unit)


def fmt_time(t):
    return eng(t, "s", 3)


class Runner(QThread):
    posted = Signal(object)
    failed = Signal(str)

    def __init__(self, fn):
        QThread.__init__(self)
        self.fn = fn
        self.alive = True

    def post(self, obj):
        self.posted.emit(obj)

    def run(self):
        try:
            self.fn(self)
        except DeviceError as e:
            self.failed.emit(str(e))
        except Exception as e:
            traceback.print_exc()
            self.failed.emit(T("Error inesperado: %s") % e)


def sleep_while(r, seconds):
    end = time.perf_counter() + seconds
    while r.alive:
        left = end - time.perf_counter()
        if left <= 0:
            return
        time.sleep(min(0.02, left))


def dspin(lo, hi, val, dec=2, suffix="", step=None):
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setDecimals(dec)
    s.setValue(val)
    if suffix:
        s.setSuffix(" " + suffix)
    s.setSingleStep(step if step is not None else 10 ** (-dec) * 10 if dec else 1)
    s.setKeyboardTracking(False)
    return s


def ispin(lo, hi, val, suffix=""):
    s = QSpinBox()
    s.setRange(lo, hi)
    s.setValue(val)
    if suffix:
        s.setSuffix(" " + suffix)
    s.setKeyboardTracking(False)
    return s


def combo(items):
    c = QComboBox()
    for it in items:
        if isinstance(it, tuple):
            c.addItem(it[1], it[0])
        else:
            c.addItem(it, it)
    return c


def group(title):
    g = QGroupBox(title)
    form = QGridLayout(g)
    form.setHorizontalSpacing(8)
    form.setVerticalSpacing(6)
    return g, form


def row(form, r, text, *widgets):
    lab = QLabel(text)
    form.addWidget(lab, r, 0)
    for i, w in enumerate(widgets):
        form.addWidget(w, r, 1 + i)
    return lab


def hint(text):
    l = QLabel(text)
    l.setObjectName("hint")
    l.setWordWrap(True)
    return l


class Led(QWidget):
    def __init__(self, color="#36ff4c", size=22):
        QWidget.__init__(self)
        self.on = False
        self.color = QColor(color)
        self.setFixedSize(size, size)

    def set(self, on):
        on = bool(on)
        if on != self.on:
            self.on = on
            self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(2, 2, self.width() - 4, self.height() - 4)
        p.setBrush(QColor("#9a9a9a"))
        p.setPen(QPen(QColor("#505050"), 1))
        p.drawEllipse(r)
        k = r.adjusted(3, 3, -3, -3)
        g = QRadialGradient(k.center().x() - k.width() * 0.2,
                            k.center().y() - k.height() * 0.25, k.width() * 0.75)
        if self.on:
            g.setColorAt(0, QColor("#e8ffe8"))
            g.setColorAt(0.35, self.color)
            g.setColorAt(1, self.color.darker(170))
        else:
            g.setColorAt(0, QColor("#2f6a2f"))
            g.setColorAt(1, QColor("#0a2a0a"))
        p.setBrush(QBrush(g))
        p.setPen(Qt.NoPen)
        p.drawEllipse(k)


class Knob(QWidget):
    valueChanged = Signal(float)

    def __init__(self, title, lo, hi, val, dec=2, suffix="", log=False):
        QWidget.__init__(self)
        self.lo, self.hi, self.log = lo, hi, log
        self._guard = False
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        t = QLabel(title)
        t.setAlignment(Qt.AlignCenter)
        self.dial = QDial()
        self.dial.setRange(0, 1000)
        self.dial.setNotchesVisible(True)
        self.dial.setFixedSize(78, 78)
        self.spin = dspin(lo, hi, val, dec, suffix)
        v.addWidget(t)
        v.addWidget(self.dial, 0, Qt.AlignHCenter)
        v.addWidget(self.spin)
        self.dial.valueChanged.connect(self._from_dial)
        self.spin.valueChanged.connect(self._from_spin)
        self._from_spin(val)

    def _pos(self, x):
        if self.log:
            x = max(self.lo, x)
            return int(round(1000 * (math.log10(x) - math.log10(self.lo)) /
                             (math.log10(self.hi) - math.log10(self.lo))))
        return int(round(1000 * (x - self.lo) / float(self.hi - self.lo or 1)))

    def _val(self, pos):
        f = pos / 1000.0
        if self.log:
            return 10 ** (math.log10(self.lo) + f * (math.log10(self.hi) - math.log10(self.lo)))
        return self.lo + f * (self.hi - self.lo)

    def _from_dial(self, pos):
        if self._guard:
            return
        self._guard = True
        self.spin.setValue(self._val(pos))
        self._guard = False
        self.valueChanged.emit(self.spin.value())

    def _from_spin(self, x):
        if not self._guard:
            self._guard = True
            self.dial.setValue(self._pos(x))
            self._guard = False
        self.valueChanged.emit(x)

    def value(self):
        return self.spin.value()

    def setValue(self, x):
        self.spin.setValue(x)

    def setRange(self, lo, hi):
        self.lo, self.hi = lo, hi
        self.spin.setRange(lo, hi)
        self._from_spin(self.spin.value())


def _clean(v, rng):
    span = abs(rng[1] - rng[0]) or 1.0
    return 0.0 if abs(v) < span * 1e-9 else round(v, 12)


class Plot(QWidget):
    def __init__(self, ticks=True, nx=10, ny=8):
        QWidget.__init__(self)
        self.xr = (0.0, 1.0)
        self.yr = (-4.0, 4.0)
        self.nx, self.ny = nx, ny
        self.logx = False
        self.ticks = ticks
        self.scope_ticks = not ticks
        self.traces = []
        self.hlines = []
        self.vlines = []
        self.overlay = []
        self.xfmt = lambda v: "%g" % v
        self.yfmt = lambda v: "%g" % v
        self.xlabel = ""
        self.ylabel = ""
        self.c_frame = QColor("#d4d4d4")
        self.c_screen = QColor("#000000")
        self.c_text = QColor("#1a1a1a")
        self.c_grid = QColor("#2e4a2e")
        self.c_grid2 = QColor("#4f7a4f")
        self.setMinimumSize(320, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_traces(self, traces):
        self.traces = traces
        self.update()

    def _mx(self, x, R):
        x0, x1 = self.xr
        if self.logx:
            if x <= 0:
                return None
            f = (math.log10(x) - math.log10(x0)) / (math.log10(x1) - math.log10(x0))
        else:
            f = (x - x0) / float(x1 - x0 or 1e-12)
        return R.left() + f * R.width()

    def _my(self, y, R):
        y0, y1 = self.yr
        f = (y - y0) / float(y1 - y0 or 1e-12)
        return R.bottom() - f * R.height()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        ml = 58 if self.ticks else 4
        mb = (34 if self.xlabel else 22) if self.ticks else 4
        p.fillRect(self.rect(), self.c_frame)
        R = QRectF(ml, 4, W - ml - 8, H - mb - 4)
        p.fillRect(R, self.c_screen)
        p.setPen(QPen(QColor("#707070"), 2))
        p.drawRect(R.adjusted(-1, -1, 1, 1))
        small = QFont(self.font())
        small.setPointSizeF(max(7.0, small.pointSizeF() - 1.5))
        p.setFont(small)

        dot = QPen(self.c_grid, 1, Qt.DotLine)
        mid = QPen(self.c_grid2, 1, Qt.DotLine)
        txt = self.c_text

        xs_grid = []
        if self.logx:
            x0, x1 = self.xr
            few = math.log10(x1 / x0) <= 2.2
            d = math.floor(math.log10(x0))
            while 10 ** d <= x1 * 1.0001:
                for m in (1, 2, 5):
                    v = m * 10 ** d
                    if x0 * 0.9999 <= v <= x1 * 1.0001:
                        xs_grid.append((v, m == 1 or few))
                d += 1
        else:
            for i in range(self.nx + 1):
                v = self.xr[0] + (self.xr[1] - self.xr[0]) * i / self.nx
                xs_grid.append((_clean(v, self.xr), True))
        for v, major in xs_grid:
            X = self._mx(v, R)
            center = (not self.logx) and abs(X - R.center().x()) < 0.5
            p.setPen(mid if center else dot)
            p.drawLine(QPointF(X, R.top()), QPointF(X, R.bottom()))
            if self.ticks and major:
                p.setPen(txt)
                s = self.xfmt(v)
                p.drawText(QRectF(X - 40, R.bottom() + 2, 80, 16), Qt.AlignCenter, s)
        for i in range(self.ny + 1):
            v = _clean(self.yr[0] + (self.yr[1] - self.yr[0]) * i / self.ny, self.yr)
            Y = self._my(v, R)
            center = abs(Y - R.center().y()) < 0.5
            p.setPen(mid if center else dot)
            p.drawLine(QPointF(R.left(), Y), QPointF(R.right(), Y))
            if self.ticks:
                p.setPen(txt)
                p.drawText(QRectF(0, Y - 8, ml - 6, 16),
                           Qt.AlignRight | Qt.AlignVCenter, self.yfmt(v))
        if self.scope_ticks and not self.logx:
            p.setPen(QPen(self.c_grid2, 1))
            cx, cy = R.center().x(), R.center().y()
            for i in range(self.nx * 5 + 1):
                X = R.left() + R.width() * i / (self.nx * 5)
                p.drawLine(QPointF(X, cy - 3), QPointF(X, cy + 3))
            for i in range(self.ny * 5 + 1):
                Y = R.top() + R.height() * i / (self.ny * 5)
                p.drawLine(QPointF(cx - 3, Y), QPointF(cx + 3, Y))
        if self.ticks and self.xlabel:
            p.setPen(txt)
            p.drawText(QRectF(R.left(), R.bottom() + 17, R.width(), 16),
                       Qt.AlignCenter, self.xlabel)
        if self.ticks and self.ylabel:
            p.save()
            p.setPen(txt)
            p.translate(10, R.center().y())
            p.rotate(-90)
            p.drawText(QRectF(-R.height() / 2, -8, R.height(), 16), Qt.AlignCenter, self.ylabel)
            p.restore()

        p.setClipRect(R)
        for y, c in self.hlines:
            p.setPen(QPen(c, 1, Qt.DashLine))
            Y = self._my(y, R)
            p.drawLine(QPointF(R.left(), Y), QPointF(R.right(), Y))
        for x, c in self.vlines:
            X = self._mx(x, R)
            if X is not None:
                p.setPen(QPen(c, 1, Qt.DashLine))
                p.drawLine(QPointF(X, R.top()), QPointF(X, R.bottom()))
        for tr in self.traces:
            xs, ys, c = tr[0], tr[1], tr[2]
            dots = len(tr) > 3 and tr[3]
            pts = []
            for x, y in zip(xs, ys):
                if y is None:
                    continue
                X = self._mx(x, R)
                if X is None:
                    continue
                pts.append(QPointF(X, self._my(y, R)))
            if not pts:
                continue
            p.setPen(QPen(c, 1.6))
            if len(pts) > 1:
                p.drawPolyline(QPolygonF(pts))
            if dots or len(pts) == 1:
                p.setBrush(c)
                for q in pts:
                    p.drawEllipse(q, 2.6, 2.6)
                p.setBrush(Qt.NoBrush)
        p.setClipping(False)
        y = R.top() + 4
        for c, t in self.overlay:
            p.setPen(c)
            p.drawText(QRectF(R.left() + 6, y, R.width() - 12, 16),
                       Qt.AlignLeft | Qt.AlignVCenter, t)
            y += 15


class InstrumentWindow(QWidget):
    TITLE = "Instrumento"
    HELP = ""
    MODES = True

    def __init__(self, hub):
        QWidget.__init__(self)
        self.hub = hub
        self.runner = None
        self.cfg = {}
        self._once = False
        self.setObjectName("panel")
        self.setStyleSheet(QSS)
        self.setWindowTitle("LV_ESP32 — " + self.TITLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 4, 0, 6)
        root.setSpacing(6)

        self.body = QWidget()
        self.body.setObjectName("panel")
        root.addWidget(self.body, 1)

        ctl, cf = group(T("Control del instrumento"))
        self.lb_dev = QLabel("")
        self.lb_dev.setObjectName("board")
        cf.addWidget(QLabel(T("Tarjeta")), 0, 0)
        cf.addWidget(self.lb_dev, 1, 0)
        self.cb_mode = combo([T("Continuo"), T("Una vez")])
        if self.MODES:
            cf.addWidget(QLabel(T("Modo de adquisición")), 0, 1)
            cf.addWidget(self.cb_mode, 1, 1)
        cf.setColumnStretch(2, 1)
        self.extra = QHBoxLayout()
        cf.addLayout(self.extra, 1, 3)
        self.btn_run = QPushButton("▶  Run")
        self.btn_run.setObjectName("run")
        self.btn_stop = QPushButton("■  Stop")
        self.btn_stop.setObjectName("stop")
        self.btn_help = QPushButton(T("Ayuda"))
        cf.addWidget(self.btn_run, 1, 4)
        cf.addWidget(self.btn_stop, 1, 5)
        cf.addWidget(self.btn_help, 1, 6)
        wrap = QHBoxLayout()
        wrap.setContentsMargins(8, 0, 8, 0)
        wrap.addWidget(ctl)
        root.addLayout(wrap)

        self.lb_status = QLabel("")
        self.lb_status.setObjectName("status")
        self.lb_status.setWordWrap(True)
        sw = QHBoxLayout()
        sw.setContentsMargins(8, 0, 8, 0)
        sw.addWidget(self.lb_status)
        root.addLayout(sw)

        self.btn_run.clicked.connect(self.run)
        self.btn_stop.clicked.connect(self.stop)
        self.btn_help.clicked.connect(self.show_help)

        self.build()
        self.device_changed()
        self.sync()
        self._buttons(False)

    def build(self):
        pass

    def work(self, r):
        pass

    def on_data(self, obj):
        pass

    def on_start(self):
        return True

    def on_stopped(self):
        pass

    def help_text(self):
        return self.HELP

    def sync(self):
        pass

    @property
    def dev(self):
        return self.hub.dev

    def watch(self, *widgets):
        for w in widgets:
            if isinstance(w, QComboBox):
                w.currentIndexChanged.connect(lambda *_a: self.sync())
            elif isinstance(w, (QDoubleSpinBox, QSpinBox, Knob)):
                w.valueChanged.connect(lambda *_a: self.sync())
            elif isinstance(w, (QCheckBox, QPushButton)):
                w.toggled.connect(lambda *_a: self.sync())

    @property
    def once(self):
        return self._once

    def set_status(self, text, kind=""):
        self.lb_status.setText(text)
        self.lb_status.setProperty("kind", kind)
        self.lb_status.style().unpolish(self.lb_status)
        self.lb_status.style().polish(self.lb_status)

    def device_changed(self):
        d = self.dev
        self.lb_dev.setText(("%s  ·  %s" % (d.board_name, d.port)) if d.connected
                            else T("(sin conexión)"))
        self.setWindowTitle("LV_ESP32 — %s%s" % (
            self.TITLE, ("  —  " + d.board_name) if d.connected else ""))
        self.refresh_channels()
        self.sync()
        if not d.connected:
            self.stop()

    def refresh_channels(self):
        pass

    def vref_changed(self):
        v = self.dev.vref
        if getattr(self, "_seen_vref", None) == v:
            return False
        self._seen_vref = v
        return True

    @staticmethod
    def fill(cb, items, keep=True):
        old = cb.currentData()
        cb.blockSignals(True)
        cb.clear()
        for it in items:
            if isinstance(it, tuple):
                cb.addItem(it[1], it[0])
            else:
                cb.addItem(it, it)
        if keep and old is not None:
            i = cb.findData(old)
            if i >= 0:
                cb.setCurrentIndex(i)
        cb.blockSignals(False)

    def _buttons(self, running):
        self.btn_run.setEnabled(not running)
        self.btn_stop.setEnabled(running)

    @property
    def running(self):
        return self.runner is not None and self.runner.isRunning()

    def run(self):
        if self.running:
            return
        if not self.dev.connected:
            self.set_status(T("Conecta una tarjeta desde el launcher."), "err")
            return
        self.sync()
        self._once = self.MODES and self.cb_mode.currentIndex() == 1
        if self.on_start() is False:
            return
        self.runner = Runner(self.work)
        self.runner.posted.connect(self.on_data)
        self.runner.failed.connect(lambda m: self.set_status(m, "err"))
        self.runner.finished.connect(self._finished)
        self._buttons(True)
        self.runner.start()

    def stop(self):
        if self.runner is not None:
            self.runner.alive = False

    def stop_wait(self):
        if self.runner is not None:
            self.runner.alive = False
            self.runner.wait(3000)

    def _finished(self):
        self._buttons(False)
        self.on_stopped()

    def show_help(self):
        QMessageBox.information(self, self.TITLE, self.help_text())

    def closeEvent(self, e):
        self.stop_wait()
        self.hub.forget(self)
        e.accept()

    def save_csv(self, header, rows, name="datos"):
        import csv
        import os
        default = os.path.join(os.path.expanduser("~"),
                               "%s_%s.csv" % (name, time.strftime("%Y%m%d_%H%M%S")))
        path, _f = QFileDialog.getSaveFileName(self, T("Guardar datos"), default,
                                               "CSV (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(header)
                w.writerows(rows)
            self.set_status(T("Guardado: %s  (%d filas)") % (path, len(rows)), "ok")
        except OSError as e:
            self.set_status(T("No se pudo guardar: %s") % e, "err")


def make_icon(kind, size=64):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    s = size / 64.0
    W = QPen(QColor("#2a2a2a"), 2.6 * s)
    W.setCapStyle(Qt.RoundCap)
    p.setPen(W)
    f = QFont()
    f.setBold(True)

    def wave(fn, x0=12, x1=52, yc=32, amp=11, n=60):
        pts = [QPointF((x0 + (x1 - x0) * i / n) * s, (yc - amp * fn(i / float(n))) * s)
               for i in range(n + 1)]
        p.drawPolyline(QPolygonF(pts))

    if kind == "dmm":
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(12 * s, 14 * s, 40 * s, 20 * s), 3 * s, 3 * s)
        f.setPixelSize(int(14 * s))
        p.setFont(f)
        p.setPen(QColor("#2a2a2a"))
        p.drawText(QRectF(12 * s, 14 * s, 40 * s, 20 * s), Qt.AlignCenter, "8.88")
        p.setPen(W)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(32 * s, 46 * s), 7 * s, 7 * s)
    elif kind == "scope":
        p.setBrush(Qt.NoBrush)
        p.drawRect(QRectF(11 * s, 13 * s, 42 * s, 34 * s))
        p.setPen(QPen(QColor("#0a8a1a"), 2.2 * s))
        wave(lambda u: math.sin(u * 4 * math.pi), 13, 51, 30, 10)
        p.setPen(W)
        p.drawLine(QPointF(24 * s, 52 * s), QPointF(40 * s, 52 * s))
    elif kind == "fgen":
        wave(lambda u: math.sin(u * 2 * math.pi), 10, 34, 26, 9)
        p.drawPolyline(QPolygonF([QPointF(36 * s, 35 * s), QPointF(36 * s, 17 * s),
                                  QPointF(45 * s, 17 * s), QPointF(45 * s, 35 * s),
                                  QPointF(54 * s, 35 * s)]))
        p.drawLine(QPointF(14 * s, 47 * s), QPointF(50 * s, 47 * s))
        p.drawLine(QPointF(44 * s, 42 * s), QPointF(50 * s, 47 * s))
        p.drawLine(QPointF(44 * s, 52 * s), QPointF(50 * s, 47 * s))
    elif kind == "vps":
        p.drawRect(QRectF(16 * s, 20 * s, 32 * s, 28 * s))
        p.drawLine(QPointF(24 * s, 14 * s), QPointF(24 * s, 20 * s))
        p.drawLine(QPointF(40 * s, 14 * s), QPointF(40 * s, 20 * s))
        f.setPixelSize(int(15 * s))
        p.setFont(f)
        p.drawText(QRectF(16 * s, 20 * s, 32 * s, 28 * s), Qt.AlignCenter, "+ −")
    elif kind == "bode":
        p.drawLine(QPointF(12 * s, 12 * s), QPointF(12 * s, 52 * s))
        p.drawLine(QPointF(12 * s, 52 * s), QPointF(54 * s, 52 * s))
        p.drawPolyline(QPolygonF([QPointF(14 * s, 22 * s), QPointF(30 * s, 22 * s),
                                  QPointF(36 * s, 26 * s), QPointF(52 * s, 46 * s)]))
    elif kind in ("digin", "digout"):
        for i, on in enumerate((1, 0, 1, 1)):
            p.setBrush(QColor("#10c030") if on else QColor("#0a3a0a"))
            p.setPen(QPen(QColor("#2a2a2a"), 1.4 * s))
            p.drawEllipse(QPointF((17 + i * 10) * s, 22 * s), 4 * s, 4 * s)
        p.setPen(W)
        if kind == "digin":
            p.drawLine(QPointF(32 * s, 50 * s), QPointF(32 * s, 34 * s))
            p.drawLine(QPointF(26 * s, 40 * s), QPointF(32 * s, 34 * s))
            p.drawLine(QPointF(38 * s, 40 * s), QPointF(32 * s, 34 * s))
        else:
            p.drawLine(QPointF(32 * s, 34 * s), QPointF(32 * s, 50 * s))
            p.drawLine(QPointF(26 * s, 44 * s), QPointF(32 * s, 50 * s))
            p.drawLine(QPointF(38 * s, 44 * s), QPointF(32 * s, 50 * s))
    p.end()
    return pm
