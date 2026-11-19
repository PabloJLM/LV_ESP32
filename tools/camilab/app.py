import os
import sys

from PyQt5.QtCore import QRectF, Qt, QUrl
from PyQt5.QtGui import QColor, QDesktopServices, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QVBoxLayout, QWidget)

import hub.lang as hlang
from hub.lang import T

from camilab import personalizados, traducciones
from camilab.config import (
    APP, app_icon, associate_linux, associate_windows, cfg_read, cfg_write, EXT_PROJ, EXT_VI,
    set_theme, side_image, TH, WIKI_URL)
from camilab.documento import load_cami
from camilab.ventana_instrumento import (
    add_actions, add_examples, add_language, add_theme, add_tools, InstrumentWindow)
from camilab.ventana_proyecto import ProjectWindow


SUBTITULO = "Instrumentación de bajo costo · Tesla Lab · Universidad Galileo"


def _png_luma(pm):
    img = pm.toImage().convertToFormat(pm.toImage().Format_ARGB32)
    img = img.scaled(64, 64, Qt.KeepAspectRatio, Qt.FastTransformation)
    tot, n = 0.0, 0
    for y in range(img.height()):
        for x in range(img.width()):
            c = QColor.fromRgba(img.pixel(x, y))
            if c.alpha() > 128:
                tot += 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
                n += 1
    return tot / n if n else None


class SideImage(QLabel):

    def __init__(self, path):
        QLabel.__init__(self)
        self.setObjectName("sideimage")
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumWidth(240)
        self.original = QPixmap(path) if path else QPixmap()
        self.luma = _png_luma(self.original) if not self.original.isNull() else None

    def resizeEvent(self, e):
        if not self.original.isNull():
            self.setPixmap(self.original.scaled(self.size() * 0.85, Qt.KeepAspectRatio,
                                                Qt.SmoothTransformation))
        QLabel.resizeEvent(self, e)

    def backing(self):
        if self.luma is None or "bg" not in TH:
            return None
        bg = TH["bg"].lightness()
        if abs(bg - self.luma) >= 90:
            return None
        return QColor("#f2f2f2") if self.luma < 128 else QColor("#1c1c1c")

    def paintEvent(self, e):
        pm = self.pixmap()
        col = self.backing()
        if col is not None and pm is not None and not pm.isNull():
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            w = pm.width() / pm.devicePixelRatio()
            h = pm.height() / pm.devicePixelRatio()
            m = 14.0
            r = QRectF((self.width() - w) / 2 - m, (self.height() - h) / 2 - m,
                       w + 2 * m, h + 2 * m)
            p.setPen(Qt.NoPen)
            p.setBrush(col)
            p.drawRoundedRect(r, 10, 10)
            p.end()
        QLabel.paintEvent(self, e)


class Home(QMainWindow):
    def __init__(self, app):
        QMainWindow.__init__(self)
        self.app = app
        self.setWindowTitle(APP)
        self.setWindowIcon(app_icon())
        self.build_menu()
        self.build_body()
        self.resize(860, 480)

    def actions(self):
        app = self.app
        return [(T("Nuevo instrumento") + " (%s)" % EXT_VI, "Ctrl+N", app.new_vi),
                (T("Nuevo proyecto") + " (%s)" % EXT_PROJ, None, app.new_project),
                (T("Abrir..."), "Ctrl+O", lambda: app.open_dialog(self)),
                (T("Asociar archivos .cami / .camp"), None, lambda: app.associate(self))]

    def build_menu(self):
        mb = self.menuBar()
        m = mb.addMenu(T("Archivo"))
        add_actions(m, self.actions())
        m.addSeparator()
        add_examples(m, self.app)
        m.addSeparator()
        m.addAction(T("Salir")).triggered.connect(QApplication.closeAllWindows)

        add_tools(mb.addMenu(T("Herramientas")), self)

        m = mb.addMenu(T("Ayuda"))
        m.addAction(T("Documentación")).triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl(WIKI_URL)))
        m.addAction(T("Acerca de CamiLab")).triggered.connect(
            lambda: QMessageBox.about(self, APP, "<b>%s</b><br>%s" % (APP, T(SUBTITULO))))

        m = mb.addMenu(T("Configuración"))
        add_theme(m, self.app)
        add_language(m, self.app, self)

    def build_body(self):
        logo = QLabel()
        logo.setPixmap(app_icon().pixmap(72, 72))
        title = QLabel(APP)
        title.setObjectName("hometitle")
        sub = QLabel(T(SUBTITULO))
        sub.setObjectName("homesub")
        sub.setWordWrap(True)

        left = QVBoxLayout()
        left.setContentsMargins(36, 0, 12, 0)
        left.setSpacing(8)
        left.addStretch(1)
        for w in (logo, title, sub):
            left.addWidget(w)
        left.addSpacing(14)
        for text, _key, fn in self.actions():
            b = QPushButton(text)
            b.setMinimumHeight(34)
            b.clicked.connect(lambda _c=False, f=fn: f())
            left.addWidget(b)
        left.addStretch(1)
        column = QWidget()
        column.setLayout(left)
        column.setFixedWidth(360)

        body = QWidget()
        body.setObjectName("panel")
        row = QHBoxLayout(body)
        row.addWidget(column)
        row.addWidget(SideImage(side_image()), 1)
        self.setCentralWidget(body)

    def closeEvent(self, e):
        self.app.forget(self)
        e.accept()


class CamiApp(object):
    def __init__(self):
        self.windows = []
        self.home = None
        personalizados.load()

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
                w.dpal.fill()

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
    set_theme(cfg_read().get("theme", "dark"))
    cami = CamiApp()
    files = [a for a in sys.argv[1:] if not a.startswith("--") and
             a.lower().endswith((EXT_VI, EXT_PROJ))]
    for f in files:
        cami.open_path(f)
    if not cami.windows:
        cami.show_home()
    sys.exit(app.exec_())
