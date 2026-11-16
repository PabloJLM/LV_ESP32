import json
import os

from PyQt5.QtGui import QIcon

import hub.lang as hlang
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
    return QIcon(make_icon("bode" if project else "scope", 64))


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
