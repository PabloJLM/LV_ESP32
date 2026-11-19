from PyQt5.QtCore import pyqtSignal, QMimeData, QObject, QRectF, QSize, Qt
from PyQt5.QtGui import QDrag, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import (
    QGraphicsItem, QGraphicsPathItem, QGraphicsScene, QGraphicsView, QLineEdit, QMenu,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from hub.lang import T
from hub.ui import svg_pixmap

from camilab.bloques import CATS, SPECS
from camilab.config import TH
from camilab.documento import (
    add_node, add_wire, compute_parents, is_desc, node_size, ports, remove_node)
from camilab.items import (
    BaseItem, frame_name, GLYPH, MIME, ncases, node_port_pos, NodeItem, PortItem, PropDialog,
    StructItem, WireItem)
from camilab.widgets import REPS


REP_TYPES = ("ctl_num", "ind_num", "ctl_arr_num", "ind_arr_num", "const_num")


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


CAT_ICON = {"LV_ESP32": "cat_io", "Diagnóstico": "cat_diag", "WiFi y FTP": "cat_net",
            "Numérico": "cat_num", "Comparación": "cat_cmp", "Booleano": "cat_bool",
            "Arreglos": "cat_arr", "Tiempo": "cat_time", "Texto": "cat_str",
            "Archivo": "cat_file", "Estructuras": "cat_struct", "Personalizados": "cat_custom"}
ICON = 24


def style_tree(t):
    f = t.font()
    f.setPixelSize(14)
    t.setFont(f)
    t.setIconSize(QSize(ICON, ICON))
    t.setIndentation(14)
    t.setHeaderHidden(True)
    t.setStyleSheet("QTreeWidget::item { padding: 3px 2px; }")


def badge(text, kind):
    pm = QPixmap(ICON, ICON)
    pm.fill(Qt.transparent)
    if not text:
        return QIcon(pm)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    io = kind == "io"
    p.setBrush(TH["io_body"] if io else TH["func"])
    p.setPen(TH["accent"] if io else TH["func_line"])
    p.drawRoundedRect(QRectF(0.5, 0.5, ICON - 1, ICON - 1), 5, 5)
    f = QFont()
    f.setBold(True)
    f.setPixelSize(12 if len(text) <= 2 else 8)
    p.setFont(f)
    p.setPen(TH["accent"] if io else TH["func_text"])
    p.drawText(QRectF(0, 0, ICON, ICON), Qt.AlignCenter, text[:4])
    p.end()
    return QIcon(pm)


class Tree(QTreeWidget):
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


class Palette(QWidget):
    add = pyqtSignal(str)
    hover = pyqtSignal(str)

    def __init__(self):
        QWidget.__init__(self)
        self.find = QLineEdit()
        self.find.setPlaceholderText(T("Buscar"))
        self.find.setClearButtonEnabled(True)
        self.find.textChanged.connect(self.filter)
        self.tree = Tree()
        style_tree(self.tree)
        self.tree.setDragEnabled(True)
        self.tree.setMouseTracking(True)
        self.tree.itemDoubleClicked.connect(self._dbl)
        self.tree.itemClicked.connect(self._click)
        self.tree.itemEntered.connect(self._hover)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(self.find)
        lay.addWidget(self.tree, 1)
        self.fill()

    def fill(self):
        self.tree.clear()
        col = TH["text"].name()
        for cat in CATS:
            top = QTreeWidgetItem([T(cat)])
            top.setFlags(Qt.ItemIsEnabled)
            top.setIcon(0, QIcon(svg_pixmap(CAT_ICON.get(cat, "cat_custom"), ICON, col)))
            f = top.font(0)
            f.setBold(True)
            f.setPixelSize(15)
            top.setFont(0, f)
            self.tree.addTopLevelItem(top)
            for s in SPECS.values():
                if s.cat == cat:
                    it = QTreeWidgetItem([T(s.label)])
                    it.setIcon(0, badge(GLYPH.get(s.tid) or s.sym or "", s.kind))
                    it.setData(0, Qt.UserRole, s.tid)
                    it.setToolTip(0, T(s.doc))
                    top.addChild(it)
        self.filter(self.find.text())

    def filter(self, text):
        q = text.strip().lower()
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            n = 0
            for k in range(top.childCount()):
                it = top.child(k)
                hide = bool(q) and q not in it.text(0).lower()
                it.setHidden(hide)
                n += not hide
            top.setHidden(n == 0)
            top.setExpanded(bool(q))

    def _click(self, it, _c):
        if it.parent() is not None or self.find.text().strip():
            return
        opening = not it.isExpanded()
        for i in range(self.tree.topLevelItemCount()):
            self.tree.topLevelItem(i).setExpanded(False)
        it.setExpanded(opening)
        if opening:
            self.tree.scrollToItem(it, QTreeWidget.PositionAtTop)

    def _dbl(self, it, _c):
        tid = it.data(0, Qt.UserRole)
        if tid:
            self.add.emit(tid)

    def _hover(self, it, _c):
        tid = it.data(0, Qt.UserRole)
        if tid:
            s = SPECS[tid]
            self.hover.emit("%s - %s" % (T(s.label), T(s.doc)))


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
            if self.doc["nodes"][cur]["type"] == "for" and not is_desc(par, b, cur) and b != cur:
                k += 1
            cur = par.get(cur)
        return k

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
        self.link(src.nid, src.name, dst.nid, dst.name)
        self.refresh_visibility()
        self.status.emit("")
        self.changed.emit()

    def exit_case(self, a, b):
        up = set()
        cur = self.parent.get(b)
        while cur is not None:
            up.add(cur)
            cur = self.parent.get(cur)
        cur = self.parent.get(a)
        while cur is not None and cur not in up:
            if self.doc["nodes"][cur]["type"] == "case":
                return cur
            cur = self.parent.get(cur)
        return None

    def link(self, a, ap, b, bp):
        c = self.exit_case(a, b)
        if c is None:
            dn = self.doc["nodes"][b]
            f = dn["params"].get("view", 1) if dn["type"] == "case" and bp.endswith("_i") else 0
            self.put_wire(a, ap, b, bp, f)
            return
        n = self.doc["nodes"][c]
        k = next((w["src"][1] for w in self.doc["wires"]
                  if w["dst"] == [b, bp] and w["src"][0] == c), None)
        if k is None:
            k = "o%d" % int(n["params"].get("outs", 0))
            n["params"]["outs"] = int(n["params"].get("outs", 0)) + 1
            self.items[c].make_ports()
            self.moved(self.items[c])
            self.link(c, k, b, bp)
        self.put_wire(a, ap, c, k + "_i", n["params"].get("view", 1))

    def put_wire(self, a, ap, b, bp, f):
        for wi in list(self.wire_items):
            if wi.w["dst"] == [b, bp] and wi.w.get("frame", 0) == f:
                self.scene.removeItem(wi)
                self.wire_items.remove(wi)
        self.make_wire(add_wire(self.doc, a, ap, b, bp, f))

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
            acts[m.addAction(T("Agregar caso"))] = ("cases", 1)
            if ncases(n) > 2:
                acts[m.addAction(T("Quitar el último caso"))] = ("cases", -1)
            nxt = (n["params"].get("view", 1) + 1) % ncases(n)
            acts[m.addAction(T("Mostrar caso %s") % frame_name(nxt, n))] = ("flip", nxt)
        if s.kind not in ("struct",):
            unw = [(nm, t, lbl) for nm, t, _d, lbl in s.ins if not self.is_wired(nid, nm)]
            if unw:
                sub = m.addMenu(T("Crear constante"))
                sub2 = m.addMenu(T("Crear control"))
                for nm, t, lbl in unw:
                    if t in ("num", "bool", "str"):
                        acts[sub.addAction(T(lbl))] = ("const", nm, t)
                        acts[sub2.addAction(T(lbl))] = ("ctl", nm, t)
            if n["type"] in ("neo_all", "neo_px"):
                acts[m.addAction(T("Crear selector de color"))] = ("color",)
            if s.outs:
                sub = m.addMenu(T("Crear indicador"))
                for nm, t, lbl in s.outs:
                    if t != "ses":
                        acts[sub.addAction(T(lbl))] = ("ind", nm, t, T(lbl))
        if n["type"] in REP_TYPES:
            sub = m.addMenu(T("Representación"))
            for k, name in REPS:
                a = sub.addAction(T(name))
                a.setCheckable(True)
                a.setChecked(n["params"].get("rep", "double") == k)
                acts[a] = ("rep", k)
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
        elif act[0] == "rep":
            self.set_rep(nid, act[1])
        elif act[0] == "cases":
            self.set_cases(nid, ncases(n) + act[1])
        elif act[0] == "flip":
            n["params"]["view"] = act[1]
            self.items[nid].update()
            self.refresh_visibility()
        elif act[0] == "del":
            self.remove_nodes([nid])
        elif act[0] == "color":
            self.create_color(nid)
        else:
            self.create_for(nid, act)

    def create_for(self, nid, act):
        n = self.doc["nodes"][nid]
        kind, port, t = act[0], act[1], act[2]
        pp = node_port_pos(n, port, "out" if kind == "ind" else "in")
        w, _h = node_size(n)
        u8 = {"rep": "byte"} if n["type"] in ("neo_all", "neo_px") and t == "num" else {}
        if kind == "const":
            tid = {"num": "const_num", "bool": "const_bool", "str": "const_str"}[t]
            new = add_node(self.doc, tid, n["x"] - 60, n["y"] + pp.y() - 11, **u8)
            self.doc["nodes"][new]["frame"] = n.get("frame", 0)
            self.make_item(new)
            w_ = add_wire(self.doc, new, "v", nid, port)
        elif kind == "ctl":
            tid = {"num": "ctl_num", "bool": "ctl_bool", "str": "ctl_str"}[t]
            if n["type"] == "open" and port == "port":
                tid = "ctl_port"
            lbl = [l for nm, _t, _d, l in SPECS[n["type"]].ins if nm == port][0]
            new = add_node(self.doc, tid, n["x"] - 80, n["y"] + pp.y() - 13, label=T(lbl),
                           **(dict(u8, max=255.0) if u8 else {}))
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

    def set_rep(self, nid, k):
        n = self.doc["nodes"][nid]
        n["params"]["rep"] = k
        it = self.items[nid]
        it.prepareGeometryChange()
        it.update()
        self.moved(it)
        if SPECS[n["type"]].kind in ("ctl", "ind"):
            self.panel_update.emit(nid)
        self.changed.emit()

    def set_cases(self, nid, cnt):
        n = self.doc["nodes"][nid]
        cnt = max(2, cnt)
        for f in range(cnt, ncases(n)):
            kids = [k for k, p in self.parent.items() if p == nid and
                    self.doc["nodes"][k].get("frame", 0) == f]
            self.remove_nodes(kids)
            for w in list(self.doc["wires"]):
                if w["dst"][0] == nid and w.get("frame", 0) == f:
                    self.remove_wire(w)
        n["params"]["cases"] = cnt
        n["params"]["view"] = min(n["params"].get("view", 1), cnt - 1)
        self.items[nid].update()
        self.refresh_visibility()
        self.changed.emit()

    def create_color(self, nid):
        n = self.doc["nodes"][nid]
        y = n["y"] + node_port_pos(n, "g", "in").y() - 30
        new = add_node(self.doc, "ctl_color", n["x"] - 110, y, label=T("Color"))
        self.doc["nodes"][new]["frame"] = n.get("frame", 0)
        self.make_item(new)
        self.panel_add.emit(new)
        for k in ("r", "g", "b"):
            self.put_wire(new, k, nid, k, 0)
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
