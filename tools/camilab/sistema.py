import os
import subprocess
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QMessageBox

from hub.lang import T

from camilab.config import APP, EXT_PROJ, EXT_VI, ICON_DIR, TOOLS_DIR, icon_file

# (texto del menú, script o carpeta en tools/, argumentos)
HERRAMIENTAS = [
    ("Hub de instrumentos", "hub", []),
    ("Flasher (programar placa)", "flasher.py", ["--tool", "flash"]),
    ("Probe (prueba del protocolo)", "flasher.py", ["--tool", "probe"]),
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
