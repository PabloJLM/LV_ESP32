import copy
import os
import time

from PyQt5.QtCore import QPointF, Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QAction, QActionGroup, QCheckBox, QDockWidget, QFileDialog, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QPlainTextEdit, QPushButton, QStackedWidget, QTabWidget, QTextBrowser,
    QVBoxLayout, QWidget)

import hub.lang as hlang
from hub.lang import LANGS, T

from camilab import personalizados
from camilab.bloques import SPECS
from camilab.config import APP, app_icon, EXT_VI, HERRAMIENTAS, lanzar, TH, THEME_NAMES
from camilab.diagrama import Diagram, Palette
from camilab.documento import new_doc, save_json
from camilab.ejemplos import EXAMPLE_GROUPS
from camilab.motor import EngineThread, RunCtx
from camilab.panel import Panel, PanelPalette


def _radio(menu, items, actual, al_elegir):
    grupo = QActionGroup(menu)
    for clave, texto in items:
        a = menu.addAction(texto)
        a.setCheckable(True)
        a.setChecked(clave == actual)
        grupo.addAction(a)
        a.triggered.connect(lambda _c=False, k=clave: al_elegir(k))


def add_actions(menu, items):
    for text, key, fn in items:
        a = menu.addAction(text)
        if key:
            a.setShortcut(key)
        a.triggered.connect(lambda _c=False, f=fn: f())


def add_examples(menu, app):
    sub = menu.addMenu(T("Ejemplos"))
    for group, items in EXAMPLE_GROUPS:
        gm = sub.addMenu(T(group))
        for name, fn in items:
            gm.addAction(T(name)).triggered.connect(
                lambda _c=False, n=name, f=fn: app.open_example(n, f))


def add_theme(menu, app):
    sub = menu.addMenu(T("Tema"))
    _radio(sub, [(k, T(nm)) for k, nm in THEME_NAMES], TH.get("name"), app.apply_theme)


def add_language(menu, app, parent):
    sub = menu.addMenu(T("Idioma"))
    _radio(sub, LANGS, hlang.LANG, lambda k: app.set_lang(k, parent))


def add_tools(menu, parent):
    from camilab import personalizados
    menu.addAction(T("Bloques personalizados")).triggered.connect(
        lambda: personalizados.show(parent))
    for texto, script, args in HERRAMIENTAS:
        menu.addAction(T(texto)).triggered.connect(
            lambda _c=False, s=script, a=args: lanzar(s, a, parent))


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
        row.addWidget(QLabel(T("Comandos enviados (hex) y respuestas de la tarjeta.")))
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
        add_actions(m, [(T("Nuevo instrumento"), "Ctrl+N", self.app.new_vi),
                        (T("Nuevo proyecto"), None, self.app.new_project),
                        (T("Abrir..."), "Ctrl+O", lambda: self.app.open_dialog(self)),
                        (T("Guardar"), "Ctrl+S", self.save),
                        (T("Guardar como..."), "Ctrl+Shift+S", self.save_as)])
        add_examples(m, self.app)
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
        add_theme(m, self.app)
        for d in (self.dock_pal, self.dock_help, self.dock_mon):
            m.addAction(d.toggleViewAction())
        m = mb.addMenu(T("Herramientas"))
        m.addAction(T("Bloques personalizados")).triggered.connect(
            lambda: personalizados.show(self))
        m.addAction(T("Asociar archivos .cami / .camp")).triggered.connect(
            lambda: self.app.associate(self))
        add_language(m, self.app, self)

    def tab_changed(self, i):
        self.pal_stack.setCurrentIndex(i)
        self.dock_pal.setWindowTitle(T("Paleta del panel") if i == 0 else T("Paleta de bloques"))
        self.a_cfg.setVisible(i == 0)
        self.a_fit.setVisible(i == 1)
        if i == 0:
            self.show_help(T("Arrastra controles e indicadores a una casilla. Clic derecho: "
                             "propiedades, tamaño o eliminar. Doble clic en el título "
                             "configura el panel."))
        else:
            self.show_help(T("Arrastra bloques desde la paleta y cablea de terminal a "
                             "terminal. Supr borra, Ctrl + rueda hace zoom. Clic derecho en un "
                             "bloque crea constante, control o indicador."))

    def show_help(self, text):
        if " - " in text:
            a, b = text.split(" - ", 1)
            self.helpbox.setHtml("<h3>%s</h3><p>%s</p>" % (a, b.replace("\n", "<br>")))
        else:
            self.helpbox.setHtml("<p>%s</p>" % text)

    def name(self):
        return os.path.basename(self.path) if self.path else self.untitled + EXT_VI

    def set_modified(self, on=True):
        self.dirty = on
        proj = ("  [%s]" % self.project.name()) if self.project else ""
        self.setWindowTitle("%s%s%s - %s" % (self.name(), " *" if on else "", proj, APP))

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
