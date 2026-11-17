import math

import hub.lang as hlang
from hub.dev import GEN_FS, GEN_MIN_PTS, DeviceError
from hub.lang import T
from hub.ui import (
    C_CH, C_MARK, InstrumentWindow, Knob, Plot, QButtonGroup, QCheckBox, QHBoxLayout, QLabel,
    QPushButton, QTimer, QVBoxLayout, combo, dspin, eng, group, hint, row, sleep_while)

from hub.instrumentos import COMMON_HELP, perf

_EN = {
    "Generar en la placa (rápido, solo DAC)": "Generate on the board (fast, DAC only)",
    "La placa genera la onda sola, sin depender del serial. Necesita el firmware con generador "
    "y una salida AO.":
        "The board generates the wave by itself, independent of the serial link. Needs "
        "firmware with the generator and an AO output.",
    "La placa no aceptó el generador. Vuelve a cargar el firmware o desmarca 'Generar en la "
    "placa'.":
        "The board rejected the generator. Reflash the firmware or untick 'Generate on the "
        "board'.",
    "Hardware  ·  f pedida %s  ·  f real %s  ·  %d muestras/s  ·  máx. %s":
        "Hardware  ·  requested f %s  ·  actual f %s  ·  %d samples/s  ·  max %s",
    "Generando en la placa (%s)": "Generating on the board (%s)",
}
for _k, _v in _EN.items():
    hlang.EN.setdefault(_k, _v)


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
        f.addWidget(hint(T("Al detener, la salida vuelve a 0 V. Con PWM pon un filtro RC (10 "
                           "kΩ + 1 µF).")),
                    1, 0, 1, 2)
        self.ck_hw = QCheckBox(T("Generar en la placa (rápido, solo DAC)"))
        f.addWidget(self.ck_hw, 2, 0, 1, 2)
        f.addWidget(hint(T("La placa genera la onda sola, sin depender del serial. Necesita el "
                           "firmware con generador y una salida AO.")), 3, 0, 1, 2)
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
                   self.sp_f0, self.sp_f1, self.sp_fs, self.sp_ti, self.ck_hw)
        self._hw_rng = False
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

    def hw_mode(self):
        return self.ck_hw.isChecked() and (self.cb_out.currentData() or "").startswith("AO")

    def _set_ranges(self):
        hw = self.hw_mode()
        if hw == self._hw_rng:
            return
        self._hw_rng = hw
        lo, hi = (0.001, GEN_FS / GEN_MIN_PTS) if hw else (0.01, 100.0)
        self.k_f.setRange(lo, hi)
        for sp in (self.sp_f0, self.sp_f1):
            sp.setRange(lo, hi)
        self.sp_fs.setRange(lo, hi)
        self.sp_f0.setDecimals(3 if hw else 2)
        self.sp_f1.setDecimals(3 if hw else 2)
        self.sp_fs.setDecimals(3 if hw else 2)

    def sync(self):
        self._set_ranges()
        self.cfg = {"hw": self.hw_mode(), "shape": self.shape(), "f": self.k_f.value(), "a": self.k_a.value(),
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
        self.ck_hw.setEnabled(False)
        self.live = None
        self.anim.start()
        if self.cfg["hw"]:
            self.set_status(T("Generando en la placa (%s)") % self.cfg["out"], "ok")
        else:
            self.set_status(T("Generando en %s") % self.cfg["out"], "ok")

    def on_stopped(self):
        self.anim.stop()
        self.live = None
        self.cb_out.setEnabled(True)
        self.ck_hw.setEnabled(True)
        self.lb_rate.setText(T("Detenido (salida en 0 V)"))
        self.preview()

    def step_freq(self, c, now, state):
        if not c["sweep"]:
            state[0] = None
            return c["f"]
        if state[0] is None or now >= state[1]:
            if state[0] is None or state[0] + c["fs"] > c["f1"] + 1e-9:
                state[0] = c["f0"]
            else:
                state[0] += c["fs"]
            state[1] = now + c["ti"]
        return state[0]

    def work_hw(self, r):
        dev = self.dev
        key = self.cfg["out"]
        ch = int(key[2:])
        ph, last_t, last_p = 0.0, perf(), None
        tr = last_t
        state = [None, last_t]
        try:
            while r.alive:
                c = self.cfg
                now = perf()
                f = self.step_freq(c, now, state)
                ph = (ph + (self.live[2] if self.live else f) * (now - last_t)) % 1.0
                last_t = now
                p = (c["shape"], f, c["a"], c["o"], c["duty"])
                if p != last_p:
                    if not dev.dacgen(ch, c["shape"], f, c["a"], c["o"], c["duty"]):
                        r.post({"err": T("La placa no aceptó el generador. Vuelve a cargar el "
                                         "firmware o desmarca 'Generar en la placa'.")})
                        return
                    last_p = p
                self.live = (now, ph, f, self.value(c, ph))
                if now - tr >= 0.5:
                    r.post({"hw": dev.dacgen_status(ch), "f": f})
                    tr = now
                sleep_while(r, 0.05)
        finally:
            try:
                dev.dacgen_stop(ch)
            except DeviceError:
                pass

    def work(self, r):
        if self.cfg["hw"]:
            return self.work_hw(r)
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
        if isinstance(obj, dict):
            if "err" in obj:
                self.set_status(obj["err"], "err")
                self.stop()
                return
            st = obj["hw"]
            if st is None:
                return
            self.lb_rate.setText(T("Hardware  ·  f pedida %s  ·  f real %s  ·  %d muestras/s  "
                                 "·  máx. %s") % (eng(obj["f"], "Hz", 3), eng(st["f"], "Hz", 4),
                                                 st["fs"], eng(st["fmax"], "Hz", 2)))
            return
        rate, f = obj
        lim = rate / 10.0
        self.lb_rate.setText(T("f actual %s   ·   %.0f actualizaciones/s   ·   "
                             "máx. recomendada %s") % (eng(f, "Hz", 3), rate, eng(lim, "Hz", 2)))
        if f > lim:
            self.set_status(T("Frecuencia muy alta para esta tasa: la onda sale escalonada."), "err")
        else:
            self.set_status(T("Generando en %s") % self.cfg["out"], "ok")


FGen.HELP = (T("Generador de funciones sobre el DAC (AO) o un PWM.\n\nLa PC manda la onda "
               "punto por punto. Mantén la frecuencia por debajo de ~1/10 de las "
               "actualizaciones por segundo (abajo de la gráfica).\n\nBarrido: va de Inicio a "
               "Fin en pasos, cambia cada Intervalo y vuelve a empezar.") + COMMON_HELP)
