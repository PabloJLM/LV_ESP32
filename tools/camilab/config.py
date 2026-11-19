import json
import os
import subprocess
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QIcon, QImage
from PyQt5.QtWidgets import QApplication, QMessageBox

import core
import hub.lang as hlang
from hub.lang import T
from hub.ui import make_icon


APP = "CamiLab"
EXT_VI = ".cami"
EXT_PROJ = ".camp"
PROJ = "(proyecto)"
TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(TOOLS_DIR)
ICON_DIR = os.path.join(REPO, "iconos")
IMAGES_DIR = os.path.join(REPO, "Images")
WIKI_URL = "https://github.com/PabloJLM/LV_ESP32/wiki"


def port_list():
    out = [(PROJ, T("(proyecto) - el del archivo .camp")), ("SIM", T("SIM (tarjeta simulada)"))]
    for p in core.list_ports():
        out.append((p["port"], p["port"] + ("  -  " + p["label"] if p["label"] else "")))
    return out


def fill_ports(c, cur):
    c.clear()
    for k, t in port_list():
        c.addItem(t, k)
    i = c.findData(cur)
    if i >= 0:
        c.setCurrentIndex(i)
    else:
        c.setEditText(cur)


def port_value(c):
    if c.currentText() == c.itemText(c.currentIndex()):
        return c.currentData()
    return c.currentText().strip()


def icon_file(name, ext):
    p = os.path.join(ICON_DIR, name + ext)
    return p if os.path.isfile(p) else None


def side_image():
    for name in ("camilab_side.png", "logo.png"):
        p = os.path.join(IMAGES_DIR, name)
        if os.path.isfile(p):
            return p
    return None


def app_icon(project=False):
    name = "camp" if project else "camilab"
    for ext in (".png", ".ico"):
        p = icon_file(name, ext)
        if p:
            return QIcon(p)
    return QIcon(make_icon("app_camp" if project else "app_camilab", 64))


def cfg_read():
    try:
        with open(hlang._CFG, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def cfg_write(**kw):
    d = cfg_read()
    d.update(kw)
    try:
        with open(hlang._CFG, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1)
    except OSError:
        pass


THEMES = {
    "light": {"bg": "#e4e4e1", "surface": "#f2f2f0", "text": "#1e1e1e", "text2": "#5a5a58",
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
    t["line"] = c["surface"].lighter(160) if dark else c["surface"].darker(128)
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
QTabWidget::pane   { border:1px solid %(line)s; background:%(bg)s; }
QTabBar::tab       { background:%(surface)s; color:%(text)s; padding:6px 14px;
                     border:1px solid %(line)s; border-bottom:none; }
QTabBar::tab:selected { background:%(bg)s; border-top:2px solid %(accent)s; }
QTreeWidget, QListWidget, QTextBrowser, QPlainTextEdit {
                     background:%(input)s; color:%(text)s; border:1px solid %(line)s;
                     selection-background-color:%(accent)s; selection-color:#ffffff; }
QPlainTextEdit#monitor { background:%(screen)s; color:%(signal)s; }
QLabel#status      { color:%(text2)s; padding:2px 4px; }
QLabel#hint        { color:%(text2)s; font-size:11px; }
QGroupBox          { background:%(surface)s; border:1px solid %(line)s; border-radius:3px;
                     margin-top:18px; padding:8px 6px 6px 6px; }
QGroupBox::title   { subcontrol-origin:margin; subcontrol-position:top left;
                     left:4px; padding:0 2px; color:%(text)s; font-weight:bold; }
QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit {
                     background:%(input)s; color:%(text)s;
                     border:1px solid %(line)s; border-radius:3px;
                     padding:2px 4px; min-height:18px; }
QComboBox QAbstractItemView { background:%(input)s; color:%(text)s;
                     selection-background-color:%(accent)s; selection-color:#ffffff; }
QPushButton        { background:%(button)s; color:%(text)s; border:1px solid %(line)s;
                     border-radius:3px; padding:5px 14px; }
QPushButton:hover  { background:%(surface)s; }
QPushButton:pressed, QPushButton:checked {
                     background:%(accent)s; color:#ffffff; border-color:%(accent)s; }
QPushButton#stopbtn { background:%(alert)s; color:#ffffff; font-weight:bold; font-size:14px; }
QPushButton#stopbtn:checked { background:%(lo)s; }
QCheckBox          { color:%(text)s; }
QLabel#lcd         { background:%(screen)s; color:%(signal)s;
                     border:1px solid %(line)s; border-radius:3px;
                     font-family:"Consolas","DejaVu Sans Mono","Courier New",monospace;
                     font-size:40px; font-weight:bold; padding:4px 10px; }
QLabel#readout     { background:%(screen)s; color:%(signal)s;
                     border:1px solid %(line)s; border-radius:3px;
                     font-family:"Consolas","DejaVu Sans Mono","Courier New",monospace;
                     font-size:12px; padding:4px 8px; }
QFrame#pitem       { background:%(surface)s; border:1px solid %(line)s; border-radius:3px; }
QLabel#phead       { font-weight:bold; color:%(text)s; }
QLabel#sideimage  { background:%(bg)s; }
QLabel#freetext    { background:transparent; color:%(text)s; }
QFrame#banner      { background:transparent; }
QLabel#btitle      { font-size:22px; font-weight:bold; color:%(text)s; }
QLabel#hometitle   { font-size:30px; font-weight:bold; color:%(text)s; }
QLabel#homesub     { font-size:13px; color:%(text2)s; }
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


# (texto del menú, script o carpeta en tools/, argumentos)
HERRAMIENTAS = [
    ("Hub de instrumentos", "hub", []),
    ("Flasher (programar placa)", "flasher.py", ["--tool", "flash"]),
]


def python_exe():
    exe = sys.executable
    if os.name == "nt" and os.path.basename(exe).lower() == "python.exe":
        alt = os.path.join(os.path.dirname(exe), "pythonw.exe")
        if os.path.isfile(alt):
            exe = alt
    return exe


def lanzar(script, args, parent=None):
    try:
        subprocess.Popen([python_exe(), os.path.join(TOOLS_DIR, script)] + args, cwd=TOOLS_DIR)
    except OSError as e:
        QMessageBox.warning(parent, APP, T("No se pudo abrir %s:\n%s") % (script, e))


def launch_cmd():
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [python_exe(), os.path.join(TOOLS_DIR, "camilab")]


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
