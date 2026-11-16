from PyQt5.QtCore import QMimeData, Qt, pyqtSignal
from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem

from hub.lang import T

from camilab.bloques import CATS, SPECS
from camilab.editor.items import MIME


class Palette(QTreeWidget):
    add = pyqtSignal(str)
    hover = pyqtSignal(str)

    def __init__(self):
        QTreeWidget.__init__(self)
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setMouseTracking(True)
        for cat in CATS:
            top = QTreeWidgetItem([T(cat)])
            top.setFlags(Qt.ItemIsEnabled)
            f = top.font(0)
            f.setBold(True)
            top.setFont(0, f)
            self.addTopLevelItem(top)
            for s in SPECS.values():
                if s.cat == cat:
                    it = QTreeWidgetItem([("%s   %s" % (s.sym, T(s.label))) if s.sym and
                                          s.kind == "func" else T(s.label)])
                    it.setData(0, Qt.UserRole, s.tid)
                    it.setToolTip(0, T(s.doc))
                    top.addChild(it)
            top.setExpanded(cat in ("LV_ESP32", "Estructuras", "Numérico"))
        self.itemDoubleClicked.connect(self._dbl)
        self.itemEntered.connect(self._hover)

    def _dbl(self, it, _c):
        tid = it.data(0, Qt.UserRole)
        if tid:
            self.add.emit(tid)

    def _hover(self, it, _c):
        tid = it.data(0, Qt.UserRole)
        if tid:
            s = SPECS[tid]
            self.hover.emit("%s - %s" % (T(s.label), T(s.doc)))

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
