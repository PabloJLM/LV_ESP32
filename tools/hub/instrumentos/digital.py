from hub.lang import T
from hub.ui import (
    InstrumentWindow, Led, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, Qt, combo, dspin,
    group, hint, row, sleep_while)

from hub.instrumentos import COMMON_HELP


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
        f.addWidget(hint(T("'Una vez' da una sola vuelta al patrón. En Manual los "
                           "interruptores se aplican con Run activo.")), 2, 0, 1, 2)
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
        f.addWidget(hint(T("Sin pull-up: una línea al aire lee cualquier cosa. Leer aquí un "
                           "canal AI lo pasa a modo digital.")), 0, 0)
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


DigOut.HELP = (T("Escribe las salidas digitales (DO).\n\nRampa cuenta en binario, Alternado da "
                 "1010 / 0101 y Caminar un 1 desplaza un solo bit.\n\nAl presionar Stop las "
                 "salidas se quedan como están.") + COMMON_HELP)


DigIn.HELP = (T("Lee las entradas digitales (DI) en binario, decimal y hexadecimal.\n\nAlgunos "
                "canales DI comparten pin con AI.") + COMMON_HELP)
