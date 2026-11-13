import argparse
import collections
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lv_hub_dev import Device, DeviceError, SimDevice
from lv_hub_lang import LANGS, T
import lv_hub_lang
from lv_hub_ui import (C_CH, C_MARK, QSS, QApplication, QButtonGroup,
                       QCheckBox, QColor, QFrame, QGridLayout, QHBoxLayout,
                       QIcon, QLabel, QPushButton, QSize, QSizePolicy, QToolButton, QVBoxLayout, QWidget, Qt, QTimer, Runner,
                       InstrumentWindow, Knob, Led, Plot, combo, dspin, eng,
                       fmt_time, group, hint, ispin, make_icon, row, sleep_while)

import lv_core

perf = time.perf_counter


def mean(v):
    return sum(v) / len(v) if v else 0.0


def stdev(v):
    if len(v) < 2:
        return 0.0
    m = mean(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / len(v))


def rms(v):
    return math.sqrt(sum(x * x for x in v) / len(v)) if v else 0.0


def freq_of(ts, vs):
    if len(vs) < 6:
        return None
    lo, hi = min(vs), max(vs)
    if hi - lo < 1e-3:
        return None
    m = (lo + hi) / 2
    h = (hi - lo) * 0.1
    state = vs[0] > m
    cross = []
    for i in range(1, len(vs)):
        if not state and vs[i] > m + h:
            state = True
            j = i
            while j > 0 and vs[j - 1] > m:
                j -= 1
            if j > 0 and vs[j] != vs[j - 1]:
                f = (m - vs[j - 1]) / (vs[j] - vs[j - 1])
                cross.append(ts[j - 1] + f * (ts[j] - ts[j - 1]))
            else:
                cross.append(ts[i])
        elif state and vs[i] < m - h:
            state = False
    if len(cross) < 2 or cross[-1] <= cross[0]:
        return None
    return (len(cross) - 1) / (cross[-1] - cross[0])


def sine_fit(ts, vs, f):
    w = 2 * math.pi * f
    A = [[0.0] * 3 for _ in range(3)]
    B = [0.0] * 3
    for t, v in zip(ts, vs):
        row_ = (math.sin(w * t), math.cos(w * t), 1.0)
        for i in range(3):
            B[i] += row_[i] * v
            for j in range(3):
                A[i][j] += row_[i] * row_[j]
    M = [A[i] + [B[i]] for i in range(3)]
    for c in range(3):
        p = max(range(c, 3), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        if abs(M[c][c]) < 1e-12:
            return 0.0, 0.0, mean(vs)
        for r in range(3):
            if r != c:
                k = M[r][c] / M[c][c]
                for j in range(c, 4):
                    M[r][j] -= k * M[c][j]
    a, b, cc = (M[i][3] / M[i][i] for i in range(3))
    return math.hypot(a, b), math.atan2(b, a), cc


def nice_step(span, n=8):
    raw = span / float(n)
    e = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 5, 10):
        if raw <= m * e:
            return m * e
    return 10 * e


def nice_range(lo, hi, n=8, zero=False):
    if zero:
        lo = min(lo, 0.0)
        hi = max(hi, 0.0)
    if hi - lo < 1e-9:
        hi, lo = hi + 0.5, lo - 0.5
    st = nice_step(hi - lo, n)
    lo = math.floor(lo / st) * st
    hi = math.ceil(hi / st) * st
    return lo, hi, max(1, int(round((hi - lo) / st)))


def ai_items(dev):
    return [(i, t) for i, t in enumerate(dev.channels("ai"))]


class DMM(InstrumentWindow):
    TITLE = T("Multímetro digital (DMM)")
    MODES_LIST = [("vdc", "V⎓", T("Voltaje DC")),
                  ("vac", "V~", T("Voltaje AC (RMS)")),
                  ("adc", "A⎓", T("Corriente DC (shunt)")),
                  ("ohm", "Ω", T("Resistencia")),
                  ("cont", "•)))", T("Continuidad"))]

    def build(self):
        lay = QVBoxLayout(self.body)
        lay.setContentsMargins(8, 4, 8, 0)

        disp, df = group(T("Pantalla"))
        self.lcd = QLabel("----")
        self.lcd.setObjectName("lcd")
        self.lcd.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lcd.setMinimumWidth(460)
        self.lb_mode = QLabel("")
        self.lb_mode.setObjectName("lcdsmall")
        self.lb_stats = QLabel("")
        self.lb_stats.setObjectName("lcdsmall")
        for l in (self.lcd, self.lb_mode, self.lb_stats):
            l.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        df.addWidget(self.lcd, 0, 0, 1, 2)
        df.addWidget(self.lb_mode, 1, 0)
        df.addWidget(self.lb_stats, 1, 1)
        lay.addWidget(disp)

        mid = QHBoxLayout()
        g, f = group(T("Configuración de medición"))
        self.bg = QButtonGroup(self)
        mrow = QHBoxLayout()
        for i, (key, sym, tip) in enumerate(self.MODES_LIST):
            b = QPushButton(sym)
            b.setObjectName("mode")
            b.setCheckable(True)
            b.setToolTip(tip)
            b.setProperty("key", key)
            self.bg.addButton(b, i)
            mrow.addWidget(b)
        self.bg.button(0).setChecked(True)
        f.addLayout(mrow, 0, 0, 1, 2)
        self.cb_ch = combo([])
        row(f, 1, T("Canal (rojo)"), self.cb_ch)
        self.sp_avg = ispin(1, 1000, 25, T("muestras"))
        row(f, 2, T("Promedio"), self.sp_avg)
        self.btn_null = QPushButton(T("Null (relativo)"))
        self.btn_null.setCheckable(True)
        f.addWidget(self.btn_null, 3, 0, 1, 2)
        mid.addWidget(g)

        g2, f2 = group(T("Ajustes"))
        self.sp_fac = dspin(0.001, 1000, 1.0, 3, "×")
        self.sp_rref = dspin(1, 10e6, 10000, 0, "Ω", 100)
        self.sp_shunt = dspin(0.001, 100000, 1.0, 3, "Ω")
        self.sp_cont = dspin(1, 1000, 50, 0, "Ω")
        row(f2, 0, T("Factor de sonda"), self.sp_fac)
        row(f2, 1, T("R referencia (Ω)"), self.sp_rref)
        row(f2, 2, T("R shunt (A)"), self.sp_shunt)
        row(f2, 3, T("Umbral continuidad"), self.sp_cont)
        mid.addWidget(g2)

        g3, f3 = group(T("Conexiones"))
        self.lb_wire = hint("")
        self.lb_wire.setMinimumWidth(270)
        f3.addWidget(self.lb_wire, 0, 0)
        mid.addWidget(g3, 1)
        lay.addLayout(mid)
        lay.addStretch(1)

        self.watch(self.cb_ch, self.sp_avg, self.sp_fac, self.sp_rref,
                   self.sp_shunt, self.sp_cont)
        self.bg.buttonClicked.connect(lambda *_a: self._mode_changed())
        self.btn_null.toggled.connect(self._null)
        self.null = 0.0
        self.last = None
        self.mm = [None, None]
        self._beep_t = 0

    def refresh_channels(self):
        self.fill(self.cb_ch, ai_items(self.dev))

    def mode(self):
        return self.bg.checkedButton().property("key")

    def sync(self):
        self.cfg = {"ch": self.cb_ch.currentData() or 0, "n": self.sp_avg.value()}
        self._wiring()

    def _mode_changed(self):
        self.btn_null.setChecked(False)
        self.mm = [None, None]
        self.lcd.setText("----")
        self._wiring()

    def _null(self, on):
        self.null = self.last if (on and self.last is not None) else 0.0

    def _wiring(self):
        d = self.dev
        ch = self.cb_ch.currentData() or 0
        pin = "AI%d (%s)" % (ch, d.pin("ai", ch)) if d.connected else "AIx"
        vref = d.vref
        m = self.mode()
        txt = {
            "vdc": T("Punta roja → %s\nPunta negra → GND\n\nRango 0 a %.1f V. Para tensiones "
                   "mayores usa un divisor y escribe su relación en 'Factor de sonda' "
                   "(p. ej. 10 kΩ + 1 kΩ → 11×).") % (pin, vref),
            "vac": T("Punta roja → %s\nPunta negra → GND\n\nMide el RMS de la parte alterna. "
                   "La señal debe quedar entre 0 y %.1f V: móntala sobre un nivel DC "
                   "(divisor + capacitor).") % (pin, vref),
            "adc": T("Shunt en serie con la carga, del lado de GND.\n%s mide la caída del "
                   "shunt.\n\nI = V / Rshunt") % pin,
            "ohm": T("Divisor:\n%.1f V → R referencia → nodo → Rx → GND\nnodo → %s\n\n"
                   "Rx = Rref·V / (%.1f − V). Usa una Rref del orden de Rx.") % (vref, pin, vref),
            "cont": T("Mismo divisor que Ω (%.1f V → Rref → nodo → Rx → GND, nodo → %s).\n"
                    "Pita si R < umbral.") % (vref, pin),
        }[m]
        self.lb_wire.setText(txt)
        self.lb_mode.setText(dict((k, t) for k, _s, t in self.MODES_LIST)[m])

    def on_start(self):
        self.mm = [None, None]
        self.set_status(T("Midiendo..."), "")

    def work(self, r):
        dev = self.dev
        while r.alive:
            c = self.cfg
            vals = []
            for _ in range(c["n"]):
                if not r.alive:
                    return
                v = dev.ai(c["ch"])
                if v is not None:
                    vals.append(v)
            r.post({"mean": mean(vals), "std": stdev(vals), "n": len(vals)} if vals else None)
            if self.once:
                return
            sleep_while(r, 0.03)

    def on_data(self, st):
        if st is None:
            self.lcd.setText(T("No disp."))
            self.set_status(T("El canal no respondió (ADC2 ocupado por el WiFi o canal "
                            "inválido)."), "err")
            return
        m = self.mode()
        vref = self.dev.vref
        fac = self.sp_fac.value()
        txt, val = None, None
        if m == "vdc":
            val = st["mean"] * fac - self.null
            txt = eng(val, "V", 5, sign=True)
        elif m == "vac":
            val = st["std"] * fac - self.null
            txt = eng(val, "V", 5) + " rms"
        elif m == "adc":
            val = st["mean"] * fac / self.sp_shunt.value() - self.null
            txt = eng(val, "A", 5, sign=True)
        else:
            v = st["mean"]
            if v >= vref * 0.985:
                val = None
                txt = "OL   Ω"
            else:
                val = self.sp_rref.value() * v / (vref - v) - (self.null if m == "ohm" else 0)
                txt = eng(val, "Ω", 5)
            if m == "cont":
                ok = val is not None and val < self.sp_cont.value()
                txt = ("•)))  " if ok else "") + txt
                if ok and perf() - self._beep_t > 0.4:
                    QApplication.beep()
                    self._beep_t = perf()
        self.last = val if not self.btn_null.isChecked() else self.last
        self.lcd.setText(txt)
        if val is not None:
            lo, hi = self.mm
            self.mm = [val if lo is None else min(lo, val), val if hi is None else max(hi, val)]
        unit = {"vdc": "V", "vac": "V", "adc": "A"}.get(m, "Ω")
        self.lb_stats.setText(T("Mín %s   Máx %s   (%d muestras, σ %s)") % (
            eng(self.mm[0], unit, 4), eng(self.mm[1], unit, 4), st["n"],
            eng(st["std"], "V", 2)))
        if self.btn_null.isChecked():
            self.lb_mode.setText(self.lb_mode.text().split("  [")[0] + "  [NULL]")


TDIV = [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
VDIV = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0]


class Scope(InstrumentWindow):
    TITLE = T("Osciloscopio (Scope)")

    def build(self):
        lay = QHBoxLayout(self.body)
        lay.setContentsMargins(8, 4, 8, 0)
        left = QVBoxLayout()
        self.plot = Plot(ticks=False)
        self.plot.setMinimumSize(620, 400)
        left.addWidget(self.plot, 1)
        rr = QHBoxLayout()
        self.lb_meas = []
        for k in range(2):
            l = QLabel("")
            l.setObjectName("readout")
            l.setStyleSheet("color:%s;" % C_CH[k].name())
            rr.addWidget(l)
            self.lb_meas.append(l)
        left.addLayout(rr)
        lay.addLayout(left, 1)

        right = QVBoxLayout()
        self.chw = []
        for k in range(2):
            g, f = group(T("Canal %d") % k)
            en = QCheckBox(T("Habilitado"))
            en.setChecked(k == 0)
            en.setStyleSheet("QCheckBox{color:%s; font-weight:bold;}" %
                             QColor(C_CH[k]).darker(220).name())
            src = combo([])
            probe = combo([(1.0, "1x"), (10.0, "10x"), (11.0, T("11x (divisor 10k/1k)"))])
            coup = combo([("DC", "DC"), ("AC", "AC")])
            vdiv = combo([(v, eng(v, "V", 2) + "/div") for v in VDIV])
            vdiv.setCurrentIndex(VDIV.index(0.5))
            pos = dspin(-4, 4, 0.0 if k else -3.0, 1, "div", 0.5)
            f.addWidget(en, 0, 0, 1, 2)
            row(f, 1, T("Fuente"), src)
            row(f, 2, T("Sonda"), probe)
            row(f, 3, T("Acoplamiento"), coup)
            row(f, 4, T("Escala"), vdiv)
            row(f, 5, T("Posición vertical"), pos)
            self.chw.append({"en": en, "src": src, "probe": probe, "coup": coup,
                             "vdiv": vdiv, "pos": pos})
            self.watch(en, src, probe, coup, vdiv, pos)
            right.addWidget(g)

        bottom = QHBoxLayout()
        g, f = group(T("Base de tiempo"))
        self.cb_tdiv = combo([(t, fmt_time(t) + "/div") for t in TDIV])
        self.cb_tdiv.setCurrentIndex(TDIV.index(0.1))
        row(f, 0, T("Tiempo/div"), self.cb_tdiv)
        bottom.addWidget(g)

        g, f = group(T("Disparo (trigger)"))
        self.cb_ttype = combo([("imm", T("Inmediato")), ("edge", T("Flanco"))])
        self.cb_tsrc = combo([(0, T("Canal 0")), (1, T("Canal 1"))])
        self.cb_slope = combo([(1, T("Subida  ↗")), (-1, T("Bajada  ↘"))])
        self.sp_level = dspin(-50, 50, 1.65, 2, "V", 0.05)
        f.addWidget(QLabel(T("Tipo")), 0, 0)
        f.addWidget(self.cb_ttype, 0, 1)
        f.addWidget(QLabel(T("Fuente")), 0, 2)
        f.addWidget(self.cb_tsrc, 0, 3)
        f.addWidget(QLabel(T("Pendiente")), 1, 0)
        f.addWidget(self.cb_slope, 1, 1)
        f.addWidget(QLabel(T("Nivel")), 1, 2)
        f.addWidget(self.sp_level, 1, 3)
        bottom.addWidget(g, 1)
        left.addLayout(bottom)
        right.addStretch(1)
        lay.addLayout(right)

        self.watch(self.cb_tdiv, self.cb_ttype, self.cb_tsrc, self.cb_slope, self.sp_level)
        self.btn_auto = QPushButton(T("Autoescala"))
        self.btn_log = QPushButton("Log")
        self.extra.addWidget(self.btn_auto)
        self.extra.addWidget(self.btn_log)
        self.btn_auto.clicked.connect(self.autoscale)
        self.btn_log.clicked.connect(self.log)
        self.bufs = [[], []]
        self.frame = None
        self.rate = 0.0
        self.redraw_empty()

    def refresh_channels(self):
        if self.vref_changed():
            self.sp_level.setValue(self.dev.vref / 2)
        items = ai_items(self.dev)
        for k, w in enumerate(self.chw):
            self.fill(w["src"], items)
            if w["src"].currentIndex() < 0 or (w["src"].count() > k and
                                                w["src"].currentData() is None):
                w["src"].setCurrentIndex(min(k, w["src"].count() - 1))
        if self.chw[1]["src"].count() > 1 and self.chw[1]["src"].currentIndex() == 0 \
                and not hasattr(self, "_once_set"):
            self.chw[1]["src"].setCurrentIndex(1)
            self._once_set = True

    def sync(self):
        chs = []
        for w in self.chw:
            chs.append((w["en"].isChecked() and w["src"].currentData() is not None,
                        w["src"].currentData() or 0))
        self.cfg = {"chs": chs, "win": 10 * self.cb_tdiv.currentData()}
        if self.frame is not None and not self.running:
            self.render()

    def on_start(self):
        self.frame = None
        self.set_status(T("Adquiriendo..."), "")

    def work(self, r):
        dev = self.dev
        bufs = [collections.deque(), collections.deque()]
        t0 = perf()
        last_post = 0.0
        while r.alive:
            c = self.cfg
            keep = max(2.5 * c["win"], 1.5)
            got = False
            for k, (en, src) in enumerate(c["chs"]):
                if not en:
                    continue
                ta = perf()
                v = dev.ai(src)
                tb = perf()
                got = True
                if v is not None:
                    bufs[k].append(((ta + tb) / 2 - t0, v))
            if not got:
                sleep_while(r, 0.05)
                continue
            now = perf() - t0
            for b in bufs:
                while b and b[0][0] < now - keep:
                    b.popleft()
            if now - last_post >= 0.05:
                last_post = now
                r.post((now, [list(b) for b in bufs]))

    def redraw_empty(self):
        self.plot.xr = (0, 10)
        self.plot.yr = (-4, 4)
        self.plot.set_traces([])

    def on_data(self, obj):
        now, bufs = obj
        self.bufs = bufs
        c = self.cfg
        win = c["win"]
        for b in bufs:
            if b:
                n = sum(1 for t, _v in b if t >= now - 1.0)
                self.rate = n / min(1.0, max(1e-3, now - b[0][0]))
                break
        proc = []
        for k, b in enumerate(bufs):
            w = self.chw[k]
            fac = w["probe"].currentData()
            pts = [(t, v * fac) for t, v in b]
            if w["coup"].currentData() == "AC" and pts:
                m = mean([v for _t, v in pts])
                pts = [(t, v - m) for t, v in pts]
            proc.append(pts)

        edge = self.cb_ttype.currentData() == "edge"
        pre = 0.1 * win if edge else 0.0
        if edge:
            k = self.cb_tsrc.currentData()
            lvl = self.sp_level.value()
            sl = self.cb_slope.currentData()
            pts = proc[k]
            tref = None
            for i in range(len(pts) - 1, 0, -1):
                (ta, va), (tb, vb) = pts[i - 1], pts[i]
                if tb > now - (win - pre):
                    continue
                if (sl > 0 and va < lvl <= vb) or (sl < 0 and va > lvl >= vb):
                    tref = ta + (lvl - va) / (vb - va) * (tb - ta) if vb != va else tb
                    break
            if tref is None:
                if self.frame is None:
                    self.set_status(T("Esperando disparo… (nivel %s, %s)") %
                                    (eng(lvl, "V", 3), self.cb_slope.currentText()), "")
                return
            status = T("Disparado")
        else:
            if now < win and self.once:
                self.set_status(T("Llenando la pantalla... %.0f %%") % (100 * now / win), "")
            tref = now - win
            status = T("Inmediato")
        frame = []
        for pts in proc:
            fr = [(t - tref, v) for t, v in pts if -pre - win * 0.02 <= t - tref <= win - pre + win * 0.02]
            frame.append(fr)
        self.frame = (frame, pre, win)
        self.set_status(T("%s  ·  %.0f muestras/s por canal") % (status, self.rate), "")
        self.render()
        if self.once and (edge or now >= win):
            self.stop()

    def render(self):
        if self.frame is None:
            return
        frame, pre, win = self.frame
        win = self.cfg["win"]
        pre = 0.1 * win if self.cb_ttype.currentData() == "edge" else 0.0
        self.plot.xr = (-pre, win - pre)
        self.plot.yr = (-4.0, 4.0)
        traces, hl, ov = [], [], []
        for k, fr in enumerate(frame):
            w = self.chw[k]
            if not w["en"].isChecked():
                self.lb_meas[k].setText(T("Canal %d: apagado") % k)
                continue
            vd = w["vdiv"].currentData()
            pos = w["pos"].value()
            traces.append(([t for t, _v in fr], [v / vd + pos for _t, v in fr], C_CH[k]))
            ov.append((C_CH[k], "CH%d  %s/div  %s" % (k, eng(vd, "V", 2),
                                                     w["coup"].currentData())))
            vs = [v for _t, v in fr]
            ts = [t for t, _v in fr]
            if vs:
                f = freq_of(ts, vs)
                self.lb_meas[k].setText(
                    T("CH%d   RMS %s   Freq %s\n       Vp-p %s   Media %s") % (
                        k, eng(rms(vs), "V", 3), eng(f, "Hz", 4) if f else "----",
                        eng(max(vs) - min(vs), "V", 3), eng(mean(vs), "V", 3)))
            if self.cb_ttype.currentData() == "edge" and self.cb_tsrc.currentData() == k:
                hl.append((self.sp_level.value() / vd + pos, C_MARK))
        ov.append((QColor("#d0d0d0"), "%s/div   %.0f S/s" %
                   (fmt_time(self.cb_tdiv.currentData()), self.rate)))
        self.plot.hlines = hl
        self.plot.vlines = [(0.0, C_MARK)] if pre else []
        self.plot.overlay = ov
        self.plot.set_traces(traces)

    def autoscale(self):
        bufs = self.bufs
        if not any(bufs):
            self.set_status(T("Primero presiona Run para tener datos."), "err")
            return
        fbest = None
        for k, b in enumerate(bufs):
            w = self.chw[k]
            if not w["en"].isChecked() or not b:
                continue
            fac = w["probe"].currentData()
            tlast = b[-1][0]
            seg = [(t, v * fac) for t, v in b if t >= tlast - 1.5]
            vs = [v for _t, v in seg]
            m = mean(vs)
            if w["coup"].currentData() == "AC":
                vs = [v - m for v in vs]
                m = 0.0
            span = max(vs) - min(vs)
            vd = next((x for x in VDIV if span <= 6 * x), VDIV[-1])
            w["vdiv"].setCurrentIndex(VDIV.index(vd))
            w["pos"].setValue(max(-4.0, min(4.0, round(-((max(vs) + min(vs)) / 2) / vd, 1))))
            f = freq_of([t for t, _v in seg], vs)
            if f and fbest is None:
                fbest = f
                if self.cb_tsrc.currentData() == k:
                    self.sp_level.setValue((max(vs) + min(vs)) / 2)
        if fbest:
            td = next((x for x in TDIV if 10 * x >= 2.5 / fbest), TDIV[-1])
            self.cb_tdiv.setCurrentIndex(TDIV.index(td))
            self.cb_ttype.setCurrentIndex(1)
        self.set_status(T("Autoescala aplicada") + (" (%s)" % eng(fbest, "Hz", 3) if fbest else ""), "ok")

    def log(self):
        if self.frame is None:
            self.set_status(T("No hay datos que guardar."), "err")
            return
        frame = self.frame[0]
        n = max(len(f) for f in frame)
        rows = []
        for i in range(n):
            r_ = []
            for f in frame:
                r_ += ["%.6f" % f[i][0], "%.5f" % f[i][1]] if i < len(f) else ["", ""]
            rows.append(r_)
        self.save_csv(["t0 (s)", "CH0 (V)", "t1 (s)", "CH1 (V)"], rows, "scope")


def wave(shape, ph, duty=0.5):
    if shape == "sine":
        return math.sin(2 * math.pi * ph)
    if shape == "tri":
        return 1.0 - 4.0 * abs(ph - 0.5)
    if shape == "square":
        return 1.0 if ph < duty else -1.0
    return 2.0 * ph - 1.0


class FGen(InstrumentWindow):
    TITLE = T("Generador de funciones (FGEN)")
    MODES = False
    SHAPES = [("sine", T("∿  Senoidal")), ("tri", T("⋀  Triangular")),
              ("square", T("⊓  Cuadrada")), ("saw", T("⩘  Diente de sierra"))]

    def build(self):
        lay = QHBoxLayout(self.body)
        lay.setContentsMargins(8, 4, 8, 0)
        left = QVBoxLayout()
        g, f = group(T("Señal de salida (2 periodos)"))
        self.plot = Plot()
        self.plot.setMinimumSize(420, 260)
        self.plot.xfmt = lambda v: eng(v, "s", 2)
        self.plot.yfmt = lambda v: "%.1f V" % v
        f.addWidget(self.plot, 0, 0)
        left.addWidget(g, 1)
        self.lb_rate = QLabel(T("Detenido"))
        self.lb_rate.setObjectName("readout")
        left.addWidget(self.lb_rate)
        lay.addLayout(left, 1)

        right = QVBoxLayout()
        g, f = group(T("Forma de onda"))
        self.bg = QButtonGroup(self)
        for i, (k, t) in enumerate(self.SHAPES):
            b = QPushButton(t)
            b.setCheckable(True)
            b.setProperty("key", k)
            self.bg.addButton(b, i)
            f.addWidget(b, i // 2, i % 2)
        self.bg.button(0).setChecked(True)
        self.bg.buttonClicked.connect(lambda *_a: self.sync())
        right.addWidget(g)

        g, f = group(T("Parámetros"))
        kn = QHBoxLayout()
        self.k_f = Knob(T("Frecuencia"), 0.01, 100.0, 1.0, 3, "Hz", log=True)
        self.k_a = Knob(T("Amplitud"), 0.0, 3.3, 2.0, 2, "Vpp")
        self.k_o = Knob(T("Offset DC"), 0.0, 3.3, 1.65, 2, "V")
        for k in (self.k_f, self.k_a, self.k_o):
            kn.addWidget(k)
        f.addLayout(kn, 0, 0, 1, 2)
        self.sp_duty = dspin(1, 99, 50, 0, "%", 5)
        row(f, 1, T("Ciclo de trabajo (cuadrada)"), self.sp_duty)
        right.addWidget(g)

        g, f = group(T("Salida"))
        self.cb_out = combo([])
        row(f, 0, T("Canal"), self.cb_out)
        f.addWidget(hint(T("Al detener, la salida vuelve a 0 V. Por PWM la señal sale "
                         "como ciclo de trabajo de 1 kHz: pon un filtro RC (10 kΩ + 1 µF).")),
                    1, 0, 1, 2)
        right.addWidget(g)

        g, f = group(T("Barrido de frecuencia"))
        self.ck_sw = QCheckBox(T("Barrido activado"))
        self.sp_f0 = dspin(0.01, 100, 0.5, 2, "Hz")
        self.sp_f1 = dspin(0.01, 100, 5.0, 2, "Hz")
        self.sp_fs = dspin(0.01, 50, 0.5, 2, "Hz")
        self.sp_ti = dspin(0.1, 60, 2.0, 1, "s")
        f.addWidget(self.ck_sw, 0, 0, 1, 2)
        row(f, 1, T("Inicio"), self.sp_f0)
        row(f, 2, T("Fin"), self.sp_f1)
        row(f, 3, T("Paso"), self.sp_fs)
        row(f, 4, T("Intervalo"), self.sp_ti)
        right.addWidget(g)
        right.addStretch(1)
        lay.addLayout(right)
        self.watch(self.k_f, self.k_a, self.k_o, self.sp_duty, self.cb_out, self.ck_sw,
                   self.sp_f0, self.sp_f1, self.sp_fs, self.sp_ti)
        self.live = None
        self.anim = QTimer(self)
        self.anim.setInterval(33)
        self.anim.timeout.connect(self.animate)

    def refresh_channels(self):
        self.fill(self.cb_out, self.dev.outputs())
        vmax = self.dev.vref
        self.k_a.setRange(0.0, vmax)
        self.k_o.setRange(0.0, vmax)
        if self.vref_changed():
            self.k_a.setValue(round(vmax * 0.6, 2))
            self.k_o.setValue(round(vmax / 2, 2))

    def shape(self):
        return self.bg.checkedButton().property("key")

    def sync(self):
        self.cfg = {"shape": self.shape(), "f": self.k_f.value(), "a": self.k_a.value(),
                    "o": self.k_o.value(), "duty": self.sp_duty.value() / 100.0,
                    "out": self.cb_out.currentData(), "sweep": self.ck_sw.isChecked(),
                    "f0": self.sp_f0.value(), "f1": self.sp_f1.value(),
                    "fs": self.sp_fs.value(), "ti": self.sp_ti.value(),
                    "vmax": self.dev.vref}
        self.preview()

    def value(self, c, ph):
        v = c["o"] + c["a"] / 2.0 * wave(c["shape"], ph, c["duty"])
        return max(0.0, min(c["vmax"], v))

    def animate(self):
        if not self.live:
            return
        t, ph, f, v = self.live
        c = self.cfg
        ph = (ph + f * (perf() - t)) % 1.0
        span = 2.0 / f
        n = 400
        xs = [span * i / n for i in range(n + 1)]
        ys = [self.value(c, (ph - (span - x) * f) % 1.0) for x in xs]
        self.plot.xr = (0, span)
        self.plot.yr = (0, c["vmax"])
        self.plot.hlines = [(c["o"], C_MARK)]
        self.plot.overlay = [(C_CH[0], T("Salida %s   f %s") % (eng(v, "V", 3), eng(f, "Hz", 3)))]
        self.plot.set_traces([(xs, ys, C_CH[0]), ([xs[-1]], [v], C_MARK, True)])

    def preview(self):
        if self.running:
            return
        self.plot.overlay = []
        c = self.cfg
        f = c["f"]
        span = 2.0 / f
        n = 400
        xs = [span * i / n for i in range(n + 1)]
        ys = [self.value(c, (x * f) % 1.0) for x in xs]
        self.plot.xr = (0, span)
        self.plot.yr = (0, c["vmax"])
        self.plot.ny = 6 if c["vmax"] < 4 else 5
        self.plot.hlines = [(c["o"], C_MARK)]
        self.plot.set_traces([(xs, ys, C_CH[0])])

    def on_start(self):
        if not self.cfg["out"]:
            self.set_status(T("Esta tarjeta no tiene salida analógica ni PWM."), "err")
            return False
        self.cb_out.setEnabled(False)
        self.live = None
        self.anim.start()
        self.set_status(T("Generando en %s") % self.cfg["out"], "ok")

    def on_stopped(self):
        self.anim.stop()
        self.live = None
        self.cb_out.setEnabled(True)
        self.lb_rate.setText(T("Detenido (salida en 0 V)"))
        self.preview()

    def work(self, r):
        dev = self.dev
        key = self.cfg["out"]
        ph = 0.0
        last = perf()
        tr, n = last, 0
        sweep_f = None
        next_step = last
        try:
            while r.alive:
                c = self.cfg
                now = perf()
                if c["sweep"]:
                    if sweep_f is None or now >= next_step:
                        if sweep_f is None or sweep_f + c["fs"] > c["f1"] + 1e-9:
                            sweep_f = c["f0"]
                        else:
                            sweep_f += c["fs"]
                        next_step = now + c["ti"]
                    f = sweep_f
                else:
                    sweep_f = None
                    f = c["f"]
                ph = (ph + f * (now - last)) % 1.0
                last = now
                v = self.value(c, ph)
                dev.write_out(key, v)
                self.live = (now, ph, f, v)
                n += 1
                if now - tr >= 0.5:
                    r.post((n / (now - tr), f))
                    tr, n = now, 0
        finally:
            try:
                dev.write_out(key, 0.0)
            except DeviceError:
                pass

    def on_data(self, obj):
        rate, f = obj
        lim = rate / 10.0
        self.lb_rate.setText(T("f actual %s   ·   %.0f actualizaciones/s   ·   "
                             "máx. recomendada %s") % (eng(f, "Hz", 3), rate, eng(lim, "Hz", 2)))
        if f > lim:
            self.set_status(T("La frecuencia supera ~1/10 de las actualizaciones por "
                            "segundo: la forma de onda sale escalonada."), "err")
        else:
            self.set_status(T("Generando en %s") % self.cfg["out"], "ok")


class VPS(InstrumentWindow):
    TITLE = T("Fuente de alimentación variable (VPS)")
    MODES = False

    def build(self):
        lay = QVBoxLayout(self.body)
        lay.setContentsMargins(8, 4, 8, 0)
        top = QHBoxLayout()
        self.sup = []
        for k, name in enumerate((T("Fuente A"), T("Fuente B"))):
            g, f = group(name)
            out = combo([])
            kn = Knob(T("Tensión"), 0.0, 3.3, 1.0 if k == 0 else 2.0, 2, "V")
            lcd = QLabel("0.00 V")
            lcd.setObjectName("lcd")
            lcd.setAlignment(Qt.AlignCenter)
            lcd.setStyleSheet("font-size:30px;")
            row(f, 0, T("Salida"), out)
            f.addWidget(kn, 1, 0, 1, 2, Qt.AlignHCenter)
            f.addWidget(lcd, 2, 0, 1, 2)
            self.sup.append({"out": out, "knob": kn, "lcd": lcd})
            self.watch(out, kn)
            top.addWidget(g)
        lay.addLayout(top)
        g, f = group(T("Notas"))
        f.addWidget(hint(T("No es una fuente de potencia: el DAC y el PWM entregan pocos "
                         "mA. Para alimentar una carga pon un seguidor con op-amp o un "
                         "transistor. El DAC y el PWM son de 8 bits (256 pasos de 0 a Vref). "
                         "Al presionar Stop las salidas vuelven a 0 V.")), 0, 0)
        lay.addWidget(g)
        lay.addStretch(1)

    def refresh_channels(self):
        items = [(None, T("— apagada —"))] + self.dev.outputs()
        for k, s in enumerate(self.sup):
            self.fill(s["out"], items)
            if s["out"].currentData() is None and s["out"].count() > 1 + k:
                s["out"].setCurrentIndex(1 + k)
            s["knob"].setRange(0.0, self.dev.vref)

    def sync(self):
        self.cfg = {"s": [(s["out"].currentData(), s["knob"].value()) for s in self.sup]}

    def on_start(self):
        keys = [k for k, _v in self.cfg["s"] if k]
        if not keys:
            self.set_status(T("Elige al menos una salida."), "err")
            return False
        if len(set(keys)) != len(keys):
            self.set_status(T("Las dos fuentes no pueden usar la misma salida."), "err")
            return False
        for s in self.sup:
            s["out"].setEnabled(False)
        self.set_status(T("Salidas activas"), "ok")

    def on_stopped(self):
        for s in self.sup:
            s["out"].setEnabled(True)
            s["lcd"].setText("0.00 V")
        self.set_status(T("Salidas en 0 V"), "")

    def work(self, r):
        dev = self.dev
        keys = [k for k, _v in self.cfg["s"]]
        applied = [None, None]
        try:
            while r.alive:
                for i, (k, v) in enumerate(self.cfg["s"]):
                    if k and applied[i] != v:
                        dev.write_out(k, v)
                        code = round(max(0.0, min(dev.vref, v)) / dev.vref * 255)
                        applied[i] = v
                        r.post((i, code * dev.vref / 255.0))
                sleep_while(r, 0.03)
        finally:
            for k in keys:
                if k:
                    try:
                        dev.write_out(k, 0.0)
                    except DeviceError:
                        pass

    def on_data(self, obj):
        i, v = obj
        self.sup[i]["lcd"].setText("%.3f V" % v)


class DigOut(InstrumentWindow):
    TITLE = T("Escritor digital (DigOut)")
    PATTERNS = [("manual", "Manual"), ("ramp", T("Rampa (cuenta binaria)")),
                ("alt", T("Alternado 1/0")), ("walk", T("Caminar un 1"))]

    def build(self):
        lay = QVBoxLayout(self.body)
        lay.setContentsMargins(8, 4, 8, 0)
        self.g_lines, self.f_lines = group(T("Líneas"))
        lay.addWidget(self.g_lines)
        mid = QHBoxLayout()
        g, f = group(T("Patrón"))
        self.cb_pat = combo(self.PATTERNS)
        self.sp_rate = dspin(0.1, 50, 2.0, 1, "Hz")
        row(f, 0, T("Patrón"), self.cb_pat)
        row(f, 1, T("Velocidad"), self.sp_rate)
        f.addWidget(hint(T("En 'Una vez' los patrones dan una sola vuelta. En Manual, "
                         "con Run activo cada interruptor se aplica al instante.")), 2, 0, 1, 2)
        mid.addWidget(g, 1)
        g, f = group(T("Valor"))
        self.lb_val = QLabel("0")
        self.lb_val.setObjectName("lcd")
        self.lb_val.setStyleSheet("font-size:26px;")
        f.addWidget(self.lb_val, 0, 0)
        mid.addWidget(g, 1)
        lay.addLayout(mid)
        lay.addStretch(1)
        self.lines = []
        self.watch(self.cb_pat, self.sp_rate)

    def refresh_channels(self):
        for w in self.lines:
            for x in (w["sw"], w["led"], w["lab"]):
                x.setParent(None)
        self.lines = []
        n = self.dev.n["do"] if self.dev.connected else 0
        for i in range(n):
            led = Led("#00ff40")
            sw = QPushButton("OFF")
            sw.setCheckable(True)
            sw.setMinimumWidth(64)
            lab = QLabel("DO%d\n%s" % (i, self.dev.pin("do", i)))
            lab.setAlignment(Qt.AlignCenter)
            sw.toggled.connect(lambda on, b=sw: (b.setText("ON" if on else "OFF"), self.sync()))
            self.f_lines.addWidget(led, 0, i, Qt.AlignHCenter)
            self.f_lines.addWidget(sw, 1, i)
            self.f_lines.addWidget(lab, 2, i)
            self.lines.append({"sw": sw, "led": led, "lab": lab})
        if not n:
            lab = QLabel(T("(conecta una tarjeta)"))
            self.f_lines.addWidget(lab, 0, 0)
            self.lines.append({"sw": lab, "led": QLabel(), "lab": QLabel()})

    def sync(self):
        st = [w["sw"].isChecked() for w in self.lines if isinstance(w["sw"], QPushButton)]
        self.cfg = {"pat": self.cb_pat.currentData(), "rate": self.sp_rate.value(), "st": st}

    @staticmethod
    def pattern(kind, k, n):
        if kind == "ramp":
            return k % (1 << n)
        if kind == "alt":
            m = sum(1 << i for i in range(0, n, 2))
            return m if k % 2 == 0 else (~m) & ((1 << n) - 1)
        return 1 << (k % n)

    def work(self, r):
        dev = self.dev
        n = dev.n["do"]
        if not n:
            return
        c = self.cfg
        if c["pat"] == "manual":
            applied = None
            while r.alive:
                st = self.cfg["st"]
                if st != applied:
                    for i, on in enumerate(st):
                        dev.do(i, on)
                    applied = list(st)
                    r.post(sum((1 << i) for i, on in enumerate(st) if on))
                if self.once:
                    return
                sleep_while(r, 0.03)
            return
        steps = {"ramp": 1 << n, "alt": 2, "walk": n}[c["pat"]]
        k = 0
        while r.alive:
            val = self.pattern(self.cfg["pat"], k, n)
            for i in range(n):
                dev.do(i, (val >> i) & 1)
            r.post(val)
            k += 1
            if self.once and k >= steps:
                return
            sleep_while(r, 1.0 / self.cfg["rate"])

    def on_data(self, val):
        for i, w in enumerate(self.lines):
            if isinstance(w["led"], Led):
                w["led"].set((val >> i) & 1)
        n = len(self.lines)
        self.lb_val.setText("%d   0x%02X   %s" % (val, val, format(val, "0%db" % max(1, n))))


class DigIn(InstrumentWindow):
    TITLE = T("Lector digital (DigIn)")

    def build(self):
        lay = QVBoxLayout(self.body)
        lay.setContentsMargins(8, 4, 8, 0)
        self.g_lines, self.f_lines = group(T("Líneas"))
        lay.addWidget(self.g_lines)
        mid = QHBoxLayout()
        g, f = group(T("Valor"))
        self.lb_val = QLabel("----")
        self.lb_val.setObjectName("lcd")
        self.lb_val.setStyleSheet("font-size:26px;")
        f.addWidget(self.lb_val, 0, 0)
        mid.addWidget(g, 1)
        g, f = group(T("Notas"))
        f.addWidget(hint(T("Entradas sin pull-up: una línea al aire lee cualquier cosa. "
                         "Las marcadas como AI también son entradas analógicas; leerlas "
                         "aquí las pasa a modo digital.")), 0, 0)
        mid.addWidget(g, 1)
        lay.addLayout(mid)
        lay.addStretch(1)
        self.leds = []

    def refresh_channels(self):
        for w in self.leds:
            w[0].setParent(None)
            w[1].setParent(None)
        self.leds = []
        n = self.dev.n["di"] if self.dev.connected else 0
        for i in range(n):
            led = Led("#00ff40", 26)
            lab = QLabel("DI%d\n%s" % (i, self.dev.pin("di", i)))
            lab.setAlignment(Qt.AlignCenter)
            self.f_lines.addWidget(led, 0, i, Qt.AlignHCenter)
            self.f_lines.addWidget(lab, 1, i)
            self.leds.append((led, lab))

    def work(self, r):
        dev = self.dev
        n = dev.n["di"]
        while r.alive:
            r.post([dev.di(i) for i in range(n)])
            if self.once:
                return
            sleep_while(r, 0.05)

    def on_data(self, bits):
        val = 0
        for i, b in enumerate(bits):
            if i < len(self.leds):
                self.leds[i][0].set(b)
            if b:
                val |= 1 << i
        self.lb_val.setText("%d   0x%03X   %s" % (val, val, format(val, "0%db" % max(1, len(bits)))))


class Bode(InstrumentWindow):
    TITLE = T("Analizador de Bode")
    MODES = False

    def build(self):
        lay = QHBoxLayout(self.body)
        lay.setContentsMargins(8, 4, 8, 0)
        left = QVBoxLayout()
        self.p_mag = Plot()
        self.p_ph = Plot()
        for p in (self.p_mag, self.p_ph):
            p.logx = True
            p.xfmt = lambda v: eng(v, "Hz", 1).replace(".0 ", " ")
            p.setMinimumSize(560, 210)
        self.p_mag.ylabel = T("Magnitud")
        self.p_ph.ylabel = T("Fase (°)")
        self.p_ph.xlabel = T("Frecuencia")
        self.p_ph.yfmt = lambda v: "%d°" % v
        left.addWidget(self.p_mag, 1)
        left.addWidget(self.p_ph, 1)
        self.lb_pt = QLabel("")
        self.lb_pt.setObjectName("readout")
        left.addWidget(self.lb_pt)
        lay.addLayout(left, 1)

        right = QVBoxLayout()
        g, f = group(T("Estímulo"))
        self.cb_out = combo([])
        self.sp_amp = dspin(0.05, 5, 1.5, 2, "Vpp")
        self.sp_off = dspin(0, 5, 1.65, 2, "V")
        row(f, 0, T("Salida"), self.cb_out)
        row(f, 1, T("Amplitud"), self.sp_amp)
        row(f, 2, "Offset", self.sp_off)
        right.addWidget(g)
        g, f = group(T("Medición"))
        self.cb_in = combo([])
        self.cb_resp = combo([])
        row(f, 0, T("Estímulo (entrada)"), self.cb_in)
        row(f, 1, T("Respuesta (salida)"), self.cb_resp)
        right.addWidget(g)
        g, f = group(T("Barrido"))
        self.sp_f0 = dspin(0.01, 100, 0.2, 2, "Hz")
        self.sp_f1 = dspin(0.01, 100, 15, 2, "Hz")
        self.sp_ppd = ispin(1, 20, 5, T("pts/déc"))
        self.sp_cyc = ispin(1, 20, 3, T("ciclos"))
        self.cb_scale = combo([("db", "dB"), ("lin", T("Lineal (V/V)"))])
        row(f, 0, T("Inicio"), self.sp_f0)
        row(f, 1, T("Fin"), self.sp_f1)
        row(f, 2, T("Resolución"), self.sp_ppd)
        row(f, 3, T("Ciclos por punto"), self.sp_cyc)
        row(f, 4, T("Escala"), self.cb_scale)
        right.addWidget(g)
        right.addWidget(hint(T("Conecta la salida elegida a la entrada del circuito y a "
                             "'Estímulo'; la salida del circuito a 'Respuesta'. Con "
                             "muestreo por software el límite práctico es ~20 Hz: usa "
                             "RC grandes (p. ej. 10 kΩ + 10 µF → fc ≈ 1.6 Hz).")))
        right.addStretch(1)
        lay.addLayout(right)
        self.watch(self.cb_out, self.sp_amp, self.sp_off, self.cb_in, self.cb_resp,
                   self.sp_f0, self.sp_f1, self.sp_ppd, self.sp_cyc)
        self.cb_scale.currentIndexChanged.connect(lambda *_a: self.render())
        self.btn_log = QPushButton("Log")
        self.extra.addWidget(self.btn_log)
        self.btn_log.clicked.connect(self.log)
        self.pts = []
        self.render()

    def refresh_channels(self):
        v = self.dev.vref
        self.sp_amp.setMaximum(v)
        self.sp_off.setMaximum(v)
        if self.vref_changed():
            self.sp_amp.setValue(round(0.45 * v, 2))
            self.sp_off.setValue(round(v / 2, 2))
        self.fill(self.cb_out, self.dev.outputs())
        items = ai_items(self.dev)
        self.fill(self.cb_in, items)
        self.fill(self.cb_resp, items)
        if self.cb_resp.currentIndex() == 0 and self.cb_resp.count() > 1:
            self.cb_resp.setCurrentIndex(1)

    def sync(self):
        self.cfg = {"out": self.cb_out.currentData(), "amp": self.sp_amp.value(),
                    "off": self.sp_off.value(), "ci": self.cb_in.currentData(),
                    "co": self.cb_resp.currentData(), "f0": self.sp_f0.value(),
                    "f1": self.sp_f1.value(), "ppd": self.sp_ppd.value(),
                    "cyc": self.sp_cyc.value()}

    def freqs(self):
        c = self.cfg
        f0, f1 = min(c["f0"], c["f1"]), max(c["f0"], c["f1"])
        n = max(2, int(round(math.log10(f1 / f0) * c["ppd"])) + 1)
        return [f0 * (f1 / f0) ** (i / float(n - 1)) for i in range(n)]

    def on_start(self):
        c = self.cfg
        if not c["out"] or c["ci"] is None or c["co"] is None:
            self.set_status(T("Hace falta una salida y dos entradas analógicas."), "err")
            return False
        self.pts = []
        self.render()
        total = sum((1 + c["cyc"]) / f for f in self.freqs())
        self.set_status(T("Barriendo %d puntos (~%s)...") % (len(self.freqs()), fmt_time(total)), "")

    def work(self, r):
        dev = self.dev
        c = dict(self.cfg)
        key = c["out"]
        try:
            for i, f in enumerate(self.freqs()):
                if not r.alive:
                    return
                settle = 1.0 / f
                tot = (1 + c["cyc"]) / f
                ti, vi, to, vo = [], [], [], []
                t0 = perf()
                while r.alive:
                    t = perf() - t0
                    if t >= tot:
                        break
                    dev.write_out(key, c["off"] + c["amp"] / 2 * math.sin(2 * math.pi * f * t))
                    ta = perf() - t0
                    a = dev.ai(c["ci"])
                    tb = perf() - t0
                    b = dev.ai(c["co"])
                    if t >= settle and a is not None and b is not None:
                        ti.append(ta)
                        vi.append(a)
                        to.append(tb)
                        vo.append(b)
                per_cycle = len(ti) / max(1e-9, c["cyc"])
                if per_cycle < 6:
                    r.post(("limit", f, per_cycle))
                    return
                ai_, phi, _ = sine_fit(ti, vi, f)
                ao_, pho, _ = sine_fit(to, vo, f)
                if ai_ < 1e-3:
                    r.post(("noin", f))
                    return
                dph = math.degrees(pho - phi)
                dph = (dph + 180.0) % 360.0 - 180.0
                r.post(("pt", f, ao_ / ai_, dph, ai_, ao_, per_cycle, i + 1))
        finally:
            try:
                dev.write_out(key, 0.0)
            except DeviceError:
                pass

    def on_data(self, obj):
        if obj[0] == "limit":
            self.set_status(T("Se detuvo en %s: solo %.1f muestras por ciclo. Es el "
                            "límite de este método.") % (eng(obj[1], "Hz", 3), obj[2]), "err")
            return
        if obj[0] == "noin":
            self.set_status(T("No hay señal en el canal de estímulo a %s: revisa la "
                            "conexión.") % eng(obj[1], "Hz", 3), "err")
            return
        _k, f, g, ph, ai_, ao_, spc, i = obj
        self.pts.append((f, g, ph))
        self.lb_pt.setText(T("f %s   |H| %.3f (%.2f dB)   fase %.1f°   Ain %s  Aout %s   "
                           "%.0f muestras/ciclo") % (eng(f, "Hz", 3), g,
                                                     20 * math.log10(max(g, 1e-9)), ph,
                                                     eng(ai_, "V", 3), eng(ao_, "V", 3), spc))
        self.set_status(T("Punto %d de %d") % (i, len(self.freqs())), "")
        self.render()

    def on_stopped(self):
        if self.pts and self.lb_status.property("kind") != "err":
            self.set_status(T("Barrido terminado (%d puntos)") % len(self.pts), "ok")

    def render(self):
        c = self.cfg or {}
        f0, f1 = (min(c.get("f0", 0.2), c.get("f1", 15)), max(c.get("f0", 0.2), c.get("f1", 15)))
        for p in (self.p_mag, self.p_ph):
            p.xr = (f0, f1)
        db = self.cb_scale.currentData() == "db"
        fs = [p[0] for p in self.pts]
        mags = [20 * math.log10(max(p[1], 1e-9)) if db else p[1] for p in self.pts]
        if mags:
            lo, hi, n = nice_range(min(mags), max(mags), 6, zero=not db)
        else:
            lo, hi, n = (-40, 10, 5) if db else (0, 1.2, 6)
        self.p_mag.yr = (lo, hi)
        self.p_mag.ny = n
        self.p_mag.yfmt = (lambda v: "%g dB" % round(v, 2)) if db else (lambda v: "%g" % round(v, 3))
        self.p_mag.set_traces([(fs, mags, C_CH[0], True)])
        self.p_ph.yr = (-180, 180)
        self.p_ph.ny = 8
        self.p_ph.set_traces([(fs, [p[2] for p in self.pts], C_CH[1], True)])

    def log(self):
        if not self.pts:
            self.set_status(T("No hay datos que guardar."), "err")
            return
        self.save_csv(["f (Hz)", "|H| (V/V)", "|H| (dB)", T("fase (grados)")],
                      [["%.5g" % f, "%.5f" % g, "%.3f" % (20 * math.log10(max(g, 1e-9))),
                        "%.2f" % ph] for f, g, ph in self.pts], "bode")


_COMMON = (T("\n\nTodas las entradas van de 0 V a la referencia de la tarjeta "
           "(3.3 V en ESP32/K8, 5 V en UNO/Nano). Nunca metas tensiones negativas "
           "ni mayores: usa un divisor y el factor de sonda.\n\n"
           "El muestreo es por software (un comando por muestra por USB): unos "
           "cientos de muestras por segundo, compartidas entre todos los "
           "instrumentos abiertos."))

DMM.HELP = (T("Multímetro de una punta sobre una entrada analógica (AI).\n\n"
            "V⎓  promedio de N muestras.\n"
            "V~  RMS de la parte alterna (desviación estándar); no necesita "
            "sincronizarse con la señal.\n"
            "A⎓  caída en una resistencia shunt: I = V / Rshunt.\n"
            "Ω   divisor con una resistencia de referencia conocida.\n"
            "•)))  continuidad: pita si R < umbral.\n\n"
            "Null guarda la lectura actual y la resta (modo relativo). "
            "El cuadro 'Conexiones' muestra el pin exacto.") + _COMMON)
Scope.HELP = (T("Osciloscopio de 2 canales.\n\n"
              "Disparo Inmediato: la pantalla corre (modo roll).\n"
              "Disparo por Flanco: congela la señal cuando cruza el nivel con "
              "la pendiente elegida; el disparo queda a 1 división del borde "
              "izquierdo (línea naranja).\n\n"
              "Acoplamiento AC resta el promedio. Sonda multiplica la lectura "
              "(para divisores). Autoescala ajusta V/div, posición, tiempo/div y "
              "nivel de disparo.\n\n"
              "Con 2 canales cada uno recibe la mitad de las muestras. Sirve "
              "para señales de hasta ~20-30 Hz.") + _COMMON)
FGen.HELP = (T("Generador de funciones sobre el DAC (AO) o un PWM.\n\n"
             "La forma de onda se calcula en la PC y se manda punto por punto, "
             "así que la frecuencia es exacta pero la resolución depende de las "
             "actualizaciones por segundo (abajo de la gráfica). Mantén la "
             "frecuencia por debajo de ~1/10 de esa tasa.\n\n"
             "PWM: la salida es una cuadrada de 1 kHz cuyo ciclo de trabajo "
             "sigue la forma de onda. Pon un filtro RC (p. ej. 10 kΩ + 1 µF) "
             "para obtener la señal analógica.\n\n"
             "Barrido: recorre de Inicio a Fin en pasos, cambiando cada "
             "Intervalo, y vuelve a empezar.") + _COMMON)
VPS.HELP = (T("Dos salidas de tensión fija (DAC o PWM).\n\n"
            "Mueve la perilla con Run activo y la salida cambia al instante. "
            "La pantalla muestra la tensión que realmente se programó (8 bits).\n\n"
            "Entrega pocos mA: para cargas usa un seguidor con op-amp o un "
            "transistor. PWM necesita filtro RC.") + _COMMON)
Bode.HELP = (T("Respuesta en frecuencia de un circuito.\n\n"
             "Conexión: Salida → entrada del circuito y → AI 'Estímulo'.\n"
             "Salida del circuito → AI 'Respuesta'. GND común.\n\n"
             "En cada frecuencia se genera una senoidal, se espera un ciclo y se "
             "ajusta una senoidal por mínimos cuadrados a las dos señales: "
             "|H| = Aout/Ain y fase = φout − φin.\n\n"
             "Límite práctico ~20 Hz: prueba filtros RC de constante grande "
             "(10 kΩ + 10 µF → fc ≈ 1.6 Hz). Si hay menos de 6 muestras por "
             "ciclo el barrido se detiene y lo avisa.") + _COMMON)
DigIn.HELP = (T("Lee todas las entradas digitales (DI) y muestra su valor binario, "
              "decimal y hexadecimal.\n\n"
              "Las entradas no tienen pull-up: una línea sin conectar lee "
              "valores al azar. Algunos canales DI comparten pin con AI.") + _COMMON)
DigOut.HELP = (T("Escribe las salidas digitales (DO).\n\n"
               "Manual: cada interruptor controla una línea (con Run activo se "
               "aplica al instante).\n"
               "Rampa: cuenta en binario. Alternado: 1010… / 0101…. "
               "Caminar un 1: un solo bit encendido que se desplaza.\n\n"
               "Las salidas se quedan como están al presionar Stop.") + _COMMON)
TOOLS = [
    ("dmm",    "DMM",     T("Multímetro digital"),          DMM,    ("ai",)),
    ("scope",  "Scope",   T("Osciloscopio"),                Scope,  ("ai",)),
    ("fgen",   "FGEN",    T("Generador de funciones"),      FGen,   ("out",)),
    ("vps",    "VPS",     T("Fuente variable"),             VPS,    ("out",)),
    ("bode",   "Bode",    T("Analizador de Bode"),          Bode,   ("out", "ai2")),
    ("digin",  "DigIn",   T("Lector digital"),              DigIn,  ("di",)),
    ("digout", "DigOut",  T("Escritor digital"),            DigOut, ("do",)),
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
        self.cb_lang.setCurrentIndex(self.cb_lang.findData(lv_hub_lang.LANG))
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

        self.lb_status = QLabel(T("Elige el puerto de la tarjeta y presiona Conectar. "
                                "'Simulador' funciona sin hardware."))
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
        for p in lv_core.list_ports():
            self.cb_port.addItem(p["port"] + ("  —  " + p["label"] if p["label"] else ""),
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
        self.btn_conn.setEnabled(False)
        self.cb_port.setEnabled(False)
        self.set_status(T("Conectando con %s (la tarjeta se reinicia, ~2 s)...") % port, "")

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
        self.setWindowTitle("LV_ESP32 Instrument Launcher — " + dev.board_name)
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
        if lang == lv_hub_lang.LANG:
            return
        lv_hub_lang.save(lang)
        args = [os.path.abspath(__file__), "--lang", lang]
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
            tb.setToolTip(name if ok else "%s — %s" % (name, why))

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

    def forget(self, w):
        k = getattr(w, "_key", None)
        if k in self.wins and self.wins[k] is w:
            del self.wins[k]

    def closeEvent(self, e):
        for w in list(self.wins.values()):
            w.close()
        self.dev.close()
        e.accept()


def main():
    ap = argparse.ArgumentParser(description="LV_ESP32 Instrument Hub")
    ap.add_argument("--port", default=None, help=T("puerto de la tarjeta (COM5, /dev/ttyUSB0...)"))
    ap.add_argument("--sim", action="store_true", help=T("usar el simulador, sin tarjeta"))
    ap.add_argument("--lang", choices=[k for k, _n in LANGS], default=None,
                    help="es / en")
    ap.add_argument("--tool", default=None, choices=[t[0] for t in TOOLS],
                    help=T("abrir directo un instrumento al conectar"))
    a = ap.parse_args()
    app = QApplication(sys.argv)
    app.setApplicationName("LV_ESP32 Instrument Hub")
    app.setStyle("Fusion")
    hub = Hub(a.port, a.sim, a.tool)
    hub.show()
    rc = app.exec_() if hasattr(app, "exec_") else app.exec()
    sys.exit(rc)


if __name__ == "__main__":
    main()
