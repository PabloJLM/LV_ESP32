from hub.cal import CalError, fit_gain, two_point
from hub.lang import T
from hub.instrumentos import mean, stdev
from hub.ui import (InstrumentWindow, QCheckBox, QHBoxLayout, QLabel, QPushButton,
                    QVBoxLayout, combo, dspin, eng, group, hint, row, sleep_while)


class CalBase(InstrumentWindow):
    def _ready(self):
        d = self.dev
        if not d.connected or d.simulated:
            self.set_status(T("El simulador no se calibra.") if d.simulated
                            else T("Conecta una tarjeta real para calibrar."), "err")
            return False
        return True

    def no_reading(self):
        self.last = None
        self.lb_live.setText("---")
        self.set_status(T("El canal no respondió (ADC2 ocupado por el WiFi o canal "
                          "inválido)."), "err")


class CalWin(CalBase):
    TITLE = T("Calibración")
    MODES = False
    HELP = T("Calibra las lecturas del Hub contra un multímetro.\n\nTarjeta: escribe el Vref "
             "real (pin 3V3 o 5V) y la Rref real del óhmetro.\n\nCanal AI:\n1. Conecta una "
             "fuente variable al canal y presiona Run.\n2. Ajusta ~10 % del rango, escribe lo "
             "que marca el multímetro y captura el punto 1.\n3. Repite cerca del 90 % con el "
             "punto 2.\n4. Presiona Calcular y guardar.\n\nSe guarda por modelo de tarjeta y "
             "solo vale para el Hub. El firmware y LabVIEW siguen dando cuentas sin calibrar.")

    def build(self):
        self.pts = [None, None]
        self.last = None
        self._ch = None
        lay = QVBoxLayout(self.body)
        lay.setContentsMargins(8, 4, 8, 0)

        gb, fb = group(T("Tarjeta"))
        self.sp_vref = dspin(1.0, 6.0, 3.3, 4, "V", 0.01)
        self.sp_rref = dspin(1, 10e6, 2200, 2, "Ω", 1)
        self.btn_board = QPushButton(T("Guardar Vref y Rref"))
        row(fb, 0, T("Vref real (pin 3V3/5V)"), self.sp_vref)
        row(fb, 1, T("R referencia del óhmetro"), self.sp_rref)
        fb.addWidget(self.btn_board, 2, 0, 1, 2)
        fb.addWidget(hint(T("Mide con el multímetro el pin de alimentación y la resistencia Rref.")), 3, 0, 1, 2)
        lay.addWidget(gb)

        gc, fc = group(T("Canal AI: ganancia y offset (2 puntos)"))
        self.cb_ch = combo([])
        row(fc, 0, T("Canal"), self.cb_ch)
        self.lb_live = QLabel("---")
        self.lb_live.setObjectName("lcdsmall")
        fc.addWidget(self.lb_live, 1, 0, 1, 4)
        self.sp_ref, self.btn_cap, self.lb_pt = [], [], []
        for k in range(2):
            sp = dspin(0.0, 6.0, 0.3 if k == 0 else 3.0, 4, "V", 0.01)
            b = QPushButton(T("Capturar punto %d") % (k + 1))
            lb = QLabel("-")
            lb.setObjectName("hint")
            b.clicked.connect(lambda _c=False, i=k: self.capture(i))
            row(fc, 2 + k, T("V referencia (punto %d)") % (k + 1), sp, b, lb)
            self.sp_ref.append(sp)
            self.btn_cap.append(b)
            self.lb_pt.append(lb)
        self.btn_apply = QPushButton(T("Calcular y guardar"))
        self.btn_clear = QPushButton(T("Borrar calibración del canal"))
        fc.addWidget(self.btn_apply, 4, 0, 1, 2)
        fc.addWidget(self.btn_clear, 4, 2, 1, 2)
        self.lb_cur = hint("")
        fc.addWidget(self.lb_cur, 5, 0, 1, 4)
        lay.addWidget(gc)
        lay.addStretch(1)

        self.btn_board.clicked.connect(self.save_board)
        self.btn_apply.clicked.connect(self.apply)
        self.btn_clear.clicked.connect(self.clear)
        self.watch(self.cb_ch)

    def refresh_channels(self):
        d = self.dev
        self.fill(self.cb_ch, [(i, t) for i, t in enumerate(d.channels("ai"))])
        if d.connected and not d.simulated:
            self.sp_vref.setValue(d.vref)
            self.sp_rref.setValue(self.hub.cal.rref(d.board))
            if self.vref_changed():
                self.sp_ref[0].setValue(round(d.vref * 0.1, 2))
                self.sp_ref[1].setValue(round(d.vref * 0.9, 2))

    def sync(self):
        ch = self.cb_ch.currentData() or 0
        self.cfg = {"ch": ch, "n": 25}
        if ch != self._ch:
            self._ch = ch
            self.pts = [None, None]
            self.last = None
            for lb in self.lb_pt:
                lb.setText("-")
        self._show_current()

    def _show_current(self):
        d = self.dev
        if not d.connected or d.simulated:
            self.lb_cur.setText("")
            return
        c = self.hub.cal.channel(d.board, self._ch)
        if c is None:
            self.lb_cur.setText(T("Sin calibrar: se usa Vref / cuentas máx. (nominal)."))
        else:
            rel = c["a"] / (d.vref / d.adc_max)
            self.lb_cur.setText(
                T("Calibrado el %s:  V = %.6g · cuentas %+.5g V   (ganancia %.4f respecto "
                  "al nominal)") % (c.get("date", "?"), c["a"], c["b"], rel))

    def _persist(self):
        try:
            self.hub.cal.save()
        except CalError as e:
            return str(e)
        return None

    def on_start(self):
        if not self._ready():
            return False
        self.set_status(T("Midiendo... captura el punto cuando la lectura esté estable."), "")
        return True

    def work(self, r):
        dev = self.dev
        while r.alive:
            c = self.cfg
            vals = []
            for _ in range(c["n"]):
                if not r.alive:
                    return
                v = dev.ai_raw(c["ch"])
                if v is not None:
                    vals.append(float(v))
            r.post({"c": mean(vals), "s": stdev(vals), "n": len(vals)} if vals else None)

    def on_data(self, st):
        if st is None:
            self.no_reading()
            return
        self.last = st
        d = self.dev
        txt = T("Sin calibrar: %s   (%.1f cuentas, σ %.2f)") % (
            eng(st["c"] * d.vref / d.adc_max, "V", 5), st["c"], st["s"])
        v = self.hub.cal.counts_to_volts(d.board, self._ch, st["c"])
        if v is not None:
            txt += "\n" + T("Calibrado: %s") % eng(v, "V", 5)
        self.lb_live.setText(txt)

    def capture(self, k):
        if not self._ready():
            return
        if self.last is None or not self.running:
            self.set_status(T("Presiona Run y espera una lectura estable antes de capturar."),
                            "err")
            return
        ref = self.sp_ref[k].value()
        self.pts[k] = (self.last["c"], ref, self.last["s"])
        self.lb_pt[k].setText(T("%.1f cuentas = %s") % (self.last["c"], eng(ref, "V", 5)))
        self.set_status(T("Punto %d capturado.") % (k + 1), "ok")

    def apply(self):
        if not self._ready():
            return
        if None in self.pts:
            self.set_status(T("Captura los dos puntos antes de calcular."), "err")
            return
        d = self.dev
        (c1, r1, _s1), (c2, r2, _s2) = self.pts
        try:
            a, b = two_point(c1, r1, c2, r2, d.adc_max)
            rel = a / (d.vref / d.adc_max)
            if not 0.5 <= rel <= 2.0:
                raise CalError(T("La ganancia sale %.2f veces la nominal: revisa los "
                               "valores de referencia.") % rel)
        except CalError as e:
            self.set_status(str(e), "err")
            return
        self.hub.cal.set_channel(d.board, self._ch, a, b, [[c1, r1], [c2, r2]])
        err = self._persist()
        self.set_status(err or T("Calibración del canal AI%d guardada.") % self._ch,
                        "err" if err else "ok")
        self._show_current()

    def clear(self):
        if not self._ready():
            return
        d = self.dev
        if not self.hub.cal.clear_channel(d.board, self._ch):
            self.set_status(T("Ese canal no tenía calibración."), "")
            return
        err = self._persist()
        self.set_status(err or T("Calibración del canal AI%d borrada.") % self._ch,
                        "err" if err else "ok")
        self._show_current()

    def save_board(self):
        if not self._ready():
            return
        d = self.dev
        try:
            self.hub.cal.set_vref(d.board, self.sp_vref.value())
            self.hub.cal.set_rref(d.board, self.sp_rref.value())
        except CalError as e:
            self.set_status(str(e), "err")
            return
        err = self._persist()
        self.hub.cal_changed()
        self.set_status(err or T("Vref y Rref guardados para %s.") % d.board_name,
                        "err" if err else "ok")


class PointCalWin(CalBase):
    MODES = False
    DEFAULTS = ()
    UNIT = ""
    MAX_ROWS = 12

    def make_ref_spin(self, val):
        raise NotImplementedError

    def fmt_ref(self, val):
        return eng(val, self.UNIT, 5)

    def extra_widgets(self, lay):
        pass

    def compute(self):
        raise NotImplementedError

    def clear_cal(self):
        raise NotImplementedError

    def show_current(self):
        pass

    def live_text(self, st):
        return "%.1f" % st["c"]

    def build(self):
        self.last = None
        self._ch = None
        self.rows = []
        lay = QVBoxLayout(self.body)
        lay.setContentsMargins(8, 4, 8, 0)
        self.extra_widgets(lay)
        gc, fc = group(T("Canal"))
        self.cb_ch = combo([])
        row(fc, 0, T("Canal"), self.cb_ch)
        self.lb_live = QLabel("---")
        self.lb_live.setObjectName("lcdsmall")
        fc.addWidget(self.lb_live, 1, 0, 1, 4)
        lay.addWidget(gc)
        self.gp, self.fp = group(self.PTS_TITLE)
        lay.addWidget(self.gp)
        for v in self.DEFAULTS:
            self.add_row(v)
        self.btn_add = QPushButton(T("Agregar punto"))
        self.btn_apply = QPushButton(T("Calcular y guardar"))
        self.btn_clear = QPushButton(T("Borrar calibración"))
        h = QHBoxLayout()
        for b in (self.btn_add, self.btn_apply, self.btn_clear):
            h.addWidget(b)
        lay.addLayout(h)
        self.lb_cur = hint("")
        lay.addWidget(self.lb_cur)
        lay.addStretch(1)
        self.btn_add.clicked.connect(lambda _c=False: self.add_row(self.DEFAULTS[-1]
                                                                   if self.DEFAULTS else 1.0))
        self.btn_apply.clicked.connect(self.apply)
        self.btn_clear.clicked.connect(self.clear)
        self.watch(self.cb_ch)

    def add_row(self, val):
        if len(self.rows) >= self.MAX_ROWS:
            return
        k = len(self.rows)
        ck = QCheckBox()
        ck.setChecked(True)
        sp = self.make_ref_spin(val)
        b = QPushButton(T("Capturar"))
        lb = QLabel("-")
        lb.setObjectName("hint")
        rec = {"ck": ck, "sp": sp, "lb": lb, "pt": None}
        b.clicked.connect(lambda _c=False, r=rec: self.capture(r))
        row(self.fp, k, "", ck, sp, b, lb)
        self.rows.append(rec)

    def refresh_channels(self):
        d = self.dev
        self.fill(self.cb_ch, [(i, t) for i, t in enumerate(d.channels("ai"))])

    def sync(self):
        ch = self.cb_ch.currentData() or 0
        self.cfg = {"ch": ch, "n": 25}
        if ch != self._ch:
            self._ch = ch
            self.last = None
            for r in self.rows:
                r["pt"] = None
                r["lb"].setText("-")
        self.show_current()

    def _persist(self):
        try:
            self.hub.cal.save()
        except CalError as e:
            return T("No se pudo guardar la calibración (sigue activa hasta cerrar el "
                     "Hub): %s") % e
        return None

    def on_start(self):
        if not self._ready():
            return False
        self.set_status(T("Midiendo... captura cada punto cuando la lectura esté estable."),
                        "")
        return True

    def work(self, r):
        dev = self.dev
        while r.alive:
            c = self.cfg
            cs, vs = [], []
            for _ in range(c["n"]):
                if not r.alive:
                    return
                p = dev.ai_pair(c["ch"])
                if p is not None:
                    cs.append(float(p[0]))
                    vs.append(float(p[1]))
            r.post({"c": mean(cs), "v": mean(vs), "s": stdev(cs), "n": len(cs)}
                   if cs else None)
            sleep_while(r, 0.05)

    def on_data(self, st):
        if st is None:
            self.no_reading()
            return
        self.last = st
        self.lb_live.setText(self.live_text(st))

    def capture(self, rec):
        if not self._ready():
            return
        if self.last is None or not self.running:
            self.set_status(T("Presiona Run y espera una lectura estable antes de capturar."),
                            "err")
            return
        ref = rec["sp"].value()
        rec["pt"] = {"c": self.last["c"], "v": self.last["v"], "ref": ref}
        rec["lb"].setText("%.1f c = %s" % (self.last["c"], self.fmt_ref(ref)))
        self.set_status(T("Punto capturado: %.1f cuentas.") % self.last["c"], "ok")

    def used_points(self):
        return [r["pt"] for r in self.rows if r["ck"].isChecked() and r["pt"] is not None]

    def apply(self):
        if not self._ready():
            return
        try:
            msg = self.compute()
        except CalError as e:
            self.set_status(str(e), "err")
            return
        err = self._persist()
        self.hub.cal_changed()
        self.set_status(err or msg, "err" if err else "ok")
        self.show_current()

    def clear(self):
        if not self._ready():
            return
        if not self.clear_cal():
            self.set_status(T("Ese canal no tenía calibración."), "")
            return
        err = self._persist()
        self.hub.cal_changed()
        self.set_status(err or T("Calibración borrada."), "err" if err else "ok")
        self.show_current()


class CalOhm(PointCalWin):
    TITLE = T("Calibrar óhmetro")
    PTS_TITLE = T("Resistencias conocidas")
    DEFAULTS = (100.0, 220.0, 1000.0, 4700.0, 10000.0, 47000.0)
    UNIT = "Ω"
    HELP = T("Calibra el óhmetro con resistencias conocidas.\n\n1. Conecta una resistencia "
             "entre el canal y GND.\n2. Escribe su valor medido con el multímetro.\n3. "
             "Presiona Run, espera una lectura estable y captura.\n4. Repite con cada una y "
             "presiona Calcular y guardar.\n\nLa tabla reemplaza a Rref en toda la tarjeta. "
             "Lejos de los puntos no es fiable. Solo vale para el Hub.")

    def make_ref_spin(self, val):
        return dspin(1.0, 10e6, val, 2, "Ω", 1)

    def extra_widgets(self, lay):
        lay.addWidget(hint(T("Conecta cada resistencia entre el canal y GND y escribe su valor "
                             "medido. Usa de 3 a 6 puntos, por ejemplo 100, 220, 1k, 4.7k, 10k "
                             "y 47k.")))

    def _raw_r(self, c):
        d = self.dev
        v = c * d.vref / d.adc_max
        if v >= 0.985 * d.vref:
            return None
        return self.hub.cal.rref(d.board) * v / (d.vref - v)

    def live_text(self, st):
        d = self.dev
        r = self._raw_r(st["c"])
        txt = T("Sin calibrar: %s   (%.1f cuentas, σ %.2f)") % (
            eng(r, "Ω", 5) if r is not None else T("OL"), st["c"], st["s"])
        rc = self.hub.cal.ohm_value(d.board, st["c"], d.adc_max)
        if rc is not None:
            txt += "\n" + T("Calibrado: %s") % eng(rc, "Ω", 5)
        return txt

    def show_current(self):
        d = self.dev
        if not d.connected or d.simulated:
            self.lb_cur.setText("")
            return
        t = self.hub.cal.ohm_table(d.board)
        if t is None:
            self.lb_cur.setText(T("Sin tabla: se usa Rref (%s) con el divisor ideal.") %
                                eng(self.hub.cal.rref(d.board), "Ω", 5))
        else:
            self.lb_cur.setText(T("Tabla guardada el %s con %d puntos.") % (
                t.get("date", "?"), len(t["pts"])) + "  " +
                T("Fuera de los puntos la curva sigue la pendiente del divisor ideal."))

    def compute(self):
        pts = [(p["c"], p["ref"]) for p in self.used_points()]
        self.hub.cal.set_ohm_table(self.dev.board, pts, self.dev.adc_max)
        return T("Tabla del óhmetro guardada con %d puntos.") % len(pts)

    def clear_cal(self):
        return self.hub.cal.clear_ohm(self.dev.board)


SAT = 0.985


class CalDiv(PointCalWin):
    TITLE = T("Calibrar divisor (sonda)")
    PTS_TITLE = T("Puntos de tensión")
    DEFAULTS = (0.0, 3.3, 5.0, 7.0, 15.0)
    UNIT = "V"
    HELP = T("Calcula el factor real del divisor de entrada de un canal.\n\n1. Verifica el "
             "divisor con un multímetro y con la cuenta teórica.\n2. Aplica cada tensión (0, "
             "3.3, 5, 7, 15 V) a la entrada del divisor.\n3. Escribe lo que marca el "
             "multímetro, presiona Run y captura.\n4. Presiona Calcular y guardar.\n\nLos "
             "puntos con el pin saturado no se usan. Solo vale para el Hub.")

    def make_ref_spin(self, val):
        return dspin(0.0, 60.0, val, 4, "V", 0.1)

    def extra_widgets(self, lay):
        w = hint(T("ADVERTENCIA: antes de calibrar verifica el divisor con un multímetro "
                   "y con el cálculo teórico. Nunca apliques al pin del ADC más que Vref "
                   "(3.3 V o 5 V). Un divisor mal armado puede dañar la tarjeta."))
        w.setStyleSheet("color:#b00020; font-weight:bold;")
        lay.addWidget(w)
        lay.addWidget(hint(T("Aplica cada tensión a la entrada del divisor y mídela con el "
                             "multímetro. Sugeridas: 0, 3.3, 5, 7 y 15 V. El punto de 0 V solo "
                             "muestra el offset.")))
        self.sp_th = dspin(0.0, 1000.0, 0.0, 4, "", 0.1)
        self.sp_th.setMinimum(0.0)
        self.sp_th.setSpecialValueText(T("sin comparar"))
        g, f = group(T("Factor teórico (opcional)"))
        row(f, 0, T("Factor teórico (opcional)"), self.sp_th)
        lay.addWidget(g)

    def live_text(self, st):
        d = self.dev
        txt = T("Pin: %s   (%.1f cuentas, σ %.2f)") % (eng(st["v"], "V", 5), st["c"], st["s"])
        k = self.hub.cal.probe(d.board, self._ch)
        if k is not None:
            txt += "\n" + T("Entrada estimada con el factor guardado: %s") % eng(
                st["v"] * k, "V", 5)
        return txt

    def show_current(self):
        d = self.dev
        if not d.connected or d.simulated:
            self.lb_cur.setText("")
            return
        p = self.hub.cal.probe_info(d.board, self._ch)
        if p is None:
            self.lb_cur.setText(T("Sin factor guardado: el Hub usa el factor que escribas "
                                  "a mano en el multímetro."))
        else:
            self.lb_cur.setText(T("Factor guardado el %s: %.5g   (%d puntos)") % (
                p.get("date", "?"), p["k"], len(p.get("pts", []))))

    def compute(self):
        d = self.dev
        pts = self.used_points()
        zero = [p for p in pts if p["ref"] <= 0.0]
        good = [(p["v"], p["ref"]) for p in pts
                if p["ref"] > 0.0 and p["v"] > 0.0 and p["v"] < SAT * d.vref]
        if not good:
            raise CalError(T("Ningún punto sirve para el factor (0 V o pin saturado)."))
        k = fit_gain(good)
        th = self.sp_th.value()
        if th > 0.0 and abs(k - th) / th > 0.30:
            raise CalError(T("El factor medido (%.4g) difiere más de 30 %% del teórico "
                             "(%.4g). Revisa el divisor antes de guardar.") % (k, th))
        self.hub.cal.set_probe(d.board, self._ch, k, [[p["v"], p["ref"]] for p in pts
                                                      if p["ref"] > 0.0])
        errs = ", ".join("%g V: %+.2f %%" % (x[1], 100.0 * (k * x[0] - x[1]) / x[1])
                         for x in good)
        msg = T("Factor %.5g guardado para el canal AI%d.") % (k, self._ch)
        msg += "  " + T("Errores: %s") % errs
        if len(good) == 1:
            msg += "  " + T("Solo hay un punto con tensión: el factor no se puede "
                             "comprobar. Agrega más.")
        if zero:
            msg += "  " + T("Offset en 0 V: el pin lee %s.") % eng(zero[0]["v"], "V", 4)
        return msg

    def clear_cal(self):
        return self.hub.cal.clear_probe(self.dev.board, self._ch)
