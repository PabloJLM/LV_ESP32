import os
import subprocess
import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget

TOOLS = os.path.dirname(os.path.abspath(__file__))

APPS = (
    ("Cargar firmware", ["flasher.py", "--tool", "flash"]),
    ("Hub", ["hub"]),
    ("CamiLab", ["camilab"]),
    ("Tester", ["tester.py"]),
)


def abrir(args):
    subprocess.Popen([sys.executable, os.path.join(TOOLS, args[0])] + args[1:], cwd=TOOLS)


app = QApplication(sys.argv)
app.setWindowIcon(QIcon(os.path.join(os.path.dirname(TOOLS), "iconos", "lanzador.png")))
w = QWidget()
w.setWindowTitle("LV_ESP32")
v = QVBoxLayout(w)
for name, args in APPS:
    b = QPushButton(name)
    b.clicked.connect(lambda _c=False, a=args: abrir(a))
    v.addWidget(b)
w.show()
sys.exit(app.exec_())
