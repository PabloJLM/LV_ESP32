from hub.lang import T

from camilab.documento import add_node, add_wire, new_doc


class ExB(object):
    def __init__(self, title, rows=3, cols=4):
        self.doc = new_doc()
        self.doc["panel"]["rows"] = rows
        self.doc["panel"]["cols"] = cols
        self.doc["panel"]["title"]["text"] = T(title)

    def n(self, t, x, y, frame=0, cell=None, **p):
        if "label" in p:
            p["label"] = T(p["label"])
        nid = add_node(self.doc, t, x, y, **p)
        self.doc["nodes"][nid]["frame"] = frame
        if cell:
            r, c, rs, cs = (list(cell) + [1, 1])[:4]
            self.doc["panel"]["items"][nid] = {"r": r, "c": c, "rs": rs, "cs": cs}
        return nid

    def c(self, v, x, y, frame=0):
        if isinstance(v, bool):
            return self.n("const_bool", x, y, frame, value=v)
        if isinstance(v, str):
            return self.n("const_str", x, y, frame, value=v)
        return self.n("const_num", x, y, frame, value=float(v))

    def w(self, a, ap, b, bp, frame=0):
        add_wire(self.doc, a, ap, b, bp, frame)

    def text(self, txt, x, y, size=11):
        self.doc["panel"]["texts"].append({"x": x, "y": y, "text": T(txt), "size": size})

    def loop_end(self, loop, x, y, ms, sx, sy, cell):
        k = self.c(ms, x, y)
        wt = self.n("wait", x + 60, y - 4)
        self.w(k, "v", wt, "ms")
        st = self.n("ctl_stop", sx, sy, cell=cell, label="Stop")
        self.w(st, "v", loop, "stop")
        return st


def ex_voltage():
    b = ExB("Voltímetro", 3, 4)
    op = b.n("open", 20, 150)
    lp = b.n("while", 200, 60, w=520, h=320)
    ch = b.n("ctl_ring", 220, 120, cell=(1, 0), label="Canal AI",
             options="AI0;AI1;AI2;AI3;AI4;AI5", value=2.0)
    ai = b.n("ai_read", 300, 120)
    num = b.n("ind_num", 560, 110, cell=(0, 0), label="Voltaje", units="V")
    ch1 = b.n("ind_chart", 560, 180, cell=(0, 1, 3, 3), label="Voltaje vs tiempo")
    b.loop_end(lp, 240, 300, 100, 640, 300, (2, 0))
    cl = b.n("close", 780, 150)
    b.w(op, "ses", ai, "ses")
    b.w(ch, "v", ai, "ch")
    b.w(ai, "volts", num, "v")
    b.w(ai, "volts", ch1, "v")
    b.w(ai, "ses", cl, "ses")
    return b.doc


def ex_led():
    b = ExB("Prender un LED", 2, 3)
    op = b.n("open", 20, 150)
    lp = b.n("while", 200, 60, w=520, h=320)
    sw = b.n("ctl_bool", 240, 120, cell=(0, 0), label="LED en DO0")
    ch = b.c(0, 250, 180)
    do = b.n("do_write", 360, 110)
    led = b.n("ind_led", 600, 200, cell=(0, 1), label="Estado")
    b.loop_end(lp, 240, 300, 50, 640, 300, (0, 2))
    cl = b.n("close", 780, 150)
    b.w(op, "ses", do, "ses")
    b.w(ch, "v", do, "ch")
    b.w(sw, "v", do, "val")
    b.w(sw, "v", led, "v")
    b.w(do, "ses", cl, "ses")
    b.text("DO0 → resistencia de 330 Ω → LED → GND", 0.05, 0.75)
    return b.doc


def ex_alarm():
    b = ExB("Alarma por umbral", 3, 4)
    op = b.n("open", 20, 150)
    lp = b.n("while", 200, 40, w=640, h=400)
    ch = b.c(2, 230, 110)
    ai = b.n("ai_read", 290, 90)
    vn = b.n("ind_num", 520, 80, cell=(0, 0), label="Voltaje", units="V")
    vc = b.n("ind_chart", 600, 80, cell=(0, 1, 3, 3), label="Señal")
    th = b.n("ctl_knob", 330, 220, cell=(1, 0), label="Umbral", units="V", min=0.0,
             max=3.3, value=2.0)
    gt = b.n("gt", 470, 200)
    al = b.n("ind_led", 600, 180, cell=(2, 0), label="Alarma")
    k0 = b.c(0, 520, 300)
    do = b.n("do_write", 600, 260)
    b.loop_end(lp, 240, 370, 100, 760, 380, (3, 0))
    cl = b.n("close", 900, 150)
    b.w(op, "ses", ai, "ses")
    b.w(ch, "v", ai, "ch")
    b.w(ai, "volts", vn, "v")
    b.w(ai, "volts", vc, "v")
    b.w(ai, "volts", gt, "a")
    b.w(th, "v", gt, "b")
    b.w(gt, "r", al, "v")
    b.w(gt, "r", do, "val")
    b.w(k0, "v", do, "ch")
    b.w(ai, "ses", do, "ses")
    b.w(do, "ses", cl, "ses")
    b.doc["panel"]["rows"] = 4
    b.doc["panel"]["items"][vc] = {"r": 0, "c": 1, "rs": 4, "cs": 3}
    return b.doc


def ex_lm35():
    b = ExB("Termómetro LM35", 2, 4)
    op = b.n("open", 20, 150)
    lp = b.n("while", 200, 60, w=600, h=320)
    ch = b.c(0, 230, 140)
    ai = b.n("ai_read", 290, 110)
    k = b.c(100, 470, 210)
    sc = b.n("mul", 540, 170)
    tg = b.n("ind_gauge", 650, 110, cell=(0, 0), label="Temperatura", units="°C",
             min=0.0, max=100.0)
    tb = b.n("ind_bar", 650, 170, cell=(0, 1), label="Termómetro", units="°C",
             min=0.0, max=100.0)
    tc = b.n("ind_chart", 650, 230, cell=(0, 2, 2, 2), label="Temperatura vs tiempo")
    b.loop_end(lp, 240, 300, 250, 720, 310, (1, 0))
    cl = b.n("close", 860, 150)
    b.w(op, "ses", ai, "ses")
    b.w(ch, "v", ai, "ch")
    b.w(ai, "volts", sc, "a")
    b.w(k, "v", sc, "b")
    for t in (tg, tb, tc):
        b.w(sc, "r", t, "v")
    b.w(ai, "ses", cl, "ses")
    b.doc["panel"]["items"][tb] = {"r": 0, "c": 1, "rs": 2, "cs": 1}
    b.doc["panel"]["footer"] = {"on": True, "text": T("LM35: 10 mV/°C → °C = 100 × V  ·  "
                                                      "Vs a 5 V, salida a AI0"), "image": None}
    return b.doc


def ex_filter():
    b = ExB("Filtro digital (shift register)", 2, 4)
    op = b.n("open", 20, 150)
    lp = b.n("while", 200, 40, w=660, h=380, sr=1)
    z = b.c(0, 130, 66)
    ch = b.c(2, 240, 120)
    ai = b.n("ai_read", 300, 100)
    raw = b.n("ind_chart", 500, 80, cell=(0, 0, 1, 3), label="Señal cruda")
    sb = b.n("sub", 480, 200)
    al = b.n("ctl_slider", 420, 280, cell=(0, 3), label="α (suavizado)", min=0.01,
             max=1.0, value=0.1)
    ml = b.n("mul", 560, 220)
    ad = b.n("add", 640, 200)
    flt = b.n("ind_chart", 740, 160, cell=(1, 0, 1, 3), label="Señal filtrada")
    b.loop_end(lp, 240, 350, 50, 770, 350, (1, 3))
    cl = b.n("close", 900, 150)
    b.w(z, "v", lp, "sr0_in")
    b.w(op, "ses", ai, "ses")
    b.w(ch, "v", ai, "ch")
    b.w(ai, "volts", raw, "v")
    b.w(ai, "volts", sb, "a")
    b.w(lp, "sr0_l", sb, "b")
    b.w(sb, "r", ml, "a")
    b.w(al, "v", ml, "b")
    b.w(lp, "sr0_l", ad, "a")
    b.w(ml, "r", ad, "b")
    b.w(ad, "r", lp, "sr0_r")
    b.w(ad, "r", flt, "v")
    b.w(ai, "ses", cl, "ses")
    return b.doc


def ex_sweep():
    b = ExB("Barrido DAC → curva", 2, 4)
    op = b.n("open", 20, 150)
    lp = b.n("for", 220, 60, w=560, h=300)
    n = b.n("ctl_num", 120, 66, cell=(0, 0), label="Puntos", min=2.0, max=255.0, value=50.0)
    st = b.c(0.066, 250, 170)
    ml = b.n("mul", 320, 130)
    k0 = b.c(0, 330, 210)
    ao = b.n("ao_write", 400, 100)
    wk = b.c(20, 400, 260)
    wt = b.n("wait", 460, 256)
    k1 = b.c(0, 560, 210)
    ai = b.n("ai_read", 600, 100)
    gr = b.n("ind_graph", 860, 120, cell=(0, 1, 2, 3), label="Voltaje leído vs paso")
    cl = b.n("close", 860, 220)
    b.w(n, "v", lp, "N")
    b.w(lp, "i", ml, "a")
    b.w(st, "v", ml, "b")
    b.w(op, "ses", ao, "ses")
    b.w(k0, "v", ao, "ch")
    b.w(ml, "r", ao, "volts")
    b.w(wk, "v", wt, "ms")
    b.w(ao, "ses", ai, "ses")
    b.w(k1, "v", ai, "ch")
    b.w(ai, "volts", gr, "v")
    b.w(ai, "ses", cl, "ses")
    b.text("AO0 (GPIO26) → AI0 (GPIO36)", 0.02, 0.6)
    return b.doc


def ex_logger():
    b = ExB("Data logger CSV", 2, 4)
    op = b.n("open", 20, 150)
    lp = b.n("while", 200, 60, w=520, h=320)
    ch = b.c(2, 230, 150)
    ai = b.n("ai_read", 290, 120)
    cs = b.n("csv_write", 560, 110, path="~/lv_datos.csv")
    gc = b.n("ind_chart", 560, 180, cell=(0, 1, 2, 3), label="Datos guardados")
    b.loop_end(lp, 240, 300, 500, 640, 300, (1, 0))
    cl = b.n("close", 780, 150)
    b.w(op, "ses", ai, "ses")
    b.w(ch, "v", ai, "ch")
    b.w(ai, "volts", cs, "v")
    b.w(ai, "volts", gc, "v")
    b.w(ai, "ses", cl, "ses")
    b.text("Se guarda en ~/lv_datos.csv", 0.02, 0.2)
    return b.doc


def ex_case():
    b = ExB("Manual / automático (Case)", 2, 4)
    op = b.n("open", 20, 150)
    lp = b.n("while", 200, 40, w=740, h=440)
    ch = b.c(2, 230, 110)
    ai = b.n("ai_read", 290, 90)
    au = b.n("ctl_bool", 300, 240, cell=(0, 0), label="Automático", value=True)
    cs = b.n("case", 420, 160, w=300, h=200, outs=1, view=1)
    k = b.c(1.65, 450, 250, frame=1)
    gt = b.n("gt", 560, 220, frame=1)
    mn = b.n("ctl_bool", 520, 240, frame=0, cell=(0, 1), label="Manual")
    led = b.n("ind_led", 780, 200, cell=(0, 2), label="Salida DO0")
    k0 = b.c(0, 770, 300)
    do = b.n("do_write", 780, 250)
    b.loop_end(lp, 240, 410, 100, 860, 420, (1, 3))
    cl = b.n("close", 1000, 150)
    b.w(op, "ses", ai, "ses")
    b.w(ch, "v", ai, "ch")
    b.w(au, "v", cs, "sel")
    b.w(ai, "volts", gt, "a")
    b.w(k, "v", gt, "b")
    b.w(gt, "r", cs, "o0_i", frame=1)
    b.w(mn, "v", cs, "o0_i", frame=0)
    b.w(cs, "o0", led, "v")
    b.w(cs, "o0", do, "val")
    b.w(k0, "v", do, "ch")
    b.w(ai, "ses", do, "ses")
    b.w(do, "ses", cl, "ses")
    return b.doc


def ex_color():
    b = ExB("Color en NeoPixel", 2, 3)
    op = b.n("open", 20, 150)
    lp = b.n("while", 200, 60, w=460, h=300)
    col = b.n("ctl_color", 240, 120, cell=(0, 0), label="Color")
    neo = b.n("neo_all", 360, 110)
    b.loop_end(lp, 240, 300, 100, 560, 300, (0, 2))
    cl = b.n("close", 720, 150)
    b.w(op, "ses", neo, "ses")
    b.w(col, "r", neo, "r")
    b.w(col, "g", neo, "g")
    b.w(col, "b", neo, "b")
    b.w(neo, "ses", cl, "ses")
    b.text("Tira NeoPixel en GPIO25 (ESP32) / D6 (UNO)", 0.05, 0.7)
    return b.doc


EXAMPLES = [
    ("Leer voltaje (AI)", ex_voltage),
    ("Prender un LED (DO)", ex_led),
    ("Alarma por umbral", ex_alarm),
    ("Termómetro LM35 (escala)", ex_lm35),
    ("Filtro con shift register", ex_filter),
    ("Barrido DAC → curva (For)", ex_sweep),
    ("Data logger CSV", ex_logger),
    ("Manual / automático (Case)", ex_case),
    ("Color en NeoPixel", ex_color),
]
