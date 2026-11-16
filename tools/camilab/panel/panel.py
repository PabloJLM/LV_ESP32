from PyQt5.QtCore import QMimeData, Qt
from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QMenu, QMessageBox, QPushButton, QSpinBox, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget)

from hub.lang import T

from camilab.bloques import CTL_KINDS, IND_KINDS, PANEL_ONLY
from camilab.config import APP
from camilab.panel.widgets import Banner, FreeText, Grid, PItem, PMIME, pick_image


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
