import collections

from hub.lang import T
from hub.ui import (
    C_CH, C_MARK, InstrumentWindow, Plot, QCheckBox, QColor, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, combo, dspin, eng, fmt_time, group, row, sleep_while)

from hub.instrumentos import COMMON_HELP, ai_items, freq_of, mean, perf, rms


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


Scope.HELP = (T("Osciloscopio de 2 canales, para señales de hasta ~20-30 Hz.\n\nDisparo "
                "Inmediato: la pantalla corre.\nDisparo por Flanco: congela la señal al cruzar "
                "el nivel (línea naranja).\n\nAC resta el promedio. Sonda multiplica la "
                "lectura. Con 2 canales cada uno recibe la mitad de las muestras.") + COMMON_HELP)
