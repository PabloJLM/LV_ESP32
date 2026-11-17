from PyQt5.QtCore import QObject, QRectF, Qt, pyqtSignal
from PyQt5.QtWidgets import QGraphicsItem, QMenu

from hub.lang import T

from camilab.bloques import SPECS
from camilab.documento import (
    add_node, add_wire, compute_parents, is_desc, node_size, ports, remove_node)
from camilab.editor.dialogos import PropDialog
from camilab.editor.escena import Scene, View
from camilab.editor.items import (
    BaseItem, NodeItem, StructItem, WireItem, frame_name, node_port_pos)


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
        frame = 0
        dn = self.doc["nodes"][dst.nid]
        if dn["type"] == "case" and dst.name.endswith("_i"):
            frame = dn["params"].get("view", 1)
        for wi in list(self.wire_items):
            if wi.w["dst"] == [dst.nid, dst.name] and wi.w.get("frame", 0) == frame:
                self.scene.removeItem(wi)
                self.wire_items.remove(wi)
        w = add_wire(self.doc, src.nid, src.name, dst.nid, dst.name, frame)
        self.make_wire(w)
        self.refresh_visibility()
        self.status.emit("")
        self.changed.emit()

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
            acts[m.addAction(T("Mostrar caso %s") % frame_name(
                0 if n["params"].get("view", 1) else 1))] = ("flip",)
        if s.kind not in ("struct",):
            unw = [(nm, t, lbl) for nm, t, _d, lbl in s.ins if not self.is_wired(nid, nm)]
            if unw:
                sub = m.addMenu(T("Crear constante"))
                sub2 = m.addMenu(T("Crear control"))
                for nm, t, lbl in unw:
                    if t in ("num", "bool", "str"):
                        acts[sub.addAction(T(lbl))] = ("const", nm, t)
                        acts[sub2.addAction(T(lbl))] = ("ctl", nm, t)
            if s.outs:
                sub = m.addMenu(T("Crear indicador"))
                for nm, t, lbl in s.outs:
                    if t != "ses":
                        acts[sub.addAction(T(lbl))] = ("ind", nm, t, T(lbl))
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
        elif act[0] == "flip":
            n["params"]["view"] = 0 if n["params"].get("view", 1) else 1
            self.items[nid].update()
            self.refresh_visibility()
        elif act[0] == "del":
            self.remove_nodes([nid])
        else:
            self.create_for(nid, act)

    def create_for(self, nid, act):
        n = self.doc["nodes"][nid]
        kind, port, t = act[0], act[1], act[2]
        pp = node_port_pos(n, port, "out" if kind == "ind" else "in")
        w, _h = node_size(n)
        if kind == "const":
            tid = {"num": "const_num", "bool": "const_bool", "str": "const_str"}[t]
            new = add_node(self.doc, tid, n["x"] - 60, n["y"] + pp.y() - 11)
            self.doc["nodes"][new]["frame"] = n.get("frame", 0)
            self.make_item(new)
            w_ = add_wire(self.doc, new, "v", nid, port)
        elif kind == "ctl":
            tid = {"num": "ctl_num", "bool": "ctl_bool", "str": "ctl_str"}[t]
            lbl = [l for nm, _t, _d, l in SPECS[n["type"]].ins if nm == port][0]
            new = add_node(self.doc, tid, n["x"] - 80, n["y"] + pp.y() - 13, label=T(lbl))
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
