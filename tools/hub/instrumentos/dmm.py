from hub.lang import T
from hub.ui import (
    InstrumentWindow, QApplication, QButtonGroup, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QVBoxLayout, Qt, combo, dspin, eng, group, hint, ispin, row, sleep_while)

from hub.instrumentos import COMMON_HELP, ai_items, mean, perf, stdev


def bip(freq=1000, ms=250):
    try:
        import threading
        import winsound
        threading.Thread(target=winsound.Beep, args=(freq, ms), daemon=True).start()
    except ImportError:
        QApplication.beep()


class DMM(InstrumentWindow):
    TITLE = T("Multímetro digital (DMM)")
    MODES_LIST = [("vdc", "V⎓", T("Voltaje DC")),
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
        self.sp_rref = dspin(1, 10e6, 2200, 2, "Ω", 100)
        self.sp_cont = dspin(1, 1000, 50, 0, "Ω")
        row(f2, 0, T("Factor de sonda"), self.sp_fac)
        row(f2, 1, T("R referencia (Ω)"), self.sp_rref)
        row(f2, 2, T("Umbral continuidad"), self.sp_cont)
        mid.addWidget(g2)

        g3, f3 = group(T("Conexiones"))
        self.lb_wire = hint("")
        self.lb_wire.setMinimumWidth(270)
        f3.addWidget(self.lb_wire, 0, 0)
        mid.addWidget(g3, 1)
        lay.addLayout(mid)
        lay.addStretch(1)

        self.watch(self.cb_ch, self.sp_avg, self.sp_fac, self.sp_rref,
                   self.sp_cont)
        self.bg.buttonClicked.connect(lambda *_a: self._mode_changed())
        self.btn_null.toggled.connect(self._null)
        self.null = 0.0
        self.last = None
        self.mm = [None, None]
        self._beep_t = 0
        self._fac_ch = None

    def refresh_channels(self):
        self.fill(self.cb_ch, ai_items(self.dev))
        d = self.dev
        self._fac_ch = None
        if d.connected and not d.simulated:
            self.sp_rref.setValue(self.hub.cal.rref(d.board))

    def mode(self):
        return self.bg.checkedButton().property("key")

    def sync(self):
        ch = self.cb_ch.currentData() or 0
        d = self.dev
        if ch != self._fac_ch and d.connected and not d.simulated:
            self._fac_ch = ch
            k = self.hub.cal.probe(d.board, ch)
            if k is not None:
                self.sp_fac.setValue(k)
        self.cfg = {"ch": ch, "n": self.sp_avg.value()}
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
            "vdc": T("Punta roja → %s\nPunta negra → GND\n\nRango 0 a %.1f V. Para más, usa un "
                     "divisor y pon su relación en 'Factor de sonda'.") % (pin, vref),
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
            vals, cnts = [], []
            for _ in range(c["n"]):
                if not r.alive:
                    return
                p = dev.ai_pair(c["ch"])
                if p is not None:
                    cnts.append(p[0])
                    vals.append(p[1])
            r.post({"mean": mean(vals), "std": stdev(vals), "n": len(vals),
                    "c": mean(cnts)} if vals else None)
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
        else:
            v = st["mean"]
            if v >= vref * 0.985:
                val = None
                txt = "OL   Ω"
            else:
                d = self.dev
                tab = None
                if d.connected and not d.simulated:
                    tab = self.hub.cal.ohm_value(d.board, st["c"])
                if tab is not None:
                    val = tab - (self.null if m == "ohm" else 0)
                else:
                    val = self.sp_rref.value() * v / (vref - v) - (self.null if m == "ohm" else 0)
                txt = eng(val, "Ω", 5)
            if m == "cont":
                ok = val is not None and val < self.sp_cont.value()
                txt = ("•)))  " if ok else "") + txt
                if ok and perf() - self._beep_t > 0.4:
                    bip()
                    self._beep_t = perf()
        self.last = val if not self.btn_null.isChecked() else self.last
        self.lcd.setText(txt)
        if val is not None:
            lo, hi = self.mm
            self.mm = [val if lo is None else min(lo, val), val if hi is None else max(hi, val)]
        unit = {"vdc": "V"}.get(m, "Ω")
        self.lb_stats.setText(T("Mín %s   Máx %s   (%d muestras, σ %s)") % (
            eng(self.mm[0], unit, 4), eng(self.mm[1], unit, 4), st["n"],
            eng(st["std"], "V", 2)))
        if self.btn_null.isChecked():
            self.lb_mode.setText(self.lb_mode.text().split("  [")[0] + "  [NULL]")


DMM.HELP = (T("Multímetro de una punta sobre una entrada analógica (AI).\n\nV⎓  promedio de N "
              "muestras.\nΩ   divisor con una resistencia de referencia.\n•)))  pita si R < "
              "umbral.\n\nNull resta la lectura actual.") + COMMON_HELP)
