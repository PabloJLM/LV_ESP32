from hub.dev import DeviceError
from hub.lang import T
from hub.ui import (
    InstrumentWindow, Knob, QHBoxLayout, QLabel, QVBoxLayout, Qt, combo, group, hint, row,
    sleep_while)

from hub.instrumentos import COMMON_HELP


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
        f.addWidget(hint(T("No es fuente de potencia: entrega pocos mA. Para una carga usa un "
                           "seguidor con op-amp o un transistor. Al presionar Stop vuelve a 0 "
                           "V.")), 0, 0)
        lay.addWidget(g)
        lay.addStretch(1)

    def refresh_channels(self):
        items = [(None, T("- apagada -"))] + self.dev.outputs()
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


VPS.HELP = (T("Dos salidas de tensión fija (DAC o PWM), de 8 bits.\n\nMueve la perilla con Run "
              "activo. La pantalla muestra la tensión que se programó.\n\nPWM necesita filtro "
              "RC.") + COMMON_HELP)
