import math
import os
import random
import time

import core
from hub.dev import BOARD_NAMES, DEFAULT_VREF, VREF
from hub.lang import T

from camilab.config import PROJ
from camilab.simulador import FakeSerial


class Spec(object):
    def __init__(self, tid, cat, label, ins=(), outs=(), fn=None, params=(),
                 sym=None, kind="func", doc=""):
        self.tid = tid
        self.cat = cat
        self.label = label
        self.ins = list(ins)
        self.outs = list(outs)
        self.fn = fn
        self.params = list(params)
        self.sym = sym
        self.kind = kind
        self.doc = doc


SPECS = {}
CATS = []


def spec(*a, **k):
    s = Spec(*a, **k)
    SPECS[s.tid] = s
    if s.cat and s.cat not in CATS:
        CATS.append(s.cat)
    return s


def num(v):
    if v is None:
        return 0.0
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (list, tuple)):
        raise ValueError(T("Se esperaba un número y llegó un arreglo"))
    try:
        return float(v)
    except (TypeError, ValueError):
        raise ValueError(T("Se esperaba un número: %r") % (v,))


def boolean(v):
    if isinstance(v, (list, tuple)):
        raise ValueError(T("Se esperaba un booleano y llegó un arreglo"))
    return bool(v)


def arr(v):
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return list(v)
    return [v]


def need_ses(w):
    if w is None or not hasattr(w, "cmd"):
        raise ValueError(T("Falta la sesión: cablea 'sesión' desde 'Abrir puerto'."))
    return w


def check_ack(r):
    if r.rx[:2] == b"AA":
        return
    if r.rx[:2] == b"XX":
        raise ValueError(T("La tarjeta respondió 'X','X': canal inválido o no soportado."))
    raise ValueError(T("Sin respuesta de la tarjeta (timeout)."))


def f_open(ctx, node, inp):
    port = (inp.get("port") or node["params"].get("port") or PROJ).strip()
    if port == PROJ:
        port = ctx.project_port or "SIM"
    if port.upper() == "SIM":
        w = core.Wire(transport=FakeSerial(), timeout=0.5)
        ctx.note(T("Abrir puerto"), T("Simulador abierto (sin tarjeta)."))
    else:
        ctx.note(T("Abrir puerto"), T("Abriendo %s. La tarjeta se reinicia, espera 2 s.") % port)
        try:
            w = core.Wire(port, timeout=1.0)
        except Exception as e:
            raise ValueError(T("No se pudo abrir %s: %s") % (port, e))
    ctx.sessions.append(w)
    r = w.cmd("id")
    ctx.log(T("Identidad"), r)
    line = r.rx.decode("latin-1").strip()
    p = line.split(",")
    board = p[4] if len(p) > 4 and p[0] == "LV" else ""
    w.vref = VREF.get(board, DEFAULT_VREF)
    w.board = T(BOARD_NAMES.get(board, board or "?"))
    if not board:
        raise ValueError(T("La tarjeta en %s no responde.") % port)
    return {"ses": w, "board": "%s  (Vref %.1f V)" % (w.board, w.vref)}


def f_close(ctx, node, inp):
    w = inp["ses"]
    if w is not None and hasattr(w, "close"):
        w.close()
        if w in ctx.sessions:
            ctx.sessions.remove(w)
        ctx.note(T("Cerrar puerto"), T("Puerto cerrado."))
    return {}


def f_do(ctx, node, inp):
    w = need_ses(inp["ses"])
    r = w.cmd("do", (int(num(inp["ch"])), 1 if boolean(inp["val"]) else 0))
    ctx.log(T("Escribir digital"), r)
    check_ack(r)
    return {"ses": w}


def f_di(ctx, node, inp):
    w = need_ses(inp["ses"])
    r = w.cmd("di", (int(num(inp["ch"])),))
    ctx.log(T("Leer digital"), r)
    if r.rx[:2] == b"XX":
        check_ack(r)
    if len(r.rx) < 2:
        raise ValueError(T("Sin respuesta de la tarjeta (timeout)."))
    return {"ses": w, "val": r.rx[1:2] == b"1"}


def f_ai(ctx, node, inp):
    w = need_ses(inp["ses"])
    r = w.cmd("ai", (int(num(inp["ch"])),))
    ctx.log(T("Leer analógico"), r)
    try:
        v = int(r.rx.strip())
    except ValueError:
        raise ValueError(T("Sin respuesta de la tarjeta (timeout)."))
    if v == -1:
        raise ValueError(T("Canal no disponible ahora (ADC2 ocupado por el WiFi)."))
    if v < 0:
        raise ValueError(T("Canal analógico inválido."))
    return {"ses": w, "counts": float(v),
            "volts": v * getattr(w, "vref", 3.3) / getattr(w, "adc_max", 4095)}


def f_ao(ctx, node, inp):
    w = need_ses(inp["ses"])
    vref = getattr(w, "vref", 3.3)
    code = int(round(max(0.0, min(vref, num(inp["volts"]))) / vref * 255))
    r = w.cmd("ao", (int(num(inp["ch"])), code))
    ctx.log(T("Escribir analógico"), r)
    check_ack(r)
    return {"ses": w}


def f_gen_dac(ctx, node, inp):
    w = need_ses(inp["ses"])
    vref = getattr(w, "vref", 3.3)

    def counts(v):
        return int(round(max(0.0, min(vref, num(v))) / vref * 255))

    shape = int(max(0, min(3, round(num(inp["shape"])))))
    mhz = int(max(0, min(0xFFFFFFFF, round(num(inp["freq"]) * 1000.0))))
    duty = int(max(1, min(99, round(num(inp["duty"])))))
    r = w.cmd("gen", (int(num(inp["ch"])), shape, (mhz >> 24) & 255, (mhz >> 16) & 255,
                      (mhz >> 8) & 255, mhz & 255, counts(inp["vpp"]), counts(inp["off"]), duty))
    ctx.log(T("Generador DAC"), r)
    check_ack(r)
    return {"ses": w}


def f_gen_stop(ctx, node, inp):
    w = need_ses(inp["ses"])
    r = w.cmd("genstop", (int(num(inp["ch"])),))
    ctx.log(T("Detener generador DAC"), r)
    check_ack(r)
    return {"ses": w}


def f_pwm(ctx, node, inp):
    w = need_ses(inp["ses"])
    duty = int(round(max(0.0, min(100.0, num(inp["duty"]))) * 2.55))
    r = w.cmd("pwm", (int(num(inp["ch"])), duty))
    ctx.log(T("PWM"), r)
    check_ack(r)
    return {"ses": w}


def f_servo(ctx, node, inp):
    w = need_ses(inp["ses"])
    r = w.cmd("servo", (int(num(inp["ch"])), int(max(0, min(180, num(inp["angle"]))))))
    ctx.log(T("Servo"), r)
    check_ack(r)
    return {"ses": w}


def f_neo(ctx, node, inp):
    w = need_ses(inp["ses"])
    rgb = [int(max(0, min(255, num(inp[k])))) for k in ("r", "g", "b")]
    r = w.cmd("neo", rgb)
    ctx.log(T("NeoPixel"), r)
    check_ack(r)
    return {"ses": w}


def f_lcd(ctx, node, inp):
    w = need_ses(inp["ses"])
    addr = int(node["params"].get("addr", 39))
    r = w.cmd("lcd", (addr, int(num(inp["col"])), int(num(inp["row"]))), text=str(inp["text"]))
    ctx.log(T("LCD"), r)
    check_ack(r)
    return {"ses": w}


def check_online(r):
    if r.rx[:2] == b"AA":
        return
    if r.rx[:2] == b"XX":
        raise ValueError(T("La tarjeta respondió 'X','X'. Falta el firmware ONLINE, los datos "
                           "guardados o la conexión WiFi."))
    raise ValueError(T("Sin respuesta de la tarjeta (timeout)."))


def f_neo_px(ctx, node, inp):
    w = need_ses(inp["ses"])
    r = w.cmd("neopx", [int(max(0, min(255, num(inp[k])))) for k in ("px", "r", "g", "b")])
    ctx.log(T("NeoPixel (un píxel)"), r)
    check_ack(r)
    return {"ses": w}


def f_neo_pin(ctx, node, inp):
    w = need_ses(inp["ses"])
    r = w.cmd("neoopt", (int(max(0, min(255, num(inp["opt"])))),))
    ctx.log(T("Pin de NeoPixel"), r)
    check_ack(r)
    return {"ses": w}


def f_gen_state(ctx, node, inp):
    w = need_ses(inp["ses"])
    r = w.cmd("genst", (int(num(inp["ch"])),))
    ctx.log(T("Estado del generador DAC"), r)
    line = r.rx.decode("latin-1").strip()
    if line == "-2":
        raise ValueError(T("Esta placa no tiene generador DAC o el canal no existe."))
    try:
        on, shape, mhz, fs, fmax = [int(x) for x in line.split(",")]
    except ValueError:
        raise ValueError(T("Sin respuesta de la tarjeta (timeout)."))
    return {"ses": w, "on": bool(on), "shape": float(shape), "freq": mhz / 1000.0,
            "fs": float(fs), "fmax": fmax / 1000.0}


def f_ping(ctx, node, inp):
    w = need_ses(inp["ses"])
    r = w.cmd("ping")
    ctx.log(T("Ping"), r)
    return {"ses": w, "ok": r.rx[:2] == b"AA", "ms": r.ms}


def f_ident(ctx, node, inp):
    w = need_ses(inp["ses"])
    r = w.cmd("id")
    ctx.log(T("Identidad"), r)
    line = r.rx.decode("latin-1").strip()
    p = line.split(",")
    if p[0] != "LV" or len(p) < 5:
        raise ValueError(T("La tarjeta no respondió con una identidad válida."))
    counts = []
    for x in p[5:12]:
        try:
            counts.append(float(int(x)))
        except ValueError:
            counts.append(float("nan"))
    return {"ses": w, "line": line, "variant": p[1], "version": p[2], "mac": p[3],
            "board": p[4], "online": p[1].endswith("-ONLINE"), "counts": counts}


def f_wifi_save(ctx, node, inp):
    w = need_ses(inp["ses"])
    ssid, pw = str(inp["ssid"]), str(inp["pass"])
    if not 1 <= len(ssid.encode("utf-8")) <= 32:
        raise ValueError(T("El SSID debe tener de 1 a 32 caracteres."))
    if len(pw.encode("utf-8")) > 63:
        raise ValueError(T("La clave del WiFi puede tener hasta 63 caracteres."))
    r = w.cmd("wsave", text=ssid, text2=pw)
    ctx.log(T("Guardar WiFi"), r)
    check_online(r)
    return {"ses": w}


def f_wifi_connect(ctx, node, inp):
    w = need_ses(inp["ses"])
    r = w.cmd("wconn")
    ctx.log(T("Conectar WiFi"), r)
    check_online(r)
    return {"ses": w}


def f_wifi_disc(ctx, node, inp):
    w = need_ses(inp["ses"])
    r = w.cmd("wdisc")
    ctx.log(T("Desconectar WiFi"), r)
    check_online(r)
    return {"ses": w}


def f_wifi_status(ctx, node, inp):
    w = need_ses(inp["ses"])
    r = w.cmd("wstat")
    ctx.log(T("Estado WiFi y FTP"), r)
    p = r.rx.decode("latin-1").strip().split(",")
    try:
        wifi, ip, rssi, ftp, sd = int(p[0]), p[1], int(p[2]), int(p[3]), int(p[4])
    except (IndexError, ValueError):
        check_online(r)
        raise ValueError(T("Respuesta de estado no válida."))
    wtxt = (T("Apagado"), T("Conectando"), T("Conectado"), T("Falló"))
    ftxt = (T("Apagado"), T("Activo"), T("Error de SD"))
    return {"ses": w, "up": wifi == 2, "wifi": wtxt[wifi] if 0 <= wifi < 4 else str(wifi),
            "ip": ip, "rssi": float(rssi), "ftp_on": ftp == 1,
            "ftp": ftxt[ftp] if 0 <= ftp < 3 else str(ftp), "sd": float(sd)}


def f_ftp_save(ctx, node, inp):
    w = need_ses(inp["ses"])
    user, pw = str(inp["user"]), str(inp["pass"])
    if not (1 <= len(user.encode("utf-8")) <= 32 and 1 <= len(pw.encode("utf-8")) <= 32):
        raise ValueError(T("Usuario y clave del FTP, de 1 a 32 caracteres cada uno."))
    r = w.cmd("ftpsave", text=user, text2=pw)
    ctx.log(T("Guardar FTP"), r)
    check_online(r)
    return {"ses": w}


def f_ftp_set(ctx, node, inp):
    w = need_ses(inp["ses"])
    r = w.cmd("ftp", (1 if boolean(inp["on"]) else 0,))
    ctx.log(T("FTP y SD"), r)
    check_online(r)
    return {"ses": w}


SES = ("ses", "ses", None, "sesión")
CH = ("ch", "num", 0.0, "canal")
CAT_IO = "LV_ESP32"

spec("open", CAT_IO, "Abrir puerto", [("port", "str", None, "puerto")],
     [("ses", "ses", "sesión"), ("board", "str", "placa")],
     f_open, [("port", "port", PROJ, "Puerto")], kind="io",
     doc="Abre el puerto serie de la tarjeta. Cablea su salida 'sesión' a los bloques de E/S: "
         "ese cable marca el orden. SIM es la tarjeta simulada y (proyecto) usa el puerto del "
         ".camp. Si cableas 'puerto' (por ejemplo con un Selector de puerto), manda sobre la "
         "propiedad.")
spec("close", CAT_IO, "Cerrar puerto", [SES], [], f_close, kind="io",
     doc="Cierra el puerto. Ponlo al final, fuera del lazo.")
spec("do_write", CAT_IO, "Escribir digital", [SES, CH, ("val", "bool", False, "valor")],
     [("ses", "ses", "sesión")], f_do, kind="io",
     doc="Pone una salida digital en alto o bajo.")
spec("di_read", CAT_IO, "Leer digital", [SES, CH],
     [("ses", "ses", "sesión"), ("val", "bool", "valor")], f_di, kind="io",
     doc="Lee una entrada digital.")
spec("ai_read", CAT_IO, "Leer analógico", [SES, CH],
     [("ses", "ses", "sesión"), ("counts", "num", "cuentas"), ("volts", "num", "voltaje")],
     f_ai, kind="io",
     doc="Lee una entrada analógica en cuentas de la resolución de la placa (10 bits: 0 a 1023, "
         "12 bits: 0 a 4095). voltaje = cuentas × Vref / cuentas máx.")
spec("ao_write", CAT_IO, "Escribir analógico", [SES, CH, ("volts", "num", 0.0, "voltaje")],
     [("ses", "ses", "sesión")], f_ao, kind="io",
     doc="Saca un voltaje por el DAC (8 bits). Solo ESP32 Wrover y Nucleo tienen DAC.")
spec("gen_dac", CAT_IO, "Generador DAC",
     [SES, CH, ("shape", "num", 0.0, "forma 0-3"), ("freq", "num", 100.0, "frecuencia Hz"),
      ("vpp", "num", 2.0, "amplitud Vpp"), ("off", "num", 1.65, "offset V"),
      ("duty", "num", 50.0, "duty %")],
     [("ses", "ses", "sesión")], f_gen_dac, kind="io",
     doc="Genera una onda en el DAC desde la placa. Sigue sola hasta 'Detener generador DAC'. "
         "Forma: 0 senoidal, 1 triangular, 2 cuadrada, 3 diente de sierra. El duty solo cuenta "
         "en la cuadrada.")
spec("gen_stop", CAT_IO, "Detener generador DAC", [SES, CH], [("ses", "ses", "sesión")],
     f_gen_stop, kind="io",
     doc="Detiene el generador y deja la salida en 0 V.")
spec("pwm_write", CAT_IO, "PWM", [SES, CH, ("duty", "num", 50.0, "duty %")],
     [("ses", "ses", "sesión")], f_pwm, kind="io",
     doc="PWM de 1 kHz, duty de 0 a 100 %.")
spec("servo_write", CAT_IO, "Servo", [SES, CH, ("angle", "num", 90.0, "ángulo")],
     [("ses", "ses", "sesión")], f_servo, kind="io",
     doc="Mueve un servo de 0 a 180 grados.")
spec("neo_all", CAT_IO, "NeoPixel", [SES, ("r", "num", 0.0, "R"), ("g", "num", 0.0, "G"),
                                      ("b", "num", 0.0, "B")],
     [("ses", "ses", "sesión")], f_neo, kind="io",
     doc="Pinta toda la tira NeoPixel de un color.")
spec("lcd_write", CAT_IO, "LCD", [SES, ("row", "num", 0.0, "fila"), ("col", "num", 0.0, "columna"),
                                  ("text", "str", "", "texto")],
     [("ses", "ses", "sesión")], f_lcd, [("addr", "num", 39, "Dirección I2C")], kind="io",
     doc="Escribe texto en un LCD I2C de 16x2.")

spec("neo_px", CAT_IO, "NeoPixel (un píxel)",
     [SES, ("px", "num", 0.0, "píxel"), ("r", "num", 0.0, "R"), ("g", "num", 0.0, "G"),
      ("b", "num", 0.0, "B")],
     [("ses", "ses", "sesión")], f_neo_px, kind="io",
     doc="Pinta un solo píxel de la tira. El píxel va de 0 a 15.")
spec("neo_pin", CAT_IO, "Pin de NeoPixel", [SES, ("opt", "num", 0.0, "opción")],
     [("ses", "ses", "sesión")], f_neo_pin, kind="io",
     doc="Elige a qué pin está conectada la tira. 0 es el pin por defecto y las demás son los "
         "pines alternativos de la placa. Apaga la tira anterior.")
spec("gen_state", CAT_IO, "Estado del generador DAC", [SES, CH],
     [("ses", "ses", "sesión"), ("on", "bool", "activo"), ("shape", "num", "forma"),
      ("freq", "num", "frecuencia real Hz"), ("fs", "num", "muestras/s"),
      ("fmax", "num", "frecuencia máx. Hz")], f_gen_state, kind="io",
     doc="Pregunta a la placa qué está generando. La frecuencia real puede diferir un poco "
         "de la pedida.")

CAT_DIAG = "Diagnóstico"
spec("ping", CAT_DIAG, "Ping", [SES],
     [("ses", "ses", "sesión"), ("ok", "bool", "responde"), ("ms", "num", "latencia ms")],
     f_ping, kind="io",
     doc="Manda un ping. No da error si la placa no responde, solo pone 'responde' en falso "
         "y la latencia es el tiempo de espera.")
spec("ident", CAT_DIAG, "Identidad", [SES],
     [("ses", "ses", "sesión"), ("line", "str", "línea completa"), ("variant", "str", "variante"),
      ("version", "str", "versión"), ("mac", "str", "MAC"), ("board", "str", "placa"),
      ("online", "bool", "ONLINE"), ("counts", "arr", "canales DI DO AI AO PWM SERVO NEO")],
     f_ident, kind="io",
     doc="Lee la identidad del firmware. La MAC solo existe en las variantes ONLINE.")

CAT_NET = "WiFi y FTP"
spec("wifi_save", CAT_NET, "Guardar WiFi",
     [SES, ("ssid", "str", "", "SSID"), ("pass", "str", "", "clave")],
     [("ses", "ses", "sesión")], f_wifi_save, kind="io",
     doc="Guarda la red WiFi en la memoria de la placa. Solo firmware ONLINE. La clave queda "
         "escrita en el archivo del instrumento.")
spec("wifi_connect", CAT_NET, "Conectar WiFi", [SES], [("ses", "ses", "sesión")],
     f_wifi_connect, kind="io",
     doc="Empieza a conectar y responde al instante. Hay que consultar 'Estado WiFi y FTP' "
         "hasta ver conectado. Si en 20 s no conecta, el estado pasa a falló.")
spec("wifi_disc", CAT_NET, "Desconectar WiFi", [SES], [("ses", "ses", "sesión")],
     f_wifi_disc, kind="io",
     doc="Apaga el WiFi y el FTP. El ADC2 vuelve a estar disponible.")
spec("wifi_status", CAT_NET, "Estado WiFi y FTP", [SES],
     [("ses", "ses", "sesión"), ("up", "bool", "conectado"), ("wifi", "str", "WiFi"),
      ("ip", "str", "IP"), ("rssi", "num", "RSSI dBm"), ("ftp_on", "bool", "FTP activo"),
      ("ftp", "str", "FTP"), ("sd", "num", "SD MB")], f_wifi_status, kind="io",
     doc="Lee el estado del WiFi y del FTP. La IP es 0.0.0.0 y el RSSI 0 si no hay conexión.")
spec("ftp_save", CAT_NET, "Guardar FTP",
     [SES, ("user", "str", "", "usuario"), ("pass", "str", "", "clave")],
     [("ses", "ses", "sesión")], f_ftp_save, kind="io",
     doc="Guarda el usuario y la clave del FTP en la placa. De 1 a 32 caracteres cada uno.")
spec("ftp_set", CAT_NET, "FTP y SD", [SES, ("on", "bool", False, "encender")],
     [("ses", "ses", "sesión")], f_ftp_set, kind="io",
     doc="Enciende o apaga el servidor FTP y la tarjeta SD. Necesita el WiFi conectado, los "
         "datos del FTP guardados y una SD puesta.")


def safe_div(a, b):
    return a / b if b else float("nan")


CAT_NUM = "Numérico"
A = ("a", "num", 0.0, "x")
B = ("b", "num", 0.0, "y")
R = [("r", "num", "resultado")]


def binop(tid, sym, label, f, doc):
    spec(tid, CAT_NUM, label, [A, B], R,
         lambda c, n, i, f=f: {"r": f(num(i["a"]), num(i["b"]))}, sym=sym, doc=doc)


def unop(tid, sym, label, f, doc):
    spec(tid, CAT_NUM, label, [A], R, lambda c, n, i, f=f: {"r": f(num(i["a"]))}, sym=sym, doc=doc)


def const_rep(v, rep):
    v = num(v)
    if rep == "int":
        return float(int(max(-2147483648, min(2147483647, round(v)))))
    if rep == "byte":
        return float(int(max(0, min(255, round(v)))))
    return v


spec("const_num", CAT_NUM, "Constante numérica", [], [("v", "num", "valor")],
     lambda c, n, i: {"v": const_rep(n["params"].get("value", 0), n["params"].get("rep"))},
     [("value", "num", 0.0, "Valor"), ("rep", "rep", "double", "Representación")],
     kind="const",
     doc="Un número fijo. Doble clic para cambiarlo.")
binop("add", "+", "Suma", lambda a, b: a + b, "x + y")
binop("sub", "−", "Resta", lambda a, b: a - b, "x − y")
binop("mul", "×", "Multiplicación", lambda a, b: a * b, "x × y")
binop("div", "÷", "División", safe_div, "x ÷ y  (NaN si y = 0)")
unop("abs", "|x|", "Valor absoluto", abs, "|x|")
unop("sqrt", "√", "Raíz cuadrada", lambda a: math.sqrt(a) if a >= 0 else float("nan"), "√x")
unop("round", "≈", "Redondear", lambda a: float(round(a)), "Entero más cercano")
spec("random", CAT_NUM, "Aleatorio", [], R, lambda c, n, i: {"r": random.random()},
     sym="⚄", doc="Número aleatorio entre 0 y 1.")
spec("scale", CAT_NUM, "Escalar (m·x + b)",
     [A, ("m", "num", 1.0, "m"), ("b", "num", 0.0, "b")], R,
     lambda c, n, i: {"r": num(i["a"]) * num(i["m"]) + num(i["b"])}, sym="mx+b",
     doc="Convierte una lectura a unidades físicas: y = m·x + b. "
         "Ej. LM35: °C = 100 × V.")
spec("map", CAT_NUM, "Mapear rango",
     [A, ("in_lo", "num", 0.0, "entrada mín"), ("in_hi", "num", 4095.0, "entrada máx"),
      ("out_lo", "num", 0.0, "salida mín"), ("out_hi", "num", 100.0, "salida máx")], R,
     lambda c, n, i: {"r": num(i["out_lo"]) + (num(i["a"]) - num(i["in_lo"])) *
                      (num(i["out_hi"]) - num(i["out_lo"])) /
                      ((num(i["in_hi"]) - num(i["in_lo"])) or 1e-12)},
     sym="map", doc="Lleva x del rango [entrada mín, entrada máx] al rango [salida mín, salida máx].")

CAT_CMP = "Comparación"
RB = [("r", "bool", "resultado")]


def cmpop(tid, sym, label, f):
    spec(tid, CAT_CMP, label, [A, B], RB,
         lambda c, n, i, f=f: {"r": bool(f(num(i["a"]), num(i["b"])))}, sym=sym,
         doc="Compara x con y y da verdadero/falso.")


cmpop("gt", ">", "Mayor que", lambda a, b: a > b)
cmpop("lt", "<", "Menor que", lambda a, b: a < b)
cmpop("ge", "≥", "Mayor o igual", lambda a, b: a >= b)
cmpop("le", "≤", "Menor o igual", lambda a, b: a <= b)
cmpop("eq", "=", "Igual", lambda a, b: a == b)
cmpop("ne", "≠", "Distinto", lambda a, b: a != b)
spec("in_range", CAT_CMP, "En rango", [A, ("lo", "num", 0.0, "mín"), ("hi", "num", 1.0, "máx")], RB,
     lambda c, n, i: {"r": num(i["lo"]) <= num(i["a"]) <= num(i["hi"])}, sym="≤x≤",
     doc="Verdadero si mín ≤ x ≤ máx.")
spec("select", CAT_CMP, "Seleccionar",
     [("s", "bool", False, "condición"), ("t", "any", 0.0, "si verdadero"),
      ("f", "any", 0.0, "si falso")], [("r", "any", "resultado")],
     lambda c, n, i: {"r": i["t"] if boolean(i["s"]) else i["f"]}, sym="?:",
     doc="Si la condición es verdadera sale 'si verdadero'; si no, 'si falso'.")

CAT_BOOL = "Booleano"
spec("const_bool", CAT_BOOL, "Constante booleana", [], [("v", "bool", "valor")],
     lambda c, n, i: {"v": bool(n["params"].get("value", False))},
     [("value", "bool", False, "Valor")], kind="const",
     doc="Verdadero o falso fijo. Doble clic para cambiarlo.")
BA = ("a", "bool", False, "x")
BB = ("b", "bool", False, "y")
spec("and", CAT_BOOL, "Y (AND)", [BA, BB], RB,
     lambda c, n, i: {"r": boolean(i["a"]) and boolean(i["b"])}, sym="AND", doc="x Y y")
spec("or", CAT_BOOL, "O (OR)", [BA, BB], RB,
     lambda c, n, i: {"r": boolean(i["a"]) or boolean(i["b"])}, sym="OR", doc="x O y")
spec("xor", CAT_BOOL, "O exclusivo (XOR)", [BA, BB], RB,
     lambda c, n, i: {"r": boolean(i["a"]) != boolean(i["b"])}, sym="XOR", doc="x distinto de y")
spec("not", CAT_BOOL, "No (NOT)", [BA], RB, lambda c, n, i: {"r": not boolean(i["a"])},
     sym="NOT", doc="Invierte el valor.")

CAT_ARR = "Arreglos"
AR = ("arr", "arr", None, "arreglo")


def arr_stat(f):
    def g(c, n, i):
        a = [num(x) for x in arr(i["arr"])]
        return {"r": f(a) if a else float("nan")}
    return g


spec("arr_size", CAT_ARR, "Tamaño de arreglo", [AR], R,
     lambda c, n, i: {"r": float(len(arr(i["arr"])))}, sym="#", doc="Cuántos elementos tiene.")
spec("arr_index", CAT_ARR, "Índice de arreglo", [AR, ("i", "num", 0.0, "índice")],
     [("r", "any", "elemento")],
     lambda c, n, i: {"r": arr(i["arr"])[int(num(i["i"]))]
                      if 0 <= int(num(i["i"])) < len(arr(i["arr"])) else 0.0},
     sym="[i]", doc="Elemento en la posición índice (empieza en 0).")
spec("arr_mean", CAT_ARR, "Promedio", [AR], R, arr_stat(lambda a: sum(a) / len(a)),
     sym="x̄", doc="Promedio de los elementos.")
spec("arr_max", CAT_ARR, "Máximo", [AR], R, arr_stat(max), sym="max", doc="Elemento mayor.")
spec("arr_min", CAT_ARR, "Mínimo", [AR], R, arr_stat(min), sym="min", doc="Elemento menor.")
spec("arr_append", CAT_ARR, "Agregar elemento", [AR, ("x", "any", 0.0, "elemento")],
     [("r", "arr", "arreglo")], lambda c, n, i: {"r": arr(i["arr"]) + [i["x"]]},
     sym="[+]", doc="Arreglo con el elemento agregado al final. Con un shift register "
                    "sirve para ir guardando lecturas.")

CAT_TIME = "Tiempo"


def f_wait(ctx, node, inp):
    ctx.sleep(max(0.0, num(inp["ms"])) / 1000.0)
    return {}


spec("wait", CAT_TIME, "Esperar (ms)", [("ms", "num", 100.0, "ms")], [], f_wait, sym="⌛",
     doc="Espera esos milisegundos. Dentro de un lazo fija el ritmo de muestreo.")
spec("tick", CAT_TIME, "Tiempo (s)", [], [("r", "num", "segundos")],
     lambda c, n, i: {"r": time.perf_counter() - c.t0}, sym="⏱",
     doc="Segundos desde que se presionó Run.")

CAT_STR = "Texto"
spec("const_str", CAT_STR, "Constante de texto", [], [("v", "str", "texto")],
     lambda c, n, i: {"v": str(n["params"].get("value", ""))},
     [("value", "str", "", "Texto")], kind="const", doc="Texto fijo. Doble clic para cambiarlo.")
spec("num_to_str", CAT_STR, "Número a texto", [A, ("dec", "num", 2.0, "decimales")],
     [("r", "str", "texto")],
     lambda c, n, i: {"r": "%.*f" % (int(max(0, min(9, num(i["dec"])))), num(i["a"]))},
     sym="1→a", doc="Convierte un número a texto con esos decimales.")
spec("concat", CAT_STR, "Concatenar", [("a", "str", "", "a"), ("b", "str", "", "b")],
     [("r", "str", "texto")], lambda c, n, i: {"r": str(i["a"]) + str(i["b"])}, sym="a+b",
     doc="Une dos textos.")

CAT_FILE = "Archivo"


def f_csv(ctx, node, inp):
    path = os.path.expanduser(node["params"].get("path") or "~/lv_datos.csv")
    v = inp["v"]
    vals = arr(v) if isinstance(v, (list, tuple)) else [v]
    new = not os.path.isfile(path)
    try:
        with open(path, "a", encoding="utf-8") as f:
            if new:
                f.write("t (s)," + ",".join("v%d" % k for k in range(len(vals))) + "\n")
            f.write("%.3f,%s\n" % (time.perf_counter() - ctx.t0,
                                   ",".join("%.6g" % num(x) for x in vals)))
    except OSError as e:
        raise ValueError(T("No se pudo escribir %s: %s") % (path, e))
    return {}


spec("csv_write", CAT_FILE, "Escribir CSV", [("v", "any", 0.0, "valor")], [], f_csv,
     [("path", "str", "~/lv_datos.csv", "Archivo")], sym="CSV",
     doc="Agrega una fila al archivo: tiempo y el valor (o los valores de un arreglo).")

CAT_STRUCT = "Estructuras"
spec("while", CAT_STRUCT, "While Loop", kind="struct",
     doc="Repite hasta que Stop (abajo a la derecha) reciba verdadero. 'i' cuenta desde 0.")
spec("for", CAT_STRUCT, "For Loop", kind="struct",
     doc="Repite N veces, 'i' va de 0 a N−1. Lo que sale del lazo se junta en un arreglo.")
spec("case", CAT_STRUCT, "Case (if)", kind="struct",
     doc="Ejecuta un caso según '?'. Con un booleano usa Falso y Verdadero, con un número el "
         "caso de ese índice (fuera de rango usa el 0). Clic derecho para agregar casos y salidas.")

def f_ctl(ctx, node, inp):
    v = ctx.ctl(node["id"])
    if node["type"] == "ctl_color":
        r, g, b = v if isinstance(v, (list, tuple)) and len(v) == 3 else (0, 0, 0)
        return {"r": float(r), "g": float(g), "b": float(b)}
    return {"v": v}


def f_ind(ctx, node, inp):
    ctx.show(node["id"], inp["v"])
    return {}


CTL_KINDS = [
    ("ctl_num", "Control numérico", [("v", "num", "valor")]),
    ("ctl_knob", "Perilla", [("v", "num", "valor")]),
    ("ctl_slider", "Deslizador", [("v", "num", "valor")]),
    ("ctl_str", "Texto de entrada", [("v", "str", "texto")]),
    ("ctl_ring", "Ring (lista)", [("v", "num", "índice")]),
    ("ctl_color", "Selector de color", [("r", "num", "R"), ("g", "num", "G"), ("b", "num", "B")]),
    ("ctl_bool", "Interruptor", [("v", "bool", "valor")]),
    ("ctl_stop", "Botón Stop", [("v", "bool", "valor")]),
    ("ctl_port", "Selector de puerto", [("v", "str", "puerto")]),
    ("ctl_arr_num", "Arreglo numérico", [("v", "arr", "arreglo")]),
    ("ctl_arr_bool", "Arreglo booleano", [("v", "arr", "arreglo")]),
    ("ctl_arr_str", "Arreglo de texto", [("v", "arr", "arreglo")]),
]
IND_KINDS = [
    ("ind_num", "Pantalla numérica", "num"),
    ("ind_led", "LED", "bool"),
    ("ind_img", "Imagen (booleano)", "bool"),
    ("ind_gauge", "Gauge", "num"),
    ("ind_bar", "Barra / termómetro", "num"),
    ("ind_chart", "Plot en el tiempo", "any"),
    ("ind_graph", "Gráfica de arreglo", "arr"),
    ("ind_str", "Pantalla de texto", "any"),
    ("ind_arr_num", "Pantalla de arreglo numérico", "arr"),
    ("ind_arr_bool", "Pantalla de arreglo booleano", "arr"),
    ("ind_arr_str", "Pantalla de arreglo de texto", "arr"),
]
CTL_DOC = "Terminal de un control del panel frontal: entrega lo que el usuario pone ahí."
IND_DOC = "Terminal de un indicador del panel frontal: muestra el valor que le llega."
for _k, _l, _o in CTL_KINDS:
    spec(_k, None, _l, [], _o, f_ctl, kind="ctl", doc=CTL_DOC)
for _k, _l, _t in IND_KINDS:
    spec(_k, None, _l, [("v", _t, 0.0, "valor")], [], f_ind, kind="ind", doc=IND_DOC)

PANEL_ONLY = [("image", "Imagen"), ("text", "Texto libre")]
