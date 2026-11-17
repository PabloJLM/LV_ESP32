from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QColor, QDesktopServices, QPainter, QPixmap
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
                             QPushButton, QVBoxLayout, QWidget)

from hub.lang import T

from camilab.config import APP, EXT_PROJ, EXT_VI, WIKI_URL, app_icon, side_image
from camilab.menus import add_examples, add_language, add_theme, add_tools
from camilab.tema import TH

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

    def build_menu(self):
        mb = self.menuBar()
        app = self.app

        m = mb.addMenu(T("Archivo"))
        for texto, tecla, fn in (
                (T("Nuevo instrumento") + " (%s)" % EXT_VI, "Ctrl+N", app.new_vi),
                (T("Nuevo proyecto") + " (%s)" % EXT_PROJ, None, app.new_project),
                (T("Abrir..."), "Ctrl+O", lambda: app.open_dialog(self)),
                (T("Asociar archivos .cami / .camp"), None, lambda: app.associate(self))):
            a = m.addAction(texto)
            if tecla:
                a.setShortcut(tecla)
            a.triggered.connect(lambda _c=False, f=fn: f())
        m.addSeparator()
        add_examples(m, app)
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
        cuerpo = QWidget()
        cuerpo.setObjectName("panel")
        fila = QHBoxLayout(cuerpo)

        izq = QVBoxLayout()
        logo = QLabel()
        logo.setPixmap(app_icon().pixmap(96, 96))
        titulo = QLabel(APP)
        titulo.setStyleSheet("font-size:30px;font-weight:bold;")
        sub = QLabel(T(SUBTITULO))
        sub.setWordWrap(True)
        for w in (logo, titulo, sub):
            izq.addWidget(w)
        for texto, fn in ((T("Nuevo instrumento") + " (%s)" % EXT_VI, self.app.new_vi),
                          (T("Nuevo proyecto") + " (%s)" % EXT_PROJ, self.app.new_project),
                          (T("Abrir..."), lambda: self.app.open_dialog(self)),
                          (T("Asociar archivos .cami / .camp"),
                           lambda: self.app.associate(self))):
            b = QPushButton(texto)
            b.setMinimumHeight(34)
            b.clicked.connect(lambda _c=False, f=fn: f())
            izq.addWidget(b)
        izq.addStretch(1)

        izquierda = QWidget()
        izquierda.setLayout(izq)
        izquierda.setFixedWidth(360)
        fila.addWidget(izquierda)
        fila.addWidget(SideImage(side_image()), 1)
        self.setCentralWidget(cuerpo)

    def closeEvent(self, e):
        self.app.forget(self)
        e.accept()
