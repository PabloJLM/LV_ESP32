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


AI_OPTS = "AI0;AI1;AI2;AI3;AI4;AI5"


def ex_digital_read():
    b = ExB("Leer una entrada digital", 1, 3)
    op = b.n("open", 20, 150)
    lp = b.n("while", 200, 60, w=520, h=320)
    ch = b.n("ctl_ring", 220, 120, cell=(0, 0), label="Canal DI",
             options="DI0;DI1;DI2;DI3", value=0.0)
    di = b.n("di_read", 300, 120)
    led = b.n("ind_led", 560, 150, cell=(0, 1), label="Entrada")
    b.loop_end(lp, 240, 300, 50, 640, 300, (0, 2))
    cl = b.n("close", 780, 150)
    b.w(op, "ses", di, "ses")
    b.w(ch, "v", di, "ch")
    b.w(di, "val", led, "v")
    b.w(di, "ses", cl, "ses")
    b.note("Conecta un botón o interruptor a la entrada digital elegida")
    return b.doc


def ex_digital_io():
    b = ExB("Entrada digital a salida digital", 1, 3)
    op = b.n("open", 20, 150)
    lp = b.n("while", 200, 60, w=560, h=320)
    ci = b.c(0, 220, 130)
    di = b.n("di_read", 280, 110)
    co = b.c(0, 360, 230)
    do = b.n("do_write", 420, 110)
    l1 = b.n("ind_led", 560, 100, cell=(0, 0), label="Entrada DI0")
    l2 = b.n("ind_led", 560, 180, cell=(0, 1), label="Salida DO0")
    b.loop_end(lp, 240, 300, 50, 680, 300, (0, 2))
    cl = b.n("close", 820, 150)
    b.w(op, "ses", di, "ses")
    b.w(ci, "v", di, "ch")
    b.w(di, "ses", do, "ses")
    b.w(co, "v", do, "ch")
    b.w(di, "val", do, "val")
    b.w(di, "val", l1, "v")
    b.w(di, "val", l2, "v")
    b.w(do, "ses", cl, "ses")
    b.note("Lo que entra por DI0 se refleja en DO0")
    return b.doc


def ex_analog_read():
    b = ExB("Leer analógico (cuentas y voltaje)", 2, 4)
    op = b.n("open", 20, 150)
    lp = b.n("while", 200, 60, w=560, h=320)
    ch = b.n("ctl_ring", 220, 120, cell=(0, 0), label="Canal AI", options=AI_OPTS, value=2.0)
    ai = b.n("ai_read", 300, 120)
    cn = b.n("ind_num", 560, 100, cell=(0, 1), label="Cuentas", rep="int")
    vn = b.n("ind_num", 560, 170, cell=(0, 2), label="Voltaje", units="V")
    br = b.n("ind_bar", 640, 220, cell=(1, 0, 1, 3), label="Nivel", min=0.0, max=3.3, units="V")
    b.loop_end(lp, 240, 300, 100, 680, 300, (0, 3))
    cl = b.n("close", 820, 150)
    b.w(op, "ses", ai, "ses")
    b.w(ch, "v", ai, "ch")
    b.w(ai, "counts", cn, "v")
    b.w(ai, "volts", vn, "v")
    b.w(ai, "volts", br, "v")
    b.w(ai, "ses", cl, "ses")
    b.note("Cuentas de 0 a 4095 en 12 bits (0 a 1023 en 10 bits)")
    return b.doc


def ex_analog_write():
    b = ExB("Escribir analógico (DAC)", 2, 3)
    op = b.n("open", 20, 150)
    lp = b.n("while", 200, 60, w=520, h=320)
    sl = b.n("ctl_slider", 220, 110, cell=(0, 0, 1, 3), label="Voltaje de salida",
             units="V", min=0.0, max=3.3, value=1.0)
    ch = b.c(0, 260, 190)
    ao = b.n("ao_write", 340, 110)
    vn = b.n("ind_num", 560, 110, cell=(1, 0), label="Salida AO0", units="V")
    br = b.n("ind_bar", 560, 180, cell=(1, 1), label="Nivel", min=0.0, max=3.3, units="V")
    b.loop_end(lp, 240, 300, 50, 640, 300, (1, 2))
    cl = b.n("close", 780, 150)
    b.w(op, "ses", ao, "ses")
    b.w(ch, "v", ao, "ch")
    b.w(sl, "v", ao, "volts")
    b.w(sl, "v", vn, "v")
    b.w(sl, "v", br, "v")
    b.w(ao, "ses", cl, "ses")
    b.note("Solo ESP32 Wrover y Nucleo F303K8 tienen DAC. Salida en AO0")
    return b.doc


def ex_analog_io():
    b = ExB("Entrada analógica a salida analógica", 3, 4)
    op = b.n("open", 20, 150)
    lp = b.n("while", 200, 60, w=560, h=320)
    ch = b.n("ctl_ring", 220, 120, cell=(2, 0), label="Canal AI", options=AI_OPTS, value=2.0)
    ai = b.n("ai_read", 300, 120)
    k0 = b.c(0, 330, 230)
    ao = b.n("ao_write", 400, 110)
    vn = b.n("ind_num", 560, 110, cell=(2, 1), label="Voltaje", units="V")
    gc = b.n("ind_chart", 560, 180, cell=(0, 0, 2, 4), label="Señal reproducida")
    b.loop_end(lp, 240, 300, 50, 680, 300, (2, 3))
    cl = b.n("close", 820, 150)
    b.w(op, "ses", ai, "ses")
    b.w(ch, "v", ai, "ch")
    b.w(ai, "ses", ao, "ses")
    b.w(k0, "v", ao, "ch")
    b.w(ai, "volts", ao, "volts")
    b.w(ai, "volts", vn, "v")
    b.w(ai, "volts", gc, "v")
    b.w(ao, "ses", cl, "ses")
    b.note("Lo que se lee en la entrada analógica sale por AO0")
    return b.doc


def ex_pwm():
    b = ExB("PWM (brillo de un LED)", 2, 3)
    op = b.n("open", 20, 150)
    lp = b.n("while", 200, 60, w=520, h=320)
    ch = b.n("ctl_ring", 220, 110, cell=(0, 0), label="Canal PWM", options="PWM0;PWM1",
             value=0.0)
    sl = b.n("ctl_slider", 220, 180, cell=(0, 1, 1, 2), label="Ciclo de trabajo", units="%",
             min=0.0, max=100.0, value=50.0)
    pw = b.n("pwm_write", 340, 110)
    br = b.n("ind_bar", 560, 110, cell=(1, 0, 1, 2), label="Duty", units="%", min=0.0, max=100.0)
    b.loop_end(lp, 240, 300, 50, 640, 300, (1, 2))
    cl = b.n("close", 780, 150)
    b.w(op, "ses", pw, "ses")
    b.w(ch, "v", pw, "ch")
    b.w(sl, "v", pw, "duty")
    b.w(sl, "v", br, "v")
    b.w(pw, "ses", cl, "ses")
    b.note("PWM de 1 kHz. Conecta un LED con resistencia de 330 Ω")
    return b.doc


def ex_servo():
    b = ExB("Control de servo", 2, 3)
    op = b.n("open", 20, 150)
    lp = b.n("while", 200, 60, w=520, h=320)
    ch = b.n("ctl_ring", 220, 110, cell=(0, 0), label="Canal servo", options="Servo0;Servo1",
             value=0.0)
    kn = b.n("ctl_knob", 220, 180, cell=(0, 1, 2, 1), label="Ángulo", units="°",
             min=0.0, max=180.0, value=90.0)
    sv = b.n("servo_write", 340, 110)
    gg = b.n("ind_gauge", 560, 110, cell=(0, 2, 2, 1), label="Posición", units="°",
             min=0.0, max=180.0)
    b.loop_end(lp, 240, 300, 50, 640, 300, (1, 0))
    cl = b.n("close", 780, 150)
    b.w(op, "ses", sv, "ses")
    b.w(ch, "v", sv, "ch")
    b.w(kn, "v", sv, "angle")
    b.w(kn, "v", gg, "v")
    b.w(sv, "ses", cl, "ses")
    b.note("Alimenta el servo con una fuente externa y une las tierras")
    return b.doc


def ex_neo_px():
    b = ExB("NeoPixel: un píxel", 2, 2)
    op = b.n("open", 20, 150)
    lp = b.n("while", 200, 60, w=520, h=320)
    px = b.n("ctl_num", 220, 110, cell=(0, 0), label="Píxel", min=0.0, max=15.0, value=0.0,
             rep="byte")
    col = b.n("ctl_color", 220, 180, cell=(0, 1), label="Color")
    nx = b.n("neo_px", 360, 100)
    b.loop_end(lp, 240, 300, 100, 640, 300, (1, 0))
    cl = b.n("close", 780, 150)
    b.w(op, "ses", nx, "ses")
    b.w(px, "v", nx, "px")
    b.w(col, "r", nx, "r")
    b.w(col, "g", nx, "g")
    b.w(col, "b", nx, "b")
    b.w(nx, "ses", cl, "ses")
    b.note("Cambia el número de píxel y el color para pintar cada LED de la tira")
    return b.doc


def ex_lcd():
    b = ExB("Texto en LCD I2C", 2, 3)
    op = b.n("open", 20, 150)
    lp = b.n("while", 200, 60, w=520, h=320)
    tx = b.n("ctl_str", 220, 110, cell=(0, 0, 1, 2), label="Texto", value="Hola CamiLab")
    rw = b.n("ctl_ring", 220, 170, cell=(0, 2), label="Fila", options="Fila 1;Fila 2", value=0.0)
    cn = b.n("ctl_num", 220, 230, cell=(1, 0), label="Columna", min=0.0, max=15.0, value=0.0,
             rep="byte")
    lc = b.n("lcd_write", 360, 100, addr=39)
    b.loop_end(lp, 240, 300, 300, 640, 300, (1, 2))
    cl = b.n("close", 780, 150)
    b.w(op, "ses", lc, "ses")
    b.w(tx, "v", lc, "text")
    b.w(rw, "v", lc, "row")
    b.w(cn, "v", lc, "col")
    b.w(lc, "ses", cl, "ses")
    b.note("LCD de 16x2 en I2C (dirección 0x27 por defecto; se cambia en el bloque)")
    return b.doc


def ex_analog_pwm():
    b = ExB("Analógico a PWM", 3, 4)
    op = b.n("open", 20, 150)
    lp = b.n("while", 200, 60, w=640, h=320)
    ch = b.n("ctl_ring", 220, 110, cell=(2, 0), label="Canal AI", options=AI_OPTS, value=2.0)
    ai = b.n("ai_read", 300, 110)
    m = b.n("map", 400, 100)
    lo, hi, ol, oh = b.c(0, 330, 230), b.c(3.3, 380, 230), b.c(0, 430, 230), b.c(100, 480, 230)
    k0 = b.c(0, 530, 250)
    pw = b.n("pwm_write", 560, 110)
    vn = b.n("ind_num", 680, 110, cell=(2, 1), label="Voltaje", units="V")
    br = b.n("ind_bar", 680, 170, cell=(2, 2), label="Duty", units="%", min=0.0, max=100.0)
    gc = b.n("ind_chart", 680, 230, cell=(0, 0, 2, 4), label="Duty (%)")
    b.loop_end(lp, 240, 300, 50, 780, 300, (2, 3))
    cl = b.n("close", 940, 150)
    b.w(op, "ses", ai, "ses")
    b.w(ch, "v", ai, "ch")
    b.w(ai, "volts", m, "a")
    b.w(lo, "v", m, "in_lo")
    b.w(hi, "v", m, "in_hi")
    b.w(ol, "v", m, "out_lo")
    b.w(oh, "v", m, "out_hi")
    b.w(ai, "ses", pw, "ses")
    b.w(k0, "v", pw, "ch")
    b.w(m, "r", pw, "duty")
    b.w(ai, "volts", vn, "v")
    b.w(m, "r", br, "v")
    b.w(m, "r", gc, "v")
    b.w(pw, "ses", cl, "ses")
    b.note("0 V a 3.3 V en la entrada es 0 % a 100 % en PWM0")
    return b.doc


def ex_generator():
    b = ExB("Generador de funciones (DAC)", 4, 4)
    op = b.n("open", 20, 260)
    sh = b.n("ctl_ring", 120, 20, cell=(0, 2), label="Forma",
             options=";".join(T(x) for x in ("Senoidal", "Triangular", "Cuadrada",
                                             "Diente de sierra")), value=0.0)
    fr = b.n("ctl_num", 120, 70, cell=(0, 3), label="Frecuencia", units="Hz", min=0.1, max=10.0,
             value=1.0)
    vp = b.n("ctl_num", 120, 120, cell=(1, 2), label="Amplitud", units="Vpp", min=0.0, max=3.3,
             value=2.0)
    of = b.n("ctl_num", 120, 170, cell=(1, 3), label="Offset", units="V", min=0.0, max=3.3,
             value=1.65)
    du = b.n("ctl_num", 120, 220, cell=(2, 2), label="Duty (cuadrada)", units="%", min=0.0,
             max=100.0, value=50.0)
    c0 = b.c(0, 180, 300)
    gd = b.n("gen_dac", 260, 120)
    c1 = b.c(0, 300, 300)
    gs = b.n("gen_state", 360, 120)
    rf = b.n("ind_num", 460, 150, cell=(2, 3), label="Frecuencia real", units="Hz", dec=2)
    lp = b.n("while", 540, 40, w=420, h=300)
    k1 = b.c(0, 560, 200)
    ai = b.n("ai_read", 600, 120)
    gc = b.n("ind_chart", 780, 110, cell=(0, 0, 4, 2), label="Señal en AI0", hist=300.0)
    b.loop_end(lp, 560, 270, 20, 860, 270, (3, 3))
    c2 = b.c(0, 1000, 220)
    gp = b.n("gen_stop", 1020, 120)
    cl = b.n("close", 1120, 150)
    b.w(op, "ses", gd, "ses")
    b.w(c0, "v", gd, "ch")
    b.w(sh, "v", gd, "shape")
    b.w(fr, "v", gd, "freq")
    b.w(vp, "v", gd, "vpp")
    b.w(of, "v", gd, "off")
    b.w(du, "v", gd, "duty")
    b.w(gd, "ses", gs, "ses")
    b.w(c1, "v", gs, "ch")
    b.w(gs, "freq", rf, "v")
    b.w(gs, "ses", ai, "ses")
    b.w(k1, "v", ai, "ch")
    b.w(ai, "volts", gc, "v")
    b.w(ai, "ses", gp, "ses")
    b.w(c2, "v", gp, "ch")
    b.w(gp, "ses", cl, "ses")
    b.note("Une AO0 con AI0. Ajusta la onda antes de presionar Run; al parar, el DAC vuelve a 0 V")
    return b.doc


def ex_board_info():
    b = ExB("Información de la placa", 3, 3)
    op = b.n("open", 20, 150)
    idn = b.n("ident", 130, 40)
    bd = b.n("ind_str", 300, 30, cell=(0, 0), label="Placa")
    va = b.n("ind_str", 300, 80, cell=(0, 1), label="Variante")
    ve = b.n("ind_str", 300, 130, cell=(0, 2), label="Versión")
    ca = b.n("ind_arr_num", 300, 190, cell=(1, 0, 1, 3),
             label="Canales (DI DO AI AO PWM SERVO NEO)")
    pg = b.n("ping", 230, 260)
    ok = b.n("ind_led", 330, 250, cell=(2, 0), label="Responde")
    ms = b.n("ind_num", 330, 310, cell=(2, 1), label="Latencia", units="ms", dec=1)
    cl = b.n("close", 430, 260)
    b.w(op, "ses", idn, "ses")
    b.w(idn, "board", bd, "v")
    b.w(idn, "variant", va, "v")
    b.w(idn, "version", ve, "v")
    b.w(idn, "counts", ca, "v")
    b.w(idn, "ses", pg, "ses")
    b.w(pg, "ok", ok, "v")
    b.w(pg, "ms", ms, "v")
    b.w(pg, "ses", cl, "ses")
    b.note("Se ejecuta una vez: presiona Run para consultar la placa")
    return b.doc


def ex_scope():
    b = ExB("Osciloscopio de 2 canales", 3, 4)
    op = b.n("open", 20, 150)
    lp = b.n("while", 200, 40, w=640, h=340)
    ca = b.n("ctl_ring", 220, 90, cell=(2, 0), label="Canal A", options=AI_OPTS, value=2.0)
    cb = b.n("ctl_ring", 220, 150, cell=(2, 1), label="Canal B", options=AI_OPTS, value=5.0)
    a1 = b.n("ai_read", 320, 90)
    a2 = b.n("ai_read", 420, 90)
    bl = b.n("arr_build", 520, 90, n=2)
    gc = b.n("ind_chart", 620, 90, cell=(0, 0, 2, 4), label="Canales A y B", multi=True,
             hist=200.0, units="V")
    b.loop_end(lp, 240, 300, 20, 760, 300, (2, 3))
    cl = b.n("close", 920, 150)
    b.w(op, "ses", a1, "ses")
    b.w(ca, "v", a1, "ch")
    b.w(a1, "ses", a2, "ses")
    b.w(cb, "v", a2, "ch")
    b.w(a1, "volts", bl, "a")
    b.w(a2, "volts", bl, "b")
    b.w(bl, "r", gc, "v")
    b.w(a2, "ses", cl, "ses")
    b.note("Cada canal se dibuja con su color. Prueba AI2 (senoidal) y AI5 (cuadrada) en el simulador")
    return b.doc


def ex_xy_sweep():
    b = ExB("Curva DAC vs ADC (XY)", 2, 4)
    op = b.n("open", 20, 150)
    lp = b.n("for", 220, 60, w=560, h=300)
    n = b.n("ctl_num", 120, 66, cell=(0, 0), label="Puntos", min=2.0, max=255.0, value=50.0,
            rep="int")
    st = b.c(0.066, 250, 170)
    ml = b.n("mul", 320, 130)
    k0 = b.c(0, 330, 210)
    ao = b.n("ao_write", 400, 100)
    wk = b.c(20, 400, 260)
    wt = b.n("wait", 460, 256)
    k1 = b.c(0, 560, 210)
    ai = b.n("ai_read", 600, 100)
    xy = b.n("ind_xy", 860, 120, cell=(0, 1, 2, 3), label="Voltaje leído vs voltaje escrito")
    cl = b.n("close", 860, 240)
    b.w(n, "v", lp, "N")
    b.w(lp, "i", ml, "a")
    b.w(st, "v", ml, "b")
    b.w(op, "ses", ao, "ses")
    b.w(k0, "v", ao, "ch")
    b.w(ml, "r", ao, "volts")
    b.w(wk, "v", wt, "ms")
    b.w(ao, "ses", ai, "ses")
    b.w(k1, "v", ai, "ch")
    b.w(ml, "r", xy, "x")
    b.w(ai, "volts", xy, "y")
    b.w(ai, "ses", cl, "ses")
    b.note("Conecta AO0 con AI0: debe salir una recta de 45°")
    return b.doc


EXAMPLE_GROUPS = [
    ("Básicos", [
        ("Leer voltaje (AI)", ex_voltage),
        ("Prender un LED (DO)", ex_led),
        ("Leer una entrada digital", ex_digital_read),
        ("Entrada digital a salida digital", ex_digital_io),
        ("Leer analógico (cuentas y voltaje)", ex_analog_read),
        ("Escribir analógico (DAC)", ex_analog_write),
        ("Entrada analógica a salida analógica", ex_analog_io),
        ("PWM (brillo de un LED)", ex_pwm),
    ]),
    ("Avanzados", [
        ("Control de servo", ex_servo),
        ("Color en NeoPixel", ex_color),
        ("NeoPixel: un píxel", ex_neo_px),
        ("Texto en LCD I2C", ex_lcd),
        ("Analógico a PWM", ex_analog_pwm),
        ("Generador de funciones (DAC)", ex_generator),
        ("Información de la placa", ex_board_info),
        ("Data logger CSV", ex_logger),
    ]),
    ("Gráficas y estructuras", [
        ("Osciloscopio de 2 canales", ex_scope),
        ("Barrido DAC a curva (For)", ex_sweep),
        ("Curva DAC vs ADC (XY)", ex_xy_sweep),
        ("Manual / automático (Case)", ex_case),
        ("Máquina de estados", ex_states),
    ]),
]
EXAMPLES = [e for _g, es in EXAMPLE_GROUPS for e in es]
