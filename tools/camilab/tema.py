from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication

from camilab.config import cfg_read


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
QLabel#sideimage  { background:%(bg)s; }
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
