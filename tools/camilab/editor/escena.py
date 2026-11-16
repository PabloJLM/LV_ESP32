from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QGraphicsPathItem, QGraphicsScene, QGraphicsView

from camilab.editor.items import MIME, PortItem
from camilab.tema import TH


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
