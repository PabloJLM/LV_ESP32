import math

from hub.dev import DeviceError
from hub.lang import T
from hub.ui import (
    C_CH, InstrumentWindow, Plot, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, combo, dspin,
    eng, fmt_time, group, hint, ispin, row)

from hub.instrumentos import COMMON_HELP, ai_items, nice_range, perf, sine_fit


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
        right.addWidget(hint(T("Salida → entrada del circuito y 'Estímulo'. Salida del "
                               "circuito → 'Respuesta'. Límite ~20 Hz.")))
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
            self.set_status(T("Se detuvo en %s: solo %.1f muestras por ciclo.") % (eng(obj[1], "Hz", 3), obj[2]), "err")
            return
        if obj[0] == "noin":
            self.set_status(T("Sin señal de estímulo a %s. Revisa la conexión.") % eng(obj[1], "Hz", 3), "err")
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


Bode.HELP = (T("Respuesta en frecuencia de un circuito.\n\nEn cada frecuencia genera una "
               "senoidal y compara las dos señales: |H| = Aout/Ain, fase = φout − φin.\n"
               "\nLímite ~20 Hz, usa RC grandes (10 kΩ + 10 µF → fc ≈ 1.6 Hz). Con menos de 6 "
               "muestras por ciclo el barrido se detiene.") + COMMON_HELP)
