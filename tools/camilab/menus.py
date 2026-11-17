from PyQt5.QtWidgets import QActionGroup

import hub.lang as hlang
from hub.lang import LANGS, T

from camilab.ejemplos import EXAMPLES
from camilab.sistema import HERRAMIENTAS, lanzar
from camilab.tema import TH, THEME_NAMES


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
    for name, fn in EXAMPLES:
        sub.addAction(T(name)).triggered.connect(
            lambda _c=False, n=name, f=fn: app.open_example(n, f))


def add_theme(menu, app):
    sub = menu.addMenu(T("Tema"))
    _radio(sub, [(k, T(nm)) for k, nm in THEME_NAMES], TH.get("name"), app.apply_theme)


def add_language(menu, app, parent):
    sub = menu.addMenu(T("Idioma"))
    _radio(sub, LANGS, hlang.LANG, lambda k: app.set_lang(k, parent))


def add_tools(menu, parent):
    for texto, script, args in HERRAMIENTAS:
        menu.addAction(T(texto)).triggered.connect(
            lambda _c=False, s=script, a=args: lanzar(s, a, parent))
