from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import (
    QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPainterPathStroker, QPen, QPolygonF)
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsObject, QGraphicsPathItem, QMenu

from hub.lang import T

from camilab.bloques import SPECS
from camilab.documento import const_text, node_size, ports
from camilab.tema import TH, tcol


MIME = "application/x-camiblock"
TYPE_COL = {"num": QColor("#e07000"), "bool": QColor("#00862b"), "str": QColor("#d0189c"),
            "arr": QColor("#e07000"), "ses": QColor("#6a2fa0"), "any": QColor("#707070")}
TYPE_TAG = {"num": "DBL", "bool": "TF", "str": "abc", "arr": "[DBL]", "any": "VAR"}


def frame_name(f):
    return T("Verdadero") if f else T("Falso")


class PortItem(QGraphicsItem):
    def __init__(self, owner, nid, name, d, side, typ, label):
        QGraphicsItem.__init__(self, owner)
        self.owner = owner
        self.nid, self.name, self.dir, self.side, self.typ, self.label = \
            nid, name, d, side, typ, label
        self.hot = False
        self.setAcceptHoverEvents(True)
        self.setZValue(5)
        self.setToolTip("%s  (%s)" % (label, typ))

    def style(self):
        n = self.name
        if self.owner.kind != "struct":
            return "dot"
        if n in ("i", "N"):
            return "box"
        if n == "stop":
            return "stop"
        if n.startswith("sr"):
            return "sr"
        if n == "sel":
            return "sel"
        if n.startswith("o"):
            return "tun"
        return "dot"

    def boundingRect(self):
        s = self.style()
        if s in ("box", "stop", "sel"):
            return QRectF(-8, -8, 16, 16)
        if s in ("sr", "tun"):
            return QRectF(-6, -7, 12, 14)
        return QRectF(-5, -5, 10, 10)

    def paint(self, p, _o, _w):
        p.setRenderHint(QPainter.Antialiasing)
        s = self.style()
        col = TYPE_COL.get(self.typ, TYPE_COL["any"])
        if s == "box":
            p.setBrush(TH["input"])
            p.setPen(QPen(TH["accent"], 1.5))
            p.drawRect(QRectF(-7, -7, 14, 14))
            f = QFont()
            f.setPixelSize(10)
            f.setBold(True)
            p.setFont(f)
            p.setPen(TH["accent"])
            p.drawText(QRectF(-7, -7, 14, 14), Qt.AlignCenter, self.name)
        elif s == "stop":
            p.setBrush(TH["alert"])
            p.setPen(QPen(TH["alert"].darker(200), 1))
            p.drawEllipse(QRectF(-7, -7, 14, 14))
            p.setBrush(QColor("#ffffff"))
            p.setPen(Qt.NoPen)
            p.drawRect(QRectF(-3, -3, 6, 6))
        elif s == "sel":
            p.setBrush(TH["input"])
            p.setPen(QPen(TYPE_COL["bool"], 1.5))
            p.drawRect(QRectF(-7, -7, 14, 14))
            p.setPen(tcol(TYPE_COL["bool"]))
            p.drawText(QRectF(-7, -7, 14, 14), Qt.AlignCenter, "?")
        elif s in ("sr", "tun"):
            p.setBrush(TH["input"])
            p.setPen(QPen(QColor("#d07000") if s == "sr" else TH["text2"], 1.2))
            p.drawRect(QRectF(-5, -6, 10, 12))
            if s == "sr":
                up = self.name.endswith("_r") or self.name.endswith("_out")
                tri = [QPointF(-3, 2), QPointF(3, 2), QPointF(0, -3)] if up else \
                    [QPointF(-3, -2), QPointF(3, -2), QPointF(0, 3)]
                p.setBrush(QColor("#b06000"))
                p.drawPolygon(QPolygonF(tri))
        else:
            p.setBrush(col if self.hot else TH["input"])
            p.setPen(QPen(col, 1.4))
            p.drawEllipse(QRectF(-4, -4, 8, 8))
        if self.hot:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(TH["accent"], 1.5))
            p.drawRect(self.boundingRect().adjusted(0.5, 0.5, -0.5, -0.5))

    def hoverEnterEvent(self, e):
        self.hot = True
        self.update()
        ed = self.owner.ed
        ed.help.emit("%s - %s  (%s)" % (T(SPECS[ed.doc["nodes"][self.nid]["type"]].label),
                                       self.label, self.typ))

    def hoverLeaveEvent(self, e):
        self.hot = False
        self.update()


def node_port_pos(node, name, d="in"):
    s = SPECS[node["type"]]
    w, h = node_size(node)
    if s.kind == "struct":
        return struct_port_pos(node, name)
    ins = [p[0] for p in s.ins]
    outs = [p[0] for p in s.outs]
    if s.kind == "io":
        if d == "in":
            return QPointF(0, 30 + 16 * ins.index(name))
        return QPointF(w, 30 + 16 * outs.index(name))
    if d == "in":
        return QPointF(0, h * (ins.index(name) + 1) / (len(ins) + 1))
    return QPointF(w, h * (outs.index(name) + 1) / (len(outs) + 1))


def struct_port_pos(node, name):
    w, h = node["w"], node["h"]
    if name == "i":
        return QPointF(16, h - 18)
    if name == "stop":
        return QPointF(w - 18, h - 18)
    if name == "N":
        return QPointF(-4, 18)
    if name == "sel":
        return QPointF(0, h / 2)
    if name.startswith("sr"):
        k = int(name[2:].split("_")[0])
        y = 46 + 28 * k
        suf = name.split("_")[1]
        return {"in": QPointF(-5, y), "l": QPointF(5, y),
                "r": QPointF(w - 5, y), "out": QPointF(w + 5, y)}[suf]
    if name.startswith("o"):
        k = int(name[1:].split("_")[0])
        y = 44 + 26 * k
        return QPointF(w - 5, y) if name.endswith("_i") else QPointF(w + 5, y)
    return QPointF(0, 0)


class BaseItem(QGraphicsObject):
    def __init__(self, ed, nid):
        QGraphicsObject.__init__(self)
        self.ed = ed
        self.nid = nid
        self.kind = SPECS[self.node["type"]].kind
        self.error = False
        self.port_items = {}
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable |
                      QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setPos(self.node["x"], self.node["y"])
        self.make_ports()

    @property
    def node(self):
        return self.ed.doc["nodes"][self.nid]

    def make_ports(self):
        for it in self.port_items.values():
            it.setParentItem(None)
            if it.scene():
                it.scene().removeItem(it)
        self.port_items = {}
        for name, d, side, typ, label in ports(self.node):
            it = PortItem(self, self.nid, name, d, side, typ, T(label))
            it.setPos(node_port_pos(self.node, name, d))
            self.port_items[(d, name)] = it

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.node["x"] = self.pos().x()
            self.node["y"] = self.pos().y()
            self.ed.moved(self)
        return QGraphicsObject.itemChange(self, change, value)

    def hoverEnterEvent(self, e):
        s = SPECS[self.node["type"]]
        self.ed.help.emit("%s - %s" % (T(s.label), T(s.doc)))

    def mouseDoubleClickEvent(self, e):
        self.ed.edit_node(self.nid)

    def contextMenuEvent(self, e):
        self.ed.node_menu(self.nid, e.screenPos())

    def mouseReleaseEvent(self, e):
        QGraphicsObject.mouseReleaseEvent(self, e)
        self.ed.after_move()


class NodeItem(BaseItem):
    def boundingRect(self):
        w, h = node_size(self.node)
        if self.kind in ("ctl", "ind"):
            lw = QFontMetrics(QFont()).width(self.node["params"].get("label", "")) + 6
            ww = max(w, lw)
            return QRectF((w - ww) / 2 - 2, -3, ww + 4, h + 22)
        return QRectF(-3, -3, w + 6, h + 6)

    def paint(self, p, _o, _w):
        p.setRenderHint(QPainter.Antialiasing)
        n = self.node
        s = SPECS[n["type"]]
        w, h = node_size(n)
        sel = self.isSelected()
        R = QRectF(0, 0, w, h)
        f = QFont()
        if self.kind == "io":
            p.setBrush(TH["io_body"])
            p.setPen(QPen(TH["accent"], 1.5))
            p.drawRect(R)
            p.fillRect(QRectF(0, 0, w, 18), TH["accent"])
            f.setPixelSize(11)
            f.setBold(True)
            p.setFont(f)
            p.setPen(QColor("#ffffff"))
            p.drawText(QRectF(4, 0, w - 8, 18), Qt.AlignVCenter | Qt.AlignLeft,
                       "LV  " + T(s.label))
            f.setBold(False)
            f.setPixelSize(10)
            p.setFont(f)
            p.setPen(TH["text"])
            for k, (nm, t, _d, lbl) in enumerate(s.ins):
                p.drawText(QRectF(8, 22 + 16 * k, w / 2, 16), Qt.AlignVCenter | Qt.AlignLeft,
                           T(lbl))
            for k, (nm, t, lbl) in enumerate(s.outs):
                p.drawText(QRectF(w / 2 - 8, 22 + 16 * k, w / 2, 16),
                           Qt.AlignVCenter | Qt.AlignRight, T(lbl))
            if n["type"] == "open":
                p.setPen(TH["text2"])
                p.drawText(QRectF(8, h - 18, w - 16, 16), Qt.AlignVCenter | Qt.AlignLeft,
                           n["params"].get("port", "SIM"))
        elif self.kind == "const":
            t = s.outs[0][1]
            p.setBrush(TH["input"])
            p.setPen(QPen(TYPE_COL[t], 1.5))
            p.drawRect(R)
            f.setPixelSize(11)
            p.setFont(f)
            p.setPen(tcol(TYPE_COL[t]))
            p.drawText(R, Qt.AlignCenter, const_text(n))
        elif self.kind in ("ctl", "ind"):
            t = (s.outs or s.ins)[0][1]
            col = TYPE_COL[t]
            p.setBrush(TH["input"])
            p.setPen(QPen(col, 3.0 if self.kind == "ctl" else 1.4))
            p.drawRect(R.adjusted(1, 1, -1, -1))
            f.setPixelSize(10)
            f.setBold(True)
            p.setFont(f)
            p.setPen(tcol(col))
            p.drawText(QRectF(0, 0, w - 8, h), Qt.AlignCenter, TYPE_TAG[t])
            p.setBrush(col)
            p.setPen(Qt.NoPen)
            if self.kind == "ctl":
                tri = [QPointF(w - 9, h / 2 - 4), QPointF(w - 3, h / 2), QPointF(w - 9, h / 2 + 4)]
            else:
                tri = [QPointF(3, h / 2 - 4), QPointF(9, h / 2), QPointF(3, h / 2 + 4)]
            p.drawPolygon(QPolygonF(tri))
            f.setBold(False)
            f.setPixelSize(11)
            p.setFont(f)
            p.setPen(TH["text"])
            p.drawText(QRectF(-60, h + 1, w + 120, 16), Qt.AlignHCenter | Qt.AlignTop,
                       n["params"].get("label", ""))
        else:
            p.setBrush(TH["func"])
            p.setPen(QPen(TH["func_line"], 1.4))
            p.drawRect(R)
            f.setPixelSize(13 if len(s.sym or "") <= 2 else 10)
            f.setBold(True)
            p.setFont(f)
            p.setPen(TH["func_text"])
            p.drawText(R, Qt.AlignCenter, s.sym or "?")
        if sel or self.error:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(TH["alert"] if self.error else TH["accent"], 2, Qt.DashLine))
            p.drawRect(R.adjusted(-2, -2, 2, 2))


class StructItem(BaseItem):
    B = 8

    def __init__(self, ed, nid):
        self.resizing = False
        self.members = []
        BaseItem.__init__(self, ed, nid)
        self.setZValue(-10)

    def hdr(self):
        w = self.node["w"]
        return QRectF(w / 2 - 75, -10, 150, 20)

    def boundingRect(self):
        return QRectF(-12, -14, self.node["w"] + 24, self.node["h"] + 26)

    def shape(self):
        w, h, b = self.node["w"], self.node["h"], self.B
        path = QPainterPath()
        path.setFillRule(Qt.OddEvenFill)
        path.addRect(QRectF(-2, -2, w + 4, h + 4))
        path.addRect(QRectF(b, b, w - 2 * b, h - 2 * b))
        p2 = QPainterPath()
        p2.addRect(QRectF(w - 16, h - 16, 18, 18))
        if self.node["type"] == "case":
            p2.addRect(self.hdr())
        return path.united(p2)

    def paint(self, p, _o, _w):
        p.setRenderHint(QPainter.Antialiasing)
        n = self.node
        w, h, b = n["w"], n["h"], self.B
        case = n["type"] == "case"
        col = QColor("#5a5a5a") if case else QColor("#8c8c8c")
        p.setPen(Qt.NoPen)
        p.setBrush(col)
        path = QPainterPath()
        path.setFillRule(Qt.OddEvenFill)
        path.addRect(QRectF(0, 0, w, h))
        path.addRect(QRectF(b, b, w - 2 * b, h - 2 * b))
        p.drawPath(path)
        p.setPen(QPen(col.lighter(150), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(QRectF(b, b, w - 2 * b, h - 2 * b))
        if n["type"] == "while" or n["type"] == "for":
            f = QFont()
            f.setPixelSize(10)
            f.setBold(True)
            p.setFont(f)
            p.setPen(QColor("#ffffff"))
            p.drawText(QRectF(14, -1, 120, 10), Qt.AlignLeft | Qt.AlignVCenter,
                       "While Loop" if n["type"] == "while" else "For Loop")
        if case:
            r = self.hdr()
            p.setBrush(TH["input"])
            p.setPen(QPen(TH["text2"], 1.2))
            p.drawRect(r)
            f = QFont()
            f.setPixelSize(12)
            f.setBold(True)
            p.setFont(f)
            p.setPen(tcol(TYPE_COL["bool"]) if n["params"].get("view", 1) else TH["alert"])
            p.drawText(r, Qt.AlignCenter, "◀  %s  ▶" % frame_name(n["params"].get("view", 1)))
        p.setPen(QPen(QColor("#ffffff"), 1.2))
        for k in range(3):
            d = 4 + 4 * k
            p.drawLine(QPointF(w - d, h - 2), QPointF(w - 2, h - d))
        if self.isSelected() or self.error:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(TH["alert"] if self.error else TH["accent"], 2, Qt.DashLine))
            p.drawRect(QRectF(-3, -3, w + 6, h + 6))

    def mousePressEvent(self, e):
        n = self.node
        w, h = n["w"], n["h"]
        pos = e.pos()
        if n["type"] == "case" and self.hdr().contains(pos) and not self.ed.locked:
            n["params"]["view"] = 0 if n["params"].get("view", 1) else 1
            self.update()
            self.ed.refresh_visibility()
            self.ed.changed.emit()
            e.accept()
            return
        if pos.x() > w - 16 and pos.y() > h - 16 and not self.ed.locked:
            self.resizing = True
            self.r0 = (e.scenePos(), w, h)
            e.accept()
            return
        self.members = self.ed.descendants(self.nid)
        self.last = self.pos()
        BaseItem.mousePressEvent(self, e)

    def mouseMoveEvent(self, e):
        if self.resizing:
            p0, w0, h0 = self.r0
            d = e.scenePos() - p0
            self.prepareGeometryChange()
            self.node["w"] = max(140.0, w0 + d.x())
            self.node["h"] = max(100.0, h0 + d.y())
            for it in self.port_items.values():
                it.setPos(struct_port_pos(self.node, it.name))
            self.ed.moved(self)
            self.update()
            return
        BaseItem.mouseMoveEvent(self, e)

    def mouseReleaseEvent(self, e):
        self.resizing = False
        self.members = []
        BaseItem.mouseReleaseEvent(self, e)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged and self.members:
            d = self.pos() - self.last
            self.last = self.pos()
            for it in self.members:
                if not it.isSelected():
                    it.moveBy(d.x(), d.y())
        return BaseItem.itemChange(self, change, value)


class WireItem(QGraphicsPathItem):
    def __init__(self, ed, w):
        QGraphicsPathItem.__init__(self)
        self.ed = ed
        self.w = w
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setZValue(3)
        self.update_path()

    def update_path(self):
        ed = self.ed
        a = ed.items.get(self.w["src"][0])
        b = ed.items.get(self.w["dst"][0])
        if not a or not b:
            return
        pa = a.port_items.get(("out", self.w["src"][1]))
        pb = b.port_items.get(("in", self.w["dst"][1]))
        if not pa or not pb:
            return
        p1, p2 = pa.scenePos(), pb.scenePos()
        dx = max(30.0, abs(p2.x() - p1.x()) / 2)
        path = QPainterPath(p1)
        path.cubicTo(QPointF(p1.x() + dx, p1.y()), QPointF(p2.x() - dx, p2.y()), p2)
        self.setPath(path)
        t = ed.wire_type(self.w)
        width = 3.2 if t == "arr" else (2.6 if t == "ses" else 1.8)
        self.setPen(QPen(TYPE_COL.get(t, TYPE_COL["any"]), width,
                         Qt.DashLine if self.isSelected() else Qt.SolidLine,
                         Qt.RoundCap))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self.update_path()
        return QGraphicsPathItem.itemChange(self, change, value)

    def shape(self):
        s = QPainterPathStroker()
        s.setWidth(8)
        return s.createStroke(self.path())

    def contextMenuEvent(self, e):
        if self.ed.locked:
            return
        m = QMenu()
        a = m.addAction(T("Eliminar cable"))
        if m.exec_(e.screenPos()) == a:
            self.ed.remove_wire(self.w)
