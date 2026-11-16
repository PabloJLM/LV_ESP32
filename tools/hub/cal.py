import json
import math
import os
import time

from hub.lang import T

CFG = os.path.join(os.path.expanduser("~"), ".cal_mod.json")
DEFAULT_RREF = 2200.0
FULL_SCALE = 4095.0
MIN_SPAN = 500
OHM_MIN_GAP = 0.05


class CalError(Exception):
    pass


def two_point(c1, r1, c2, r2):
    if abs(c2 - c1) < MIN_SPAN:
        raise CalError(T("Puntos muy juntos: sepáralos al menos %d cuentas (usa ~10 %% y ~90 "
                         "%% del rango).") % MIN_SPAN)
    a = (r2 - r1) / (c2 - c1)
    return a, r1 - a * c1


def ohm_z(counts):
    x = min(max(float(counts), 1.0), FULL_SCALE - 1.0) / FULL_SCALE
    return math.log(x / (1.0 - x))


def fit_gain(pairs):
    sxx = sum(x * x for x, _y in pairs)
    if sxx <= 0.0:
        raise CalError(T("Ningún punto tiene tensión en el pin para calcular el factor."))
    return sum(x * y for x, y in pairs) / sxx


class Calibration(object):

    def __init__(self, path=CFG):
        self.path = path
        self.boards = {}
        self.load()

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                b = json.load(f).get("boards", {})
            self.boards = b if isinstance(b, dict) else {}
        except (OSError, ValueError, AttributeError):
            self.boards = {}

    def save(self):
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"version": 1, "boards": self.boards}, f, indent=1)
            os.replace(tmp, self.path)
        except OSError as e:
            raise CalError(T("No se pudo guardar la calibración (sigue activa hasta cerrar "
                           "el Hub): %s") % e)

    def _get(self, board):
        return self.boards.get(board) or {}

    def _make(self, board):
        return self.boards.setdefault(board, {})

    def vref(self, board, nominal):
        v = self._get(board).get("vref")
        return float(v) if v else float(nominal)

    def set_vref(self, board, v):
        if not 1.0 <= v <= 6.0:
            raise CalError(T("Vref fuera de rango (1 a 6 V)."))
        self._make(board)["vref"] = float(v)

    def rref(self, board):
        r = self._get(board).get("rref")
        return float(r) if r else DEFAULT_RREF

    def set_rref(self, board, r):
        if not 1.0 <= r <= 10e6:
            raise CalError(T("Rref fuera de rango (1 Ω a 10 MΩ)."))
        self._make(board)["rref"] = float(r)

    def channel(self, board, ch):
        c = self._get(board).get("ai", {}).get(str(ch))
        if isinstance(c, dict) and "a" in c and "b" in c:
            return c
        return None

    def set_channel(self, board, ch, a, b, pts):
        ai = self._make(board).setdefault("ai", {})
        ai[str(ch)] = {"a": a, "b": b, "pts": pts, "date": time.strftime("%Y-%m-%d %H:%M")}

    def clear_channel(self, board, ch):
        ai = self._get(board).get("ai", {})
        return ai.pop(str(ch), None) is not None

    def ohm_table(self, board):
        t = self._get(board).get("ohm")
        return t if isinstance(t, dict) and t.get("pts") else None

    def set_ohm_table(self, board, pts):
        rows = []
        for c, r in pts:
            if not 1.0 <= r <= 10e6:
                raise CalError(T("Resistencia fuera de rango (1 Ω a 10 MΩ)."))
            rows.append((ohm_z(c), math.log(r), float(c), float(r)))
        if not rows:
            raise CalError(T("Captura al menos un punto."))
        rows.sort()
        for a, b in zip(rows, rows[1:]):
            if b[0] - a[0] < OHM_MIN_GAP:
                raise CalError(T("Dos puntos dan casi la misma lectura. Revisa las resistencias."))
            if b[1] <= a[1]:
                raise CalError(T("La lectura debe subir con la resistencia. Revisa valores y "
                                 "conexiones."))
        self._make(board)["ohm"] = {"pts": [[c, r] for _z, _l, c, r in rows],
                                    "date": time.strftime("%Y-%m-%d %H:%M")}

    def clear_ohm(self, board):
        return self._get(board).pop("ohm", None) is not None

    def ohm_value(self, board, counts):
        t = self.ohm_table(board)
        if t is None:
            return None
        pts = [(ohm_z(c), math.log(r)) for c, r in t["pts"]]
        z = ohm_z(counts)
        if z <= pts[0][0]:
            lr = pts[0][1] + (z - pts[0][0])
        elif z >= pts[-1][0]:
            lr = pts[-1][1] + (z - pts[-1][0])
        else:
            lr = pts[-1][1]
            for (z0, l0), (z1, l1) in zip(pts, pts[1:]):
                if z0 <= z <= z1:
                    lr = l0 + (l1 - l0) * (z - z0) / (z1 - z0)
                    break
        return math.exp(lr)

    def probe(self, board, ch):
        p = self._get(board).get("probe", {}).get(str(ch))
        if isinstance(p, dict) and p.get("k"):
            return float(p["k"])
        return None

    def probe_info(self, board, ch):
        p = self._get(board).get("probe", {}).get(str(ch))
        return p if isinstance(p, dict) and p.get("k") else None

    def set_probe(self, board, ch, k, pts):
        if not 0.5 <= k <= 1000.0:
            raise CalError(T("Factor de sonda fuera de rango (0.5 a 1000)."))
        pr = self._make(board).setdefault("probe", {})
        pr[str(ch)] = {"k": float(k), "pts": pts, "date": time.strftime("%Y-%m-%d %H:%M")}

    def clear_probe(self, board, ch):
        return self._get(board).get("probe", {}).pop(str(ch), None) is not None

    def counts_to_volts(self, board, ch, counts):
        c = self.channel(board, ch)
        if c is None:
            return None
        return c["a"] * counts + c["b"]
