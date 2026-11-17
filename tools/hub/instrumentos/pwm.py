from hub.dev import DeviceError
from hub.lang import T
from hub.ui import (
    InstrumentWindow, Knob, QHBoxLayout, QLabel, QVBoxLayout, Qt, combo, group, hint, row,
    sleep_while)

from hub.instrumentos import COMMON_HELP

N_OUT = 3


class PWM(InstrumentWindow):
    TITLE = T("Salida PWM")
    MODES = False

    def build(self):
        lay = QVBoxLayout(self.body)
        lay.setContentsMargins(8, 4, 8, 0)
        top = QHBoxLayout()
        self.ch = []
        for k in range(N_OUT):
            g, f = group(T("PWM %d") % (k + 1))
            out = combo([])
            kn = Knob(T("Ciclo de trabajo"), 0.0, 100.0, 50.0, 0, "%")
            lcd = QLabel("0 %")
            lcd.setObjectName("lcd")
            lcd.setAlignment(Qt.AlignCenter)
            lcd.setStyleSheet("font-size:30px;")
            row(f, 0, T("Salida"), out)
            f.addWidget(kn, 1, 0, 1, 2, Qt.AlignHCenter)
            f.addWidget(lcd, 2, 0, 1, 2)
            self.ch.append({"out": out, "knob": kn, "lcd": lcd})
            self.watch(out, kn)
            top.addWidget(g)
        lay.addLayout(top)
        g, f = group(T("Notas"))
        f.addWidget(hint(T("La salida PWM es una onda cuadrada. Para obtener una tensión "
                           "necesita un filtro RC. Al presionar Stop vuelve a 0 %.")), 0, 0)
        lay.addWidget(g)
        lay.addStretch(1)

    def refresh_channels(self):
        items = [(None, T("- apagada -"))] + list(enumerate(self.dev.channels("pwm")))
        for k, c in enumerate(self.ch):
            self.fill(c["out"], items)
            if c["out"].currentData() is None and c["out"].count() > 1 + k:
                c["out"].setCurrentIndex(1 + k)

    def sync(self):
        self.cfg = {"c": [(c["out"].currentData(), c["knob"].value()) for c in self.ch]}

    def on_start(self):
        keys = [k for k, _v in self.cfg["c"] if k is not None]
        if not keys:
            self.set_status(T("Elige al menos una salida."), "err")
            return False
        if len(set(keys)) != len(keys):
            self.set_status(T("Dos canales no pueden usar la misma salida."), "err")
            return False
        for c in self.ch:
            c["out"].setEnabled(False)
        self.set_status(T("Salidas activas"), "ok")

    def on_stopped(self):
        for c in self.ch:
            c["out"].setEnabled(True)
            c["lcd"].setText("0 %")
        self.set_status(T("Salidas en 0 %"), "")

    def work(self, r):
        dev = self.dev
        keys = [k for k, _v in self.cfg["c"]]
        applied = [None] * N_OUT
        try:
            while r.alive:
                for i, (k, v) in enumerate(self.cfg["c"]):
                    if k is not None and applied[i] != v:
                        dev.pwm_raw(k, round(v / 100.0 * 255))
                        applied[i] = v
                        r.post((i, v))
                sleep_while(r, 0.03)
        finally:
            for k in keys:
                if k is not None:
                    try:
                        dev.pwm_raw(k, 0)
                    except DeviceError:
                        pass

    def on_data(self, obj):
        i, v = obj
        self.ch[i]["lcd"].setText("%d %%" % round(v))


PWM.HELP = (T("Hasta tres salidas PWM con ciclo de trabajo de 0 a 100 %, en pasos de 8 bits.\n\n"
              "Mueve la perilla con Run activo. La frecuencia la define el firmware de la "
              "placa y aquí no se mide.") + COMMON_HELP)
