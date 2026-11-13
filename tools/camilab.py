import base64
import copy
import json
import math
import os
import random
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtCore import (QByteArray, QBuffer, QIODevice, QMimeData, QObject, QPoint,
                          QPointF, QRectF, QSize, Qt, QThread, QTimer, pyqtSignal)
from PyQt5.QtGui import (QBrush, QColor, QDrag, QFont, QFontMetrics, QIcon, QImage,
                         QKeySequence, QPainter, QPainterPath, QPainterPathStroker, QPen,
                         QPixmap, QPolygonF)
from PyQt5.QtWidgets import (QAction, QApplication, QCheckBox, QColorDialog, QComboBox,
                             QDial, QDialog, QDialogButtonBox, QDockWidget, QDoubleSpinBox,
                             QFileDialog, QFormLayout, QFrame, QGraphicsItem,
                             QGraphicsObject, QGraphicsPathItem, QGraphicsScene,
                             QGraphicsView, QGridLayout, QGroupBox, QHBoxLayout,
                             QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QPushButton,
                             QSizePolicy, QSlider, QSpinBox, QStackedWidget, QTabWidget,
                             QTextBrowser, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                             QWidget)

import lv_core
import lv_hub_lang
import lv_wire
from lv_hub_dev import BOARD_NAMES, DEFAULT_VREF, PINS, VREF, SimDevice
from lv_hub_lang import EN, LANGS, T
from lv_hub_ui import Led, Plot, eng, make_icon

APP = "CamiLab"
EXT_VI = ".cami"
EXT_PROJ = ".camp"
PROJ = "(proyecto)"
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ICON_DIR = os.path.join(REPO, "iconos")


def icon_file(name, ext):
    p = os.path.join(ICON_DIR, name + ext)
    return p if os.path.isfile(p) else None


def app_icon(project=False):
    name = "camp" if project else "camilab"
    for ext in (".png", ".ico"):
        p = icon_file(name, ext)
        if p:
            return QIcon(p)
    return QIcon(make_icon("bode" if project else "scope", 64))


THEME_KEYS = [
    ("bg", "Fondo de la ventana"),
    ("surface", "Superficie (secciones, casillas, paletas)"),
    ("text", "Texto principal"),
    ("text2", "Texto secundario (ayudas, etiquetas)"),
    ("accent", "Acento (selección, botones activos, bloques de E/S)"),
    ("screen", "Pantallas (fondo de displays, plots y monitor)"),
    ("signal", "Señal (trazas, dígitos, LED encendido)"),
    ("alert", "Alerta (Stop, errores, alarmas)"),
]
THEMES = {
    "light": {"bg": "#d4d4d4", "surface": "#e4e4e4", "text": "#1a1a1a", "text2": "#4a4a4a",
              "accent": "#2f4f7f", "screen": "#0a0a0a", "signal": "#00ff40", "alert": "#b01010"},
    "dark": {"bg": "#202124", "surface": "#2d2f33", "text": "#e8e8e8", "text2": "#a0a4aa",
             "accent": "#4f8fe0", "screen": "#000000", "signal": "#00ff40", "alert": "#e04848"},
}
THEME_NAMES = [("light", "Claro"), ("dark", "Oscuro"), ("custom", "Personalizado")]
TH = {}


def cfg_read():
    try:
        with open(lv_hub_lang._CFG, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def cfg_write(**kw):
    d = cfg_read()
    d.update(kw)
    try:
        with open(lv_hub_lang._CFG, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1)
    except OSError:
        pass


def theme_base(name):
    if name == "custom":
        base = dict(THEMES["light"])
        base.update({k: v for k, v in cfg_read().get("custom_theme", {}).items() if k in base})
        return base
    return dict(THEMES.get(name, THEMES["light"]))


def resolve_theme(name):
    b = theme_base(name)
    c = {k: QColor(v) for k, v in b.items()}
    dark = c["bg"].lightness() < 128
    t = dict(c)
    t["name"] = name
    t["dark"] = dark
    t["hi"] = c["surface"].lighter(135 if dark else 125)
    t["lo"] = c["surface"].darker(150 if dark else 165)
    t["input"] = c["bg"].darker(140) if dark else QColor("#ffffff")
    t["button"] = c["surface"].lighter(115) if dark else c["surface"].darker(104)
    t["canvas"] = c["bg"].darker(125) if dark else QColor("#ffffff")
    t["func"] = QColor("#4a4320") if dark else QColor("#fff2a8")
    t["func_line"] = QColor("#c8a830") if dark else QColor("#9a7a00")
    t["func_text"] = QColor("#ffe9a0") if dark else QColor("#3a2a00")
    t["io_body"] = c["surface"].lighter(112) if dark else QColor("#eef2f8")
    t["grid"] = c["signal"].darker(450)
    t["grid2"] = c["signal"].darker(260)
    t["ok"] = c["signal"].darker(150) if not dark else c["signal"]
    return t


def tcol(c):
    return c.lighter(140) if TH.get("dark") else c.darker(140)


def hexc(k):
    return TH[k].name()


def theme_qss():
    return """
QWidget            { color:%(text)s; font-size:12px;
                     font-family:"Tahoma","Segoe UI","DejaVu Sans",sans-serif; }
QMainWindow, QWidget#panel, QDialog { background:%(bg)s; }
QDockWidget        { color:%(text)s; }
QDockWidget::title { background:%(surface)s; padding:3px; }
QMenuBar, QMenu, QToolBar, QStatusBar { background:%(surface)s; color:%(text)s; }
QMenu::item:selected, QMenuBar::item:selected { background:%(accent)s; color:#ffffff; }
QToolButton        { color:%(text)s; padding:3px 6px; }
QToolButton:hover  { background:%(button)s; }
QTabWidget::pane   { border:1px solid %(lo)s; background:%(bg)s; }
QTabBar::tab       { background:%(surface)s; color:%(text)s; padding:5px 12px;
                     border:1px solid %(lo)s; border-bottom:none; }
QTabBar::tab:selected { background:%(bg)s; border-top:2px solid %(accent)s; }
QTreeWidget, QListWidget, QTextBrowser, QPlainTextEdit {
                     background:%(input)s; color:%(text)s; border:1px solid %(lo)s;
                     selection-background-color:%(accent)s; selection-color:#ffffff; }
QPlainTextEdit#monitor { background:%(screen)s; color:%(signal)s; }
QLabel#status      { color:%(text2)s; padding:2px 4px; }
QLabel#hint        { color:%(text2)s; font-size:11px; }
QGroupBox          { background:%(surface)s; border:2px solid;
                     border-color:%(hi)s %(lo)s %(lo)s %(hi)s;
                     margin-top:18px; padding:8px 6px 6px 6px; }
QGroupBox::title   { subcontrol-origin:margin; subcontrol-position:top left;
                     left:4px; padding:0 2px; color:%(text)s; font-weight:bold; }
QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit {
                     background:%(input)s; color:%(text)s; border:2px solid;
                     border-color:%(lo)s %(hi)s %(hi)s %(lo)s; padding:2px 4px; min-height:18px; }
QComboBox QAbstractItemView { background:%(input)s; color:%(text)s;
                     selection-background-color:%(accent)s; selection-color:#ffffff; }
QPushButton        { background:%(button)s; color:%(text)s; border:2px solid;
                     border-color:%(hi)s %(lo)s %(lo)s %(hi)s; padding:4px 12px; }
QPushButton:hover  { background:%(surface)s; }
QPushButton:pressed, QPushButton:checked {
                     background:%(accent)s; color:#ffffff;
                     border-color:%(lo)s %(hi)s %(hi)s %(lo)s; }
QPushButton#stopbtn { background:%(alert)s; color:#ffffff; font-weight:bold; font-size:14px; }
QPushButton#stopbtn:checked { background:%(lo)s; }
QCheckBox          { color:%(text)s; }
QLabel#lcd         { background:%(screen)s; color:%(signal)s; border:3px solid;
                     border-color:%(lo)s %(hi)s %(hi)s %(lo)s;
                     font-family:"Consolas","DejaVu Sans Mono","Courier New",monospace;
                     font-size:40px; font-weight:bold; padding:4px 10px; }
QLabel#readout     { background:%(screen)s; color:%(signal)s; border:2px solid;
                     border-color:%(lo)s %(hi)s %(hi)s %(lo)s;
                     font-family:"Consolas","DejaVu Sans Mono","Courier New",monospace;
                     font-size:12px; padding:4px 8px; }
QFrame#pitem       { background:%(surface)s; border:2px solid;
                     border-color:%(hi)s %(lo)s %(lo)s %(hi)s; }
QLabel#phead       { font-weight:bold; color:%(text)s; }
QLabel#freetext    { background:transparent; color:%(text)s; }
QFrame#banner      { background:transparent; }
QLabel#btitle      { font-size:22px; font-weight:bold; color:%(text)s; }
QLabel#bfooter     { font-size:12px; color:%(text2)s; }
QLabel#running     { color:%(ok)s; font-weight:bold; }
QDial              { background:%(button)s; }
""" % {k: (v.name() if isinstance(v, QColor) else v) for k, v in TH.items()}


def theme_palette():
    from PyQt5.QtGui import QPalette
    p = QPalette()
    for role, key in ((QPalette.Window, "bg"), (QPalette.WindowText, "text"),
                      (QPalette.Base, "input"), (QPalette.AlternateBase, "surface"),
                      (QPalette.Text, "text"), (QPalette.Button, "button"),
                      (QPalette.ButtonText, "text"), (QPalette.Highlight, "accent"),
                      (QPalette.ToolTipBase, "surface"), (QPalette.ToolTipText, "text")):
        p.setColor(role, TH[key])
    p.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    return p


def style_plot(pl):
    pl.c_frame = QColor(TH["surface"])
    pl.c_screen = QColor(TH["screen"])
    pl.c_text = QColor(TH["text"])
    pl.c_grid = QColor(TH["grid"])
    pl.c_grid2 = QColor(TH["grid2"])


def set_theme(name):
    TH.clear()
    TH.update(resolve_theme(name))
    app = QApplication.instance()
    if app is not None:
        app.setPalette(theme_palette())
        app.setStyleSheet(theme_qss())


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


class FakeSerial(object):
    LEN = {0x01: 3, 0x02: 3, 0x03: 4, 0x04: 5, 0x05: 2, 0x06: 3, 0x07: 3, 0x08: 3,
           0x0A: 2, 0xEF: 1, 0xF0: 1, 0xC2: 1, 0xC3: 1, 0xC4: 1, 0xC6: 2}

    def __init__(self):
        self.sim = SimDevice()
        self.sim.open()
        self.buf = bytearray()
        self.out = bytearray()

    def reset_input_buffer(self):
        self.out = bytearray()

    def write(self, data):
        self.buf += data
        while self.buf:
            c = self.buf[0]
            if c == 0x09:
                if len(self.buf) < 5 or len(self.buf) < 5 + self.buf[4]:
                    return
                n = 5 + self.buf[4]
            else:
                n = self.LEN.get(c, 1)
                if len(self.buf) < n:
                    return
            frame = bytes(self.buf[:n])
            del self.buf[:n]
            self.out += self.reply(frame)
        return len(data)

    def reply(self, f):
        s = self.sim
        c = f[0]
        if c == 0x01:
            return b"AA" if s.do(f[1], f[2]) else b"XX"
        if c == 0x02:
            v = s.di(f[1])
            return b"XX" if v is None else (b"A1" if v else b"A0")
        if c == 0x05:
            v = s.ai_raw(f[1])
            return (b"%d\r\n" % v) if v is not None else b"-2\r\n"
        if c == 0x06:
            return b"AA" if s.ao_raw(f[1], f[2]) else b"XX"
        if c == 0x07:
            return b"AA" if s.pwm_raw(f[1], f[2]) else b"XX"
        if c == 0x08:
            time.sleep(0.001)
            return b"AA" if f[1] < 2 else b"XX"
        if c in (0x03, 0x04, 0x09, 0x0A, 0xF0):
            time.sleep(0.001)
            return b"AA"
        if c == 0xEF:
            return b"LV,ESP32,3.0.0,-,SIM,10,3,6,1,2,2,2\r\n"
        return b"XX"

    def read(self, n=1):
        if not self.out:
            time.sleep(0.0005)
            return b""
        r = bytes(self.out[:n])
        del self.out[:n]
        return r

    def close(self):
        pass


def f_open(ctx, node, inp):
    port = (node["params"].get("port") or PROJ).strip()
    if port == PROJ:
        port = ctx.project_port or "SIM"
    if port.upper() == "SIM":
        w = lv_wire.Wire(transport=FakeSerial(), timeout=0.5)
        ctx.note(T("Abrir puerto"), T("Simulador abierto (sin tarjeta)."))
    else:
        ctx.note(T("Abrir puerto"), T("Abriendo %s a 115200 baudios. La tarjeta se reinicia: "
                                      "se esperan 2 s antes del primer comando.") % port)
        try:
            w = lv_wire.Wire(port, timeout=1.0)
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
        raise ValueError(T("La tarjeta en %s no respondió a la identidad (0xEF).") % port)
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
    return {"ses": w, "counts": float(v), "volts": v * getattr(w, "vref", 3.3) / 4095.0}


def f_ao(ctx, node, inp):
    w = need_ses(inp["ses"])
    vref = getattr(w, "vref", 3.3)
    code = int(round(max(0.0, min(vref, num(inp["volts"]))) / vref * 255))
    r = w.cmd("ao", (int(num(inp["ch"])), code))
    ctx.log(T("Escribir analógico"), r)
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


SES = ("ses", "ses", None, "sesión")
CH = ("ch", "num", 0.0, "canal")
CAT_IO = "LV_ESP32"

spec("open", CAT_IO, "Abrir puerto", [], [("ses", "ses", "sesión"), ("board", "str", "placa")],
     f_open, [("port", "port", PROJ, "Puerto")], kind="io",
     doc="Abre el puerto serie de la tarjeta (como VISA Open) y pide su identidad (0xEF). "
         "Su salida 'sesión' se cablea a todos los bloques de E/S: ese cable marca el orden. "
         "Puerto SIM = tarjeta simulada; (proyecto) = el puerto que diga el proyecto .camp.")
spec("close", CAT_IO, "Cerrar puerto", [SES], [], f_close, kind="io",
     doc="Cierra el puerto (VISA Close). Ponlo al final, fuera del lazo.")
spec("do_write", CAT_IO, "Escribir digital", [SES, CH, ("val", "bool", False, "valor")],
     [("ses", "ses", "sesión")], f_do, kind="io",
     doc="Salida digital. Manda 0x01 [canal, valor] y espera 'A','A'.")
spec("di_read", CAT_IO, "Leer digital", [SES, CH],
     [("ses", "ses", "sesión"), ("val", "bool", "valor")], f_di, kind="io",
     doc="Entrada digital. Manda 0x02 [canal, 0] y recibe 'A','0' o 'A','1'.")
spec("ai_read", CAT_IO, "Leer analógico", [SES, CH],
     [("ses", "ses", "sesión"), ("counts", "num", "cuentas"), ("volts", "num", "voltaje")],
     f_ai, kind="io",
     doc="Entrada analógica. Manda 0x05 [canal] y recibe un número 0..4095 en texto "
         "terminado en salto de línea. voltaje = cuentas × Vref / 4095.")
spec("ao_write", CAT_IO, "Escribir analógico", [SES, CH, ("volts", "num", 0.0, "voltaje")],
     [("ses", "ses", "sesión")], f_ao, kind="io",
     doc="DAC. Convierte el voltaje a 0..255 y manda 0x06 [canal, código]. "
         "Solo ESP32 Wrover y Nucleo tienen DAC.")
spec("pwm_write", CAT_IO, "PWM", [SES, CH, ("duty", "num", 50.0, "duty %")],
     [("ses", "ses", "sesión")], f_pwm, kind="io",
     doc="PWM de 1 kHz. Convierte 0..100 % a 0..255 y manda 0x07 [canal, duty].")
spec("servo_write", CAT_IO, "Servo", [SES, CH, ("angle", "num", 90.0, "ángulo")],
     [("ses", "ses", "sesión")], f_servo, kind="io",
     doc="Servo de 50 Hz. Manda 0x08 [canal, ángulo 0..180].")
spec("neo_all", CAT_IO, "NeoPixel", [SES, ("r", "num", 0.0, "R"), ("g", "num", 0.0, "G"),
                                      ("b", "num", 0.0, "B")],
     [("ses", "ses", "sesión")], f_neo, kind="io",
     doc="Pinta toda la tira NeoPixel. Manda 0x03 [R, G, B].")
spec("lcd_write", CAT_IO, "LCD", [SES, ("row", "num", 0.0, "fila"), ("col", "num", 0.0, "columna"),
                                  ("text", "str", "", "texto")],
     [("ses", "ses", "sesión")], f_lcd, [("addr", "num", 39, "Dirección I2C")], kind="io",
     doc="Escribe texto en un LCD I2C de 16x2. Manda 0x09 [dir, col, fila, largo, texto...].")


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


spec("const_num", CAT_NUM, "Constante numérica", [], [("v", "num", "valor")],
     lambda c, n, i: {"v": num(n["params"].get("value", 0))},
     [("value", "num", 0.0, "Valor")], kind="const",
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
     doc="Repite lo de adentro hasta que la terminal Stop (abajo a la derecha) reciba "
         "verdadero. 'i' cuenta las iteraciones desde 0.")
spec("for", CAT_STRUCT, "For Loop", kind="struct",
     doc="Repite N veces. 'i' va de 0 a N−1. Los valores que salen del lazo se juntan en "
         "un arreglo (auto-indexado).")
spec("case", CAT_STRUCT, "Case (if)", kind="struct",
     doc="Ejecuta solo uno de sus dos casos según la terminal '?' (verdadero/falso). "
         "Usa clic derecho → 'Agregar salida' para sacar valores: cablea la salida en los "
         "dos casos.")

CAT_CTL = "Controles"
CAT_IND = "Indicadores"


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
]
IND_KINDS = [
    ("ind_num", "Pantalla numérica", "num"),
    ("ind_led", "LED", "bool"),
    ("ind_gauge", "Gauge", "num"),
    ("ind_bar", "Barra / termómetro", "num"),
    ("ind_chart", "Plot en el tiempo", "any"),
    ("ind_graph", "Gráfica de arreglo", "arr"),
    ("ind_str", "Pantalla de texto", "any"),
]
CTL_DOC = "Terminal de un control del panel frontal: entrega lo que el usuario pone ahí."
IND_DOC = "Terminal de un indicador del panel frontal: muestra el valor que le llega."
for _k, _l, _o in CTL_KINDS:
    spec(_k, None, _l, [], _o, f_ctl, kind="ctl", doc=CTL_DOC)
for _k, _l, _t in IND_KINDS:
    spec(_k, None, _l, [("v", _t, 0.0, "valor")], [], f_ind, kind="ind", doc=IND_DOC)

PANEL_ONLY = [("image", "Imagen"), ("text", "Texto libre")]


def struct_ports(node):
    t = node["type"]
    p = []
    nsr = int(node["params"].get("sr", 0))
    if t in ("while", "for"):
        if t == "for":
            p.append(("N", "in", "outer", "num", "N"))
        p.append(("i", "out", "inner", "num", "i"))
        if t == "while":
            p.append(("stop", "in", "inner", "bool", "stop"))
        for k in range(nsr):
            p.append(("sr%d_in" % k, "in", "outer", "any", T("valor inicial")))
            p.append(("sr%d_l" % k, "out", "inner", "any", T("valor anterior")))
            p.append(("sr%d_r" % k, "in", "inner", "any", T("valor siguiente")))
            p.append(("sr%d_out" % k, "out", "outer", "any", T("valor final")))
    elif t == "case":
        p.append(("sel", "in", "outer", "any", "?"))
        for k in range(int(node["params"].get("outs", 0))):
            p.append(("o%d_i" % k, "in", "inner", "any", T("salida %d") % k))
            p.append(("o%d" % k, "out", "outer", "any", T("salida %d") % k))
    return p


def ports(node):
    s = SPECS[node["type"]]
    if s.kind == "struct":
        return struct_ports(node)
    return ([(n, "in", "outer", t, lbl) for n, t, _d, lbl in s.ins] +
            [(n, "out", "outer", t, lbl) for n, t, lbl in s.outs])


def const_text(node):
    v = node["params"].get("value", 0)
    t = node["type"]
    if t == "const_bool":
        return "T" if v else "F"
    if t == "const_str":
        return '"%s"' % v
    return "%g" % float(v)


def node_size(node):
    s = SPECS[node["type"]]
    if s.kind == "struct":
        return node.get("w", 300), node.get("h", 200)
    nin, nout = len(s.ins), len(s.outs)
    if s.kind == "io":
        return 150, 24 + 16 * max(nin, nout, 1) + 6
    if s.kind == "const":
        return max(38, 8 * len(const_text(node)) + 14), 22
    if s.kind in ("ctl", "ind"):
        return 46, max(26, 14 * max(nin, nout) + 6)
    return max(36, 9 * len(s.sym or "") + 14), max(30, 14 * max(nin, nout) + 6)


def new_panel():
    return {"rows": 3, "cols": 4, "title": {"text": "", "image": None},
            "footer": {"on": False, "text": "", "image": None},
            "items": {}, "texts": []}


def new_doc():
    return {"camilab": 1, "nodes": {}, "wires": [], "next": 1, "panel": new_panel()}


def add_node(doc, tid, x, y, **params):
    nid = "n%d" % doc["next"]
    doc["next"] += 1
    s = SPECS[tid]
    p = {}
    for name, _k, default, _l in s.params:
        p[name] = default
    if s.kind == "ctl" or s.kind == "ind":
        p.setdefault("label", T(s.label))
        p.setdefault("units", "")
        if tid in ("ctl_num", "ctl_knob", "ctl_slider", "ind_gauge", "ind_bar"):
            p.setdefault("min", 0.0)
            p.setdefault("max", 10.0)
        if tid in ("ctl_num", "ctl_knob", "ctl_slider"):
            p.setdefault("value", 0.0)
        if tid == "ctl_ring":
            p.setdefault("options", T("Opción A") + ";" + T("Opción B") + ";" + T("Opción C"))
            p.setdefault("value", 0.0)
        if tid == "ctl_color":
            p.setdefault("value", [255, 0, 0])
        if tid in ("ctl_bool", "ctl_stop"):
            p.setdefault("value", False)
        if tid == "ctl_str":
            p.setdefault("value", "")
        if tid == "ind_chart":
            p.setdefault("hist", 200)
    if tid in ("while", "for"):
        p.setdefault("sr", 0)
    if tid == "case":
        p.setdefault("outs", 0)
        p.setdefault("view", 1)
    p.update(params)
    n = {"id": nid, "type": tid, "x": float(x), "y": float(y), "params": p, "frame": 0}
    if s.kind == "struct":
        n["w"], n["h"] = float(p.pop("w", 320)), float(p.pop("h", 200))
    doc["nodes"][nid] = n
    return nid


def add_wire(doc, a, ap, b, bp, frame=0):
    doc["wires"] = [w for w in doc["wires"] if not (w["dst"] == [b, bp] and
                                                    w.get("frame", 0) == frame)]
    w = {"src": [a, ap], "dst": [b, bp], "frame": frame}
    doc["wires"].append(w)
    return w


def remove_node(doc, nid):
    doc["nodes"].pop(nid, None)
    doc["wires"] = [w for w in doc["wires"] if w["src"][0] != nid and w["dst"][0] != nid]


def rect(node):
    w, h = node_size(node)
    return node["x"], node["y"], w, h


def compute_parents(doc):
    nodes = doc["nodes"]
    structs = [n for n in nodes.values() if SPECS[n["type"]].kind == "struct"]
    structs.sort(key=lambda n: n["w"] * n["h"])
    parent = {}
    for n in nodes.values():
        x, y, w, h = rect(n)
        cx, cy = x + w / 2.0, y + h / 2.0
        area = w * h
        parent[n["id"]] = None
        for s in structs:
            if s["id"] == n["id"] or s["w"] * s["h"] <= area:
                continue
            if s["x"] < cx < s["x"] + s["w"] and s["y"] < cy < s["y"] + s["h"]:
                parent[n["id"]] = s["id"]
                break
    return parent


class Abort(Exception):
    pass


class VIError(Exception):
    def __init__(self, msg, nid=None):
        Exception.__init__(self, msg)
        self.nid = nid


class Ctx(object):
    def __init__(self):
        self.stop_flag = threading.Event()
        self.sessions = []
        self.t0 = time.perf_counter()
        self.project_port = ""

    def check(self):
        if self.stop_flag.is_set():
            raise Abort()

    def sleep(self, s):
        end = time.perf_counter() + s
        while True:
            self.check()
            left = end - time.perf_counter()
            if left <= 0:
                return
            time.sleep(min(0.02, left))

    def log(self, title, result):
        pass

    def note(self, title, text):
        pass

    def ctl(self, nid):
        return 0.0

    def show(self, nid, value):
        pass

    def close_all(self):
        for w in list(self.sessions):
            try:
                w.close()
            except Exception:
                pass
        self.sessions = []


class Engine(object):
    def __init__(self, doc, ctx):
        self.doc = doc
        self.ctx = ctx
        self.nodes = doc["nodes"]
        self.wires = doc["wires"]
        self.parent = compute_parents(doc)
        self.kind = {nid: SPECS[n["type"]].kind for nid, n in self.nodes.items()}
        self.values = {}
        self.tunnel = {}
        self.order_cache = {}
        self.inw = {}
        for i, w in enumerate(self.wires):
            self.inw.setdefault(tuple(w["dst"]), []).append(i)
        self.children = {}
        for nid in self.nodes:
            p = self.parent[nid]
            f = self.nodes[nid].get("frame", 0) if p and self.nodes[p]["type"] == "case" else 0
            self.children.setdefault((p, f), []).append(nid)

    def is_desc(self, nid, sid):
        cur = self.parent.get(nid)
        while cur is not None:
            if cur == sid:
                return True
            cur = self.parent.get(cur)
        return False

    def member(self, nid, sid, f):
        cur = nid
        while cur is not None:
            p = self.parent[cur]
            if p == sid:
                if sid is not None and self.nodes[sid]["type"] == "case" and \
                        self.nodes[cur].get("frame", 0) != f:
                    return None
                return cur
            cur = p
        return None

    def order(self, sid, f):
        key = (sid, f)
        if key in self.order_cache:
            return self.order_cache[key]
        mem = list(self.children.get(key, []))
        deps = {m: set() for m in mem}
        for w in self.wires:
            a = self.member(w["src"][0], sid, f)
            b = self.member(w["dst"][0], sid, f)
            if a is not None and b is not None and a != b:
                deps[b].add(a)
        out = []
        ready = sorted([m for m in mem if not deps[m]],
                       key=lambda m: (self.nodes[m]["x"], self.nodes[m]["y"]))
        done = set()
        while ready:
            m = ready.pop(0)
            out.append(m)
            done.add(m)
            new = [k for k in mem if k not in done and k not in out and k not in ready
                   and deps[k] <= done]
            ready = sorted(ready + new, key=lambda k: (self.nodes[k]["x"], self.nodes[k]["y"]))
        if len(out) != len(mem):
            bad = [m for m in mem if m not in done][0]
            raise VIError(T("Hay un ciclo de cables (un valor depende de sí mismo). "
                            "Dentro de un lazo usa un shift register."), bad)
        self.order_cache[key] = out
        return out

    def read_wire(self, i):
        if i in self.tunnel:
            return self.tunnel[i]
        w = self.wires[i]
        return self.values.get(tuple(w["src"]))

    def read(self, nid, port, default, frame=None):
        ids = self.inw.get((nid, port), [])
        if frame is not None:
            ids = [i for i in ids if self.wires[i].get("frame", 0) == frame]
        if not ids:
            return self.nodes[nid]["params"].get("def_" + port, default)
        v = self.read_wire(ids[0])
        return default if v is None else v

    def wired(self, nid, port):
        return bool(self.inw.get((nid, port)))

    def run(self):
        try:
            self.scope(None, 0)
        finally:
            self.ctx.close_all()

    def scope(self, sid, f):
        for nid in self.order(sid, f):
            self.ctx.check()
            k = self.kind[nid]
            if k == "struct":
                t = self.nodes[nid]["type"]
                if t == "case":
                    self.case(nid)
                else:
                    self.loop(nid, t)
            else:
                self.exec_node(nid)

    def exec_node(self, nid):
        n = self.nodes[nid]
        s = SPECS[n["type"]]
        inp = {}
        for name, _t, default, _l in s.ins:
            inp[name] = self.read(nid, name, default)
        try:
            out = s.fn(self.ctx, n, inp) or {}
        except Abort:
            raise
        except VIError:
            raise
        except Exception as e:
            raise VIError("%s: %s" % (T(s.label), e), nid)
        for k, v in out.items():
            self.values[(nid, k)] = v

    def leaving(self, sid):
        out = []
        for i, w in enumerate(self.wires):
            a, b = w["src"][0], w["dst"][0]
            if self.is_desc(a, sid) and not self.is_desc(b, sid) and b != sid:
                out.append(i)
        return out

    def loop(self, sid, t):
        n = self.nodes[sid]
        nsr = int(n["params"].get("sr", 0))
        leave = self.leaving(sid)
        sr = [self.read(sid, "sr%d_in" % k, 0.0) for k in range(nsr)]
        count = None
        if t == "for":
            try:
                count = int(float(self.read(sid, "N", 0)))
            except (TypeError, ValueError):
                raise VIError(T("N del For Loop debe ser un número."), sid)
            acc = {i: [] for i in leave}
        it = 0
        while True:
            if count is not None and it >= count:
                break
            self.ctx.check()
            self.values[(sid, "i")] = float(it)
            for k in range(nsr):
                self.values[(sid, "sr%d_l" % k)] = sr[k]
            self.scope(sid, 0)
            for k in range(nsr):
                if self.wired(sid, "sr%d_r" % k):
                    sr[k] = self.read(sid, "sr%d_r" % k, sr[k])
            if count is not None:
                for i in leave:
                    acc[i].append(self.read_wire(i))
            it += 1
            if t == "while":
                if not self.wired(sid, "stop"):
                    raise VIError(T("El While Loop no tiene cableada su terminal Stop."), sid)
                if bool(self.read(sid, "stop", True)):
                    break
                if it % 50 == 0:
                    time.sleep(0)
        for k in range(nsr):
            self.values[(sid, "sr%d_out" % k)] = sr[k]
        for i in leave:
            self.tunnel[i] = acc[i] if count is not None else self.read_wire(i)

    def case(self, sid):
        n = self.nodes[sid]
        sel = self.read(sid, "sel", False)
        if isinstance(sel, (list, tuple)):
            raise VIError(T("El selector del Case no puede ser un arreglo."), sid)
        f = 1 if sel else 0
        self.scope(sid, f)
        for k in range(int(n["params"].get("outs", 0))):
            self.values[(sid, "o%d" % k)] = self.read(sid, "o%d_i" % k, 0.0, frame=f)
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


MIME = "application/x-camiblock"
TYPE_COL = {"num": QColor("#e07000"), "bool": QColor("#00862b"), "str": QColor("#d0189c"),
            "arr": QColor("#e07000"), "ses": QColor("#6a2fa0"), "any": QColor("#707070")}
TYPE_TAG = {"num": "DBL", "bool": "TF", "str": "abc", "arr": "[DBL]", "any": "VAR"}


def frame_name(f):
    return T("Verdadero") if f else T("Falso")


class PortItem(QGraphicsItem):
    def __init__(self, owner, nid, name, d, side, typ, label):
        QGraphicsItem.__init__(self, owner)
        self.owner = owner
        self.nid, self.name, self.dir, self.side, self.typ, self.label = \
            nid, name, d, side, typ, label
        self.hot = False
        self.setAcceptHoverEvents(True)
        self.setZValue(5)
        self.setToolTip("%s  (%s)" % (label, typ))

    def style(self):
        n = self.name
        if self.owner.kind != "struct":
            return "dot"
        if n in ("i", "N"):
            return "box"
        if n == "stop":
            return "stop"
        if n.startswith("sr"):
            return "sr"
        if n == "sel":
            return "sel"
        if n.startswith("o"):
            return "tun"
        return "dot"

    def boundingRect(self):
        s = self.style()
        if s in ("box", "stop", "sel"):
            return QRectF(-8, -8, 16, 16)
        if s in ("sr", "tun"):
            return QRectF(-6, -7, 12, 14)
        return QRectF(-5, -5, 10, 10)

    def paint(self, p, _o, _w):
        p.setRenderHint(QPainter.Antialiasing)
        s = self.style()
        col = TYPE_COL.get(self.typ, TYPE_COL["any"])
        if s == "box":
            p.setBrush(TH["input"])
            p.setPen(QPen(TH["accent"], 1.5))
            p.drawRect(QRectF(-7, -7, 14, 14))
            f = QFont()
            f.setPixelSize(10)
            f.setBold(True)
            p.setFont(f)
            p.setPen(TH["accent"])
            p.drawText(QRectF(-7, -7, 14, 14), Qt.AlignCenter, self.name)
        elif s == "stop":
            p.setBrush(TH["alert"])
            p.setPen(QPen(TH["alert"].darker(200), 1))
            p.drawEllipse(QRectF(-7, -7, 14, 14))
            p.setBrush(QColor("#ffffff"))
            p.setPen(Qt.NoPen)
            p.drawRect(QRectF(-3, -3, 6, 6))
        elif s == "sel":
            p.setBrush(TH["input"])
            p.setPen(QPen(TYPE_COL["bool"], 1.5))
            p.drawRect(QRectF(-7, -7, 14, 14))
            p.setPen(tcol(TYPE_COL["bool"]))
            p.drawText(QRectF(-7, -7, 14, 14), Qt.AlignCenter, "?")
        elif s in ("sr", "tun"):
            p.setBrush(TH["input"])
            p.setPen(QPen(QColor("#d07000") if s == "sr" else TH["text2"], 1.2))
            p.drawRect(QRectF(-5, -6, 10, 12))
            if s == "sr":
                up = self.name.endswith("_r") or self.name.endswith("_out")
                tri = [QPointF(-3, 2), QPointF(3, 2), QPointF(0, -3)] if up else \
                    [QPointF(-3, -2), QPointF(3, -2), QPointF(0, 3)]
                p.setBrush(QColor("#b06000"))
                p.drawPolygon(QPolygonF(tri))
        else:
            p.setBrush(col if self.hot else TH["input"])
            p.setPen(QPen(col, 1.4))
            p.drawEllipse(QRectF(-4, -4, 8, 8))
        if self.hot:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(TH["accent"], 1.5))
            p.drawRect(self.boundingRect().adjusted(0.5, 0.5, -0.5, -0.5))

    def hoverEnterEvent(self, e):
        self.hot = True
        self.update()
        ed = self.owner.ed
        ed.help.emit("%s — %s  (%s)" % (T(SPECS[ed.doc["nodes"][self.nid]["type"]].label),
                                       self.label, self.typ))

    def hoverLeaveEvent(self, e):
        self.hot = False
        self.update()


def node_port_pos(node, name, d="in"):
    s = SPECS[node["type"]]
    w, h = node_size(node)
    if s.kind == "struct":
        return struct_port_pos(node, name)
    ins = [p[0] for p in s.ins]
    outs = [p[0] for p in s.outs]
    if s.kind == "io":
        if d == "in":
            return QPointF(0, 30 + 16 * ins.index(name))
        return QPointF(w, 30 + 16 * outs.index(name))
    if d == "in":
        return QPointF(0, h * (ins.index(name) + 1) / (len(ins) + 1))
    return QPointF(w, h * (outs.index(name) + 1) / (len(outs) + 1))


def struct_port_pos(node, name):
    w, h = node["w"], node["h"]
    if name == "i":
        return QPointF(16, h - 18)
    if name == "stop":
        return QPointF(w - 18, h - 18)
    if name == "N":
        return QPointF(-4, 18)
    if name == "sel":
        return QPointF(0, h / 2)
    if name.startswith("sr"):
        k = int(name[2:].split("_")[0])
        y = 46 + 28 * k
        suf = name.split("_")[1]
        return {"in": QPointF(-5, y), "l": QPointF(5, y),
                "r": QPointF(w - 5, y), "out": QPointF(w + 5, y)}[suf]
    if name.startswith("o"):
        k = int(name[1:].split("_")[0])
        y = 44 + 26 * k
        return QPointF(w - 5, y) if name.endswith("_i") else QPointF(w + 5, y)
    return QPointF(0, 0)


class BaseItem(QGraphicsObject):
    def __init__(self, ed, nid):
        QGraphicsObject.__init__(self)
        self.ed = ed
        self.nid = nid
        self.kind = SPECS[self.node["type"]].kind
        self.error = False
        self.port_items = {}
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable |
                      QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setPos(self.node["x"], self.node["y"])
        self.make_ports()

    @property
    def node(self):
        return self.ed.doc["nodes"][self.nid]

    def make_ports(self):
        for it in self.port_items.values():
            it.setParentItem(None)
            if it.scene():
                it.scene().removeItem(it)
        self.port_items = {}
        for name, d, side, typ, label in ports(self.node):
            it = PortItem(self, self.nid, name, d, side, typ, T(label))
            it.setPos(node_port_pos(self.node, name, d))
            self.port_items[(d, name)] = it

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.node["x"] = self.pos().x()
            self.node["y"] = self.pos().y()
            self.ed.moved(self)
        return QGraphicsObject.itemChange(self, change, value)

    def hoverEnterEvent(self, e):
        s = SPECS[self.node["type"]]
        self.ed.help.emit("%s — %s" % (T(s.label), T(s.doc)))

    def mouseDoubleClickEvent(self, e):
        self.ed.edit_node(self.nid)

    def contextMenuEvent(self, e):
        self.ed.node_menu(self.nid, e.screenPos())

    def mouseReleaseEvent(self, e):
        QGraphicsObject.mouseReleaseEvent(self, e)
        self.ed.after_move()


class NodeItem(BaseItem):
    def boundingRect(self):
        w, h = node_size(self.node)
        if self.kind in ("ctl", "ind"):
            lw = QFontMetrics(QFont()).width(self.node["params"].get("label", "")) + 6
            ww = max(w, lw)
            return QRectF((w - ww) / 2 - 2, -3, ww + 4, h + 22)
        return QRectF(-3, -3, w + 6, h + 6)

    def paint(self, p, _o, _w):
        p.setRenderHint(QPainter.Antialiasing)
        n = self.node
        s = SPECS[n["type"]]
        w, h = node_size(n)
        sel = self.isSelected()
        R = QRectF(0, 0, w, h)
        f = QFont()
        if self.kind == "io":
            p.setBrush(TH["io_body"])
            p.setPen(QPen(TH["accent"], 1.5))
            p.drawRect(R)
            p.fillRect(QRectF(0, 0, w, 18), TH["accent"])
            f.setPixelSize(11)
            f.setBold(True)
            p.setFont(f)
            p.setPen(QColor("#ffffff"))
            p.drawText(QRectF(4, 0, w - 8, 18), Qt.AlignVCenter | Qt.AlignLeft,
                       "LV  " + T(s.label))
            f.setBold(False)
            f.setPixelSize(10)
            p.setFont(f)
            p.setPen(TH["text"])
            for k, (nm, t, _d, lbl) in enumerate(s.ins):
                p.drawText(QRectF(8, 22 + 16 * k, w / 2, 16), Qt.AlignVCenter | Qt.AlignLeft,
                           T(lbl))
            for k, (nm, t, lbl) in enumerate(s.outs):
                p.drawText(QRectF(w / 2 - 8, 22 + 16 * k, w / 2, 16),
                           Qt.AlignVCenter | Qt.AlignRight, T(lbl))
            if n["type"] == "open":
                p.setPen(TH["text2"])
                p.drawText(QRectF(8, h - 18, w - 16, 16), Qt.AlignVCenter | Qt.AlignLeft,
                           n["params"].get("port", "SIM"))
        elif self.kind == "const":
            t = s.outs[0][1]
            p.setBrush(TH["input"])
            p.setPen(QPen(TYPE_COL[t], 1.5))
            p.drawRect(R)
            f.setPixelSize(11)
            p.setFont(f)
            p.setPen(tcol(TYPE_COL[t]))
            p.drawText(R, Qt.AlignCenter, const_text(n))
        elif self.kind in ("ctl", "ind"):
            t = (s.outs or s.ins)[0][1]
            col = TYPE_COL[t]
            p.setBrush(TH["input"])
            p.setPen(QPen(col, 3.0 if self.kind == "ctl" else 1.4))
            p.drawRect(R.adjusted(1, 1, -1, -1))
            f.setPixelSize(10)
            f.setBold(True)
            p.setFont(f)
            p.setPen(tcol(col))
            p.drawText(QRectF(0, 0, w - 8, h), Qt.AlignCenter, TYPE_TAG[t])
            p.setBrush(col)
            p.setPen(Qt.NoPen)
            if self.kind == "ctl":
                tri = [QPointF(w - 9, h / 2 - 4), QPointF(w - 3, h / 2), QPointF(w - 9, h / 2 + 4)]
            else:
                tri = [QPointF(3, h / 2 - 4), QPointF(9, h / 2), QPointF(3, h / 2 + 4)]
            p.drawPolygon(QPolygonF(tri))
            f.setBold(False)
            f.setPixelSize(11)
            p.setFont(f)
            p.setPen(TH["text"])
            p.drawText(QRectF(-60, h + 1, w + 120, 16), Qt.AlignHCenter | Qt.AlignTop,
                       n["params"].get("label", ""))
        else:
            p.setBrush(TH["func"])
            p.setPen(QPen(TH["func_line"], 1.4))
            p.drawRect(R)
            f.setPixelSize(13 if len(s.sym or "") <= 2 else 10)
            f.setBold(True)
            p.setFont(f)
            p.setPen(TH["func_text"])
            p.drawText(R, Qt.AlignCenter, s.sym or "?")
        if sel or self.error:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(TH["alert"] if self.error else TH["accent"], 2, Qt.DashLine))
            p.drawRect(R.adjusted(-2, -2, 2, 2))


class StructItem(BaseItem):
    B = 8

    def __init__(self, ed, nid):
        self.resizing = False
        self.members = []
        BaseItem.__init__(self, ed, nid)
        self.setZValue(-10)

    def hdr(self):
        w = self.node["w"]
        return QRectF(w / 2 - 75, -10, 150, 20)

    def boundingRect(self):
        return QRectF(-12, -14, self.node["w"] + 24, self.node["h"] + 26)

    def shape(self):
        w, h, b = self.node["w"], self.node["h"], self.B
        path = QPainterPath()
        path.setFillRule(Qt.OddEvenFill)
        path.addRect(QRectF(-2, -2, w + 4, h + 4))
        path.addRect(QRectF(b, b, w - 2 * b, h - 2 * b))
        p2 = QPainterPath()
        p2.addRect(QRectF(w - 16, h - 16, 18, 18))
        if self.node["type"] == "case":
            p2.addRect(self.hdr())
        return path.united(p2)

    def paint(self, p, _o, _w):
        p.setRenderHint(QPainter.Antialiasing)
        n = self.node
        w, h, b = n["w"], n["h"], self.B
        case = n["type"] == "case"
        col = QColor("#5a5a5a") if case else QColor("#8c8c8c")
        p.setPen(Qt.NoPen)
        p.setBrush(col)
        path = QPainterPath()
        path.setFillRule(Qt.OddEvenFill)
        path.addRect(QRectF(0, 0, w, h))
        path.addRect(QRectF(b, b, w - 2 * b, h - 2 * b))
        p.drawPath(path)
        p.setPen(QPen(col.lighter(150), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(QRectF(b, b, w - 2 * b, h - 2 * b))
        if n["type"] == "while" or n["type"] == "for":
            f = QFont()
            f.setPixelSize(10)
            f.setBold(True)
            p.setFont(f)
            p.setPen(QColor("#ffffff"))
            p.drawText(QRectF(14, -1, 120, 10), Qt.AlignLeft | Qt.AlignVCenter,
                       "While Loop" if n["type"] == "while" else "For Loop")
        if case:
            r = self.hdr()
            p.setBrush(TH["input"])
            p.setPen(QPen(TH["text2"], 1.2))
            p.drawRect(r)
            f = QFont()
            f.setPixelSize(12)
            f.setBold(True)
            p.setFont(f)
            p.setPen(tcol(TYPE_COL["bool"]) if n["params"].get("view", 1) else TH["alert"])
            p.drawText(r, Qt.AlignCenter, "◀  %s  ▶" % frame_name(n["params"].get("view", 1)))
        p.setPen(QPen(QColor("#ffffff"), 1.2))
        for k in range(3):
            d = 4 + 4 * k
            p.drawLine(QPointF(w - d, h - 2), QPointF(w - 2, h - d))
        if self.isSelected() or self.error:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(TH["alert"] if self.error else TH["accent"], 2, Qt.DashLine))
            p.drawRect(QRectF(-3, -3, w + 6, h + 6))

    def mousePressEvent(self, e):
        n = self.node
        w, h = n["w"], n["h"]
        pos = e.pos()
        if n["type"] == "case" and self.hdr().contains(pos) and not self.ed.locked:
            n["params"]["view"] = 0 if n["params"].get("view", 1) else 1
            self.update()
            self.ed.refresh_visibility()
            self.ed.changed.emit()
            e.accept()
            return
        if pos.x() > w - 16 and pos.y() > h - 16 and not self.ed.locked:
            self.resizing = True
            self.r0 = (e.scenePos(), w, h)
            e.accept()
            return
        self.members = self.ed.descendants(self.nid)
        self.last = self.pos()
        BaseItem.mousePressEvent(self, e)

    def mouseMoveEvent(self, e):
        if self.resizing:
            p0, w0, h0 = self.r0
            d = e.scenePos() - p0
            self.prepareGeometryChange()
            self.node["w"] = max(140.0, w0 + d.x())
            self.node["h"] = max(100.0, h0 + d.y())
            for it in self.port_items.values():
                it.setPos(struct_port_pos(self.node, it.name))
            self.ed.moved(self)
            self.update()
            return
        BaseItem.mouseMoveEvent(self, e)

    def mouseReleaseEvent(self, e):
        self.resizing = False
        self.members = []
        BaseItem.mouseReleaseEvent(self, e)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged and self.members:
            d = self.pos() - self.last
            self.last = self.pos()
            for it in self.members:
                if not it.isSelected():
                    it.moveBy(d.x(), d.y())
        return BaseItem.itemChange(self, change, value)


class WireItem(QGraphicsPathItem):
    def __init__(self, ed, w):
        QGraphicsPathItem.__init__(self)
        self.ed = ed
        self.w = w
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setZValue(3)
        self.update_path()

    def update_path(self):
        ed = self.ed
        a = ed.items.get(self.w["src"][0])
        b = ed.items.get(self.w["dst"][0])
        if not a or not b:
            return
        pa = a.port_items.get(("out", self.w["src"][1]))
        pb = b.port_items.get(("in", self.w["dst"][1]))
        if not pa or not pb:
            return
        p1, p2 = pa.scenePos(), pb.scenePos()
        dx = max(30.0, abs(p2.x() - p1.x()) / 2)
        path = QPainterPath(p1)
        path.cubicTo(QPointF(p1.x() + dx, p1.y()), QPointF(p2.x() - dx, p2.y()), p2)
        self.setPath(path)
        t = ed.wire_type(self.w)
        width = 3.2 if t == "arr" else (2.6 if t == "ses" else 1.8)
        self.setPen(QPen(TYPE_COL.get(t, TYPE_COL["any"]), width,
                         Qt.DashLine if self.isSelected() else Qt.SolidLine,
                         Qt.RoundCap))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self.update_path()
        return QGraphicsPathItem.itemChange(self, change, value)

    def shape(self):
        s = QPainterPathStroker()
        s.setWidth(8)
        return s.createStroke(self.path())

    def contextMenuEvent(self, e):
        if self.ed.locked:
            return
        m = QMenu()
        a = m.addAction(T("Eliminar cable"))
        if m.exec_(e.screenPos()) == a:
            self.ed.remove_wire(self.w)


class Scene(QGraphicsScene):
    def __init__(self, ed):
        QGraphicsScene.__init__(self)
        self.ed = ed
        self.drag = None
        self.tmp = None
        self.setBackgroundBrush(TH["canvas"])

    def port_at(self, pos):
        for it in self.items(pos):
            if isinstance(it, PortItem) and it.isVisible():
                return it
        return None

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self.ed.locked:
            p = self.port_at(e.scenePos())
            if p is not None:
                self.drag = p
                self.tmp = QGraphicsPathItem()
                self.tmp.setPen(QPen(TH["accent"], 1.5, Qt.DashLine))
                self.tmp.setZValue(50)
                self.addItem(self.tmp)
                e.accept()
                return
        QGraphicsScene.mousePressEvent(self, e)

    def mouseMoveEvent(self, e):
        if self.drag is not None:
            p1 = self.drag.scenePos()
            p2 = e.scenePos()
            path = QPainterPath(p1)
            path.lineTo(p2)
            self.tmp.setPath(path)
            return
        QGraphicsScene.mouseMoveEvent(self, e)

    def mouseReleaseEvent(self, e):
        if self.drag is not None:
            a = self.drag
            b = self.port_at(e.scenePos())
            self.removeItem(self.tmp)
            self.tmp = None
            self.drag = None
            if b is not None and b is not a:
                self.ed.connect_ports(a, b)
            return
        QGraphicsScene.mouseReleaseEvent(self, e)

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(MIME) and not self.ed.locked:
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(MIME):
            e.acceptProposedAction()

    def dropEvent(self, e):
        tid = bytes(e.mimeData().data(MIME)).decode()
        self.ed.add_block(tid, e.scenePos())
        e.acceptProposedAction()


class View(QGraphicsView):
    def __init__(self, scene, ed):
        QGraphicsView.__init__(self, scene)
        self.ed = ed
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setAcceptDrops(True)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    def mousePressEvent(self, e):
        if e.button() == Qt.MiddleButton:
            self.pan = e.pos()
            self.viewport().setCursor(Qt.ClosedHandCursor)
            e.accept()
            return
        QGraphicsView.mousePressEvent(self, e)

    def mouseMoveEvent(self, e):
        if getattr(self, "pan", None) is not None:
            d = e.pos() - self.pan
            self.pan = e.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - d.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - d.y())
            e.accept()
            return
        QGraphicsView.mouseMoveEvent(self, e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MiddleButton and getattr(self, "pan", None) is not None:
            self.pan = None
            self.viewport().unsetCursor()
            e.accept()
            return
        QGraphicsView.mouseReleaseEvent(self, e)

    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier:
            f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
            self.scale(f, f)
            return
        QGraphicsView.wheelEvent(self, e)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Delete, Qt.Key_Backspace) and not self.ed.locked:
            self.ed.delete_selected()
            return
        QGraphicsView.keyPressEvent(self, e)


class Palette(QTreeWidget):
    add = pyqtSignal(str)
    hover = pyqtSignal(str)

    def __init__(self):
        QTreeWidget.__init__(self)
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setMouseTracking(True)
        for cat in CATS:
            top = QTreeWidgetItem([T(cat)])
            top.setFlags(Qt.ItemIsEnabled)
            f = top.font(0)
            f.setBold(True)
            top.setFont(0, f)
            self.addTopLevelItem(top)
            for s in SPECS.values():
                if s.cat == cat:
                    it = QTreeWidgetItem([("%s   %s" % (s.sym, T(s.label))) if s.sym and
                                          s.kind == "func" else T(s.label)])
                    it.setData(0, Qt.UserRole, s.tid)
                    it.setToolTip(0, T(s.doc))
                    top.addChild(it)
            top.setExpanded(cat in ("LV_ESP32", "Estructuras", "Numérico"))
        self.itemDoubleClicked.connect(self._dbl)
        self.itemEntered.connect(self._hover)

    def _dbl(self, it, _c):
        tid = it.data(0, Qt.UserRole)
        if tid:
            self.add.emit(tid)

    def _hover(self, it, _c):
        tid = it.data(0, Qt.UserRole)
        if tid:
            s = SPECS[tid]
            self.hover.emit("%s — %s" % (T(s.label), T(s.doc)))

    def startDrag(self, actions):
        it = self.currentItem()
        tid = it.data(0, Qt.UserRole) if it else None
        if not tid:
            return
        md = QMimeData()
        md.setData(MIME, tid.encode())
        d = QDrag(self)
        d.setMimeData(md)
        d.exec_(Qt.CopyAction)


def port_list():
    out = [(PROJ, T("(proyecto) — el del archivo .camp")), ("SIM", T("SIM (tarjeta simulada)"))]
    for p in lv_core.list_ports():
        out.append((p["port"], p["port"] + ("  —  " + p["label"] if p["label"] else "")))
    return out


class PropDialog(QDialog):
    def __init__(self, ed, nid, parent=None):
        QDialog.__init__(self, parent)
        self.ed = ed
        self.nid = nid
        n = ed.doc["nodes"][nid]
        s = SPECS[n["type"]]
        self.setWindowTitle(T("Propiedades") + " — " + T(s.label))
        f = QFormLayout(self)
        self.get = {}
        p = n["params"]
        if s.kind in ("ctl", "ind"):
            panel_fields(self, f, n)
        for name, kind, default, label in s.params:
            v = p.get(name, default)
            if kind == "num":
                self.num(f, name, T(label), v)
            elif kind == "bool":
                c = QCheckBox()
                c.setChecked(bool(v))
                f.addRow(T(label), c)
                self.get[name] = c.isChecked
            elif kind == "port":
                c = QComboBox()
                c.setEditable(True)
                for k, t in port_list():
                    c.addItem(t, k)
                i = c.findData(v)
                if i >= 0:
                    c.setCurrentIndex(i)
                else:
                    c.setEditText(v)
                f.addRow(T(label), c)
                self.get[name] = lambda c=c: (c.currentData() if c.currentText() ==
                                              c.itemText(c.currentIndex()) else
                                              c.currentText().strip())
            else:
                e = QLineEdit(str(v))
                f.addRow(T(label), e)
                self.get[name] = e.text
        if s.kind == "struct":
            if n["type"] in ("while", "for"):
                sp = QSpinBox()
                sp.setRange(0, 4)
                sp.setValue(int(p.get("sr", 0)))
                f.addRow(T("Shift registers"), sp)
                self.get["sr"] = sp.value
            else:
                sp = QSpinBox()
                sp.setRange(0, 6)
                sp.setValue(int(p.get("outs", 0)))
                f.addRow(T("Terminales de salida"), sp)
                self.get["outs"] = sp.value
        for name, typ, default, label in s.ins:
            if ed.is_wired(nid, name) or typ not in ("num", "bool", "str"):
                continue
            v = p.get("def_" + name, default)
            if typ == "num":
                self.num(f, "def_" + name, T("Si no se cablea: ") + T(label), v)
            elif typ == "bool":
                c = QCheckBox()
                c.setChecked(bool(v))
                f.addRow(T("Si no se cablea: ") + T(label), c)
                self.get["def_" + name] = c.isChecked
            else:
                e = QLineEdit(str(v))
                f.addRow(T("Si no se cablea: ") + T(label), e)
                self.get["def_" + name] = e.text
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)

    def num(self, f, key, label, v, dec=4):
        sp = QDoubleSpinBox()
        sp.setRange(-1e9, 1e9)
        sp.setDecimals(dec)
        sp.setValue(float(v))
        f.addRow(label, sp)
        self.get[key] = sp.value

    def values(self):
        return {k: g() for k, g in self.get.items()}


def panel_fields(dlg, f, n):
    p = n["params"]
    t = n["type"]
    e = QLineEdit(p.get("label", ""))
    f.addRow(T("Etiqueta"), e)
    dlg.get["label"] = e.text
    if t not in ("ctl_bool", "ctl_stop", "ind_led", "ctl_color", "ctl_ring", "ctl_str",
                 "ind_str", "ind_graph"):
        u = QLineEdit(p.get("units", ""))
        f.addRow(T("Unidades"), u)
        dlg.get["units"] = u.text
    if t in ("ctl_num", "ctl_knob", "ctl_slider", "ind_gauge", "ind_bar"):
        dlg.num(f, "min", T("Mínimo"), p.get("min", 0.0))
        dlg.num(f, "max", T("Máximo"), p.get("max", 10.0))
    if t in ("ctl_num", "ctl_knob", "ctl_slider"):
        dlg.num(f, "value", T("Valor inicial"), p.get("value", 0.0))
    if t == "ctl_ring":
        e2 = QLineEdit(p.get("options", ""))
        f.addRow(T("Opciones (separadas por ;)"), e2)
        dlg.get["options"] = e2.text
    if t in ("ctl_bool",):
        c = QCheckBox()
        c.setChecked(bool(p.get("value", False)))
        f.addRow(T("Valor inicial"), c)
        dlg.get["value"] = c.isChecked
    if t == "ind_chart":
        dlg.num(f, "hist", T("Puntos visibles"), p.get("hist", 200), 0)
    if t in ("ind_num", "ind_gauge", "ind_bar"):
        dlg.num(f, "dec", T("Decimales"), p.get("dec", 3), 0)


class Diagram(QObject):
    changed = pyqtSignal()
    help = pyqtSignal(str)
    status = pyqtSignal(str)
    panel_add = pyqtSignal(str)
    panel_remove = pyqtSignal(str)
    panel_update = pyqtSignal(str)

    def __init__(self, doc):
        QObject.__init__(self)
        self.doc = doc
        self.locked = False
        self.scene = Scene(self)
        self.view = View(self.scene, self)
        self.items = {}
        self.wire_items = []
        self.parent = {}
        self.rebuild()

    def rebuild(self):
        self.scene.clear()
        self.items = {}
        self.wire_items = []
        self.parent = {}
        for nid, n in self.doc["nodes"].items():
            self.make_item(nid)
        for w in self.doc["wires"]:
            self.make_wire(w)
        self.after_move(emit=False)

    def make_item(self, nid):
        k = SPECS[self.doc["nodes"][nid]["type"]].kind
        it = StructItem(self, nid) if k == "struct" else NodeItem(self, nid)
        self.scene.addItem(it)
        self.items[nid] = it
        return it

    def make_wire(self, w):
        it = WireItem(self, w)
        self.scene.addItem(it)
        self.wire_items.append(it)
        return it

    def is_wired(self, nid, port):
        return any(w["dst"] == [nid, port] for w in self.doc["wires"])

    def port_type(self, nid, port, want=None):
        for name, d, side, typ, label in ports(self.doc["nodes"][nid]):
            if name == port and (want is None or d == want):
                return typ
        return "any"

    def loops_between(self, a, b):
        par = self.parent
        k = 0
        cur = par.get(a)
        while cur is not None:
            if self.doc["nodes"][cur]["type"] == "for" and not self.is_desc(b, cur) and b != cur:
                k += 1
            cur = par.get(cur)
        return k

    def is_desc(self, nid, sid):
        cur = self.parent.get(nid)
        while cur is not None:
            if cur == sid:
                return True
            cur = self.parent.get(cur)
        return False

    def wire_type(self, w):
        t = self.port_type(w["src"][0], w["src"][1], "out")
        if t == "any":
            t2 = self.port_type(w["dst"][0], w["dst"][1], "in")
            t = t2 if t2 != "any" else "any"
        if self.loops_between(w["src"][0], w["dst"][0]):
            return "arr"
        return t

    def moved(self, item):
        nid = item.nid
        for wi in self.wire_items:
            if wi.w["src"][0] == nid or wi.w["dst"][0] == nid:
                wi.update_path()
        if isinstance(item, StructItem):
            for wi in self.wire_items:
                wi.update_path()

    def descendants(self, sid):
        par = compute_parents(self.doc)
        out = []
        for nid in self.doc["nodes"]:
            cur = par.get(nid)
            while cur is not None:
                if cur == sid:
                    out.append(self.items[nid])
                    break
                cur = par.get(cur)
        return out

    def after_move(self, emit=True):
        old = self.parent
        self.parent = compute_parents(self.doc)
        for nid, p in self.parent.items():
            if p is not None and old.get(nid) != p and \
                    self.doc["nodes"][p]["type"] == "case" and old:
                self.doc["nodes"][nid]["frame"] = self.doc["nodes"][p]["params"].get("view", 1)
        for nid, it in self.items.items():
            d = 0
            cur = self.parent.get(nid)
            while cur is not None:
                d += 1
                cur = self.parent.get(cur)
            it.setZValue((-10 + d) if isinstance(it, StructItem) else 10 + d)
        self.refresh_visibility()
        r = self.scene.itemsBoundingRect().adjusted(-2000, -1500, 2000, 1500)
        self.scene.setSceneRect(r.united(QRectF(-1000, -800, 3200, 2400)))
        if emit:
            self.changed.emit()

    def visible(self, nid):
        cur = nid
        while True:
            p = self.parent.get(cur)
            if p is None:
                return True
            pn = self.doc["nodes"][p]
            if pn["type"] == "case" and \
                    self.doc["nodes"][cur].get("frame", 0) != pn["params"].get("view", 1):
                return False
            cur = p

    def refresh_visibility(self):
        for nid, it in self.items.items():
            it.setVisible(self.visible(nid))
        for wi in self.wire_items:
            w = wi.w
            a, b = w["src"][0], w["dst"][0]
            ok = self.visible(a) and self.visible(b)
            bn = self.doc["nodes"].get(b)
            if ok and bn and bn["type"] == "case" and w["dst"][1].endswith("_i"):
                ok = w.get("frame", 0) == bn["params"].get("view", 1)
            wi.setVisible(ok)
            wi.update_path()

    def add_block(self, tid, pos):
        if self.locked:
            return None
        s = SPECS[tid]
        x, y = pos.x(), pos.y()
        if s.kind == "struct":
            nid = add_node(self.doc, tid, x, y, w=320, h=200)
        else:
            nid = add_node(self.doc, tid, x, y)
        self.make_item(nid)
        self.after_move()
        self.items[nid].setSelected(True)
        return nid

    def add_center(self, tid):
        c = self.view.mapToScene(self.view.viewport().rect().center())
        return self.add_block(tid, c)

    def connect_ports(self, a, b):
        if a.dir == b.dir:
            self.status.emit(T("Un cable une una salida con una entrada."))
            return
        src, dst = (a, b) if a.dir == "out" else (b, a)
        if src.nid == dst.nid:
            self.status.emit(T("No se puede cablear un bloque consigo mismo."))
            return
        ts, td = src.typ, dst.typ
        self.parent = compute_parents(self.doc)
        if self.loops_between(src.nid, dst.nid):
            ts = "arr"
        if not (ts == td or "any" in (ts, td)):
            self.status.emit(T("Tipos incompatibles: %s → %s") % (ts, td))
            return
        frame = 0
        dn = self.doc["nodes"][dst.nid]
        if dn["type"] == "case" and dst.name.endswith("_i"):
            frame = dn["params"].get("view", 1)
        for wi in list(self.wire_items):
            if wi.w["dst"] == [dst.nid, dst.name] and wi.w.get("frame", 0) == frame:
                self.scene.removeItem(wi)
                self.wire_items.remove(wi)
        w = add_wire(self.doc, src.nid, src.name, dst.nid, dst.name, frame)
        self.make_wire(w)
        self.refresh_visibility()
        self.status.emit("")
        self.changed.emit()

    def remove_wire(self, w):
        if w in self.doc["wires"]:
            self.doc["wires"].remove(w)
        for wi in list(self.wire_items):
            if wi.w is w:
                self.scene.removeItem(wi)
                self.wire_items.remove(wi)
        self.changed.emit()

    def remove_nodes(self, nids):
        allids = set(nids)
        for nid in list(nids):
            if SPECS[self.doc["nodes"][nid]["type"]].kind == "struct":
                allids.update(it.nid for it in self.descendants(nid))
        for nid in allids:
            if nid not in self.doc["nodes"]:
                continue
            kind = SPECS[self.doc["nodes"][nid]["type"]].kind
            remove_node(self.doc, nid)
            it = self.items.pop(nid, None)
            if it:
                self.scene.removeItem(it)
            if kind in ("ctl", "ind"):
                self.panel_remove.emit(nid)
        live = [w for w in self.doc["wires"]]
        for wi in list(self.wire_items):
            if wi.w not in live:
                self.scene.removeItem(wi)
                self.wire_items.remove(wi)
        self.after_move()

    def delete_selected(self):
        sel = self.scene.selectedItems()
        for it in sel:
            if isinstance(it, WireItem):
                self.remove_wire(it.w)
        self.remove_nodes([it.nid for it in sel if isinstance(it, BaseItem)])

    def edit_node(self, nid):
        if self.locked:
            return
        n = self.doc["nodes"][nid]
        dlg = PropDialog(self, nid, self.view)
        if not dlg.exec_():
            return
        vals = dlg.values()
        n["params"].update(vals)
        it = self.items[nid]
        it.prepareGeometryChange()
        if SPECS[n["type"]].kind == "struct":
            names = [p[0] for p in ports(n)]
            for w in list(self.doc["wires"]):
                for end in ("src", "dst"):
                    if w[end][0] == nid and w[end][1] not in names:
                        self.remove_wire(w)
                        break
        it.make_ports()
        it.update()
        self.moved(it)
        for wi in self.wire_items:
            wi.update_path()
        if SPECS[n["type"]].kind in ("ctl", "ind"):
            self.panel_update.emit(nid)
        self.changed.emit()

    def node_menu(self, nid, pos):
        if self.locked:
            return
        n = self.doc["nodes"][nid]
        s = SPECS[n["type"]]
        m = QMenu()
        acts = {}
        acts[m.addAction(T("Propiedades..."))] = ("props",)
        if s.kind == "struct" and n["type"] in ("while", "for"):
            acts[m.addAction(T("Agregar shift register"))] = ("sr", 1)
            if n["params"].get("sr", 0):
                acts[m.addAction(T("Quitar shift register"))] = ("sr", -1)
        if n["type"] == "case":
            acts[m.addAction(T("Agregar salida"))] = ("outs", 1)
            if n["params"].get("outs", 0):
                acts[m.addAction(T("Quitar salida"))] = ("outs", -1)
            acts[m.addAction(T("Mostrar caso %s") % frame_name(
                0 if n["params"].get("view", 1) else 1))] = ("flip",)
        if s.kind not in ("struct",):
            unw = [(nm, t, lbl) for nm, t, _d, lbl in s.ins if not self.is_wired(nid, nm)]
            if unw:
                sub = m.addMenu(T("Crear constante"))
                sub2 = m.addMenu(T("Crear control"))
                for nm, t, lbl in unw:
                    if t in ("num", "bool", "str"):
                        acts[sub.addAction(T(lbl))] = ("const", nm, t)
                        acts[sub2.addAction(T(lbl))] = ("ctl", nm, t)
            if s.outs:
                sub = m.addMenu(T("Crear indicador"))
                for nm, t, lbl in s.outs:
                    if t != "ses":
                        acts[sub.addAction(T(lbl))] = ("ind", nm, t, T(lbl))
        m.addSeparator()
        acts[m.addAction(T("Eliminar"))] = ("del",)
        a = m.exec_(pos)
        if a not in acts:
            return
        act = acts[a]
        if act[0] == "props":
            self.edit_node(nid)
        elif act[0] in ("sr", "outs"):
            key = act[0]
            n["params"][key] = max(0, int(n["params"].get(key, 0)) + act[1])
            it = self.items[nid]
            names = [p[0] for p in ports(n)]
            for w in list(self.doc["wires"]):
                if (w["src"][0] == nid and w["src"][1] not in names) or \
                        (w["dst"][0] == nid and w["dst"][1] not in names):
                    self.remove_wire(w)
            it.make_ports()
            self.moved(it)
            self.changed.emit()
        elif act[0] == "flip":
            n["params"]["view"] = 0 if n["params"].get("view", 1) else 1
            self.items[nid].update()
            self.refresh_visibility()
        elif act[0] == "del":
            self.remove_nodes([nid])
        else:
            self.create_for(nid, act)

    def create_for(self, nid, act):
        n = self.doc["nodes"][nid]
        kind, port, t = act[0], act[1], act[2]
        pp = node_port_pos(n, port, "out" if kind == "ind" else "in")
        w, _h = node_size(n)
        if kind == "const":
            tid = {"num": "const_num", "bool": "const_bool", "str": "const_str"}[t]
            new = add_node(self.doc, tid, n["x"] - 60, n["y"] + pp.y() - 11)
            self.doc["nodes"][new]["frame"] = n.get("frame", 0)
            self.make_item(new)
            w_ = add_wire(self.doc, new, "v", nid, port)
        elif kind == "ctl":
            tid = {"num": "ctl_num", "bool": "ctl_bool", "str": "ctl_str"}[t]
            lbl = [l for nm, _t, _d, l in SPECS[n["type"]].ins if nm == port][0]
            new = add_node(self.doc, tid, n["x"] - 80, n["y"] + pp.y() - 13, label=T(lbl))
            self.doc["nodes"][new]["frame"] = n.get("frame", 0)
            self.make_item(new)
            self.panel_add.emit(new)
            w_ = add_wire(self.doc, new, "v", nid, port)
        else:
            tid = {"num": "ind_num", "bool": "ind_led", "str": "ind_str",
                   "arr": "ind_graph"}.get(t, "ind_num")
            new = add_node(self.doc, tid, n["x"] + w + 50, n["y"] + pp.y() - 13, label=act[3])
            self.doc["nodes"][new]["frame"] = n.get("frame", 0)
            self.make_item(new)
            self.panel_add.emit(new)
            w_ = add_wire(self.doc, nid, port, new, "v")
        self.make_wire(w_)
        self.after_move()

    def set_locked(self, on):
        self.locked = on
        for it in self.items.values():
            it.setFlag(QGraphicsItem.ItemIsMovable, not on)

    def clear_errors(self):
        for it in self.items.values():
            if it.error:
                it.error = False
                it.update()

    def mark_error(self, nid):
        it = self.items.get(nid)
        if it:
            it.error = True
            it.update()
            if not it.isVisible():
                cur = self.parent.get(nid)
                child = nid
                while cur is not None:
                    pn = self.doc["nodes"][cur]
                    if pn["type"] == "case":
                        pn["params"]["view"] = self.doc["nodes"][child].get("frame", 0)
                        self.items[cur].update()
                    child, cur = cur, self.parent.get(cur)
                self.refresh_visibility()
            self.view.ensureVisible(it)

    def fit(self):
        r = self.scene.itemsBoundingRect().adjusted(-40, -40, 40, 40)
        self.view.resetTransform()
        if r.width() > self.view.viewport().width() or r.height() > self.view.viewport().height():
            self.view.fitInView(r, Qt.KeepAspectRatio)
        self.view.centerOn(r.center())
PMIME = "application/x-camipanel"
MMIME = "application/x-camimove"


def nice_range(lo, hi, n=5):
    if hi - lo < 1e-9:
        hi, lo = hi + 0.5, lo - 0.5
    raw = (hi - lo) / float(n)
    e = 10 ** math.floor(math.log10(raw))
    st = next(m * e for m in (1, 2, 5, 10) if raw <= m * e)
    lo = math.floor(lo / st) * st
    hi = math.ceil(hi / st) * st
    return lo, hi, max(1, int(round((hi - lo) / st)))


def img_to_b64(path, maxpx=900):
    im = QImage(path)
    if im.isNull():
        return None
    if max(im.width(), im.height()) > maxpx:
        im = im.scaled(maxpx, maxpx, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.WriteOnly)
    im.save(buf, "PNG")
    return base64.b64encode(bytes(ba)).decode("ascii")


def b64_to_pix(data):
    pm = QPixmap()
    if data:
        pm.loadFromData(base64.b64decode(data), "PNG")
    return pm


def pick_image(parent):
    path, _f = QFileDialog.getOpenFileName(parent, T("Elegir imagen"), os.path.expanduser("~"),
                                           T("Imágenes") + " (*.png *.jpg *.jpeg *.bmp *.gif)")
    if not path:
        return None
    data = img_to_b64(path)
    if data is None:
        QMessageBox.warning(parent, APP, T("No se pudo leer la imagen."))
    return data


def fmt(v, dec=3):
    if isinstance(v, bool):
        return "T" if v else "F"
    if isinstance(v, (int, float)):
        if v != v:
            return "NaN"
        return "%.*f" % (int(dec), v)
    if isinstance(v, (list, tuple)):
        return "[%d]" % len(v)
    return str(v)


class ImageBox(QLabel):
    def __init__(self, data=None):
        QLabel.__init__(self)
        self.pm = b64_to_pix(data)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(20, 20)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

    def resizeEvent(self, e):
        if not self.pm.isNull():
            self.setPixmap(self.pm.scaled(self.size(), Qt.KeepAspectRatio,
                                          Qt.SmoothTransformation))
        QLabel.resizeEvent(self, e)


class Gauge(QWidget):
    def __init__(self, p):
        QWidget.__init__(self)
        self.p = p
        self.v = None
        self.setMinimumSize(90, 80)

    def put(self, v):
        self.v = v
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        lo, hi = float(self.p.get("min", 0)), float(self.p.get("max", 10))
        s = max(40.0, min(self.width() - 10, (self.height() - 14) / 0.86))
        R = QRectF((self.width() - s) / 2, 6, s, s)
        p.setPen(QPen(TH["lo"], 2))
        p.setBrush(TH["input"])
        p.drawPie(R, -45 * 16, 270 * 16)
        c = R.center()
        r = s / 2
        f = QFont()
        f.setPixelSize(max(8, int(s / 14)))
        p.setFont(f)
        for k in range(11):
            a = math.radians(225 - 27 * k)
            x0, y0 = c.x() + math.cos(a) * r * 0.82, c.y() - math.sin(a) * r * 0.82
            x1, y1 = c.x() + math.cos(a) * r * 0.95, c.y() - math.sin(a) * r * 0.95
            p.setPen(QPen(TH["text"], 2 if k % 5 == 0 else 1))
            p.drawLine(QPointF(x0, y0), QPointF(x1, y1))
            if k % 5 == 0:
                tx, ty = c.x() + math.cos(a) * r * 0.66, c.y() - math.sin(a) * r * 0.66
                p.drawText(QRectF(tx - 30, ty - 8, 60, 16), Qt.AlignCenter,
                           "%g" % round(lo + (hi - lo) * k / 10.0, 3))
        v = self.v if isinstance(self.v, (int, float)) and not isinstance(self.v, bool) else None
        if v is not None and v == v:
            fr = max(0.0, min(1.0, (v - lo) / ((hi - lo) or 1e-12)))
            a = math.radians(225 - 270 * fr)
            p.setPen(QPen(TH["alert"], 3, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(c, QPointF(c.x() + math.cos(a) * r * 0.8, c.y() - math.sin(a) * r * 0.8))
        p.setBrush(TH["text"])
        p.setPen(Qt.NoPen)
        p.drawEllipse(c, 5, 5)
        f.setPixelSize(max(10, int(s / 9)))
        f.setBold(True)
        p.setFont(f)
        p.setPen(TH["accent"])
        txt = (fmt(v, self.p.get("dec", 2)) if v is not None else "---") + " " + \
            self.p.get("units", "")
        p.drawText(QRectF(R.left(), c.y() + r * 0.5, R.width(), r * 0.36), Qt.AlignCenter, txt)


class Bar(QWidget):
    def __init__(self, p):
        QWidget.__init__(self)
        self.p = p
        self.v = None
        self.setMinimumSize(60, 80)

    def put(self, v):
        self.v = v
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        lo, hi = float(self.p.get("min", 0)), float(self.p.get("max", 10))
        H = self.height() - 30
        bw = min(26, self.width() / 3)
        x = self.width() / 2 - bw / 2 - 14
        R = QRectF(x, 6, bw, H)
        p.setPen(QPen(TH["lo"], 2))
        p.setBrush(TH["screen"])
        p.drawRect(R)
        v = self.v if isinstance(self.v, (int, float)) and not isinstance(self.v, bool) else None
        if v is not None and v == v:
            fr = max(0.0, min(1.0, (v - lo) / ((hi - lo) or 1e-12)))
            p.fillRect(QRectF(R.left() + 2, R.bottom() - 2 - (H - 4) * fr, bw - 4, (H - 4) * fr),
                       TH["signal"])
        f = QFont()
        f.setPixelSize(10)
        p.setFont(f)
        p.setPen(TH["text"])
        for k in range(6):
            y = R.bottom() - H * k / 5.0
            p.drawLine(QPointF(R.right() + 2, y), QPointF(R.right() + 7, y))
            p.drawText(QRectF(R.right() + 9, y - 7, 60, 14), Qt.AlignLeft | Qt.AlignVCenter,
                       "%g" % round(lo + (hi - lo) * k / 5.0, 3))
        f.setBold(True)
        f.setPixelSize(12)
        p.setFont(f)
        p.setPen(TH["accent"])
        p.drawText(QRectF(0, self.height() - 22, self.width(), 20), Qt.AlignCenter,
                   (fmt(v, self.p.get("dec", 2)) if v is not None else "---") + " " +
                   self.p.get("units", ""))


class PItem(QFrame):
    def __init__(self, panel, iid):
        QFrame.__init__(self, panel.grid)
        self.panel = panel
        self.iid = iid
        self.setObjectName("pitem")
        self.hist = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 6)
        lay.setSpacing(3)
        self.head = QLabel("")
        self.head.setObjectName("phead")
        lay.addWidget(self.head)
        self.body = QWidget()
        self.bl = QVBoxLayout(self.body)
        self.bl.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.body, 1)
        self.build()

    @property
    def node(self):
        return self.panel.doc["nodes"].get(self.iid)

    @property
    def kind(self):
        n = self.node
        return n["type"] if n else "image"

    def build(self):
        while self.bl.count():
            w = self.bl.takeAt(0).widget()
            if w:
                w.setParent(None)
        k = self.kind
        n = self.node
        p = n["params"] if n else {}
        self.head.setText(p.get("label", "") if n else "")
        self.head.setVisible(bool(n))
        self.w = None
        if k == "image":
            self.w = ImageBox(self.panel.doc["panel"]["items"][self.iid].get("data"))
        elif k == "ctl_num":
            self.w = QDoubleSpinBox()
            self.w.setRange(float(p.get("min", 0)), float(p.get("max", 10)))
            self.w.setDecimals(int(p.get("dec", 3)))
            self.w.setSingleStep((float(p.get("max", 10)) - float(p.get("min", 0))) / 100.0)
            if p.get("units"):
                self.w.setSuffix(" " + p["units"])
            self.w.setValue(float(p.get("value", 0)))
            self.w.setMinimumHeight(30)
            f = self.w.font()
            f.setPointSize(13)
            self.w.setFont(f)
            self.w.valueChanged.connect(self.changed)
        elif k in ("ctl_knob", "ctl_slider"):
            box = QWidget()
            v = QVBoxLayout(box)
            v.setContentsMargins(0, 0, 0, 0)
            if k == "ctl_knob":
                self.dial = QDial()
                self.dial.setNotchesVisible(True)
                self.dial.setMinimumSize(60, 60)
            else:
                self.dial = QSlider(Qt.Horizontal)
            self.dial.setRange(0, 1000)
            lo, hi = float(p.get("min", 0)), float(p.get("max", 10))
            self.dial.setValue(int(round(1000 * (float(p.get("value", 0)) - lo) / ((hi - lo) or 1))))
            self.val = QLabel("")
            self.val.setObjectName("readout")
            self.val.setAlignment(Qt.AlignCenter)
            v.addWidget(self.dial, 1)
            v.addWidget(self.val)
            self.w = box
            self.dial.valueChanged.connect(self.changed)
        elif k == "ctl_str":
            self.w = QLineEdit(str(p.get("value", "")))
            self.w.textChanged.connect(self.changed)
        elif k == "ctl_ring":
            self.w = QComboBox()
            for o in [x.strip() for x in str(p.get("options", "")).split(";") if x.strip()]:
                self.w.addItem(o)
            self.w.setCurrentIndex(int(p.get("value", 0)))
            self.w.currentIndexChanged.connect(self.changed)
        elif k == "ctl_color":
            self.w = QPushButton("")
            self.w.setMinimumHeight(34)
            self.w.clicked.connect(self.pick_color)
        elif k in ("ctl_bool", "ctl_stop"):
            box = QWidget()
            hl = QHBoxLayout(box)
            hl.setContentsMargins(0, 0, 0, 0)
            self.btn = QPushButton("STOP" if k == "ctl_stop" else "OFF")
            self.btn.setCheckable(True)
            self.btn.setMinimumHeight(34)
            if k == "ctl_stop":
                self.btn.setObjectName("stopbtn")
            self.btn.setChecked(bool(p.get("value", False)) and k == "ctl_bool")
            self.led = Led(TH["signal"].name(), 22)
            hl.addWidget(self.btn, 1)
            hl.addWidget(self.led)
            self.w = box
            self.btn.toggled.connect(self.changed)
        elif k == "ind_num":
            self.w = QLabel("---")
            self.w.setObjectName("lcd")
            self.w.setStyleSheet("font-size:%dpx;" % max(18, min(48, 14 * self.span_h())))
            self.w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        elif k == "ind_led":
            box = QWidget()
            hl = QHBoxLayout(box)
            self.led = Led(TH["signal"].name(), 40)
            hl.addStretch(1)
            hl.addWidget(self.led)
            hl.addStretch(1)
            self.w = box
        elif k == "ind_gauge":
            self.w = Gauge(p)
        elif k == "ind_bar":
            self.w = Bar(p)
        elif k in ("ind_chart", "ind_graph"):
            self.w = Plot()
            style_plot(self.w)
            self.w.setMinimumSize(120, 90)
            self.w.yfmt = lambda v: "%g" % round(v, 4)
            self.w.xfmt = lambda v: "%g" % round(v, 2)
            self.w.nx, self.w.ny = 5, 5
        elif k == "ind_str":
            self.w = QLabel("")
            self.w.setObjectName("readout")
            self.w.setWordWrap(True)
            self.w.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        if self.w is not None:
            self.bl.addWidget(self.w)
        self.changed()
        self.reset()

    def span_h(self):
        it = self.panel.doc["panel"]["items"].get(self.iid, {})
        return it.get("rs", 1)

    def value(self):
        k = self.kind
        p = self.node["params"] if self.node else {}
        if k == "ctl_num":
            return self.w.value()
        if k in ("ctl_knob", "ctl_slider"):
            lo, hi = float(p.get("min", 0)), float(p.get("max", 10))
            return lo + (hi - lo) * self.dial.value() / 1000.0
        if k == "ctl_str":
            return self.w.text()
        if k == "ctl_ring":
            return float(max(0, self.w.currentIndex()))
        if k == "ctl_color":
            return list(p.get("value", [255, 0, 0]))
        if k in ("ctl_bool", "ctl_stop"):
            return self.btn.isChecked()
        return None

    def changed(self, *_a):
        k = self.kind
        if not k.startswith("ctl"):
            return
        v = self.value()
        p = self.node["params"]
        if k in ("ctl_knob", "ctl_slider"):
            self.val.setText(fmt(v, p.get("dec", 3)) + " " + p.get("units", ""))
        if k == "ctl_color":
            r, g, b = v
            self.w.setText("R %d  G %d  B %d" % (r, g, b))
            fg = "#000000" if (r * 0.3 + g * 0.59 + b * 0.11) > 128 else "#ffffff"
            self.w.setStyleSheet("QPushButton{background:rgb(%d,%d,%d);color:%s;"
                                 "font-weight:bold;}" % (r, g, b, fg))
        if k == "ctl_bool":
            self.btn.setText("ON" if v else "OFF")
            self.led.set(v)
        if k == "ctl_stop":
            self.led.set(v)
        self.panel.ctl_values[self.iid] = v
        if not self.panel.running and k != "ctl_stop" and p.get("value") != v:
            p["value"] = v
            self.panel.modified()

    def pick_color(self):
        r, g, b = self.node["params"].get("value", [255, 0, 0])
        c = QColorDialog.getColor(QColor(int(r), int(g), int(b)), self, T("Color"))
        if c.isValid():
            self.node["params"]["value"] = [c.red(), c.green(), c.blue()]
            self.changed()

    def reset(self):
        k = self.kind
        self.hist = []
        if k == "ind_num":
            self.w.setText("---")
        elif k == "ind_led":
            self.led.set(False)
        elif k in ("ind_gauge", "ind_bar"):
            self.w.put(None)
        elif k in ("ind_chart", "ind_graph"):
            self.w.overlay = []
            self.w.xr, self.w.yr = (0, 10), (0, 1)
            self.w.set_traces([])
        elif k == "ind_str":
            self.w.setText("")
        elif k == "ctl_stop":
            self.btn.setChecked(False)

    def put(self, v):
        k = self.kind
        p = self.node["params"]
        if k == "ind_num":
            self.w.setText(fmt(v, p.get("dec", 3)) + (" " + p["units"] if p.get("units") else ""))
        elif k == "ind_led":
            self.led.set(bool(v) if not isinstance(v, (list, tuple)) else any(v))
        elif k in ("ind_gauge", "ind_bar"):
            self.w.put(v)
        elif k == "ind_str":
            self.w.setText(fmt(v) if not isinstance(v, str) else v)
        elif k == "ind_graph":
            ys = [float(x) for x in (v if isinstance(v, (list, tuple)) else [v])
                  if isinstance(x, (int, float))]
            self.draw(list(range(len(ys))), ys)

    def feed(self, vals):
        p = self.node["params"]
        for v in vals:
            if isinstance(v, (list, tuple)):
                self.hist.extend(float(x) for x in v if isinstance(x, (int, float)))
            elif isinstance(v, (int, float)):
                self.hist.append(float(v))
        n = int(p.get("hist", 200)) or 200
        self.hist = self.hist[-n:]
        self.chart_n = getattr(self, "chart_n", 0) + len(vals)
        x0 = max(0, self.chart_n - len(self.hist))
        self.draw([x0 + i for i in range(len(self.hist))], self.hist, n)

    def draw(self, xs, ys, span=None):
        pl = self.w
        if not ys:
            return
        lo, hi, ny = nice_range(min(ys), max(ys), 5)
        pl.yr = (lo, hi)
        pl.ny = ny
        if span:
            pl.xr = (xs[0], xs[0] + span)
            pl.nx = 5
        else:
            x0, x1, nx = nice_range(0, max(1, len(ys) - 1), 5)
            pl.xr = (0, x1)
            pl.nx = nx
        pl.overlay = [(TH["signal"], fmt(ys[-1], self.node["params"].get("dec", 3)) + " " +
                       self.node["params"].get("units", ""))]
        pl.set_traces([(xs, ys, TH["signal"])])

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self.panel.running:
            self.drag_start = e.pos()
        QFrame.mousePressEvent(self, e)

    def mouseMoveEvent(self, e):
        if not self.panel.running and getattr(self, "drag_start", None) is not None and \
                (e.pos() - self.drag_start).manhattanLength() > 8:
            self.drag_start = None
            md = QMimeData()
            md.setData(MMIME, self.iid.encode())
            d = QDrag(self)
            d.setMimeData(md)
            d.setPixmap(self.grab().scaled(160, 120, Qt.KeepAspectRatio))
            d.exec_(Qt.MoveAction)
            return
        QFrame.mouseMoveEvent(self, e)

    def mouseDoubleClickEvent(self, e):
        if not self.panel.running:
            self.panel.props(self.iid)

    def contextMenuEvent(self, e):
        if self.panel.running:
            return
        self.panel.item_menu(self.iid, e.globalPos())


class FreeText(QLabel):
    def __init__(self, panel, t):
        QLabel.__init__(self, panel)
        self.panel = panel
        self.t = t
        self.setObjectName("freetext")
        self.setText(t["text"])
        f = self.font()
        f.setPointSize(int(t.get("size", 11)))
        f.setBold(bool(t.get("bold", False)))
        self.setFont(f)
        self.adjustSize()
        self.off = None

    def place(self):
        r = self.panel.rect()
        self.adjustSize()
        self.move(int(self.t["x"] * r.width()), int(self.t["y"] * r.height()))
        self.raise_()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self.panel.running:
            self.off = e.pos()

    def mouseMoveEvent(self, e):
        if self.off is not None:
            p = self.mapToParent(e.pos() - self.off)
            r = self.panel.rect()
            self.move(max(0, min(r.width() - 20, p.x())), max(0, min(r.height() - 10, p.y())))

    def mouseReleaseEvent(self, e):
        if self.off is not None:
            r = self.panel.rect()
            self.t["x"] = self.x() / float(max(1, r.width()))
            self.t["y"] = self.y() / float(max(1, r.height()))
            self.off = None
            self.panel.modified()

    def mouseDoubleClickEvent(self, e):
        if not self.panel.running:
            self.panel.edit_text(self)

    def contextMenuEvent(self, e):
        if self.panel.running:
            return
        m = QMenu()
        a1 = m.addAction(T("Editar texto..."))
        sub = m.addMenu(T("Tamaño de letra"))
        sizes = {}
        for s in (9, 11, 14, 18, 24, 32):
            sizes[sub.addAction("%d pt" % s)] = s
        a2 = m.addAction(T("Negrita"))
        a2.setCheckable(True)
        a2.setChecked(bool(self.t.get("bold")))
        m.addSeparator()
        a3 = m.addAction(T("Eliminar"))
        a = m.exec_(e.globalPos())
        if a == a1:
            self.panel.edit_text(self)
        elif a in sizes:
            self.t["size"] = sizes[a]
            self.panel.rebuild_texts()
        elif a == a2:
            self.t["bold"] = not self.t.get("bold")
            self.panel.rebuild_texts()
        elif a == a3:
            self.panel.doc["panel"]["texts"].remove(self.t)
            self.panel.rebuild_texts()
        self.panel.modified()


class Grid(QWidget):
    GAP = 6

    def __init__(self, panel):
        QWidget.__init__(self)
        self.panel = panel
        self.setAcceptDrops(True)
        self.hover = None
        self.setMinimumSize(300, 200)

    def cell_rect(self, r, c, rs=1, cs=1):
        P = self.panel.doc["panel"]
        W = self.width() - self.GAP
        H = self.height() - self.GAP
        cw = W / float(P["cols"])
        ch = H / float(P["rows"])
        return QRectF(self.GAP + c * cw, self.GAP + r * ch, cs * cw - self.GAP, rs * ch - self.GAP)

    def cell_at(self, pos):
        P = self.panel.doc["panel"]
        cw = (self.width() - self.GAP) / float(P["cols"])
        ch = (self.height() - self.GAP) / float(P["rows"])
        c = int((pos.x() - self.GAP / 2) // cw)
        r = int((pos.y() - self.GAP / 2) // ch)
        if 0 <= r < P["rows"] and 0 <= c < P["cols"]:
            return r, c
        return None

    def layout_items(self):
        for iid, w in self.panel.widgets.items():
            it = self.panel.doc["panel"]["items"][iid]
            w.setGeometry(self.cell_rect(it["r"], it["c"], it["rs"], it["cs"]).toRect())
            w.show()

    def resizeEvent(self, e):
        self.layout_items()

    def paintEvent(self, e):
        if self.panel.running:
            return
        p = QPainter(self)
        P = self.panel.doc["panel"]
        for r in range(P["rows"]):
            for c in range(P["cols"]):
                R = self.cell_rect(r, c)
                hot = self.hover == (r, c)
                p.setPen(QPen(TH["accent"] if hot else TH["text2"], 1.5 if hot else 1,
                              Qt.DashLine))
                p.setBrush(QColor(TH["accent"].red(), TH["accent"].green(), TH["accent"].blue(),
                                  70) if hot else Qt.NoBrush)
                p.drawRect(R)

    def dragEnterEvent(self, e):
        md = e.mimeData()
        if (md.hasFormat(PMIME) or md.hasFormat(MMIME)) and not self.panel.running:
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        self.hover = self.cell_at(e.pos())
        self.update()
        e.acceptProposedAction()

    def dragLeaveEvent(self, e):
        self.hover = None
        self.update()

    def dropEvent(self, e):
        self.hover = None
        self.update()
        cell = self.cell_at(e.pos())
        md = e.mimeData()
        if md.hasFormat(PMIME):
            tid = bytes(md.data(PMIME)).decode()
            if tid == "text":
                self.panel.add_text(self.mapTo(self.panel, e.pos()))
            elif cell:
                self.panel.add_item(tid, cell)
        elif md.hasFormat(MMIME) and cell:
            self.panel.move_item(bytes(md.data(MMIME)).decode(), cell)
        e.acceptProposedAction()


class Banner(QFrame):
    def __init__(self, panel, key):
        QFrame.__init__(self)
        self.panel = panel
        self.key = key
        self.setObjectName("banner")
        hl = QHBoxLayout(self)
        hl.setContentsMargins(10, 4, 10, 4)
        self.img = QLabel()
        self.txt = QLabel()
        self.txt.setObjectName("btitle" if key == "title" else "bfooter")
        self.txt.setWordWrap(True)
        hl.addWidget(self.img)
        hl.addWidget(self.txt, 1)

    def refresh(self):
        d = self.panel.doc["panel"][self.key]
        pm = b64_to_pix(d.get("image"))
        h = 54 if self.key == "title" else 36
        if not pm.isNull():
            self.img.setPixmap(pm.scaledToHeight(h, Qt.SmoothTransformation))
            self.img.show()
        else:
            self.img.hide()
        self.txt.setText(d.get("text", ""))
        on = d.get("on", True) and (bool(d.get("text")) or not pm.isNull())
        self.setVisible(on or (not self.panel.running and self.key == "title"))
        if not d.get("text") and pm.isNull():
            self.txt.setText(T("Título del panel (doble clic para editar)")
                             if self.key == "title" else "")

    def mouseDoubleClickEvent(self, e):
        if not self.panel.running:
            self.panel.config()





class Panel(QWidget):
    def __init__(self, host):
        QWidget.__init__(self)
        self.host = host
        self.setObjectName("panel")
        self.running = False
        self.widgets = {}
        self.texts = []
        self.ctl_values = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(4)
        self.title = Banner(self, "title")
        self.grid = Grid(self)
        self.footer = Banner(self, "footer")
        lay.addWidget(self.title)
        lay.addWidget(self.grid, 1)
        lay.addWidget(self.footer)

    @property
    def doc(self):
        return self.host.doc

    def modified(self):
        self.host.set_modified()

    def rebuild(self):
        for w in self.widgets.values():
            w.setParent(None)
        self.widgets = {}
        self.ctl_values.clear()
        P = self.doc["panel"]
        for iid in list(P["items"]):
            if iid in self.doc["nodes"] or P["items"][iid].get("kind") == "image":
                self.widgets[iid] = PItem(self, iid)
            else:
                del P["items"][iid]
        self.title.refresh()
        self.footer.refresh()
        self.grid.layout_items()
        self.rebuild_texts()

    def rebuild_texts(self):
        for t in self.texts:
            t.setParent(None)
        self.texts = []
        for t in self.doc["panel"]["texts"]:
            ft = FreeText(self, t)
            ft.show()
            ft.place()
            self.texts.append(ft)

    def resizeEvent(self, e):
        QWidget.resizeEvent(self, e)
        for t in self.texts:
            t.place()

    def set_running(self, on):
        self.running = on
        self.title.refresh()
        self.footer.refresh()
        self.grid.update()

    def occupied(self, ignore=None):
        occ = set()
        for iid, it in self.doc["panel"]["items"].items():
            if iid == ignore:
                continue
            for r in range(it["r"], it["r"] + it["rs"]):
                for c in range(it["c"], it["c"] + it["cs"]):
                    occ.add((r, c))
        return occ

    def fits(self, r, c, rs, cs, ignore=None):
        P = self.doc["panel"]
        if r < 0 or c < 0 or r + rs > P["rows"] or c + cs > P["cols"]:
            return False
        occ = self.occupied(ignore)
        return all((rr, cc) not in occ for rr in range(r, r + rs) for cc in range(c, c + cs))

    def free_cell(self):
        P = self.doc["panel"]
        for r in range(P["rows"]):
            for c in range(P["cols"]):
                if self.fits(r, c, 1, 1):
                    return r, c
        P["rows"] += 1
        return P["rows"] - 1, 0

    def place(self, iid, cell, big=False):
        r, c = cell
        rs = cs = 1
        if big and self.fits(r, c, 2, 2):
            rs = cs = 2
        elif big and self.fits(r, c, 1, 2):
            cs = 2
        if not self.fits(r, c, rs, cs):
            QMessageBox.information(self, APP, T("Esa casilla ya está ocupada."))
            return False
        self.doc["panel"]["items"][iid] = {"r": r, "c": c, "rs": rs, "cs": cs}
        return True

    def add_item(self, tid, cell):
        if tid == "image":
            data = pick_image(self)
            if not data:
                return
            n = 1
            while "img%d" % n in self.doc["panel"]["items"]:
                n += 1
            iid = "img%d" % n
            if self.place(iid, cell, big=True):
                self.doc["panel"]["items"][iid].update({"kind": "image", "data": data})
        else:
            if not self.fits(cell[0], cell[1], 1, 1):
                QMessageBox.information(self, APP, T("Esa casilla ya está ocupada."))
                return
            iid = self.host.new_terminal(tid)
            self.place(iid, cell, big=tid in ("ind_chart", "ind_graph"))
        self.rebuild()
        self.modified()

    def adopt(self, nid):
        if nid not in self.doc["panel"]["items"]:
            self.place(nid, self.free_cell())
        self.rebuild()

    def move_item(self, iid, cell):
        it = self.doc["panel"]["items"].get(iid)
        if not it:
            return
        if self.fits(cell[0], cell[1], it["rs"], it["cs"], ignore=iid):
            it["r"], it["c"] = cell
        elif self.fits(cell[0], cell[1], 1, 1, ignore=iid):
            it["r"], it["c"], it["rs"], it["cs"] = cell[0], cell[1], 1, 1
        else:
            return
        self.grid.layout_items()
        self.modified()

    def remove_item(self, iid):
        self.doc["panel"]["items"].pop(iid, None)
        w = self.widgets.pop(iid, None)
        if w:
            w.setParent(None)
        self.ctl_values.pop(iid, None)

    def props(self, iid):
        if iid in self.doc["nodes"]:
            self.host.diagram.edit_node(iid)
        else:
            data = pick_image(self)
            if data:
                self.doc["panel"]["items"][iid]["data"] = data
                self.rebuild()
                self.modified()

    def update_item(self, iid):
        if iid in self.widgets:
            self.widgets[iid].build()

    def item_menu(self, iid, pos):
        it = self.doc["panel"]["items"][iid]
        m = QMenu()
        a_p = m.addAction(T("Propiedades...") if iid in self.doc["nodes"] else T("Cambiar imagen..."))
        sub = m.addMenu(T("Tamaño (ancho × alto)"))
        sizes = {}
        for cs, rs in ((1, 1), (2, 1), (1, 2), (2, 2), (3, 1), (3, 2), (2, 3), (3, 3), (4, 2)):
            a = sub.addAction("%d × %d" % (cs, rs))
            a.setEnabled(self.fits(it["r"], it["c"], rs, cs, ignore=iid))
            sizes[a] = (rs, cs)
        a_g = None
        if iid in self.doc["nodes"]:
            a_g = m.addAction(T("Ver en el diagrama"))
        m.addSeparator()
        a_d = m.addAction(T("Eliminar"))
        a = m.exec_(pos)
        if a == a_p:
            self.props(iid)
        elif a in sizes:
            it["rs"], it["cs"] = sizes[a]
            self.update_item(iid)
            self.grid.layout_items()
            self.modified()
        elif a is not None and a == a_g:
            self.host.show_in_diagram(iid)
        elif a == a_d:
            if iid in self.doc["nodes"]:
                self.host.diagram.remove_nodes([iid])
            self.remove_item(iid)
            self.modified()

    def add_text(self, pos):
        txt, ok = QInputDialog.getText(self, APP, T("Texto:"))
        if not ok or not txt.strip():
            return
        r = self.rect()
        self.doc["panel"]["texts"].append({"x": pos.x() / float(r.width()),
                                           "y": pos.y() / float(r.height()),
                                           "text": txt, "size": 12})
        self.rebuild_texts()
        self.modified()

    def edit_text(self, ft):
        txt, ok = QInputDialog.getText(self, APP, T("Texto:"), text=ft.t["text"])
        if ok:
            ft.t["text"] = txt
            self.rebuild_texts()
            self.modified()

    def config(self):
        P = self.doc["panel"]
        dlg = QDialog(self)
        dlg.setWindowTitle(T("Configurar panel"))
        f = QFormLayout(dlg)
        rows = QSpinBox()
        rows.setRange(1, 12)
        rows.setValue(P["rows"])
        cols = QSpinBox()
        cols.setRange(1, 12)
        cols.setValue(P["cols"])
        f.addRow(T("Filas de la cuadrícula"), rows)
        f.addRow(T("Columnas de la cuadrícula"), cols)
        tt = QLineEdit(P["title"].get("text", ""))
        f.addRow(T("Título"), tt)
        imgs = {"title": P["title"].get("image"), "footer": P["footer"].get("image")}

        def img_row(key, label):
            hl = QHBoxLayout()
            b1 = QPushButton(T("Elegir..."))
            b2 = QPushButton(T("Quitar"))
            st = QLabel(T("con imagen") if imgs[key] else T("sin imagen"))
            hl.addWidget(b1)
            hl.addWidget(b2)
            hl.addWidget(st, 1)

            def choose():
                d = pick_image(dlg)
                if d:
                    imgs[key] = d
                    st.setText(T("con imagen"))

            def clear():
                imgs[key] = None
                st.setText(T("sin imagen"))
            b1.clicked.connect(choose)
            b2.clicked.connect(clear)
            f.addRow(label, hl)
        img_row("title", T("Imagen del título"))
        fon = QCheckBox(T("Mostrar footer"))
        fon.setChecked(bool(P["footer"].get("on")))
        f.addRow("", fon)
        ft = QLineEdit(P["footer"].get("text", ""))
        f.addRow(T("Texto del footer"), ft)
        img_row("footer", T("Imagen del footer"))
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if not dlg.exec_():
            return
        need_r = max([it["r"] + it["rs"] for it in P["items"].values()] or [1])
        need_c = max([it["c"] + it["cs"] for it in P["items"].values()] or [1])
        if rows.value() < need_r or cols.value() < need_c:
            QMessageBox.information(self, APP, T("La cuadrícula no puede ser más chica que los "
                                                 "objetos que ya tiene (mínimo %d × %d).")
                                    % (need_r, need_c))
        P["rows"] = max(rows.value(), need_r)
        P["cols"] = max(cols.value(), need_c)
        P["title"] = {"text": tt.text(), "image": imgs["title"]}
        P["footer"] = {"on": fon.isChecked(), "text": ft.text(), "image": imgs["footer"]}
        self.rebuild()
        self.modified()

    def capture(self):
        self.ctl_values.clear()
        for iid, w in self.widgets.items():
            if w.kind.startswith("ctl"):
                if w.kind == "ctl_stop":
                    w.btn.setChecked(False)
                self.ctl_values[iid] = w.value()
            w.reset()

    def show_values(self, latest, feeds):
        for iid, v in latest.items():
            w = self.widgets.get(iid)
            if w is not None and w.kind != "ind_chart":
                w.put(v)
        for iid, vals in feeds.items():
            w = self.widgets.get(iid)
            if w is not None:
                w.feed(vals)


class PanelPalette(QTreeWidget):
    def __init__(self):
        QTreeWidget.__init__(self)
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        groups = [(T("Controles"), [(k, l) for k, l, _o in CTL_KINDS]),
                  (T("Indicadores"), [(k, l) for k, l, _t in IND_KINDS]),
                  (T("Decoración"), PANEL_ONLY)]
        for name, items in groups:
            top = QTreeWidgetItem([name])
            top.setFlags(Qt.ItemIsEnabled)
            f = top.font(0)
            f.setBold(True)
            top.setFont(0, f)
            self.addTopLevelItem(top)
            for k, l in items:
                it = QTreeWidgetItem([T(l)])
                it.setData(0, Qt.UserRole, k)
                top.addChild(it)
            top.setExpanded(True)

    def startDrag(self, actions):
        it = self.currentItem()
        tid = it.data(0, Qt.UserRole) if it else None
        if not tid:
            return
        md = QMimeData()
        md.setData(PMIME, tid.encode())
        d = QDrag(self)
        d.setMimeData(md)
        d.exec_(Qt.CopyAction)


def hexs(b):
    return " ".join("%02X" % x for x in b)


def rx_text(b):
    if not b:
        return T("(nada: timeout)")
    if b.endswith(b"\n"):
        return "'%s\\n'" % b.decode("latin-1").rstrip("\r\n")
    return " ".join("'%s'" % chr(x) if 32 <= x < 127 else "%02X" % x for x in b)


class RunCtx(Ctx):
    def __init__(self, win):
        Ctx.__init__(self)
        self.win = win
        self.lock = threading.Lock()
        self.latest = {}
        self.feeds = {}
        self.lines = []
        self.charts = {nid for nid, n in win.doc["nodes"].items() if n["type"] == "ind_chart"}
        self.vals = win.panel.ctl_values
        self.defaults = {nid: n["params"].get("value") for nid, n in win.doc["nodes"].items()}

    def ctl(self, nid):
        v = self.vals.get(nid)
        return self.defaults.get(nid, 0.0) if v is None else v

    def show(self, nid, v):
        with self.lock:
            if nid in self.charts:
                self.feeds.setdefault(nid, []).append(v)
            else:
                self.latest[nid] = v

    def log(self, title, r):
        line = "%-18s → %-22s ← %-16s %5.1f ms" % (title, hexs(r.tx), rx_text(r.rx), r.ms)
        with self.lock:
            self.lines.append(line)

    def note(self, title, text):
        with self.lock:
            self.lines.append("— %s: %s" % (title, text))

    def take(self):
        with self.lock:
            a, b, c = self.latest, self.feeds, self.lines
            self.latest, self.feeds, self.lines = {}, {}, []
        return a, b, c


class EngineThread(QThread):
    done = pyqtSignal(str, str)

    def __init__(self, doc, ctx):
        QThread.__init__(self)
        self.doc = doc
        self.ctx = ctx

    def run(self):
        try:
            Engine(self.doc, self.ctx).run()
            self.done.emit("", "")
        except Abort:
            self.done.emit("abort", "")
        except VIError as e:
            self.done.emit(str(e), e.nid or "")
        except Exception as e:
            self.done.emit(T("Error inesperado: %s") % e, "")


def load_cami(path):
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    if "nodes" not in doc:
        raise ValueError(T("No es un archivo de CamiLab."))
    for n in doc["nodes"].values():
        if n["type"] not in SPECS:
            raise ValueError(T("Bloque desconocido: %s") % n["type"])
        n.setdefault("frame", 0)
        n.setdefault("params", {})
    for w in doc["wires"]:
        w.setdefault("frame", 0)
    p = doc.setdefault("panel", new_panel())
    for k, v in new_panel().items():
        p.setdefault(k, v)
    return doc


def save_json(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


class InstrumentWindow(QMainWindow):
    def __init__(self, app, path=None, doc=None, project=None, title=None):
        QMainWindow.__init__(self)
        self.app = app
        self.path = path
        self.project = project
        self.untitled = title or T("Sin título")
        self.doc = doc if doc is not None else new_doc()
        self.dirty = False
        self.thread = None
        self.ctx = None
        self.setWindowIcon(app_icon())
        self.resize(1250, 800)

        self.diagram = Diagram(self.doc)
        self.panel = Panel(self)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.panel, T("Panel frontal"))
        self.tabs.addTab(self.diagram.view, T("Diagrama de bloques"))
        self.setCentralWidget(self.tabs)

        self.pal_stack = QStackedWidget()
        self.ppal = PanelPalette()
        self.dpal = Palette()
        self.pal_stack.addWidget(self.ppal)
        self.pal_stack.addWidget(self.dpal)
        self.dock_pal = QDockWidget(T("Paleta"), self)
        self.dock_pal.setWidget(self.pal_stack)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_pal)

        self.helpbox = QTextBrowser()
        self.dock_help = QDockWidget(T("Ayuda contextual"), self)
        self.dock_help.setWidget(self.helpbox)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock_help)

        mon = QWidget()
        ml = QVBoxLayout(mon)
        ml.setContentsMargins(2, 2, 2, 2)
        self.monitor = QPlainTextEdit()
        self.monitor.setReadOnly(True)
        self.monitor.setMaximumBlockCount(3000)
        f = QFont("Consolas")
        f.setStyleHint(QFont.Monospace)
        f.setPointSize(9)
        self.monitor.setFont(f)
        self.monitor.setObjectName("monitor")
        row = QHBoxLayout()
        self.ck_pause = QCheckBox(T("Pausar"))
        bclr = QPushButton(T("Limpiar"))
        bclr.clicked.connect(self.monitor.clear)
        row.addWidget(QLabel(T("Comando enviado (hex) y respuesta de la tarjeta, como los ve el "
                               "puerto serie.")))
        row.addStretch(1)
        row.addWidget(self.ck_pause)
        row.addWidget(bclr)
        ml.addLayout(row)
        ml.addWidget(self.monitor)
        self.dock_mon = QDockWidget(T("Monitor del protocolo"), self)
        self.dock_mon.setWidget(mon)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock_mon)

        self.st = QLabel("")
        self.statusBar().addPermanentWidget(self.st)

        self.make_actions()
        self.tabs.currentChanged.connect(self.tab_changed)
        self.diagram.changed.connect(self.set_modified)
        self.diagram.help.connect(self.show_help)
        self.dpal.hover.connect(self.show_help)
        self.dpal.add.connect(self.diagram.add_center)
        self.diagram.status.connect(lambda m: self.statusBar().showMessage(m, 5000))
        self.diagram.panel_add.connect(self.panel.adopt)
        self.diagram.panel_remove.connect(self.panel.remove_item)
        self.diagram.panel_update.connect(self.panel.update_item)
        self.flush_timer = QTimer(self)
        self.flush_timer.setInterval(40)
        self.flush_timer.timeout.connect(self.flush)

        self.panel.rebuild()
        self.tab_changed(0)
        self.set_modified(False)
        self.show_help(T("Pasa el mouse sobre un bloque o una terminal para ver qué hace."))
        QTimer.singleShot(0, self.diagram.fit)

    def make_actions(self):
        tb = self.addToolBar(T("Ejecución"))
        tb.setMovable(False)
        self.a_run = QAction("▶  " + T("Ejecutar"), self)
        self.a_run.setShortcut("Ctrl+R")
        self.a_run.triggered.connect(self.run)
        self.a_stop = QAction("■  " + T("Abortar"), self)
        self.a_stop.setShortcut("Ctrl+.")
        self.a_stop.triggered.connect(self.abort)
        self.a_stop.setEnabled(False)
        self.a_swap = QAction(T("Panel ⇄ Diagrama"), self)
        self.a_swap.setShortcut("Ctrl+E")
        self.a_swap.triggered.connect(lambda: self.tabs.setCurrentIndex(1 - self.tabs.currentIndex()))
        self.a_cfg = QAction(T("Configurar panel..."), self)
        self.a_cfg.triggered.connect(self.panel.config)
        self.a_fit = QAction(T("Ajustar vista"), self)
        self.a_fit.triggered.connect(self.diagram.fit)
        for a in (self.a_run, self.a_stop, None, self.a_swap, self.a_cfg, self.a_fit):
            if a is None:
                tb.addSeparator()
            else:
                tb.addAction(a)
        mb = self.menuBar()
        m = mb.addMenu(T("Archivo"))
        for txt, key, fn in ((T("Nuevo instrumento"), "Ctrl+N", lambda: self.app.new_vi()),
                             (T("Nuevo proyecto"), None, lambda: self.app.new_project()),
                             (T("Abrir..."), "Ctrl+O", lambda: self.app.open_dialog(self)),
                             (T("Guardar"), "Ctrl+S", self.save),
                             (T("Guardar como..."), "Ctrl+Shift+S", self.save_as)):
            a = m.addAction(txt)
            if key:
                a.setShortcut(key)
            a.triggered.connect(fn)
        ex = m.addMenu(T("Ejemplos"))
        for name, fn in EXAMPLES:
            ex.addAction(T(name)).triggered.connect(lambda _c=False, n=name, f=fn:
                                                     self.app.open_example(n, f))
        m.addSeparator()
        m.addAction(T("Inicio de CamiLab")).triggered.connect(self.app.show_home)
        m.addAction(T("Cerrar")).triggered.connect(self.close)
        m = mb.addMenu(T("Editar"))
        a = m.addAction(T("Eliminar selección"))
        a.triggered.connect(self.diagram.delete_selected)
        m = mb.addMenu(T("Operar"))
        m.addAction(self.a_run)
        m.addAction(self.a_stop)
        m = mb.addMenu(T("Ver"))
        m.addAction(self.a_swap)
        th = m.addMenu(T("Tema"))
        for k, nm in THEME_NAMES:
            a = th.addAction(T(nm))
            a.triggered.connect(lambda _c=False, k=k: self.app.apply_theme(k))
        for d in (self.dock_pal, self.dock_help, self.dock_mon):
            m.addAction(d.toggleViewAction())
        m = mb.addMenu(T("Herramientas"))
        m.addAction(T("Asociar archivos .cami / .camp")).triggered.connect(
            lambda: self.app.associate(self))
        lang = m.addMenu(T("Idioma"))
        for k, nm in LANGS:
            a = lang.addAction(nm)
            a.setCheckable(True)
            a.setChecked(k == lv_hub_lang.LANG)
            a.triggered.connect(lambda _c=False, k=k: self.app.set_lang(k, self))

    def tab_changed(self, i):
        self.pal_stack.setCurrentIndex(i)
        self.dock_pal.setWindowTitle(T("Paleta del panel") if i == 0 else T("Paleta de bloques"))
        self.a_cfg.setVisible(i == 0)
        self.a_fit.setVisible(i == 1)
        if i == 0:
            self.show_help(T("Arrastra controles e indicadores a una casilla. Clic derecho en "
                             "un objeto: propiedades, tamaño o eliminar. Arrastra un objeto "
                             "para moverlo. Doble clic en el título para configurar el panel."))
        else:
            self.show_help(T("Arrastra bloques desde la paleta. Para cablear, arrastra desde una "
                             "terminal hasta otra. Supr borra lo seleccionado. Ctrl + rueda "
                             "hace zoom. Clic derecho en un bloque: crear constante, control "
                             "o indicador."))

    def show_help(self, text):
        if " — " in text:
            a, b = text.split(" — ", 1)
            self.helpbox.setHtml("<h3>%s</h3><p>%s</p>" % (a, b.replace("\n", "<br>")))
        else:
            self.helpbox.setHtml("<p>%s</p>" % text)

    def name(self):
        return os.path.basename(self.path) if self.path else self.untitled + EXT_VI

    def set_modified(self, on=True):
        self.dirty = on
        proj = ("  [%s]" % self.project.name()) if self.project else ""
        self.setWindowTitle("%s%s%s — %s" % (self.name(), " *" if on else "", proj, APP))

    def new_terminal(self, tid):
        r = self.diagram.scene.itemsBoundingRect()
        x = (r.right() + 40) if self.doc["nodes"] else 40
        y = r.top() if self.doc["nodes"] else 40
        n = sum(1 for nd in self.doc["nodes"].values() if SPECS[nd["type"]].kind in ("ctl", "ind"))
        return self.diagram.add_block(tid, QPointF(x, y + 50 * (n % 8)))

    def show_in_diagram(self, nid):
        self.tabs.setCurrentIndex(1)
        self.diagram.scene.clearSelection()
        it = self.diagram.items.get(nid)
        if it:
            it.setSelected(True)
            self.diagram.view.ensureVisible(it)

    def save(self):
        if not self.path:
            return self.save_as()
        try:
            save_json(self.doc, self.path)
        except OSError as e:
            QMessageBox.warning(self, APP, T("No se pudo guardar: %s") % e)
            return False
        self.set_modified(False)
        self.statusBar().showMessage(T("Guardado: %s") % self.path, 4000)
        if self.project:
            self.project.add_instrument(self.path)
        return True

    def save_as(self):
        start = self.path or os.path.join(self.project.folder() if self.project else
                                          os.path.expanduser("~"), self.untitled + EXT_VI)
        p, _f = QFileDialog.getSaveFileName(self, T("Guardar instrumento"), start,
                                            T("Instrumento CamiLab") + " (*%s)" % EXT_VI)
        if not p:
            return False
        if not p.lower().endswith(EXT_VI):
            p += EXT_VI
        self.path = p
        return self.save()

    def run(self):
        if self.thread is not None:
            return
        self.diagram.clear_errors()
        self.panel.capture()
        self.panel.set_running(True)
        self.diagram.set_locked(True)
        self.ctx = RunCtx(self)
        self.ctx.project_port = self.project.port() if self.project else ""
        self.thread = EngineThread(copy.deepcopy(self.doc), self.ctx)
        self.thread.done.connect(self.finished)
        self.a_run.setEnabled(False)
        self.a_stop.setEnabled(True)
        self.st.setText("●  " + T("Ejecutando"))
        self.st.setObjectName("running")
        self.st.setStyle(self.st.style())
        self.monitor.appendPlainText("=== %s  %s ===" % (T("Ejecutar"), time.strftime("%H:%M:%S")))
        self.flush_timer.start()
        self.thread.start()

    def abort(self):
        if self.ctx:
            self.ctx.stop_flag.set()

    def flush(self):
        if not self.ctx:
            return
        latest, feeds, lines = self.ctx.take()
        self.panel.show_values(latest, feeds)
        if lines and not self.ck_pause.isChecked():
            if len(lines) > 300:
                lines = [T("... %d líneas omitidas ...") % (len(lines) - 300)] + lines[-300:]
            self.monitor.appendPlainText("\n".join(lines))

    def finished(self, err, nid):
        self.flush()
        self.flush_timer.stop()
        self.thread.wait(1000)
        self.thread = None
        self.ctx = None
        self.panel.set_running(False)
        self.diagram.set_locked(False)
        self.a_run.setEnabled(True)
        self.a_stop.setEnabled(False)
        self.st.setText("")
        if err == "abort":
            self.statusBar().showMessage(T("Abortado."), 5000)
            return
        if not err:
            self.statusBar().showMessage(T("Terminó sin errores."), 5000)
            return
        if nid:
            self.tabs.setCurrentIndex(1)
            self.diagram.mark_error(nid)
        self.monitor.appendPlainText("!!! " + err)
        QMessageBox.warning(self, APP, err)

    def closeEvent(self, e):
        if self.thread is not None:
            self.abort()
            self.thread.wait(3000)
        if self.dirty:
            r = QMessageBox.question(self, APP, T("¿Guardar los cambios de %s?") % self.name(),
                                     QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if r == QMessageBox.Cancel or (r == QMessageBox.Save and not self.save()):
                e.ignore()
                return
        self.app.forget(self)
        e.accept()


class IdentThread(QThread):
    done = pyqtSignal(object, str)

    def __init__(self, port):
        QThread.__init__(self)
        self.port = port

    def run(self):
        try:
            if self.port.upper() == "SIM":
                w = lv_wire.Wire(transport=FakeSerial(), timeout=0.5)
            else:
                w = lv_wire.Wire(self.port, timeout=1.0)
            d = w.identity()
            w.close()
            if not d or "n" not in d:
                raise ValueError(T("La tarjeta no respondió a la identidad (0xEF)."))
            self.done.emit(d, "")
        except Exception as e:
            self.done.emit(None, str(e))


def board_html(d):
    b = d["board"]
    vref = VREF.get(b, DEFAULT_VREF)
    n = d["n"]
    pins = PINS.get(b, {})
    rows = []
    for k, name in (("ai", T("Entradas analógicas (AI)")), ("di", T("Entradas digitales (DI)")),
                    ("do", T("Salidas digitales (DO)")), ("ao", T("Salidas analógicas (AO, DAC)")),
                    ("pwm", "PWM")):
        cnt = n.get(k) or 0
        if not cnt:
            rows.append("<tr><td><b>%s</b></td><td>—</td></tr>" % name)
            continue
        lst = ", ".join("%s%d = %s" % (k.upper(), i, pins.get(k, [])[i] if i < len(pins.get(k, []))
                                       else "?") for i in range(cnt))
        rows.append("<tr><td><b>%s</b></td><td>%s</td></tr>" % (name, lst))
    return ("<h3>%s</h3><p>%s %s · Vref <b>%.1f V</b></p>"
            "<p>%s</p><table cellspacing=4>%s</table>") % (
        T(BOARD_NAMES.get(b, b)), T("Firmware"), "%s %s" % (d["variant"], d["version"]), vref,
        T("El ADC convierte de 0 a %.1f V en 0 a 4095 cuentas: cada cuenta vale %.2f mV. "
          "El DAC y el PWM son de 8 bits: 256 pasos de %.1f mV.") % (
            vref, vref / 4095 * 1000, vref / 255 * 1000),
        "".join(rows))


class ProjectWindow(QMainWindow):
    def __init__(self, app, path=None):
        QMainWindow.__init__(self)
        self.app = app
        self.path = path
        self.data = {"camilab_project": 1, "name": T("Mi proyecto"), "port": "SIM",
                     "instruments": [], "notes": ""}
        if path:
            with open(path, encoding="utf-8") as f:
                self.data.update(json.load(f))
        self.setWindowIcon(app_icon(True))
        self.resize(820, 640)
        w = QWidget()
        w.setObjectName("panel")
        self.setCentralWidget(w)
        lay = QVBoxLayout(w)
        g = QGroupBox(T("Proyecto"))
        f = QFormLayout(g)
        self.ed_name = QLineEdit(self.data["name"])
        f.addRow(T("Nombre"), self.ed_name)
        lay.addWidget(g)
        g = QGroupBox(T("Tarjeta"))
        v = QVBoxLayout(g)
        hl = QHBoxLayout()
        self.cb_port = QComboBox()
        self.cb_port.setEditable(True)
        b1 = QPushButton(T("Actualizar"))
        b2 = QPushButton(T("Probar conexión"))
        hl.addWidget(QLabel(T("Puerto")))
        hl.addWidget(self.cb_port, 1)
        hl.addWidget(b1)
        hl.addWidget(b2)
        v.addLayout(hl)
        v.addWidget(QLabel(T("Los bloques 'Abrir puerto' con puerto (proyecto) usan este.")))
        self.info = QTextBrowser()
        self.info.setMinimumHeight(150)
        self.info.setHtml(T("Presiona 'Probar conexión' para ver qué tarjeta es, su Vref y qué "
                            "pin físico corresponde a cada canal."))
        v.addWidget(self.info)
        lay.addWidget(g)
        g = QGroupBox(T("Instrumentos (.cami)"))
        hl = QHBoxLayout(g)
        self.lst = QListWidget()
        hl.addWidget(self.lst, 1)
        bv = QVBoxLayout()
        for txt, fn in ((T("Nuevo"), self.new_vi), (T("Agregar existente..."), self.add_existing),
                        (T("Abrir"), self.open_sel), (T("Quitar de la lista"), self.remove_sel)):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            bv.addWidget(b)
        bv.addStretch(1)
        hl.addLayout(bv)
        lay.addWidget(g, 1)
        g = QGroupBox(T("Notas"))
        vl = QVBoxLayout(g)
        self.notes = QPlainTextEdit(self.data.get("notes", ""))
        self.notes.setMaximumHeight(90)
        vl.addWidget(self.notes)
        lay.addWidget(g)
        mb = self.menuBar()
        m = mb.addMenu(T("Archivo"))
        for txt, key, fn in ((T("Guardar proyecto"), "Ctrl+S", self.save),
                             (T("Guardar proyecto como..."), "Ctrl+Shift+S", self.save_as)):
            a = m.addAction(txt)
            a.setShortcut(key)
            a.triggered.connect(fn)
        m.addAction(T("Inicio de CamiLab")).triggered.connect(self.app.show_home)
        m.addAction(T("Cerrar")).triggered.connect(self.close)
        b1.clicked.connect(self.scan)
        b2.clicked.connect(self.probe)
        self.lst.itemDoubleClicked.connect(lambda _i: self.open_sel())
        self.ed_name.textChanged.connect(self.touch)
        self.notes.textChanged.connect(self.touch)
        self.cb_port.currentTextChanged.connect(self.touch)
        self.scan()
        self.refresh_list()
        self.dirty = False
        self.title()

    def name(self):
        return self.ed_name.text() or T("Proyecto")

    def folder(self):
        return os.path.dirname(self.path) if self.path else os.path.expanduser("~")

    def port(self):
        d = self.cb_port.currentData()
        txt = self.cb_port.currentText().strip()
        if d and self.cb_port.itemText(self.cb_port.currentIndex()) == txt:
            return d
        return txt or "SIM"

    def touch(self, *_a):
        self.dirty = True
        self.title()

    def title(self):
        self.setWindowTitle("%s%s — %s" % (os.path.basename(self.path) if self.path else
                                           self.name() + EXT_PROJ, " *" if self.dirty else "", APP))

    def scan(self):
        cur = self.data.get("port", "SIM")
        self.cb_port.blockSignals(True)
        self.cb_port.clear()
        self.cb_port.addItem(T("SIM (tarjeta simulada)"), "SIM")
        for p in lv_core.list_ports():
            self.cb_port.addItem(p["port"] + ("  —  " + p["label"] if p["label"] else ""), p["port"])
        i = self.cb_port.findData(cur)
        if i >= 0:
            self.cb_port.setCurrentIndex(i)
        else:
            self.cb_port.setEditText(cur)
        self.cb_port.blockSignals(False)

    def probe(self):
        self.info.setHtml(T("Conectando con %s (la tarjeta se reinicia, ~2 s)...") % self.port())
        self.th = IdentThread(self.port())
        self.th.done.connect(self.probed)
        self.th.start()

    def probed(self, d, err):
        if d is None:
            self.info.setHtml("<p style='color:#a01010'><b>%s</b></p>" % err)
        else:
            self.info.setHtml(board_html(d))

    def abs_paths(self):
        base = self.folder()
        return [os.path.normpath(os.path.join(base, p)) for p in self.data["instruments"]]

    def refresh_list(self):
        self.lst.clear()
        for rel, ab in zip(self.data["instruments"], self.abs_paths()):
            it = QListWidgetItem(rel + ("" if os.path.isfile(ab) else "   " + T("(no existe)")))
            it.setData(Qt.UserRole, ab)
            self.lst.addItem(it)

    def add_instrument(self, path):
        base = self.folder()
        try:
            rel = os.path.relpath(path, base)
        except ValueError:
            rel = path
        if rel not in self.data["instruments"]:
            self.data["instruments"].append(rel)
            self.refresh_list()
            self.touch()

    def new_vi(self):
        if not self.path:
            QMessageBox.information(self, APP, T("Guarda primero el proyecto para saber en qué "
                                                 "carpeta van sus instrumentos."))
            if not self.save_as():
                return
        self.app.new_vi(project=self)

    def add_existing(self):
        paths, _f = QFileDialog.getOpenFileNames(self, T("Agregar instrumentos"), self.folder(),
                                                 T("Instrumento CamiLab") + " (*%s)" % EXT_VI)
        for p in paths:
            self.add_instrument(p)

    def open_sel(self):
        it = self.lst.currentItem()
        if it:
            self.app.open_path(it.data(Qt.UserRole), project=self)

    def remove_sel(self):
        r = self.lst.currentRow()
        if r >= 0:
            del self.data["instruments"][r]
            self.refresh_list()
            self.touch()

    def collect(self):
        self.data["name"] = self.ed_name.text()
        self.data["port"] = self.port()
        self.data["notes"] = self.notes.toPlainText()
        return self.data

    def save(self):
        if not self.path:
            return self.save_as()
        try:
            save_json(self.collect(), self.path)
        except OSError as e:
            QMessageBox.warning(self, APP, T("No se pudo guardar: %s") % e)
            return False
        self.dirty = False
        self.title()
        return True

    def save_as(self):
        old = self.abs_paths()
        p, _f = QFileDialog.getSaveFileName(self, T("Guardar proyecto"),
                                            os.path.join(self.folder(), self.name() + EXT_PROJ),
                                            T("Proyecto CamiLab") + " (*%s)" % EXT_PROJ)
        if not p:
            return False
        if not p.lower().endswith(EXT_PROJ):
            p += EXT_PROJ
        self.path = p
        self.data["instruments"] = []
        for ab in old:
            self.add_instrument(ab)
        return self.save()

    def closeEvent(self, e):
        if self.dirty:
            r = QMessageBox.question(self, APP, T("¿Guardar los cambios de %s?") % self.name(),
                                     QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if r == QMessageBox.Cancel or (r == QMessageBox.Save and not self.save()):
                e.ignore()
                return
        self.app.forget(self)
        e.accept()


class Home(QWidget):
    def __init__(self, app):
        QWidget.__init__(self)
        self.app = app
        self.setObjectName("panel")
        self.setWindowTitle(APP)
        self.setWindowIcon(app_icon())
        lay = QHBoxLayout(self)
        left = QVBoxLayout()
        logo = QLabel()
        logo.setPixmap(app_icon().pixmap(96, 96))
        t = QLabel(APP)
        t.setStyleSheet("font-size:30px;font-weight:bold;")
        s = QLabel(T("Instrumentación de bajo costo · Tesla Lab · Universidad Galileo"))
        s.setWordWrap(True)
        left.addWidget(logo)
        left.addWidget(t)
        left.addWidget(s)
        for txt, fn in ((T("Nuevo instrumento") + " (%s)" % EXT_VI, lambda: app.new_vi()),
                        (T("Nuevo proyecto") + " (%s)" % EXT_PROJ, lambda: app.new_project()),
                        (T("Abrir..."), lambda: app.open_dialog(self)),
                        (T("Asociar archivos .cami / .camp"), lambda: app.associate(self))):
            b = QPushButton(txt)
            b.setMinimumHeight(34)
            b.clicked.connect(fn)
            left.addWidget(b)
        h2 = QHBoxLayout()
        h2.addWidget(QLabel(T("Tema")))
        ct = QComboBox()
        for k, nm in THEME_NAMES:
            ct.addItem(T(nm), k)
        ct.setCurrentIndex(max(0, ct.findData(TH.get("name", "light"))))
        ct.currentIndexChanged.connect(lambda _i: app.apply_theme(ct.currentData()))
        h2.addWidget(ct)
        left.addLayout(h2)
        hl = QHBoxLayout()
        hl.addWidget(QLabel(T("Idioma")))
        cb = QComboBox()
        for k, nm in LANGS:
            cb.addItem(nm, k)
        cb.setCurrentIndex(cb.findData(lv_hub_lang.LANG))
        cb.currentIndexChanged.connect(lambda _i: app.set_lang(cb.currentData(), self))
        hl.addWidget(cb)
        left.addLayout(hl)
        left.addStretch(1)
        lay.addLayout(left, 1)
        g = QGroupBox(T("Ejemplos"))
        v = QVBoxLayout(g)
        self.ex = QListWidget()
        for name, fn in EXAMPLES:
            it = QListWidgetItem(T(name))
            it.setData(Qt.UserRole, name)
            self.ex.addItem(it)
        self.ex.itemDoubleClicked.connect(self.open_ex)
        v.addWidget(self.ex)
        v.addWidget(QLabel(T("Doble clic para abrir. Todos corren con la tarjeta simulada.")))
        lay.addWidget(g, 1)
        self.resize(760, 460)

    def open_ex(self, it):
        name = it.data(Qt.UserRole)
        fn = dict(EXAMPLES)[name]
        self.app.open_example(name, fn)

    def closeEvent(self, e):
        self.app.forget(self)
        e.accept()


def launch_cmd():
    if getattr(sys, "frozen", False):
        return [sys.executable]
    exe = sys.executable
    if os.name == "nt" and os.path.basename(exe).lower() == "python.exe":
        alt = os.path.join(os.path.dirname(exe), "pythonw.exe")
        if os.path.isfile(alt):
            exe = alt
    return [exe, os.path.abspath(__file__)]


def ensure_icon(name, ext, size=256):
    p = icon_file(name, ext)
    if p:
        return p
    src = icon_file(name, ".png" if ext == ".ico" else ".ico")
    if not src:
        return None
    im = QImage(src)
    if im.isNull():
        return None
    out = os.path.join(ICON_DIR, name + ext)
    im.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation).save(out)
    return out if os.path.isfile(out) else None


def associate_windows():
    import winreg
    cmd = " ".join('"%s"' % c for c in launch_cmd()) + ' "%1"'
    items = [(EXT_VI, "TeslaLab.CamiLab.Instrument", T("Instrumento CamiLab"), "camilab"),
             (EXT_PROJ, "TeslaLab.CamiLab.Project", T("Proyecto CamiLab"), "camp")]
    missing = []

    def put(path, value):
        k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Software\\Classes\\" + path)
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, value)
        winreg.CloseKey(k)

    for ext, progid, desc, icon in items:
        put(ext, progid)
        put(progid, desc)
        ico = ensure_icon(icon, ".ico")
        if ico:
            put(progid + "\\DefaultIcon", '"%s",0' % ico)
        else:
            missing.append(icon + ".ico")
        put(progid + "\\shell\\open\\command", cmd)
    import ctypes
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
    return missing


def associate_linux():
    home = os.path.expanduser("~")
    share = os.path.join(home, ".local", "share")
    mime_dir = os.path.join(share, "mime", "packages")
    app_dir = os.path.join(share, "applications")
    os.makedirs(mime_dir, exist_ok=True)
    os.makedirs(app_dir, exist_ok=True)
    with open(os.path.join(mime_dir, "camilab.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">\n'
                '  <mime-type type="application/x-cami">\n'
                '    <comment>%s</comment>\n    <glob pattern="*%s"/>\n'
                '    <icon name="application-x-cami"/>\n  </mime-type>\n'
                '  <mime-type type="application/x-camp">\n'
                '    <comment>%s</comment>\n    <glob pattern="*%s"/>\n'
                '    <icon name="application-x-camp"/>\n  </mime-type>\n'
                '</mime-info>\n' % (T("Instrumento CamiLab"), EXT_VI,
                                    T("Proyecto CamiLab"), EXT_PROJ))
    missing = []
    for src, dst in (("camilab", ("apps", "camilab")), ("camilab", ("mimetypes", "application-x-cami")),
                     ("camp", ("mimetypes", "application-x-camp"))):
        png = ensure_icon(src, ".png")
        if not png:
            missing.append(src + ".png")
            continue
        im = QImage(png)
        for sz in (48, 128, 256):
            d = os.path.join(share, "icons", "hicolor", "%dx%d" % (sz, sz), dst[0])
            os.makedirs(d, exist_ok=True)
            im.scaled(sz, sz, Qt.KeepAspectRatio, Qt.SmoothTransformation).save(
                os.path.join(d, dst[1] + ".png"))
    exe = " ".join('"%s"' % c for c in launch_cmd())
    with open(os.path.join(app_dir, "camilab.desktop"), "w", encoding="utf-8") as f:
        f.write("[Desktop Entry]\nType=Application\nName=%s\nComment=%s\nExec=%s %%f\n"
                "Icon=camilab\nTerminal=false\nCategories=Education;Science;Electronics;\n"
                "MimeType=application/x-cami;application/x-camp;\n"
                % (APP, T("Instrumentación de bajo costo"), exe))
    for cmd in (["update-mime-database", os.path.join(share, "mime")],
                ["update-desktop-database", app_dir],
                ["gtk-update-icon-cache", "-f", "-t", os.path.join(share, "icons", "hicolor")],
                ["xdg-mime", "default", "camilab.desktop", "application/x-cami"],
                ["xdg-mime", "default", "camilab.desktop", "application/x-camp"]):
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        except (OSError, subprocess.SubprocessError):
            pass
    return missing


class CamiApp(object):
    def __init__(self):
        self.windows = []
        self.home = None

    def keep(self, w):
        self.windows.append(w)
        w.show()
        w.raise_()
        return w

    def forget(self, w):
        if w in self.windows:
            self.windows.remove(w)
        if w is self.home:
            self.home = None

    def show_home(self):
        if self.home is None:
            self.home = self.keep(Home(self))
        else:
            self.home.show()
            self.home.raise_()

    def new_vi(self, project=None):
        return self.keep(InstrumentWindow(self, project=project))

    def new_project(self):
        return self.keep(ProjectWindow(self))

    def open_example(self, name, fn):
        w = self.keep(InstrumentWindow(self, doc=fn(), title=T(name)))
        w.set_modified(False)
        return w

    def open_dialog(self, parent):
        p, _f = QFileDialog.getOpenFileName(parent, T("Abrir"), os.path.expanduser("~"),
                                            "CamiLab (*%s *%s)" % (EXT_VI, EXT_PROJ))
        if p:
            self.open_path(p)

    def open_path(self, path, project=None):
        path = os.path.abspath(path)
        for w in self.windows:
            if getattr(w, "path", None) == path:
                w.show()
                w.raise_()
                return w
        try:
            if path.lower().endswith(EXT_PROJ):
                return self.keep(ProjectWindow(self, path))
            return self.keep(InstrumentWindow(self, path=path, doc=load_cami(path),
                                              project=project))
        except Exception as e:
            QMessageBox.warning(None, APP, T("No se pudo abrir %s:\n%s") % (path, e))
            return None

    def associate(self, parent):
        try:
            if os.name == "nt":
                missing = associate_windows()
            else:
                missing = associate_linux()
        except Exception as e:
            QMessageBox.warning(parent, APP, T("No se pudieron asociar los archivos: %s") % e)
            return
        msg = T("Listo: los archivos %s y %s se abren con CamiLab.") % (EXT_VI, EXT_PROJ)
        if missing:
            msg += "\n\n" + T("Faltan íconos en la carpeta iconos/: %s. Ponlos y vuelve a "
                              "asociar para que se vean.") % ", ".join(missing)
        QMessageBox.information(parent, APP, msg)

    def apply_theme(self, name):
        set_theme(name)
        cfg_write(theme=name)
        for w in self.windows:
            if isinstance(w, InstrumentWindow):
                w.diagram.scene.setBackgroundBrush(TH["canvas"])
                w.diagram.scene.update()
                w.panel.rebuild()

    def set_lang(self, lang, parent):
        if lang == lv_hub_lang.LANG:
            return
        lv_hub_lang.save(lang)
        QMessageBox.information(parent, APP, T("El idioma cambia la próxima vez que abras "
                                               "CamiLab."))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP)
    app.setStyle("Fusion")
    app.setWindowIcon(app_icon())
    set_theme(cfg_read().get("theme", "light"))
    cami = CamiApp()
    files = [a for a in sys.argv[1:] if not a.startswith("--") and
             a.lower().endswith((EXT_VI, EXT_PROJ))]
    for f in files:
        cami.open_path(f)
    if not cami.windows:
        cami.show_home()
    sys.exit(app.exec_())


EN.update({
    "Tema": "Theme",
    "Claro": "Light",
    "Oscuro": "Dark",
    "Personalizado": "Custom",
    "Sin respuesta de la tarjeta (timeout).": "No answer from the board (timeout).",
    "Identidad": "Identity",
    "Escribir digital": "Digital write",
    "Leer digital": "Digital read",
    "Leer analógico": "Analog read",
    "Escribir analógico": "Analog write",
    "Verdadero": "True",
    "Falso": "False",
    "Etiqueta": "Label",
    "Elegir imagen": "Choose image",
    "(nada: timeout)": "(nothing: timeout)",
    "Se esperaba un número y llegó un arreglo": "Expected a number but got an array",
    "Se esperaba un booleano y llegó un arreglo": "Expected a boolean but got an array",
    "Falta la sesión: cablea 'sesión' desde 'Abrir puerto'.":
        "Missing session: wire 'session' from 'Open port'.",
    "La tarjeta respondió 'X','X': canal inválido o no soportado.":
        "The board answered 'X','X': invalid or unsupported channel.",
    "Abrir puerto": "Open port",
    "Simulador abierto (sin tarjeta).": "Simulator opened (no board).",
    "Cerrar puerto": "Close port",
    "Puerto cerrado.": "Port closed.",
    "Canal no disponible ahora (ADC2 ocupado por el WiFi).":
        "Channel not available now (ADC2 busy with WiFi).",
    "Canal analógico inválido.": "Invalid analog channel.",
    "Eliminar cable": "Delete wire",
    "(proyecto) — el del archivo .camp": "(proyecto) — the one in the .camp file",
    "SIM (tarjeta simulada)": "SIM (simulated board)",
    "Unidades": "Units",
    "Mínimo": "Minimum",
    "Máximo": "Maximum",
    "Valor inicial": "Initial value",
    "Opciones (separadas por ;)": "Options (separated by ;)",
    "Puntos visibles": "Visible points",
    "Decimales": "Decimals",
    "Imágenes": "Images",
    "No se pudo leer la imagen.": "Could not read the image.",
    "Editar texto...": "Edit text...",
    "Tamaño de letra": "Font size",
    "Negrita": "Bold",
    "Eliminar": "Delete",
    "Tamaño (ancho × alto)": "Size (width × height)",
    "Texto:": "Text:",
    "Configurar panel": "Panel settings",
    "Configurar panel...": "Panel settings...",
    "Filas de la cuadrícula": "Grid rows",
    "Columnas de la cuadrícula": "Grid columns",
    "Título": "Title",
    "Imagen del título": "Title image",
    "Mostrar footer": "Show footer",
    "Texto del footer": "Footer text",
    "Imagen del footer": "Footer image",
    "No es un archivo de CamiLab.": "Not a CamiLab file.",
    "Sin título": "Untitled",
    "Panel frontal": "Front panel",
    "Diagrama de bloques": "Block diagram",
    "Paleta": "Palette",
    "Paleta del panel": "Panel palette",
    "Paleta de bloques": "Block palette",
    "Ayuda contextual": "Context help",
    "Pausar": "Pause",
    "Limpiar": "Clear",
    "Monitor del protocolo": "Protocol monitor",
    "Pasa el mouse sobre un bloque o una terminal para ver qué hace.":
        "Hover over a block or a terminal to see what it does.",
    "Ejecución": "Execution",
    "Panel ⇄ Diagrama": "Panel ⇄ Diagram",
    "Ajustar vista": "Fit view",
    "Archivo": "File",
    "Ejemplos": "Examples",
    "Editar": "Edit",
    "Eliminar selección": "Delete selection",
    "Operar": "Operate",
    "Ver": "View",
    "Herramientas": "Tools",
    "Guardar instrumento": "Save instrument",
    "Entradas analógicas (AI)": "Analog inputs (AI)",
    "Entradas digitales (DI)": "Digital inputs (DI)",
    "Salidas digitales (DO)": "Digital outputs (DO)",
    "Salidas analógicas (AO, DAC)": "Analog outputs (AO, DAC)",
    "Mi proyecto": "My project",
    "Proyecto": "Project",
    "Nombre": "Name",
    "Probar conexión": "Test connection",
    "Presiona 'Probar conexión' para ver qué tarjeta es, su Vref y qué pin físico corresponde a cada canal.":
        "Press 'Test connection' to see which board it is, its Vref and which physical pin "
        "belongs to each channel.",
    "Instrumentos (.cami)": "Instruments (.cami)",
    "Agregar instrumentos": "Add instruments",
    "Guardar proyecto": "Save project",
    "Guardar proyecto como...": "Save project as...",
    "Instrumentación de bajo costo · Tesla Lab · Universidad Galileo":
        "Low-cost instrumentation · Tesla Lab · Universidad Galileo",
    "Instrumentación de bajo costo": "Low-cost instrumentation",
    "Instrumento CamiLab": "CamiLab instrument",
    "Proyecto CamiLab": "CamiLab project",
    "Abrir": "Open",
    "Abrir...": "Open...",
    "Listo: los archivos %s y %s se abren con CamiLab.": "Done: %s and %s files open with CamiLab.",
    "El idioma cambia la próxima vez que abras CamiLab.":
        "The language changes the next time you open CamiLab.",
    "Abriendo %s a 115200 baudios. La tarjeta se reinicia: se esperan 2 s antes del primer comando.":
        "Opening %s at 115200 baud. The board resets: waiting 2 s before the first command.",
    "La tarjeta en %s no respondió a la identidad (0xEF).":
        "The board on %s did not answer the identity command (0xEF).",
    "La tarjeta no respondió a la identidad (0xEF).":
        "The board did not answer the identity command (0xEF).",
    "Hay un ciclo de cables (un valor depende de sí mismo). Dentro de un lazo usa un shift register.":
        "There is a wire cycle (a value depends on itself). Inside a loop use a shift register.",
    "El selector del Case no puede ser un arreglo.": "The Case selector cannot be an array.",
    "Un cable une una salida con una entrada.": "A wire joins an output to an input.",
    "No se puede cablear un bloque consigo mismo.": "A block cannot be wired to itself.",
    "Propiedades": "Properties",
    "Propiedades...": "Properties...",
    "Esa casilla ya está ocupada.": "That cell is already taken.",
    "Cambiar imagen...": "Change image...",
    "Ver en el diagrama": "Show in diagram",
    "Elegir...": "Choose...",
    "Quitar": "Remove",
    "Controles": "Controls",
    "Indicadores": "Indicators",
    "Decoración": "Decoration",
    "Comando enviado (hex) y respuesta de la tarjeta, como los ve el puerto serie.":
        "Command sent (hex) and board reply, as the serial port sees them.",
    "Ejecutar": "Run",
    "Abortar": "Abort",
    "Nuevo instrumento": "New instrument",
    "Nuevo proyecto": "New project",
    "Guardar": "Save",
    "Guardar como...": "Save as...",
    "Arrastra controles e indicadores a una casilla. Clic derecho en un objeto: propiedades, tamaño o eliminar. Arrastra un objeto para moverlo. Doble clic en el título para configurar el panel.":
        "Drag controls and indicators into a cell. Right-click an object: properties, size or "
        "delete. Drag an object to move it. Double-click the title to configure the panel.",
    "Arrastra bloques desde la paleta. Para cablear, arrastra desde una terminal hasta otra. Supr borra lo seleccionado. Ctrl + rueda hace zoom. Clic derecho en un bloque: crear constante, control o indicador.":
        "Drag blocks from the palette. To wire, drag from one terminal to another. Delete "
        "removes the selection. Ctrl + wheel zooms. Right-click a block: create constant, "
        "control or indicator.",
    "Guardado: %s": "Saved: %s",
    "Ejecutando": "Running",
    "Abortado.": "Aborted.",
    "Terminó sin errores.": "Finished without errors.",
    "El ADC convierte de 0 a %.1f V en 0 a 4095 cuentas: cada cuenta vale %.2f mV. El DAC y el PWM son de 8 bits: 256 pasos de %.1f mV.":
        "The ADC turns 0 to %.1f V into 0 to 4095 counts: each count is %.2f mV. DAC and PWM "
        "are 8-bit: 256 steps of %.1f mV.",
    "Los bloques 'Abrir puerto' con puerto (proyecto) usan este.":
        "'Open port' blocks set to (proyecto) use this one.",
    "Nuevo": "New",
    "Agregar existente...": "Add existing...",
    "Quitar de la lista": "Remove from list",
    "Guarda primero el proyecto para saber en qué carpeta van sus instrumentos.":
        "Save the project first so its instruments know which folder they go in.",
    "Asociar archivos .cami / .camp": "Associate .cami / .camp files",
    "Doble clic para abrir. Todos corren con la tarjeta simulada.":
        "Double-click to open. All of them run with the simulated board.",
    "Se esperaba un número: %r": "Expected a number: %r",
    "No se pudo escribir %s: %s": "Could not write %s: %s",
    "valor inicial": "initial value",
    "valor anterior": "previous value",
    "valor siguiente": "next value",
    "valor final": "final value",
    "Opción A": "Option A",
    "Opción B": "Option B",
    "Opción C": "Option C",
    "Shift registers": "Shift registers",
    "Terminales de salida": "Output terminals",
    "Tipos incompatibles: %s → %s": "Incompatible types: %s → %s",
    "Agregar shift register": "Add shift register",
    "Quitar shift register": "Remove shift register",
    "Agregar salida": "Add output",
    "Quitar salida": "Remove output",
    "Mostrar caso %s": "Show %s case",
    "Crear constante": "Create constant",
    "Crear control": "Create control",
    "Crear indicador": "Create indicator",
    "Título del panel (doble clic para editar)": "Panel title (double-click to edit)",
    "con imagen": "with image",
    "sin imagen": "no image",
    "La cuadrícula no puede ser más chica que los objetos que ya tiene (mínimo %d × %d).":
        "The grid cannot be smaller than the objects it already holds (minimum %d × %d).",
    "Bloque desconocido: %s": "Unknown block: %s",
    "¿Guardar los cambios de %s?": "Save changes to %s?",
    "Faltan íconos en la carpeta iconos/: %s. Ponlos y vuelve a asociar para que se vean.":
        "Icons missing in the iconos/ folder: %s. Add them and associate again to see them.",
    "N del For Loop debe ser un número.": "The For Loop N must be a number.",
    "El While Loop no tiene cableada su terminal Stop.": "The While Loop Stop terminal is not wired.",
    "Si no se cablea: ": "If not wired: ",
    "Inicio de CamiLab": "CamiLab home",
    "Cerrar": "Close",
    "No se pudo abrir %s:\n%s": "Could not open %s:\n%s",
    "No se pudieron asociar los archivos: %s": "Could not associate the files: %s",
    "salida %d": "output %d",
    "... %d líneas omitidas ...": "... %d lines skipped ...",
    "(no existe)": "(missing)",
    "Abre el puerto serie de la tarjeta (como VISA Open) y pide su identidad (0xEF). Su salida 'sesión' se cablea a todos los bloques de E/S: ese cable marca el orden. Puerto SIM = tarjeta simulada; (proyecto) = el puerto que diga el proyecto .camp.":
        "Opens the board's serial port (like VISA Open) and asks for its identity (0xEF). Its "
        "'session' output is wired to every I/O block: that wire sets the order. Port SIM = "
        "simulated board; (proyecto) = the port set in the .camp project.",
    "sesión": "session",
    "placa": "board",
    "Cierra el puerto (VISA Close). Ponlo al final, fuera del lazo.":
        "Closes the port (VISA Close). Put it at the end, outside the loop.",
    "Salida digital. Manda 0x01 [canal, valor] y espera 'A','A'.":
        "Digital output. Sends 0x01 [channel, value] and expects 'A','A'.",
    "canal": "channel",
    "valor": "value",
    "Entrada digital. Manda 0x02 [canal, 0] y recibe 'A','0' o 'A','1'.":
        "Digital input. Sends 0x02 [channel, 0] and gets 'A','0' or 'A','1'.",
    "Entrada analógica. Manda 0x05 [canal] y recibe un número 0..4095 en texto terminado en salto de línea. voltaje = cuentas × Vref / 4095.":
        "Analog input. Sends 0x05 [channel] and gets a number 0..4095 as text ending in a "
        "newline. voltage = counts × Vref / 4095.",
    "cuentas": "counts",
    "voltaje": "voltage",
    "DAC. Convierte el voltaje a 0..255 y manda 0x06 [canal, código]. Solo ESP32 Wrover y Nucleo tienen DAC.":
        "DAC. Converts the voltage to 0..255 and sends 0x06 [channel, code]. Only ESP32 Wrover "
        "and Nucleo have a DAC.",
    "PWM de 1 kHz. Convierte 0..100 % a 0..255 y manda 0x07 [canal, duty].":
        "1 kHz PWM. Converts 0..100 % to 0..255 and sends 0x07 [channel, duty].",
    "Servo de 50 Hz. Manda 0x08 [canal, ángulo 0..180].": "50 Hz servo. Sends 0x08 [channel, angle 0..180].",
    "ángulo": "angle",
    "Pinta toda la tira NeoPixel. Manda 0x03 [R, G, B].": "Paints the whole NeoPixel strip. Sends 0x03 [R, G, B].",
    "Escribe texto en un LCD I2C de 16x2. Manda 0x09 [dir, col, fila, largo, texto...].":
        "Writes text on a 16x2 I2C LCD. Sends 0x09 [addr, col, row, length, text...].",
    "fila": "row",
    "columna": "column",
    "texto": "text",
    "Dirección I2C": "I2C address",
    "Constante numérica": "Numeric constant",
    "Un número fijo. Doble clic para cambiarlo.": "A fixed number. Double-click to change it.",
    "Numérico": "Numeric",
    "Suma": "Add",
    "resultado": "result",
    "Resta": "Subtract",
    "Multiplicación": "Multiply",
    "División": "Divide",
    "x ÷ y  (NaN si y = 0)": "x ÷ y  (NaN if y = 0)",
    "Valor absoluto": "Absolute value",
    "Raíz cuadrada": "Square root",
    "Redondear": "Round",
    "Entero más cercano": "Nearest integer",
    "Aleatorio": "Random",
    "Número aleatorio entre 0 y 1.": "Random number between 0 and 1.",
    "Escalar (m·x + b)": "Scale (m·x + b)",
    "Convierte una lectura a unidades físicas: y = m·x + b. Ej. LM35: °C = 100 × V.":
        "Turns a reading into physical units: y = m·x + b. E.g. LM35: °C = 100 × V.",
    "Mapear rango": "Map range",
    "Lleva x del rango [entrada mín, entrada máx] al rango [salida mín, salida máx].":
        "Maps x from [in min, in max] to [out min, out max].",
    "entrada mín": "in min",
    "entrada máx": "in max",
    "salida mín": "out min",
    "salida máx": "out max",
    "Mayor que": "Greater than",
    "Compara x con y y da verdadero/falso.": "Compares x with y and gives true/false.",
    "Comparación": "Comparison",
    "Menor que": "Less than",
    "Mayor o igual": "Greater or equal",
    "Menor o igual": "Less or equal",
    "Igual": "Equal",
    "Distinto": "Not equal",
    "En rango": "In range",
    "Verdadero si mín ≤ x ≤ máx.": "True if min ≤ x ≤ max.",
    "mín": "min",
    "máx": "max",
    "Seleccionar": "Select",
    "Si la condición es verdadera sale 'si verdadero'; si no, 'si falso'.":
        "If the condition is true the output is 'if true'; otherwise 'if false'.",
    "condición": "condition",
    "si verdadero": "if true",
    "si falso": "if false",
    "Constante booleana": "Boolean constant",
    "Verdadero o falso fijo. Doble clic para cambiarlo.": "Fixed true or false. Double-click to change it.",
    "Booleano": "Boolean",
    "Y (AND)": "AND",
    "x Y y": "x AND y",
    "O (OR)": "OR",
    "x O y": "x OR y",
    "O exclusivo (XOR)": "Exclusive OR (XOR)",
    "x distinto de y": "x different from y",
    "No (NOT)": "NOT",
    "Invierte el valor.": "Inverts the value.",
    "Tamaño de arreglo": "Array size",
    "Cuántos elementos tiene.": "How many elements it has.",
    "Arreglos": "Arrays",
    "arreglo": "array",
    "Índice de arreglo": "Index array",
    "Elemento en la posición índice (empieza en 0).": "Element at position index (starts at 0).",
    "índice": "index",
    "elemento": "element",
    "Promedio": "Mean",
    "Promedio de los elementos.": "Mean of the elements.",
    "Elemento mayor.": "Largest element.",
    "Elemento menor.": "Smallest element.",
    "Agregar elemento": "Append element",
    "Arreglo con el elemento agregado al final. Con un shift register sirve para ir guardando lecturas.":
        "Array with the element added at the end. With a shift register it keeps a history "
        "of readings.",
    "Esperar (ms)": "Wait (ms)",
    "Espera esos milisegundos. Dentro de un lazo fija el ritmo de muestreo.":
        "Waits that many milliseconds. Inside a loop it sets the sampling rate.",
    "Tiempo": "Timing",
    "Tiempo (s)": "Time (s)",
    "Segundos desde que se presionó Run.": "Seconds since Run was pressed.",
    "segundos": "seconds",
    "Constante de texto": "String constant",
    "Texto fijo. Doble clic para cambiarlo.": "Fixed text. Double-click to change it.",
    "Texto": "Text",
    "Número a texto": "Number to text",
    "Convierte un número a texto con esos decimales.": "Turns a number into text with that many decimals.",
    "decimales": "decimals",
    "Concatenar": "Concatenate",
    "Une dos textos.": "Joins two texts.",
    "Escribir CSV": "Write CSV",
    "Agrega una fila al archivo: tiempo y el valor (o los valores de un arreglo).":
        "Appends a row to the file: time and the value (or the values of an array).",
    "Repite lo de adentro hasta que la terminal Stop (abajo a la derecha) reciba verdadero. 'i' cuenta las iteraciones desde 0.":
        "Repeats what is inside until the Stop terminal (bottom right) gets true. 'i' counts "
        "iterations from 0.",
    "Estructuras": "Structures",
    "Repite N veces. 'i' va de 0 a N−1. Los valores que salen del lazo se juntan en un arreglo (auto-indexado).":
        "Repeats N times. 'i' goes from 0 to N−1. Values leaving the loop are collected into "
        "an array (auto-indexing).",
    "Ejecuta solo uno de sus dos casos según la terminal '?' (verdadero/falso). Usa clic derecho → 'Agregar salida' para sacar valores: cablea la salida en los dos casos.":
        "Runs only one of its two cases depending on the '?' terminal (true/false). Use "
        "right-click → 'Add output' to get values out: wire the output in both cases.",
    "Control numérico": "Numeric control",
    "Terminal de un control del panel frontal: entrega lo que el usuario pone ahí.":
        "Terminal of a front-panel control: gives whatever the user sets there.",
    "Perilla": "Knob",
    "Deslizador": "Slider",
    "Texto de entrada": "Text input",
    "Ring (lista)": "Ring (list)",
    "Selector de color": "Color picker",
    "Interruptor": "Switch",
    "Botón Stop": "Stop button",
    "Pantalla numérica": "Numeric display",
    "Terminal de un indicador del panel frontal: muestra el valor que le llega.":
        "Terminal of a front-panel indicator: shows the value it receives.",
    "Barra / termómetro": "Bar / thermometer",
    "Plot en el tiempo": "Time plot",
    "Gráfica de arreglo": "Array graph",
    "Pantalla de texto": "Text display",
    "Imagen": "Image",
    "Texto libre": "Free text",
    "Leer voltaje (AI)": "Read voltage (AI)",
    "Prender un LED (DO)": "Turn on an LED (DO)",
    "Alarma por umbral": "Threshold alarm",
    "Termómetro LM35 (escala)": "LM35 thermometer (scaling)",
    "Filtro con shift register": "Filter with a shift register",
    "Barrido DAC → curva (For)": "DAC sweep → curve (For)",
    "Data logger CSV": "CSV data logger",
    "Manual / automático (Case)": "Manual / automatic (Case)",
    "Color en NeoPixel": "NeoPixel color",
    "Voltímetro": "Voltmeter",
    "Prender un LED": "Turn on an LED",
    "Termómetro LM35": "LM35 thermometer",
    "Filtro digital (shift register)": "Digital filter (shift register)",
    "Barrido DAC → curva": "DAC sweep → curve",
    "Voltaje": "Voltage",
    "Canal AI": "AI channel",
    "Voltaje vs tiempo": "Voltage vs time",
    "LED en DO0": "LED on DO0",
    "Estado": "State",
    "Umbral": "Threshold",
    "Señal": "Signal",
    "Alarma": "Alarm",
    "Temperatura": "Temperature",
    "Termómetro": "Thermometer",
    "Temperatura vs tiempo": "Temperature vs time",
    "Señal cruda": "Raw signal",
    "α (suavizado)": "α (smoothing)",
    "Señal filtrada": "Filtered signal",
    "Puntos": "Points",
    "Voltaje leído vs paso": "Measured voltage vs step",
    "Datos guardados": "Logged data",
    "Automático": "Automatic",
    "Salida DO0": "DO0 output",
    "DO0 → resistencia de 330 Ω → LED → GND": "DO0 → 330 Ω resistor → LED → GND",
    "AO0 (GPIO26) → AI0 (GPIO36)": "AO0 (GPIO26) → AI0 (GPIO36)",
    "Se guarda en ~/lv_datos.csv": "Saved to ~/lv_datos.csv",
    "Tira NeoPixel en GPIO25 (ESP32) / D6 (UNO)": "NeoPixel strip on GPIO25 (ESP32) / D6 (UNO)",
    "LM35: 10 mV/°C → °C = 100 × V  ·  Vs a 5 V, salida a AI0":
        "LM35: 10 mV/°C → °C = 100 × V  ·  Vs to 5 V, output to AI0",
})




if __name__ == "__main__":
    main()
