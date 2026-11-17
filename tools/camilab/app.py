import os
import sys

from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox

import hub.lang as hlang
from hub.lang import T

from camilab import traducciones  # noqa: F401  (registra los textos en inglés)
from camilab.documento import load_cami
from camilab.sistema import associate_linux, associate_windows
from camilab.config import APP, EXT_PROJ, EXT_VI, app_icon, cfg_read, cfg_write
from camilab.inicio import Home
from camilab.tema import TH, set_theme
from camilab.ventana_instrumento import InstrumentWindow
from camilab.ventana_proyecto import ProjectWindow


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
        if lang == hlang.LANG:
            return
        hlang.save(lang)
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
