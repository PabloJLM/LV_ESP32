import os

from hub.lang import T

from camilab.config import IMAGES_DIR
from camilab.documento import add_node, add_wire, new_doc
from camilab.widgets import img_to_b64


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

    def note(self, txt):
        self.doc["panel"]["footer"] = {"on": True, "text": T(txt), "image": None}

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
    b.note("Señal de 0 V a Vref en el canal AI elegido")
    return b.doc


def ex_led():
    b = ExB("Prender un LED", 1, 3)
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
    b.note("Conecta DO0 a una resistencia de 330 Ω, luego el LED y GND")
    return b.doc


def ex_sweep():
    b = ExB("Barrido DAC a curva", 2, 4)
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
    vn = b.n("ind_num", 690, 200, cell=(1, 0), label="Voltaje", units="V")
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
    b.w(ai, "volts", vn, "v")
    b.w(ai, "ses", cl, "ses")
    b.note("Conecta AO0 (GPIO26) con AI0 (GPIO36)")
    return b.doc


def ex_logger():
    b = ExB("Data logger CSV", 2, 4)
    op = b.n("open", 20, 150)
    lp = b.n("while", 200, 60, w=520, h=320)
    ch = b.c(2, 230, 150)
    ai = b.n("ai_read", 290, 120)
    cs = b.n("csv_write", 560, 110, path="~/lv_datos.csv")
    vn = b.n("ind_num", 560, 240, cell=(0, 0), label="Voltaje", units="V")
    gc = b.n("ind_chart", 560, 180, cell=(0, 1, 2, 3), label="Datos guardados")
    b.loop_end(lp, 240, 300, 500, 640, 300, (1, 0))
    cl = b.n("close", 780, 150)
    b.w(op, "ses", ai, "ses")
    b.w(ch, "v", ai, "ch")
    b.w(ai, "volts", cs, "v")
    b.w(ai, "volts", gc, "v")
    b.w(ai, "volts", vn, "v")
    b.w(ai, "ses", cl, "ses")
    b.note("Señal en AI2  ·  Se guarda en ~/lv_datos.csv")
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
    sg = b.n("ind_chart", 470, 80, cell=(1, 0, 1, 4), label="Señal")
    k0 = b.c(0, 770, 300)
    do = b.n("do_write", 780, 250)
    b.loop_end(lp, 240, 410, 100, 860, 420, (0, 3))
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
    b.w(ai, "volts", sg, "v")
    b.note("Señal en AI2  ·  En automático DO0 se enciende si pasa de 1.65 V")
    return b.doc


def ex_color():
    b = ExB("Color en NeoPixel", 1, 2)
    op = b.n("open", 20, 150)
    lp = b.n("while", 200, 60, w=460, h=300)
    col = b.n("ctl_color", 240, 120, cell=(0, 0), label="Color")
    neo = b.n("neo_all", 360, 110)
    b.loop_end(lp, 240, 300, 100, 560, 300, (0, 1))
    cl = b.n("close", 720, 150)
    b.w(op, "ses", neo, "ses")
    b.w(col, "r", neo, "r")
    b.w(col, "g", neo, "g")
    b.w(col, "b", neo, "b")
    b.w(neo, "ses", cl, "ses")
    b.note("Tira NeoPixel en GPIO25 (ESP32) / D6 (UNO)")
    return b.doc


def ex_states():
    b = ExB("Máquina de estados", 3, 4)
    op = b.n("open", 20, 220)
    k0 = b.c(0, 130, 70)
    lp = b.n("while", 200, 40, w=1000, h=540, sr=1)
    b.w(k0, "v", lp, "sr0_in")
    one = b.c(1, 240, 150)
    ad = b.n("add", 300, 110)
    est = b.n("ind_num", 380, 110, cell=(0, 3), label="Estado", rep="int")
    cs = b.n("case", 440, 170, w=440, h=330, cases=5, outs=4, view=0)
    col = b.n("ctl_color", 260, 330, cell=(1, 2), label="Color", value=[0, 200, 255])
    tm = b.n("ctl_num", 240, 520, cell=(1, 3), label="Tiempo por estado", units="ms",
             value=1000.0, min=100.0, max=5000.0, rep="int")
    wt = b.n("wait", 340, 516)
    st = b.n("ctl_stop", 1100, 530, cell=(2, 3), label="Stop")
    img = b.n("ind_img", 960, 180, cell=(0, 0, 2, 2), label="Imagen",
              image=img_to_b64(os.path.join(IMAGES_DIR, "logo.png")))
    led = b.n("ind_led", 960, 240, cell=(0, 2), label="LED del panel")
    ch = b.c(0, 920, 340)
    do = b.n("do_write", 980, 300)
    cl = b.n("close", 1260, 300)
    b.w(lp, "sr0_l", cs, "sel")
    b.w(lp, "sr0_l", ad, "a")
    b.w(one, "v", ad, "b")
    b.w(ad, "r", est, "v")
    b.w(tm, "v", wt, "ms")
    b.w(st, "v", lp, "stop")
    b.w(cs, "o0", img, "v")
    b.w(cs, "o1", led, "v")
    b.w(cs, "o2", do, "val")
    b.w(cs, "o3", lp, "sr0_r")
    b.w(op, "ses", do, "ses")
    b.w(ch, "v", do, "ch")
    b.w(do, "ses", cl, "ses")
    for f in range(5):
        vals = (f == 0, f == 1, f == 2, (f + 1) % 5)
        for k, v in enumerate(vals):
            c = b.c(v, 800, 200 + 40 * k, frame=f)
            b.w(c, "v", cs, "o%d_i" % k, frame=f)

    def neo(x, y, f, rgb):
        n = b.n("neo_all", x, y, frame=f)
        for k, v in zip("rgb", rgb):
            c = b.n("const_num", x - 70, y + {"r": 4, "g": 28, "b": 52}[k], f, value=float(v),
                    rep="byte")
            b.w(c, "v", n, k)
        b.w(op, "ses", n, "ses")
        return n

    neo(560, 230, 0, (0, 0, 0))
    off = neo(560, 230, 3, (0, 0, 0))
    px = b.n("neo_px", 660, 330, frame=3)
    p0 = b.n("const_num", 590, 330, 3, value=0.0, rep="byte")
    b.w(off, "ses", px, "ses")
    b.w(p0, "v", px, "px")
    for k in "rgb":
        b.w(col, k, px, k)
    neo(560, 230, 4, (128, 0, 128))
    b.note("Cada estado dura el tiempo elegido. LED real en DO0, tira NeoPixel en su pin por "
           "defecto.")
    return b.doc


EXAMPLES = [
    ("Leer voltaje (AI)", ex_voltage),
    ("Prender un LED (DO)", ex_led),
    ("Barrido DAC a curva (For)", ex_sweep),
    ("Data logger CSV", ex_logger),
    ("Manual / automático (Case)", ex_case),
    ("Color en NeoPixel", ex_color),
    ("Máquina de estados", ex_states),
]
